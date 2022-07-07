# mod_convert

An AHTSE component (apache httpd module) to convert tile image formats

# Status

Only implicit conversion from JPEG w/Zen (8 or 12bit) to JPEG or PNG is supported currently.  
Explicit LUT driven modification of values is handled, for unsigned short to byte or byte to byte.

# Building

Requires libahtse.  

# Apache Configuration Directives  

## *Convert_RegExp* Match  
Can be used more than once, a request has to match at least one of the patterns before it is considered a mod_convert request

## *Convert_ConfigurationFiles* source_configuration_file configuration_file
The source_configuration should be the name of the file describing the AHTSE tile data source.  The main_configurtion contains directives controlling the output of the mod_convert.

## *Convert_Indirect* On
If set, the AHTSE convert module will not respond to normal requests, only to internal subrequests


# AHTSE directives that can appear both the source and the main configuration

## Size X Y Z C
- Mandatory entry, the size of the source image in pixels.  Z defaults to 1 and C defaults to 3

## PageSize X Y Z C
- Optional, pagesize of the source in pixels.  Defaults to 512 512 1 and Size:C

## SkippedLevels N
- Optional, defaults to 0.  How many levels at the top of the overview pyramid are not counted

## DataType Type
- Optional, defaults to Byte.  JPEG and PNG support Byte and UInt16

## EmptyTile size offset filename
- Optional, the file which is sent as the default (missing) tile.  When present, filename is required.  Offset defaults to 0 and size defaults to the size of the file.
If this directive is not present, a missing tile request will result in a HTTP not found (400) error.

## ETagSeed value
- Optional, a base 32 encoded 64bit value, used as a seed for ETag generation.  Defaults to 0

## NoDataValue value
- Optional, the value of the nodata pixels, single numerical value, C style double

## MinValue value
- Optional, the minimum value of the pixels, single numerical value, C style double

## MaxValue value
- Optional, the maximum value of the pixels, single numerical value, C style double

# Directives that appear in the convert configuration only

## SourcePath Redirect_Path Postfix
- Mandatory, the location of the source, up to the first numerical argument, as a local web path

## SourcePostfix string
- Optional, a constant string literal that is appended to each request to the source

## LUT conversion_list
- Optional, only valid when input data type is different from the output data type, single band data conversion via linear interpolation on segments.
Only implemented for UInt16 to Byte.
The conversion list is a comma separated list of pairs separated by colon.  
Example:  
LUT 0:0,1:1,4095:255
