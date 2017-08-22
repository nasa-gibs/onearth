/*
* Copyright (c) 2002-2016, California Institute of Technology.
* All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
*
* Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
*   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
*   2. Redistributions in binary form must reproduce the above copyright notice,
*      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
*   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
*      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
*      endorse or promote products derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
* INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
* IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
* EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
* LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
* STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
* http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

/* 
 * OnEarth module for Apache 2.0
 * Version 1.3.1
 *
 * Only takes server configuration, no point in doing directories,
 * as these have to be read in for every request, negating the cache
 * It reads in the cache configuration file, provided by
 * the WMSCache command at startup
 * For each request, it serves only tiles that are found in the cache.
 * It declines to deal with tiles not in the cache, so the request can
 * be looked at by other modules, such as the cgi one.
 * Beware, it looks like the error messages logged for a declined 
 * request never make it to the error log.
 *  
 * Lucian Plesea
 * Joe Roberts
 * Joshua Rodriguez
 */

#include "httpd.h"
#include "http_config.h"
#include "http_core.h"
#include "http_log.h"
#include "http_main.h"
#include "http_protocol.h"
#include "http_request.h"
#include "util_script.h"
#include "http_connection.h"

#include "cache.h"
#include "apr_lib.h"
#include "apr_strings.h"
#include "apr_file_io.h"

#include <sqlite3.h>
#include <unistd.h>
#include <math.h>

#include "mod_wmts_wrapper.h"

// Use APLOG_WARNING APLOG_DEBUG or APLOG_ERR.  Sets the level for the "Unhandled .." 
#define LOG_LEVEL APLOG_ERR

typedef struct {
  double x0,y0,x1,y1;
} wms_wmsbbox;

typedef struct {
  index_s index;
  void *data;
} wms_empty_record;

typedef struct {
  // This points to a table, one per match
  ap_regex_t **regex;
  char *mime_type;
  // this is a table, one such per level
  wms_empty_record *empties;
} meta_cache;

// All pointers, can be copied as long as the pool stays around
typedef struct {
  Caches *caches;   // The cache configuration
  apr_pool_t *p;    // The persistent server pool
  char *cachedir;   // The cache directory name
  meta_cache *meta; // Run-time information for each cache
  char *dir;		// The server directory
} wms_cfg;

// WMTS error handling
struct wmts_error{
  int status;
  char *exceptionCode;
  char *locator;
  char *exceptionText;
};
typedef struct wmts_error wmts_error;
struct wmts_error wmts_errors[5];
int errors = 0;
static int wmts_add_error(request_rec *r, int status, char *exceptionCode, char *locator, char *exceptionText);
static int wmts_return_all_errors(request_rec *r);

// Module constants
static char kmltype[]="application/vnd.google-earth.kml+xml";
static int kmlt_len=36; // Number of charachters in kmltype
static char Matrix[]="TILEMATRIX=";
static int matrix_len=11; // Number of chars in Matrix;
static char WMTS_marker[]="=WMTS";
static int moffset[12]={0,31,59,90,120,151,181,212,243,273,304,334};
static char colon[] = "%3A";

// This module
module AP_MODULE_DECLARE_DATA onearth_module;

// Evaluate the time period for days or seconds
static int evaluate_period(char *time_period)
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

static apr_time_t get_pre_1970_epoch(apr_time_exp_t date)
{
	struct tm t;
	t.tm_year = date.tm_year;
	t.tm_mon = date.tm_mon;
	t.tm_mday = date.tm_mday;
	t.tm_hour = date.tm_hour;
	t.tm_min = date.tm_min;
	t.tm_sec = date.tm_sec;
	apr_time_t epoch = (apr_time_t)timegm(&t) * 1000 * 1000;
	return epoch;
}

static apr_time_t add_date_interval(apr_time_t start_epoch, int interval, char *units) {
	apr_time_exp_t date = {0};
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
	if (date.tm_year < 70) return get_pre_1970_epoch(date);
	apr_time_exp_get(&start_epoch, &date);
	return start_epoch;		

}

static apr_time_t parse_date_string(char *string)
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

	// The Apache time struct doesn't support dates before Jan 01, 1970, so we use the normal UNIX date stuff
	// to get a negative epoch for those cases.
	if (date.tm_year < 70) return get_pre_1970_epoch(date);

	// Now convert the string into UNIX time and return it
	apr_time_t epoch = 0;
	apr_time_exp_get(&epoch, &date);
	return epoch;
}

// single shot, open fname file, read nbytes from location, close file.
// Allocates memory form request pool, returns a pointer to the buffer
static void *p_file_pread(apr_pool_t *p, char *fname, 
                          apr_size_t nbytes, apr_off_t location)
{
  int fd;

  void *buffer;
  apr_size_t readbytes;

  if (!(buffer=apr_pcalloc(p,nbytes))) return 0;
  if (0>(fd=open(fname,O_RDONLY))) return 0;

  readbytes=pread64(fd,buffer,nbytes,location);
  close(fd);

  return (readbytes==nbytes)?buffer:0;
}

// Get the filename with timestamp
char *tstamp_fname(request_rec *r,char *fname)
{
  static char* timearg="time=";
  static char* tstamp="TTTTTTT_";
  char *targ;

  if ((targ=ap_strcasestr(r->args,timearg))&&ap_strstr(fname,tstamp)) { 
    // This part is not apr compatible, since mktime is not available easily
    int year=0,month=0,day=0;
    char *fn=apr_pstrdup(r->pool,fname);
    char *fnloc=ap_strstr(fn,tstamp);
    // Get a new place
    char old_char=*(fnloc+7);
    char *yearloc=0;

    targ+=5; // Skip the time= part
    year=apr_atoi64(targ);
    targ+=5; // Skip the YYYY- part
    month=apr_atoi64(targ);
    targ+=3; // Due to UV bug
    if ('-'==*targ) targ++;
    day=apr_atoi64(targ);

    if ((year>0)&&(month>0)&&(day>0)) { // We do have a time stamp
      int leap=(year%4)?0:((year%400)?((year%100)?1:0):1);
      sprintf(fnloc,"%04d%03d",year,day+moffset[month-1]+((month>2)?leap:0));
      *(fnloc+7)=old_char; // We have to put this character back

	  // Name change for Year
	  if ((yearloc=ap_strstr(fn,"YYYY"))) {
		  old_char=*(yearloc+4);
		  sprintf(yearloc,"%04d",year); // replace YYYY with actual year
		  *(yearloc+4)=old_char;
	  }
    }
    return fn;
  } 
  return fname;
}

// Same, but uses a request, and does the time stamp part

static void *r_file_pread(request_rec *r, char *fname, 
                          apr_size_t nbytes, apr_off_t location, char *time_period, int num_periods, int zlevels)
{
  int fd;
  int leap=0;
  int hastime=0;
  static char* timearg="time=";
  static char* tstamp="TTTTTTT_";
  static char* year="YYYY";
  char *targ=0,*fnloc=0,*yearloc=0;
  apr_time_exp_t tm = {0};

  void *buffer;
  apr_size_t readbytes;

//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"r_file_pread file %s size %ld at %ld",fname,nbytes,location);

  // Duplicate the file name, in case we need to change it
  char *fn=apr_pstrdup(r->pool,fname);
  if (!(buffer=apr_pcalloc(r->pool,nbytes))) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "Can't get memory for pread");
    return 0;
  }

  // Hook and name change for time variant file names
  if ((targ=ap_strcasestr(r->args,timearg))&&(fnloc=ap_strstr(fn,tstamp))) { 
    // This part is not apr compatible, since mktime is not available easily
//    apr_time_exp_t tm;
    char old_char=*(fnloc+7);
    targ+=5; // Skip the time= part    

    // Treat "DEFAULT" time parameter same as empty
    if (apr_strnatcasecmp(targ,"default")==0) {
    	targ[0] = 0;
    }

    if (strlen(targ)==24 || strlen(targ)==10 || strlen(targ)==0) { // Make sure time is in correct length
		tm.tm_year=apr_atoi64(targ);
		targ+=5; // Skip the YYYY- part
		tm.tm_mon=apr_atoi64(targ);
		targ+=3; // Skip the MM- part
		tm.tm_mday=apr_atoi64(targ);
		if (strlen(targ)==16 && zlevels==0 && ap_strstr(fn,"TTTTTTTTTTTTT_") != 0) {
			hastime=1;
			targ+=3;
			tm.tm_hour = apr_atoi64(targ);
			targ+=5;
			tm.tm_min = apr_atoi64(targ);
			targ+=5;
			tm.tm_sec = apr_atoi64(targ);
		}
    } else {
    	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Request: %s",r->args);
    	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Invalid time format: %s",targ);
		wmts_add_error(r,400,"InvalidParameterValue","TIME", "Invalid time format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ");
    	return 0;
    }
	if ((tm.tm_year>0)&&(tm.tm_year<9999)&&(tm.tm_mon>0)&&(tm.tm_mon<13)&&(tm.tm_mday>0)&&(tm.tm_mday<32)) { // We do have a time stamp
	  leap=(tm.tm_year%4)?0:((tm.tm_year%400)?((tm.tm_year%100)?1:0):1);
	  tm.tm_yday=tm.tm_mday+moffset[tm.tm_mon-1]+((tm.tm_mon>2)?leap:0);

	  if (hastime==1) {
		  fnloc-=6;
//		  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"time is %04d-%02d-%02dT%02d:%02d:%02d", tm.tm_year, tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
		  sprintf(fnloc,"%04d%03d%02d%02d%02d",tm.tm_year,tm.tm_yday, tm.tm_hour, tm.tm_min, tm.tm_sec);
		  *(fnloc+13)=old_char;
	  } else {
		  sprintf(fnloc,"%04d%03d",tm.tm_year,tm.tm_yday);
		  *(fnloc+7)=old_char;
	  }

	  // Name change for Year
	  if ((yearloc=ap_strstr(fn,year))) {
		  old_char=*(yearloc+4);
		  sprintf(yearloc,"%04d",tm.tm_year); // replace YYYY with actual year
		  *(yearloc+4)=old_char;
	  }
	} else if (tm.tm_year>0) { // Needs to know if there is at least a time value somehow
    	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Invalid time format");
		wmts_add_error(r,400,"InvalidParameterValue","TIME", "Invalid time format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ");
    	return 0;
    }
  }

  // Check if redirected from Mapserver for time snapping
  char *layer = 0;
  char *layers = 0;
  char *prev_time = 0;
  char *new_uri = 0;
  int max_size = 0;
  if (r->prev != 0) {
  			if (r->prev->args && ap_strstr(r->prev->args, "&MAP=") != 0) {
				layer = (char *) apr_table_get(r->prev->notes, "oems_clayer");
				layers = (char *) apr_table_get(r->prev->notes, "oems_layers");
				prev_time = (char *) apr_table_get(r->prev->notes, "oems_time");
				max_size = strlen(r->prev->uri) + strlen(r->prev->args) + strlen(prev_time);
				new_uri = (char*) apr_pcalloc(r->pool, max_size);
				// Set notes for next request
				if (prev_time != 0) {
					apr_table_setn(r->notes, "oems_time", prev_time);
				}
				if (layer != 0) {
					apr_table_setn(r->notes, "oems_clayer", layer);
				}
				if (layers != 0) {
					apr_table_setn(r->notes, "oems_layers", layers);
				}
  			}
  }

  // check if layer has multi-day period if file not found
  if (0>(fd=open(fn,O_RDONLY))) 
  {
	  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"%s is not available",fn);
	  if (!fnloc) {
		  close(fd);
		  return 0;
	  }
	  else {
    		
		  if (sizeof(time_period) > 0) {
			// Fix request time (apache expects to see years since 1900 and zero-indexed months)
			tm.tm_year -= 1900;
			tm.tm_mon -= 1;
		  	int i;
   		    for (i=0;i<num_periods;i++) {
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
			  	apr_time_t req_epoch;

			  	// Can't use the Apache time struct for pre-1970 dates
			  	if (tm.tm_year < 70) {
			  		req_epoch = get_pre_1970_epoch(tm);
			  	} else {
					apr_time_exp_get(&req_epoch, &tm);
			  	}

			  	// First, check if the request date is earlier than the start date of the period. (we don't snap forward)
			  	if (req_epoch < start_epoch) {
			  		// Move to next period
			  		if (i == num_periods) {
			  			break;
			  		} else {
				 		time_period+=strlen(time_period)+1;
				 		continue;
				 	}
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
			  		if (i == num_periods) {
			  			break;
			  		} else {
				 		time_period+=strlen(time_period)+1;
				 		continue;
			  		}
			  	}

			  	// We have a snap date, time to build the filename (remember that tm_yday is zero-indexed)
			  	apr_time_exp_t snap_date = {0};
			  	apr_time_exp_gmt(&snap_date, snap_epoch);

			  	// Fix year part of file path
					if(yearloc != NULL) {
					char oldpath=*(yearloc+4);
					sprintf(yearloc,"%04d",snap_date.tm_year + 1900);
					*(yearloc+4)=oldpath;
			  	}

			  	// Build rest of filename
			  	if (hastime == 0) {
					char old_char=*(fnloc+7);
					sprintf(fnloc,"%04d%03d",snap_date.tm_year + 1900,snap_date.tm_yday + 1);
				  	*(fnloc+7)=old_char;
			  	} else {
					char old_char=*(fnloc+13);
					sprintf(fnloc,"%04d%03d%02d%02d%02d",snap_date.tm_year + 1900,snap_date.tm_yday + 1, snap_date.tm_hour, snap_date.tm_min, snap_date.tm_sec);
					*(fnloc+13)=old_char;
			  	}
			  	// Now let's try the request with our new filename
				ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Snapping to period in file %s",fn);
			    if (0>(fd=open(fn,O_RDONLY))) {
		  		    ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"No valid data exists for time period");
					time_period+=strlen(time_period)+1; // try next period
				} else {
					if (r->prev != 0) {
						if (ap_strstr(r->prev->args, "&MAP=") != 0) {
							char *layer_time = (char*)apr_pcalloc(r->pool, max_size);
							char *layer_subdaily = (char*)apr_pcalloc(r->pool, max_size);
							char *firstpart = (char*)apr_pcalloc(r->pool, max_size);
							char *pos;
							char *split;
							layer_time = apr_psprintf(r->pool,"&%s_TIME=", layer);
							layer_subdaily = apr_psprintf(r->pool,"&%s_SUBDAILY=", layer);
							apr_cpystrn(new_uri, r->prev->args, strlen(r->prev->args)+1);
							pos = ap_strstr(new_uri, layer_time);
							if (pos) {
								size_t len = pos - new_uri;
								memcpy(firstpart, new_uri, len);
							}
							pos += strlen(layer_time)+7;
							if (ap_strstr(r->prev->args, layer_subdaily) != 0) {
								pos += strlen(layer_time)+10;
							}
							new_uri = apr_psprintf(r->pool,"%s?TIME=%s&%s%s%04d%03d&%s_SUBDAILY=%02d%02d%02d%s", r->prev->uri, prev_time, firstpart, layer_time, snap_date.tm_year + 1900, snap_date.tm_yday + 1, layer, snap_date.tm_hour, snap_date.tm_min, snap_date.tm_sec, pos);
							ap_internal_redirect(new_uri, r);
						}
					}
					break;
				}
   		    }
			if (i==num_periods) {
				  // no data found within all periods
				  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Data not found in %d periods", num_periods);
				  if (r->prev != 0) {
						if (ap_strstr(r->prev->args, "&MAP=") != 0) { // Don't include layer in Mapserver request if no time found
							char *args_cpy = (char*)apr_pcalloc(r->pool, strlen(r->prev->args)+1);
						    char *args_pt;
							apr_cpystrn(new_uri, r->prev->args, strlen(r->prev->args)+1);
							args_pt = ap_strstr(new_uri, layer);
							if (args_pt != NULL) {
								size_t len = args_pt - new_uri;
								memcpy(args_cpy, new_uri, len);
							}
							if (args_pt[strlen(layer)] == ',') {
								args_pt += strlen(layer)+1;
							} else {
								args_pt += strlen(layer);
								args_cpy[strlen(args_cpy)-1] = 0;
							}
							apr_table_setn(r->notes, "oe_error", "Invalid TIME.");
							new_uri = apr_psprintf(r->pool, "%s?%s%s", r->prev->uri, args_cpy, args_pt);
							ap_internal_redirect(new_uri, r);
						}
				  }
			}
		}
	  }
  } else {
	  if (r->prev != 0) {
			if (r->prev->args && ap_strstr(r->prev->args, "&MAP=") != 0) { // no time-snapping for Mapserver, so redirect back
				new_uri = apr_psprintf(r->pool, "%s?TIME=%s&%s", r->prev->uri, prev_time, r->prev->args);
				ap_internal_redirect(new_uri, r);
			}
	  }
  }

  readbytes=pread64(fd,buffer,nbytes,location);
