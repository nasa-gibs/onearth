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
 * Version 1.3.1
 */

#include "mod_oems.h"

ap_regex_t* daily_time;
ap_regex_t* subdaily_time;
static const char *daily_time_pattern = "\\d{4}-\\d{2}-\\d{2}";
static const char *subdaily_time_pattern = "\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z";

static int change_xml_node_values(const xmlChar *search_xpath, 
								  xmlXPathContextPtr *xpathCtx, 
								  const char *search_txt,
								  const char *replacement_txt)
{
	int rv = 0;
	xmlXPathObjectPtr xpathObj = xmlXPathEvalExpression(search_xpath, *xpathCtx);
    if (xpathObj->nodesetval) 
    {
    	rv = 1;
        for (int i=0; i<xpathObj->nodesetval->nodeNr; i++)
        {
        	xmlNode *node = xpathObj->nodesetval->nodeTab[i];
        	// Only replace node text if the search string is present (if one was specified).
        	if (search_txt && !ap_strstr((const char*)xmlNodeGetContent(node), search_txt)) return 0;
            xmlNodeSetContent(xpathObj->nodesetval->nodeTab[i], (const xmlChar *)replacement_txt);    
        }	        	
    }
    xmlXPathFreeObject(xpathObj);
    return rv;
}

// This SAX function checks to see if the XML repsonse from Mapserver is one of the types that we're filtering.
static void xml_first_element_handler(void * user_data, const xmlChar * name, const xmlChar ** attrs)
{
	xml_filter_ctx *ctx = (xml_filter_ctx *)user_data;
	if (!ctx->root_elem_found) // We only care about the first element in the XML response
	{
		ctx->root_elem_found = 1;
	    if (apr_strnatcasecmp((const char *)name, "WMS_Capabilities") == 0
	    	|| apr_strnatcasecmp((const char *)name, "WMT_MS_Capabilities") == 0)
	    {
	    	ctx->is_gc = 1;
	    }
	    else if (apr_strnatcasecmp((const char *)name, "ServiceExceptionReport") == 0)
	    {
	    	ctx->is_error = 1;
	    }
	    if (apr_strnatcasecmp((const char *)attrs[0], "version") == 0)
	    {
	    	apr_cpystrn(ctx->wms_version, (char *)attrs[1], 7);
	    }
	    ctx->should_parse = ctx->is_gc || ctx->is_error;
	}
}

