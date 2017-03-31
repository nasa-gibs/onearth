/*
* An OnEarth module that serves tiles from an MRF
* Lucian Plesea
* (C) 2016
*/

#include "mod_time.h"
#include "receive_context.h"
#include <jansson.h>

#include <algorithm>
#include <cmath>

using namespace std;

static void *create_dir_config(apr_pool_t *p, char *dummy)
{
    time_snap_conf *c =
        (time_snap_conf *)apr_pcalloc(p, sizeof(time_snap_conf));
    return c;
}

static const char* date_string_replace(apr_pool_t *p, char **buf, const char *t_string, const char *fmt, int value) {
    char *marker;
    char *before;
    char *after;
    if ((marker = ap_strstr(*buf, t_string))) {
        before = apr_pstrmemdup(p, *buf, marker - *buf);
        after = marker + strlen(t_string);
        const char *date_str = apr_psprintf(p, fmt, value);
        *buf = apr_pstrcat(p, before, date_str, after, NULL);
    }
    return NULL;
}

static const char* format_date_with_template(apr_pool_t *p, const char *date_template, apr_time_exp_t date) {
    char *buf = apr_pstrdup(p, date_template);
    date_string_replace(p, &buf, "YYYY", "%04d", date.tm_year + 1900);
    date_string_replace(p, &buf, "DD", "%04d", date.tm_year + 1900);
    return buf;
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
static void read_pKVP_from_file(apr_pool_t *pool, const char *fname, char **err_message, apr_table_t **table, apr_array_header_t **time_periods)
{
    // Should parse it here and initialize the configuration structure
    ap_configfile_t *cfg_file;
    apr_status_t s = ap_pcfg_openfile(&cfg_file, pool, fname);

    if (APR_SUCCESS != s) { // %pm means print status error string
        *err_message = apr_psprintf(pool, "%s - %pm", fname, &s);
        return;
    }

    char buffer[MAX_STRING_LEN];
    *table = apr_table_make(pool, 8);
    *time_periods = apr_array_make(pool, 10, sizeof(char *));

    // This can return ENOSPC if lines are too long
    while (APR_SUCCESS == (s = ap_cfg_getline(buffer, MAX_STRING_LEN, cfg_file))) {
        if ((strlen(buffer) == 0) || buffer[0] == '#')
            continue;
        const char *value = buffer;
        char *key = ap_getword_white(pool, &value);

        // TimePeriod entries are loaded into a separate array
        if (!apr_strnatcasecmp(key, "TimePeriod"))
        {
            const char *time_period = apr_pstrdup(pool, value);
            *(const char**)apr_array_push(*time_periods) = time_period;
        } else {
            apr_table_add(*table, key, value);
        }
    }

    ap_cfg_closefile(cfg_file);
    if (s == APR_ENOSPC) {
        *err_message = apr_psprintf(pool, "%s lines should be smaller than %d", fname, MAX_STRING_LEN);
        return;
    }

    return;
}


// Allow for one or more RegExp guard
// If present, at least one of them has to match the URL
static const char *set_regexp(cmd_parms *cmd, time_snap_conf *c, const char *pattern)
{
    char *err_message = NULL;
    if (c->regexp == 0)
        c->regexp = apr_array_make(cmd->pool, 2, sizeof(ap_regex_t));
    ap_regex_t *m = (ap_regex_t *)apr_array_push(c->regexp);
    int error = ap_regcomp(m, pattern, 0);
    if (error) {
        int msize = 2048;
        err_message = (char *)apr_pcalloc(cmd->pool, msize);
        ap_regerror(error, m, err_message, msize);
        return apr_pstrcat(cmd->pool, "MRF Regexp incorrect ", err_message, NULL);
    }
    return NULL;
}

static apr_time_t parse_date_string(const char *string)
// This function parses a date string into a UNIX time int (microseconds since 1970)
{
    // First we parse the date into a apr_time_exp_t struct.
    apr_time_exp_t date = {0};
    date.tm_year = apr_atoi64(string) - 1900; // tm_year is years since 1900
    // Push the pointer forward
    string += 5;
    date.tm_mon = apr_atoi64(string) - 1; // tm_mon is zero-indexed
    string += 3;
    date.tm_mday = apr_atoi64(string);
    string += 2;

    // Check if we have a time value in this string
    if (string[0] == 'T')
    {
        string++;
        date.tm_hour = apr_atoi64(string);
        string += 3;
        date.tm_min = apr_atoi64(string);
        string += 3;
        date.tm_sec = apr_atoi64(string);
    }

    // Now convert the string into UNIX time and return it
    apr_time_t epoch = 0;
    apr_time_exp_get(&epoch, &date);
    return epoch;
}

// Evaluate the time period for days or seconds
static int evaluate_period(const char *time_period)
{
    int period = 1;
    if (strlen(time_period) > 43) {
        if (time_period[43] == 'T') {
            period = apr_atoi64(time_period+44);
        }
    } else {
        if (time_period[22] == 'P') {
            period = apr_atoi64(time_period+23);
        }
    }
    return period;
}

static apr_time_t add_date_interval(apr_time_t start_epoch, int interval, char *units) {
    apr_time_exp_t date;
    // Convert start date to apr_time_exp_t
    apr_time_exp_gmt(&date, start_epoch);
    int i;
    if(apr_strnatcmp(units, "months") == 0) {
        for(i=0; i<interval; i++) {
            date.tm_mon++;
            if(date.tm_mon == 12) {
                date.tm_mon = 0;
                date.tm_year++;
            }
        }

    } else if (apr_strnatcmp(units, "years") == 0) {
        // Add one interval
        date.tm_year += (interval);
    }
    // Convert it back to epoch form
    apr_time_exp_get(&start_epoch, &date);
    return start_epoch;     

}


static const char *config_set(cmd_parms *cmd, void *dconf, const char *arg)
{
    ap_assert(sizeof(apr_off_t) == 8);
    time_snap_conf *c = (time_snap_conf *)dconf;
    
    char *err_message;
    const char *line;

    apr_table_t *kvp;
    apr_array_header_t *time_periods;

    // Get KvP stuff from the sub-config
    read_pKVP_from_file(cmd->temp_pool, arg, &err_message, &kvp, &time_periods);
    c->time_periods = time_periods;
    if (NULL == kvp) return err_message;

    // Got the parsed kvp table, parse the configuration items
    line = apr_table_get(kvp, "MRF_Endpoint");
    if (!line) {
        return "MRF_Endpoint directive is missing!";
    }
    c->mrf_endpoint = apr_pstrdup(cmd->pool, line);

    line = apr_table_get(kvp, "Layer_Name_Format");
    if (!line) {
        line = "%Y%j_";
    }
    c->layer_name_format = apr_pstrdup(cmd->pool, line);

    line = apr_table_get(kvp, "DatetimeJsonServiceRegexp");
    if (line) {
        if (c->datetime_service_regexp == 0) {
            c->datetime_service_regexp = (ap_regex_t*)apr_pcalloc(cmd->pool, sizeof(ap_regex_t));
        }
        int error = ap_regcomp(c->datetime_service_regexp, line, 0);
        if (error) {
            int msize = 2048;
            err_message = (char *)apr_pcalloc(cmd->pool, msize);
            ap_regerror(error, c->datetime_service_regexp, err_message, msize);
            return apr_pstrcat(cmd->pool, "Datetime JSON Service Regex incorrect ", err_message, NULL);
        }
    }

    return NULL;
}


#define REQ_ERR_IF(X) if (X) {\
    return HTTP_BAD_REQUEST; \
}

