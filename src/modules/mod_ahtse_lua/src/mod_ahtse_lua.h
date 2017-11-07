/*
 * mod_ahtse_lua header file
 * Lucian Plesea
 * (C) 2016
 */

#if !defined(MOD_AHTSE_LUA)
#define MOD_AHTSE_LUA

#include <http_protocol.h>
#include <http_config.h>

#if defined(APLOG_USE_MODULE)
APLOG_USE_MODULE(ahtse_lua);
#endif

typedef struct {
    const char *doc_path;
    void *script;
    apr_size_t script_len;
    const char *func;
    apr_array_header_t *regexp;

    // Issue an internal redirect if a redirect code is received
    int allow_redirect;
    // Reuse lua state for the duration of the connection
    int persistent;
} ahtse_lua_conf;

extern module AP_MODULE_DECLARE_DATA ahtse_lua_module;

#endif