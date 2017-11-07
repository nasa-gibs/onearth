/*
* An OnEarth module that serves tiles from an MRF
* Lucian Plesea
* (C) 2016-2017
*/

#include "mod_mrf.h"
#include "receive_context.h"

#include <algorithm>
#include <cmath>

using namespace std;

static void *create_dir_config(apr_pool_t *p, char *dummy)
{
    mrf_conf *c =
        (mrf_conf *)apr_pcalloc(p, sizeof(mrf_conf));
    return c;
}

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

// Returns a table read from a file, or NULL and an error message
static apr_table_t *read_pKVP_from_file(apr_pool_t *pool, const char *fname, char **err_message)

{
    // Should parse it here and initialize the configuration structure
    ap_configfile_t *cfg_file;
    apr_status_t s = ap_pcfg_openfile(&cfg_file, pool, fname);

    if (APR_SUCCESS != s) { // %pm means print status error string
        *err_message = apr_psprintf(pool, "%s - %pm", fname, &s);
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
        *err_message = apr_psprintf(pool, "%s lines should be smaller than %d", fname, MAX_STRING_LEN);
        return NULL;
    }

    return table;
}

// Returns NULL if it worked as expected, returns a four integer value from "x y", "x y z" or "x y z c"
static char *get_xyzc_size(apr_pool_t *p, struct sz *size, const char *value, const char*err_prefix) {
    char *s;
    if (!value)
        return apr_psprintf(p, "%s directive missing", err_prefix);
    size->x = apr_strtoi64(value, &s, 0);
    size->y = apr_strtoi64(s, &s, 0);
    size->c = 3;
    size->z = 1;
    if (errno == 0 && *s) { // Read optional third and fourth integers
        size->z = apr_strtoi64(s, &s, 0);
        if (*s)
            size->c = apr_strtoi64(s, &s, 0);
    } // Raster size is 4 params max
    if (errno || *s)
        return apr_psprintf(p, "%s incorrect", err_prefix);
    return NULL;
}

// Converts a 64bit value into 13 trigesimal chars
static void uint64tobase32(apr_uint64_t value, char *buffer, int flag = 0) {
    static char b32digits[] = "0123456789abcdefghijklmnopqrstuv";
    // From the bottom up
    buffer[13] = 0; // End of string marker
    for (int i = 0; i < 12; i++, value >>= 5)
        buffer[12 - i] = b32digits[value & 0x1f];
    // First char holds the empty tile flag
    if (flag) flag = 0x10; // Making sure it has the right value
    buffer[0] = b32digits[flag | value];
}

// Return the value from a base 32 character
// Returns a negative value if char is not a valid base32 char
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
    while (*s == '"') s++; // Skip initial quotes
    *flag = (b32(*s) >> 4) & 1; // Pick up the flag from bit 5
    for (int v = b32(*s++) & 0xf; v >= 0; v = b32(*s++))
        value = (value << 5) + v;
    return value;
}

static void mrf_init(apr_pool_t *p, mrf_conf *c) {
    struct rset level;
    level.width = static_cast<int>(1 + (c->size.x - 1) / c->pagesize.x);
    level.height = static_cast<int>(1 + (c->size.y - 1) / c->pagesize.y);
    level.offset = 0;
    // How many levels do we have
    c->n_levels = 2 + ilogb(max(level.height, level.width) - 1);
    c->rsets = (struct rset *)apr_pcalloc(p, sizeof(rset) * c->n_levels);

    // Populate rsets from the bottom, the way tile protcols count levels
    // These are MRF rsets, not all of them are visible
    struct rset *r = c->rsets + c->n_levels - 1;
    for (int i = 0; i < c->n_levels; i++) {
        *r-- = level;
        // Prepare for the next level, assuming powers of two
        level.offset += sizeof(TIdx) * level.width * level.height * c->size.z;
        level.width = 1 + (level.width - 1) / 2;
        level.height = 1 + (level.height - 1) / 2;
    }
    // MRF has one tile at the top
    ap_assert(c->rsets->height == 1 && c->rsets->width == 1);
}

