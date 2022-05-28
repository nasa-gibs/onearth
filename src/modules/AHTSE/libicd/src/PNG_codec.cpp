/*
* PNG_codec.cpp
* C++ Wrapper around libpng, providing encoding and decoding functions
*
* This code only handles a basic subset of the PNG capabilities
*
* (C)Lucian Plesea 2016-2020
*/

#include "icd_codecs.h"
#include <vector>
#include <png.h>
#include <string>
#include <cstring>
#include <cassert>

NS_ICD_START

// TODO: Add palette PNG support, possibly other fancy options

png_params::png_params(const Raster& r) : codec_params(r)
    , color_type(0)
    , bit_depth((raster.dt == ICDT_Byte) ? 8 : 16)
    , compression_level(6)
    , has_transparency(false)
{
    assert(raster.size.c < 5);
    static int ctypes[] = {PNG_COLOR_TYPE_GRAY , PNG_COLOR_TYPE_GA , PNG_COLOR_TYPE_RGB , PNG_COLOR_TYPE_RGBA };
    color_type = ctypes[raster.size.c - 1];
    has_transparency = color_type & 1;
}

// Memory output doesn't need flushing
static void flush_png(png_structp) {};

// Do nothing for warnings
static void pngWH(png_structp pngp, png_const_charp message) {};

// Error function
static void pngEH(png_structp pngp, png_const_charp message)
{
    codec_params* params = reinterpret_cast<codec_params*>(png_get_error_ptr(pngp));
    strncpy(params->error_message, message, 1024);
    longjmp(png_jmpbuf(pngp), 1);
}

// Read memory handler for PNG
static void get_data(png_structp pngp, png_bytep data, png_size_t length)
{
    storage_manager *src = reinterpret_cast<storage_manager *>(png_get_io_ptr(pngp));
    if (static_cast<png_size_t>(src->size) < length) {
        codec_params* params = (codec_params*)(png_get_error_ptr(pngp));
        strcpy(params->error_message, "PNG decode expects more data than given");
        longjmp(png_jmpbuf(pngp), 1);
    }
    memcpy(data, src->buffer, length);
    src->buffer = reinterpret_cast<char*>(src->buffer) + length;
    src->size -= length;
}

// Write memory handler for PNG
static void store_data(png_structp pngp, png_bytep data, png_size_t length)
{
    storage_manager *dst = static_cast<storage_manager *>(png_get_io_ptr(pngp));
    if (static_cast<png_size_t>(dst->size) < length) {
        codec_params* params = (codec_params*)(png_get_error_ptr(pngp));
        strcpy(params->error_message, "PNG encode buffer overflow");
        longjmp(png_jmpbuf(pngp), 1);
    }
    memcpy(dst->buffer, data, length);
    dst->buffer = reinterpret_cast<char*>(dst->buffer) + length;
    dst->size -= length;
}

static const char ERR_PNG[] = "Corrupt or invalid PNG";
static const char ERR_SMALL[] = "Input buffer too small";
static const char ERR_DIFFERENT[] = "Unknown type of PNG";

static uint32_t readBE32(const unsigned char* src) {
    uint32_t result = 0;
    memcpy(&result, src, 4);
    return be32toh(result);
}

