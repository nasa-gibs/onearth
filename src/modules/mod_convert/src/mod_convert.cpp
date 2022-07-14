/*
* mod_convert.cpp
*
* Part of AHTSE, converts from one image format to another
*
* (C) Lucian Plesea 2018-2020
*/

#include <ahtse.h>
#include <http_main.h>
#include <http_protocol.h>
#include <http_core.h>
#include <http_request.h>
#include <http_log.h>
#include <apr_strings.h>
#include <png.h>
#include <receive_context.h>

NS_AHTSE_USE
NS_ICD_USE

extern module AP_MODULE_DECLARE_DATA convert_module;
#define USER_AGENT "AHTSE Convert"

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(convert);
#endif

struct convert_conf {
    // array of guard regexp pointers, one of them has to match
    apr_array_header_t *arr_rxp;

    TiledRaster raster, inraster;

    // internal path of source
    char *source;
    // append this to the end of request url to the input
    char *suffix;

    // the maximum size of an input tile
    apr_size_t max_input_size;

    // Table of doubles.
    // Three values per point, except for the last one
    // inputs, output, slope
    // Input values are in increasing order
    apr_array_header_t *lut;

    // Meaning depends on output format
    double quality;

    // Set if this module is to be used from indirect (not external) requests?
    int indirect;
};

using namespace std;

// Converstion of src from TFrom to TTo, as required by the configuration
template<typename TFrom, typename TTo> static void 
    conv_dt(const convert_conf *cfg, TFrom *src, TTo *dst)
{
    // Assume compact buffers, allocated with the right values
    int count = static_cast<int>(cfg->inraster.pagesize.x 
        * cfg->inraster.pagesize.y * cfg->inraster.pagesize.c);
    const apr_array_header_t *arr = cfg->lut;
    while (count--) {
        double in_val = *src++;
        int i = 0;

        // Find the segment that contains in_val, or use last point
        while (in_val > APR_ARRAY_IDX(arr, i, double) 
            && arr->nelts > i + 3 
            && in_val >= APR_ARRAY_IDX(arr, i + 3, double))
            i += 3;

        const double segment = in_val - APR_ARRAY_IDX(arr, i, double);
        const double offset = APR_ARRAY_IDX(arr, i + 1, double);

        // A shortcut, when the input value matches the point
        if (segment <= 0) {
            *dst++ = static_cast<TTo>(offset);
            continue;
        }

        const double slope = APR_ARRAY_IDX(arr, i + 2, double);
        // No over/under flow checks
        *dst++ = static_cast<TTo>(offset + segment * slope);
    }
}

