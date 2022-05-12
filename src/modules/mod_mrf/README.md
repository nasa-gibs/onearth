# mod_mrf [AHTSE](https://github.com/lucianpls/AHTSE)

An apache module that serves tiles directly from a local MRF, 2D or 3D.  
With the MRF data on a local SSD, this module average tile request latency is .25ms (as measured by httpd), and reaches request rates above 20000 req/sec on a single core.

Apache configuration directives:

**MRF_RegExp**
 Required, only requests matching this pattern are handled.  It can appear multiple times
 If not provided, the module is inactive

**MRF_Indirect On|Off**

 If set, this module will only respond to internal subrequests

**MRF_ConfigurationFile  Filename**

 Points to an AHTSE Control text file, where the first word on a line is a directive, followed by parameters
 - Empty lines, lines that start with # are considered comments
 - Unknown directives are ignored

AHTSE Control Directives for this module are:

***DataFile path start_offset size***
 - The path to the MRF data file to serve tiles from. Start and size are optional, by default 
 a single DataFile is used. At least one DataFile directive is required.  If the path start 
 with ://, the path is interpreted as an internal redirect to a path 
 within the same server, starting from DocRoot. Otherwise it is assumed to be a local file 
 name. May appear multiple times, with different start offset and size values. If the values are 
 present, read operations within start_offset and start_offset + size are made to the data file, 
 after the read  offset is adjusted downward by start_offset.
 If the read offset falls outside the range, the other DataFile entries are searched, 
 in the order in which they appear in the configuration file. Old style redirects are tested last.
 The multiple entries allows an MRF data file to be split into multiple parts. Single tiles 
 cannot be split between sources, but overlapping ranges between source are allowed. Only one read 
 operation is issued, to the first DataFile entry that matches the range.  If the read fails, 
 the server will report an error.
 Start offset and size default to zero. Zero size means that any read above the offset will be 
 considered present in this data file.

***Size X Y Z C***
 - Mandatory, at least x and y, the size in pixels of the input MRF.
 Z defaults to 1 and C defaults to 3 (these are usually not meaningful)

***PageSize X Y 1 C***
 - Optional, the pagesize in pixels. X and Y default to 512. 
 Z has to be 1 if C is provided, which has to match the C value from size

***RetryCount N***
  - Optional, [0 - 99). If the DataFiles are redirects, how many times to retry a redirected 
  read that fails to retun the requested data. The Default is 5.

***IndexFile string***
 - Optional, the index file name. Can only be provided once.
  If not provided it uses the data file name if its extension is not three letters.
  Otherwise it uses the first data file name with the extension changed to .idx
  It can be a redirect path in the host namespace, if it starts with ://
 
***EmptyTile Size Offset FileName***
 - Optional, provides the tile content to be sent when the requested tile is missing.
 The file has to be local, since the empty tile is read at start-up
 By default the request is ignored, which results in a 404 error if a fallback mechanism does not 
 exist. If present, the first number is assumed to be the size, second is offset. If filename is 
 not given, the first data file name is used.

***SkippedLevels N***
 - Optional, how many levels to ignore, at the top of the MRF pyramid. For example a GCS pyramid 
 will have to skip the one tile level, so this should be 1
 
***ETagSeed base32_string***
 - Optional, 64 bits as 13 base32 digits [0-9a-v], defaults to 0. The empty tile ETag will be 
 this value but 65th bit is set, also the only value that has this bit set. All the other tiles 
 have 64 bit ETags that depend on this value.
 
***Dynamic On***
 - Optional, flags the local files as dynamic, disabling any caching or file handle reuse. To be used
 when the MRF files are changed at run-time, avoiding stale or even broken content.  MRF in-place
 modification do not require this flag because the old content is still available

 ***MMapping prefix***
 - Optional, controls the mapping of the M parameter to data source.  The only value currently 
 implemented is _prefix_, which means that the M, as a decimal number will be added right in front of
 the basename of the file, both the Index and Data. The range based data file split still applies, 
 each part will be prefixed by the M value


***CannedIndex On***
 - Optional, flags the index file as a canned format index, see mrf_apps/can.cpp.  This is a dense 
 format index that can be much smaller.  Should be used only when needed, and not recommended when
 Dynamic is also on

***Redirect path start_offset size***
  *Deprecated*, use the DataFile directive and start path with ://

For better performance on local files, the httpd source against which this module is compiled should include support for random file access optimization. A patch file for libapr is provided, see apr_FOPEN_RANDOM.patch

For better performance when using object stores, the mod_proxy should be patched to reuse connections on subrequests.  A patch file is included, see mod_proxy_httpd.patch