const char* png_peek(const storage_manager& src, Raster& raster)
{
    const unsigned char* buffer = reinterpret_cast<unsigned char*>(src.buffer);
    const unsigned char* sentinel = buffer + src.size;
    if (src.size < 8)
        return ERR_SMALL;
    if (!png_check_sig(buffer, 8))
        return ERR_PNG;
    buffer += 8;

    bool seen_IHDR = false;
    bool seen_IDAT = false;
    bool seen_IEND = false;

    // A chunk is at least 12 bytes
    while (!seen_IEND && buffer + 12 <= sentinel) {
        auto size = readBE32(buffer);
        buffer += 4;
        std::string chunk(buffer, buffer + 4);
        buffer += 4;
        // deal with known types of chunk
        if (chunk == "IHDR") { // Has to be first
            if (seen_IHDR) // Only once
                return ERR_PNG;
            if (size != 13 || buffer + size + 4 > sentinel)
                return ERR_PNG;
            raster.size.x = readBE32(buffer);
            raster.size.y = readBE32(buffer + 4);
            // Bits per sample
            auto bps = buffer[8]; // Valid values are 1, 2, 4, 8, 16, but we only handle 8 and 16
            if (bps == 8)
                raster.dt = ICDT_Byte;
            else if (bps == 16)
                raster.dt = ICDT_UInt16;
            else
                return ERR_DIFFERENT;

            /*  buffer[9] is color type, mostly ignored
            From https://www.w3.org/TR/PNG-Chunks.html

                Color    Allowed        Interpretation
                Type    Bit Depths

                0       1, 2, 4, 8, 16  Each pixel is a grayscale sample.

                2       8, 16           Each pixel is an R, G, B triple.

                3       1, 2, 4, 8      Each pixel is a palette index;
                                        a PLTE chunk must appear.

                4       8, 16           Each pixel is a grayscale sample,
                                        followed by an alpha sample.

                6       8, 16           Each pixel is an R, G, B triple,
                                        followed by an alpha sample.
            */

            auto ctype = buffer[9];
            static const uint8_t bands[] = { 1, 255, 3, 1, 2, 255, 4 };
            if (ctype > 6 || bands[ctype] > 4)
                return ERR_DIFFERENT;
            raster.size.c = bands[ctype];

            // buffer[10] is compression method, only 0 is defined
            if (buffer[10])
                return ERR_DIFFERENT;

            // buffer[11] is filter method. Only 0 supported
            if (buffer[11])
                return ERR_DIFFERENT;

            // buffer[12] is interlace method, 0 and 1 supported
            if (buffer[12] > 1)
                return ERR_DIFFERENT;
            seen_IHDR = true;
        }
        else if (!seen_IHDR) {
            // Every other type is after IHDR
            return ERR_PNG;
        }
        else if (chunk == "IDAT") {
            // Data chunk
            seen_IDAT = true;
        }
        else if (chunk == "IEND") {
            // End of the PNG, should have no data
            if (size || !seen_IDAT)
                return ERR_PNG;
            seen_IEND = true;
        }

        // Ignore all the other chunk types, assume they are fine

        // Skip the chunk data, if any
        if (size) {
            if (size >> 31) // max chunk size is 2^31 - 1
                return ERR_PNG;
            buffer += size;
            // Check that we still have enough space for the CRC
            if (buffer + 4 > sentinel)
                return ERR_PNG;
        }

        buffer += 4; // Skip the CRC, assume OK
    }

    if (!seen_IEND)
        return ERR_SMALL;

    // All OK
    raster.format = IMG_PNG;
    return nullptr;
}

const char *png_stride_decode(codec_params &params, storage_manager &src, void *buffer, int &ct, png_colorp &palette, png_bytep &trans, int &num_trans)
{
    png_structp pngp = nullptr;
    png_infop infop = nullptr;
    png_uint_32 width, height;
    int bit_depth;
    pngp = png_create_read_struct(PNG_LIBPNG_VER_STRING, &params, pngEH, pngEH);
    if (!pngp)
        return "PNG error while creating decode PNG structure";
    infop = png_create_info_struct(pngp);
    if (!infop)
        return "PNG error while creating decode info structure";

    if (setjmp(png_jmpbuf(pngp)))
        return params.error_message;

    png_set_read_fn(pngp, &src, get_data);

    // This reads all chunks up to the first IDAT
    png_read_info(pngp, infop);

    png_get_IHDR(pngp, infop, &width, &height, &bit_depth, &ct, NULL, NULL, NULL);
    
    int num_palette;
    png_color_16 *trans_values;
    png_colorp palettep;
    if (params.raster.size.c == 1) {
        png_get_PLTE(pngp, infop, &palettep, &num_palette);
        for (int p = 0; p < num_palette; p++) {
            palette[p].red = palettep[p].red;
            palette[p].green = palettep[p].green;
            palette[p].blue = palettep[p].blue;
        }
        png_bytep transp;
        png_get_tRNS(pngp, infop, &transp, &num_trans, &trans_values);
        for (int p = 0; p < num_trans; p++) {
            trans[p] = transp[p];
        }
    }
    auto const& rsize = params.raster.size;
    if (rsize.y != static_cast<size_t>(height)
        || rsize.x != static_cast<size_t>(width)) {
        strcpy(params.error_message, "Input PNG has the wrong size");
        longjmp(png_jmpbuf(pngp), 1);
    }

    if ((params.raster.dt == ICDT_Byte && bit_depth != 8) ||
        ((params.raster.dt == ICDT_UInt16 || params.raster.dt == ICDT_Int16) && bit_depth != 16)) {
        strcpy(params.error_message, "Input PNG has the wrong type");
        longjmp(png_jmpbuf(pngp), 1);
    }

#if defined(NEED_SWAP)
    if (bit_depth > 8)
        png_set_swap(pngp);
#endif

    // TODO: Decode to expected format
    // png_set_palette_to_rgb(pngp); // Palette to RGB
    // png_set_tRNS_to_alpha(pngp); // transparency to Alpha
    // png_set_add_alpha(pngp, 255, PNG_FILTER_AFTER); // Add alpha if not there
    // Call this after using any of the png_set_*
    png_read_update_info(pngp, infop);

    auto line_stride = static_cast<png_size_t>(params.line_stride);
    if (0 == line_stride)
        line_stride = png_get_rowbytes(pngp, infop);

    std::vector<png_bytep> png_rowp(rsize.y);
    for (size_t i = 0; i < png_rowp.size(); i++) // line_stride is always in bytes
        png_rowp[i] = reinterpret_cast<png_bytep>(
            static_cast<char*>(buffer) + i * line_stride);

    png_read_image(pngp, png_rowp.data());
    png_read_end(pngp, infop);
    png_destroy_read_struct(&pngp, &infop, 0);

    return nullptr;
}

