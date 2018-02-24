/*
 * mod_reproject.cpp
 * An AHTSE tile to tile conversion module, should do most of the functionality required by a WMS server
 * Uses a 3-4 paramter rest tile service as a data source
 *
 * (C) Lucian Plesea 2016-2017
 */

// TODO: Test
// TODO: Handle ETag conditional requests
// TODO: Add LERC support
// TODO: Allow overlap between tiles

#include "mod_reproject.h"
#include <cmath>
#include <clocale>
#include <vector>
#include <cctype>

extern module AP_MODULE_DECLARE_DATA reproject_module;

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(reproject);
#endif

// From mod_receive
#include <receive_context.h>

using namespace std;

// Rather than use the _USE_MATH_DEFINES, just calculate pi once, C++ style
const static double pi = acos(-1.0);

#define USER_AGENT "AHTSE Reproject"

// A structure for the coordinate information used in the current tile conversion
struct work {
    repro_conf *c;
    // Output bbox
    bbox_t out_bbox;
    // Output bbox in input projection
    bbox_t out_equiv_bbox;
    // Input bounding box
    bbox_t in_bbox;
    // Output tile
    sz out_tile;
    // Input tile range
    sz tl, br;
    // Numerical ETag
    apr_uint64_t seed;
    int in_level;
};

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

static int send_image(request_rec *r, const storage_manager &src, const char *mime_type = NULL)
{
    if (mime_type)
        ap_set_content_type(r, mime_type);
    else
        switch (hton32(*src.buffer)) {
        case JPEG_SIG:
            ap_set_content_type(r, "image/jpeg");
            break;
        case PNG_SIG:
            ap_set_content_type(r, "image/png");
            break;
        default: // LERC goes here too
            ap_set_content_type(r, "application/octet-stream");
    }
    // Is it gzipped content?
    if (GZIP_SIG == hton32(*src.buffer))
        apr_table_setn(r->headers_out, "Content-Encoding", "gzip");

    ap_set_content_length(r, src.size);
    ap_rwrite(src.buffer, src.size, r);
    return OK;
}

// Returns NULL if it worked as expected, returns a four integer value from 
// "x y", "x y z" or "x y z c"
static const char *get_xyzc_size(struct sz *size, const char *value) {
    char *s;
    if (!value)
        return " values missing";
    size->x = apr_strtoi64(value, &s, 0);
    size->y = apr_strtoi64(s, &s, 0);
    size->c = 3;
    size->z = 1;
    if (errno == 0 && *s != 0) {
        // Read optional third and fourth integers
        size->z = apr_strtoi64(s, &s, 0);
        if (*s != 0)
            size->c = apr_strtoi64(s, &s, 0);
    }
    if (errno != 0 || *s != 0) {
        // Raster size is 4 params max
        return " incorrect format";
    }
    return NULL;
}

// Converts a 64bit value into 13 trigesimal chars
static void uint64tobase32(apr_uint64_t value, char *buffer, int flag = 0) {
    static char b32digits[] = "0123456789abcdefghijklmnopqrstuv";
    // First char has the flag bit
    if (flag) flag = 1; // Normalize value
    buffer[0] = b32digits[((value & 0xf) << 1) | flag];
    value >>= 4; // Encoded 4 bits
    // Five bits at a time, 60 bytes
    for (int i = 1; i < 13; i++) {
        buffer[i] = b32digits[value & 0x1f];
        value >>= 5;
    }
    buffer[13] = '\0';
}

// Return the value from a base 32 character
// Returns a negative value if char is not a valid base32 char
// ASCII only
static int b32(char ic) {
    int c = 0xff & (static_cast<int>(ic));
    if (c < '0') return -1;
    if (c - '0' < 10) return c - '0';
    if (c < 'A') return -1;
    if (c - 'A' < 22) return c - 'A' + 10;
    if (c < 'a') return -1;
    if (c - 'a' < 22) return c - 'a' + 10;
    return -1;
}

static apr_uint64_t base32decode(const char *is, int *flag) {
    apr_int64_t value = 0;
    const unsigned char *s = reinterpret_cast<const unsigned char *>(is);
    while (*s == static_cast<unsigned char>('"'))
        s++; // Skip quotes
    *flag = b32(*s) & 1; // Pick up the flag, least bit of top char
    // Initial value ignores the flag
    int digits = 0; // How many base32 digits we've seen
    for (int v = (b32(*s++) >> 1); v >= 0; v = b32(*s++), digits++)
        value = (value << 5) + v;
    // Trailing zeros are missing if digits < 13
    if (digits < 13)
        value <<= 5 * (13 - digits);
    return value;
}

static void *create_dir_config(apr_pool_t *p, char *path)
{
    repro_conf *c = (repro_conf *)apr_pcalloc(p, sizeof(repro_conf));
    c->doc_path = path;
    return c;
}

// Returns a table read from a file, or NULL and an error message
static apr_table_t *read_pKVP_from_file(apr_pool_t *pool, const char *fname, char **err_message)

{
    *err_message = NULL;
    ap_configfile_t *cfg_file;
    apr_status_t s = ap_pcfg_openfile(&cfg_file, pool, fname);

    if (APR_SUCCESS != s) { // %pm means print status error string
        *err_message = apr_psprintf(pool, " %s - %pm", fname, &s);
        return NULL;
    }

    char buffer[MAX_STRING_LEN];
    apr_table_t *table = apr_table_make(pool, 8);
    // This can return ENOSPC if lines are too long
    while (APR_SUCCESS == (s = ap_cfg_getline(buffer, MAX_STRING_LEN, cfg_file))) {
        if ((strlen(buffer) == 0) || buffer[0] == '#')
            continue;
        const char *value = buffer;
        char *key = ap_getword_white(pool, &value);
        apr_table_add(table, key, value);
    }

    ap_cfg_closefile(cfg_file);
    if (s == APR_ENOSPC) {
        *err_message = apr_psprintf(pool, "maximum line length of %d exceeded", MAX_STRING_LEN);
        return NULL;
    }

    return table;
}

