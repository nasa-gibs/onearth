#include <apr.h>
#include <httpd.h>
#include <http_config.h>
#include <http_log.h>
#include <http_protocol.h>
#include <apr_tables.h>
#include <apr_strings.h>
#include <ap_regex.h>

#include <luajit-2.0/lua.h>
#include <luajit-2.0/lauxlib.h>
#include <luajit-2.0/lualib.h>

#include <jansson.h>

#include "mod_m_lookup.h"

// Tokenize a string into an array
static apr_array_header_t* tokenize(apr_pool_t *p, const char *s, char sep)
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

static int handler(request_rec *r)
{
    m_lookup_conf *cfg = (m_lookup_conf *)ap_get_module_config(r->per_dir_config, &m_lookup_module);
    if (!cfg) return DECLINED;

    if (cfg->regexp) { // Check the guard regexps if they exist, matches against URL
        int i;
        char * url_to_match = r->args ? apr_pstrcat(r->pool, r->uri, "?", r->args, NULL) : r->uri;
        for (i = 0; i < cfg->regexp->nelts; i++) {
            ap_regex_t *m = &APR_ARRAY_IDX(cfg->regexp, i, ap_regex_t);
            if (ap_regexec(m, url_to_match, 0, NULL, 0)) continue; // Not matched
            break;
        }
        if (i == cfg->regexp->nelts) // No match found
            return DECLINED;
    }

    apr_array_header_t *tokens = tokenize(r->pool, r->uri, '/');
    if (tokens->nelts < 5) return DECLINED; // At least Level Row Column TMS Time Layer

    // Get tile parameters from request
    int col = apr_atoi64(*(char **)apr_array_pop(tokens));
    int row = apr_atoi64(*(char **)apr_array_pop(tokens));
    int matrix = apr_atoi64(*(char **)apr_array_pop(tokens));
    const char *tile_matrix_set = *(const char **)apr_array_pop(tokens);
    const char *m_value = *(const char **)apr_array_pop(tokens);
    const char *layer_name = *(const char **)apr_array_pop(tokens);

    lua_State *L = luaL_newstate();
    luaL_openlibs(L); 
    
    if (luaL_loadbuffer(L, cfg->lookup_script, (size_t)cfg->lookup_script_len, NULL) ||
        lua_pcall(L, 0, 0, 0))
    {
        const char *err_msg = apr_psprintf(r->pool, "Error initializing m-lookup Lua script: %s", lua_tostring(L, -1));
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, err_msg);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    lua_getglobal(L, "getZ"); // get z-finding function

    // Load in the arguments to the lua function
    lua_pushstring(L, layer_name);
    lua_pushstring(L, m_value);
    lua_pushstring(L, tile_matrix_set);
    lua_pushnumber(L, matrix);
    lua_pushnumber(L, row);
    lua_pushnumber(L, col);

    // Call function and handle execution errors
    if (lua_pcall(L, 6, 2, 0))
    {
        const char *err_msg = apr_psprintf(r->pool, "Error running m-lookup Lua script: %s", lua_tostring(L, -1));
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, err_msg);
        return HTTP_INTERNAL_SERVER_ERROR;
    }

    if (!lua_toboolean(L, -2))
    {
        const char *err_msg = lua_tostring(L, -1);
        ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, err_msg);
    }
    const char *zidx = lua_tostring(L, -1);

    // Handle z-index service requests (like from mod_oems)
    if (cfg->lookup_service_regexp && !ap_regexec(cfg->lookup_service_regexp, r->uri, 0, NULL, 0)) {
        json_t *json_out_obj = json_object();

        json_t *z_out_string = json_string(zidx);
        json_object_set(json_out_obj, "z-index", z_out_string);
        const char *out_string = json_dumps(json_out_obj, JSON_COMPACT);

        ap_set_content_type(r, "application/json");
        ap_set_content_length(r, strlen(out_string) * sizeof(char));
        ap_rwrite(out_string, strlen(out_string) * sizeof(char), r);

        return OK;
    }

    const char *redirect_url = apr_psprintf(r->pool, "%s/%s/%s/%s/%d/%d/%d",
                                                     cfg->endpoint, 
                                                     layer_name,
                                                     zidx,
                                                     tile_matrix_set,
                                                     matrix,
                                                     row,
                                                     col
                                                     );

    // m_value = "2012-11-31T16:00:00Z";

    // struct tm *date = apr_pcalloc(r->pool, sizeof(* date));
    // if (!strptime(m_value, "%Y-%m-%dT%H:%M:%S", &date))
    // {
    //     ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "INVALID DATE FORMAT");   
    // }
    // const char *input_date = apr_pcalloc(r->pool, 11);
    // strftime(input_date, 11, "%Y-%m-%d", &date);
    // const char *formatted_date = apr_pcalloc(r->pool, 11);
    // mktime(&date);
    // strftime(formatted_date, 11, "%Y-%m-%d", &date);
    // if (apr_strnatcasecmp(input_date, formatted_date))
    // {
    //     ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, "INVALID DATE! OH NO!!!!");
    // }


    return OK;
}