#define SERR_IF(X, msg) if (X) { \
    ap_log_error(APLOG_MARK, APLOG_ERR, 0, r->server, msg);\
    return HTTP_INTERNAL_SERVER_ERROR; \
}

static int handler(request_rec *r)
{
    // Only get and no arguments
    if (r->method_number != M_GET) return DECLINED;
    if (r->args) return DECLINED; // Don't accept arguments

    time_snap_conf *cfg = (time_snap_conf *)ap_get_module_config(r->per_dir_config, &time_handler_module);
    // if (!cfg->enabled) return DECLINED; // Not enabled

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
    const char *col = *(const char **)apr_array_pop(tokens); // REQ_ERR_IF(errno); -- the error always triggers and I'm not sure why...
    int row = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    int matrix = apr_atoi64(*(char **)apr_array_pop(tokens)); REQ_ERR_IF(errno);
    const char *tile_matrix_set = *(const char **)apr_array_pop(tokens); REQ_ERR_IF(errno);
    const char *time_string = *(const char **)apr_array_pop(tokens); REQ_ERR_IF(errno);
    const char *layer_name = *(const char **)apr_array_pop(tokens); REQ_ERR_IF(errno);

    const char *url_prefix = "/";
    while (tokens->nelts) {
        const char *url_part = *(const char **)apr_array_pop(tokens);
        url_prefix = apr_pstrcat(r->pool, url_prefix, url_part, "/", NULL);
    }

    // Check that it's the length of a valid time or date request
    if (strlen(time_string) != 10 && strlen(time_string) != 24) {
        return DECLINED;
    }
    int hastime = strlen(time_string) == 24;
    // Parse the date string into a UNIX epoch time (TODO: ADD ERROR CHECKING FOR INVALID DATE STRING?????)
    apr_time_t req_epoch = parse_date_string(time_string);

    for (int i=0; i<cfg->time_periods->nelts; i++) 
    {                
        char *time_period = APR_ARRAY_IDX(cfg->time_periods, i, char *);
        ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Evaluating time period %s", time_period);
        if (!ap_strstr(time_period,"P")) {
            ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"No duration detected in %s", time_period);
            continue;
        }
        apr_time_t interval = evaluate_period(time_period);

        // START OF DATE SNAPPING ROUTINE 
        // First, parse the period start and end time strings, as well as the request.
        // We're going to parse them into UNIX time integers (microseconds since 1970) for ease of working with them
        apr_time_t start_epoch = parse_date_string(time_period);
        if (time_period[11] == 'T') {
            time_period += 21;
        } else {
            time_period += 11;
        }
        apr_time_t end_epoch = parse_date_string(time_period);

        // First, check if the request date is earlier than the start date of the period. (we don't snap forward)
        if (req_epoch < start_epoch) {
            continue;
        }

        // Now we find the closest time before the requested time
        // We do this by counting up intervals from the start date.
        // Years and months aren't a fixed time interval so we process separately
        apr_time_t snap_epoch = 0;
        apr_time_t date_epoch;
        apr_time_t prev_epoch = start_epoch;
        char interval_char = time_period[(strlen(time_period) - 1)];
        switch (interval_char) {
            case 'Y':
                for(;;) {
                    date_epoch = add_date_interval(prev_epoch, interval, "years");  
                    // If the new counter date is bigger than the request date, we've found the snap date
                    if (date_epoch > req_epoch) {
                        snap_epoch = prev_epoch;
                        break;
                    }
                    // Didn't snap yet, check if we're past the end date
                    if (date_epoch > end_epoch) {
                        break;
                    }
                    // If we made it this far, increment the date and try again
                    prev_epoch = date_epoch;
                    continue;
                }
                break;
            case 'M':
                for (;;) {
                    date_epoch = add_date_interval(prev_epoch, interval, "months");
                    // If the new counter date is bigger than the request date, we've found the snap date
                    if (date_epoch > req_epoch) {
                        snap_epoch = prev_epoch;
                        break;
                    }
                    // Didn't snap yet, check if we're past the end date
                    if (date_epoch > end_epoch) {
                        break;
                    }
                    // If we made it this far, increment the date and try again
                    prev_epoch = date_epoch;
                    continue;
                }
                break;
            default:
                // Not year or month. Since days and time intervals are fixed, we can treat them all as microsecond intervals
                // Get interval in ms
                switch (interval_char) {
                    case 'D':
                        interval = interval * 24 * 60 * 60 * 1000 * 1000;
                        break;
                    case 'H':
                        interval = interval * 60 * 60 * 1000 * 1000;
                        break;
                    case 'M':
                        interval = interval * 60 * 1000 * 1000;
                        break;
                    case 'S':
                        interval = interval * 1000 * 1000;
                        break;
                }
                apr_time_t closest_interval =  (((req_epoch - start_epoch) / interval) * interval) + start_epoch;
                if (closest_interval <= end_epoch) {
                    // Closest date we can snap to is beyond end of the last allowable interval
                    snap_epoch = closest_interval;
                }
                break;
        }

        // Go to next time period if we still don't have a snap date
        if (snap_epoch == 0) {
            continue;
        }

        // We have a snap date, time to build the filename (remember that tm_yday is zero-indexed)
        apr_time_exp_t snap_date;
        apr_time_exp_gmt(&snap_date, snap_epoch);

        // const char *date_string = format_date_with_template(r->pool, "YYYY", snap_date);
        char *date_string = (char *)apr_pcalloc(r->pool, sizeof(char));
        apr_size_t date_stringlen;
        apr_strftime(date_string, &date_stringlen, 11, "%F", &snap_date);

        // If this is a request for just the snapped date and time, we assemble a JSON string with that info and return it.
        if (cfg->datetime_service_regexp && !ap_regexec(cfg->datetime_service_regexp, col, 0, NULL, 0)) {
            json_t *json_out_obj = json_object();

            apr_time_exp_t req_date;
            apr_time_exp_gmt(&req_date, req_epoch);
            apr_size_t len;
            const char *date_template = hastime ? "%FT%TZ" : "%F";
            char *iso_date_string = (char *)apr_pcalloc(r->pool, sizeof(char) * 20);

            apr_strftime(iso_date_string, &len, 20, date_template, &req_date);
            json_t *req_date_json = json_string(iso_date_string);
            json_object_set(json_out_obj, "request_time", req_date_json);

            apr_strftime(iso_date_string, &len, 20, date_template, &snap_date);
            json_t *snap_date_json = json_string(iso_date_string);
            json_object_set(json_out_obj, "nearest_previous_time", snap_date_json);
            const char *out_string = json_dumps(json_out_obj, JSON_COMPACT);

            ap_set_content_type(r, "application/json");
            ap_set_content_length(r, strlen(out_string) * sizeof(char));
            ap_rwrite(out_string, strlen(out_string) * sizeof(char), r);

            return OK;
        }

        // Build a layer name using the date we're snapping to, then redirect it.
        // TODO: Right now, we're using the standard GIBS YYYYDDD_ format for layer names. Do we want to make this user-modifiable?

        char *mrf_datestring = (char *)apr_pcalloc(r->pool, sizeof(char) * 20);
        apr_size_t len;
        apr_strftime(mrf_datestring, &len, 20, cfg->layer_name_format, &snap_date);
        const char *mrf_filename = apr_pstrcat(r->pool, layer_name, mrf_datestring, NULL);

        // const char *layer_name_template = "%s%04d%03d_";
        // const char *mrf_filename = apr_psprintf(r->connection->pool,
        //                                         layer_name_template,
        //                                         layer_name,
        //                                         snap_date.tm_year + 1900,
        //                                         snap_date.tm_yday + 1
        //                                         );

        const char *uri_template = "%s%s/%s/%01d/%01d/%s";
        const char *mrf_redirect = apr_psprintf(r->pool,
                                                    uri_template,
                                                    cfg->mrf_endpoint,
                                                    mrf_filename,
                                                    tile_matrix_set,
                                                    matrix,
                                                    row,
                                                    col
                                                    );
        ap_internal_redirect(mrf_redirect, r);
        return DECLINED;
    }

    return DECLINED;
}

static const command_rec mrf_cmds[] =
{
    AP_INIT_TAKE1(
    "Time_Handler_ConfigurationFile",
    CMD_FUNC config_set
    , // Callback
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "The configuration file for this module"
    ),

    AP_INIT_TAKE1(
    "Time_Handler_RegExp",
    (cmd_func)set_regexp,
    0, // Self-pass argument
    ACCESS_CONF, // availability
    "Regular expression that the URL has to match.  At least one is required."
    ),

    { NULL }
};


// Return OK or DECLINED, anything else is error
static int check_config(apr_pool_t *pconf, apr_pool_t *plog, apr_pool_t *ptemp, server_rec *server)
{
   return DECLINED;
    // This gets called once for the whole server, it would have to check the configuration for every folder
}

static void mrf_register_hooks(apr_pool_t *p)
{
    ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST);
       ap_hook_check_config(check_config, NULL, NULL, APR_HOOK_MIDDLE);
}

module AP_MODULE_DECLARE_DATA time_handler_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config,
    0, // No dir_merge
    0, // No server_config
    0, // No server_merge
    mrf_cmds, // configuration directives
    mrf_register_hooks // processing hooks
};
