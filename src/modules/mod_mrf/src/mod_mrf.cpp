/*
* An AHTSE module that serves tiles from an MRF
* Lucian Plesea
* (C) 2016-2019
*/

#include <ahtse.h>
#include "receive_context.h"

#include <algorithm>
#include <cmath>
#include <http_log.h>
#include <http_request.h>
#include <string>

using namespace std;
NS_AHTSE_USE
NS_ICD_USE

// Max count, should never happen
#define NPOS 0xffffffff
// Block size for canned format
#define BSZ 512

// Bit set count for 32bit values
#if defined(_WIN32)
#include <intrin.h>
#define bsc __popcnt
#else
// This only works in gcc
#define bsc __builtin_popcount
#endif

// The next few functions are from the mrf/mrf_apps/can program
// Check a specific bit position in a canned index header line
// The bit position is [0, 95] and the first 32bit value is skipped
static inline bool is_on(uint32_t *values, int bit) {
    return 0 != (values[1 + bit / 32] & (static_cast<uint32_t>(1) << bit % 32));
}

// Canned index file header size
// 16 byte prefix + 96 bit records in 128 bit lines
static inline uint64_t hsize(uint64_t in_size) {
    return 16 + 16 * ((96 * BSZ - 1 + in_size) / (96 * BSZ));
}

// Packed block count, for a bit position in a line
static inline uint32_t block_count(uint32_t *values, int bit) {
    if (!is_on(values, bit))
        return NPOS;
    return (values[0] +
        bsc(values[1]) * (((bit / 32) & 1) | (bit / 64)) +
        bsc(values[2]) * (bit / 64) +
        bsc(values[1 + (bit / 32)] & ((1ULL << (bit % 32)) - 1)));
}

// How do we map M param mapping to a file name?
enum mappings{
    MAPM_NONE = 0, 
    MAPM_PREFIX // The M value prefixes the file name, both index and data
};

struct mrf_conf {
    // array of guard regexp, one of them has to match
    apr_array_header_t *arr_rxp;

    // The raster represented by this MRF configuration
    TiledRaster raster;

    // At least one source, but there could be more
    apr_array_header_t *source;

    // The MRF index file, required
    vfile_t idx;

    // Used for redirect, how many times to try
    // defaults to 5
    int retries;

    // If set, only secondary requests are allowed
    int indirect;

    // If set, file handles are not held open
    int dynamic;

    // How do we map M param mapping to a file name?
    int mmapping;

    // the canned index header size, or 0 for normal index
    uint64_t can_hsize;
};

extern module AP_MODULE_DECLARE_DATA mrf_module;

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(mrf);
#endif

static void *create_dir_config(apr_pool_t *p, char *dummy) {
    mrf_conf *c = reinterpret_cast<mrf_conf *>(
        apr_pcalloc(p, sizeof(mrf_conf)));
    c->retries = 5;
    return c;
}

// Parse a comma separated list of sources, add the entries to the array
// Source may include offset and size, white space separated
static const char *parse_sources(cmd_parms *cmd, const char *src, 
    apr_array_header_t *arr, bool redir = false)
{
    apr_array_header_t *inputs = tokenize(cmd->temp_pool, src, ',');
    for (int i = 0; i < inputs->nelts; i++) {
        vfile_t *entry = &APR_ARRAY_PUSH(arr, vfile_t);
        memset(entry, 0, sizeof(vfile_t));
        char *input = APR_ARRAY_IDX(inputs, i, char *);

        char *fname = ap_getword_white_nc(arr->pool, &input);
        if (!fname || strlen(fname) < 1)
            return "Source name missing";

        if (redir) { // Check that it is absolute and add :/
            if (fname[0] != '/')
                return apr_pstrcat(cmd->pool, "Only absolute redirects as allowed, ",
                    fname, " is not absolute", NULL);
            fname = apr_pstrcat(arr->pool, ":/", fname, NULL);
        }

        entry->name = fname;

        // See if there are more arguments, should be offset and size
        if (*input != 0) entry->range.offset = strtoull(input, &input, 0);
        if (*input != 0) entry->range.size = strtoull(input, &input, 0);
    }
    return nullptr;
}

