#include "mod_ahtse_lua.h"
#include <apr_strings.h>
#include <http_log.h>
#include <http_request.h>

// Define LUA_IS_CPP if the lua library is compiled as C++/
#if defined(LUA_IS_CPP)
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#else
#include <lua.hpp>
#endif

#if !defined(LUA_OK)
#define LUA_OK 0
#endif

// Connection note key for lua state
#define LUA_NOTE "ahtse_lua"

typedef struct {
  lua_State *L;
  ahtse_lua_conf *c; // Which configuration the state belongs to
} LState;

static bool our_request(request_rec *r) {
    if (r->method_number != M_GET) return false;
    apr_array_header_t *regexp_table = ((ahtse_lua_conf *)
            ap_get_module_config(r->per_dir_config, &ahtse_lua_module))->regexp;

    if (!regexp_table) return false;
    char *url_to_match = apr_pstrcat(r->pool, r->uri, r->args ? "?" : NULL, r->args, NULL);
    for (int i = 0; i < regexp_table->nelts; i++) {
        ap_regex_t *m = APR_ARRAY_IDX(regexp_table, i, ap_regex_t *);
        if (!ap_regexec(m, url_to_match, 0, NULL, 0))
            return true;
    }
    return false;
}

// Some output headers are special, an apr_table_set won't cut it
// Some need to be set specifically, with a non-transient value
#define error_from_lua(S) static_cast<const char *>(apr_pstrcat(r->pool, S, lua_tostring(L, -1), NULL))

// apr callback for pushing a table to outgoing headers
// the input strings have to be valid for the duration of the request, no copy is made
int set_header(void *rec, const char *key, const char *val) {
    request_rec *r = reinterpret_cast<request_rec *>(rec);
    if (key == ap_strcasestr(key, "Content-Type"))
        ap_set_content_type(r, val);
    else
        apr_table_setn(r->headers_out, key, val);
    return 1; // Continue
}

// apr callback for conversion to lua table.  Assumes table is on top of stack, already initialized
int push_to_lua_table(void *Lua, const char *key, const char *val) {
    lua_State *L = reinterpret_cast<lua_State *>(Lua);
    lua_pushstring(L, key);
    lua_pushstring(L, val);
    lua_settable(L, -3);
    return 1; // Continue
}

static int lua_print_to_log(lua_State *L) {
  request_rec *r = (request_rec *)lua_touserdata(L, lua_upvalueindex(1));
  int nargs = lua_gettop(L);
  for (int i=1; i <= nargs; i++) {
    if (lua_isstring(L, i)) {   
      const char *log_msg = lua_tostring(L, i);
      ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "%s", log_msg);
    }
  }
  return 0;
}

// An apr pool cleanup function for a pool owned lua state
apr_status_t LState_cleanup(void *data) {
  LState *luastate = (LState *)data;

  // Check for the presence of a "close" routine
  lua_State *L = luastate->L;
  lua_getglobal(L, "closeFunc");
  if (lua_isfunction(L, -1)) {
    int err = lua_pcall(L, 0, 0, 0);
  }

  if (luastate->L) {
    lua_close(luastate->L);
    luastate->L = NULL;
  }
  return APR_SUCCESS;
}

