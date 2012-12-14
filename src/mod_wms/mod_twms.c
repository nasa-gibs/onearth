/*
 * Tiled WMS cache module for Apache 2.0
 * Version 2.0
 *
 * Lucian Plesea
 */

#include <httpd.h>
#include <http_config.h>
#include <http_core.h>
#include <http_log.h>
#include <http_main.h>
#include <http_request.h>

#include "apr.h"
#include "apr_pools.h"
#include "apr_strings.h"
#include "apr_tables.h"

#define APR_WANT_STRFUNC
#define APR_WANT_MEMFUNC
#include "apr_want.h"

//#include "mod_twms.h" // external API
//#include "twms.h" // internal use

typedef struct {
  server_rec *s;
  void *data_ptr;
} twms_server_conf;

typedef struct {
  apr_pool_t *p;
  char *Config;
  char *path;
  server_rec *s;
} twms_dir_conf;

// This module
module AP_MODULE_DECLARE_DATA twms_module;

static int twms_handler(request_rec *r)

{
  twms_dir_conf *dcfg;
  const char *data;
  const char *val;
  apr_table_t *tab;
  apr_file_t *fh;
  apr_size_t nsend;
  apr_finfo_t info;


  if ((r->method_number != M_GET )||(r->args==0)) return DECLINED;
  data=r->args;
  // scfg=ap_get_module_config(r->server->module_config,&twms_module);
  dcfg=ap_get_module_config(r->per_dir_config,&twms_module);
  if (!dcfg) return DECLINED; // Does this ever happen?

  if (!ap_strstr(data,"GetTileService")) return DECLINED;
  // Do we have a config for this directory

//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"TWMS_handler: args %s, path %s scfg %x dcfg %x dir %s conf %s",
//    data,r->parsed_uri.path,scfg,dcfg,dcfg->path,dcfg->Config);
  if (!dcfg->Config) return DECLINED;


  // This is overkill here, but it works
  tab=apr_table_make(r->pool,0);

  while (*data && (val=ap_getword(r->pool, &data, '&'))) {
    char *key=apr_pstrdup(r->pool,ap_getword(r->pool, &val, '='));
    char *ival=apr_pstrdup(r->pool,val);
    ap_unescape_url(key);ap_unescape_url(ival);
    apr_table_merge(tab,key,ival);
  }

  if (!(val=apr_table_get(tab,"request"))) return DECLINED;
  if (apr_strnatcmp(val,"GetTileService")) return DECLINED;

  if (APR_SUCCESS!=apr_file_open(&fh,apr_pstrcat(r->pool,dcfg->path,dcfg->Config,0),
      APR_READ,APR_OS_DEFAULT,r->pool)) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"TWMS file can't be read");
    return HTTP_CONFLICT;
  }
  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"TWMS Sending GTS file");
  apr_file_info_get(&info,APR_FINFO_SIZE,fh);

  ap_set_content_type(r,"text/xml");
  ap_send_fd(fh,r,0,info.size,&nsend);

  apr_file_close(fh);
  return OK;
}

static void twms_register_hooks(apr_pool_t *p)

{
  ap_hook_handler(twms_handler,NULL,NULL,APR_HOOK_FIRST);
};

static const *twms_config_set(cmd_parms *cmd, void *dummy, const char *arg)
{
  server_rec *server=cmd->server;

  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server,"Server %s TWMSConfig %s",
        server->server_hostname,arg);
  return NULL;
};

static const *twms_dir_config_set(cmd_parms *cmd, void *dconf, const char *arg)
{

  twms_dir_conf *d=(twms_dir_conf *)dconf;
  d->p=cmd->pool;
  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,d->s,"Previous path was %s",d->path);
  d->path=apr_pstrdup(cmd->pool,cmd->path);
  d->Config=apr_pstrdup(d->p,arg);
  d->s=cmd->server;
  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,d->s,"Server %s config @%x TWMSDirConfig %s, path %s",
        d->s->server_hostname,d,d->Config,cmd->path);
  return NULL;
};

static const command_rec twms_cmds[] =
{
  AP_INIT_TAKE1(
        "TWMSConfig",
        twms_config_set, // Callback
        0, // Self-pass argument
        RSRC_CONF, // availability
        "Tiled WMS configuration - points to the configuration file" // help
 ),
  AP_INIT_TAKE1(
        "TWMSDirConfig",
        twms_dir_config_set, // Callback
        0, // Self-pass argument
        ACCESS_CONF, // availability
        "Tiled WMS directory configuration - points to the configuration file" // help
 ),
 { NULL }
};
static void *create_server_config(apr_pool_t *p, server_rec *s)
{
  ap_log_error(APLOG_MARK, APLOG_ERR,0,s,
        "Create server called, host %s",s->server_hostname );
  twms_server_conf *c=
    (twms_server_conf *) apr_pcalloc(p, sizeof(twms_server_conf));
  c->s=s;
  return c;
}

static void *merge_server_config(apr_pool_t *p, void *basev, void *overlayv)
{
  twms_server_conf *c=
    (twms_server_conf *) apr_pcalloc(p, sizeof(twms_server_conf));
  twms_server_conf *base=(twms_server_conf *)basev;
  twms_server_conf *overlay=(twms_server_conf *)overlayv;
  ap_log_error(APLOG_MARK, APLOG_ERR,0,base->s,
     "Subhost merge called host %s",base->s->server_hostname);
  ap_log_error(APLOG_MARK, APLOG_ERR,0,overlay->s,
     "Merge called for %s",overlay->s->server_hostname);
  c->s=overlay->s;
  return c;
}

// These two can't report errors.  Strange but true?
//

static void *create_dir_config(apr_pool_t *p, char *dummy)
{

  twms_dir_conf *c=
    (twms_dir_conf *) apr_pcalloc(p, sizeof(twms_dir_conf));
  return c;
}

static void *merge_dir_config(apr_pool_t *p, void *basev, void *overlayv)
{
  twms_dir_conf *c=
    (twms_dir_conf *) apr_pcalloc(p, sizeof(twms_dir_conf));
  twms_dir_conf *base=(twms_dir_conf *)basev;
  twms_dir_conf *overlay=(twms_dir_conf *)overlayv;

  if (base->path) c->path=apr_pstrdup(p,base->path);
  if (overlay->path) c->path=apr_pstrdup(p,overlay->path);
  if (overlay->Config) c->Config=apr_pstrdup(p,overlay->Config);
  return c;
}

module AP_MODULE_DECLARE_DATA twms_module =
{
        STANDARD20_MODULE_STUFF,
        create_dir_config, // Dir Create
        merge_dir_config, // Dir Merge
        0, // Per-server Config Create
        0, // Server Merge
        twms_cmds, // configuration directive table
        twms_register_hooks // set up processing hooks
};
