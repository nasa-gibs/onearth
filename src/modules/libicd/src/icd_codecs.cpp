#include "icd_codecs.h"
#include <string>
#include <cctype>
#include <cstring>

NS_ICD_START

// Given a data type name, returns a data type
ICDDataType getDT(const char* name)
{
    if (name == nullptr)
        return ICDT_Byte;

    std::string s(name);
    for (auto& c : s)
        c = std::tolower(c);

    if (s == "uint16")
        return ICDT_UInt16;
    if (s == "int16" || s == "short")
        return ICDT_Int16;
    if (s == "uint32")
        return ICDT_UInt32;
    if (s == "int" || s == "int32" || s == "long")
        return ICDT_Int32;
    if (s == "float" || s == "float32")
        return ICDT_Float32;
    if (s == "double" || s == "float64")
        return ICDT_Float64;
    else
        return ICDT_Byte;
}

size_t getTypeSize(ICDDataType dt, size_t n) {
    switch (dt) {
    case ICDT_Byte:
        return n;
    case ICDT_UInt16:
    case ICDT_Short:
        return 2 * n;
    case ICDT_UInt32:
    case ICDT_Int:
    case ICDT_Float:
        return 4 * n;
    case ICDT_Double:
        return 8 * n;
    default:
        return ~0;
    }
}

IMG_T getFMT(const char *name) {
    std::string s(name);
    if (s == "image/jpeg")
        return IMG_JPEG;
    if (s == "image/png")
        return IMG_PNG;
    if (s == "raster/lerc")
        return IMG_LERC;
    return IMG_UNKNOWN;
}


const char* stride_decode(codec_params& params, storage_manager& src, void* buffer, int &ct, png_colorp &palette, png_bytep &trans, int &num_trans)
{
    const char* error_message = nullptr;
    uint32_t sig = 0;
    memcpy(&sig, src.buffer, sizeof(sig));
    params.raster.format = IMG_UNKNOWN;
    switch (sig)
    {
    case JPEG_SIG:
    case JPEG1_SIG:
        params.raster.format = IMG_JPEG;
        error_message = jpeg_stride_decode(params, src, buffer);
        break;
    case PNG_SIG:
        params.raster.format = IMG_PNG;
        error_message = png_stride_decode(params, src, buffer, ct, palette, trans, num_trans);
        break;
    case LERC_SIG:
        params.raster.format = IMG_LERC;
        error_message = lerc_stride_decode(params, src, buffer);
        break;
    default:
        error_message = "Decode requested for unknown format";
    }
    return error_message;
}


const char* image_peek(const storage_manager& src, Raster& raster) {
    uint32_t sig = 0;
    if (src.size < sizeof(sig))
        return "Input buffer too small";
    memcpy(&sig, src.buffer, sizeof(sig));
    switch (sig) {
    case JPEG_SIG:
    case JPEG1_SIG:
        return jpeg_peek(src, raster);
    case PNG_SIG:
        return png_peek(src, raster);
    case LERC_SIG:
        return lerc_peek(src, raster);
    }
    return "Unknown format";
}

const char* Raster::init(const storage_manager& src) {
    return image_peek(src, *this);
}

NS_END