static void init_rsets(apr_pool_t *p, struct TiledRaster &raster)
{
    // Clean up pagesize defaults
    raster.pagesize.c = raster.size.c;
    raster.pagesize.z = 1;

    struct rset level;
    level.width = int(1 + (raster.size.x - 1) / raster.pagesize.x);
    level.height = int(1 + (raster.size.y - 1) / raster.pagesize.y);
    level.rx = (raster.bbox.xmax - raster.bbox.xmin) / raster.size.x;
    level.ry = (raster.bbox.ymax - raster.bbox.ymin) / raster.size.y;

    // How many levels do we have
    raster.n_levels = 2 + ilogb(max(level.height, level.width) - 1);
    raster.rsets = (struct rset *)apr_pcalloc(p, sizeof(rset) * raster.n_levels);

    // Populate rsets from the bottom, the way tile protcols count levels
    // These are MRF rsets, not all of them have to be exposed
    struct rset *r = raster.rsets + raster.n_levels - 1;
    for (int i = 0; i < raster.n_levels; i++) {
        *r-- = level;
        // Prepare for the next level, assuming powers of two
        level.width = 1 + (level.width - 1) / 2;
        level.height = 1 + (level.height - 1) / 2;
        level.rx *= 2;
        level.ry *= 2;
    }

    // MRF has one tile at the top
    ap_assert(raster.rsets[0].height == 1 && raster.rsets[0].width == 1);
    ap_assert(raster.n_levels > raster.skip);
}

// Temporary switch locale to C, get four comma separated numbers in a bounding box, WMS style
static const char *getbbox(const char *line, bbox_t *bbox)
{
    const char *lcl = setlocale(LC_NUMERIC, NULL);
    const char *message = " format incorrect, expects four comma separated C locale numbers";
    char *l;
    setlocale(LC_NUMERIC, "C");

    do {
        bbox->xmin = strtod(line, &l); if (*l++ != ',') break;
        bbox->ymin = strtod(l, &l);    if (*l++ != ',') break;
        bbox->xmax = strtod(l, &l);    if (*l++ != ',') break;
        bbox->ymax = strtod(l, &l);
        message = NULL;
    } while (false);

    setlocale(LC_NUMERIC, lcl);
    return message;
}

static const char *ConfigRaster(apr_pool_t *p, apr_table_t *kvp, struct TiledRaster &raster)
{
    const char *line;
    line = apr_table_get(kvp, "Size");
    if (!line)
        return "Size directive is mandatory";
    const char *err_message;
    err_message = get_xyzc_size(&(raster.size), line);
    if (err_message) return apr_pstrcat(p, "Size", err_message, NULL);
    // Optional page size, defaults to 512x512
    raster.pagesize.x = raster.pagesize.y = 512;
    line = apr_table_get(kvp, "PageSize");
    if (line) {
        err_message = get_xyzc_size(&(raster.pagesize), line);
        if (err_message) return apr_pstrcat(p, "PageSize", err_message, NULL);
    }

    // Optional data type, defaults to unsigned byte
    raster.datatype = GetDT(apr_table_get(kvp, "DataType"));

    line = apr_table_get(kvp, "SkippedLevels");
    if (line)
        raster.skip = int(apr_atoi64(line));

    // Default projection is WM, meaning web mercator
    line = apr_table_get(kvp, "Projection");
    raster.projection = line ? apr_pstrdup(p, line) : "WM";

    // Bounding box: minx, miny, maxx, maxy
    raster.bbox.xmin = raster.bbox.ymin = 0.0;
    raster.bbox.xmax = raster.bbox.ymax = 1.0;
    line = apr_table_get(kvp, "BoundingBox");
    if (line)
        err_message = getbbox(line, &raster.bbox);
    if (err_message)
        return apr_pstrcat(p, "BoundingBox", err_message, NULL);

    init_rsets(p, raster);

    return NULL;
}

static char *read_empty_tile(cmd_parms *cmd, repro_conf *c, const char *line)
{
    // If we're provided a file name or a size, pre-read the empty tile in the 
    apr_file_t *efile;
    apr_off_t offset = 0;
    apr_status_t stat;
    char *last;

    c->empty.size = static_cast<int>(apr_strtoi64(line, &last, 0));
    // Might be an offset, or offset then file name
    if (last != line)
        apr_strtoff(&(offset), last, &last, 0);

    while (*last && isblank(*last)) last++;
    const char *efname = last;

    // Use the temp pool for the file open, it will close it for us
    if (!c->empty.size) { // Don't know the size, get it from the file
        apr_finfo_t finfo;
        stat = apr_stat(&finfo, efname, APR_FINFO_CSIZE, cmd->temp_pool);
        if (APR_SUCCESS != stat)
            return apr_psprintf(cmd->pool, "Can't stat %s %pm", efname, &stat);
        c->empty.size = static_cast<int>(finfo.csize);
    }
    stat = apr_file_open(&efile, efname, READ_RIGHTS, 0, cmd->temp_pool);
    if (APR_SUCCESS != stat)
        return apr_psprintf(cmd->pool, "Can't open empty file %s, %pm", efname, &stat);
    c->empty.buffer = static_cast<char *>(apr_palloc(cmd->pool, (apr_size_t)c->empty.size));
    stat = apr_file_seek(efile, APR_SET, &offset);
    if (APR_SUCCESS != stat)
        return apr_psprintf(cmd->pool, "Can't seek empty tile %s: %pm", efname, &stat);
    apr_size_t size = (apr_size_t)c->empty.size;
    stat = apr_file_read(efile, c->empty.buffer, &size);
    if (APR_SUCCESS != stat)
        return apr_psprintf(cmd->pool, "Can't read from %s: %pm", efname, &stat);
    apr_file_close(efile);
    return NULL;
}

