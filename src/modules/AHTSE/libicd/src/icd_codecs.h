/*
* icd_codecs.h
*
* Raster codecs only
* No include dependencies on apr or http
* No include dependencies on actual codec libraries
*
* (C) Lucian Plesea 2019-2021
*/

#pragma once

#if !defined(ICD_CODECS_H)
#define ICD_CODECS_H

#if !defined(NS_ICD_START)
#define NS_ICD_START namespace ICD {
#define NS_END }
#define NS_ICD_USE using namespace ICD;
#endif

#include <cstdint>
#include <cstddef>
#include <png.h>
//
// Define DLL_PUBLIC to make a symbol visible
// Define DLL_LOCAL to hide a symbol
// Default behavior is system depenent
//

#ifdef DLL_PUBLIC
#undef DLL_PUBLIC
#endif

#ifdef DLL_LOCAL
#undef DLL_LOCAL
#endif

#if defined _WIN32 || defined __CYGWIN__
#define DLL_LOCAL

#ifdef libicd_EXPORTS

#ifdef __GNUC__
#define DLL_PUBLIC __attribute__ ((dllexport))
#else
#define DLL_PUBLIC __declspec(dllexport)
#endif
#else
#ifdef __GNUC__
#define DLL_PUBLIC __attribute__ ((dllimport))
#else
#define DLL_PUBLIC __declspec(dllimport)
#endif
#endif

#else
// Not windows
#if __GNUC__ >= 4
#define DLL_PUBLIC __attribute__ ((visibility ("default")))
#define DLL_LOCAL  __attribute__ ((visibility ("hidden")))
#else
#define DLL_PUBLIC
#define DLL_LOCAL
#endif

#endif

#if defined(__BYTE_ORDER__) && (__BYTE_ORDER__ == __ORDER_BIG_ENDIAN__)
#define IS_BIGENDIAN
#else
#endif

#if IS_BIGENDIAN // Big endian, do nothing

// These values are big endian
#define PNG_SIG 0x89504e47
#define JPEG_SIG 0xffd8ffe0
// JPEG has two signatures
#define JPEG1_SIG 0xffd8ffe1

// Lerc is only supported on little endian
#define LERC_SIG 0x436e745a

// This one is not an image type, but an encoding
#define GZIP_SIG 0x1f8b0800

#else // Little endian

// For formats that need net order, equivalent to !IS_BIGENDIAN
#define NEED_SWAP

#if defined(_WIN32)
// Windows is always little endian, supply functions to swap bytes
 // These are defined in <cstdlib>
#define htobe16 _byteswap_ushort
#define be16toh _byteswap_ushort
#define htobe32 _byteswap_ulong
#define be32toh _byteswap_ulong
#define htobe64 _byteswap_uint64
#define be64toh _byteswap_uint64

#define le64toh(X) (X)
#define htole64(X) (X)

#else
// Assume linux
#include <endian.h>

#endif

#define PNG_SIG  0x474e5089
#define JPEG_SIG 0xe0ffd8ff
#define JPEG1_SIG 0xe1ffd8ff
#define LERC_SIG 0x5a746e43

// This one is not an image type, but an encoding
#define GZIP_SIG 0x00088b1f

#endif

NS_ICD_START

// Pixel value data types
// Copied and slightly modified from GDAL
typedef enum {
    ICDT_Unknown = 0,    // Unknown or unspecified type
    ICDT_Byte = 1,       // Eight bit unsigned integer
    ICDT_Char = 1,
    ICDT_UInt16 = 2,     // Sixteen bit unsigned integer
    ICDT_Int16 = 3,      // Sixteen bit signed integer
    ICDT_Short = 3,
    ICDT_UInt32 = 4,     // Thirty two bit unsigned integer
    ICDT_Int32 = 5,      // Thirty two bit signed integer
    ICDT_Int = 5,
    // Keep the floats at the end
    ICDT_Float32 = 6,    // Thirty two bit floating point
    ICDT_Float = 6,
    ICDT_Float64 = 7,    // Sixty four bit floating point
    ICDT_Double = 7
    //    ICDT_TypeCount = 8   // Not a type
} ICDDataType;

// IMG_ANY is the default, but no checks can be done at config time
// On input, it decodes to byte, on output it is equivalent to IMG_JPEG
// JPEG is always JPEG_ZEN
enum IMG_T { IMG_ANY = 0, IMG_JPEG, IMG_PNG, IMG_LERC, IMG_UNKNOWN };

DLL_PUBLIC IMG_T getFMT(const char *name);

// Size in bytes
DLL_PUBLIC size_t getTypeSize(ICDDataType dt, size_t num = 1);