//  if (readbytes!=nbytes) {
//	  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Error reading from %s, read %ld instead of %ld, from %ld",fn,readbytes,nbytes,location);
//  }
  close(fd);
  return (readbytes==nbytes)?buffer:0;
}

char *get_keyword(request_rec *r) {
	  char *keyword = apr_pcalloc(r->pool,24);

	  static char* timearg="time=";
	  static char* stylearg="style=";
	  char *targ=0;
	  char *sarg=0;
	  apr_time_exp_t tm; tm.tm_year=0; tm.tm_mon=0; tm.tm_mday=0; tm.tm_hour=0; tm.tm_min=0; tm.tm_sec=0;

	  // Assume keyword is time for granules
	  if ((targ=ap_strcasestr(r->args,timearg))) {
	    targ+=5; // Skip the time= part
	    if (strlen(targ)==24) { // Make sure time is in correct length
			tm.tm_year=apr_atoi64(targ);
			targ+=5; // Skip the YYYY- part
			tm.tm_mon=apr_atoi64(targ);
			targ+=3; // Skip the MM- part
			tm.tm_mday=apr_atoi64(targ);
			if (strlen(targ)==16) {
				targ+=3;
				tm.tm_hour = apr_atoi64(targ);
				targ+=5;
				tm.tm_min = apr_atoi64(targ);
				targ+=5;
				tm.tm_sec = apr_atoi64(targ);
			}
			// Check if keyword should also include style
	    	if ((sarg=ap_strcasestr(r->args,stylearg))) {
	    		sarg+=6; // Skip the style= part
	    		apr_cpystrn(keyword, sarg, 8);
	    		if (ap_strstr(keyword,"encoded")) {
	    			sprintf(keyword,"%04d%02d%02d%02d%02d%02d|encoded",tm.tm_year,tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
	    		} else {
	    			sprintf(keyword,"%04d%02d%02d%02d%02d%02d",tm.tm_year,tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
	    		}
	    	}
	    	else {
	    		sprintf(keyword,"%04d%02d%02d%02d%02d%02d",tm.tm_year,tm.tm_mon, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
	    	}
	    } else {
	    	// Check if keyword should be style
	    	if ((sarg=ap_strcasestr(r->args,stylearg))) {
	    		sarg+=6; // Skip the style= part
	    		apr_cpystrn(keyword, sarg, 8);
	    		if (ap_strstr(keyword,"&TILEMA")) { // handle default styling
	    			sprintf(keyword,"");
	    		}
	    	}
//	    	else if (strlen(targ)!=0) {
//				ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Request: %s",r->args);
//				ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Invalid time format: %s",targ);
//				wmts_add_error(r,400,"InvalidParameterValue","TIME", "Invalid time format, granules must be YYYY-MM-DDThh:mm:ssZ");
//				return 0;
//	    	}
	    }
	  }

	  return keyword;
}

// Lookup the z index from ZDB file based on keyword
static int get_zlevel(request_rec *r, char *zidxfname, char *keyword) {
//	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Get z-index from %s with keyword %s", zidxfname, keyword);

    sqlite3 *db;
    sqlite3_stmt *res;

    int z = -1;
    int rc = sqlite3_open_v2(zidxfname, &db, SQLITE_OPEN_READONLY, NULL);

    if (keyword==0) { // Bail if keyword is an error code
    	return -1; 
    }

    if (rc != SQLITE_OK) {
        ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Cannot get z-index from %s", zidxfname);
        sqlite3_close(db);
        return -1;
    }

    char *sql = strlen(keyword)!=0 ? "SELECT * FROM ZINDEX WHERE key_str = ? LIMIT 1" :  "SELECT * FROM ZINDEX WHERE key_str NOT LIKE '%encoded%' ORDER BY key_str DESC LIMIT 1";
    rc = sqlite3_prepare_v2(db, sql, -1, &res, 0);

    if (rc != SQLITE_OK) {
    	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Failed to fetch data from %s", zidxfname);
        sqlite3_close(db);
        return -1;
    } else if (strlen(keyword)!=0) {
        sqlite3_bind_text(res, 1, keyword, strlen(keyword), SQLITE_STATIC);
    }

    rc = sqlite3_step(res);

    if (rc == SQLITE_ROW) {
    	z = apr_atoi64((char*)sqlite3_column_text(res, 0));
    	if (sqlite3_column_count(res) > 1) { // Check if there is a key_str column
    		if (strcmp(sqlite3_column_name(res, 1), "key_str") == 0) {
				char *key = apr_pcalloc(r->pool,strlen(sqlite3_column_text(res, 1))+1);
				apr_cpystrn(key, (char*)sqlite3_column_text(res, 1), strlen(sqlite3_column_text(res, 1))+1);
				apr_table_setn(r->headers_out, "Source-Key", key);
    		}
    	}
    	if (sqlite3_column_count(res) > 2) { // Check if there is a source_url column
    		if (strcmp(sqlite3_column_name(res, 2), "source_url") == 0) {
    			if (sqlite3_column_text(res, 2) != NULL) {
					char *source_data = apr_pcalloc(r->pool,strlen(sqlite3_column_text(res, 2))+1);
					apr_cpystrn(source_data, (char*)sqlite3_column_text(res, 2), strlen(sqlite3_column_text(res, 2))+1);
					apr_table_setn(r->headers_out, "Source-Data", source_data);
    			}
    		}
    	}
    	if (sqlite3_column_count(res) > 5) { // Check if there are scale, offset, and uom columns
    		if (strcmp(sqlite3_column_name(res, 3), "scale") == 0) {
    			if (sqlite3_column_text(res, 3) != NULL) {
					char *scale = apr_pcalloc(r->pool,strlen(sqlite3_column_text(res, 3))+1);
					apr_cpystrn(scale, (char*)sqlite3_column_text(res, 3), strlen(sqlite3_column_text(res, 3))+1);
					apr_table_setn(r->headers_out, "Scale", scale);
    			}
    		}
    		if (strcmp(sqlite3_column_name(res, 4), "offset") == 0) {
    			if (sqlite3_column_text(res, 4) != NULL) {
    				char *offset = apr_pcalloc(r->pool,strlen(sqlite3_column_text(res, 4))+1);
					apr_cpystrn(offset, (char*)sqlite3_column_text(res, 4), strlen(sqlite3_column_text(res, 4))+1);
					apr_table_setn(r->headers_out, "Offset", offset);
    			}
    		}
    		if (strcmp(sqlite3_column_name(res, 5), "uom") == 0) {
    			if (sqlite3_column_text(res, 5) != NULL) {
    				char *uom = apr_pcalloc(r->pool,strlen(sqlite3_column_text(res, 5))+1);
					apr_cpystrn(uom, (char*)sqlite3_column_text(res, 5), strlen(sqlite3_column_text(res, 5))+1);
					apr_table_setn(r->headers_out, "UOM", uom);
    			}
    		}
    	}
    } else {
    	wmts_add_error(r,404,"ImageNotFound","TIME", "Image cannot be found for the requested date and time");
    }

    sqlite3_finalize(res);
    sqlite3_close(db);

	return z;
}

static int withinbbox(WMSlevel *level, double x0, double y0, double x1, double y1) {
  return (!((level->X0>=x1)||(level->X1<=x0)||(level->Y0>=y1)||(level->Y1<=y0)));
}

static int kml_return_error(request_rec *r, char *message)
{
// Returning the error message in KML would be in agreement
// with the inimage error return.
// For now, this is identical to the wms error return
static char preamble[]=
"<?xml version='1.0' encoding=\"UTF-8\" standalone=\"no\" ?>\n"
"<!DOCTYPE ServiceExceptionReport SYSTEM \"http://schemas.opengeospatial.net/wms/1.1.1/exception_1_1_1.dtd \">\n"
"<ServiceExceptionReport version=\"1.1.0\"><ServiceException>\n";
static char postamble[]="</ServiceException></ServiceExceptionReport>" ;

    ap_set_content_type(r,"application/vnd.ogc.se_xml");
    ap_rputs(preamble, r);
    ap_rputs(message  ,r);
    ap_rputs(postamble,r);
    return OK; // Request handled
}

static int wms_return_error(request_rec *r, char *message)
{
static char preamble[]=
"<?xml version='1.0' encoding=\"UTF-8\" standalone=\"no\" ?>\n"
"<!DOCTYPE ServiceExceptionReport SYSTEM \"http://schemas.opengeospatial.net/wms/1.1.1/exception_1_1_1.dtd \">\n"
"<ServiceExceptionReport version=\"1.1.0\"><ServiceException>\n";
static char postamble[]="</ServiceException></ServiceExceptionReport>" ;

    ap_set_content_type(r,"application/vnd.ogc.se_xml");
    ap_rputs(preamble, r);
    ap_rputs(message  ,r);
    ap_rputs(postamble,r);
    return OK; // Request handled
}

static int wmts_add_error(request_rec *r, int status, char *exceptionCode, char *locator, char *exceptionText)
{

	wmts_error error;
	error.status = status;
	error.exceptionCode = exceptionCode;
	error.locator = locator;
	error.exceptionText = exceptionText;

	wmts_errors[errors] = error;
	errors++;

    return OK; // Request handled
}

static int wmts_return_all_errors(request_rec *r)
{

	static char preamble[]=
			"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
			"<ExceptionReport xmlns=\"http://www.opengis.net/ows/1.1\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd\" version=\"1.1.0\" xml:lang=\"en\">";
	static char postamble[]="\n</ExceptionReport>" ;

	ap_set_content_type(r,"text/xml");
	ap_rputs(preamble, r);

	int i;
	for(i = 0; i < errors; i++)
	{
		wmts_error error = wmts_errors[i];

		static char preexception[]="\n<Exception exceptionCode=\"";
		static char prelocator[]="\" locator=\"";
		static char postlocator[]="\">";
		static char pretext[]="\n<ExceptionText>";
		static char posttext[]="</ExceptionText>";
		static char postexception[]="</Exception>";

		ap_rputs(preexception, r);
		ap_rputs(error.exceptionCode, r);
		ap_rputs(prelocator, r);
		ap_rputs(error.locator, r);
		ap_rputs(postlocator, r);
		ap_rputs(pretext, r);
		ap_rputs(error.exceptionText, r);
		ap_rputs(posttext, r);
		ap_rputs(postexception, r);

		r->status = error.status;
		error.exceptionCode = 0;
	}

	ap_rputs(postamble, r);
	errors = 0;

    return OK; // Request handled
}

// It should be done for each server independently
// arg is the value of the WMSCache directive, this is the init function.

static const char *cache_dir_set(cmd_parms *cmd,void *dconf, const char *arg)
{
  static char msg_onlyone[]="Only one cache configuration allowed";

  server_rec *server=cmd->server;
  wms_cfg *cfg=(wms_cfg *)dconf;
  int f;
  int readb;
  int cachesize,count;
  Caches *caches; // Pointer to where the cache config file is loaded
  cfg->dir = cmd->path; // Need directory path to translate REST calls properly

  // This should never happen
  if (!cfg) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server, "Can't find module configuration");
    return 0;
  }

  if (cfg->caches) return msg_onlyone;

  if (0>(f=open(arg,O_RDONLY))) { 
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server, 
    		"MOD_ONEARTH: Can't open cache config file\n file %s: %s",arg,strerror(errno));
    cfg->caches=(Caches *)apr_pcalloc(cfg->p,sizeof(Caches));
    cfg->caches->size=0 ; cfg->caches->count=0;
    close(f);
    return 0;
  }

  readb=read(f,&cachesize,sizeof(cachesize));
  if (sizeof(cachesize)!=readb)
  {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
		"Can't read from configuration file");
    close(f);
    return 0;
  }
  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server, 
  		"Cache file size is %d", cachesize);

  if (!(caches=(Caches *)apr_pcalloc(cfg->p, cachesize))) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
		"Can't get memory for cache configuration");
    close(f); return 0;
  }

  caches->size=cachesize;
  // Read the rest of the cache file and close it
  readb=read(f,&(caches->count),cachesize-sizeof(cachesize));
  close(f);
  if (cachesize-sizeof(cachesize)!=readb)
  {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
		"Can't read from configuration file");
    return 0;
  }

  // Hook it up
  cfg->caches=caches;
  // Store the directory
  cfg->cachedir=ap_make_dirstr_parent(cfg->p,arg);
  count=caches->count;
  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server,
       "Cache count is %d", count);

  // Now prepare the regexps and mime types
  cfg->meta=(meta_cache *)apr_pcalloc(cfg->p,count*sizeof(meta_cache));

  while (count--) {
    int i;
    char *pattern;
    WMSCache *cache;

    // Compile the regexp(s)
    cache=GETCACHE(caches,count);

    // Adjust the relative pointers, by adding the start of the real storage area
    cache->pattern+=(apr_off_t)caches;
    cache->prefix+=(apr_off_t)caches;
    cache->time_period+=(apr_off_t)caches;
    cache->zidxfname+=(apr_off_t)caches;

    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server,
      "Cache number %d at %llx, count %d, first string %s",count,(long long) cache,
      cache->num_patterns,cache->pattern);

    // Allocate the table for regexps
    cfg->meta[count].regex=
      (ap_regex_t**) apr_pcalloc(cfg->p, (cache->num_patterns)*sizeof(ap_regex_t *));
    pattern=cache->pattern;
    for (i=0;i<cache->num_patterns;i++) {
      if (!(cfg->meta[count].regex[i]=ap_pregcomp(cfg->p,pattern,0)))
	ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
	  "Can't compile expression %s",pattern);
      pattern+=strlen(pattern)+1; // Skip the zero at the end, ready for the next one
    }

    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server,
       "Cache %d has %d levels",count,cache->levels);
    
    if (cache->levels) {
      int lev_num;
      WMSlevel *levelt= GETLEVELS(cache); // Table of offsets
      ap_log_error(APLOG_MARK,APLOG_DEBUG,0,server,
        "Cache has %d levels", cache->levels);
      // Set the type
      if (ap_find_token(cfg->p,cache->prefix,"jpeg")) 
	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"image/jpeg");
      else if (ap_find_token(cfg->p,cache->prefix,"png")) 
	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"image/png");
      else if (ap_find_token(cfg->p,cache->prefix,"tiff"))
 	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"image/tiff");
      else if (ap_find_token(cfg->p,cache->prefix,"lerc"))
 	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"image/lerc");
      else if (ap_find_token(cfg->p,cache->prefix,"x-protobuf;type=mapbox-vector"))
 	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"application/x-protobuf;type=mapbox-vector");
      else if (ap_find_token(cfg->p,cache->prefix,"vnd.mapbox-vector-tile"))
 	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"application/vnd.mapbox-vector-tile");
      else {
	ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
	  "Type not found, using text/html for cache %s", cache->pattern);
	cfg->meta[count].mime_type=apr_pstrdup(cfg->p,"text/html");
      }
      cfg->meta[count].empties=apr_pcalloc(cfg->p, cache->levels*sizeof(wms_empty_record));

      // Initialize the empties and use this loop to adjust all the string name pointers 
      for (lev_num=0;lev_num<cache->levels;lev_num++,levelt++) {
	WMSlevel *prev_level=levelt-1; // preceding level
	// We might as well use this loop to adjust all the file name
	// pointers
	levelt->dfname+=(apr_off_t)caches;
	levelt->ifname+=(apr_off_t)caches;

	cfg->meta[count].empties[lev_num].data=0;
	cfg->meta[count].empties[lev_num].index.size   = 
	    levelt->empty_record.size;
	cfg->meta[count].empties[lev_num].index.offset = 
	    levelt->empty_record.offset;

	// Read them, if available
        if (levelt->empty_record.size) {
	  //
	  // To save space, since most levels of a cache use the same empty tile
	  // Use the previous level if the information matches
	  // The dfname is a direct pointer comparison
	  //
	  if ((lev_num>0) && 
	      (prev_level->empty_record.size==levelt->empty_record.size) &&
	      (prev_level->empty_record.offset==levelt->empty_record.offset) &&
	      (prev_level->dfname==levelt->dfname)) { 
	    // All match
	    cfg->meta[count].empties[lev_num].data=
		cfg->meta[count].empties[lev_num-1].data;
	  } else { 
	    // Try to read the record
		  char *dfname;
		  if (levelt->dfname[0] == '/') { // decide absolute or relative path from cachedir
			  dfname = apr_pstrcat(cfg->p,levelt->dfname,0);
		  } else {
			  dfname = apr_pstrcat(cfg->p,cfg->cachedir,levelt->dfname,0);
		  }
		  cfg->meta[count].empties[lev_num].data=
				  p_file_pread(cfg->p,dfname,
						  levelt->empty_record.size,levelt->empty_record.offset);
	  }

	  // If an error happened, report and mark it as unavailable to prevent crashes
	  if (!cfg->meta[count].empties[lev_num].data) {
	    ap_log_error(APLOG_MARK,APLOG_ERR,0,server,
		"Failed empty tile read for %s level %d, %d bytes at %d", 
		cache->pattern, lev_num, 
		(int) cfg->meta[count].empties[lev_num].index.size,
		(int) cfg->meta[count].empties[lev_num].index.offset);
	    cfg->meta[count].empties[lev_num].index.size=0;
	  }
        }
      }
    }
  }
  return 0;
}