// Convert src as required by the configuration
// returns pointer to where the output is, could be different from source
// Returns nullptr in case of errors
// cfg->lut is always valid
static void *convert_dt(const convert_conf *cfg, void *src) {
    // Partial implementation
    void *result = nullptr; // Assume error, set result to non-null otherwise

// In place conversions, with LUT, when the output type is <= input type
#define CONV(T_src, T_dst) conv_dt(cfg, reinterpret_cast<T_src *>(src), reinterpret_cast<T_dst *>(src)); result = src; break;

    switch (cfg->inraster.dt) {
    case ICDT_Int32:
        switch (cfg->raster.dt) {
        case ICDT_Float: CONV(int32_t, float);
        case ICDT_UInt32: CONV(int32_t, uint32_t);
        case ICDT_Int32: CONV(int32_t, int32_t);
        case ICDT_UInt16: CONV(int32_t, uint16_t);
        case ICDT_Int16: CONV(int32_t, int16_t);
        case ICDT_Byte: CONV(int32_t, uint8_t);
        default:;
        }
        break;
    case ICDT_UInt32:
        switch (cfg->raster.dt) {
        case ICDT_Float: CONV(uint32_t, float);
        case ICDT_UInt32: CONV(uint32_t, uint32_t);
        case ICDT_Int32: CONV(uint32_t, int32_t);
        case ICDT_UInt16: CONV(uint32_t, uint16_t);
        case ICDT_Int16: CONV(uint32_t, int16_t);
        case ICDT_Byte: CONV(uint32_t, uint8_t);
        default:;
        }
        break;
    case ICDT_Int16:
        switch (cfg->raster.dt) {
        case ICDT_UInt16: CONV(int16_t, uint16_t);
        case ICDT_Int16: CONV(int16_t, int16_t);
        case ICDT_Byte: CONV(int16_t, uint8_t);
        default:;
        }
        break;
    case ICDT_UInt16:
        switch (cfg->raster.dt) {
        case ICDT_UInt16: CONV(uint16_t, uint16_t);
        case ICDT_Int16: CONV(uint16_t, int16_t);
        case ICDT_Byte: CONV(uint16_t, uint8_t);
        default:;
        }
        break;
    case ICDT_Byte:
        switch (cfg->raster.dt) {
        case ICDT_Byte: CONV(uint8_t, uint8_t);
        default:;
        }
        break;
    case ICDT_Float:
        switch (cfg->raster.dt) {
        case ICDT_Float: CONV(float, float);
        case ICDT_UInt32: CONV(float, uint32_t);
        case ICDT_Int32: CONV(float, int32_t);
        case ICDT_UInt16: CONV(float, uint16_t);
        case ICDT_Int16: CONV(float, int16_t);
        case ICDT_Byte: CONV(float, uint8_t);
        default:;
        }
    default:;
    }

#undef CONV

    // If the conversion wasn't done, it can't be done in place
    // TODO: allocate a destinaton buffer and do the conversion to that buffer
    if (result == nullptr) {
    }

    return result;
}

static const char *find_and_replace_string(apr_pool_t *p, const char *search_str, const char *source_str, const char *replacement_str) {
    if (const char *replacefield = ap_strstr(source_str, search_str)) {
        const char *prefix = apr_pstrmemdup(p, source_str, replacefield - source_str);
        return apr_pstrcat(p, prefix, replacement_str, replacefield + strlen(search_str), NULL);
    }
    return source_str;
}