#define parse_redirects(cmd, src, arr) parse_sources(cmd, src, arr, true)

//
// This function sets the MRF specific parameters
// The raster size is defined using the normal libahtse parameters
// Unique directives:
// IndexFile : May be local paths or indirect, if prefixed by ://
// DataFile
// Redirect : Old style redirects, only if DataFile is not present
// RetryCount : // For indirect redirect range requests
// EmptyTile :
// Dynamic On : If the file handles are not to be hold
//
static const char *file_set(cmd_parms *cmd, void *dconf, const char *arg)
{
    ap_assert(sizeof(apr_off_t) == 8);
    mrf_conf *c = (mrf_conf *)dconf;
    const char *err_message, *line;

    apr_table_t *kvp = readAHTSEConfig(cmd->temp_pool, arg, &err_message);
    if (NULL == kvp)
        return err_message;

    err_message = configRaster(cmd->pool, kvp, c->raster);
    if (err_message)
        return err_message;

    // Got the parsed kvp table, parse the configuration items
    // Usually there is a single source, but we still need an array
    c->source = apr_array_make(cmd->pool, 1, sizeof(vfile_t));

    // Index file can also be provided, there could be a default
    line = apr_table_get(kvp, "IndexFile");
    c->idx.name = apr_pstrdup(cmd->pool, line);

    // The DataFile, required, multiple times, includes redirects
    line = apr_table_getm(cmd->temp_pool, kvp, "DataFile");
    if ((NULL != (line = apr_table_getm(cmd->temp_pool, kvp, "DataFile"))) &&
        (NULL != (err_message = parse_sources(cmd, line, c->source))))
        return err_message;

    // Old style redirects go at the end
    if ((NULL != (line = apr_table_getm(cmd->temp_pool, kvp, "Redirect"))) &&
        (NULL != (err_message = parse_redirects(cmd, line, c->source))))
        return err_message;

    // Check that we have at least one data file
    const char *firstname = nullptr;
    if (0 == c->source->nelts || !(firstname = APR_ARRAY_IDX(c->source, 0, vfile_t).name))
        return "Need at least one DataFile directive";

    line = apr_table_get(kvp, "RetryCount");
    c->retries = 1 + (line ? atoi(line) : 0);
    if ((c->retries < 1) || (c->retries > 100))
        return "Invalid RetryCount value, should be 0 to 99";

    // If an emtpy tile is not provided, it falls through, which results in a 404 error
    // If provided, it has an optional size and offset followed by file name which 
    // defaults to datafile read the empty tile
    // Default file name is the name of the first data file, if provided
    line = apr_table_get(kvp, "EmptyTile");
    if (line && strlen(line) && (err_message = readFile(
        cmd->pool, c->raster.missing.data, line)))
        return err_message;

    // Set the index file name based on the first data file, if there is only one
    if (!c->idx.name) {
        c->idx.name = apr_pstrdup(cmd->pool, firstname);
        char *last;
        char *token = apr_strtok(c->idx.name, ".", &last); // strtok destroys the idxfile
        while (*last != 0 && token != NULL)
            token = apr_strtok(NULL, ".", &last);
        memcpy(c->idx.name, firstname, strlen(firstname)); // Get a new copy
        if (token != NULL && strlen(token) == 3)
            memcpy(token, "idx", 3);
    }

    if ((line = apr_table_get(kvp, "Dynamic")) && getBool(line))
        c->dynamic = true;

    // The original index file size is the number of tiles * 16
    // Since the MRF always ends with a single tile, the total number
    // of tiles in the MRF is equal to the number of tiles at level 0 + size.z
    if ((line = apr_table_get(kvp, "CannedIndex")) && getBool(line))
        c->can_hsize = hsize((c->raster.size.z + c->raster.rsets[0].tiles) * 16);

    // What parameters we need for M mapping ?
    if ((line = apr_table_get(kvp, "MMapping"))) {
        if (!apr_strnatcmp(line, "prefix")) {
            // Direct mapping means M becomes the prefix for the file name, no folder
            c->mmapping = MAPM_PREFIX;
        }
        else
            return "Unknown value for MMapping";
    }

    return NULL;
}

