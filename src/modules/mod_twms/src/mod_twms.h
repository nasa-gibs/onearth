/*
 * mod_twms header file
 * Lucian Plesea
 * (C) 2016
 */

#if !defined(MOD_TWMS_H)
#define MOD_TWMS_H

#include <httpd.h>
#include <http_config.h>
#include <http_main.h>
#include <http_protocol.h>
#include <http_core.h>
#include <http_request.h>
#include <http_log.h>
#include <apr_strings.h>

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(twms);
#endif

// Copied and modified from GDAL, probably not a great idea
// Only 1,2,4 int types and 4 and 8 floating point types are supported
/*! Pixel data types */
typedef enum {
    /*! Unknown or unspecified type */ 		GDT_Unknown = 0,
    /*! Eight bit unsigned integer */           GDT_Byte = 1,
    GDT_Char = 1,
    /*! Sixteen bit unsigned integer */         GDT_UInt16 = 2,
    /*! Sixteen bit signed integer */           GDT_Int16 = 3,
    GDT_Short = 3,
    /*! Thirty two bit unsigned integer */      GDT_UInt32 = 4,
    /*! Thirty two bit signed integer */        GDT_Int32 = 5,
    GDT_Int = 5,
    /*! Thirty two bit floating point */        GDT_Float32 = 6,
    GDT_Float = 6,
    /*! Sixty four bit floating point */        GDT_Float64 = 7,
    GDT_Double = 7,
    /*! Complex Int16 */                        GDT_CInt16 = 8,
    /*! Complex Int32 */                        GDT_CInt32 = 9,
    /*! Complex Float32 */                      GDT_CFloat32 = 10,
    /*! Complex Float64 */                      GDT_CFloat64 = 11,
    GDT_TypeCount = 12          /* maximum type # + 1 */
} GDALDataType;

//
// How many bytes in each type, keep in sync with the numbers above
// Could use C++11 uniform initializers
//
const int dt_size[GDT_TypeCount] = { -1, 1, 2, 2, 4, 4, 4, 4, 4, 8, 8, 16 };

#define DT_SIZE(T) dt_size[T]

// Given a data type name, returns a data type
static GDALDataType GetDT(const char *name) {
    if (name == NULL) return GDT_Byte;
    if (!apr_strnatcasecmp(name, "UINT16"))
        return GDT_UInt16;
    else if (!apr_strnatcasecmp(name, "INT16") || !apr_strnatcasecmp(name, "INT"))
        return GDT_Int16;
    else if (!apr_strnatcasecmp(name, "UINT32"))
        return GDT_UInt32;
    else if (!apr_strnatcasecmp(name, "INT32") || !apr_strnatcasecmp(name, "INT"))
        return GDT_Int32;
    else if (!apr_strnatcasecmp(name, "FLOAT32") || !apr_strnatcasecmp(name, "FLOAT"))
        return GDT_Float32;
    else if (!apr_strnatcasecmp(name, "FLOAT64") || !apr_strnatcasecmp(name, "DOUBLE"))
        return GDT_Float64;
    else
        return GDT_Byte;
}

// Separate channels and level, just in case
struct sz {
    apr_int64_t x, y, z, c, l;
};

struct bbox_t {
    double xmin, ymin, xmax, ymax;
};

struct rset {
    double rx, ry;     // Resolution in units per pixel
    int width, height; // In tiles
};

struct TiledRaster {
    // Size and pagesize of the raster
    struct sz size, pagesize;
    // width and height for each pyramid level
    struct rset *rsets;
    // how many levels from full size, computed
    int n_levels;
    // How many levels to skip at the top of the pyramid
    int skip;
    int datatype;

    // geographical projection
    const char *projection;
    bbox_t bbox;
};

struct twms_conf {
    // The disk path for this configuration
    const char *doc_path;

    // Path for redirect
    const char *source, *postfix;

    // array of guard regexp, one of them has to match
    apr_array_header_t *arr_rxp;

    // The output and input raster figures
    TiledRaster raster;

    const char *cfg_filename_template;

    int enabled;
};

extern module AP_MODULE_DECLARE_DATA twms_module;

#endif