static const char *load_lookup_script(cmd_parms *cmd, void *dconf, const char *filename)
{
    m_lookup_conf *cfg = (m_lookup_conf *)dconf;

    apr_file_t *script_file;
    if (apr_file_open(&script_file, filename, APR_FOPEN_READ, 0, cmd->temp_pool) != APR_SUCCESS) 
    {
        return "Can't open script file!";
    }
    char *buf = apr_pcalloc(cmd->temp_pool, MAX_FILE_SIZE);
    apr_size_t size = (apr_size_t)MAX_FILE_SIZE;
    if (apr_file_read(script_file, buf, &size) != APR_SUCCESS) {
        return "Can't read script file";
    }
    apr_file_close(script_file);
   
    cfg->lookup_script = apr_pstrdup(cmd->pool, buf);
    cfg->lookup_script_len = size;
   
    return NULL;
}

static const char *set_endpoint(cmd_parms *cmd, void *dconf, const char *endpoint)
{
    m_lookup_conf *cfg = (m_lookup_conf *)dconf;
    cfg->endpoint = endpoint;
    return NULL;
}

static const char *set_service_regexp(cmd_parms *cmd, void *dconf, const char *regex_str)
{
    m_lookup_conf *cfg = (m_lookup_conf *)dconf;
    cfg->lookup_service_regexp = apr_pcalloc(cmd->pool, sizeof(ap_regex_t));
    int error = ap_regcomp(cfg->lookup_service_regexp, regex_str, 0);
    if (error) {
        int msize = 2048;
        char *err_message = apr_pcalloc(cmd->pool, msize);
        ap_regerror(error, cfg->lookup_service_regexp, err_message, msize);
        return apr_pstrcat(cmd->pool, "M-dimension JSON Service Regex incorrect ", err_message, NULL);
    }
    return NULL;    
}

static const char *set_regexp(cmd_parms *cmd, void *dconf, const char *pattern)
{
    m_lookup_conf *cfg = (m_lookup_conf *)dconf;
    char *err_message = NULL;
    if (cfg->regexp == 0)
        cfg->regexp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t));
    ap_regex_t *m = (ap_regex_t *)apr_array_push(cfg->regexp);
    int error = ap_regcomp(m, pattern, 0);
    if (error) {
        int msize = 2048;
        err_message = apr_pcalloc(cmd->pool, msize);
        ap_regerror(error, m, err_message, msize);
        return apr_pstrcat(cmd->pool, "MRF Regexp incorrect ", err_message, NULL);
    }
    return NULL;
}


static void register_hooks(apr_pool_t *p)
{
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

static void *create_dir_config(apr_pool_t *p, char *unused)
{
    return apr_pcalloc(p, sizeof(m_lookup_conf));
}

static const command_rec cmds[] = 
{
    AP_INIT_TAKE1(
        "MLookupScript",
        load_lookup_script, // Callback
        0, // Self pass argument
        ACCESS_CONF,
        "Location of Lua script to derive z-index"
    ),

    AP_INIT_TAKE1(
        "MLookupEndpoint",
        set_endpoint,
        0,
        ACCESS_CONF,
        "Endpoint to be used for tile requests."
    ),
    
    AP_INIT_TAKE1(
        "MLookupRegexp",
        set_regexp,
        0,
        ACCESS_CONF,
        "Regexp to determine requests that will be handled by mod_m_lookup."
    ),

    AP_INIT_TAKE1(
        "MLookupServiceRegexp",
        set_service_regexp,
        0,
        ACCESS_CONF,
        "Regexp to determine which requests will result in JSON z-index response."
    ),

    {NULL}
};

module AP_MODULE_DECLARE_DATA m_lookup_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge, no inheritance
    0, // No server_config
    0, // No server_merge
    cmds, // configuration directives
    register_hooks // processing hooks
};
