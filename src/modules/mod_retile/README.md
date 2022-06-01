# mod_retile [AHTSE](https://github.com/lucianpls/AHTSE)

An apache module that converts an AHTSE tile service from one projection or tiling grid to another. 
In addition to tile grid conversions within the same projection can convert between GCS (lat-lon), Web Mercator and WGS84 Mercator.

# Building

Requires libahtse, apache httpd, libapr to be available for linking and at runtime.
In Windows, headers shoudl be in \HTTPD\include. The libraries for all the above packages should be available in \HTTPD\lib and \HTTPD\bin

# Usage

When projecting from GCS to WM or backwards, the input level gets chosen based on the relative resolution of the output tile and the input levels.
There are two such values, calculated on the two axis.  The lowest output resolution axis figure is chosen, it will fall between two input levels. By default, the slightly lower resolution input level is chosen, which will lead to the minimum number of input tiles, thus maximum performance.  When the ___Oversample___ parameter is on, it chooses the next higher resolution input level, which in general will improve the output image sharpness, while degrading the performance slightly.
At hight latitudes, for GCS to WM projection it might be necessary to use an even higher input resolution level.  This can be done by using the ___ExtraLevels___ parameter, which takes a positive numerical value (defaults to 0).  The allowed extra levels are only used when needed (at high latitudes).
Use this setting with care, as it decreases performance considerably and increasing latency, processing and memory usage per request.  The ___Oversample___ and ___ExtraLevels___ have slightly different purpose and can be combined, for example having oversample off while allowing one or two extra levels.
They do interact however, the extra level implicit in the ___Oversample___ is added to the ones provided by ___ExtraLevels___.

Implements two apache configuration directives:

## Retile_RegExp pattern
Can be present more than once, one of the existing regular expressions has to match the request URL for the request to be considered

## Retile_ConfigurationFiles source_configuration_file configuration_file
The first file contains the source raster information, while the second the desired configuration for the output 

## Retile_Source string
Required, the source path, up to the numerical arguments, as a local web path suitable for a subrequest

## Retile_Postfix string
Optional, gets appended to the source URL tile requests, after the tile address

## Retile_Indirect On
Optional, if set the module only responds to indirect requests

# Directives in both source and retile configuration files

## Size X Y Z C
  - Mandatory, at least x and y, the raster size in pixels, in both files

## PageSize X Y 1 C
  - Optional, the pagesize in pixels, in both files, defaults to 512x512

## Projection string
  - Optional, in which case the bounding box has to be correct
  -- GCS, WGS84, EPSG:4326
  -- WM, EPSG:3857, EPSG:3785
  -- Mercator, EPSG:3395
  
## DataType type
  - Required if not unsigned byte.  Valid values are Byte, Int16, UInt16, Int32, UInt32, Float.  Case insensitive
 
## SkippedLevels N
  - Optional, defaults to 0, counted from the top of the pyramid, in both files

## BoundingBox xmin,ymin,xmax,ymax
  - Optional, , defaults to the 0 to 1 interval, in both x and y.  These are mandatory when using this module for geo projection 
  change, otherwise the defaults will apply. WMS style bounding box, floating point using decimal dot format, comma separated
  
## ETagSeed base32_value
  - A base32 64bit number, to be used as a seed for ETag generation

# Directives valid only in the retile configuration file

## EmptyTile size offset filename
  - Size is required, Offset defaults to zero and filename defaults to sourcepath

## Format mtype
  - Output format

## InputBufferSize size
  - Buffer for one input tile, default is 1MB, should be larger than the maximum expected input tile size

## OutputBufferSize size
  - Buffer for out output tile, default is 1MB, should be larger than the maximum expected output tile size

## Quality value
  - A floating point value, controls the output format features, it is format dependent.  Default for JPEG is 75.  Default for PNG is 6

## Oversample On
  - If on and the output resolution falls between two available input resolution levels, the lower resolution input will be chosen instead of the higher one

## ExtraLevels N
  - By default, mod_retile avoids oversampling, which can generate stretched pixels in one direction. Turning oversample on picks the next higher resolution level. This parameter lets it use more higer resolution levels.  It defaults to 0, the value is in addition to the one added by oversample (if on).

## Nearest On
  - If on, use nearest neighbor resampling instead of bilinear interpolation

## Radius value
  - The planet radius in meters, used in projection calculations. Default is the earth major radius

## Transparent On
  - If set, the 0 value pixels in the output will be set as transparent (PNG only)