const char *png_encode(png_params &params, storage_manager &src, storage_manager &dst, png_colorp &palette, png_bytep &trans, int &num_trans)
{
    png_structp pngp = nullptr;
    png_infop infop = nullptr;
    auto const& rsize = params.raster.size;
    png_uint_32 width = static_cast<png_uint_32>(rsize.x);
    png_uint_32 height = static_cast<png_uint_32>(rsize.y);
    // Check inputs for sanity
    if (getTypeSize(params.raster.dt) > 2)
        return "Invalid PNG encoding data type";
    // if (rsize.x * rsize.y * getTypeSize(params.raster.dt) > src.size)
    //     return "Insufficient input data for PNG encoding";
    // Use a vector so it cleans up itself
    std::vector<png_bytep> png_rowp(height);

    // To avoid changing the buffer pointer
    storage_manager mgr = dst;

    pngp = png_create_write_struct(PNG_LIBPNG_VER_STRING, &params, pngEH, pngWH);
    if (!pngp)
        return "PNG error while creating encoding PNG structure";
    infop = png_create_info_struct(pngp);
    if (!infop)
        return "PNG error while creating encoding info structure";
    if (setjmp(png_jmpbuf(pngp)))
        return params.error_message;

    png_set_write_fn(pngp, &mgr, store_data, flush_png);
    png_set_IHDR(pngp, infop, width, height, params.bit_depth, params.color_type,
        PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);
    png_set_compression_level(pngp, params.compression_level);
    if (params.color_type == PNG_COLOR_TYPE_PALETTE) {
        png_set_PLTE(pngp, infop, palette, 256);
    }
    // Flag NDV as transparent color
    if (params.has_transparency) {
        // TODO: Pass the transparent color via params.
        // For now, 0 is the no data value, regardless of the type of data
        if (params.color_type == PNG_COLOR_TYPE_PALETTE) {
            png_set_tRNS(pngp, infop, trans, num_trans, NULL);
        } else {
            png_color_16 tcolor;
            memset(&tcolor, 0, sizeof(png_color_16));
            png_set_tRNS(pngp, infop, 0, 0, &tcolor);
        }
    }

#if defined(NEED_SWAP)
    if (params.bit_depth > 8)
        png_set_swap(pngp);
#endif

    auto rowbytes = png_get_rowbytes(pngp, infop);
    for (size_t i = 0; i < png_rowp.size(); i++)
        png_rowp[i] = reinterpret_cast<png_bytep>(src.buffer) + i * rowbytes;
    // Last check, do we have enough input
    // if (png_rowp.size() * rowbytes > src.size) {
    //     png_destroy_write_struct(&pngp, &infop);
    //     return "Insufficient input data for PNG encoding";
    // }

    png_write_info(pngp, infop);
    png_write_image(pngp, png_rowp.data());
    png_write_end(pngp, infop);

    png_destroy_write_struct(&pngp, &infop);
    dst.size -= mgr.size; // mgr.size is bytes left

    return nullptr;
}

int set_png_params(const Raster &raster, png_params *params) {
    // Pick some defaults
    // Only handles 8 or 16 bits
    memset(params, 0, sizeof(png_params));
    params->raster = raster;
    params->bit_depth = (raster.dt == ICDT_Byte) ? 8 : 16;
    params->compression_level = 6;
    params->has_transparency = false;

    switch (raster.size.c) {
    case 1:
        params->color_type = PNG_COLOR_TYPE_GRAY;
        break;
    case 2:
        params->color_type = PNG_COLOR_TYPE_GA;
        break;
    case 3:
        params->color_type = PNG_COLOR_TYPE_RGB;
        break;
    case 4:
        params->color_type = PNG_COLOR_TYPE_RGBA;
        break;
    }
    return 0;
}

NS_END