static int handler(request_rec *r)
{
    if (!our_request(r))
        return DECLINED;

    const char *uuid = apr_table_get(r->headers_in, "UUID") 
        ? apr_table_get(r->headers_in, "UUID") 
        : apr_table_get(r->subprocess_env, "UNIQUE_ID");
    apr_time_t start_mod_ahtse_process = apr_time_now();
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=end_send_to_date_service, timestamp=%ld, uuid=%s",
      apr_time_now(), uuid);

    ahtse_lua_conf * c = (ahtse_lua_conf *)
        ap_get_module_config(r->per_dir_config, &ahtse_lua_module);

    lua_State *L = NULL;

    // Let's see if the lua state is already present for this connection
    LState *luastate = (LState *)apr_table_get(r->connection->notes, LUA_NOTE);

    if (c->persistent && luastate) {
      if (luastate->c != c) {

        // Clean up the old lua state
        // This leaves the LState structure to be cleaned by the connection pool
        // so make sure the LState cleanup function knows there is nothing to do
        apr_pool_cleanup_run(r->connection->pool, luastate, LState_cleanup);
        apr_table_unset(r->connection->notes, LUA_NOTE);
        luastate = NULL;

      }
      else
        L = luastate->L;
    }

    // Initialize Lua 
    if (!L) try {
      // Start a new lua state
      L = luaL_newstate();
      if (!L)
        throw "Lua state allocation error";
      luaL_openlibs(L);
      if (LUA_OK != luaL_loadbuffer(L, reinterpret_cast<const char *>(c->script), c->script_len, c->func)
        || LUA_OK != lua_pcall(L, 0, 0, 0))
        throw error_from_lua("Lua initialization script ");
    }
    catch (const char *msg) { // Errors during initialization
      if (L)
        lua_close(L);

      if (luastate) { // If there is a persistent luastate, something is seriously wrong with it
        apr_pool_cleanup_run(r->connection->pool, luastate, LState_cleanup);
        apr_table_unset(r->connection->notes, LUA_NOTE);
        luastate = NULL;
      }

      ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "%s", msg);
      return HTTP_INTERNAL_SERVER_ERROR;
    }

    if (c->persistent && !luastate) {
      // Initialize a LState struct, leave the note and register the pool cleanup
      luastate = (LState *)apr_palloc(r->connection->pool, sizeof(LState));
      luastate->c = c;
      luastate->L = L;
      apr_table_addn(r->connection->notes, LUA_NOTE, (const char *)luastate);
      // No child cleanup action needed
      apr_pool_cleanup_register(r->connection->pool, luastate, LState_cleanup, apr_pool_cleanup_null);
    }

    int status = OK;

    //
    // Execute the lua script and send the result back
    //
    // The function takes three parameters
    // - the arguments for the request, or nil
    // - A table of input headers
    // - A table of AHTSE specific notes
    //

    try {

      // We have a state here, get the handler function
      lua_getglobal(L, c->func);
      if (!lua_isfunction(L, -1)) {
        status = HTTP_INTERNAL_SERVER_ERROR;
        throw "Lua handler missing";
      }

      // Add redefined print function so print statements in Lua appear as debug level log messages
      lua_pushlightuserdata(L, r);
      lua_pushcclosure(L, lua_print_to_log, 1);
      lua_setglobal(L, "print");

      if (r->args)
        lua_pushstring(L, r->args);
      else
        lua_pushnil(L);

      // Convert the input table from apr to lua
      lua_createtable(L, 0, apr_table_elts(r->headers_in)->nelts);
      apr_table_do(push_to_lua_table, L, r->headers_in, NULL);

      // The input notes table
      // The URI is passed this way, and the HTTPS flag, if set
      lua_newtable(L);
      push_to_lua_table(L, "URI", r->uri);
      if (apr_table_get(r->subprocess_env, "HTTPS"))
        push_to_lua_table(L, "HTTPS", "On");

      // returns content, headers and code
      int err = lua_pcall(L, 3, 3, 0);
      if (LUA_OK != err)
        throw error_from_lua("Lua execution error ");

      // Get the return code
      if (!lua_isnumber(L, -1))
        throw "Lua third return should be an http numeric status code";
      status = static_cast<int>(lua_tonumber(L, -1));
      lua_pop(L, 1); // Remove the return code

      // 200 means all OK
      if (HTTP_OK == status)
        status = OK;
      int type = lua_type(L, -1);

      apr_table_t *out_headers = NULL;

      // Convert the LUA table to an apache header table
      if (type == LUA_TTABLE) {
        out_headers = apr_table_make(r->pool, 4);

        lua_pushnil(L); // First key
        while (lua_next(L, -2)) {
          if (!(lua_isstring(L, -1) && lua_isstring(L, -2)))
            throw "Lua header table non-string key or value found";

          // This makes a copy for the request
          apr_table_add(out_headers, lua_tostring(L, -2), lua_tostring(L, -1));
          lua_pop(L, 1); // Pop the value
        }

        lua_pop(L, 1); // Pop the key
      }
      else if (type != LUA_TNIL) { // Only table and nil are accepted
        throw "Lua second return should be table of headers or nil";
      }

      // Special case, if a redirect code is received and internal redirect is allowed
      if (c->allow_redirect && (
        HTTP_MOVED_PERMANENTLY == status || HTTP_MOVED_TEMPORARILY == status
        || HTTP_PERMANENT_REDIRECT == status || HTTP_TEMPORARY_REDIRECT == status)
        )
      {   // If no Location is provided use the normal response path
        const char *uri = apr_table_get(out_headers, "Location");
        if (uri) {
          // Cleanup lua and then issue internal redirect
          ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "Redirecting to %s", uri);

          // Pop the content, we don't care what it is
          lua_pop(L, 1);
          if (!c->persistent)
            lua_close(L);

          ap_internal_redirect(uri, r);
          // This request is done
          return OK;
        }
      }

      // Pass the result and the headers to the requester
      const char *result = NULL;
      size_t size = 0;

      // Content, which could be nil
      type = lua_type(L, -1);

      if (type != LUA_TNIL)
        result = lua_tolstring(L, -1, &size);

      // Might have no headers on return
      if (out_headers)
        apr_table_do(set_header, r, out_headers, NULL);

      if (size) { // Got this far, send the result if any
        ap_set_content_length(r, size);
        ap_rwrite(result, size, r);
      }

      // Get rid of the returned content only when no longer needed
      lua_pop(L, 1);
    }
    catch (const char *msg) {
      if (msg) { // No message means early exit
        ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "%s", msg);
        status = HTTP_INTERNAL_SERVER_ERROR;
      }
    }

    if (!c->persistent)
      lua_close(L);

    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=mod_ahtse_handle, duration=%ld, uuid=%s",
      apr_time_now() - start_mod_ahtse_process, uuid);
    ap_log_rerror(APLOG_MARK, APLOG_DEBUG, 0, r, "step=begin_return_to_wrapper, timestamp=%ld, uuid=%s",
      apr_time_now(), uuid);

    return status;
}

