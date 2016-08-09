/*
* Copyright (c) 2016, California Institute of Technology.
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
 * mod_oems.cpp: Mapserver wrapper module for OnEarth
 * Version 1.0
 */

#include "mod_oems.h"

const char *mapfiledir;
const char *imagetempdir;

static char epsg4326_aux[] = "<PAMDataset>\n<SRS>GEOGCS[\"GCS_WGS_1984\",DATUM[\"D_WGS_1984\",SPHEROID[\"WGS_1984\",6378137,298.257223563]],PRIMEM[\"Greenwich\",0],UNIT[\"Degree\",0.017453292519943295]]</SRS>\n</PAMDataset> ";
static char epsg3414_aux[] = "<PAMDataset>\n<SRS>PROJCS[\"WGS 84 / NSIDC Sea Ice Polar Stereographic North\",GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.01745329251994328,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],PROJECTION[\"Polar_Stereographic\"],PARAMETER[\"latitude_of_origin\",70],PARAMETER[\"central_meridian\",-45],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],AUTHORITY[\"EPSG\",\"3413\"],AXIS[\"X\",UNKNOWN],AXIS[\"Y\",UNKNOWN]]</SRS>\n</PAMDataset>";
static char epsg3031_aux[] = "<PAMDataset>\n<SRS>PROJCS[\"WGS 84 / Antarctic Polar Stereographic\",GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.01745329251994328,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],PROJECTION[\"Polar_Stereographic\"],PARAMETER[\"latitude_of_origin\",-71],PARAMETER[\"central_meridian\",0],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],AUTHORITY[\"EPSG\",\"3031\"],AXIS[\"Easting\",UNKNOWN],AXIS[\"Northing\",UNKNOWN]]</SRS>\n</PAMDataset>";
static char epsg3857_aux[] = "<PAMDataset>\n<SRS>PROJCS[\"WGS 84 / Pseudo-Mercator\",GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4326\"]],PROJECTION[\"Mercator_1SP\"],PARAMETER[\"central_meridian\",0],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AXIS[\"X\",EAST],AXIS[\"Y\",NORTH],EXTENSION[\"PROJ4\",\"+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs\"],AUTHORITY[\"EPSG\",\"3857\"]]</SRS>\n</PAMDataset> ";

static const char *mapfile_dir_set(cmd_parms *cmd, void *cfg, const char *arg) {
	mapfiledir = arg;
	return 0;
}

static const char *imagetemp_dir_set(cmd_parms *cmd, void *cfg, const char *arg) {
	imagetempdir = arg;
	return 0;
}