// Allow for one or more RegExp guard
// One of them has to match if the request is to be considered
static const char *set_regexp(cmd_parms *cmd, repro_conf *c, const char *pattern)
{
    char *err_message = NULL;
    if (c->arr_rxp == 0)
        c->arr_rxp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t *));
    ap_regex_t **m = (ap_regex_t **)apr_array_push(c->arr_rxp);
    *m = ap_pregcomp(cmd->pool, pattern, 0);
    return (NULL != *m) ? NULL : "Bad regular expression";
}

// Is the projection GCS
static bool is_gcs(const char *projection) {
    return !apr_strnatcasecmp(projection, "GCS")
        || !apr_strnatcasecmp(projection, "WGS84")
        || !apr_strnatcasecmp(projection, "EPSG:4326");
}

// Is the projection spherical mercator, include the Pseudo Mercator code
static bool is_wm(const char *projection) {
    return !apr_strnatcasecmp(projection, "WM")
        || !apr_strnatcasecmp(projection, "EPSG:3857")  // The current code
        || !apr_strnatcasecmp(projection, "EPSG:3785"); // Wrong code
}

static bool is_m(const char *projection) {
    return !apr_strnatcasecmp(projection, "Mercator")
        || !apr_strnatcasecmp(projection, "EPSG:3395");
}

// If projection is the same, the transformation is an affine scaling
#define IS_AFFINE_SCALING(cfg) (!apr_strnatcasecmp(cfg->inraster.projection, cfg->raster.projection))
#define IS_GCS2WM(cfg) (is_gcs(cfg->inraster.projection) && is_wm(cfg->raster.projection))
#define IS_WM2GCS(cfg) (is_wm(cfg->inraster.projection) && is_gcs(cfg->raster.projection))
#define IS_WM2M(cfg) (is_wm(cfg->inraster.projection) && is_m(cfg->raster.projection))

//
// Tokenize a string into an array
//  
static apr_array_header_t* tokenize(apr_pool_t *p, const char *s, char sep = '/')
{
    apr_array_header_t* arr = apr_array_make(p, 10, sizeof(char *));
    while (sep == *s) s++;
    char *val;
    while (*s && (val = ap_getword(p, &s, sep))) {
        char **newelt = (char **)apr_array_push(arr);
        *newelt = val;
    }
    return arr;
}

static int etag_matches(request_rec *r, const char *ETag) {
    const char *ETagIn = apr_table_get(r->headers_in, "If-None-Match");
    return ETagIn != 0 && strstr(ETagIn, ETag);
}

// Returns the empty tile if defined
static int send_empty_tile(request_rec *r) {
    repro_conf *cfg = (repro_conf *)ap_get_module_config(r->per_dir_config, &reproject_module);
    if (etag_matches(r, cfg->eETag)) {
        apr_table_setn(r->headers_out, "ETag", cfg->eETag);
        return HTTP_NOT_MODIFIED;
    }

    if (!cfg->empty.buffer) return DECLINED;
    return send_image(r, cfg->empty);
}

// Returns a bad request error if condition is met
#define REQ_ERR_IF(X) if (X) {\
    return HTTP_BAD_REQUEST; \
}

// If the condition is met, sends the message to the error log and returns HTTP INTERNAL ERROR
#define SERR_IF(X, msg) if (X) { \
    ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, msg);\
    return HTTP_INTERNAL_SERVER_ERROR; \
}

// Pick an input level based on desired output resolution
static int input_level(work &info, double rx, double ry) {
    // The raster levels are in increasing resolution order, test until the best match, both x and y
    int choiceX, choiceY;
    int over = info.c->oversample;

    const TiledRaster &raster = info.c->inraster;
    for (choiceX = 0; choiceX < (raster.n_levels - 1); choiceX++) {
        double cres = raster.rsets[choiceX].rx;
        cres += cres / raster.pagesize.x / 2; // Add half pixel worth to choose matching level
        if (cres < rx) { // This is the better choice
            if (!over) choiceX -= 1; // Use the lower resolution level if not oversampling
            if (choiceX < raster.skip)
                choiceX = raster.skip; // Only use defined levels
            break;
        }
    }

    for (choiceY = 0; choiceY < (raster.n_levels - 1); choiceY++) {
        double cres = raster.rsets[choiceY].ry;
        cres += cres / raster.pagesize.y / 2; // Add half pixel worth to avoid jitter noise
        if (cres < ry) { // This is the best choice
            if (!over) choiceY -= 1; // Use the higher level if oversampling
            if (choiceY < raster.skip)
                choiceY = raster.skip; // Only use defined levels
            break;
        }
    }

    // Pick the higher level number for normal quality
    info.in_level = (choiceX > choiceY) ? choiceX : choiceY;
    // Make choiceX the lower level, to see how far we would be
    if (choiceY < choiceX) choiceX = choiceY;

    // Use min of higher level or low + max extra
    if (info.in_level > choiceX + info.c->max_extra_levels)
        info.in_level = choiceX + info.c->max_extra_levels;

    return info.in_level;
}

// From a tile location, generate a bounding box of a raster
static void tile_to_bbox(const TiledRaster &raster, const sz *tile, bbox_t &bb) {
    double rx = raster.rsets[tile->l].rx;
    double ry = raster.rsets[tile->l].ry;

    // Compute the top left
    bb.xmin = raster.bbox.xmin + tile->x * rx * raster.pagesize.x;
    bb.ymax = raster.bbox.ymax - tile->y * ry * raster.pagesize.y;
    // Adjust for the bottom right
    bb.xmax = bb.xmin + rx * raster.pagesize.x;
    bb.ymin = bb.ymax - ry * raster.pagesize.y;
}