/*
 This filter works on various types of Mapserver text output. It currently strips filenames
from error messages and makes a couple of corrections to GetCapabilities responses.
*/
static apr_status_t mapserver_output_filter(ap_filter_t *f, apr_bucket_brigade *bb)
{
	request_rec *r = f->r;
	conn_rec *c = r->connection;
	apr_bucket_brigade *bb_out = apr_brigade_create(r->pool, c->bucket_alloc);
	xml_filter_ctx *ctx = (xml_filter_ctx *)f->ctx;
	
	ctx->should_parse = ap_strstr(r->content_type, "text/xml")
						|| ap_strstr(r->content_type, "application/vnd.ogc.se_xml")
						|| ap_strstr(r->content_type, "application/vnd.ogc.wms_xml");
	
	if (!ctx->should_parse) ap_remove_output_filter(f); // Bail early if this isn't an XML response.

	/* 
	Set up the libxml2 SAX parser and the tree parser. The SAX parser is used to see
	if this is a response we want to modify, in which case the tree parser is used for those 
	operations. 
	*/
	xmlParserCtxtPtr xmlctx = 0;
	xmlParserCtxtPtr xmlsaxctx = 0;
	xmlDocPtr doc = 0;
	xmlSAXHandler SAXHandler;
	memset(&SAXHandler, 0, sizeof(xmlSAXHandler));
	SAXHandler.startElement = xml_first_element_handler;
	ctx->wms_version = (char *)apr_pcalloc(r->pool, 7);

    for (apr_bucket *b = APR_BRIGADE_FIRST(bb); 
		b != APR_BRIGADE_SENTINEL(bb); 
		b = APR_BUCKET_NEXT(b))
	{
		// If this isn't a response that we need to modify, we pass back the cached buckets and bail on the rest of the brigade.
		if (!ctx->should_parse)
		{
		    xmlFreeParserCtxt(xmlctx);
		    xmlFreeParserCtxt(xmlsaxctx);
			ap_pass_brigade(f->next, bb_out);
			apr_brigade_cleanup(bb_out);
			ap_pass_brigade(f->next, bb);
			return APR_SUCCESS;
		}

		if (APR_BUCKET_IS_EOS(b) || APR_BUCKET_IS_FLUSH(b)) 
		{
			// Stream is over, now we check the XML for stuff we need to change, dump it into a buffer, and send it off.
			xmlParseChunk(xmlctx, 0, 0, 1);
			if (!xmlctx->valid)
			{
				ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, "Can't parse Mapserver output: invalid XML");	
			}
			doc = xmlctx->myDoc;
	        const char* out_buf;
	        int out_size;
	        xmlXPathContextPtr xpathCtx = xmlXPathNewContext(doc);
	        const xmlChar *search_xpath;

			if (ctx->is_gc) // Have to swap nearestValue=0 to nearestValue=1 in the GC responses
			{
	    		if (apr_strnatcasecmp(ctx->wms_version, "1.3.0") == 0)
	    		{
			        xmlXPathRegisterNs(xpathCtx, BAD_CAST "default", BAD_CAST "http://www.opengis.net/wms");
		        	search_xpath = (const xmlChar *)"/default:WMS_Capabilities/default:Capability/default:Layer/default:Layer/default:Dimension/@nearestValue";			
	    		} 
	    		else if (apr_strnatcasecmp(ctx->wms_version, "1.1.1") == 0)
	    		{
		        	search_xpath = (const xmlChar *)"/WMT_MS_Capabilities/Capability/Layer/Layer/Extent/@nearestValue";
	    		}
		        change_xml_node_values(search_xpath, &xpathCtx, NULL, "1");
			}

			if (ctx->is_error) // We also want to strip out any filenames the come through Mapserver errors.
			{
	    		char *oe_error = 0;
	    		if (apr_strnatcasecmp(ctx->wms_version, "1.3.0") == 0)
	    		{
			        xmlXPathRegisterNs(xpathCtx, BAD_CAST "default", BAD_CAST "http://www.opengis.net/ogc");
		        	search_xpath = (const xmlChar *)"/default:ServiceExceptionReport/default:ServiceException/text()";	    			
	    		} 
	    		else if (apr_strnatcasecmp(ctx->wms_version, "1.1.1") == 0)
	    		{
		        	search_xpath = (const xmlChar *)"/ServiceExceptionReport/ServiceException/text()";
	    		}
	    		else
	    		{
	    			ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, "Can't fix XML error message -- not v1.3.0 or 1.1.1");
	    		}
		        change_xml_node_values(search_xpath, &xpathCtx, ".mrf", "msWMSLoadGetMapParams(): WMS server error. Unable to access -- corrupt, empty or missing file.");
		    	if (r->prev != 0) {
		    		oe_error = (char *) apr_table_get(r->prev->notes, "oe_error");
		    	}
		    	if (oe_error != 0) {
			        change_xml_node_values(search_xpath, &xpathCtx, "Invalid layer", "msWMSLoadGetMapParams(): WMS server error. Unable to access -- invalid TIME for LAYER.");
		    	} else {
			        change_xml_node_values(search_xpath, &xpathCtx, "Invalid layer", "msWMSLoadGetMapParams(): WMS server error. Unable to access -- invalid LAYER(s).");
		    	}
  			}

  			// Cleanup for all the XML parser stuff
	        xmlDocDumpMemory(doc, (xmlChar **)&out_buf, &out_size);
	        xmlFreeParserCtxt(xmlctx);
	        xmlFreeParserCtxt(xmlsaxctx);
	        xmlXPathFreeContext(xpathCtx);
	        xmlFreeDoc(doc);

	        // Dump new XML into a new brigade
			apr_brigade_cleanup(bb_out);
	    	ap_fwrite(f->next, bb_out, out_buf, out_size);

	    	// Add EOS bucket to tail once we're done w/ the XML
			APR_BUCKET_REMOVE(b);
			APR_BRIGADE_INSERT_TAIL(bb_out, b);
			ap_pass_brigade(f->next, bb_out);
			apr_brigade_cleanup(bb_out);
			return APR_SUCCESS;
		}

		// Read bucket content into a buffer.
		const char *buf = 0;
		apr_size_t bytes;
		if (APR_SUCCESS != apr_bucket_read(b, &buf, &bytes, APR_BLOCK_READ)) {
			ap_log_rerror(APLOG_MARK, APLOG_ERR, 0, r, "Error reading bucket");
		}

		// We have to cache buckets until we know what kind of document we're dealing with.
		if (!ctx->root_elem_found)
		{
			apr_bucket * b_out = apr_bucket_immortal_create(buf, bytes, c->bucket_alloc);
			APR_BRIGADE_INSERT_TAIL(bb_out, b_out);
			APR_BUCKET_REMOVE(b);			
		}

		if (!xmlctx && !xmlsaxctx) // Set up parser contexts
		{
			xmlctx = xmlCreatePushParserCtxt(NULL, NULL, buf, bytes, NULL);
			xmlsaxctx = xmlCreatePushParserCtxt(&SAXHandler, ctx, buf, bytes, NULL);
			continue;
		}

		xmlParseChunk(xmlctx, buf, bytes, 0);
		if (!ctx->root_elem_found) xmlParseChunk(xmlsaxctx, buf, bytes, 0); // Don't update the SAX parser once it's served its purpose.
	}
	return APR_SUCCESS;
}