static int handler(request_rec *r)
{
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Start convert");
    const char *message;
    if (r->method_number != M_GET)
        return DECLINED;
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Starting convert");

    convert_conf *cfg = (convert_conf *)ap_get_module_config(r->per_dir_config, &convert_module);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Config source: %s", cfg->source);

    // If indirect is set, only activate on subrequests
    if (cfg->indirect && r->main == nullptr)
        return DECLINED;
    if (!cfg || !cfg->arr_rxp || !requestMatches(r, cfg->arr_rxp)){
        ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Request %s doesn't match regex %s",r->uri, cfg->arr_rxp);
        return DECLINED;
    }
    apr_array_header_t *tokens = tokenize(r->pool, r->uri);
    if (tokens->nelts < 3) {
        ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Failed tokenize");
        return DECLINED; // At least three values, for RLC
    }
    // This is a request to be handled here
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Not Declined");
    // server configuration error ?
    SERVER_ERR_IF(!ap_get_output_filter_handle("Receive"),
        r, "mod_receive not found");

    sz5 tile;
    memset(&tile, 0, sizeof(tile));

    tile.x = apr_atoi64(ARRAY_POP(tokens, char *)); RETURN_ERR_IF(errno);
    tile.y = apr_atoi64(ARRAY_POP(tokens, char *)); RETURN_ERR_IF(errno);
    tile.l = apr_atoi64(ARRAY_POP(tokens, char *)); RETURN_ERR_IF(errno);

    const char *datetime_str;
    datetime_str = r->prev ? apr_table_get(r->prev->notes, "mod_wmts_wrapper_date") : "default";
    // Ignore the error on the M, it defaults to zero
    if (cfg->raster.size.z != 1 && tokens->nelts > 0)
        tile.z = apr_atoi64(ARRAY_POP(tokens, char *));

    // But we still need to check the results
    if (tile.x < 0 || tile.y < 0 || tile.l < 0)
        return sendEmptyTile(r, cfg->raster.missing);

    // Adjust the level to the full pyramid one
    tile.l += cfg->raster.skip;

    // Outside of bounds tile
    if (tile.l >= cfg->raster.n_levels ||
        tile.x >= cfg->raster.rsets[tile.l].w ||
        tile.y >= cfg->raster.rsets[tile.l].h)
        return sendEmptyTile(r, cfg->raster.missing);

    // Same is true for outside of input bounds
    if (tile.l >= cfg->inraster.n_levels ||
        tile.x >= cfg->inraster.rsets[tile.l].w ||
        tile.y >= cfg->inraster.rsets[tile.l].h)
        return sendEmptyTile(r, cfg->raster.missing);

     // Convert to true input level
    tile.l -= cfg->inraster.skip;

    // Create the subrequest

    const char* user_agent = apr_table_get(r->headers_in, "User-Agent");
    user_agent = (nullptr == user_agent) ?
        USER_AGENT : apr_pstrcat(r->pool, USER_AGENT ", ", user_agent, NULL);
    char* sub_uri = tile_url(r->pool, cfg->source, tile, cfg->suffix);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Before replace %s", sub_uri);
    sub_uri = (char *)find_and_replace_string(r->pool, "${date}", sub_uri, datetime_str);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "After replace %s", sub_uri);

    receive_ctx rctx;
    rctx.maxsize = cfg->max_input_size;
    rctx.buffer = (char *)apr_palloc(r->pool, rctx.maxsize);
    ap_filter_t *rf = ap_add_output_filter("Receive", &rctx, r, r->connection);    
    uint64_t evalue = 0;
    int missing = 0;

    request_rec *rr = ap_sub_req_lookup_uri(sub_uri, r, r->output_filters);
    rctx.size = 0; // Reset the receive size
    int rr_status = ap_run_sub_req(rr); // This returns http status, aka 404, 200

    // input ETag, if any, before destroying subrequest
    const char *intag = apr_table_get(rr->headers_out, "ETag");
    if (intag)
        evalue = base32decode(intag, &missing);
    // Build an etag from raw content, if it's large enough
    if (!evalue && rctx.size > 128) {
        evalue = *(reinterpret_cast<uint64_t*>(rctx.buffer) + 4);
        evalue |= *(reinterpret_cast<uint64_t*>(rctx.buffer) + rctx.size / 8 - 4);
        evalue ^= *(reinterpret_cast<uint64_t*>(rctx.buffer) + rctx.size / 8 - 6);
    }

    char etagsrc[14] = { 0 };
    tobase32(evalue, etagsrc, missing);

    if (rr_status != APR_SUCCESS) {
        LOGNOTE(r, "Receive failed with code %d for %s", rr_status, sub_uri);
        return HTTP_NOT_FOUND == rr_status ? sendEmptyTile(r, cfg->raster.missing) : rr_status;
    }

    // Etag is not modified, just passes through
    // remember to set the output etag later
    if (etagMatches(r, etagsrc)) {
        apr_table_set(r->headers_out, "ETag", etagsrc);
        return HTTP_NOT_MODIFIED;
    }

    // If the input tile is the empty tile, send the output empty tile right now

    base32decode(etagsrc, &missing);
    if (missing && etagsrc == cfg->inraster.missing.eTag)
        return sendEmptyTile(r, cfg->raster.missing);

    codec_params params(cfg->inraster);
    // Expected input raster is a single tile
    params.raster.size = cfg->inraster.pagesize;
    params.reset();
    storage_manager raw;
    raw.size = static_cast<int>(params.get_buffer_size());
    raw.buffer = reinterpret_cast<char *>(apr_palloc(r->pool, raw.size));
    SERVER_ERR_IF(raw.buffer == nullptr, r, "Memmory allocation error");
    
    int ct;
    png_colorp png_palette;
    png_bytep png_trans;
    png_palette = (png_colorp)apr_pcalloc(r->pool, 256 * sizeof(png_color));
    png_trans = (png_bytep)apr_pcalloc(r->pool, 256 * sizeof(unsigned char));
    int num_trans;

    storage_manager src = { rctx.buffer, rctx.size };
    // Accept any input format
    LOGNOTE(r, "Decoding");
    message = stride_decode(params, src, raw.buffer, ct, png_palette, png_trans, num_trans);
    LOGNOTE(r, "Decoding returned %s", message);

    ap_destroy_sub_req(rr);
    ap_remove_output_filter(rf);
    if (message) {
        ap_log_rerror(APLOG_MARK, APLOG_WARNING, 0, r, "%s from %s", message, sub_uri);
        ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "raster type is %d size %d", 
            static_cast<int>(cfg->inraster.dt), static_cast<int>(params.get_buffer_size()));
        return HTTP_NOT_FOUND;
    }

    // LUT presence implies a data conversion, otherwise the source is ready
    void* buffer = raw.buffer;
    if (cfg->lut) {
        buffer = convert_dt(cfg, buffer);
        SERVER_ERR_IF(buffer == nullptr, r, "Conversion error, likely not implemented");
        raw.buffer = reinterpret_cast<char *>(buffer);
        params.modified = 1;
    }

    // This part is only for converting Zen JPEGs to JPNG, as needed
    if (IMG_JPEG == params.raster.format && params.modified == 0) {
        // Zen mask absent or superfluous, just send the input
        apr_table_set(r->headers_out, "ETag", etagsrc);
        return sendImage(r, src, "image/jpeg");
    }

    // Space for the output image
    storage_manager dst(apr_palloc(r->pool, cfg->max_input_size), cfg->max_input_size);
    SERVER_ERR_IF(dst.buffer == nullptr, r, "Memmory allocation error");
    // output mime type
    const char* out_mime = "image/jpeg"; // Default

    switch (cfg->raster.format) {
    case IMG_ANY:
    case IMG_JPEG:
        // TODO: Something here
    case IMG_PNG: {
        png_params out_params(cfg->raster);
        out_params.raster.size = cfg->raster.pagesize;
        out_params.reset();

        // By default the NDV is zero, and the NVD field is zero
        // Check one more time that we had a Zen mask before turning the transparency on
        if (params.modified)
            out_params.has_transparency = true;

        message = png_encode(out_params, raw, dst, png_palette, png_trans, num_trans);
        SERVER_ERR_IF(message != nullptr, r, "PNG encoding error: %s from %s", message, r->uri);
        out_mime = "image/png";
        break;
    }
    case IMG_LERC: {
        lerc_params out_params(cfg->raster);

        message = lerc_encode(out_params, raw, dst);
        SERVER_ERR_IF(message != nullptr, r, "%s from %s", message, r->uri);
        out_mime = "raster/lerc";
        break;
    }
    default:
        SERVER_ERR_IF(true, r, "Output format not implemented, from %s", r->uri);
    }

    apr_table_set(r->headers_out, "ETag", etagsrc);
    return sendImage(r, dst, out_mime);
}