// find the string "bbox=", return a pointer after the equal sign
// Might be faster to use regex, but this should be faster

static char *getbbox(char *arg) {
  // At least four characters are still there, guaranteed by regexp
  // The 0x20 makes it case insensitive
  while (arg[5]) {
    if ( (arg[0]==arg[1]) && ((arg[1]|0x20)=='b') && 
       ((arg[2]|0x20)=='o') && ((arg[3]|0x20)=='x') && (arg[4]=='=') )
        return arg+5; // return a pointer after the equal sign
    arg++;
  }
  return 0; // We reached the end of string, found nothing
}

// find the end character of the bbox arguments
// Skips [0123456789,-.+]

static char *getbboxend(char *arg) {
  char c;
  while (0!=(c=*arg)) {
    if (!((('0'<=c)&&(c<='9'))||
        (c==',')||(c=='.')||(c=='-')||(c=='+')))
      break;
    arg++;
  }
  return arg;
}

// Find a level which matches the WMTS request
// Returns 0 if not found
// Returns 1 (can't be a pointer) if request is bad
//
// WARNING
// This function makes assumptions:
//   That the tilematrix parameter is uppercase
//   That the tilematrix value is equal to the level, with zero being the lowest res
//   That levels in the cache config are successive in increasing res order
//

static WMSlevel *wmts_get_matching_level(request_rec *r,
		WMSCache *cache)
{

   unsigned char *args;
   char *pszl;
   int lcount,i;

   //ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
   //   "In wmts_get_matching_level");
   // Convert the whole input string to uppercase
   args=(unsigned char *)apr_pstrdup(r->pool,r->args);
   for (i=0;args[i]!=0;i++) args[i]=apr_toupper(args[i]);

   if (!(pszl=ap_strstr(apr_pstrdup(r->pool,r->args),Matrix)))
     return (WMSlevel *)1;

   lcount=apr_atoi64(pszl+matrix_len);
   if (lcount>=cache->levels)
     return (WMSlevel *)0;
  
   return GETLEVELS(cache)+cache->levels-1-lcount;
}