static const apr_int32_t open_flags = APR_FOPEN_READ | APR_FOPEN_BINARY | APR_FOPEN_LARGEFILE;

// Return the first source which contains the index, adjusts the index offset if necessary
static const vfile_t *pick_source(const apr_array_header_t *sources, range_t *index) {
    for (int i = 0; i < sources->nelts; i++) {
        vfile_t *source = &APR_ARRAY_IDX(sources, i, vfile_t);
        if ((source->range.offset == 0 && source->range.size == 0)
            || (index->offset >= source->range.offset 
                && (source->range.size == 0
                    || index->offset - source->range.offset + index->size <= source->range.size)))
        {
            index->offset -= source->range.offset;
            return source;
        }
    }
    return NULL;
}

// An open file handle and the matching file name, to be used as a note
struct file_note {
    const char *fname;
    apr_file_t *pfh;
};

//
// Open or retrieve a connection cached file handle
// This is a real file
// Do no close the returned file handle, it will be removed when the connection drops
//
// Only one opened handle exists per connection/token pair
// This may lead to less caching, but avoids having too many opened files
//
static apr_status_t openConnFile(request_rec *r, apr_file_t **ppfh, const char *fname,
    const char *token, apr_int32_t extra_open_flags = 0)
{
    apr_table_t *conn_notes = r->connection->notes;

    file_note *fnote = (file_note *)apr_table_get(conn_notes, token);
    if (fnote && !apr_strnatcmp(fnote->fname, fname)) { // Match, return the handle
        *ppfh = fnote->pfh;
        return APR_SUCCESS;
    }

    // Use the connection pool, it will close the file when it gets dropped
    apr_pool_t *pool = r->connection->pool;
    if (!fnote) { // new connection file
        fnote = reinterpret_cast<file_note *>(apr_pcalloc(pool, sizeof(file_note)));
    }
    else { // Not the right file, clean it up
        apr_table_unset(conn_notes, token); // Does not remove the storage
        apr_file_close(fnote->pfh);
    }

    apr_status_t stat = apr_file_open(ppfh, fname, open_flags || extra_open_flags, 0, pool);
    if (APR_SUCCESS != stat)
        return stat;

    // Update the note and hook it up before returning
    fnote->fname = apr_pstrdup(pool, fname);
    fnote->pfh = *ppfh;
    apr_table_setn(conn_notes, token, (const char *)fnote);
    return APR_SUCCESS;
}

// Like pread, except not really thread safe
// Range reads are done if file starts with ://
// Range offset is offset, size is mgr->size
// The token is used for connection caching