static int ntiles(const sz &tl, const sz &br) {
    return int((br.x - tl.x) * (br.y - tl.y));
}

// From a bounding box, calculate the top-left and bottom-right tiles of a specific level of a raster
// Input level is absolute, the one set in output tiles is relative
static void bbox_to_tile(const TiledRaster &raster, int level, const bbox_t &bb, sz &tl_tile, sz &br_tile) {
    double rx = raster.rsets[level].rx;
    double ry = raster.rsets[level].ry;
    double x = (bb.xmin - raster.bbox.xmin) / (rx * raster.pagesize.x);
    double y = (raster.bbox.ymax - bb.ymax) / (ry * raster.pagesize.y);

    // Truncate is fine for these two, after adding quarter pixel to eliminate jitter
    // X and Y are in pages, so a pixel is 1/pagesize
    tl_tile.x = int(x + 0.25 / raster.pagesize.x);
    tl_tile.y = int(y + 0.25 / raster.pagesize.y);

    x = (bb.xmax - raster.bbox.xmin) / (rx * raster.pagesize.x);
    y = (raster.bbox.ymax - bb.ymin) / (ry * raster.pagesize.y);

    // Pad these quarter pixel to avoid jitter
    br_tile.x = int(x + 0.25 / raster.pagesize.x);
    br_tile.y = int(y + 0.25 / raster.pagesize.y);
    // Use a tile only if we get more than half pixel in
    if (x - br_tile.x > 0.5 / raster.pagesize.x) br_tile.x++;
    if (y - br_tile.y > 0.5 / raster.pagesize.y) br_tile.y++;
}

// Fetches and decodes all tiles between tl and br, writes output in buffer
// aligned as a single raster
// Returns APR_SUCCESS if everything is fine, otherwise an HTTP error code

static apr_status_t retrieve_source(request_rec *r, work &info, void **buffer, int &ct, png_colorp &palette, png_bytep &trans)
{
    const  sz &tl = info.tl, &br = info.br;
    repro_conf *cfg = info.c;
    apr_uint64_t &etag_out = info.seed;
    const char *error_message;

    int nt = ntiles(tl, br);
    // Should have a reasonable number of input tiles, 64 is a good figure
    SERR_IF(nt > 64, "Too many input tiles required, maximum is 64");

    // Allocate a buffer for receiving responses
    receive_ctx rctx;
    rctx.maxsize = cfg->max_input_size;
    rctx.buffer = (char *)apr_palloc(r->pool, rctx.maxsize);

    ap_filter_t *rf = ap_add_output_filter("Receive", &rctx, r, r->connection);

    codec_params params;
    int pixel_size = DT_SIZE(cfg->inraster.datatype);

    // inraster->pagesize.c has to be set correctly
    int input_line_width = int(cfg->inraster.pagesize.x * cfg->inraster.pagesize.c * pixel_size);
    int pagesize = int(input_line_width * cfg->inraster.pagesize.y);

    params.line_stride = int((br.x - tl.x) * input_line_width);

    apr_size_t bufsize = pagesize * nt;
    if (*buffer == NULL) // Allocate the buffer if not provided, filled with zeros
        *buffer = apr_pcalloc(r->pool, bufsize);

    // Retrieve every required tile and decompress it in the right place
    for (int y = int(tl.y); y < br.y; y++) for (int x = int(tl.x); x < br.x; x++) {
        char *sub_uri = apr_pstrcat(r->pool,
            (tl.z == 0) ?
            apr_psprintf(r->pool, "%s/%d/%d/%d", cfg->source, int(tl.l), y, x) :
            apr_psprintf(r->pool, "%s/%d/%d/%d/%d", cfg->source, int(tl.z), int(tl.l), y, x),
            cfg->postfix, NULL);

        request_rec *rr = ap_sub_req_lookup_uri(sub_uri, r, r->output_filters);

        // Location of first byte of this input tile
        void *b = (char *)(*buffer) + pagesize * (y - tl.y) * (br.x - tl.x)
            + input_line_width * (x - tl.x);

        // Set up user agent signature, prepend the info
        const char *user_agent = apr_table_get(r->headers_in, "User-Agent");
        user_agent = user_agent == NULL ? USER_AGENT :
            apr_pstrcat(r->pool, USER_AGENT ", ", user_agent, NULL);
        apr_table_setn(rr->headers_in, "User-Agent", user_agent);

        rctx.size = 0; // Reset the receive size
        int rr_status = ap_run_sub_req(rr);
        if (rr_status != APR_SUCCESS) {
            ap_remove_output_filter(rf);
            ap_log_rerror(APLOG_MARK, APLOG_ERR, rr_status, r, "Receive failed for %s", sub_uri);
            return rr_status; // Pass status along
        }

        const char *ETagIn = apr_table_get(rr->headers_out, "ETag");
        apr_uint64_t etag;
        int empty_flag = 0;
        if (nullptr != ETagIn) {
            etag = base32decode(ETagIn, &empty_flag);
            if (empty_flag) continue; // Ignore empty input tiles
        }
        else { // Input came without an ETag, make one up
            etag = rctx.size; // Start with the input tile size
            // And pick some data out of the input buffer, towards the end
            if (rctx.size > 50) {
                char *tptr = rctx.buffer + rctx.size - 24; // Temporary pointer
                tptr -= reinterpret_cast<apr_uint64_t>(tptr) % 8; // Make it 8 byte aligned
                etag ^= *reinterpret_cast<apr_uint64_t*>(tptr);
                tptr = rctx.buffer + rctx.size - 35; // Temporary pointer
                tptr -= reinterpret_cast<apr_uint64_t>(tptr) % 8; // Make it 8 byte aligned
                etag ^= *reinterpret_cast<apr_uint64_t*>(tptr);
            }
        }
        // Build up the outgoing ETag
        etag_out = (etag_out << 8) | (0xff & (etag_out >> 56)); // Rotate existing tag one byte left
        etag_out ^= etag; // And combine it with the incoming tile etag

        storage_manager src = { rctx.buffer, rctx.size };
        apr_uint32_t sig;
        memcpy(&sig, rctx.buffer, sizeof(sig));

        switch (hton32(sig))
        {
        case JPEG_SIG:
            error_message = jpeg_stride_decode(params, cfg->inraster, src, b);
            break;
        case PNG_SIG:
        	error_message = png_stride_decode(r->pool, params, cfg->inraster, src, b, ct, palette, trans);
            break;
        default:
            error_message = "Unsupported format received";
        }

        if (error_message != NULL) { // Something went wrong
            ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "%s :%s", error_message, sub_uri);
            return HTTP_NOT_FOUND;
        }
    }

    ap_remove_output_filter(rf);
    //    apr_table_clear(r->headers_out); // Clean up the headers set by subrequests

    return APR_SUCCESS;
}