// Allow for one or more RegExp guard
// One of them has to match if the request is to be considered
static const char *set_regexp(cmd_parms *cmd, ahtse_lua_conf *c, const char *pattern)
{
    if (c->regexp == 0)
        c->regexp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t *));

    ap_regex_t **m = (ap_regex_t **)apr_array_push(c->regexp);

    *m = ap_pregcomp(cmd->pool, pattern, 0);

    return (NULL == *m) ? "Bad regular expression" : NULL;
}

// Sets the script and possibly the function name to be called
static const char *set_script(cmd_parms *cmd, ahtse_lua_conf *c, const char *script, const char *func)
{
    // Read the script file, makes it faster if the file is small and self-contained
    apr_finfo_t status;
    if (APR_SUCCESS != apr_stat(&status, script, APR_FINFO_SIZE, cmd->temp_pool))
        return apr_pstrcat(cmd->pool, "Can't stat ", script, NULL);
    c->script_len = static_cast<apr_size_t>(status.size);
    c->script = apr_palloc(cmd->pool, c->script_len);
    if (!c->script)
        return "Can't allocate memory for lua script";
    apr_file_t *thefile;
    if (APR_SUCCESS != apr_file_open(&thefile, script, APR_FOPEN_READ | APR_FOPEN_BINARY, 0, cmd->temp_pool))
        return apr_pstrcat(cmd->pool, "Can't open ", script, NULL);

    apr_size_t bytes_read;
    if (APR_SUCCESS != apr_file_read_full(thefile, c->script, c->script_len, &bytes_read)
        || bytes_read != c->script_len)
        return apr_pstrcat(cmd->pool, "Can't read ", script, NULL);

    // Get the function name too, if present, otherwise use "handler"
    c->func = (func) ? apr_pstrcat(cmd->pool, func, NULL) : "handler";
    return NULL;
}

static void *create_dir_config(apr_pool_t *p, char *path)
{
    ahtse_lua_conf *c = (ahtse_lua_conf *)(apr_pcalloc(p, sizeof(ahtse_lua_conf)));
    c->doc_path = path;
    return c;
}

static void register_hooks(apr_pool_t *p) {
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_MIDDLE);
}

static const command_rec cmds[] = {
    AP_INIT_TAKE12(
        "AHTSE_lua_Script",
        (cmd_func)set_script, // Callback
        0, // Self-pass argument
        ACCESS_CONF, // availability
        "Lua script to execute"
    ),

    AP_INIT_TAKE1(
        "AHTSE_lua_RegExp",
        (cmd_func)set_regexp,
        0, // Self-pass argument
        ACCESS_CONF, // availability
        "Regular expression for URL matching.  At least one is required."
     ),

     AP_INIT_FLAG(
        "AHTSE_lua_Redirect",
        (cmd_func)ap_set_flag_slot, (void *) APR_OFFSETOF(ahtse_lua_conf, allow_redirect),
        ACCESS_CONF,
        "Enable internal redirect on temporary or permanent redirect status"
     ),

     AP_INIT_FLAG(
        "AHTSE_lua_KeepAlive",
        (cmd_func)ap_set_flag_slot, (void *)APR_OFFSETOF(ahtse_lua_conf, persistent),
        ACCESS_CONF,
        "Enable Lua state to be reused for requests on the same connection"
     ),

     { NULL }
};

module AP_MODULE_DECLARE_DATA ahtse_lua_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    NULL,
    NULL,
    NULL,
    cmds,
    register_hooks
};
