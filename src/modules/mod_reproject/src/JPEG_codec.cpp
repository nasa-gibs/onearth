/*
 * JPEG_Codec.cpp
 * C++ Wrapper around libjpeg, providing encoding and decoding functions
 * uses C++ throw-catch instead of setjmp
 *
 * (C)Lucian Plesea 2016-2017
 */

#include "mod_reproject.h"
#include <jpeglib.h>

static void emitMessage(j_common_ptr cinfo, int msgLevel);
static void errorExit(j_common_ptr cinfo);

struct ErrorMgr : public jpeg_error_mgr {
    inline ErrorMgr() {
        jpeg_std_error(this);
        error_exit = errorExit;
        emit_message = emitMessage;
    }
    // A place to hold a message
    char message[JMSG_LENGTH_MAX];
};

static void emitMessage(j_common_ptr cinfo, int msgLevel)
{
    ErrorMgr* err = (ErrorMgr *)cinfo->err;
    if (msgLevel > 0) return; // No trace msgs

    // There can be many warnings, just store the first one
    if (err->num_warnings++ >1) return;
    err->format_message(cinfo, err->message);
}

// No return to caller
static void errorExit(j_common_ptr cinfo)
{
    ErrorMgr* err = (ErrorMgr*)cinfo->err;
    err->format_message(cinfo, err->message);
    throw err->message;
}

/**
*\Brief Do nothing stub function for JPEG library, called
*/
static void stub_source_dec(j_decompress_ptr cinfo) {}

/**
*\Brief: Do nothing stub function for JPEG library
*/
static void skip_input_data_dec(j_decompress_ptr cinfo, long l) {}

// Destination should be already set up
static void init_or_terminate_destination(j_compress_ptr cinfo) {}

/**
*\Brief: Do nothing stub function for JPEG library, called?
*/
static boolean fill_input_buffer_dec(j_decompress_ptr cinfo) { return TRUE; }

// Called if the buffer provided is too small
static boolean empty_output_buffer(j_compress_ptr cinfo) { return FALSE; }

// IMPROVE: could reuse the cinfo, to save some memory allocation
// IMPROVE: Use a jpeg memory manager to link JPEG memory into apache's pool mechanism
const char *jpeg_stride_decode(codec_params &params, const TiledRaster &raster, storage_manager &src, 
    void *buffer)
{
    const char *message = NULL;
    jpeg_decompress_struct cinfo;
    ErrorMgr err;
    struct jpeg_source_mgr s = { (JOCTET *)src.buffer, static_cast<size_t>(src.size) };

    cinfo.err = &err;
    s.term_source = s.init_source = stub_source_dec;
    s.skip_input_data = skip_input_data_dec;
    s.fill_input_buffer = fill_input_buffer_dec;
    s.resync_to_restart = jpeg_resync_to_restart;

    try {
        jpeg_create_decompress(&cinfo);
        cinfo.src = &s;
        jpeg_read_header(&cinfo, TRUE);
        cinfo.dct_method = JDCT_FLOAT;
        if (!(raster.pagesize.c == 1 || raster.pagesize.c == 3))
            throw "JPEG only handles one or three color components";

        cinfo.out_color_space = (raster.pagesize.c == 3) ? JCS_RGB : JCS_GRAYSCALE;
        jpeg_start_decompress(&cinfo);
        char *rp[2]; // Two lines at a time

        while (cinfo.output_scanline < cinfo.image_height) {
            rp[0] = (char *)buffer + params.line_stride * cinfo.output_scanline;
            rp[1] = rp[0] + params.line_stride;
            jpeg_read_scanlines(&cinfo, JSAMPARRAY(rp), 2);
        }
        jpeg_finish_decompress(&cinfo);
    }
    catch (char *error) { // Capture the error
        strcpy(params.error_message, error);
        message = params.error_message;
    }

    jpeg_destroy_decompress(&cinfo);
    return message; // Either null or error message
}

const char *jpeg_encode(jpeg_params &params, const TiledRaster &raster, storage_manager &src, 
    storage_manager &dst)
{
    const char *message = NULL;
    struct jpeg_compress_struct cinfo;
    ErrorMgr err;
    jpeg_destination_mgr mgr;

    mgr.next_output_byte = (JOCTET *)dst.buffer;
    mgr.free_in_buffer = dst.size;
    mgr.init_destination = init_or_terminate_destination;
    mgr.empty_output_buffer = empty_output_buffer;
    mgr.term_destination = init_or_terminate_destination;
    cinfo.err = &err;

    try {
        jpeg_create_compress(&cinfo);
        cinfo.dest = &mgr;
        cinfo.image_width = static_cast<JDIMENSION>(raster.pagesize.x);
        cinfo.image_height = static_cast<JDIMENSION>(raster.pagesize.y);
        cinfo.input_components = static_cast<int>(raster.pagesize.c);
        cinfo.in_color_space = (raster.pagesize.c == 3) ? JCS_RGB : JCS_GRAYSCALE;

        jpeg_set_defaults(&cinfo);

        jpeg_set_quality(&cinfo, params.quality, TRUE);
        cinfo.dct_method = JDCT_FLOAT;
        int linesize = cinfo.image_width * cinfo.num_components;

        char *rp[2];
        jpeg_start_compress(&cinfo, TRUE);
        while (cinfo.next_scanline != cinfo.image_height) {
            rp[0] = src.buffer + linesize * cinfo.next_scanline;
            rp[1] = rp[0] + linesize;
            jpeg_write_scanlines(&cinfo, JSAMPARRAY(rp), 2);
        }
        jpeg_finish_compress(&cinfo);
    }
    catch (char *error_message) {
        strcpy(params.error_message, error_message);
        message = params.error_message;
    }

    jpeg_destroy_compress(&cinfo);
    dst.size -= mgr.free_in_buffer;
    return message;
}