// Interpolation line, contains the above line and the relative weight (never zero)
// These don't have to be bit fields, but it keeps them smaller
// w is weigth of next line *256, can be 0 but not 256.
// line is the higher line to be interpolated, always positive
struct iline {
    unsigned int w : 8, line : 24;
};

// Offset should be Out - In, center of first pixels, real world coordinates
// If this is negative, we got trouble?
static void init_ilines(double delta_in, double delta_out, double offset, iline *itable, int lines)
{
    for (int i = 0; i < lines; i++) {
        double pos = (offset + i * delta_out) / delta_in;
        // The high line
        itable[i].line = static_cast<int>(ceil(pos));
        if (ceil(pos) != floor(pos))
            itable[i].w = static_cast<int>(floor(256.0 * (pos - floor(pos))));
        else // Perfect match with this line
            itable[i].w = 255;
    }
}

// Adjust an interpolation table to avoid addressing unavailable lines
// Max available is the max available line
static void adjust_itable(iline *table, int n, unsigned int max_avail) {
    // Adjust the end first
    while (n && table[--n].line > max_avail) {
        table[n].line = max_avail;
        table[n].w = 255; // Mostly the last available line
    }
    for (int i = 0; i < n && table[i].line <= 0; i++) {
        table[i].line = 1;
        table[i].w = 0; // Use line zero value
    }
}

// A 2D buffer
struct interpolation_buffer {
    void *buffer;       // Location of first value per line
    sz size;            // Describes the organization of the buffer
};


//
// Perform the actual interpolation using ilines, working type WT
//
template<typename T = apr_byte_t, typename WT = apr_int32_t> static void interpolate(
    const interpolation_buffer &src, interpolation_buffer &dst,
    const iline *h, const iline *v)
{
    const int colors = static_cast<int>(dst.size.c);
    ap_assert(src.size.c == colors); // Same number of colors
    T *data = reinterpret_cast<T *>(dst.buffer);
    T *s = reinterpret_cast<T *>(src.buffer);
    const int slw = static_cast<int>(src.size.x * colors);

    // single band optimization
    if (1 == colors) {
        for (int y = 0; y < dst.size.y; y++) {
            const WT vw = v[y].w;
            for (int x = 0; x < dst.size.x; x++)
            {
                const WT hw = h[x].w;
                const int idx = slw * v[y].line + h[x].line; // high left index
                const WT lo = static_cast<WT>(s[idx - slw - 1]) * (256 - hw)
                    + static_cast<WT>(s[idx - slw]) * hw;
                const WT hi = static_cast<WT>(s[idx - 1]) * (256 - hw)
                    + static_cast<WT>(s[idx]) * hw;
                const WT value = hi * vw + lo * (256 - vw);
                *data++ = static_cast<T>(value / (256 * 256));
            }
        }
        return;
    }

    // More than one band
    for (int y = 0; y < dst.size.y; y++) {
        const WT vw = v[y].w;
        for (int x = 0; x < dst.size.x; x++)
        {
            const WT hw = h[x].w;
            int idx = slw * v[y].line + h[x].line * colors; // high left index
            for (int c = 0; c < colors; c++) {
                const WT lo = static_cast<WT>(s[idx + c - slw]) * hw +
                    static_cast<WT>(s[idx + c - slw - colors]) * (256 - hw);
                const WT hi = static_cast<WT>(s[idx + c]) * hw +
                    static_cast<WT>(s[idx + c - colors]) * (256 - hw);
                const WT value = hi * vw + lo * (256 - vw);
                *data++ = static_cast<T>(value / (256 * 256));
            }
        }
    }
}

//
// NearNb sampling, based on ilines
// Uses the weights to pick between two choices
//

template<typename T = apr_byte_t> static void interpolateNN(
    const interpolation_buffer &src, interpolation_buffer &dst,
    const iline *h, const iline *v)
{
    ap_assert(src.size.c == dst.size.c);
    T *data = reinterpret_cast<T *>(dst.buffer);
    T *s = reinterpret_cast<T *>(src.buffer);
    const int colors = static_cast<int>(dst.size.c);

    // Precompute the horizontal pick table, the vertical is only used once
    std::vector<int> hpick(static_cast<unsigned int>(dst.size.x));
    for (int i = 0; i < static_cast<int>(hpick.size()); i++)
        hpick[i] = colors * (h[i].line - ((h[i].w < 128) ? 1 : 0));

    if (colors == 1) { // optimization, only two loops
        for (int y = 0; y < static_cast<int>(dst.size.y); y++) {
            int vidx = static_cast<int>(src.size.x * (v[y].line - ((v[y].w < 128) ? 1 : 0)));
            for (auto const &hid : hpick)
                *data++ = s[vidx + hid];
        }
        return;
    }

    for (int y = 0; y < static_cast<int>(dst.size.y); y++) {
        int vidx = static_cast<int>(colors * src.size.x * (v[y].line - ((v[y].w < 128) ? 1 : 0)));
        for (auto const &hid : hpick)
            for (int c = 0; c < colors; c++)
                *data++ = s[vidx + hid + c];
    }
}

