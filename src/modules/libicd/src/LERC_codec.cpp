/*
* LERC_codec.cpp
* C++ Wrapper around lerc1, providing encoding and decoding functions
*
* Modified from: https://github.com/OSGeo/gdal/blob/master/gdal/frmts/mrf/LERC_band.cpp
* 
* (C)Lucian Plesea 2020
* Lerc1 is only little endian, it should not be compiled on big endian machines
*/

#include "icd_codecs.h"
#if !defined(NEED_SWAP)
#error Lerc 1 only works in little endian
#endif

#include "lerc1/Lerc1Image.h"
#include <string>

USING_NAMESPACE_LERC1
NS_ICD_START

// Reads and unaligned value, increments the pointer
template <typename T>
void READP(T& X, const char*& p) {
    memcpy(&X, p, sizeof(X));
    p += sizeof(X);
}

// Arbitrary epsilon
static bool FIsEqual(float v1, float v2) {
    return abs(v1 - v2) < 1e-12;
}

template<typename T> static void Lerc1ImgFill(Lerc1Image& zImg, T* src, const lerc_params &params) {
    auto const& rsize = params.raster.size;
    int w = static_cast<int>(rsize.x);
    int h = static_cast<int>(rsize.y);
    zImg.resize(w, h);
    const auto ndv = static_cast<float>(params.raster.ndv);
    for (int row = 0; row < h; row++)
        for (int col = 0; col < w; col++) {
            auto val = static_cast<float>(*src++);
            zImg(row, col) = val;
            zImg.SetMask(row, col, !FIsEqual(ndv, val));
        }
}

const char* lerc_encode(lerc_params& params, storage_manager& src, storage_manager& dst) {
    Lerc1Image zImg;

    switch (params.raster.dt) {
#define FILL(T) Lerc1ImgFill(zImg, reinterpret_cast<T *>(src.buffer), params)
    case ICDT_Byte: FILL(uint8_t); break;
    case ICDT_UInt16: FILL(uint16_t); break;
    case ICDT_Int16: FILL(int16_t); break;
    case ICDT_UInt32: FILL(uint32_t); break;
    case ICDT_Int32: FILL(int32_t); break;
    case ICDT_Float32: FILL(float); break;
    default:
        return "Unsupported data type for LERC1 encode"; // Error return
    }
#undef FILL
    auto buffer = reinterpret_cast<Lerc1NS::Byte*>(dst.buffer);
    auto pdst = buffer;
    if (!zImg.write(&pdst, params.prec))
        return "Error during LERC1 compression";
    // Write advances the pdst pointer
    auto pd = static_cast<size_t>(pdst - buffer);
    // This is too late, better than never?
    if (pd > dst.size)
        return "Output buffer overflow";
    dst.size = pd;
    return nullptr;
}

static const char ERR_LERC[] = "Corrupt or invalid LERC1";
static const char ERR_SMALL[] = "Input buffer too small";

const char* lerc_peek(const storage_manager& src, Raster& raster)
{
    auto minlerc = Lerc1Image::computeNumBytesNeededToWriteVoidImage();
    if (src.size < minlerc)
        return ERR_SMALL;

    const char* s = reinterpret_cast<char *>(src.buffer);
    std::string l1sig(s, s + 10);
    if (l1sig != "CntZImage ")
        return ERR_LERC;
    s += 10;
    uint32_t version, tpe;
    READP(version, s); READP(tpe, s);
    if (version != 11 || tpe != 8)
        return ERR_LERC;

    // Next is the size of the raster itself
    uint32_t h, w;
    READP(h, s); READP(w, s);
    if (w > 20000 || h > 20000)
        return ERR_LERC;
    raster.size.x = w;
    raster.size.y = h;

    // Read the LERC_PREC double
    READP(raster.res, s);

    // First array header is the mask, 0 blocks
    READP(h, s); READP(w, s);
    if (h > 0 || w > 0)
        return ERR_LERC;

    uint32_t msz; // Mask size, in bytes
    READP(msz, s);
    // mask max value shold be 1, or maybe 0 (empty)
    float mmval;
    READP(mmval, s);
    if (mmval != 0.0f && mmval != 1.0f)
        return ERR_LERC;

    if (static_cast<size_t>(minlerc) + msz > src.size)
        return ERR_SMALL;
    s += msz;

    // Second array is data
    // Data block count, never single pixels, at most size / 2
    READP(h, s);
    READP(w, s);
    if (h > raster.size.y / 2 || w > raster.size.x / 2)
        return ERR_LERC;
    uint32_t dsz; // data size, in bytes
    READP(dsz, s);
    float maxval;
    READP(maxval, s);
    raster.max = maxval;
    raster.has_max = true;

    // Good enough
    if (static_cast<size_t>(minlerc - 1) + msz + dsz > src.size)
        return ERR_SMALL;

    raster.dt = ICDT_Unknown; // LERC1 can be read as anything
    raster.format = IMG_LERC;
    return nullptr;
}

template <typename T> static void Lerc1ImgUFill(Lerc1Image& zImg, 
    const codec_params &params, T* buffer) {
    const auto ndv = static_cast<T>(params.raster.ndv);
    for (int row = 0; row < zImg.getHeight(); row++) {
        auto ptr = reinterpret_cast<T*>(reinterpret_cast<char *>(buffer) 
            + static_cast<size_t>(row) * params.line_stride);
        for (int col = 0; col < zImg.getWidth(); col++)
            *ptr++ = zImg.IsValid(row, col) ? static_cast<T>(zImg(row, col)) : ndv;
    }
}

const char* lerc_stride_decode(codec_params& params, storage_manager& src, void* buffer) {
    auto const& rsize = params.raster.size;
    if (rsize.c != 1)
        return "Lerc1 multi-band is not supported";

    Raster lerc_raster;
    auto err_message = lerc_peek(src, lerc_raster);
    if (err_message)
        return err_message;

    // Set default line stride if it wasn't specified explicitly
    if (0 == params.line_stride)
        params.line_stride = getTypeSize(params.raster.dt, rsize.x);
    Lerc1Image zImg;

    size_t nRemainingBytes = src.size;
    auto ptr = reinterpret_cast<Lerc1NS::Byte*>(src.buffer);
    if (!zImg.read(&ptr, nRemainingBytes, 1e12))
        return "Error during LERC decompression";
    if (static_cast<size_t>(zImg.getHeight()) != rsize.y 
        || static_cast<size_t>(zImg.getWidth()) != rsize.x)
        return "Image received has the wrong size";

    // Got the data and the mask in zImg
#define UFILL(T) Lerc1ImgUFill(zImg, params, reinterpret_cast<T*>(buffer))
    switch (params.raster.dt) {
    case ICDT_Byte: UFILL(uint8_t); break;
    case ICDT_UInt16: UFILL(uint16_t); break;
    case ICDT_Int16: UFILL(int16_t); break;
    case ICDT_UInt32: UFILL(uint32_t); break;
    case ICDT_Int32: UFILL(int32_t); break;
    case ICDT_Float: UFILL(float); break;
    default: break;
    }
#undef UFILL

    return nullptr; // Success
}

NS_END
