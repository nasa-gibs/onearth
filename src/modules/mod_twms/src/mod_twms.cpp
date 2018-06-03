/*
 *
 * An OnEarth protocol module, converts a tWMS request to a M/L/R/C tile request
 * Lucian Plesea
 * (C) 2016
 *
 */

#include "mod_twms.h"
#include <receive_context.h>
#include <clocale>
#include <cmath>
#include <algorithm>

// Tokenize the URI parameters
static apr_table_t* tokenize_args(request_rec *r)
{
    apr_table_t *tab = apr_table_make(r->pool, 8);
    const char *val, *key, *data = r->args;
    for (data = r->args; data && *data && (val = ap_getword(r->pool, &data, '&'));)
        if (key = ap_getword(r->pool, &val, '='))
            apr_table_addn(tab, key, val);
    return tab;
}

// static const char *get_file_ext(request_rec *r, apr_table_t *args)
// {
//     const char *image_types[2][2] = {
//         {"image/jpeg", ".jpg"},
//         {"image/png", ".png"}
//     };

//     int i;
//     for (i=0; i<2; i++)
//         if (apr_strnatcasecmp(apr_table_get(args, "format"), image_types[i][0]) == 0)
//             return image_types[i][1];

//     return "";
// }

static const char *get_base_uri(request_rec *r)
{
    const char *uri = r->uri;
    int uri_len = strlen(uri);
    int i;
    for (i=0;i<uri_len; i++)
    {
        if (uri[uri_len-i] == '/') break;
    }
    return apr_pstrmemdup(r->pool, uri, uri_len-i);
}


static const char *add_date_to_uri(apr_pool_t *p, const char *source_str, const char *date_str)
{
    if (const char *datefield = ap_strstr(source_str, "${date}")) {
        const char *prefix = apr_pstrmemdup(p, source_str, datefield - source_str);
        return apr_pstrcat(p, prefix, date_str, datefield + strlen("${date}"), NULL);
    }
    return source_str;
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
    raster.n_levels = 2 + ilogb(std::max(level.height, level.width) - 1);
    raster.rsets = (struct rset *)apr_pcalloc(p, sizeof(rset) * raster.n_levels);

    // Populate rsets from the bottom, the way tile protcols count levels
    // These are MRF rsets, not all of them are visible
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
    const char *message = " incorrect bbox format, expects four comma separated C locale values";
    char *l;
    setlocale(LC_NUMERIC, "C");

    do { // Something to break out of
        bbox->xmin = strtod(line, &l); if (*l++ != ',') break;
        bbox->ymin = strtod(l, &l);    if (*l++ != ',') break;
        bbox->xmax = strtod(l, &l);    if (*l++ != ',') break;
        bbox->ymax = strtod(l, &l);
        message = NULL; // Success
    } while (false);

    setlocale(LC_NUMERIC, lcl);
    return message;
}

// Returns NULL if it worked as expected, returns a four integer value from "x y", "x y z" or "x y z c"
static const char *get_xyzc_size(struct sz *size, const char *value) {
    char *s;
    if (!value)
        return " values missing";
    size->x = apr_strtoi64(value, &s, 0);
    size->y = apr_strtoi64(s, &s, 0);
    size->c = 3;
    size->z = 1;
    if (errno == 0 && *s != NULL) { // Read optional third and fourth integers
        size->z = apr_strtoi64(s, &s, 0);
        if (*s != NULL)
            size->c = apr_strtoi64(s, &s, 0);
    } // Raster size is 4 params max
    if (errno != 0 || *s != NULL)
        return " incorrect format";
    return NULL;
}

static const char *ConfigRaster(apr_pool_t *p, apr_table_t *kvp, TiledRaster &raster)
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
    if (line)
        if (err_message = get_xyzc_size(&(raster.pagesize), line))
            return apr_pstrcat(p, "PageSize", err_message, NULL);

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
        if (err_message = getbbox(line, &raster.bbox))
            return apr_pstrcat(p, "BoundingBox", err_message, NULL);

    init_rsets(p, raster);
    return NULL;
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

static const char *set_config(cmd_parms *cmd, twms_conf *c, const char *src, const char *fname)
{
    c->cfg_filename_template = apr_pstrdup(cmd->pool, src);
    c->enabled = true;
    return NULL;
}