static int vfile_pread(request_rec *r, storage_manager &mgr,
    apr_off_t offset, const char *fname, const char *token = "MRF_DATA")
{
    auto cfg = get_conf<mrf_conf>(r, &mrf_module);
    const char *name = fname;

    bool redirect = (strlen(name) > 3 && name[0] == ':' && name[1] == '/');
    if (redirect) {
        // Remote file, just use a range request
        // TODO: S3 authorized requests

        // Skip the ":/" used to mark a redirect
        name = fname + 2;

        ap_filter_rec_t *receive_filter = ap_get_output_filter_handle("Receive");
        if (!receive_filter) {
            ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
                "Can't find receive filter, did you load mod_receive?");
            return 0;
        }

        // Get a buffer for the received image
        receive_ctx rctx;
        rctx.buffer = static_cast<char *>(mgr.buffer);
        rctx.maxsize = static_cast<int>(mgr.size);
        rctx.size = 0;

        // Data file is on a remote site a range request redirect with a range header
        char *Range = apr_psprintf(r->pool,
            "bytes=%" APR_UINT64_T_FMT "-%" APR_UINT64_T_FMT,
            offset, offset + mgr.size);

        // S3 may return less than requested, so we retry the request a couple of times
        int tries = cfg->retries;
        bool failed = false;
        apr_time_t now = apr_time_now();
        do {
            request_rec *sr = ap_sub_req_lookup_uri(name, r, r->output_filters);
            ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=begin in mrf, filterName=%s", r->output_filters->frec->name);
            apr_table_setn(sr->headers_in, "Range", Range);
            ap_filter_t *rf = ap_add_output_filter_handle(receive_filter, &rctx,
                sr, sr->connection);
            int status = ap_run_sub_req(sr);
            ap_remove_output_filter(rf);
            ap_destroy_sub_req(sr);

            if ((status != APR_SUCCESS
                    || sr->status != HTTP_PARTIAL_CONTENT
                    || static_cast<size_t>(rctx.size) != mgr.size)
                        && (0 == tries--))
            {
                ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
                    "Can't fetch data from %s, took %" APR_TIME_T_FMT "us",
                    name, apr_time_now() - now);
                failed = true;
            }
        } while (!failed && static_cast<size_t>(rctx.size) != mgr.size);

        return rctx.size;
    } // Redirect read

    // Local file
    apr_file_t *pfh;
    apr_status_t stat;

    int dynamic = 0;
    // Keep handles open, except if dynamic is on and fname is the default
    if (cfg->dynamic) {
        if (!apr_strnatcmp(token, "MRF_DATA")) {
            // Only single data file, unmodified can be dynamic
            if (1 == cfg->source->nelts) {
                dynamic = !apr_strnatcmp(fname, APR_ARRAY_IDX(cfg->source, 0, vfile_t).name);
            }
        }
        else { // Only unmodified index name can be dynamic
            dynamic = !apr_strnatcmp(fname, cfg->idx.name);
        }
    }

    if (dynamic)
        stat = apr_file_open(&pfh, fname, open_flags, 0, r->pool);
    else
        stat = openConnFile(r, &pfh, fname, token, APR_FOPEN_BUFFERED);
        ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=begin mrf_read , fname=%s name=%s stat=%d t=%s", fname,name,stat,token);
    if (stat != APR_SUCCESS) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
            "Can't open file %s", name);
        return 0; // No file
    }

    apr_size_t sz = static_cast<apr_size_t>(mgr.size);
    stat = apr_file_seek(pfh, APR_SET, &offset);
    if (APR_SUCCESS != stat || APR_SUCCESS != apr_file_read(pfh, mgr.buffer, &sz)) {
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r,
            "Read error in %s offset %" APR_OFF_T_FMT, name, offset);
        sz = 0;
    } 

    if (dynamic)
        apr_file_close(pfh);
    // Don't close non-dynamic mode handles, they are reused

    mgr.size = sz;
    return static_cast<int>(sz);
}

// read index, returns error message or null
// MRF index file is network order
static const char *read_index(request_rec *r, range_t *idx, apr_off_t offset, const char *fname) {
    auto  cfg = get_conf<mrf_conf>(r, &mrf_module);
    storage_manager dst(idx, sizeof(range_t));

    if (cfg->can_hsize) { // No checks that the file is correct
        // Original block offset
        uint64_t boffset = offset / BSZ;

        // Read the line containing the target bit
        uint32_t line[4];
        storage_manager lmgr(line, 16);
        if (16 != vfile_pread(r, lmgr, 
            16 * (1 + (boffset / 96)), fname, "MRF_INDEX"))
            return "Bitmap read error";

#if defined(be32toh)
        // Change to host endian
        for (int i = 0; i < 4; i++)
            line[i] = be32toh(line[i]);
#endif

        // The relocated block number for the original index record
        uint64_t blockn = block_count(line, static_cast<int>(boffset % 96));
        if (NPOS == blockn) {
            idx->size = idx->offset = 0;
            return nullptr;
        }

        // Adjust the offset before reading the data
        offset = cfg->can_hsize + blockn * BSZ + offset % BSZ;
    }

    if (sizeof(range_t) != vfile_pread(r, dst, offset, fname, "MRF_INDEX"))
        return "Read error";

#if defined(be64toh)
    idx->offset = be64toh(idx->offset);
    idx->size = be64toh(idx->size);
#endif

    return nullptr;
}