static const char *mapfile_dir_set(cmd_parms *cmd, oems_conf *cfg, const char *arg) {
	cfg->mapfiledir = arg;
	return 0;
}

static const char *default_mapfile_set(cmd_parms *cmd, oems_conf *cfg, const char *arg) {
	cfg->defaultmap = arg;
	return 0;
}

static void *create_dir_config(apr_pool_t *p, char *dummy)
{
	oems_conf *cfg;
	cfg = (oems_conf *)(apr_pcalloc(p, sizeof(oems_conf)));

	// compile regexes
	daily_time = ap_pregcomp(p, daily_time_pattern, 0);
	subdaily_time = ap_pregcomp(p, subdaily_time_pattern, 0);

    return cfg;
}

// Retrieve parameter value from URL
void get_param(char *args, char *Name, char *Value) {
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

// Return mapfile with full path
char *get_mapfile(request_rec *r, char *mapfile, const char *mapfiledir, const char *defaultmap) {
	get_param(r->args, "crs", mapfile); // Use CRS for WMS 1.3
	if(strlen(mapfile) == 0) {
		get_param(r->args, "srs", mapfile); // Use SRS for WMS 1.1
		if(strlen(mapfile) == 0) {
			get_param(r->args, "srsname", mapfile); // Use SRSNAME for WFS
			if(strlen(mapfile) == 0) {
				mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, defaultmap);
			}
		}
	}
	if (ap_strstr(mapfile, "4326") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg4326.map");
	} else if (ap_strstr(mapfile, "3031") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3031.map");
	} else if (ap_strstr(mapfile, "3413") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3413.map");
	} else if (ap_strstr(mapfile, "3857") != 0) {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, "epsg3857.map");
	} else {
		mapfile = apr_psprintf(r->pool, "%s/%s", mapfiledir, defaultmap);
	}
	return mapfile;
}