// Calls the interpolation for the right data type
void resample(const repro_conf *cfg, const iline *h,
    const interpolation_buffer &src, interpolation_buffer &dst)
{
#define RESAMP(T) if (cfg->nearNb) interpolateNN<T>(src, dst, h, v); else interpolate<T>(src, dst, h, v)

    const iline *v = h + dst.size.x;
    switch (cfg->raster.datatype) {
    case GDT_UInt16:
        RESAMP(apr_uint16_t);
        break;
    case GDT_Int16:
        RESAMP(apr_int16_t);
        break;
    default: // Byte
        RESAMP(apr_byte_t);
    }

#undef RESAMP
}


// first param is reverse of radius, second is input coordinate
typedef double coord_conv_f(double, double);

// Identical projection coordinate conversion
static double same_proj(double, double c) {
    return c;
}

// Web mercator X to longitude in degrees
static double wm2lon(double eres, double x) {
    return 360 * eres * x;
}

static double lon2wm(double eres, double lon) {
    return lon / eres / 360;
}

static double m2lon(double eres, double x) {
    return wm2lon(eres, x);
}

static double lon2m(double eres, double lon) {
    return lon2wm(eres, lon);
}

// Web mercator Y to latitude in degrees
static double wm2lat(double eres, double y) {
    return 90 * (1 - 4 / pi * atan(exp(eres * pi * 2 * -y)));
}

// Goes out of bounds close to the poles, valid latitude range is under 85.052
static double lat2wm(double eres, double lat) {
    if (abs(lat) > 85.052)
        return (lat > 0) ? (0.5 / eres) : (-0.5 / eres); // pi*R or -pi*R
    return log(tan(pi / 4 * (1 + lat / 90))) / eres / 2 / pi;
}

// Mercator, projection EPSG:3395, conversion to WebMercator and degrees
// Earth
const double E = 0.08181919084262149; // sqrt(f * ( 2 - f)), f = 1/298.257223563

static double lat2m(double eres, double lat) {
    // WGS84
    // Real mercator reaches a bit further on earth due to flattening
    if (abs(lat) > 85.052)
        return (lat > 0) ? (0.5 / eres) : (-0.5 / eres); // pi*R or -pi*R
    double s = sin(pi * lat / 180);
    return log(tan((1 + s) / (1 - s) * pow((1 - E*s) / (1 + E*s), E))) / eres / 2 / pi;
}

// The iterative solution, slightly time-consuming
static double m2lat(double eres, double y) {
    // Normalize y
    y *= eres * pi * 2;
    // Starting value, in radians
    double lat = pi / 2 - 2 * atan(exp(-y));
    // Max 10 iterations, it takes about 6 or 7
    for (int i = 0; i < 10; i++) {
        double es = E * sin(lat);
        double nlat = pi / 2 - 2 * atan(exp(-y)*pow((1 - es) / (1 + es), E / 2));
        if (lat == nlat) // Max 
            break; // Normal exit
        lat = nlat;
    }
    return lat * 180 / pi;  // Return the value in degrees
}

// Web mercator to mercator and vice-versa are composite transformations
static double m2wm(double eres, double y) {
    return lat2wm(eres, m2lat(eres, y));
}

static double wm2m(double eres, double y) {
    return lat2m(eres, wm2lat(eres, y));
}

// The x dimension is most of the time linear, convenience function
static void prep_x(work &info, iline *table) {
    bbox_t &bbox = info.out_equiv_bbox;
    const double out_r = (bbox.xmax - bbox.xmin) / info.c->raster.pagesize.x;
    const double in_r = info.c->inraster.rsets[info.tl.l].rx;
    const double offset = bbox.xmin - info.in_bbox.xmin + 0.5 * (out_r - in_r);
    init_ilines(in_r, out_r, offset, table, static_cast<int>(info.c->raster.pagesize.x));
}

// Initialize ilines for y
// coord_f is the function converting from output coordinates to input
static void prep_y(work &info, iline *table, coord_conv_f coord_f) {
    const int size = static_cast<int>(info.c->raster.pagesize.y);
    const double out_r = (info.out_bbox.ymax - info.out_bbox.ymin) / size;
    const double in_r = info.c->inraster.rsets[info.tl.l].ry;
    double offset = info.in_bbox.ymax - 0.5 * in_r;
    for (int i = 0; i < size; i++) {
        // Coordinate of output line in input projection
        const double coord = coord_f(info.c->eres, info.out_bbox.ymax - out_r * (i + 0.5));
        // Same in pixels
        const double pos = (offset - coord) / in_r;
        // Pick the higher line
        table[i].line = static_cast<int>(ceil(pos));
        if (ceil(pos) != floor(pos))
            table[i].w = static_cast<int>(floor(256.0 * (pos - floor(pos))));
        else // Perfect match with this line
            table[i].w = 255;
    }
}

static bool our_request(request_rec *r, repro_conf *cfg) {
    if (r->method_number != M_GET || cfg->arr_rxp == NULL || cfg->code >= P_COUNT)
        return false;

    char *url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;
    for (int i = 0; i < cfg->arr_rxp->nelts; i++) {
        ap_regex_t *m = APR_ARRAY_IDX(cfg->arr_rxp, i, ap_regex_t *);
        if (!ap_regexec(m, url_to_match, 0, NULL, 0)) return true; // Found
    }

    return false;
}