// Quiet error
#define REQ_ERR_IF(X) if (X) {\
    return HTTP_BAD_REQUEST; \
}

// Logged error
#define SERR_IF(X, msg) if (X) { \
    ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "%s", msg);\
    return HTTP_INTERNAL_SERVER_ERROR; \
}

// Change the file name depending on the configuration
// Returns nullptr if something went wrong
const char *apply_mmapping(request_rec *r, const sz5* tile, const char *fname)
{
    auto cfg = get_conf<mrf_conf>(r, &mrf_module);
    if (cfg->mmapping == MAPM_NONE || tile->z == 0)
        return fname;

    // Switch to C++
    string ret_fname(fname);
    switch (cfg->mmapping) {
    case MAPM_PREFIX:
        size_t bnamepos = ret_fname.find_last_of("/");
        if (bnamepos == string::npos)
            return NULL;
        ret_fname.insert(bnamepos + 1, apr_ltoa(r->pool, static_cast<long>(tile->z)));
        break;
    }
    return apr_pstrdup(r->pool, ret_fname.c_str());
}

static int handler(request_rec *r) {
    if (r->method_number != M_GET)
        return DECLINED;

    auto cfg = get_conf<mrf_conf>(r, &mrf_module);
    if ((cfg->indirect && !r->main) || 
        !requestMatches(r, cfg->arr_rxp))
        return DECLINED;

    apr_array_header_t *tokens = tokenize(r->pool, r->uri, '/');
    if (tokens->nelts < 3)
        return DECLINED; // At least Level Row Column

    const char *uuid = apr_table_get(r->headers_in, "UUID") 
        ? apr_table_get(r->headers_in, "UUID") 
        : apr_table_get(r->subprocess_env, "UNIQUE_ID");
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=begin_mod_mrf_handle, timestamp=%ld, uuid=%s",
        apr_time_now(), uuid);

    // Use a xyzc structure, with c being the level
    // Input order is M/Level/Row/Column, with M being optional
    sz5 tile;
    memset(&tile, 0, sizeof(tile));

    // Need at least three numerical arguments
    tile.x = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.y = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.l = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);

    const TiledRaster &raster(cfg->raster);

    // We can ignore the error on this one, defaults to zero
    // The parameter before the level can't start with a digit for an extra-dimensional MRF
    if (tokens->nelts && (raster.size.z != 1 || cfg->mmapping != MAPM_NONE))
        tile.z = apr_atoi64(*(char **)apr_array_pop(tokens));

    // Don't allow access to levels less than zero, send the empty tile instead
    if (tile.l < 0 || tile.x < 0 || tile.y < 0)
        return sendEmptyTile(r, raster.missing);

    tile.l += raster.skip;
    // Check for bad requests, outside of the defined bounds
    REQ_ERR_IF(tile.l >= static_cast<size_t>(raster.n_levels));
    rset *level = raster.rsets + tile.l;
    REQ_ERR_IF(tile.x >= static_cast<size_t>(level->w) || tile.y >= static_cast<size_t>(level->h));

    // Force single z if that's how the MRF is set up, maybe file name mapping applies
    apr_int64_t tz = (raster.size.z != 1) ? tile.z : 0;
    // Offset of the index entry for this tile
    apr_off_t tidx_offset = sizeof(range_t) * (level->tiles +
        + level->w * (tz * level->h + tile.y) + tile.x);
    apr_time_t start_index_lookup = apr_time_now();
    range_t index;
    const char *idx_fname = apply_mmapping(r, &tile, cfg->idx.name);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=mod_mrf_index_read, duration=%ld, IDX=%s",
        apr_time_now() - start_index_lookup, idx_fname);
    const char *message = read_index(r, &index, tidx_offset, idx_fname);
    if (message) { // Fatal error
        if (!apr_strnatcmp(idx_fname, cfg->idx.name)) {
            SERR_IF(message, message);
        }
        REQ_ERR_IF(message);
    }

    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=mod_mrf_index_read, duration=%ld, uuid=%s",
        apr_time_now() - start_index_lookup, uuid);

    // MRF index record is in network order
    if (index.size < 4) // Need at least four bytes for signature check
        return sendEmptyTile(r, raster.missing);

    SERR_IF(MAX_TILE_SIZE < index.size, apr_pstrcat(r->pool,
        "Tile too large found in ", idx_fname, NULL));

    // Check for conditional ETag here, no need to get the data
    char ETag[16];
    // Try to distribute the bits a bit to generate an ETag
    tobase32((raster.seed ^ (index.size << 40)) ^ index.offset, ETag);
    if (etagMatches(r, ETag)) {
        apr_table_set(r->headers_out, "ETag", ETag);
        return HTTP_NOT_MODIFIED;
    }

    // Now for the data part
    const vfile_t *src = pick_source(cfg->source, &index);
    const char *name = (src && src->name) ? apply_mmapping(r, &tile, src->name) : nullptr;
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=mod_mrf_data_read, duration=%ld, DATA=%s",
        apr_time_now() - start_index_lookup, name);
    SERR_IF(!name, apr_psprintf(r->pool, "No data file configured for %s", r->uri));

    apr_size_t size = static_cast<apr_size_t>(index.size);
    storage_manager img(apr_palloc(r->pool, size), size);

    SERR_IF(!img.buffer, "Memory allocation error in mod_mrf");
    SERR_IF(img.size != static_cast<size_t>(vfile_pread(r, img, index.offset, name)),
        "Data read error");

    // Pass-through header
    const char *layer_id_request = apr_table_get(r->notes, "Layer-Identifier-Request");
    if (layer_id_request) {
        apr_table_set(r->headers_out, "Layer-Identifier-Request", layer_id_request);
    }
    const char *layer_id_actual = apr_table_get(r->notes, "Layer-Identifier-Actual");
    if (layer_id_actual) {
        apr_table_set(r->headers_out, "Layer-Identifier-Actual", layer_id_actual);
    }
    const char *layer_time_request = apr_table_get(r->notes, "Layer-Time-Request");
    if (layer_time_request) {
        apr_table_set(r->headers_out, "Layer-Time-Request", layer_time_request);
    }
    const char *layer_time_actual = apr_table_get(r->notes, "Layer-Time-Actual");
    if (layer_time_actual) {
        apr_table_set(r->headers_out, "Layer-Time-Actual", layer_time_actual);
    }

    // Looks fine, set the outgoing etag and then the image
    apr_table_set(r->headers_out, "ETag", ETag);
    apr_table_set(r->headers_out, "Access-Control-Allow-Origin", "*");
    auto status = sendImage(r, img);
    if (status != OK) {
        return status;
    }
    // LOGGING
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=end_mod_mrf_handle, timestamp=%ld, uuid=%s",
        apr_time_now(), uuid);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=end_onearth_handle, timestamp=%ld, uuid=%s",
        apr_time_now(), uuid);

    return status;
}

static const command_rec cmds[] = {
    AP_INIT_TAKE1(
    "MRF_RegExp",
    (cmd_func)set_regexp<mrf_conf>,
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Regular expression that the URL has to match.  At least one is required."
    ),

    AP_INIT_FLAG(
    "MRF_Indirect",
    (cmd_func) ap_set_flag_slot,
    (void *)APR_OFFSETOF(mrf_conf, indirect),
    ACCESS_CONF,
    "If set, this configuration only responds to subrequests"
    ),

    AP_INIT_TAKE1(
    "MRF_ConfigurationFile",
    (cmd_func) file_set, // Callback
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "The configuration file for this module"
    ),

    { NULL }
};

static void register_hooks(apr_pool_t *p) {
    // Up in the stack, but leave APR_HOOK_FIRST available
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST + 1);
}

module AP_MODULE_DECLARE_DATA mrf_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge
    0, // No server_config
    0, // No server_merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
