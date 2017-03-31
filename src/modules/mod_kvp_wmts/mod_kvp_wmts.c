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

#include "mod_kvp_wmts.h"

// Returns 1 if string s ends with the ending string
//static int ends_with(const char *ending, const char *s) {
//    int ls = strlen(s);
//    int le = strlen(ending);
//    if (le > ls) return 0;
//    return NULL != strstr(s + ls - le, ending);
//}
//

const char *mime_ext_table[][2] = {
    {"image/jpeg", ".jpg"}, 
    {"image/png", ".png"}
};

const char *get_ext_for_mime(const char *mime_str) {
    int table_len = sizeof(mime_ext_table)/sizeof(mime_ext_table[0]);
    for(int i=0; i<table_len; i++) {
        if(!apr_strnatcasecmp(mime_ext_table[i][0], mime_str)) {
            return mime_ext_table[i][1];
        }
    }
    return NULL;
}

// Find first instance of char c in string, or null
const char *find_first(const char *s, char c) {
    while (*s && *s != c) s++;
    return s;
}

apr_table_t *tokenize_args(request_rec *r)
{
    apr_table_t *table = apr_table_make(r->pool, 4);
    const char *start = r->args;
    do {
        const char *end = find_first(start, '&');
        const char *equal = find_first(start, '=');
        if (*equal) { // found a key value pair
            char *key = apr_pstrndup(r->pool, start, equal - start);
            // Make all keys in the table lowercase
            for( ; *key; ++key) *key = tolower(*key);

            char *val = apr_pstrndup(r->pool, equal + 1, end - equal - 1);
            apr_table_addn(table, key, val);
        }
        start = *end ? end + 1 : end;
    } while (*start);
    return table;
}

