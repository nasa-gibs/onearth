/* 
 * WMS cache module for Apache 2.0
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
 *
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

// Why does injest need extra headers?
#include <unistd.h>
#include <math.h>

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
} wms_cfg;

// Module constants
static char kmltype[]="application/vnd.google-earth.kml+xml";
static int kmlt_len=36; // Number of charachters in kmltype
static char Matrix[]="TILEMATRIX=";
static int matrix_len=11; // Number of chars in Matrix;

static char WMTS_marker[]="=WMTS";

// This module
module AP_MODULE_DECLARE_DATA wms_module;

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

// Apply a time stamp to a movie
char *tstamp_fname(request_rec *r,char *fname)
{
  static char* timearg="time=";
  static char* tstamp="TTTTTTT";
  char *targ;

  if ((targ=ap_strcasestr(r->args,timearg))&&ap_strstr(fname,tstamp)) { 
    // This part is not apr compatible, since mktime is not available easily
    int year=0,month=0,day=0;
    char *fn=apr_pstrdup(r->pool,fname);
    char *fnloc=ap_strstr(fn,tstamp);
    // Get a new place
    char old_char=*(fnloc+7);

    targ+=5; // Skip the time= part
    year=apr_atoi64(targ);
    targ+=5; // Skip the YYYY- part
    month=apr_atoi64(targ);
    targ+=2; // Due to UV bug
    if ('-'==*targ) targ++;
    day=apr_atoi64(targ);
    if ((year)&&(month)&&(day)) { // We do have a time stamp
      static int moffset[12]={0,31,59,90,120,151,181,212,243,273,304,334};
      int leap=(year%4)?0:((year%400)?((year%100)?1:0):1);
      sprintf(fnloc,"%04d%03d",year,day+moffset[month]+((month>2)?leap:0));
      *(fnloc+7)=old_char; // We have to put this character back
    }
    return fn;
  } 
  return fname;
}

// Same, but uses a request, and does the time stamp part

static void *r_file_pread(request_rec *r, char *fname, 
                          apr_size_t nbytes, apr_off_t location)
{
  int fd;
  static char* timearg="time=";
  static char* tstamp="TTTTTTT";
  char *targ=0,*fnloc=0;

  void *buffer;
  apr_size_t readbytes;

  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
  //  "Pread file %s size %ld at %ld",fname,nbytes,location);
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
    apr_time_exp_t tm;
    char old_char=*(fnloc+7);
    targ+=5; // Skip the time= part
    tm.tm_year=apr_atoi64(targ)-1900; // Convert to tm standard
    targ+=5; // Skip the YYYY- part
    tm.tm_mon=apr_atoi64(targ);
    targ+=3; // Skip the MM- part
    tm.tm_mday=apr_atoi64(targ);
    if ((tm.tm_year)&&(tm.tm_mon)&&(tm.tm_mday)) { // We do have a time stamp
      static int moffset[12]={0,31,59,90,120,151,181,212,243,273,304,334};
      int leap=(tm.tm_year%4)?0:((tm.tm_year%400)?((tm.tm_year%100)?1:0):1);
      tm.tm_yday=tm.tm_mday+moffset[tm.tm_mon-1]+((tm.tm_mon>2)?leap:0);
      sprintf(fnloc,"%04d%03d",tm.tm_year+1900,tm.tm_yday);
      *(fnloc+7)=old_char; // so we have to put this character back
    }
  }

  if (0>(fd=open(fn,O_RDONLY))) 
  {
    if (!fnloc) return 0; else { // It was a timestamp, covert to default
      fnloc[1]=fnloc[2]=fnloc[3]=fnloc[4]=fnloc[5]=fnloc[6]=fnloc[7]='T';
      fnloc[0]='_';
      if (0>(fd=open(fn,O_RDONLY))) return 0;
    }
  }

  readbytes=pread64(fd,buffer,nbytes,location);
  if (readbytes!=nbytes)
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "Error reading from %s, read %ld instead of %ld, from %ld",fn,readbytes,nbytes,location);
  close(fd);
  return (readbytes==nbytes)?buffer:0;
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

  // This should never happen
  if (!cfg) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server, "Can't find module configuration");
    return 0;
  }

  if (cfg->caches) return msg_onlyone;

  if (0>(f=open(arg,O_RDONLY))) { 
    ap_log_error(APLOG_MARK,APLOG_ERR,0,server, 
    		"MOD_WMS: Can't open cache config file\n file %s: %s",arg,strerror(errno));
    cfg->caches=(Caches *)apr_pcalloc(cfg->p,sizeof(Caches));
    cfg->caches->size=0 ; cfg->caches->count=0;
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
	    cfg->meta[count].empties[lev_num].data=
	        p_file_pread(cfg->p,apr_pstrcat(cfg->p,cfg->cachedir,levelt->dfname,0),
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
    return -1;
 }
 return level->index_add + sizeof(index_s) * (y*level->xcount+x);
 
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

  return 
    level->index_add+sizeof(index_s)*(iy*level->xcount+ix);
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

  ap_log_error(APLOG_MARK,APLOG_DEBUG,0,r->server, "Start URL should be %s",hname(r,1));

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
    ap_get_module_config(r->per_dir_config,&wms_module);

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
  image_arg=apr_pstrcat(r->pool,r->args,"image/png",the_rest,0);

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
    image_arg=apr_pstrcat(r->pool,r->args,"image/jpeg",the_rest,0);
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

  // Get the configuration
  cfg=(wms_cfg *) 
    ap_get_module_config(r->per_dir_config,&wms_module);

  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got config");

  if (!(cfg->caches)) return DECLINED; // Not configured?
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "Got caches %d",cfg->caches->count);
  // Let's see if we have a request
  if (!(count=cfg->caches->count)) return DECLINED; // Cache count 0

  if (!cfg->meta) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
      "No prepared regexps");
    return DECLINED;
  }

  // DEBUG
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, "In WMS handler");

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
    if (r->connection->local_addr->port==80)
	ap_log_error(APLOG_MARK,LOG_LEVEL,0,r->server,
      "Unhandled %s%s?%s",r->hostname,r->uri,r->args);
	else
	ap_log_error(APLOG_MARK,LOG_LEVEL,0,r->server,
      "Unhandled %s:%d%s?%s",r->hostname,r->connection->local_addr->port,r->uri,r->args);
    return DECLINED; // No cache pattern match, pass it to the real wms server
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
	    ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
			"Unmatched level %s",r->args);
		return DECLINED; // No level match
      }

      // DEBUG
      // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,"Got level %d %s %s",level,level->ifname,level->ifname);

      if ((WMSlevel *)1==level) { // Malformed bbox
	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server, "Sending error, bad bbox");
	return wms_return_error(r,
	  "WMS parameter bbox format incorect");
      }

      if ((WMSlevel *)2==level) { // Too far from bin level
	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server, 
	      "Sending error, not cached %s",r->args);
	return wms_return_error(r,
	  "Resolution not cached. Please do not modify configuration!");
      }

      // got a matching level and cache
      offset=get_index_offset(level,&bbox,cache->orientation,r);

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
		return DECLINED; // No level match
    }

    if (level<(WMSlevel *) 2) {
	ap_log_error(APLOG_MARK,APLOG_WARNING,0,r->server,
	  "Can't find TILEMATRIX %s",r->args);
	return DECLINED;
    }

    offset=wmts_get_index_offset(r,level);
    if (0>offset) 
      return DECLINED; 
  }

  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
  //            "record read prepared %s %d", cfg->cachedir, offset);

  this_record=r_file_pread(r,
              apr_pstrcat(r->pool,cfg->cachedir,level->ifname,0),
              sizeof(index_s),offset);

  if (!this_record) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
                 "Can't get index record from %s\nBased on %s",
		 tstamp_fname(r,level->ifname),r->args);
    perror("Index read error: ");
    return DECLINED;
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
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
  //   "Try to read tile from %ld, size %ld\n",this_record->offset,this_record->size);

  if (this_record->size) {
    this_data=r_file_pread(r,
            apr_pstrcat(r->pool,cfg->cachedir,level->dfname,0),
            this_record->size,this_record->offset);
  } else {
    int lc=level-GETLEVELS(cache);
    if ((cfg->meta[count].empties[lc].index.size)&&
	(cfg->meta[count].empties[lc].data)) {
        this_record->size=cfg->meta[count].empties[lc].index.size;
        this_data=cfg->meta[count].empties[lc].data;
    } else { // This might be first time, we need to read the empty page
      if (cfg->meta[count].empties[lc].index.size) {
        this_record->size=cfg->meta[count].empties[lc].index.size;
        this_record->offset=cfg->meta[count].empties[lc].index.offset;
	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
	  "INITIALIZING EMPTY FOR: %s",r->args);
        this_data=
	cfg->meta[count].empties[lc].data=p_file_pread(cfg->p,
		apr_pstrcat(r->pool,cfg->cachedir,level->dfname,0),
		this_record->size, this_record->offset);
      }
      if (!this_data) { // No empty tile provided, let it pass
	miss_count--;
	ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
	  "Record not present %s",r->args);
        return DECLINED;
      }
    }
  }

  if (!this_data) {
    ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
       "Data read error from file %s size %lld offset %lld",level->dfname,this_record->size, this_record->offset);
    return DECLINED; // Can't read the data for some reason
  }

  // DEBUG
  // ap_log_error(APLOG_MARK,APLOG_ERR,0,r->server,
  // "Got data at %x",this_data);

  ap_set_content_type(r,cfg->meta[count].mime_type);
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

static int handler(request_rec *r) {
  // Easy cases first, Has to be a get with arguments
  if ((r->method_number != M_GET) || (!(r->args))) return DECLINED;

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

module AP_MODULE_DECLARE_DATA wms_module =
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