// Check for valid arguments and transform request for Mapserver
char *validate_args(request_rec *r, char *mapfile) {
	char *args = r->args;
	char proj[4];
	int max_chars;
	max_chars = strlen(r->args) + 1;

	// Time args
	const char *time_error = "Invalid TIME format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ";
	apr_time_exp_t tm = {0};
	apr_size_t tmlen;
	char *time = (char*)apr_pcalloc(r->pool,max_chars);
	char *doytime = (char*)apr_pcalloc(r->pool,max_chars); // Ordinal date with time
	char *productyear = (char*)apr_pcalloc(r->pool,5);
	char *formatted_time = (char*)apr_pcalloc(r->pool,21);
	char *subdaily = 0;

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


	// Previous args
	char *prev_format = 0;
	char *prev_time = 0;

	// Set notes from previous request if there is one
	if (r->prev != 0) {
		prev_format = (char *) apr_table_get(r->prev->notes, "oems_format");
		prev_time = (char *) apr_table_get(r->prev->notes, "oems_time");
		if (prev_format != 0) {
			apr_table_setn(r->notes, "oems_format", prev_format);
		} else {
			apr_table_setn(r->notes, "oems_format", format);
		}
		if (prev_time != 0) {
			apr_table_setn(r->notes, "oems_time", prev_time);
		}
	} else {
		apr_table_setn(r->notes, "oems_format", format);
	}

	// handle TIME
	if (ap_strchr(time, '-') != 0) {
		int i; i= 0;
		char *times[6];
		char *t;
		char *last;
		t = apr_strtok(time,"-",&last);
		while (t != NULL && i < 3) {
			times[i++] = t;
			t = apr_strtok(NULL,"-",&last);
		}
		if (times[2] == NULL) {
			ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, time_error);
			ap_rprintf(r, time_error);
			return 0;
		}
		if (ap_strstr(times[2],"T") != 0) {
			subdaily = times[2];
			// Check for subdaily delimiters
			if (ap_strstr(subdaily,":") != 0) {
				t = apr_strtok(subdaily,"T:",&last);
				i = 2;
				while (t != NULL && i < 6) {
					times[i++] = t;
					t = apr_strtok(NULL,"T:",&last);
				}
			} else if (ap_strstr(subdaily,"%3A") != 0) {
				t = apr_strtok(subdaily,"T%",&last);
				i = 2;
				while (t != NULL && i < 6) {
					times[i++] = t;
					t = apr_strtok(NULL,"T%",&last);
				}
				if (ap_strstr(times[4],"3A") != 0) {
					times[4] += 2;
				}
				if (ap_strstr(times[5],"3A") != 0) {
					times[5] += 2;
				}
			}
		}
		if (subdaily == 0) {
			time = apr_psprintf(r->pool, "%s-%s-%s", times[0], times[1], times[2]);
			if (ap_regexec(daily_time,time,0,NULL,0)) {
				ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, time_error);
				ap_rprintf(r, time_error);
				return 0;
			}
		} else {
			time = apr_psprintf(r->pool, "%s-%s-%sT%s:%s:%s", times[0], times[1], times[2], times[3], times[4], times[5]);
			if (ap_regexec(subdaily_time,time,0,NULL,0)) {
				ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, time_error);
				ap_rprintf(r, time_error);
				return 0;
			}
		}
		apr_table_setn(r->notes, "oems_time", time);

		tm.tm_year = apr_atoi64(times[0]) - 1900;
		tm.tm_mon = apr_atoi64(times[1]) - 1;
		tm.tm_mday = apr_atoi64(times[2]);
		if (subdaily != 0) {
			tm.tm_hour = apr_atoi64(times[3]);
			tm.tm_min = apr_atoi64(times[4]);
			tm.tm_sec = apr_atoi64(times[5]);
		}

		apr_time_t epoch = 0;
		apr_time_exp_get(&epoch, &tm);
		apr_time_exp_gmt(&tm, epoch);

		// Create DOY date and time
		apr_strftime(doytime, &tmlen, 14, "%Y%j", &tm);
		if (subdaily != 0) {
			apr_strftime(subdaily, &tmlen, 7, "%H%M%S", &tm);
		}

		// Validate real date/time
		if (subdaily != 0) {
			apr_strftime(formatted_time, &tmlen, 21, "%Y-%m-%dT%H:%M:%SZ", &tm);
			if (apr_strnatcasecmp(time, formatted_time)) {
				char *error = "Invalid TIME";
				ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, "%s: %s", error, time);
				ap_rprintf(r, error);
				return 0;
			}
		} else {
			apr_strftime(formatted_time, &tmlen, 11, "%Y-%m-%d", &tm);
			if (apr_strnatcasecmp(time, formatted_time)) {
				char *error = "Invalid date in TIME";
				ap_log_rerror( APLOG_MARK, APLOG_ERR, 0, r, "%s: %s", error, time);
				ap_rprintf(r, error);
				return 0;
			}
		}
	}

	// check if WMS or WFS
	if (ap_strcasecmp_match(service, "WMS") == 0)  {

		char *transparent = (char*)apr_pcalloc(r->pool,max_chars);
		char *layers = (char*)apr_pcalloc(r->pool,max_chars);
		char *srs = (char*)apr_pcalloc(r->pool,max_chars);
		char *styles = (char*)apr_pcalloc(r->pool,max_chars);
		char *width = (char*)apr_pcalloc(r->pool,max_chars);
		char *height = (char*)apr_pcalloc(r->pool,max_chars);
		char *maplayerops = (char*)apr_pcalloc(r->pool,max_chars);
		char *layer_years = (char*)apr_pcalloc(r->pool,max_chars);
		char *layer_times = (char*)apr_pcalloc(r->pool,max_chars);

		get_param(args,"transparent",transparent);
		get_param(args,"layers",layers);
		get_param(args,"styles",styles);
		get_param(args,"width",width);
		get_param(args,"height",height);

		// Projection handling
		long epsg = 0;
		char *p = r->uri;
		while (*p) {
			if (isdigit(*p)) {
				epsg = strtol(p, &p, 10);
			} else {
				p++;
			}
		}
		if (epsg != 0) {
			apr_table_setn(r->notes, "oems_srs", apr_psprintf(r->pool,"EPSG:%d", epsg)); // For mod_oemstime
		}
		if (ap_strstr(version, "1.1") != 0) {
			apr_cpystrn(proj, "SRS", 4);
			get_param(args,"srs",srs);
		} else {
			apr_cpystrn(proj, "CRS", 4);
			get_param(args,"crs",srs);
		}
		if(strlen(srs) == 0 || ((ap_strstr(srs, ":") == 0) && ap_strcasestr(srs, "%3A") == 0)) {
			apr_cpystrn(srs, "NONE", 5);
			apr_table_setn(r->notes, "oems_srs", 0);
		} else if (epsg == 0) {
			apr_table_setn(r->notes, "oems_srs", srs);
		}

		// Split out layers
		char *layer_cpy = (char*)apr_pcalloc(r->pool,max_chars);
		char *layer_time_param = (char*)apr_pcalloc(r->pool,strlen(layers)+6);
		char *layer_time_value = (char*)apr_pcalloc(r->pool,13);
		char *layer_subdaily_param = (char*)apr_pcalloc(r->pool,strlen(layers)+10);
		char *layer_subdaily_value = (char*)apr_pcalloc(r->pool,7);
		char *last_layer = 0;
	    char *prev_last_layer = 0;
	    char *prev_last_layers = 0;
	    if (r->prev != 0) {
	    	prev_last_layer = (char *) apr_table_get(r->prev->notes, "oems_clayer");
	    	prev_last_layers = (char *) apr_table_get(r->prev->notes, "oems_layers");
			last_layer = (char*)apr_pcalloc(r->pool,max_chars+strlen(prev_last_layer));
	    } else {
	    	last_layer = (char*)apr_pcalloc(r->pool,max_chars);
	    }
	    apr_cpystrn(layer_cpy, layers, strlen(layers)+1);
	    char *pt;
	    char *last;
	    pt = apr_strtok(layer_cpy, ",", &last);
	    while (pt != NULL) {
	    	if (prev_last_layers != 0) {
	    		if (ap_strstr(prev_last_layers, pt) == 0) {
	    			last_layer = pt;
	    		}
	    	} else {
		    	last_layer = pt;
	    	}
	    	layer_time_param = apr_psprintf(r->pool,"%s_TIME", pt);
	    	get_param(args,layer_time_param,layer_time_value);
	    	if(strlen(layer_time_value) != 0) {
	    		doytime = layer_time_value;
	    	}
	    	layer_subdaily_param = apr_psprintf(r->pool,"%s_SUBDAILY", pt);
	    	get_param(args,layer_subdaily_param,layer_subdaily_value);
	    	if(strlen(layer_subdaily_value) != 0) {
	    		subdaily = layer_subdaily_value;
	    	}
	    	// set to default if no time
	    	if (strlen(doytime) == 0 || ap_strstr(doytime, "TTTTTTT") != 0) {
    			doytime = "TTTTTTT";
    			productyear = "YYYY";
    		} else {
    	    	apr_cpystrn(productyear, doytime, 5);
    	    	productyear[4] = 0;
    		}
	    	if (subdaily != 0) {
				layer_times = apr_psprintf(r->pool,"%s&%s_TIME=%s&%s_SUBDAILY=%s", layer_times, pt, doytime, pt, subdaily);
	    	} else {
	    		layer_times = apr_psprintf(r->pool,"%s&%s_TIME=%s", layer_times, pt, doytime);
	    	}
	    	layer_years = apr_psprintf(r->pool,"%s&%s_YEAR=%s", layer_years, pt, productyear);
	    	// Get additional map.layer options
	    	char *layer_ops = (char*)apr_pcalloc(r->pool,max_chars);
	    	get_param(args,apr_psprintf(r->pool,"map.layer[%s]", pt), layer_ops);
	    	if (strlen(layer_ops) != 0) {
	    		maplayerops = apr_psprintf(r->pool,"%s&map.layer[%s]=%s", maplayerops, pt, layer_ops);
	    	}
	    	pt = apr_strtok(NULL, ",", &last);
	    }

	    if (prev_last_layer != 0) {
			if (prev_format != 0){
				last_layer = prev_last_layer;
				apr_table_setn(r->notes, "oems_layers", prev_last_layers);
			}
			apr_table_setn(r->notes, "oems_clayer", last_layer);
			if ((strlen(last_layer) != 0) && (prev_format == 0)) {
				last_layer = apr_psprintf(r->pool,"%s,%s", last_layer, prev_last_layers);
				apr_table_setn(r->notes, "oems_layers", last_layer);
			}
	    } else {
	    	apr_table_setn(r->notes, "oems_clayer", last_layer);
	    	apr_table_setn(r->notes, "oems_layers", last_layer);
	    }

	    if (strlen(last_layer) != 0) {
			// Set filters for time snapping if there is a layer that hasn't been checked
		    ap_filter_rec_t *receive_filter = ap_get_output_filter_handle("OEMSTIME_OUT");
		    if (receive_filter != NULL) {
		    	ap_filter_t *rf = ap_add_output_filter_handle(receive_filter, NULL, r, r->connection);
		    }
	    }

		// Add output filter to sanitize error messages from Mapserver. The filter iself is defined in this file.
		xml_filter_ctx *filter_ctx = (xml_filter_ctx *)apr_pcalloc(r->pool, sizeof(xml_filter_ctx));
		ap_filter_rec_t *err_filter_handle = ap_register_output_filter_protocol("mapserver_err_filter",
																		mapserver_output_filter,
																		NULL,
																		AP_FTYPE_CONTENT_SET,
																		AP_FILTER_PROTO_CHANGE
																		);
		ap_add_output_filter_handle(err_filter_handle, filter_ctx, r, r->connection);

	    // In case all layers have been stripped out due to invalid time requests
	    if (strlen(layers) == 0 && prev_last_layers != 0) {
	    	layers = apr_psprintf(r->pool,"INVALIDTIME");
	    }
		args = apr_psprintf(r->pool,"SERVICE=%s&REQUEST=%s&VERSION=%s&FORMAT=%s&TRANSPARENT=%s&LAYERS=%s&MAP=%s&%s=%s&STYLES=&WIDTH=%s&HEIGHT=%s&BBOX=%s%s%s%s","WMS",request,version,format,transparent,layers,mapfile,proj,srs,width,height,bbox,layer_times,layer_years,maplayerops);

	} else if (ap_strcasecmp_match(service, "WFS") == 0) {
		char *typenames = (char*)apr_pcalloc(r->pool,max_chars);
		char *outputformat = (char*)apr_pcalloc(r->pool,max_chars);
		char *srsname = (char*)apr_pcalloc(r->pool,max_chars);
		char *layer_years = (char*)apr_pcalloc(r->pool,max_chars);
		char *layer_times = (char*)apr_pcalloc(r->pool,max_chars);

		get_param(args,"typenames",typenames);
		if(strlen(typenames) == 0) {
			get_param(args,"typename",typenames);
		}
		get_param(args,"outputformat",outputformat);
		if(strlen(outputformat) == 0) { // default output when none provided
			outputformat = apr_psprintf(r->pool,"text/xml;subtype=gml/3.2.1");
		}
		get_param(args,"srsname",srsname);
		if(strlen(srsname) == 0 || ap_strstr(srsname, ":") == 0) {
			apr_table_setn(r->notes, "oems_srs", 0);
		} else {
			apr_table_setn(r->notes, "oems_srs", srsname);
		}

		// Prepend typenames to TIME and YEAR
		char *layer_cpy = (char*)apr_pcalloc(r->pool,max_chars);
	    apr_cpystrn(layer_cpy, typenames, strlen(typenames)+1);
	    char *pt;
	    char *last;
	    pt = apr_strtok(layer_cpy, ",", &last);
	    while (pt != NULL) {
	    	layer_times = apr_psprintf(r->pool,"%s&%s_TIME=%s", layer_times, pt, doytime);
	    	apr_cpystrn(productyear, doytime, 5);
	    	productyear[4] = 0;
	    	layer_years = apr_psprintf(r->pool,"%s&%s_YEAR=%s", layer_years, pt, productyear);
	    	pt = apr_strtok(NULL, ",", &last);
	    }

		args = apr_psprintf(r->pool,"SERVICE=%s&REQUEST=%s&VERSION=%s&OUTPUTFORMAT=%s&TYPENAMES=%s&MAP=%s&%s&%s","WFS",request,version,outputformat,typenames,mapfile,layer_times,layer_years);
		if(strlen(srsname) != 0) {
			args = apr_psprintf(r->pool,"%s&SRSNAME=%s",args,srsname);
		}
		if(strlen(bbox) != 0) {
			args = apr_psprintf(r->pool,"%s&BBOX=%s",args,bbox);
		}
	} else {
		args = r->args;
	}
	return args;
}

