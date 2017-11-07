# mod_twms

# WORK IN PROGRESS
# LIMITED FUNCTIONALITY

An apache httpd module converting tiledWMS requests to the REST M/L/R/C encoding

* Requirements
- Apache 2.x, runtime and development
* Building

** Linux
In the src folder, edit Copy Makefile.lcl.example as Makefile.lcl, edit content to match the current system.  Then run make.

** Windows
Visual Studio 2013 solution is included.  It assumes Apache 2.4 is installed under __\\Apache24, including the development files.

* Usage

Implements two apache configuration directives:
**tWMS_RegExp string**
Can be present more than once, one of the existing regular expressions has to match the request URL for the request to be considered

**tWMS_ConfigurationFile configuration_file**
Raster and tiled WMS specific directives

* Size X Y Z C : Mandatory, at last X and Y.  If C is specified Z also has to be present.  Z defaults to 1 and C to 3

* PageSize X Y : Defaults to 512 512.

* SkippedLevels N : Optional, defaults to 0. How many levels of the equivalent MRF are skipped, from the top.

* BoundingBox xmin,ymin,xmax,ymax : WMS style bounding box.  Defaults to 0,0,1,1

* SourcePath local_path : Mandatory, the tile service used to provide the actual tiles, as a local http path. The three or four numerical tile address will be appended.

* SourcePostfix string : Optional, a string which will be appended to the source URL, after the tile address.  Can not include http paramters.

The extra dimension of the tile dataset can be passed as the value for the parameter called M. If present, the source service will receive tile requests with four numerical values, M/L/R/C