// Allow for one or more RegExp guard
// If present, at least one of them has to match the URL
static const char *set_regexp(cmd_parms *cmd, mrf_conf *c, const char *pattern)
{
    char *err_message = NULL;
    if (c->arr_rxp == 0)
        c->arr_rxp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t *));
    ap_regex_t **m = (ap_regex_t **)apr_array_push(c->arr_rxp);
    *m = ap_pregcomp(cmd->pool, pattern, 0);
    return (NULL != *m) ? NULL : "Bad regular expression";
}

/*
 Read the configuration file, which is a key-value text file, with one key per line
 comment lines that start with #
 empty lines are allowed, as well as continued lines if the first one ends with \
 However, every line is limited to the Apache max string size, defaults to 8192 chars

 Unknown keys, or keys that are misspelled are silently ignored
 Keys are not case sensitive, but values are
 Keys and values are space separated.  The last value per line, if it is a string, may contain spaces

 Supported keys:

 Size X Y <Z> <C>
 Mandatory, the size in pixels of the input MRF.  Z defaults to 1 and C defaults to 3 (usually not meaningful)

 PageSize X Y <1> <C>
 Optional, the pagesize in pixels.  X and Y default to 512. Z has to be 1 if C is provided, which has to match the C value from size

 DataFile string
 Mandatory, the data file of the MRF.

 IndexFile string
 Optional, The index file name.
 If not provided it uses the data file name if its extension is not three letters.
 Otherwise it uses the datafile name with the extension changed to .idx

 MimeType string
 Optional.  Defaults to autodetect

 EmptyTile <Size> <Offset> <FileName>
 Optional.  By default it ignores the request if a tile is missing
 First number is assumed to be the size, second is offset
 If filename is not provided, it uses the data file name

 SkippedLevels <N>
 Optional, how many levels to ignore, at the top of the MRF pyramid
 For example a GCS pyramid will have to skip the one tile level, so this should be 1

 Redirect
 Instead of reading from the data file, make range requests to this URI

 ETagSeed base32_string
 Optional, 64 bits in base32 digits.  Defaults to 0
 The empty tile ETag will be this value but bit 64 (65th bit) is set. All the other tiles
 have ETags that depend on this one and bit 64 is zero
 */