// Find a level which matches
// Returns 0 if not found
// Returns 1 if bbox is broken, can't be a real pointer
// Returns 2 if bbox is too far from binary level
static WMSlevel *wms_get_matching_level(request_rec *r,
                WMSCache *cache, wms_wmsbbox *bb)

{
  char *bbstring;

  double plevel;
  int i;
  WMSlevel *levelt;
  
  if (!(bbstring=getbbox(r->args))) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "No bbox found");
    return 0; // no bbox no match
  }

  // only four floating point numbers allowed in bbox param
  // Five might mean a bad floating point separator
  if (4!=sscanf(bbstring,"%lf,%lf,%lf,%lf,%lf",
                &bb->x0,&bb->y0,&bb->x1,&bb->y1, &plevel))
    return (WMSlevel *)1; // Error code, bad bbox

  plevel=bb->x1-bb->x0; // Target level

  levelt=GETLEVELS(cache);

  for (i=cache->levels;i;i--,levelt++) 
    if ( (plevel>levelt->levelx*0.965)&&
         (plevel<levelt->levelx*1.035) ) break;

  return i?levelt:0; // Zero is not found, othewise it returns a pointer
}

static apr_off_t wmts_get_index_offset(request_rec *r, WMSlevel *level)
{
 char *args;
 char *pszx,*pszy;
 // The tile indices are directly passed from the top-left
 int x,y,i;
 
 //ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
 //     "In wmts_get_index_offset");

 // Convert the whole input string to uppercase
 args=apr_pstrdup(r->pool,r->args);
 for (i=0;args[i]!=0;i++) args[i]=apr_toupper(args[i]);

 pszx=ap_strstr(args,"TILEROW=");
 pszy=ap_strstr(args,"TILECOL=");

 if ((0==pszx)||(0==pszy)) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Can't find TILEROW= or TILECOL= in %s",
    	r->args);
    return -1;
 }

 y=apr_atoi64(pszx+8);
 x=apr_atoi64(pszy+8);
 //ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
 //     "In wmts_get_index_offset col %d row %d",x,y);

 if (x<0 || x>=level->xcount || y<0 || y>=level->ycount ) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Col or Row overflow, max values are %d and %d, %s ",
    	level->xcount-1, level->ycount-1, r->args);
    if (x<0 || x>=level->xcount) {
    	char *tilecol_mes = apr_psprintf(r->pool, "TILECOL is out of range, maximum value is %d",level->xcount-1);
    	wmts_add_error(r,400,"TileOutOfRange","TILECOL", tilecol_mes);
    }
    if (y<0 || y>=level->ycount) {
    	char *tilerow_mes = apr_psprintf(r->pool, "TILEROW is out of range, maximum value is %d",level->ycount-1);
    	wmts_add_error(r,400,"TileOutOfRange","TILEROW", tilerow_mes);
    }
    return -1;
 }
// int level_int = level->index_add + sizeof(index_s) * (y*level->xcount+x);
// ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "offset: %d, max values are %d and %d, x: %d, y: %d, index_add: %d",
//		 level_int, level->xcount-1, level->ycount-1, x, y, level->index_add);
 return level->index_add + sizeof(index_s) * (y*level->xcount+x);
 
}

static apr_off_t wmts_get_index_offset_z(request_rec *r, WMSlevel *level, long long z, long long zlevels)
{
 char *args;
 char *pszx,*pszy;
 // The tile indices are directly passed from the top-left
 long long x,y,i;

 // Convert the whole input string to uppercase
 args=apr_pstrdup(r->pool,r->args);
 for (i=0;args[i]!=0;i++) args[i]=apr_toupper(args[i]);

 pszx=ap_strstr(args,"TILEROW=");
 pszy=ap_strstr(args,"TILECOL=");

 if ((0==pszx)||(0==pszy)) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Can't find TILEROW= or TILECOL= in %s",
    	r->args);
    return -1;
 }

 if (z >= zlevels) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Requested z %d is greater than max z-level %d", z, zlevels-1);
    return 0;
 }

 y=apr_atoi64(pszx+8);
 x=apr_atoi64(pszy+8);

 if (x<0 || x>=level->xcount || y<0 || y>=level->ycount ) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Col or Row overflow, max values are %d and %d, %s ",
    	level->xcount-1, level->ycount-1, r->args);
    if (x<0 || x>=level->xcount) {
    	char *tilecol_mes = apr_psprintf(r->pool, "TILECOL is out of range, maximum value is %d",level->xcount-1);
    	wmts_add_error(r,400,"TileOutOfRange","TILECOL", tilecol_mes);
    }
    if (y<0 || y>=level->ycount) {
    	char *tilerow_mes = apr_psprintf(r->pool, "TILEROW is out of range, maximum value is %d",level->ycount-1);
    	wmts_add_error(r,400,"TileOutOfRange","TILEROW", tilerow_mes);
    }
    return -1;
 }

 long long level_int = level->index_add + sizeof(index_s) * (y*level->xcount+x);
 long long level_z = (level->xcount*level->ycount*zlevels)*sizeof(index_s)/zlevels*z;

// ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "offset: %d, max values are %d and %d, x: %d, y: %d, index_add: %d",
//		 level_int+level_z, level->xcount-1, level->ycount-1, x, y, level->index_add);

 return level_int+level_z;
}


static apr_off_t get_index_offset(WMSlevel *level, wms_wmsbbox *bb,
                                  int ori,request_rec *r) 

{
  apr_off_t ix,iy;
  double x,y;

  if (ori &0x2) 
    ix=0.5+(x=((level->X1-bb->x1)/level->levelx));
  else
    ix=0.5+(x=((bb->x0-level->X0)/level->levelx));

  if (ori & 0x1)
    iy=0.5+(y=((bb->y0-level->Y0)/level->levely));
  else
    iy=0.5+(y=((level->Y1-bb->y1)/level->levely));

  // Alignment too far, more than +-1% off
  if ((x-ix)>0.01 || (ix-x)>0.01 || (y-iy)>0.01 || (iy-y)>0.01) {
    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server, "Slightly off : "
      "ix %d ,x %f ,iy %d,y %f, Level x %f y %f, page count x %d y %d\n",
      (int) ix,x,(int) iy,y,
      level->levelx,level->levely,level->xcount,level->ycount );
    return -2;
  }


  // Non existing level

  if ( (ix<0) || (ix>=level->xcount) ||
       (iy<0) || (iy>=level->ycount) )
    return -1;

//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
//    "ix %d ,x %d ,iy %d,y %d, Level x %d y %d, page count x %d y %d\n",
//    ix,x,iy,y,
//    level->levelx,level->levely,level->xcount,level->ycount );

//  int level_int = level->index_add+sizeof(index_s)*(iy*level->xcount+ix);
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "offset: %d",
// 		 level_int);

  return 
    level->index_add+sizeof(index_s)*(iy*level->xcount+ix);
}

static apr_off_t twms_get_index_offset_z(WMSlevel *level, wms_wmsbbox *bb,
                                  int ori, long long z, long long zlevels, request_rec *r)
{
  apr_off_t ix,iy;
  double x,y;

  if (ori &0x2) 
    ix=0.5+(x=((level->X1-bb->x1)/level->levelx));
  else
    ix=0.5+(x=((bb->x0-level->X0)/level->levelx));

  if (ori & 0x1)
    iy=0.5+(y=((bb->y0-level->Y0)/level->levely));
  else
    iy=0.5+(y=((level->Y1-bb->y1)/level->levely));

  // Alignment too far, more than +-1% off
  if ((x-ix)>0.01 || (ix-x)>0.01 || (y-iy)>0.01 || (iy-y)>0.01) {
    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server, "Slightly off : "
      "ix %d ,x %f ,iy %d,y %f, Level x %f y %f, page count x %d y %d\n",
      (int) ix,x,(int) iy,y,
      level->levelx,level->levely,level->xcount,level->ycount );
    return -2;
  }

  // Non existing level

  if ( (ix<0) || (ix>=level->xcount) ||
       (iy<0) || (iy>=level->ycount) )
    return -1;

//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
//    "ix %d ,x %d ,iy %d,y %d, Level x %d y %d, page count x %d y %d\n",
//    ix,x,iy,y,
//    level->levelx,level->levely,level->xcount,level->ycount );

//  int level_int = level->index_add+sizeof(index_s)*(iy*level->xcount+ix);
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "offset: %d",
// 		 level_int);
 long long level_int = level->index_add + sizeof(index_s) * (iy*level->xcount+ix);
 long long level_z = (level->xcount*level->ycount*zlevels)*sizeof(index_s)/zlevels*z;
 return level_int+level_z;
  // return 
  //   level->index_add+sizeof(index_s)*(iy*level->xcount+ix);
}

// Escapes the ampersand as ampersand command
// Returns pointer to EOS
char *escape_ampersand(char *source, char *dest) {

  while (0!=(*dest=*source++))
    if ('&'==*dest++) { 
      *dest++='a';
      *dest++='m';
      *dest++='p';
      *dest++=';'; 
  }
  return dest;
}

//
// Brings back the host + uri parts of the request as a string.
// The alias part is not done
//

char * hname( request_rec *r, int use_alias) {

    const int ssz=128;
    char *hn,*h; // H is the insertion point
    int i;

    // Host name storage
    hn=apr_pcalloc(r->pool,ssz);
  

    // use the incoming request host name if conditions are not met
    if ( 0==use_alias || 80 != r->connection->local_addr->port || 0== (r->server->wild_names->nelts + r->server->names->nelts ) ) {
        if (80!=r->connection->local_addr->port)
          h=hn+snprintf(hn,ssz,"%s:%d",r->hostname,r->connection->local_addr->port);
	else
          h=apr_cpystrn(hn,r->hostname,ssz);
    } else { // We got other aliases and no special port
    
        char **wnms=0 , **nms=0;
        // Which one we pick
	int sel=0;
	int n_nms,n_wnms,nelts;

	// These can be null pointers, so we have to guard agains
        if (r->server->wild_names) wnms=(char **)(r->server->wild_names->elts);
        if (r->server->names) nms=(char **)(r->server->names->elts);

	// Total number of names we could use
        n_nms=(0==nms)?0:r->server->names->nelts;
        n_wnms=(0==wnms)?0:r->server->wild_names->nelts;
	nelts=1+n_nms+n_wnms;

	// List the full host aliases
	if (nms) {
	    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server,
			"Hostaliases count %d",r->server->names->nelts);
	    for (i=0;i < r->server->names->nelts; i++)
		  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server,
			"Hostaliases %s",nms[i]);
	}

	// List the wildcard host aliases
	if (wnms) {
	    ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server,
			"Wild Hostaliases count %d",r->server->wild_names->nelts);
	    for (i=0;i < r->server->wild_names->nelts; i++)
		  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server,
			"Wild Hostaliases %s",wnms[i]);
	}

	apr_generate_random_bytes((unsigned char *)&sel,sizeof(sel));
	sel&=0x7fff;  // Make it positive
	sel%=nelts; // Pick one

	if (sel==0) { // The normal host name
	    h=apr_cpystrn(hn,r->server->server_hostname,ssz);
	} else if ( n_nms && (sel < n_nms +1 )) {
	   // One of the full aliases
	    h=apr_cpystrn(hn,nms[sel-1],ssz);
	} else { // It is here for sure
	    // Wildcard aliases, this could be broken.  Assume 
	    // the wildcard is the domainname
	    h=apr_cpystrn(hn,nms[sel-1-n_nms],ssz);
	    // Does it have a wildcard
	    if (!(h=ap_strchr(hn,'*'))) // Ups, stay safe
	      h=apr_cpystrn(hn,r->hostname,ssz);
	    else // Append the domainname
	      h=apr_cpystrn(h,ap_strchr(r->hostname,'.'),ssz-(h-hn));
	}

    }

    // Append the URI
    apr_cpystrn(h,r->uri,ssz-(h-hn));
    return hn;
}