// Returns true if a string exists in a list of strings.
int string_in(const char *search_str, const char **str_list, int list_length) {
    for(int i=0; i<list_length; i++) {
        if(apr_strnatcasecmp(search_str, str_list[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

static int send_the_file(request_rec *r, const char *filename, const char *type)
{
    static const char *fmt = "%s: %m";
    apr_status_t stat;
    apr_finfo_t info;
    stat = apr_stat(&info, filename, APR_FINFO_SIZE, r->pool);
    if (APR_SUCCESS != stat) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, stat);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    if (info.size > MAX_FILE_SIZE) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "File %s too large, max is %d", filename, MAX_FILE_SIZE);
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    void *buffer = apr_palloc(r->pool, (apr_size_t)info.size);

    if (!buffer) { // Good luck with this one
        ap_log_error(APLOG_MARK, APLOG_CRIT, 0, r->server, "Memory allocation failure");
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    apr_file_t *f;
    stat = apr_file_open(&f, filename, APR_FOPEN_READ | APR_FOPEN_BINARY, 0, r->pool);
    if (APR_SUCCESS != stat) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, stat);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    apr_size_t read_bytes = (apr_size_t)info.size;
    stat = apr_file_read(f, buffer, &read_bytes);
    if (APR_SUCCESS != stat) {
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, fmt, filename, stat);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    // Use applicaton/pjson type as a flag to look after the callback
    const char *callback = NULL;

    // Got the content, send it
    if (0 == apr_strnatcmp(type, "application/jsonp")) {
        if (r->args) // Pick up the callback if we have one
            callback = apr_table_get(tokenize_args(r), "callback");
        ap_set_content_type(r, "application/json"); // Set the type to plain json
    } else 
        ap_set_content_type(r, type);

    if (callback) {
        ap_set_content_length(r, read_bytes + strlen(callback) + 2);
        ap_rwrite(callback, strlen(callback), r);
        ap_rwrite("(", 1, r);
        ap_rwrite(buffer, read_bytes, r);
        ap_rwrite(")", 1, r);
        return OK;
    }

    ap_set_content_length(r, read_bytes);
    ap_rwrite(buffer, read_bytes, r);
    return OK; // Done
}
 
int url_matches_regex(request_rec *r) {
    sfim_conf *cfg = (sfim_conf *)ap_get_module_config(r->per_dir_config, &kvp_wmts_module);
    if (!cfg || cfg->matches == NULL) return DECLINED;
    // Match against the URL if args exist
    char * url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;
    for (int i = 0; i < cfg->matches->nelts; i++) {
        match m = APR_ARRAY_IDX(cfg->matches, i, match);
        // Returns 0 for a match
        if (ap_regexec(m.regexp, url_to_match, 0, NULL, 0))
            continue;
        // It did match
        return 1;
    }
    return 0;
}

const char* get_endpoint(request_rec *r) {
    sfim_conf *cfg = (sfim_conf *)ap_get_module_config(r->per_dir_config, &kvp_wmts_module);
    return cfg->endpoint;
}

static int handler(request_rec *r)
{
    // //STUFF FOR TESTING REGEX
    // const char* regex_str = "/somelayer(.*?)/";
    // ap_regex_t *regex = apr_palloc(r->pool, sizeof(ap_regex_t));
    // int comp = ap_regcomp(regex, regex_str, 0);
    // const char *test_str = "/somelayer2014/0/2/1";
    // ap_regmatch_t res[AP_MAX_REG_MATCH];
    // apr_size_t m = AP_MAX_REG_MATCH;
    // int result = ap_regexec(regex, test_str, m, res, 0);
    // char *dir_str;
    // apr_cpystrn(dir_str, test_str + res[1].rm_so, res[1].rm_eo - res[1].rm_so + 1);




    if (r->method_number != M_GET) return DECLINED; // Only GET requests
    if(!r->args) {
        return DECLINED;
    }
    if(!url_matches_regex(r)) {
        return DECLINED;
    }
    apr_table_t *args_table = tokenize_args(r);
    const char *service = apr_table_get(args_table, "service");
    if(!service || apr_strnatcasecmp(service, "WMTS") != 0) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *request = apr_table_get(args_table, "request");
    if(!request || apr_strnatcasecmp(request, "GetTile")) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *version = apr_table_get(args_table, "version");
    const char *allowed_versions[] = {"1.0.0", "1.1.0"};
    if(!version || !string_in(version, allowed_versions, sizeof(allowed_versions)/sizeof(allowed_versions[0]))) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *layer = apr_table_get(args_table, "layer");
    if(!layer) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *tilematrixset = apr_table_get(args_table, "tilematrixset");
    if(!tilematrixset) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *format = apr_table_get(args_table, "format");
    if(!format) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *req_ext = get_ext_for_mime(format);
    if(!req_ext) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    const char *matrix = apr_table_get(args_table, "tilematrix");
    if(!matrix) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *tilecol = apr_table_get(args_table, "tilecol");
    if(!tilecol) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *tilerow = apr_table_get(args_table, "tilerow");
    if(!tilerow) {
        return HTTP_INTERNAL_SERVER_ERROR;
    }
    const char *endpoint = get_endpoint(r);
    const char *req_template = "%s/%s/%s/%s/%s%s";
    const char *req_url = apr_psprintf(r->pool, req_template, endpoint, layer, matrix, tilerow, tilecol, req_ext);
    ap_internal_redirect(req_url, r);


    // int i;
    // if (r->method_number != M_GET) return DECLINED; // Only GET requests
    // sfim_conf *cfg = (sfim_conf *)ap_get_module_config(r->per_dir_config, &sfim_module);
    // if (!cfg || cfg->matches == NULL) return DECLINED;

    // // Match against the URL if args exist
    // char * url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;
    // for (i = 0; i < cfg->matches->nelts; i++) {
    //     match m = APR_ARRAY_IDX(cfg->matches, i, match);
    //     // Returns 0 for a match
    //     if (ap_regexec(m.regexp, url_to_match, 0, NULL, 0))
    //         continue;
    //     // It did match
    //     return send_the_file(r, m.filename, m.type);
    // }
    return OK;
}

// One directive per call, per folder
static const char *entry_set(cmd_parms *cmd, void *dconf, const char *regexp)
{
    sfim_conf *cfg = (sfim_conf *)dconf;
    if (cfg->matches == NULL) // Initialize the table if not already done
        cfg->matches = apr_array_make(cmd->pool, 2, sizeof(match));

    // compile the regexp first
    match *m = (match *)apr_array_push(cfg->matches);

    m->regexp = apr_palloc(cmd->pool, sizeof(ap_regex_t));
    int error = ap_regcomp(m->regexp, regexp, 0);
    if (error) {
        int msize = 2048;
        char *message = apr_palloc(cmd->temp_pool, msize);
        ap_regerror(error, m->regexp, message, msize);
        return apr_psprintf(cmd->pool, "SFIM Regexp failed %s", message);
    }

    return NULL;
}

static const char *set_endpoint(cmd_parms *cmd, void *dconf, const char *endpoint)
{
    sfim_conf *cfg = (sfim_conf *)dconf;
    cfg->endpoint = endpoint;
    return NULL;
}

static void *create_dir_config(apr_pool_t *p, char *dummy)
{
    sfim_conf *c =
        (sfim_conf *)apr_pcalloc(p, sizeof(sfim_conf));
    return c;
}

static void register_hooks(apr_pool_t *p)

{
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

static const command_rec cmds[] = 
{
    AP_INIT_TAKE1(
        "KVP_WMTS_RegExp",
        entry_set, // Callback
        0, // Self pass argument
        ACCESS_CONF,
        "The file to send and the regexp to match against the URI"
    ),
    AP_INIT_TAKE1(
        "KVP_WMTS_Endpoint",
        set_endpoint,
        0,
        ACCESS_CONF,
        "Endpoint to redirect WMTS queries to"
    ),
    {NULL}
};

module AP_MODULE_DECLARE_DATA kvp_wmts_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge, no inheritance
    0, // No server_config
    0, // No server_merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