static const char *mrf_file_set(cmd_parms *cmd, void *dconf, const char *arg)
{
    ap_assert(sizeof(apr_off_t) == 8);
    mrf_conf *c = (mrf_conf *)dconf;
    char *err_message;
    apr_table_t *kvp = read_pKVP_from_file(cmd->temp_pool, arg, &err_message);
    if (NULL == kvp) return err_message;

    // Got the parsed kvp table, parse the configuration items
    const char *line;
    char *err_prefix;

    line = apr_table_get(kvp, "Size");
    if (!line)
        return apr_psprintf(cmd->temp_pool, "%s Size directive is mandatory", arg);
    err_prefix = apr_psprintf(cmd->temp_pool, "%s Size", arg);
    err_message = get_xyzc_size(cmd->temp_pool, &(c->size), line, err_prefix);
    if (err_message) return err_message;

    // PageSize is optional, use reasonable defaults
    c->pagesize.x = c->pagesize.z = 512;
    c->pagesize.c = c->size.c;
    c->pagesize.z = 1;
    line = apr_table_get(kvp, "PageSize");
    if (line) {
        err_prefix = apr_psprintf(cmd->temp_pool, "%s PageSize", arg);
        err_message = get_xyzc_size(cmd->temp_pool, &(c->pagesize), line, err_prefix);
        if (err_message) return err_message;
    }
    if (c->pagesize.c != c->size.c || c->pagesize.z != 1)
        return apr_psprintf(cmd->temp_pool, "%s PageSize has invalid parameters", arg);

    // Initialize the run-time structures
    mrf_init(cmd->pool, c);

    // The DataFile is optional, if provided the index file is the same thing with the extension removed
    line = apr_table_get(kvp, "DataFile");

    // Data and index in the same location by default
    if (line) { // If the data file has a three letter extension, change it to idx for the index
        c->datafname = apr_pstrdup(cmd->pool, line);
        c->idxfname = apr_pstrdup(cmd->pool, line);
        char *last;
        char *token = apr_strtok(c->idxfname, ".", &last); // strtok destroys the idxfile
        while (*last != 0 && token != NULL)
            token = apr_strtok(NULL, ".", &last);
        memcpy(c->idxfname, c->datafname, strlen(c->datafname)); // Get a new copy
        if (token != NULL && strlen(token) == 3)
            memcpy(token, "idx", 3);
    }

    // Index file can also be provided
    line = apr_table_get(kvp, "IndexFile");
    if (line)
        c->idxfname = apr_pstrdup(cmd->pool, line);

    // Mime type is autodetected if not provided
    line = apr_table_get(kvp, "MimeType");
    if (line)
        c->mime_type = apr_pstrdup(cmd->pool, line);

    // Skip levels, from the top of the MRF
    line = apr_table_get(kvp, "SkippedLevels");
    if (line)
        c->skip_levels = atoi(line);

    // If an emtpy tile is not provided, it falls through
    // If provided, it has an optional size and offset followed by file name which defaults to datafile
    // read the empty tile
    const char *efname = c->datafname; // Default file name is data file
    line = apr_table_get(kvp, "EmptyTile");
    if (line) {
        char *last;
        // Try to read a figure first
        c->esize = apr_strtoi64(line, &last, 0);

        // If that worked, try to get an offset too
        if (last != line)
            apr_strtoff(&(c->eoffset), last, &last, 0);

        // If there is anything left
        while (*last && isspace(*last)) last++;
        if (*last != 0)
            efname = last;
    }

    line = apr_table_get(kvp, "Redirect");
    if (line)
        c->redirect = apr_pstrdup(cmd->pool, line);

    // If we're provided a file name or a size, pre-read the empty tile in the
    if (efname && (c->datafname == NULL || apr_strnatcmp(c->datafname, efname) || c->esize))
    {
        apr_file_t *efile;
        apr_off_t offset = c->eoffset;
        apr_status_t stat;

        // Use the temp pool for the file open, it will close it for us
        if (!c->esize) { // Don't know the size, get it from the file
            apr_finfo_t finfo;
            stat = apr_stat(&finfo, efname, APR_FINFO_CSIZE, cmd->temp_pool);
            if (APR_SUCCESS != stat)
                return apr_psprintf(cmd->pool, "Can't stat %s %pm", efname, stat);
            c->esize = (apr_uint64_t)finfo.csize;
        }

        stat = apr_file_open(&efile, efname, APR_FOPEN_READ | APR_FOPEN_BINARY, 0, cmd->temp_pool);
        if (APR_SUCCESS != stat)
            return apr_psprintf(cmd->pool, "Can't open empty file %s, loaded from %s: %pm",
            efname, arg, stat);
        c->empty = (apr_uint32_t *)apr_palloc(cmd->pool, static_cast<apr_size_t>(c->esize));
        stat = apr_file_seek(efile, APR_SET, &offset);
        if (APR_SUCCESS != stat)
            return apr_psprintf(cmd->pool, "Can't seek empty tile %s: %pm", efname, stat);
        apr_size_t size = (apr_size_t)c->esize;
        stat = apr_file_read(efile, c->empty, &size);
        if (APR_SUCCESS != stat)
            return apr_psprintf(cmd->pool, "Can't read from %s, loaded from %s: %pm",
            efname, arg, stat);
        apr_file_close(efile);
    }

    line = apr_table_get(kvp, "ETagSeed");
    // Ignore the flag
    int flag;
    c->seed = line ? base32decode(line, &flag) : 0;
    // Set the missing tile etag, with the extra bit set
    uint64tobase32(c->seed, c->eETag, 1);
    c->enabled = 1;
    return NULL;
}