// This function generates the four sublinks if required
static void PrintLink(request_rec *r, wms_wmsbbox *bbox, WMSlevel *level, char *outqs,
			char *postamble) {

  double e,w,n,s;
  double midlon,midlat;

  const char *NetworkLink="<NetworkLink><name>None%d</name><Region>\n"
       "<LatLonAltBox><north>%12.10f</north><south>%12.10f</south>"
       "<east>%12.10f</east><west>%12.10f</west></LatLonAltBox>\n"
       "<Lod><minLodPixels>128</minLodPixels><maxLodPixels>4096</maxLodPixels></Lod></Region>\n"
       "<Link><href>http://%s?%sbbox=%12.10f,%12.10f,%12.10f,%12.10f%s</href>"
       "<viewRefreshMode>onRegion</viewRefreshMode></Link></NetworkLink>\n";

  n=bbox->y1;s=bbox->y0;e=bbox->x1;w=bbox->x0;
  // Center coordinates
  midlon=(e+w)/2;
  midlat=(n+s)/2;

  hname(r,0);

//  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server, "Start URL should be %s",hname(r,1));

  if (withinbbox(level,w,midlat,midlon,n))
    ap_rprintf(r,NetworkLink,rand(),n,midlat,midlon,w,
	       hname(r,0),outqs,w,midlat,midlon,n,postamble);
  if (withinbbox(level,midlon,midlat,e,n))
    ap_rprintf(r,NetworkLink,rand(),n,midlat,e,midlon,
	       hname(r,0),outqs,midlon,midlat,e,n,postamble);
  if (withinbbox(level,w,s,midlon,midlat))
    ap_rprintf(r,NetworkLink,rand(),midlat,s,midlon,w,
	       hname(r,0),outqs,w,s,midlon,midlat,postamble);
  if (withinbbox(level,midlon,s,e,midlat))
    ap_rprintf(r,NetworkLink,rand(),midlat,s,e,midlon,
	       hname(r,0),outqs,midlon,s,e,midlat,postamble);

}

/*
 * This is the kml handler, it generates the subrequests if there is a match,
 * or a simple kml wrapper if there is no cache.  This makes the backing WMS
 * implementation able to handle native KML
 */

static int kml_handler (request_rec *r)

{
  wms_cfg  *cfg;
  WMSCache *cache;
  WMSlevel *level;
  WMSlevel *levelt;

  int i;
  char *format_p;
  char *the_rest;
  char *bbox_p;
  char *bbox_end;

  char outqs[3000]; // Place to hold the quoted start of the request
  char postamble[3000]; // Place to hold the end of the request
  char *image_arg;

  int count;
  wms_wmsbbox bbox;
  int subdivide=0;
  int dorder;
  double e,w,n,s;

  const char* preamble="<kml><Document>\n"
    "<Region><LatLonAltBox>\n"
    "<north>%12.10f</north><south>%12.10f</south><east>%12.10f</east><west>%12.10f</west>\n"
    "<minAltitude>0.0</minAltitude><maxAltitude>0.0</maxAltitude>\n"
    "</LatLonAltBox><Lod><minLodPixels>128</minLodPixels><maxLodPixels>4096</maxLodPixels></Lod></Region>\n";

  char *GrndOvlay="<GroundOverlay><drawOrder>%d</drawOrder>\n"
    "<Icon><href>http://%s?%s</href>\n"
    "</Icon><LatLonBox>\n"
    "<north>%12.10f</north><south>%12.10f</south><east>%12.10f</east><west>%12.10f</west>\n"
    "</LatLonBox></GroundOverlay></Document></kml>\n";

  // Get the configuration
  cfg=(wms_cfg *) 
    ap_get_module_config(r->per_dir_config,&onearth_module);

  if ((0==cfg)||(0==cfg->caches)||(0==cfg->caches->count)) return DECLINED; // No caches

  count=cfg->caches->count;

  // Look for a google-earth request type
  format_p=ap_strstr(r->args,kmltype);
  // Paranoid check, this is guaranteed by the caller
  if (0==format_p) return DECLINED;

  // Pointer to the remainder of the paramter string
  the_rest=format_p+kmlt_len;

  *format_p=0; // Terminate the request there
 
  // Try a png request first
  image_arg=apr_pstrcat(r->pool,r->args,"image%2Fpng",the_rest,0);

  while (count--) {
    int i;
    cache=GETCACHE(cfg->caches,count);
    i=cache->num_patterns;
    while (i--)
      if (!ap_regexec(cfg->meta[count].regex[i],image_arg,0,NULL,0)) 
        break;
    if (-1!=i) break; // Break out of this while also, we don't need the argument any more
  }

  if (-1==count) { // No match for the png, maybe a jpeg?
    count=cfg->caches->count;
    image_arg=apr_pstrcat(r->pool,r->args,"image%2Fjpeg",the_rest,0);
    while (count--) {
      int i;
      cache=GETCACHE(cfg->caches,count);
      i=cache->num_patterns;
      while (i--) {
        if (!ap_regexec(cfg->meta[count].regex[i],image_arg,0,NULL,0)) 
          break;
      }
      if (-1!=i) break; // Break out of this while also, we don't need the argument any more
    } 

    if (-1==count) { // No string match with a jpeg either, wrap the WMS in KML
      char *bbstring;
      double w,s,e,n,dummy;
      static const char* kmlpreamble="<kml><Document>\n"
	"<Region><LatLonAltBox>\n"
	"<north>%12.10f</north><south>%12.10f</south><east>%12.10f</east><west>%12.10f</west>\n"
	"<minAltitude>0.0</minAltitude><maxAltitude>0.0</maxAltitude>\n"
	"</LatLonAltBox></Region>\n";

      char *kmlGrndOvlay="<GroundOverlay>\n"
	"<Icon><href>http://%s?%s</href>\n"
	"</Icon><LatLonBox>\n"
	"<north>%12.10f</north><south>%12.10f</south><east>%12.10f</east><west>%12.10f</west>\n"
	"</LatLonBox></GroundOverlay></Document></kml>\n";

      // Set the type
      // Copy the args up to bbox to outqs while escaping the ampersand
      *format_p=kmltype[0]; // Put the first letter back for the following KMLs
      if (!(bbstring=getbbox(r->args)))
	return kml_return_error(r,"bbox: required parameter mising!");
      if (4!=sscanf(bbstring,"%lf,%lf,%lf,%lf,%lf",
		    &w,&s,&e,&n, &dummy))
	return kml_return_error(r,"bbox: values can't be parsed!");

      ap_set_content_type(r,kmltype);
      ap_rprintf(r,kmlpreamble,n,s<-90?-90:s,e>180?180:e,w);
      // outqs has to be the full wms request
      escape_ampersand(image_arg,outqs); // The wms request, kml

      ap_rprintf(r,kmlGrndOvlay,hname(r,0),outqs,n,s,e,w);
      return OK;
    }
  } // OK, so we got a match, the image request is in image_arg

  *format_p=kmltype[0]; // Put the first letter back for the following KMLs

  if (!cache->levels) return kml_return_error(r,"No data found!"); // This is a block

  // Finds the level and parses the bbox at the same time
  if (!(level=wms_get_matching_level(r, cache, &bbox))) { // Paranoid check
    ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
      "Unmatched level kml request %s",r->args);
    return DECLINED; // No level match
  }

  // We got the level , do we need to subdivide?
  // levelt is the next level down
  levelt=GETLEVELS(cache);

  // Needs fuzzy math, +-0.1%
  for (i=cache->levels;i;i--,levelt++)
    if ( ( (level->levelx/levelt->levelx/2) > 0.999 ) &&
         ( (level->levelx/levelt->levelx/2) < 1.001 ) )
      { subdivide=1; break; } // Found it

  n=bbox.y1;s=bbox.y0;e=bbox.x1;w=bbox.x0;

  // Set the type
  ap_set_content_type(r,kmltype);

  // Cut the current request at the last arg, which has to be bbox
  bbox_p=getbbox(r->args);
  bbox_end=getbboxend(bbox_p);
  bbox_p-=5;
  *bbox_p=0;
  
  // Copy the args up to bbox to outqs while escaping the ampersand
  escape_ampersand(r->args,outqs);
  // Copy the args after the bbox to outqs while escaping the ampersand
  escape_ampersand(bbox_end,postamble);

  // Send out the begining of the KML, which includes the area
  ap_rprintf(r,preamble,n,s<-90?-90:s,e>180?180:e,w);

  // Send the extra links if we need them
  if (subdivide) 
    PrintLink(r,&bbox,levelt,outqs,postamble);

  escape_ampersand(image_arg,outqs); // The image request

  // Draw order for KML superoverlay has to increase as resolution increases
  // This is in powers of 2, which is fine
  // This formula puts a 256 degree 512 pixel at 15-8 and the 0.0625 at 15+4

  dorder=10-ilogb(level->levelx/level->psizex);
  ap_rprintf(r,GrndOvlay,dorder,hname(r,0),outqs,n,s,e,w);
  return OK;
}

void getParam(char *args, char *Name, char *Value) {
	char *pos1 = ap_strcasestr(args, Name);
	if (pos1) {
		pos1 += strlen(Name);
		if (*pos1 != '=') { // Make sure we get a real parameter
			char nName[(strlen(Name) + 1)];
			sprintf(nName, "%s=", Name);
			pos1 = ap_strcasestr(args, nName);
			if (pos1) {
				pos1 += strlen(Name);
			} else {
				Value[0]='\0';
				return;
			}
		}
		if (*pos1 == '=') {
			pos1++;
			while (*pos1 && *pos1 != '&') {
				*Value++ = *pos1++;
			}
			*Value++ = '\0';
			return;
		}
	} else {
		Value[0]='\0';
	}
	return;
}

