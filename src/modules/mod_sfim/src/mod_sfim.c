/*
* An OnEarth module, sends a static file if the request matches a regexp
* Lucian Plesea
* (C) 2016
*/

#include <apr.h>
#include <httpd.h>
#include <http_config.h>
#include <http_log.h>
#include <http_protocol.h>
#include <apr_tables.h>
#include <apr_strings.h>
#include <ap_regex.h>

#include "mod_sfim.h"

#define CALLBACK_REGEXP "^[a-zA-Z][0-9a-zA-Z_$.]*$"

static int is_absolute(const char *s) {
    if (s == NULL) return 0;
    int len = strlen(s);
    return ((len && s[0] == '/') || (len > 1 && s[1] == ':'));
}

// Find first instance of char c in string, or null
static const char *find_first(const char *s, char c) {
    while (s && *s && *s != c) 
        s++;
    return s;
}

static apr_table_t *tokenize_args(request_rec *r)
{
    apr_table_t *table = apr_table_make(r->pool, 4);
    const char *start = r->args;
    do {
        const char *end = find_first(start, '&');
        const char *equal = find_first(start, '=');
        if (*equal) { // found a key value pair
            char *key = apr_pstrndup(r->pool, start, equal - start);
            char *val = apr_pstrndup(r->pool, equal + 1, end - equal - 1);
            apr_table_addn(table, key, val);
        }
        start = *end ? end + 1 : end;
    } while (*start);
    return table;
}

static int send_the_file(request_rec *r, const char *filename, const char *type)
{
    sfim_conf *cfg = (sfim_conf *)ap_get_module_config(r->per_dir_config, &sfim_module);
    static const char *fmt = "%s: %pm";
    apr_status_t stat;
    apr_finfo_t info;
    apr_size_t size;
    apr_size_t sent = 0;

    stat = apr_stat(&info, filename, APR_FINFO_SIZE, r->pool);

    if (APR_SUCCESS != stat) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, &stat);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    size = (apr_size_t) ((info.size > MAX_FILE_SIZE) ? MAX_FILE_SIZE : info.size);

    void *buffer = apr_palloc(r->pool, size);
    if (!buffer) { // Good luck with this one
        ap_log_error(APLOG_MARK, APLOG_CRIT, 0, r->server, "Memory allocation failure");
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    apr_file_t *f;
    stat = apr_file_open(&f, filename, APR_FOPEN_READ | APR_FOPEN_BINARY, 0, r->pool);
    if (APR_SUCCESS != stat) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, &stat);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    // Use applicaton/pjson type as a flag to look after the callback
    const char *callback = NULL;

    // Got the content, send it
    if (0 == apr_strnatcmp(type, "application/jsonp")) {
        ap_set_content_type(r, "application/json"); // Set the type to plain json
        if (r->args) // Pick up the callback if we have one
            callback = apr_table_get(tokenize_args(r), "callback");

        // Only use the callback if it matches the callback regexp
        if (callback && ap_regexec(cfg->cbackregx, callback, 0, NULL, 0))
            callback = NULL;
    }
    else
        ap_set_content_type(r, type);

    apr_off_t cl = info.size;
    if (callback)
        cl += strlen(callback) + 2;
    ap_set_content_length(r, cl);

    if (callback) {
        ap_rwrite(callback, strlen(callback), r);
        ap_rwrite("(", 1, r);
    }

    while (sent != (apr_size_t)info.size) {
        apr_size_t read_bytes = size;
        stat = apr_file_read(f, buffer, &read_bytes);

        if (APR_SUCCESS != stat || size != read_bytes) {
            ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, &stat);
            return HTTP_INTERNAL_SERVER_ERROR;
        }

        ap_rwrite(buffer, read_bytes, r);
        sent += read_bytes;
        if (sent + size > info.size)
            size = info.size - sent;
    }

    if (callback)
        ap_rwrite(")", 1, r);

    return OK; // Done
}
 

static int handler(request_rec *r)
{
    int i;
    if (r->method_number != M_GET) return DECLINED; // Only GET requests
    sfim_conf *cfg = (sfim_conf *)ap_get_module_config(r->per_dir_config, &sfim_module);
    if (!cfg || cfg->matches == NULL) return DECLINED;

    // Match against the URL if args exist
    char * url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;

    for (i = 0; i < cfg->matches->nelts; i++) {
        match m = APR_ARRAY_IDX(cfg->matches, i, match);
        // Returns 0 for a match
        if (ap_regexec(m.regx, url_to_match, 0, NULL, 0))
            continue;
        // It did match
        return send_the_file(r, m.filename, m.type);
    }

    return DECLINED;
}

// One directive per call, per folder
static const char *entry_set(cmd_parms *cmd, void *dconf,
    const char *filename, const char *regexp, const char *type)
{
    sfim_conf *cfg = (sfim_conf *)dconf;
    if (cfg->matches == NULL) {
        // Initialize the table
        cfg->matches = apr_array_make(cmd->pool, 2, sizeof(match));
        // Initialize the callback regexp
        cfg->cbackregx = ap_pregcomp(cmd->pool, CALLBACK_REGEXP, 0);
    }

    // compile the regexp first
    match *m = (match *)apr_array_push(cfg->matches);
    m->regx = ap_pregcomp(cmd->pool, regexp, 0);
    if (m->regx == NULL)
        return "Bad regexp";

    m->filename = is_absolute(filename) ? 
        apr_pstrdup(cmd->pool, filename) : apr_pstrcat(cmd->pool, cmd->path, filename, NULL);

    m->type = apr_pstrdup(cmd->pool, type);
    return NULL;
}

static void *create_dir_config(apr_pool_t *p, char *unused)
{
    return apr_pcalloc(p, sizeof(sfim_conf));
}

static void register_hooks(apr_pool_t *p)

{
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

static const command_rec cmds[] = 
{
    AP_INIT_TAKE3(
        "SendFileIfMatch",
        entry_set, // Callback
        0, // Self pass argument
        ACCESS_CONF,
        "The file to send and the regexp to match against the URI"
    ),
    {NULL}
};

module AP_MODULE_DECLARE_DATA sfim_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge, no inheritance
    0, // No server_config
    0, // No server_merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