static int etag_matches(request_rec *r, const char *ETag) {
    const char *ETagIn = apr_table_get(r->headers_in, "If-None-Match");
    return ETagIn != 0 && strstr(ETagIn, ETag);
}

static int send_image(request_rec *r, apr_uint32_t *buffer, apr_size_t size)
{
    mrf_conf *cfg = (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        ? (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        : (mrf_conf *)ap_get_module_config(r->per_dir_config, &mrf_module);
    if (cfg->mime_type)
        ap_set_content_type(r, cfg->mime_type);
    else
        switch (hton32(*buffer)) {
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
    if (GZIP_SIG == hton32(*buffer))
        apr_table_setn(r->headers_out, "Content-Encoding", "gzip");

    // TODO: Set headers, as chosen by user
    ap_set_content_length(r, size);
    ap_rwrite(buffer, size, r);
    return OK;
}

// Returns the empty tile if defined
static int send_empty_tile(request_rec *r) {
    mrf_conf *cfg = (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        ? (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        : (mrf_conf *)ap_get_module_config(r->per_dir_config, &mrf_module);
    if (etag_matches(r, cfg->eETag)) {
        apr_table_setn(r->headers_out, "ETag", cfg->eETag);
        return HTTP_NOT_MODIFIED;
    }

    if (!cfg->empty) return DECLINED; // Passthrough
    return send_image(r, cfg->empty, static_cast<apr_size_t>(cfg->esize));
}

// An open file handle and the matching file name, to be used as a note
struct file_note {
    const char *name;
    apr_file_t *pfh;
};

static const apr_int32_t open_flags = APR_FOPEN_READ | APR_FOPEN_BINARY | APR_FOPEN_LARGEFILE;

/*
 * Open or retrieve an connection cached file.
 */
static apr_status_t open_connection_file(request_rec *r, apr_file_t **ppfh, const char *name,
    apr_int32_t flags = open_flags, const char *note_name = "MRF_INDEX_FILE")

{
    apr_table_t *conn_notes = r->connection->notes;

    // Try to pick it up from the connection notes
    file_note *fn = (file_note *) apr_table_get(conn_notes, note_name);
    if ((fn != NULL) && !apr_strnatcmp(name, fn->name)) { // Match, set file and return
        *ppfh = fn->pfh;
        return APR_SUCCESS;
    }

    // Use the connection pool for the note and file, to ensure it gets closed with the connection
    apr_pool_t *pool = r->connection->pool;

    if (fn != NULL) { // We have an file note but it is not the right file
        apr_table_unset(conn_notes, note_name); // Unhook the existing note
        apr_file_close(fn->pfh); // Close the existing file
    }
    else { // no previous note, allocate a clean one
        fn = (file_note *)apr_palloc(pool, sizeof(file_note));
    }

    apr_status_t stat = apr_file_open(ppfh, name, flags, 0, pool);
    if (stat != APR_SUCCESS) 
        return stat;

    // Fill the note and hook it up, then return
    fn->pfh = *ppfh;
    fn->name = apr_pstrdup(pool, name); // The old string will persist until cleaned by the pool
    apr_table_setn(conn_notes, note_name, (const char *) fn);
    return APR_SUCCESS;
}

#define open_index_file open_connection_file

// Open data file optimized for random access if possible
static apr_status_t open_data_file(request_rec *r, apr_file_t **ppfh, const char *name)
{
    static const char data_note_name[] = "MRF_DATA_FILE";

#if defined(APR_FOPEN_RANDOM)
    // apr has portable support for random access to files
    return open_connection_file(r, ppfh, name, open_flags | APR_FOPEN_RANDOM, data_note_name);
#else

    apr_status_t stat = open_connection_file(r, ppfh, name, open_flags, data_note_name);

#if !defined(POSIX_FADV_RANDOM)
    return stat;

#else // last chance, turn random flag on if supported
    apr_os_file_t fd;
    if (APR_SUCCESS == apr_os_file_get(&fd, *ppfh))
        posix_fadvise(static_cast<int>(fd), 0, 0, POSIX_FADV_RANDOM);
    return stat;
#endif
#endif // APR_FOPEN_RANDOM
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

static bool our_request(request_rec *r, mrf_conf *cfg) {
    if (r->method_number != M_GET || cfg->arr_rxp == NULL)
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
    // Only get and no arguments
    if (r->args) return DECLINED; // Don't accept arguments

    mrf_conf *cfg = (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        ? (mrf_conf *)ap_get_module_config(r->request_config, &mrf_module)
        : (mrf_conf *)ap_get_module_config(r->per_dir_config, &mrf_module);
    if (!cfg->enabled || !our_request(r, cfg)) return DECLINED;

    apr_array_header_t *tokens = tokenize(r->pool, r->uri, '/');
    if (tokens->nelts < 3) return DECLINED; // At least Level Row Column

    // Use a xyzc structure, with c being the level
    // Input order is M/Level/Row/Column, with M being optional
    sz tile;
    memset(&tile, 0, sizeof(tile));

    // Need at least three numerical arguments
    tile.x = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.y = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    tile.l = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);

    // We can ignore the error on this one, defaults to zero
    // The parameter before the level can't start with a digit for an extra-dimensional MRF
    if (cfg->size.z != 1 && tokens->nelts)
        tile.z = apr_atoi64(*(char **)apr_array_pop(tokens));

    // Don't allow access to levels less than zero, send the empty tile instead
    if (tile.l < 0)
        return send_empty_tile(r);

    tile.l += cfg->skip_levels;
    // Check for bad requests, outside of the defined bounds
    REQ_ERR_IF(tile.l >= cfg->n_levels);
    rset *level = cfg->rsets + tile.l;
    REQ_ERR_IF(tile.x >= level->width || tile.y >= level->height);

    // Offset of the index entry for this tile
    apr_off_t tidx_offset = level->offset +
        sizeof(TIdx) * (tile.x + level->width * (tile.z * level->height + tile.y));

    apr_file_t *idxf, *dataf;
    SERR_IF(open_index_file(r, &idxf, cfg->idxfname),
        apr_psprintf(r->pool, "Can't open %s", cfg->idxfname));
    TIdx index;
    apr_size_t read_size = sizeof(TIdx);

    SERR_IF(apr_file_seek(idxf, APR_SET, &tidx_offset) 
        || apr_file_read(idxf, &index, &read_size) 
        || read_size != sizeof(TIdx),
        apr_psprintf(r->pool, "Tile index doesn't exist in %s", cfg->idxfname));

    // MRF index record is in network order
    index.size = ntoh64(index.size);
    index.offset = ntoh64(index.offset);

    if (index.size < 4) // Need at least four bytes for signature check
        return send_empty_tile(r);

    if (MAX_TILE_SIZE < index.size) { // Tile is too large, log and send error code
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "Tile too large in %s", cfg->idxfname);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    // Check for conditional ETag here, no need to open the data file
    char ETag[16];
    // Try to distribute the bits a bit to generate an ETag
    uint64tobase32(cfg->seed ^ (index.size << 40) ^ index.offset, ETag);
    if (etag_matches(r, ETag)) {
        apr_table_set(r->headers_out, "ETag", ETag);
        return HTTP_NOT_MODIFIED;
    }

    // Now for the data part
    if (!cfg->datafname && !cfg->redirect)
        SERR_IF(true, apr_psprintf(r->pool, "No data file configured for %s", r->uri));

    apr_uint32_t *buffer = static_cast<apr_uint32_t *>(
        apr_palloc(r->pool, static_cast<apr_size_t>(index.size)));

    if (cfg->redirect) {
        // TODO: S3 authorized requests
        ap_filter_rec_t *receive_filter = ap_get_output_filter_handle("Receive");
        SERR_IF(!receive_filter, "Redirect needs mod_receive to be available");

        // Get a buffer for the received image
        receive_ctx rctx;
        rctx.buffer = reinterpret_cast<char *>(buffer);
        rctx.maxsize = static_cast<int>(index.size);
        rctx.size = 0;

        ap_filter_t *rf = ap_add_output_filter_handle(receive_filter, &rctx, r, r->connection);
        request_rec *sr = ap_sub_req_lookup_uri(cfg->redirect, r, r->output_filters);

        // Data file is on a remote site a range request redirect with a range header
        static const char *rfmt = "bytes=%" APR_UINT64_T_FMT "-%" APR_UINT64_T_FMT;
        char *Range = apr_psprintf(r->pool, rfmt, index.offset, index.offset + index.size);
        apr_table_setn(sr->headers_in, "Range", Range);
        int status = ap_run_sub_req(sr);
        ap_remove_output_filter(rf);

        if (status != APR_SUCCESS || sr->status != HTTP_PARTIAL_CONTENT 
            || rctx.size != static_cast<int>(index.size)) {
            ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Can't fetch data from %s", cfg->redirect);
            return HTTP_SERVICE_UNAVAILABLE;
        }
        apr_table_clear(r->headers_out);
    }
    else
    { // Read from a local file
        SERR_IF(open_data_file(r, &dataf, cfg->datafname),
            apr_psprintf(r->pool, "Can't open %s", cfg->datafname));

        // We got the tile index, and is not empty
        SERR_IF(!buffer,
            "Memory allocation error in mod_mrf");
        SERR_IF(apr_file_seek(dataf, APR_SET, (apr_off_t *)&index.offset),
            apr_psprintf(r->pool, "Seek error in %s", cfg->datafname));
        read_size = static_cast<apr_size_t>(index.size);
        SERR_IF(apr_file_read(dataf, buffer, &read_size) || read_size != index.size,
            apr_psprintf(r->pool, "Can't read from %s", cfg->datafname));
    }

    // Looks fine, set the outgoing etag and then the image
    apr_table_set(r->headers_out, "ETag", ETag);
    return send_image(r, buffer, static_cast<apr_size_t>(index.size));
}

static const command_rec mrf_cmds[] =
{
    AP_INIT_FLAG(
    "MRF",
    CMD_FUNC ap_set_flag_slot,
    (void *)APR_OFFSETOF(mrf_conf, enabled),
    ACCESS_CONF,
    "mod_mrf enable, defaults to on if configuration is provided"
    ),

    AP_INIT_TAKE1(
    "MRF_ConfigurationFile",
    CMD_FUNC mrf_file_set, // Callback
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "The configuration file for this module"
    ),

    AP_INIT_TAKE1(
    "MRF_RegExp",
    (cmd_func)set_regexp,
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Regular expression that the URL has to match.  At least one is required."
    ),

    { NULL }
};


// Return OK or DECLINED, anything else is error
//static int check_config(apr_pool_t *pconf, apr_pool_t *plog, apr_pool_t *ptemp, server_rec *server)
//{
//    return DECLINED;
    // This gets called once for the whole server, it would have to check the configuration for every folder
//}

static void mrf_register_hooks(apr_pool_t *p)

{
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST);
    //    ap_hook_check_config(check_config, NULL, NULL, APR_HOOK_MIDDLE);
}

module AP_MODULE_DECLARE_DATA mrf_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge
    0, // No server_config
    0, // No server_merge
    mrf_cmds, // configuration directives
    mrf_register_hooks // processing hooks
};