// function to order request arguments in the expected pattern
char *order_args(request_rec *r) {

	char *args = r->args;
	int max_chars;
	//use size of request args to prevent memory errors
	max_chars = strlen(r->args) + 1;

	// valid formats
	char * formats [] = { "image%2Fpng", "image%2Fjpeg", "image%2Ftiff", "image%2Flerc", "application%2Fx-protobuf;type=mapbox-vector"};

	// common args
	char *service = apr_pcalloc(r->pool,max_chars);
	char *request = apr_pcalloc(r->pool,max_chars);
	char *version = apr_pcalloc(r->pool,max_chars);
	char *format = apr_pcalloc(r->pool,max_chars);
	char *time = apr_pcalloc(r->pool,max_chars);

	getParam(args,"service",service);
	getParam(args,"request",request);
	getParam(args,"version",version);
	getParam(args,"format",format);
	getParam(args,"time",time);

	// fix format slash
	ap_str_tolower(format);
	if (ap_strstr(format, "%2f")) {
		char *formatslash = ap_strstr(format, "%2f");
		formatslash += 2;
		*formatslash = 'F';
	}
	if (ap_strcasecmp_match(format, "image/png") == 0) {
		strcpy(format,"image%2Fpng");
	} else if (ap_strcasecmp_match(format, "image/jpeg") == 0) {
		strcpy(format,"image%2Fjpeg");
	} else if (ap_strcasecmp_match(format, "image/tiff") == 0) {
		strcpy(format,"image%2Ftiff");
	} else if (ap_strcasecmp_match(format, "image/lerc") == 0) {
		strcpy(format,"image%2Flerc");
	} // special handling for vectors
	  else if (ap_strcasecmp_match(format, "application%2Fx-protobuf;type=mapbox-vector") == 0) {
		ap_set_content_type(r,"application/x-protobuf;type=mapbox-vector");
	} else if (ap_strcasecmp_match(format, "application/x-protobuf;type=mapbox-vector") == 0) {
		strcpy(format,"application%2Fx-protobuf;type=mapbox-vector");
		ap_set_content_type(r,"application/x-protobuf;type=mapbox-vector");
	} else if (ap_strcasecmp_match(format, "application/vnd.mapbox-vector-tile") == 0) {
		strcpy(format,"application%2Fx-protobuf;type=mapbox-vector");
		ap_set_content_type(r,"application/vnd.mapbox-vector-tile");
	} else if (ap_strcasecmp_match(format, "application%2Fvnd.mapbox-vector-tile") == 0) {
		strcpy(format,"application%2Fx-protobuf;type=mapbox-vector");
		ap_set_content_type(r,"application/vnd.mapbox-vector-tile");
	}

	// make sure there are no extra characters in format
	if (format[0] != NULL) {
		int formats_len = sizeof(formats)/sizeof(formats[0]);
		int f;
		int f_match = 0;
		for(f = 0; f < formats_len; ++f) {
			if(!strcmp(formats[f], format)) {
				f_match++;
			}
		}
		if (f_match == 0) {
			wmts_add_error(r,400,"InvalidParameterValue","FORMAT", "FORMAT is invalid");
		}
	}

	// handle colons
	if (ap_strchr(time, ':') != 0) {
		int i; i= 0;
		char *times[3];
		char *t;
		char *last;
		t = apr_strtok(time,":",&last);
		while (t != NULL && i < 4) {
			times[i++] = t;
			t = apr_strtok(NULL,":",&last);
		}
		time = apr_psprintf(r->pool, "%s%s%s%s%s", times[0],colon,times[1],colon,times[2]);
	}

	// check if TWMS or WMTS
	if ((ap_strcasecmp_match(service, "WMTS") == 0) && (ap_strcasecmp_match(request, "GetTile") == 0))  {
		// WMTS specific args
		char *layer = apr_pcalloc(r->pool,max_chars);
		char *style = apr_pcalloc(r->pool,max_chars);
		char *tilematrixset = apr_pcalloc(r->pool,max_chars);
		char *tilematrix = apr_pcalloc(r->pool,max_chars);
		char *tilerow = apr_pcalloc(r->pool,max_chars);
		char *tilecol = apr_pcalloc(r->pool,max_chars);

		getParam(args,"layer",layer);
		getParam(args,"style",style);
		getParam(args,"tilematrixset",tilematrixset);
		getParam(args,"tilerow",tilerow);
		getParam(args,"tilecol",tilecol);

		// need to ignore occurrence of tilematrix in tilematrixset - replace only one char for optimal performance
		if (tilematrixset[0]!='\0') {
			char *pos1 = ap_strcasestr(args, "tilematrixset");
			*pos1 = 1;
			getParam(args,"tilematrix",tilematrix);
			if (tilematrix[0]=='\0') { // return error if not exist
				wmts_add_error(r,400,"MissingParameterValue","TILEMATRIX", "Missing TILEMATRIX parameter");
			}
			if (tilerow[0]=='\0') { // return error if not exist
				wmts_add_error(r,400,"MissingParameterValue","TILEROW", "Missing TILEROW parameter");
			}
			if (tilecol[0]=='\0') { // return error if not exist
				wmts_add_error(r,400,"MissingParameterValue","TILECOL", "Missing TILECOL parameter");
			}
		}

		// GIBS-273 handle style=default, treat as empty. We don't need this if done in the layer regex pattern.
		if (ap_strcasecmp_match(style, "default") == 0) {
			style[0] = '\0';
		}

		args = apr_psprintf(r->pool,"SERVICE=%s&REQUEST=%s&VERSION=%s&LAYER=%s&STYLE=%s&TILEMATRIXSET=%s&TILEMATRIX=%s&TILEROW=%s&TILECOL=%s&FORMAT=%s&TIME=%s","WMTS","GetTile",version,layer,style,tilematrixset,tilematrix,tilerow,tilecol,format,time);

	} else if (ap_strcasecmp_match(request, "GetMap") == 0) { //assume WMS/TWMS
		//WMS specific args
		char *layers = apr_pcalloc(r->pool,max_chars);
		char *srs = apr_pcalloc(r->pool,max_chars);
		char *styles = apr_pcalloc(r->pool,max_chars);
		char *width = apr_pcalloc(r->pool,max_chars);
		char *height = apr_pcalloc(r->pool,max_chars);
		char *bbox = apr_pcalloc(r->pool,max_chars);
		char *transparent = apr_pcalloc(r->pool,max_chars);
		char *bgcolor = apr_pcalloc(r->pool,max_chars);
		char *exceptions = apr_pcalloc(r->pool,max_chars);
		char *elevation = apr_pcalloc(r->pool,max_chars);

		getParam(args,"layers",layers);
		getParam(args,"srs",srs);
		getParam(args,"styles",styles);
		getParam(args,"width",width);
		getParam(args,"height",height);
		getParam(args,"bbox",bbox);
		getParam(args,"transparent",transparent);
		getParam(args,"bgcolor",bgcolor);
		getParam(args,"exceptions",exceptions);
		getParam(args,"elevation",elevation);

		args = apr_psprintf(r->pool,"version=%s&request=%s&layers=%s&srs=%s&format=%s&styles=%s&width=%s&height=%s&bbox=%s&transparent=%s&bgcolor=%s&exceptions=%s&elevation=%s&time=%s",version,"GetMap",layers,srs,format,styles,width,height,bbox,transparent,bgcolor,exceptions,elevation,time);

	} else if (ap_strcasecmp_match(request, "GetCapabilities") == 0) { // getCapabilities
		args = apr_psprintf(r->pool, "request=GetCapabilities");
	} else if (ap_strcasecmp_match(request, "GetTileService") == 0) { // getTileService
		args = apr_psprintf(r->pool, "request=GetTileService");
	} else if (ap_strcasecmp_match(request, "GetLegendGraphic") == 0) { // GetLegendGraphic is not supported
		wmts_add_error(r,501,"OperationNotSupported","REQUEST", "The request type is not supported");
	} else if ( ap_strcasestr(r->args,"layers") != 0) { // is KML
//    	ap_log_error(APLOG_MARK,APLOG_NOTICE,0,r->server,"Requesting KML");
	} else if (service[0]=='\0') { // missing WMTS service
		wmts_add_error(r,400,"MissingParameterValue","SERVICE", "Missing SERVICE parameter");
	} else if (ap_strcasecmp_match(service, "WMTS") != 0) { // unrecognized service
		wmts_add_error(r,400,"InvalidParameterValue","SERVICE", "Unrecognized service");
	} else { // invalid REQUEST value
		wmts_add_error(r,400,"InvalidParameterValue","REQUEST", "Unrecognized request");
	}

	return args;
}

static int specify_error(request_rec *r)
{
	wms_cfg  *cfg;
	WMSCache *cache;

	// Get the configuration
	cfg=(wms_cfg *)
	ap_get_module_config(r->per_dir_config,&onearth_module);

	// url params
	const char *args_backup = apr_pstrdup(r->pool, r->args);
	char *args = r->args;
	int max_chars;
	max_chars = strlen(r->args) + 1;

	// make sure it's WMTS
	char *service = apr_pcalloc(r->pool,max_chars);
	getParam(args,"service",service);
	if (ap_strcasecmp_match(service, "WMTS") != 0) {
		return;
	}

	// don't worry about performance with error cases
	char *layer = apr_pcalloc(r->pool,max_chars);
	char *layer_reg = apr_pcalloc(r->pool,max_chars);
	char *layer_mes = apr_pcalloc(r->pool,max_chars);
	char *version = apr_pcalloc(r->pool,max_chars);
	char *version_reg = apr_pcalloc(r->pool,max_chars);
	char *version_mes = apr_pcalloc(r->pool,max_chars);
	char *style = apr_pcalloc(r->pool,max_chars);
	char *style_reg = apr_pcalloc(r->pool,max_chars);
	char *style_mes = apr_pcalloc(r->pool,max_chars);
	char *tilematrixset = apr_pcalloc(r->pool,max_chars);
	char *tilematrixset_reg = apr_pcalloc(r->pool,max_chars);
	char *tilematrixset_mes = apr_pcalloc(r->pool,max_chars);
	char *tilematrix = apr_pcalloc(r->pool,max_chars);
	char *tilerow = apr_pcalloc(r->pool,max_chars);
	char *tilecol = apr_pcalloc(r->pool,max_chars);
	char *format = apr_pcalloc(r->pool,max_chars);
	char *format_reg = apr_pcalloc(r->pool,max_chars);
	char *format_mes = apr_pcalloc(r->pool,max_chars);

	getParam(args,"layer",layer);
	getParam(args,"version",version);
	getParam(args,"style",style);
	getParam(args,"format",format);
	getParam(args,"tilerow",tilerow);
	getParam(args,"tilecol",tilecol);
	getParam(args,"tilematrixset",tilematrixset);
	if (tilematrixset[0]!='\0') {
		// ignore first occurrence of tilematrix in tilematrixset
		char *pos1 = ap_strcasestr(args, "tilematrixset");
		*pos1 = 1;
		getParam(args,"tilematrix",tilematrix);
	}

	int count;
	count=cfg->caches->count;

	int version_match = 0;
	int layer_match = 0;
	int layer_version_match = 0;
	int style_match = 0;
	int format_match = 0;
	int tilematrixset_match = 0;

	while (count--) {
		int i;
		cache=GETCACHE(cfg->caches,count);
		i=cache->num_patterns;

		getParam(cache->pattern,"layer",layer_reg);
		getParam(cache->pattern,"version",version_reg);
		getParam(cache->pattern,"style",style_reg);
		getParam(cache->pattern,"format",format_reg);
		getParam(cache->pattern,"tilematrixset",tilematrixset_reg);

		if (ap_strcmp_match(layer, layer_reg) == 0) {
			layer_match++;

			if (ap_strcmp_match(version, version_reg) == 0) {
				layer_version_match++;
			}
			if (ap_strcmp_match(style, style_reg) == 0) {
				style_match++;
			}
			if (ap_strcmp_match(format, format_reg) == 0) {
				format_match++;
			}
			if (ap_strcmp_match(tilematrixset, tilematrixset_reg) == 0) {
				tilematrixset_match++;
			}
		}

		if (ap_strcmp_match(version, version_reg) == 0) {
			version_match++;
		}

	}

	// VERSION
	if (version[0]=='\0') {
		wmts_add_error(r,400,"MissingParameterValue","VERSION", "Missing VERSION parameter");
	}
	else if (version_match==0) {
		version_mes = apr_psprintf(r->pool, "VERSION is invalid");
		wmts_add_error(r,400,"InvalidParameterValue","VERSION", version_mes);
	}
	// LAYER
	if (layer[0]=='\0') {
		wmts_add_error(r,400,"MissingParameterValue","LAYER", "Missing LAYER parameter");
	}
	else if (layer_match==0) {
		layer_mes = apr_psprintf(r->pool, "LAYER does not exist");
		// If OnEarth can't handle this layer and mod_wmts_wrapper is active on this endpoint, let the request pass through.
		module *wmts_wrapper_module = (ap_find_linked_module("mod_wmts_wrapper.cpp"));
		if (wmts_wrapper_module) {
			wmts_wrapper_conf *wmts_wrapper_config = ap_get_module_config(r->per_dir_config, wmts_wrapper_module);
			if (wmts_wrapper_config->role) {
				r->args = args_backup;
				return 0;				
			}
		}
		wmts_add_error(r,400,"InvalidParameterValue","LAYER", layer_mes);
	}
	else if (version[0]!='\0' && layer_version_match==0 && layer_match>0 && version_match>0) {
		version_mes = apr_psprintf(r->pool, "LAYER does not exist for VERSION");
		wmts_add_error(r,400,"InvalidParameterValue","VERSION", version_mes);
	}
	// STYLE
	if (style_match==0 && style[0]!='\0' && layer_match>0) {
		style_mes = apr_psprintf(r->pool, "STYLE is invalid for LAYER");
		wmts_add_error(r,400,"InvalidParameterValue","STYLE", style_mes);
	}
	// FORMAT
	if (format[0]=='\0') {
		wmts_add_error(r,400,"MissingParameterValue","FORMAT", "Missing FORMAT parameter");
	}
	else if (format_match==0 && layer_match>0) {
		format_mes = apr_psprintf(r->pool, "FORMAT is invalid for LAYER");
		wmts_add_error(r,400,"InvalidParameterValue","FORMAT", format_mes);
	}
	// TILEMATRIXSET
	if (tilematrixset[0]=='\0') {
		wmts_add_error(r,400,"MissingParameterValue","TILEMATRIXSET", "Missing TILEMATRIXSET parameter");
	}
	else if (tilematrixset_match==0 && layer_match>0) {
		tilematrixset_mes = apr_psprintf(r->pool, "TILEMATRIXSET is invalid for LAYER");
		wmts_add_error(r,400,"InvalidParameterValue","TILEMATRIXSET", tilematrixset_mes);
	}
	// TILEMATRIX
   while (*tilematrix)
   {
	  if (!isdigit(*tilematrix)) {
		  wmts_add_error(r,400,"InvalidParameterValue","TILEMATRIX", "TILEMATRIX is not a valid integer");
		  break;
	  } else
		  ++tilematrix;
   }
	// TILEROW
   while (*tilerow)
   {
	  if (!isdigit(*tilerow)) {
		  wmts_add_error(r,400,"InvalidParameterValue","TILEROW", "TILEROW is not a valid integer");
		  break;
	  } else
		  ++tilerow;
   }
	// TILECOL
   while (*tilecol)
   {
	  if (!isdigit(*tilecol)) {
		  wmts_add_error(r,400,"InvalidParameterValue","TILECOL", "TILECOL is not a valid integer");
		  break;
	  } else
		  ++tilecol;
   }
   return 1;
}