static apr_status_t get_config_for_layer(request_rec *r, twms_conf **cfg, const char *layer_name)
{
    char *err_message;
    const char *line;

    const char *cfg_filename = (*cfg)->cfg_filename_template;

    // Substitute layer name into the template for our config file
    if (const char *layer_field = ap_strstr(cfg_filename, "{layer}")) {
        const char *prefix = apr_pstrmemdup(r->pool, cfg_filename, layer_field - cfg_filename);
        cfg_filename = apr_pstrcat(r->pool, prefix, layer_name, layer_field + strlen("{layer}"), NULL);
    }

    // Start with the source configuration
    apr_table_t *kvp = read_pKVP_from_file(r->pool, cfg_filename, &err_message);
    if (NULL == kvp) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "Error opening config file: %s", cfg_filename);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    err_message = const_cast<char*>(ConfigRaster(r->pool, kvp, (*cfg)->raster));
    if (err_message) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "Error parsing config file: %s", cfg_filename);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    line = apr_table_get(kvp, "SourcePath");
    if (!line) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server,  "SourcePath directive missing in config file %s", cfg_filename);
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    (*cfg)->source = apr_pstrdup(r->pool, line);

    line = apr_table_get(kvp, "SourcePostfix");
    if (line)
        (*cfg)->postfix = apr_pstrdup(r->pool, line);

    return APR_SUCCESS;
}

// Allow for one or more RegExp guard
// One of them has to match if the request is to be considered
static const char *set_regexp(cmd_parms *cmd, twms_conf *c, const char *pattern)
{
    char *err_message = NULL;
    if (c->arr_rxp == 0)
        c->arr_rxp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t *));
    ap_regex_t **m = (ap_regex_t **)apr_array_push(c->arr_rxp);
    *m = ap_pregcomp(cmd->pool, pattern, 0);
    return (NULL != *m) ? NULL : "Bad regular expression";
}

static void *create_dir_config(apr_pool_t *p, char *path)
{
    twms_conf *c = reinterpret_cast<twms_conf *>(apr_pcalloc(p, sizeof(twms_conf)));
    c->doc_path = path;
    return c;
}

static bool our_request(request_rec *r) {
    if (r->method_number != M_GET) return false;
    if (!r->args) return false; // tWMS takes arguments

    twms_conf *cfg = static_cast<twms_conf *>ap_get_module_config(r->per_dir_config, &twms_module);
    if (!cfg->enabled) return false;

    if (cfg->arr_rxp) { // Check the guard regexps if they exist, matches agains URL
        char *url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;
        for (int i = 0; i < cfg->arr_rxp->nelts; i++) {
            ap_regex_t *m = APR_ARRAY_IDX(cfg->arr_rxp, i, ap_regex_t *);
            if (!ap_regexec(m, url_to_match, 0, NULL, 0)) return true; // Found
        }
    }
    return false;
}

//
// Are the three values in increasing order, usefule for checking that b is between a and c,
// especially useful for floating point types
//
template<typename T> bool ordered(const T &a, const T &b, const T &c) {
    return (a <= b && b <= c);
}

// Fills in sz and returns it if the bounding box matches a given tile, otherwise returns NULL
static sz *bbox_to_tile(const TiledRaster &raster, const bbox_t &bb, sz *tile) {
    // Tile size in real coordinates
    double resx = bb.xmax - bb.xmin;
    double dx = resx / raster.pagesize.x / 2;
    double resy = bb.ymax - bb.ymin;
    double dy = resy / raster.pagesize.y / 2;

    // Search for a resolution match
    for (int l = 0; l < raster.n_levels; l++) {
        const double rx = raster.rsets[l].rx * raster.pagesize.x; // tile resolution
        if (!ordered(resx - dx, rx, resx + dx)) continue;
        const double ry = raster.rsets[l].ry * raster.pagesize.y; // tile resolution
        if (!ordered(resy - dy, ry , resy + dy)) continue;
        // figure out the tile row and column
        // Casting truncates, add half pixel to avoid the fp noise
        tile->x = static_cast<apr_int64_t>((bb.xmin + dx - raster.bbox.xmin) / rx);
        tile->y = static_cast<apr_int64_t>((raster.bbox.ymax - bb.ymax + dy) / ry);

        // Check that the tile is within the box for this level
        if (tile->x < 0 || tile->x >= raster.rsets[l].width) return NULL;
        if (tile->y < 0 || tile->y >= raster.rsets[l].height) return NULL;

        // Check that the provided coordinates are within half pixel
        double xm = raster.bbox.xmin + tile->x * rx;
        if (!ordered(xm - dx, bb.xmin, xm + dx)) return NULL;
        double ym = raster.bbox.ymax - tile->y * ry;
        if (!ordered(ym - dy, bb.ymax, ym + dy)) return NULL;
        // Indeed, this is the right tile, is it within the level?

        // Adjust the level
        tile->l = l - raster.skip;
        return tile;
    }
    return NULL;
}