// Retrieve parameter value from URL
void get_param(char *args, char *Name, char *Value) {
	char *pos1 = ap_strcasestr(args, Name);
	if (pos1) {
		pos1 += strlen(Name);
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

// Return mapfile with full path
char *get_mapfile(request_rec *r, char *mapfile) {
	get_param(r->args, "crs", mapfile); // Use CRS for WMS 1.3
	if(strlen(mapfile) == 0) {
		get_param(r->args, "srs", mapfile); // Use SRS for WMS 1.1
		if(strlen(mapfile) == 0) {
			get_param(r->args, "srsname", mapfile); // Use SRSNAME for WFS
		}
	}
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "SRS: %s", mapfile);
	if (ap_strstr(mapfile, "4326") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg4326.map");
	} else if (ap_strstr(mapfile, "3031") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3031.map");
	} else if (ap_strstr(mapfile, "3413") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3413.map");
	} else {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3857.map");
	}
	return mapfile;
}

// Check for valid arguments and transform request for Mapserver
char *validate_args(request_rec *r, char *mapfile) {

	char proj[4];
	char *args = r->args;
	int max_chars;
	max_chars = strlen(r->args) + 1;

	// Time args
	apr_time_exp_t tm = {0};
	apr_size_t tmlen;
	char *time = (char*)apr_pcalloc(r->pool,max_chars);
	char *doytime = (char*)apr_pcalloc(r->pool,max_chars); // Ordinal date with time
	char *productyear = (char*)apr_pcalloc(r->pool,max_chars);

	// General args
	char *service = (char*)apr_pcalloc(r->pool,max_chars);
	char *version = (char*)apr_pcalloc(r->pool,max_chars);
	char *request = (char*)apr_pcalloc(r->pool,max_chars);
	char *format = (char*)apr_pcalloc(r->pool,max_chars);
	char *bbox = (char*)apr_pcalloc(r->pool,max_chars);

	get_param(args,"time",time);
	get_param(args,"service",service);
	get_param(args,"version",version);
	get_param(args,"request",request);
	get_param(args,"format",format);
	get_param(args,"bbox",bbox);

	// handle TIME
	if (ap_strchr(time, '-') != 0) {
		int i; i= 0;
		char *times[3];
		char *t;
		char *last;
		t = apr_strtok(time,"-",&last);
		while (t != NULL && i < 4) {
			times[i++] = t;
			t = apr_strtok(NULL,"-",&last);
		}
		// TODO: Handle HH:MM:SS
		productyear = apr_psprintf(r->pool, "%s", times[0]);
		time = apr_psprintf(r->pool, "%s%s%s", times[0], times[1], times[2]);
		ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "TIME: %s", time);

		tm.tm_year = apr_atoi64(times[0]) - 1900;
		tm.tm_mon = apr_atoi64(times[1]) - 1;
		tm.tm_mday = apr_atoi64(times[2]);

		apr_time_t epoch = 0;
		apr_time_exp_get(&epoch, &tm);
		apr_time_exp_gmt(&tm, epoch);

		apr_strftime(doytime, &tmlen, 14, "%Y%j", &tm);
		ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "DOYTIME: %s", doytime);
	}

	// check if WMS or WFS
	if (ap_strcasecmp_match(service, "WMS") == 0)  {
		char *transparent = (char*)apr_pcalloc(r->pool,max_chars);
		char *layers = (char*)apr_pcalloc(r->pool,max_chars);
		char *srs = (char*)apr_pcalloc(r->pool,max_chars);
		char *styles = (char*)apr_pcalloc(r->pool,max_chars);
		char *width = (char*)apr_pcalloc(r->pool,max_chars);
		char *height = (char*)apr_pcalloc(r->pool,max_chars);

		get_param(args,"transparent",transparent);
		get_param(args,"layers",layers);
		get_param(args,"styles",styles);
		get_param(args,"width",width);
		get_param(args,"height",height);

		if (ap_strstr(version, "1.1") != 0) {
			strcpy(proj,"SRS");
			get_param(args,"srs",srs);
		} else {
			strcpy(proj,"CRS");
			get_param(args,"crs",srs);
		}
		args = apr_psprintf(r->pool,"SERVICE=%s&REQUEST=%s&VERSION=%s&FORMAT=%s&TRANSPARENT=%s&LAYERS=%s&MAP=%s&%s=%s&STYLES=&WIDTH=%s&HEIGHT=%s&BBOX=%s&TIME=%s&PRODUCTYEAR=%s","WMS",request,version,format,transparent,layers,mapfile,proj,srs,width,height,bbox,doytime,productyear);

	} else if (ap_strcasecmp_match(service, "WFS") == 0) {
		char *typenames = (char*)apr_pcalloc(r->pool,max_chars);
		char *outputformat = (char*)apr_pcalloc(r->pool,max_chars);
		char *srsname = (char*)apr_pcalloc(r->pool,max_chars);

		get_param(args,"typenames",typenames);
		if(strlen(typenames) == 0) {
			get_param(args,"typename",typenames);
		}
		get_param(args,"outputformat",outputformat);
		get_param(args,"srsname",srsname);

		args = apr_psprintf(r->pool,"SERVICE=%s&REQUEST=%s&VERSION=%s&OUTPUTFORMAT=%s&TYPENAMES=%s&BBOX=%s&SRSNAME=%s&MAP=%s&TIME=%s&PRODUCTYEAR=%s","WFS",request,version,outputformat,typenames,bbox,srsname,mapfile,doytime,productyear);
	} else {
		args = r->args;
	}
	return args;
}

// OnEarth Mapserver handler
static int oems_handler(request_rec *r) {
	// Log directory and args for debugging
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Mapfile Dir: %s", mapfiledir);
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Image Temp Dir: %s", imagetempdir);
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Request args: %s", r->args);

	char *mapfile = (char*)apr_pcalloc(r->pool,strlen(mapfiledir)+16);
	mapfile = get_mapfile(r, mapfile);
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Mapfile: %s", mapfile);

	// Call Mapserver with mapfile
	r->args = validate_args(r, mapfile);
	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Mapserver args: %s", r->args);

	return DECLINED; // Pass request to Mapserver
}

// Main handler for module
static int handler(request_rec *r) {
	if (r->method_number != M_GET) return DECLINED;

	if (!(r->args)) { // Dont handle if no arguments
		return DECLINED;
	}
	return oems_handler(r);
}

// Configuration options that go in the httpd.conf
static const command_rec cmds[] =
{
	AP_INIT_TAKE1(
		"MapfileDir",
		(cmd_func) mapfile_dir_set,
		0, /* argument to include in call */
		ACCESS_CONF, /* where available */
		"The directory containing mapfiles" /* help string */
	),
	AP_INIT_TAKE1(
		"ImageTempDir",
		(cmd_func) imagetemp_dir_set,
		0, /* argument to include in call */
		ACCESS_CONF, /* where available */
		"Temporary directory for processing images" /* help string */
	),
	{NULL}
};

static void register_hooks(apr_pool_t *p) {
	ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST);
}

module AP_MODULE_DECLARE_DATA oems_module = {
    STANDARD20_MODULE_STUFF,
    0, 0, 0, 0, cmds, register_hooks
};
