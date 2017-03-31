/*
* mod_mrf header file
* Lucian Plesea
* (C) 2016
*/

#if !defined(MOD_MRF_H)
#include <httpd.h>
#include <http_config.h>
#include <http_main.h>
#include <http_protocol.h>
#include <http_core.h>
#include <http_request.h>
#include <http_log.h>
#include <cctype>

#include <apr_strings.h>

#define APR_WANT_STRFUNC
#define APR_WANT_MEMFUNC
#include <apr_want.h>

#define CMD_FUNC (cmd_func)

// The maximum size of a tile, to avoid MRF corruption errors
#define MAX_TILE_SIZE 4*1024*1024

// signatures in big endian, to autodetect tile type
#define PNG_SIG 0x89504e47
#define JPEG_SIG 0xffd8ffe0
#define LERC_SIG 0x436e745a

// This one is not a type, just an encoding
#define GZIP_SIG 0x436e745a

// Conversion to and from network order, endianess depenent

#if (APR_IS_BIGENDIAN == 0) // Little endian
#if defined(WIN32) // Windows
#define ntoh32(v) _byteswap_ulong(v)
#define hton32(v) _byteswap_ulong(v)
#define ntoh64(v) _byteswap_uint64(v)
#define hton64(v) _byteswap_uint64(v)
#else // Assume linux
#define ntoh32(v) __builtin_bswap32(v)
#define hton32(v) __builtin_bswap32(v)
#define ntoh64(v) __builtin_bswap64(v)
#define hton64(v) __builtin_bswap64(v)
#endif
#else // Big endian, do nothing
#define ntoh32(v)  (v)
#define ntoh64(v)  (v)
#define hton32(v)  (v)
#define hton64(v)  (v)
#endif

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(mrf);
#endif

typedef struct {
    // array of guard regexp, one of them has to match
    apr_array_header_t *regexp;

    // Turns the module functionality off
    int enabled;

    // The internal redirect path or null
    char *redirect;

    // This determines the endpoint that MRF requests will be sent to
    const char *mrf_endpoint;

    // Table to store all the time periods
    apr_array_header_t *time_periods;

    // A regexp to catch queries that we return as JSON datetime strings. It not present the service is disabled.
    ap_regex_t *datetime_service_regexp;

    // strftime format to be used to form layer names.
    const char *layer_name_format;

} time_snap_conf;

extern module AP_MODULE_DECLARE_DATA time_handler_module;

#endif