static int mrf_handler(request_rec *r)

{
  static int hit_count=1000;
  static int miss_count=1000;

  wms_cfg *cfg;
  int count;
  WMSlevel *level;
  WMSCache *cache;
  wms_wmsbbox bbox;
  apr_off_t offset;
  index_s *this_record;
  void *this_data=0;
  int default_idx;
  int z = -1;

  // Get the configuration
  cfg=(wms_cfg *) 
    ap_get_module_config(r->per_dir_config,&onearth_module);

//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got config");

  if (!(cfg->caches)) return DECLINED; // Not configured?
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got caches %d",cfg->caches->count);
  // Let's see if we have a request
  if (!(count=cfg->caches->count)) return DECLINED; // Cache count 0

  if (!cfg->meta) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "No prepared regexps");
    return DECLINED;
  }

  if (ap_strcasestr(r->args,"zindex=")) {
	  char *zchar = apr_pcalloc(r->pool,strlen(r->args) + 1);
	  getParam(r->args,"zindex",zchar);
	  z = apr_atoi64(zchar);
	  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"ZINDEX override: %d, %s", z, r->args);
  }

  // DEBUG
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "In WMS handler");

  // DEBUG
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Request args: %s",r->args);
  r->args=order_args(r);
  // DEBUG
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Ordered args: %s",r->args);

  // short-circuit if there is already a problem
  if (errors > 0) {
	  return wmts_return_all_errors(r);
  }

  // Count is the number of caches
  while (count--) {
    int i;
    cache=GETCACHE(cfg->caches,count);
    i=cache->num_patterns;
    while (i--) if (!ap_regexec(cfg->meta[count].regex[i],r->args,0,NULL,0)) break;
    if (-1!=i) break; // Break out of this while also, we don't need the argument any more
  }

  // No match?
  if (-1==count) {

	// Redirected from Mapserver
	if (r->prev != 0) {
		if (ap_strstr(r->prev->args, "&MAP=") != 0) {
			int max_size = strlen(r->prev->uri)+strlen(r->prev->args);
			char *new_uri = (char*)apr_pcalloc(r->pool, max_size);
		    char *prev_clayer = 0;
		    char *prev_layers = 0;
		    char *prev_time = 0;
		    char *prev_format = 0;
			prev_clayer = (char *) apr_table_get(r->prev->notes, "oems_clayer");
			prev_layers = (char *) apr_table_get(r->prev->notes, "oems_layers");
			prev_time = (char *) apr_table_get(r->prev->notes, "oems_time");
			prev_format = (char *) apr_table_get(r->prev->notes, "oems_format");
			new_uri = apr_psprintf(r->pool,"%s?%s", r->prev->uri, r->prev->args);
			if (prev_time != 0) {
				apr_table_setn(r->notes, "oems_time", prev_time);
			}
			if (prev_layers != 0) {
				apr_table_setn(r->notes, "oems_layers", prev_layers);
			}
			if (prev_clayer != 0) {
				apr_table_setn(r->notes, "oems_clayer", prev_clayer);
			}
			if (prev_format != 0 && ap_strstr(prev_format, "bounce") == 0) {
				// try changing the format string and bounce back
				if (ap_strcasestr(prev_format, "png") != 0) {
					apr_table_setn(r->notes, "oems_format", "image/jpeg&bounce=");
					ap_internal_redirect(new_uri, r);
				} else {
					apr_table_setn(r->notes, "oems_format", "image/png&bounce=");
					ap_internal_redirect(new_uri, r);
				}
			} else { // Fail by setting to NULL
				apr_table_setn(r->notes, "oems_format", 0);
				ap_internal_redirect(new_uri, r);
			}
		}
	}

    // if (r->connection->local_addr->port==80) {
    	if (ap_strcasecmp_match(r->args, "request=GetCapabilities") == 0) {
        	ap_log_error(APLOG_MARK,APLOG_NOTICE,0,r->server,"Requesting getCapabilities");
    	} else {
			int err_status = specify_error(r);
			if (!err_status) return DECLINED;
    		if (errors > 0) {
    			ap_log_error(APLOG_MARK,LOG_LEVEL,0,r->server,
        			"Unhandled %s%s?%s",r->hostname,r->uri,r->args);
            	return wmts_return_all_errors(r);
    		}
    	}
 //    }
	// else
	// ap_log_error(APLOG_MARK,LOG_LEVEL,0,r->server,
 //      "Unhandled %s:%d%s?%s",r->hostname,r->connection->local_addr->port,r->uri,r->args);
 //    return DECLINED; // No cache pattern match, pass it to the real wms server
  }

  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Request: <%s>",r->the_request);

  // DEBUG
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got pattern");

  if (!cache->levels) {
    ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
      "Sending error message, no levels %s",r->args);
    return wms_return_error(r,"No data found!"); // This is the block
  }

  if (!ap_strstr(r->args,WMTS_marker))
  { // Tiled WMS. Figure out where the index is, store it in offset

      // We got cache with levels, but do we have the data?
      if (!(level=wms_get_matching_level(r, cache, &bbox))) {
//	    ap_log_error(APLOG_MARK, APLOG_WARNING,0,r->server, "Unmatched level %s",r->args);
	    if (r->prev != 0) {
			if (ap_strstr(r->prev->args, "&MAP=") != 0) { // Redirected from Mapserver
				level = GETLEVELS(cache);
				char *ifname;
				if (level->ifname[0] == '/') { // decide absolute or relative path from cachedir
					  ifname = apr_pstrcat(r->pool,level->ifname,0);
				} else {
					  ifname = apr_pstrcat(r->pool,cfg->cachedir,level->ifname,0);
				}
				r_file_pread(r, ifname, sizeof(index_s),offset, cache->time_period, cache->num_periods, cache->zlevels);
				return DECLINED;
			} else {
				return DECLINED;
			}
	    } else {
	    	return DECLINED; // No level match
	    }
      }

      // DEBUG
      // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Got level %d %s %s",level,level->ifname,level->ifname);

      if ((WMSlevel *)1==level) { // Malformed bbox
	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server, "Sending error, bad bbox");
	return wms_return_error(r,
	  "WMS parameter bbox format incorrect");
      }

      if ((WMSlevel *)2==level) { // Too far from bin level
    	  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
	      "Sending error, not cached %s",r->args);
    	  return wms_return_error(r, "Resolution not cached. Please do not modify configuration!");
      }

      // got a matching level and cache
      	  if (!cache->zlevels) {
		  	offset=get_index_offset(level,&bbox,cache->orientation,r);
	  } else {
		  if (!cache->zidxfname) {
			  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"No z-index filename %s",r->args);
			  offset = -1;
		  } else {
			  char *zidxfname;
//			  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"z-index filename %s",cache->zidxfname);
			  if (cache->zidxfname[0] == '/') { // decide absolute or relative path from cachedir
				  zidxfname = apr_pstrcat(r->pool,cache->zidxfname,0);
			  } else {
				  zidxfname = apr_pstrcat(r->pool,cfg->cachedir,cache->zidxfname,0);
			  }

			  if (z<0) {
				  // Lookup the z index from the ZDB file based on keyword
				  z = get_zlevel(r,tstamp_fname(r,zidxfname),get_keyword(r));
				  if (z<0) {
					  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"z index %d, %s", z, r->args);
				  }
			  }
			  if (z >= cache->zlevels) {
				  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Retrieved z-index %d is greater than the maximum for the layer %d",z,cache->zlevels);
			  }
			  offset=twms_get_index_offset_z(level,&bbox,cache->orientation,z,cache->zlevels,r);
		  }
	  }

      // DEBUG
      // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      //   "index add is %ld",level->index_add);
      //
      // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      //   "index offset returns %ld, size is %ld",offset,sizeof(offset));

      if (-1==offset) {
	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
		    "Bogus index offset %s",r->args);
	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
		    "ix %d, iy %d, count %d,%d",
		    (int)((bbox.x0-level->X0)/level->levelx),
		    (int)((level->Y1-bbox.y1)/level->levely),
		    level->xcount,level->ycount);

	return DECLINED;
      }


      if (-2==offset) {
	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
		    "Bogus alignment %s",r->args);
	return DECLINED;
      }


  } else { // WMTS branch
    if (!(level=wmts_get_matching_level(r, cache))) {
		ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
			"WMTS Unmatched level %s",r->args);
//		return DECLINED; // No level match
//		wmts_add_error(r,400,"InvalidParameterValue","TILEROW", "Unmatched TILEROW");
//		wmts_add_error(r,400,"InvalidParameterValue","TILECOL", "Unmatched TILECOL");
    }

    if (level<(WMSlevel *) 2) {
	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
	  "Can't find TILEMATRIX %s",r->args);
		wmts_add_error(r,400,"InvalidParameterValue","TILEMATRIX", "Invalid TILEMATRIX");
    }

    if (errors > 0) {
    	return wmts_return_all_errors(r);
    }

	  if (!cache->zlevels) {
		  offset=wmts_get_index_offset(r,level);
	  } else {
		  if (!cache->zidxfname) {
			  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"No z-index filename %s",r->args);
			  offset = -1;
		  } else {
			  char *zidxfname;
//			  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"z-index filename %s",cache->zidxfname);
			  if (cache->zidxfname[0] == '/') { // decide absolute or relative path from cachedir
				  zidxfname = apr_pstrcat(r->pool,cache->zidxfname,0);
			  } else {
				  zidxfname = apr_pstrcat(r->pool,cfg->cachedir,cache->zidxfname,0);
			  }

			  // Lookup the z index from the ZDB file based on keyword
			  if (z<0) {
			  	z = get_zlevel(r,tstamp_fname(r,zidxfname),get_keyword(r));
			  	if (z<0) {
				  	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"z index %d, %s", z, r->args);
			  	}
			  }
			  if (z >= cache->zlevels) {
				  ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Retrieved z-index %d is greater than the maximum for the layer %d",z,cache->zlevels);
			  }
			  offset=wmts_get_index_offset_z(r,level,z,cache->zlevels);
		  }
	  }

    if (0>offset || errors>0)
    	return wmts_return_all_errors(r);
  }