static int handler(request_rec *r)
{
    // Tables of reprojection code dependent functions, to dispatch on
    // Could be done with a switch, this is more compact and easier to extend
    // The order has to match the PCode definitions
    static coord_conv_f *cxf[P_COUNT] = { same_proj, wm2lon, lon2wm, same_proj, same_proj };
    static coord_conv_f *cyf[P_COUNT] = { same_proj, wm2lat, lat2wm, m2wm, wm2m };

    // TODO: use r->header_only to verify ETags, assuming the subrequests are faster in that mode

    // pick up a modified config if one exists in the notes for this request.
    repro_conf *cfg = ap_get_module_config(r->request_config, &reproject_module)
        ? (repro_conf *)ap_get_module_config(r->request_config, &reproject_module) :
            (repro_conf *)ap_get_module_config(r->per_dir_config, &reproject_module);

    if (!our_request(r, cfg)) return DECLINED;

    apr_array_header_t *tokens = tokenize(r->pool, r->uri);
    if (tokens->nelts < 3) return DECLINED; // At least Level Row Column

    int ct;
    png_colorp png_palette;
    png_bytep png_trans;
    png_palette = (png_colorp)apr_pcalloc(r->pool, 256 * sizeof(png_color));
    png_trans = (png_bytep)apr_pcalloc(r->pool, 256 * sizeof(unsigned char));

    work info;
    info.c = cfg;
    info.seed = cfg->seed;
    sz &tile = info.out_tile;
    bbox_t &oebb = info.out_equiv_bbox;
    memset(&tile, 0, sizeof(tile));

    // Input order is M/Level/Row/Column, with M being optional
    // Need at least three numerical arguments
    tile.x = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.y = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.l = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);

    // We can ignore the error on this one, defaults to zero
    // The parameter before the level can't start with a digit for an extra-dimensional MRF
    if (cfg->raster.size.z != 1 && tokens->nelts)
        tile.z = apr_atoi64(*(char **)apr_array_pop(tokens));

    // Don't allow access to negative values, send the empty tile instead
    if (tile.l < 0 || tile.x < 0 || tile.y < 0)
        return send_empty_tile(r);

    // Adjust the level to internal
    tile.l += cfg->raster.skip;

    // Outside of bounds tile returns a not-found error
    if (tile.l >= cfg->raster.n_levels ||
        tile.x >= cfg->raster.rsets[tile.l].width ||
        tile.y >= cfg->raster.rsets[tile.l].height)
        return send_empty_tile(r);

    // Need to have mod_receive available
    SERR_IF(!ap_get_output_filter_handle("Receive"), "mod_receive not installed");

    tile_to_bbox(cfg->raster, &(info.out_tile), info.out_bbox);
    // calculate the input projection equivalent bbox
    oebb.xmin = cxf[cfg->code](cfg->eres, info.out_bbox.xmin);
    oebb.xmax = cxf[cfg->code](cfg->eres, info.out_bbox.xmax);
    oebb.ymin = cyf[cfg->code](cfg->eres, info.out_bbox.ymin);
    oebb.ymax = cyf[cfg->code](cfg->eres, info.out_bbox.ymax);
    double out_equiv_rx = (oebb.xmax - oebb.xmin) / cfg->raster.pagesize.x;
    double out_equiv_ry = (oebb.ymax - oebb.ymin) / cfg->raster.pagesize.y;

    // WM and GCS distortion is under 12:1, this eliminates the case where
    // WM has no input tiles
    if (out_equiv_ry < out_equiv_rx / 12)
        return send_empty_tile(r);

    // Pick the input level
    int input_l = input_level(info, out_equiv_rx, out_equiv_ry);
    bbox_to_tile(cfg->inraster, input_l, oebb, info.tl, info.br);

    info.tl.z = info.br.z = info.out_tile.z;
    info.tl.c = info.br.c = cfg->inraster.pagesize.c;
    info.tl.l = info.br.l = input_l;
    tile_to_bbox(info.c->inraster, &info.tl, info.in_bbox);
    // Use relative level to request the data
    info.tl.l -= cfg->inraster.skip;
    info.br.l -= cfg->inraster.skip;

    // Incoming tiles buffer
    void *buffer = NULL;
    apr_status_t status = retrieve_source(r, info, &buffer, ct, png_palette, png_trans);
    if (APR_SUCCESS != status) return status;
    // back to absolute level for input tiles
    info.tl.l = info.br.l = input_l;

    // Check the etag match before preparing output
    char ETag[16];
    uint64tobase32(info.seed, ETag, info.seed == cfg->seed);
    apr_table_set(r->headers_out, "ETag", ETag);
    if (etag_matches(r, ETag))
        return HTTP_NOT_MODIFIED;

    // Outgoing raw tile buffer
    int pixel_size = static_cast<int>(cfg->raster.pagesize.c * DT_SIZE(cfg->raster.datatype));
    storage_manager raw;
    raw.size = static_cast<int>(cfg->raster.pagesize.x * cfg->raster.pagesize.y * pixel_size);
    raw.buffer = static_cast<char *>(apr_palloc(r->pool, raw.size));

    // Set up the input and output 2D interpolation buffers
    interpolation_buffer ib = { buffer, cfg->inraster.pagesize };
    // The input buffer contains multiple input pages
    ib.size.x *= (info.br.x - info.tl.x);
    ib.size.y *= (info.br.y - info.tl.y);
    interpolation_buffer ob = { raw.buffer, cfg->raster.pagesize };

    iline *table = static_cast<iline *>(apr_palloc(r->pool, static_cast<apr_size_t>(sizeof(iline)*(ob.size.x + ob.size.y))));
    iline *ytable = table + ob.size.x;

    // The x dimension scaling is always linear
    prep_x(info, table);
    adjust_itable(table, static_cast<int>(ob.size.x), static_cast<unsigned int>(ib.size.x - 1));
    prep_y(info, ytable, cyf[cfg->code]);
    adjust_itable(ytable, static_cast<int>(ob.size.y), static_cast<unsigned int>(ib.size.y - 1));

    // Perform the actual resampling
    resample(cfg, table, ib, ob);

    // A buffer for the output tile
    storage_manager dst;
    dst.size = cfg->max_output_size;
    dst.buffer = static_cast<char *>(apr_palloc(r->pool, dst.size));

    const char *error_message = "Unknown output format requested";

    if (NULL == cfg->mime_type || 0 == apr_strnatcmp(cfg->mime_type, "image/jpeg")) {
        jpeg_params params;
        params.quality = static_cast<int>(cfg->quality);
        error_message = jpeg_encode(params, cfg->raster, raw, dst);
    }
    else if (0 == apr_strnatcmp(cfg->mime_type, "image/png")) {
        png_params params;
        set_png_params(cfg->raster, &params);
        if (cfg->quality < 10) // Otherwise use the default of 6
            params.compression_level = static_cast<int>(cfg->quality);
        if (png_trans != NULL)
         	params.has_transparency = TRUE;
        if (png_palette != NULL) {
        	params.color_type = ct;
			params.bit_depth = 8;
        }
        error_message = png_encode(params, cfg->raster, raw, dst, png_palette, png_trans);
        png_palette = 0;
		png_trans = 0;
    }

    if (error_message) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "%s from :%s", error_message, r->uri);
        // Something went wrong if compression fails
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    apr_table_set(r->headers_out, "ETag", ETag);
    return send_image(r, dst, cfg->mime_type);
}