// OnEarth Mapserver handler
static int oems_handler(request_rec *r) {
	oems_conf *cfg = static_cast<oems_conf *>ap_get_module_config(r->per_dir_config, &oems_module);
	if (cfg->mapfiledir == 0 || cfg->defaultmap == 0) {
		return DECLINED; // Don't handle if no mapfile can be found
	}
	char *mapfile = (char*)apr_pcalloc(r->pool,strlen(cfg->mapfiledir)+strlen(cfg->defaultmap)+1);
	mapfile = apr_psprintf(r->pool, "%s/%s", cfg->mapfiledir, cfg->defaultmap);
	// Call Mapserver with mapfile
	r->args = validate_args(r, mapfile);
//	ap_log_error(APLOG_MARK, APLOG_WARNING, 0, r->server, "Mapserver args: %s", r->args);
	if (r->args != 0) {
		return DECLINED; // Pass request to Mapserver
	} else {
		return OK; // We handled this request due to errors
	}
}

// Main handler for module
static int handler(request_rec *r) {
	if (r->method_number != M_GET) return DECLINED;

	if (!(r->args)) { // Don't handle if no arguments
		return DECLINED;
	} else {
		if ((ap_strstr(r->args, "SERVICE=WMS") == 0) && (ap_strstr(r->args, "SERVICE=WFS") == 0)) { // Don't handle if not WMS or WFS
			return DECLINED;
		}
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
		"DefaultMapfile",
		(cmd_func) default_mapfile_set,
		0, /* argument to include in call */
		ACCESS_CONF, /* where available */
		"File name of the default mapfile" /* help string */
	),
	{NULL}
};

static void register_hooks(apr_pool_t *p) {
	ap_hook_handler(handler, NULL, NULL, APR_HOOK_FIRST);
}

module AP_MODULE_DECLARE_DATA oems_module = {
    STANDARD20_MODULE_STUFF,
    create_dir_config, 0, 0, 0, cmds, register_hooks
};