//   ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
//              "record read prepared %s %d", cfg->cachedir, offset);

  char *ifname;
  if (level->ifname[0] == '/') { // decide absolute or relative path from cachedir
  	  ifname = apr_pstrcat(r->pool,level->ifname,0);
  } else {
  	  ifname = apr_pstrcat(r->pool,cfg->cachedir,level->ifname,0);
  }
  default_idx = 0;
  this_record = r_file_pread(r, ifname, sizeof(index_s),offset, cache->time_period, cache->num_periods, cache->zlevels);

	if (!this_record) {
		// try to read from 0,0 in static index
		this_record = p_file_pread(r->pool, ifname, sizeof(index_s), 0);
		default_idx = 1;
	}
	if (!this_record) {
		// still no record
		if (errors > 0)
			return wmts_return_all_errors(r);
		char *fname = tstamp_fname(r,ifname);
		ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Can't get index record from %s Based on %s", fname,r->args);
//		perror("Index read error: ");
		return DECLINED;

//		// code to return error when time is out of range (includes blank tile for +1 day slack)
//		// safe to assume invalid date?
//		char *timepart = ap_strcasestr(fname, "_.");
//
//		if (timepart) {
//			timepart = timepart-3;
//			int day = atoi(timepart);
//			day--; // check yesterday (one day slack for current date)
//			if (day==0)
//				day = 365; // forget about leap years
//			char *strday = apr_pcalloc(r->pool,4);
//			strday = apr_psprintf(r->pool, "%d", day);
//			if (day < 100) {
//				timepart[0]=*"0";
//				timepart[1] = strday[0];
//				timepart[2] = strday[1];
//			} else {
//				timepart[0] = strday[0];
//				timepart[1] = strday[1];
//				timepart[2] = strday[2];
//			}
//
//			// read file using previous date
//			this_record=r_file_pread(r,fname,sizeof(index_s),offset);
//			if (!this_record && day!=-1) // also checks for valid TIME format
//				if (ap_strstr(r->args,WMTS_marker)) // don't return error for TWMS/KML
//					wmts_add_error(r,400,"InvalidParameterValue","TIME", "TIME is out of range for layer");
//		} else {
//			wmts_add_error(r,400,"InvalidParameterValue","TIME", "TIME is out of range for layer");
//		}
//		if (errors > 0) {
//			return wmts_return_all_errors(r);
//		} else {
//			return DECLINED;
//		}
	}

//
// This is the only endian dependent part
// Linux defines __LITTLE_ENDIAN
// Could use the internal macros, but this is simpler
//
#if defined(__LITTLE_ENDIAN)
  {
    apr_size_t temp_size_t;
    char *source,*dest;
    int i;

    source=(char *) &this_record->size;
    dest=(char *) &temp_size_t;
    for (i=0;i<8;i++) dest[i]=source[7-i];
    this_record->size=temp_size_t;

    source=(char *) &this_record->offset;
    dest=(char *) &temp_size_t;
    for (i=0;i<8;i++) dest[i]=source[7-i];
    this_record->offset=temp_size_t;
  }
#endif

  // Check for tile not in the cache
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Try to read tile from %ld, size %ld",this_record->offset,this_record->size);
	
  char *dfname;
  if (level->dfname[0] == '/') { // decide absolute or relative path from cachedir
	  dfname = apr_pstrcat(r->pool,level->dfname,0);
  } else {
	  dfname = apr_pstrcat(r->pool,cfg->cachedir,level->dfname,0);
  }
  if (this_record->size && default_idx==0) {
	  this_data=r_file_pread(r, dfname, this_record->size,this_record->offset, cache->time_period, cache->num_periods, cache->zlevels);
  }
  if (!this_data) { // get empty tile
    int lc=level-GETLEVELS(cache);
    if ((cfg->meta[count].empties[lc].index.size)&& (cfg->meta[count].empties[lc].data)) {
        this_record->size=cfg->meta[count].empties[lc].index.size;
        this_data=cfg->meta[count].empties[lc].data;
    } else { // This might be first time, we need to read the empty page
      if (cfg->meta[count].empties[lc].index.size) {
        this_record->size=cfg->meta[count].empties[lc].index.size;
        this_record->offset=cfg->meta[count].empties[lc].index.offset;
        ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "INITIALIZING EMPTY FOR: %s",r->args);
        this_data=cfg->meta[count].empties[lc].data=p_file_pread(cfg->p,
        		dfname, this_record->size, this_record->offset);
      }
      if (!this_data) { // No empty tile provided, let it pass
    	  miss_count--;
    	  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Record not present %s",r->args);
    	  return DECLINED;
      }
    }
  }

  if (!this_data) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
       "Data read error from file %s size %ld offset %ld",level->dfname,this_record->size, this_record->offset);
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Request args: %s",r->args);
    apr_table_set(r->notes, "mod_onearth_failed", "true");
    return DECLINED; // Can't read the data for some reason
  }

  if (ap_strstr(r->args,WMTS_marker) && (errors > 0)) {
  	return wmts_return_all_errors(r);
  }

  // DEBUG
//  ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got data at %x",this_data);

  // Set gzip encoding if output is pbf
  if ((apr_strnatcmp(cfg->meta[count].mime_type, "application/x-protobuf;type=mapbox-vector") == 0) || (apr_strnatcmp(cfg->meta[count].mime_type, "application/vnd.mapbox-vector-tile") == 0)) {
  	apr_table_setn(r->headers_out, "Content-Encoding", "gzip");
  } else {
	  ap_set_content_type(r,cfg->meta[count].mime_type);
  }
  if (apr_strnatcmp(cfg->meta[count].mime_type, "image/lerc") == 0) {
  	apr_table_setn(r->headers_out, "Content-Encoding", "deflate");
  }
  ap_set_content_length(r,this_record->size);
  ap_rwrite(this_data,this_record->size,r);

  // Got a hit, do we log anything?
  if (!hit_count--) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "MISS_MARK %d", 1000-miss_count);
    miss_count=hit_count=1000;
  }

  // DEBUG
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
  //  "All done");

  return OK;
}

int rewrite_rest_uri(request_rec *r) {

	wms_cfg *cfg;
	cfg = (wms_cfg *)ap_get_module_config(r->per_dir_config,&onearth_module);

	if (cfg->dir == NULL)
		return -1;

//	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"Config dir %s",cfg->dir);

	int i;
	char *p;
	char *params[16];
	char *last;
	char *format = apr_pcalloc(r->pool,45);

	i = 0;
	p = apr_strtok(r->uri,"/",&last);
	while (p != NULL && i < 11) {
		params[i++] = p;
		p = apr_strtok(NULL, "/",&last);
	}

	r->uri = ""; // need to rebuild the URI
	int d = -1; // directories before first REST param
	int j = 0;
	for(j = 0; j < i; j++) {
		if(ap_strstr(cfg->dir, params[j]) != NULL) {
			d++;
			r->uri = apr_psprintf(r->pool,"%s/%s",r->uri,params[j]);
			if ((ap_strstr(cfg->dir, params[j+1])) == '\0') {
				break;
			}
		}
	}

	int length = i-d;
	// test using number of slashes
	if (length < 7 || length > 9)
		return -1;

	i = i-1; // step back to split on "."
	p = apr_strtok(params[i],".",&last);
	while (p != NULL) {
		params[i++] = p;
		p = apr_strtok(NULL, ".",&last);
	}

	if (ap_strcasecmp_match(params[length+d],"pbf") == 0) {
		sprintf(format,"application%%2Fx-protobuf;type=mapbox-vector");
	} else if (ap_strcasecmp_match(params[length+d],"mvt") == 0) {
		sprintf(format,"application%%2Fvnd.mapbox-vector-tile");
	} else if (ap_strcasecmp_match(params[length+d],"jpg") == 0) {
		sprintf(format,"image%%2Fjpeg");
	} else {
		sprintf(format,"image%%2F%s", params[length+d]);
	}

	if (length == 7)
		r->args = apr_psprintf(r->pool,"wmts.cgi?SERVICE=%s&REQUEST=%s&VERSION=%s&LAYER=%s&STYLE=%s&TILEMATRIXSET=%s&TILEMATRIX=%s&TILEROW=%s&TILECOL=%s&FORMAT=%s","WMTS","GetTile","1.0.0",params[1+d],params[2+d],params[3+d],params[4+d],params[5+d],params[6+d],format);
	if (length == 8)
		r->args = apr_psprintf(r->pool,"wmts.cgi?SERVICE=%s&REQUEST=%s&VERSION=%s&LAYER=%s&STYLE=%s&TILEMATRIXSET=%s&TILEMATRIX=%s&TILEROW=%s&TILECOL=%s&FORMAT=%s&TIME=%s","WMTS","GetTile","1.0.0",params[1+d],params[2+d],params[4+d],params[5+d],params[6+d],params[7+d],format,params[3+d]);
	if (length == 9)
		r->args = apr_psprintf(r->pool,"wmts.cgi?SERVICE=%s&REQUEST=%s&VERSION=%s&LAYER=%s&STYLE=%s&TILEMATRIXSET=%s&TILEMATRIX=%s&TILEROW=%s&TILECOL=%s&FORMAT=%s&TIME=%s&ZINDEX=%s","WMTS","GetTile","1.0.0",params[1+d],params[2+d],params[4+d],params[5+d],params[6+d],params[7+d],format,params[3+d],params[8+d]);
	// Try to get image, otherwise redirect to cgi to handle error
	if (mrf_handler(r) < 0) {
//		ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,"REST redirect -> %s/wmts.cgi?%s",r->uri,r->args);
		apr_table_set(r->notes, "mod_onearth_handled", "true");
		ap_internal_redirect(apr_psprintf(r->pool,"%s/wmts.cgi?%s",r->uri,r->args),r);
	}
	return 0;
}

static int handler(request_rec *r) {
  // Easy cases first, Has to be a get with arguments
  if (r->method_number != M_GET) return DECLINED;
  if (r->prev && apr_table_get(r->prev->notes, "mod_onearth_handled")) return DECLINED;
  if (!(r->args)) {
	  if(strlen(r->uri) > 4 && (!strcmp(r->uri + strlen(r->uri) - 4, ".png") || !strcmp(r->uri + strlen(r->uri) - 4, ".jpg") || !strcmp(r->uri + strlen(r->uri) - 5, ".jpeg") || !strcmp(r->uri + strlen(r->uri) - 4, ".tif") || !strcmp(r->uri + strlen(r->uri) - 5, ".tiff") || !strcmp(r->uri + strlen(r->uri) - 5, ".lerc") || !strcmp(r->uri + strlen(r->uri) - 4, ".pbf") || !strcmp(r->uri + strlen(r->uri) - 4, ".mvt") )) {
		  if (rewrite_rest_uri(r) < 0)
			  return DECLINED;
		  else
			  return OK;
	  }
	  else
		  return DECLINED;
  }

  if (ap_strstr(r->args,kmltype)) // This is the KML hook
    return kml_handler(r);

  return mrf_handler(r);
}

static void register_hooks(apr_pool_t *p)

{
  ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST);
}

// Configuration options that go in the httpd.conf
static const command_rec cmds[] =
{
  AP_INIT_TAKE1(
    "WMSCache",
    cache_dir_set,
    NULL, /* argument to include in call */
    ACCESS_CONF, /* where available */
    "Cache directive - points to the configuration file" /* help string */
  ),
  {NULL}
};

static void *create_dir_config(apr_pool_t *p, char *dummy)
{
  wms_cfg *cfg;
  // Allocate the config record
  cfg=(wms_cfg *) apr_pcalloc(p,sizeof(wms_cfg));
  // Keep track of the pool
  cfg->p=p;
  // Not initialized yet
  cfg->caches=0;
  return (void *)cfg;
}

static void*merge_dir_config(apr_pool_t *p, void *basev, void *overlay)
{
  wms_cfg *c=
    (wms_cfg *) apr_pcalloc(p,sizeof(wms_cfg));
  // We don't inherit the configuration from parent directories,
  // each directory has to define its own cache

  // Only pick up configurations for the current directory
  *c=*((wms_cfg *) overlay);

  return (void *)c;
}

module AP_MODULE_DECLARE_DATA onearth_module =
{
  STANDARD20_MODULE_STUFF,
  create_dir_config, // Create per directory
  merge_dir_config, // Per Directory merge
//  create_server_config, /* per-server config creator */
  NULL, // per-server config creator 
  NULL, // wp_merge_server_config, Merge per dir?
  cmds, /* command table */
  register_hooks, /* set up the request processing hooks */
};