static const char *read_config(cmd_parms *cmd, repro_conf *c, const char *src, const char *fname)
{
    char *err_message;
    const char *line;

    // Start with the source configuration
    apr_table_t *kvp = read_pKVP_from_file(cmd->temp_pool, src, &err_message);
    if (NULL == kvp) return err_message;

    err_message = const_cast<char*>(ConfigRaster(cmd->pool, kvp, c->inraster));
    if (err_message) return apr_pstrcat(cmd->pool, "Source ", err_message, NULL);

    // Then the real configuration file
    kvp = read_pKVP_from_file(cmd->temp_pool, fname, &err_message);
    if (NULL == kvp) return err_message;
    err_message = const_cast<char *>(ConfigRaster(cmd->pool, kvp, c->raster));
    if (err_message) return err_message;

    // Output mime type
    line = apr_table_get(kvp, "MimeType");
    c->mime_type = (line) ? apr_pstrdup(cmd->pool, line) : "image/jpeg";

    // Get the planet circumference in meters, for partial coverages
    line = apr_table_get(kvp, "Radius");
    // Stored as radius and the inverse of circumference
    double radius = (line) ? strtod(line, NULL) : 6378137.0;
    c->eres = 1.0 / (2 * pi * radius);

    // Sampling flags
    c->oversample = NULL != apr_table_get(kvp, "Oversample");
    c->nearNb = NULL != apr_table_get(kvp, "Nearest");

    line = apr_table_get(kvp, "ExtraLevels");
    c->max_extra_levels = (line) ? int(atoi(line)) : 0;

    line = apr_table_get(kvp, "ETagSeed");
    // Ignore the flag
    int flag;
    c->seed = line ? base32decode(line, &flag) : 0;
    // Set the missing tile etag, with the extra bit set
    uint64tobase32(c->seed, c->eETag, 1);

    // EmptyTile, defaults to pass-through
    line = apr_table_get(kvp, "EmptyTile");
    if (line) {
        err_message = read_empty_tile(cmd, c, line);
        if (err_message) return err_message;
    }

    line = apr_table_get(kvp, "InputBufferSize");
    c->max_input_size = DEFAULT_INPUT_SIZE;
    if (line)
        c->max_input_size = (apr_size_t)apr_strtoi64(line, NULL, 0);

    line = apr_table_get(kvp, "OutputBufferSize");
    c->max_output_size = DEFAULT_INPUT_SIZE;
    if (line)
        c->max_output_size = (apr_size_t)apr_strtoi64(line, NULL, 0);

    line = apr_table_get(kvp, "SourcePath");
    if (!line)
        return "SourcePath directive is missing";
    c->source = apr_pstrdup(cmd->pool, line);

    line = apr_table_get(kvp, "SourcePostfix");
    if (line)
        c->postfix = apr_pstrdup(cmd->pool, line);

    c->quality = 75.0; // Default for JPEG
    line = apr_table_get(kvp, "Quality");
    if (line)
        c->quality = strtod(line, NULL);

    // Set the reprojection code
    if (IS_AFFINE_SCALING(c))
        c->code = P_AFFINE;
    else if (IS_GCS2WM(c))
        c->code = P_GCS2WM;
    else if (IS_WM2GCS(c))
        c->code = P_WM2GCS;
    else if (IS_WM2M(c))
        c->code = P_WM2M;
    else
        return "Can't determine reprojection function";

    return NULL;
}

static const command_rec cmds[] =
{
    AP_INIT_TAKE2(
    "Reproject_ConfigurationFiles",
    (cmd_func)read_config, // Callback
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Source and output configuration files"
    ),

    AP_INIT_TAKE1(
    "Reproject_RegExp",
    (cmd_func)set_regexp,
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Regular expression that the URL has to match.  At least one is required."),

    { NULL }
};

static void register_hooks(apr_pool_t *p) {
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

module AP_MODULE_DECLARE_DATA reproject_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge
    0, // No server_config
    0, // No server_merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