// Reads a sequence of in:out floating point pairs, separated by commas.
// Input values should be in increasing order
// Might need "C" locale
static const char *read_lut(cmd_parms *cmd, convert_conf *c, const char *lut, int isint = true) {
    char *lut_string = apr_pstrdup(cmd->temp_pool, lut);
    char *last = nullptr;
    char *token = apr_strtok(lut_string, ",", &last);

    if (c->lut != nullptr)
        return "LUT redefined";

    // Start with sufficient space for 4 points
    apr_array_header_t *arr = apr_array_make(cmd->pool, 12, sizeof(double));

    char *sep=nullptr;
    // Use 0.5 bias for integer output types
    double bias = isint ? 0.5 : 0;
    while (token != nullptr) {
        double value_in = strtod(token, &sep);
        if (*sep++ != ':')
            return apr_psprintf(cmd->temp_pool, "Error in LUT token %s", token);
        if (arr->nelts > 1 && APR_ARRAY_IDX(arr, arr->nelts - 2, double) >= value_in)
            return "Incorrect LUT, input values should be increasing";

        double value_out = strtod(sep, &sep) + bias;
        if (*sep != 0)
            return apr_psprintf(cmd->temp_pool, 
                "Extra characters in LUT token %s", token);

        if (arr->nelts > 1) { // Fill in slope for the previous pair
            double slope =
                (value_out - APR_ARRAY_IDX(arr, arr->nelts - 1, double))
                / (value_in - APR_ARRAY_IDX(arr, arr->nelts - 2, double));
            APR_ARRAY_PUSH(arr, double) = slope;
        }

        APR_ARRAY_PUSH(arr, double) = value_in;
        APR_ARRAY_PUSH(arr, double) = value_out;
        token = apr_strtok(NULL, ",", &last);
    }
    // Push a zero for the last slope value, it will keep output values from overflowing
    APR_ARRAY_PUSH(arr, double) = 0.0;
    c->lut = arr;
    return nullptr;
}

