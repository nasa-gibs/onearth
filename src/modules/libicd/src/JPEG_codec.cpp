/*
 * JPEG_Codec.cpp
 * C++ Wrapper around libjpeg, providing encoding and decoding functions
 *
 * use setjmp, the only safe way to mix C++ and libjpeg and still get error messages
 *
 * (C)Lucian Plesea 2016-2019
 */

#include "JPEG_codec.h"
#include <algorithm>
// For string.find()
#include <string>
// For strcpy & co
#include <cstring>

NS_ICD_START

const char* jpeg_peek(const storage_manager& src, Raster& raster)
{
    const unsigned char* buffer = reinterpret_cast<unsigned char*>(src.buffer);
    const unsigned char* sentinel = buffer + src.size;

    if (src.size < 10) // It should be much larger than this
        goto ERR;

    if (*buffer != 0xff || buffer[1] != 0xd8)
        goto ERR_NOTJPEG; // SOI header not found
    buffer += 2;

    while (buffer < sentinel) {
        int sz;
        if (*buffer++ != 0xff)
            continue; // Skip non-markers, in case padding exists

        // Make sure we can read at least one more byte
        if (buffer >= sentinel)
            break;

        // Flags with no size, RST, EOI, TEM or raw 0xff byte
        if (((*buffer & 0xf8) == 0xd0) || (*buffer == 0xd9) || (*buffer <= 1)) {
            buffer++;
            continue;
        }

        switch (*buffer++) {
        case 0xc0: // SOF0, baseline which includes the size and precision
        case 0xc1: // SOF1, also baseline
            // Chunk size, in big endian short, has to be at least 11
            sz = 256 * buffer[0] + buffer[1];
            if (buffer + sz >= sentinel)
                break; // Error in JPEG

            // Size of SOF is at least 8 + 3 * bands;
            if (sz < 11 || buffer[7] * 3 + 8 != sz)
                goto ERR_NOTJPEG;

            // precision in bits is stored in the byte right after the chunk size
            sz = static_cast<int>(buffer[2]);
            if (sz != 8 && sz != 12) // Only 8 and 12 are valid
                goto ERR_NOTJPEG;
            raster.dt = (sz == 8) ? ICDT_Byte : ICDT_UInt16;

            // The precision is followed by y size and x size, each two bytes
            // in big endian order
            // Then comes 1 byte, number of components
            // Then 3 bytes per component
            // Byte 1, type
            //  1 - Y, 2 - Cb, 3 - Cr, 4 - I, 5 Q
            // Byte 2, sampling factors
            //  Bits 0-3 vertical, 4-7 horizontal
            // Byte 3, Which quantization table to use

            // Pick up raster size            
            raster.size.y = 256ull * buffer[3] + buffer[4];
            raster.size.x = 256ull * buffer[5] + buffer[6];
            raster.size.c = buffer[7];

            raster.format = IMG_JPEG;
            return nullptr; // Normal exit, found the header


        case 0xda:
            // Reaching the start of scan without finding the frame 0 is an error
            goto ERR_NOTJPEG;

        default: // Normal segments with size, safe to skip
            if (buffer + 2 >= sentinel)
                break;

            sz = (static_cast<int>(*buffer) << 8) | buffer[1];
            buffer += sz;
        }
    }

ERR:
    return "Input buffer too small"; // Something went wrong

ERR_NOTJPEG:
    return "Corrupt or invalid JPEG";
}

// Dispatcher for 8 or 12 bit jpeg decoder
const char* jpeg_stride_decode(codec_params& params, storage_manager& src, void* buffer)
{
    constexpr size_t MSGSZ = sizeof(params.error_message) - 1;
    Raster img_raster;
    const char* err_message = jpeg_peek(src, img_raster);
    if (err_message) {
        strncpy(params.error_message, err_message, MSGSZ);
        return params.error_message;
    }

    return (img_raster.dt == ICDT_Byte) ?
        jpeg8_stride_decode(params, src, buffer)
        : jpeg12_stride_decode(params, src, buffer);
}

const char *jpeg_encode(jpeg_params &params, storage_manager &src, storage_manager &dst)
{
    constexpr size_t MSGSZ = sizeof(params.error_message) - 1;
    const char* message = nullptr;
    switch (getTypeSize(params.raster.dt)) {
    case 1:
        message = jpeg8_encode(params, src, dst);
        break;
    case 2:
        message = jpeg12_encode(params, src, dst);
        break;
    default:
        message = "Usage error, only 8 and 12 bit input can be encoded as JPEG";
    }
    if (!message)
        return nullptr;

    // Had an error reported
    strncpy(params.error_message, message, MSGSZ);
    if (std::string::npos != std::string(message).find("Write to EMS")) {
        // Convert weird message to the actual reason
        strncpy(params.error_message, "Write buffer too small", MSGSZ);
        message = params.error_message;
    }
    return message;
}

NS_END // ICD
