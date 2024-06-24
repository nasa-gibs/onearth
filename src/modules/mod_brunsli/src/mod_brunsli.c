/*
 * mod_brunsli
 * An apache httpd brunsli-jpeg convertor filter
 * 
 */

#define APR_WANT_STRFUNC
#define APR_WANT_MEMFUNC
#include <apr_want.h>

#include <httpd.h>
#include <http_core.h>
#include <http_log.h>
#include <http_protocol.h>

#include <brunsli/decode.h>
#include <brunsli/encode.h>

// Maximum size of input, output may be larger
#define MAX_SZ 1024*1024
// Mime type to use for brunsli
static const char BRUNSLI_MIME_TYPE[] = "image/x-j";

APLOG_USE_MODULE(brunsli);

// Callback function for both encoding and decoding
static size_t out_fun(void* pbb, const uint8_t* data, size_t size) {
    apr_bucket_brigade* bb = (apr_bucket_brigade*)(pbb);
    APR_BRIGADE_INSERT_TAIL(bb,
        apr_bucket_heap_create((const char *)data, size, NULL, bb->bucket_alloc));
    return size;
}

//
//  Only for use in the debugger, to inspect a table
// Place breakpoint here and call: inspect_table(f->r->headers_out)
//
#if defined(_DEBUG)
static void inspect_table(apr_table_t * tbl) {
    const apr_array_header_t * pthdr = apr_table_elts(tbl);
    for (int i = 0; i < pthdr->nelts; i++) {
        apr_table_entry_t val = APR_ARRAY_IDX(pthdr, i, apr_table_entry_t);
        const char * key = val.key;
    }
}
#endif

static apr_status_t benc_filter(ap_filter_t* f, apr_bucket_brigade* bb)
{
    char* buff;
    apr_size_t bytes;
    apr_bucket* first = APR_BRIGADE_FIRST(bb);
    if (!first) return APR_SUCCESS; // empty brigade
    int state = apr_bucket_read(first, (const char **)&buff, &bytes, APR_BLOCK_READ);
    static const char JPEG_SIG[] = {0xff, 0xd8, 0xff, 0xe0};
    static const char JPEG1_SIG[] = {0xff, 0xd8, 0xff, 0xe1};
    if (APR_SUCCESS != state || bytes < 4 ||
        (memcmp(buff, JPEG_SIG, sizeof(JPEG_SIG)) && memcmp(buff, JPEG1_SIG, sizeof(JPEG_SIG)))) 
    {
        ap_remove_output_filter(f);
        return ap_pass_brigade(f->next, bb);
    }

    // Look like jpeg content
    apr_off_t len;
    state = apr_brigade_length(bb, 1, &len);
    if (APR_SUCCESS != state || len < 0 || len > MAX_SZ) {
        ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, f->r, "Can't read jpeg input");
        ap_remove_output_filter(f);
        return ap_pass_brigade(f->next, bb);
    }

    if (len == bytes) { // Single bucket
        APR_BUCKET_REMOVE(first);
    }
    else {
        apr_brigade_pflatten(bb, &buff, &bytes, f->r->pool);
        first = NULL;
    }
    apr_brigade_cleanup(bb); // Reuse brigade

//    inspect_table(f->r->headers_out);
//    const char *ETG = apr_table_get(f->r->headers_out, "ETag");
    apr_table_unset(f->r->headers_out, "Content-Length");
    apr_table_unset(f->r->headers_out, "Content-Type");
    if (!EncodeBrunsli((size_t)len, (const unsigned char *)buff, bb, out_fun)) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, f->r, "Encoding error, possibly input is not supported");
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    if (first)
        apr_bucket_free(first);
    APR_BRIGADE_INSERT_TAIL(bb, apr_bucket_eos_create(f->c->bucket_alloc));
    state = apr_brigade_length(bb, 1, &len);
    // something is really wrong if the call above fails
    if (APR_SUCCESS == state) {
        ap_set_content_type(f->r, BRUNSLI_MIME_TYPE);
        ap_set_content_length(f->r, len);
    }
    else {
        ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, f->r, "Error getting size of brunsli output");
    }
    return ap_pass_brigade(f->next, bb);
}

static apr_status_t bdec_filter(ap_filter_t* f, apr_bucket_brigade* bb)
{
    // Read some data, look for brunsli signature
    char* buff;
    apr_size_t bytes;
    apr_bucket* first = APR_BRIGADE_FIRST(bb);
    if (!first) return APR_SUCCESS; // empty brigade
    int state = apr_bucket_read(first, (const char **)&buff, &bytes, APR_BLOCK_READ);
    static const char SIG[] = { 0x0a, 0x04, 0x42, 0xd2, 0xd5, 0x4e };
    if (APR_SUCCESS != state || bytes < 6 || memcmp(buff, SIG, sizeof(SIG))) {
        ap_remove_output_filter(f);
        return ap_pass_brigade(f->next, bb);
    }

//    inspect_table(f->r->headers_out);

    // Looks like brunsli content, is is small enough
    apr_off_t len;
    //  Returns -1 if it fails
    state = apr_brigade_length(bb, 1, &len);
//    const char tg = apr_table_get(f->r->headers_out, "ETag");
    if (APR_SUCCESS != state || len > MAX_SZ || len < 0) {
        ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, f->r, "Can't read brunsli input or input too large");
        ap_remove_output_filter(f);
        return ap_pass_brigade(f->next, bb);
    }

    // Avoid making a copy if the whole input is in the first bucket
    // buff is already set up
    if (len == bytes) {
        APR_BUCKET_REMOVE(first); // Keep this buffer when cleaning up the brigade
    }
    else {
        apr_brigade_pflatten(bb, &buff, &bytes, f->r->pool);
        first = NULL;
    }
    apr_brigade_cleanup(bb); // Reuse the brigade

    if (!DecodeBrunsli(len, (const unsigned char *)buff, bb, out_fun)) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, f->r, "Decoding error");
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    if (first) // Free the input bucket if we saved it until now
        apr_bucket_free(first);
    APR_BRIGADE_INSERT_TAIL(bb, apr_bucket_eos_create(f->c->bucket_alloc));
    apr_table_unset(f->r->headers_out, "Content-Length");
    apr_table_unset(f->r->headers_out, "Content-Type");
    state = apr_brigade_length(bb, 1, &len);
    // something is really wrong if that call fails
    if (APR_SUCCESS == state) {
        ap_set_content_type(f->r, "image/jpeg");
        ap_set_content_length(f->r, len);
    }
    return ap_pass_brigade(f->next, bb);
}

static const command_rec cmds[] = {
    {NULL}
};

static const char CBName[] = "CBRUNSLI";
static const char DBName[] = "DBRUNSLI";

#define DEC_PROTO_FLAGS  AP_FILTER_PROTO_CHANGE | AP_FILTER_PROTO_CHANGE_LENGTH | AP_FILTER_PROTO_NO_BYTERANGE

static void register_hooks(apr_pool_t *p) {
    ap_register_output_filter_protocol(DBName, bdec_filter, NULL, AP_FTYPE_CONTENT_SET, DEC_PROTO_FLAGS);
    ap_register_output_filter_protocol(CBName, benc_filter, NULL, AP_FTYPE_CONTENT_SET, DEC_PROTO_FLAGS);
}

module AP_MODULE_DECLARE_DATA brunsli_module = {
    STANDARD20_MODULE_STUFF,
    0,
    0,
    0,
    0,
    cmds,
    register_hooks
};