static const char *read_config(cmd_parms *cmd, convert_conf *c, const char *src, const char *conf_name) {
    const char *err_message;
    const char *line; // temporary input
    // The input configuration file
    apr_table_t *kvp = readAHTSEConfig(cmd->temp_pool, src, &err_message);
    if (nullptr == kvp)
        return err_message;
    err_message = configRaster(cmd->pool, kvp, c->inraster);
    if (err_message)
        return err_message;

    // The output configuration file
    kvp = readAHTSEConfig(cmd->temp_pool, conf_name, &err_message);
    if (nullptr == kvp)
        return err_message;
    err_message = configRaster(cmd->pool, kvp, c->raster);
    if (err_message)
        return err_message;

    line = apr_table_get(kvp, "EmptyTile");
    if (nullptr != line) {
        err_message = readFile(cmd->pool, c->raster.missing.data, line);
        if (err_message)
            return err_message;
    }

    c->max_input_size = MAX_TILE_SIZE;
    line = apr_table_get(kvp, "InputBufferSize");
    if (line)
        c->max_input_size = static_cast<apr_size_t>(apr_strtoi64(line, nullptr, 0));

    // Single band, comma separated in:out value pairs
    if (nullptr != (line = apr_table_get(kvp, "LUT")) &&
        (err_message = read_lut(cmd, c, line, c->raster.dt < ICDT_Float32)))
        return err_message;

    if (c->raster.dt != c->inraster.dt && c->lut == nullptr)
        return "Data type conversion without LUT defined";

    return nullptr;
}

static const command_rec cmds[] =
{
    AP_INIT_TAKE2(
        "Convert_ConfigurationFiles",
        (cmd_func) read_config, // Callback
        0, // user_data
        ACCESS_CONF, // availability
        "Source and output configuration files"
    ),

    AP_INIT_TAKE1(
        "Convert_RegExp",
        (cmd_func) set_regexp<convert_conf>,
        0, // user_data
        ACCESS_CONF, // availability
        "Regular expression for triggering mod_convert"
    ),

    AP_INIT_TAKE12(
        "Convert_Source",
        (cmd_func) set_source<convert_conf>,
        0,
        ACCESS_CONF,
        "Required, internal redirect path for the source"
    ),

    AP_INIT_FLAG(
        "Convert_Indirect",
        (cmd_func) ap_set_flag_slot,
        (void *)APR_OFFSETOF(convert_conf, indirect),
        ACCESS_CONF,
        "If set, the module does not respond to external requests, only to internal redirects"
    ),

    { NULL }
};

static void register_hooks(apr_pool_t *p) {
    ap_hook_handler(handler, nullptr, nullptr, APR_HOOK_MIDDLE);
}

module AP_MODULE_DECLARE_DATA convert_module = {
    STANDARD20_MODULE_STUFF,
    pcreate< convert_conf>,
    NULL, // dir merge
    NULL, // server config
    NULL, // server merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