static int handler(request_rec *r)
{
    const char *message = NULL;

    if (!our_request(r)) 
        return DECLINED;
    apr_table_t *args = tokenize_args(r);
    
    if (const char *request = apr_table_get(args, "request")) {
        const char *lookup_uri = NULL;
        if (apr_strnatcasecmp(request, "GetCapabilities") == 0) {
            lookup_uri = ".lib/getCapabilities.xml";
        } else if (apr_strnatcasecmp(request, "GetTileService") == 0) {
            lookup_uri = ".lib/getTileService.xml";
        }
        if (lookup_uri) {
            ap_internal_redirect(apr_psprintf(r->pool, "%s/%s", get_base_uri(r), lookup_uri), r);
            return OK;
        }
    }

    const char *bb_string = apr_table_get(args, "bbox");

    // Missing the required bbox argument
    if (!bb_string) 
        return HTTP_BAD_REQUEST;
    // this should be picked up by the regexp, in which case the response will be HTTP_FORBIDDEN

    bbox_t bbox;
    message = getbbox(bb_string, &bbox);
    if (message != NULL) // Bounding box formatting error
        return HTTP_BAD_REQUEST;

    // Got the bounding box, need to figure out the tile request
    sz tile;
    
    // Use the passed-in layer name to get the configuration filename
    const char *layer_name = apr_table_get(args, "layers");
    if (!layer_name) return HTTP_BAD_REQUEST;

    twms_conf *base_cfg = static_cast<twms_conf *>ap_get_module_config(r->per_dir_config, &twms_module);

    twms_conf *cfg = (twms_conf *)apr_pcalloc(r->pool, sizeof(twms_conf));
    memcpy(cfg, base_cfg, sizeof(twms_conf));

    apr_status_t status = get_config_for_layer(r, &cfg, layer_name);
    if (status != APR_SUCCESS) return HTTP_BAD_REQUEST;

    // Get TIME and append it to the source URI if applicable
    const char *source = cfg->source;
    const char *time_str = apr_table_get(args, "time") ? apr_table_get(args, "time") : "default";
    source = add_date_to_uri(r->pool, cfg->source, time_str);

    // Convert to a source tile
    if (&tile != bbox_to_tile(cfg->raster, bbox, &tile))
        return HTTP_BAD_REQUEST;

    // The types and format below have to match
    unsigned int level  = static_cast<unsigned int>(tile.l);
    unsigned int row    = static_cast<unsigned int>(tile.y);
    unsigned int column = static_cast<unsigned int>(tile.x);

    const char *m_string = apr_table_get(args, "M"); // Extra dimension
    unsigned int m_val = 0;

    char *new_uri;
    if (m_string) { // We have an extra dimension
        m_val = static_cast<unsigned int>(apr_atoi64(m_string));
        new_uri = (cfg->postfix == NULL) ?
            apr_psprintf(r->pool, "%s/%u/%u/%u/%u" , source, m_val, level, row, column) :
            apr_psprintf(r->pool, "%s/%u/%u/%u/%u%s", source, m_val, level, row, column, cfg->postfix);
    }
    else {
        new_uri = (cfg->postfix == NULL) ?
            apr_psprintf(r->pool, "%s/%u/%u/%u", source, level, row, column) :
            apr_psprintf(r->pool, "%s/%u/%u/%u%s", source, level, row, column, cfg->postfix);
    }

    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server,"Requesting tile URI: %s", new_uri);
    ap_internal_redirect(new_uri, r);
    return OK; // Not sure what this does, because it was already handled
}

static void register_hooks(apr_pool_t *p) {
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

static const command_rec cmds[] = {
    AP_INIT_TAKE1(
    "tWMS_ConfigurationFile",
    (cmd_func)set_config, // Callback
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "TWMS configuration file"
    ),

    AP_INIT_TAKE1(
    "tWMS_RegExp",
    (cmd_func)set_regexp,
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Regular expression that the URL has to match.  At least one is required."),

    {NULL}
};

module AP_MODULE_DECLARE_DATA twms_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0,
    0,
    0,
    cmds,
    register_hooks
};