// Return a data type by name
DLL_PUBLIC ICDDataType getDT(const char* name);

struct sz5 {
    size_t x, y, z, c, l;
    const bool operator==(const sz5& other) {
        return (x == other.x) & (y == other.y) & (z == other.z) & (c == other.c) & (l == other.l);
    }
    const bool operator!=(const sz5& other) {
        return !operator==(other);
    }
};

struct storage_manager {
    storage_manager(void) : buffer(nullptr), size(0) {}
    storage_manager(void* ptr, size_t _size) :
        buffer(ptr), size(_size) {};
    void * buffer;
    size_t size; // In bytes
};

struct Raster {
    sz5 size;
    double ndv, min, max, res;
    int has_ndv, has_min, has_max;
    ICDDataType dt;
    IMG_T format;
    // Populates size from a compressed source
    const char* init(const storage_manager& src);
};

//
// Any decoder needs a static place for an error message and a line stride when decoding
// This structure is accepted by the decoders, regardless of type
// For encoders, see format specific extensions below
//
struct codec_params {
    DLL_PUBLIC codec_params(const Raster& r) :
        raster(r),
        line_stride(0),
        error_message({0}),
        modified(false)
    { reset(); }

    // Call if modifying the raster
    DLL_PUBLIC void reset() {
        line_stride = getTypeSize(raster.dt, raster.size.x * raster.size.c);
    }

    DLL_PUBLIC size_t get_buffer_size() const {
        return getTypeSize(raster.dt, raster.size.x * raster.size.y * raster.size.c);
    }

    Raster raster;
    // Line size in bytes for decoding only
    size_t line_stride;
    // A buffer for codec error message
    char error_message[1024];
    // Set if special data handling took place during decoding (zero mask on JPEG)
    bool modified;
};

// Specialized by format, for encode
struct jpeg_params : codec_params {
    DLL_PUBLIC jpeg_params(const Raster& r) : codec_params(r), quality(75) {}
    int quality;
};

struct png_params : codec_params {
    DLL_PUBLIC png_params(const Raster& r);

    // As defined by PNG
    int color_type, bit_depth;
    // 0 to 9
    int compression_level;

    // If true, NDV is the transparent color
    int has_transparency;
    // TODO: Have a way to pass the transparent color when has_transparency is true
};

struct lerc_params : codec_params {
    lerc_params(const Raster& r) : codec_params(r), prec(r.res / 2) {
        if (r.dt < ICDT_Float && prec < 0.5)
            prec = 0.5;
    }
    double prec; // half of quantization step
};

// Generic image decode dispatcher, parameters should be already set to what is expected
// Returns error message or null.
DLL_PUBLIC const char* image_peek(const storage_manager& src, Raster& raster);
DLL_PUBLIC const char* stride_decode(codec_params& params, storage_manager& src, void* buffer, int &ct, png_colorp &palette, png_bytep &trans, int &num_trans);

// In JPEG_codec.cpp
// raster defines the expected tile
// src contains the input JPEG
// buffer is the location of the first byte on the first line of decoded data
// line_stride is the size of a line in buffer (larger or equal to decoded JPEG line)
// Returns NULL if everything looks fine, or an error message
DLL_PUBLIC const char* jpeg_peek(const storage_manager& src, Raster& raster);
DLL_PUBLIC const char* jpeg_stride_decode(codec_params& params, storage_manager& src, void* buffer);
DLL_PUBLIC const char* jpeg_encode(jpeg_params& params, storage_manager& src, storage_manager& dst);

// In PNG_codec.cpp
// raster defines the expected tile
// src contains the input PNG
// buffer is the location of the first byte on the first line of decoded data
// line_stride is the size of a line in buffer (larger or equal to decoded PNG line)
// Returns NULL if everything looks fine, or an error message
DLL_PUBLIC const char* png_peek(const storage_manager& src, Raster& raster);
DLL_PUBLIC const char* png_stride_decode(codec_params& params, storage_manager& src, void* buffer, int &ct, png_colorp &palette, png_bytep &trans, int &num_trans);
DLL_PUBLIC const char* png_encode(png_params& params, storage_manager& src, storage_manager& dst, png_colorp &palette, png_bytep &trans, int &num_trans);

// In LERC_codec.cpp
DLL_PUBLIC const char* lerc_peek(const storage_manager& src, Raster& raster);
DLL_PUBLIC const char* lerc_stride_decode(codec_params& params, storage_manager& src, void* buffer);
DLL_PUBLIC const char* lerc_encode(lerc_params& params, storage_manager& src, storage_manager& dst);

NS_END
#endif