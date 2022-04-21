## mrfgen.py

This tool is used to help automate the generation of MRF files. It takes in a list of image files or a single global image and generates an MRF output that is configured for use with the OnEarth server.

## Installation

Yum install
```Shell
sudo yum -y install onearth-mrfgen-*.x86_64.rpm
```

Manual install
```Shell
cp src/mrfgen <installation location>
```

## Usage

```
Usage: mrfgen.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIGURATION_FILENAME, --configuration_filename=CONFIGURATION_FILENAME
                        Full path of configuration filename.  Default:
                        ./mrfgen_configuration_file.xml
  -d, --data_only       Only output the MRF data, index, and header files
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value)
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value)
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value)
  --email_logging_level=EMAIL_LOGGING_LEVEL
                        Logging level for email notifications: ERROR, WARN, or
                        INFO.  Default: ERROR
```

## Samples

* [Sample mrfgen configuration file](mrfgen_configuration_sample.xml)
* [mrfgen configuration schema](mrfgen_configuration.xsd)

## Instructions

Sample imagery and configurations may be found [here](../test/mrfgen_files/).

### Prepare Imagery

* Gather image files for generating the MRF.  Imagery must be PNG, JPEG, or [GeoTIFF](http://trac.osgeo.org/geotiff/).  ESRI [world files](http://en.wikipedia.org/wiki/World_file) may be used for geo-referencing.

* Bit depth must be 24-bit true color or 8-bit indexed color; alpha channel is optional.

* A single global image or a set of tiles may be used as input.

* An "encoded" PNG (where a Float32 data type is packed into a 3 channel RGB image) can optionally be generated from GeoTIFF input.  

### Create Configuration File

Prepare an MRF configuration file.  This [file](../test/mrfgen_files/mrfgen_test_config.xml) may be used as an example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mrfgen_configuration>
 <date_of_data>20141004</date_of_data>
 <parameter_name>MYR4ODLOLLDY</parameter_name>
 <input_dir>test/MYR4ODLOLLDY</input_dir>
 <output_dir>test/output_dir</output_dir>
 <working_dir>test/working_dir</working_dir>
 <logfile_dir>test/logfile_dir</logfile_dir>
 <mrf_empty_tile_filename>empty_tiles/Blank_RGBA_512.png</mrf_empty_tile_filename>
 <mrf_blocksize>512</mrf_blocksize>
 <mrf_compression_type>PPNG</mrf_compression_type>
 <target_x>4096</target_x>
</mrfgen_configuration>
```

Directory paths may be different than the example. Directories that do not exist must be created before running the tool.

#### Parameters

* date_of_data: (format: yyyymmdd) Denotes the actual date of the file, which will be appended to the resulting MRF filename.  ```<time_of_data>``` (format: HHMMSS) may be used for sub-daily imagery.
* parameter_name: The layer name, which is also used as the suffix of the file name.
* input_dir: The location of the input tiles. Individual tiles may be alternatively specified using ```<input_files>``` with each file specified within a ```<file>``` sub-element.
* output_dir: The location of the resulting MRF.
* working_dir: The staging directory for generating the MRF. This should NOT be the same as the input or output directory as files will be deleted.
* logfile_dir: The location of the log files.
* mrf_empty_tile_filename: The file to be used for when there is a request for a tile with that is empty or contains all NoData values. It should be in the same file format as the MRF.
* mrf_blocksize: The MRF tile size. All tiles are square.
* mrf_compression_type: The internal image of the MRF. Valid values are JPEG, PNG (for RGBA PNGs), PPNG (for 256 color paletted PNGs), EPNG (for encoded PNGs, requires [overtiffpacker.py](overtiffpacker.py)), JPNG (for blended JPEG/PNG MRF), TIFF, or [LERC](https://github.com/Esri/lerc).
* target_x: The full x output size of the MRF image. target_y is calculated to maintain native aspect ratio if not defined in ```<target_y>```.  ```<outsize>``` may be used to specify both x and y output size as one parameter.  
* mrf_merge: (true/false) Whether overlapping input images should be merged on a last-in basis when performing inserts. Defaults to "false" for faster performance.
* mrf_noaddo: (true/false) Don't run gdaladdo if UNIFORM_SCALE has been set. Defaults to "false".
* mrf_clean: (true/false) run mrf_clean.py script on generated mrf file to reduce file size
* mrf_parallel: (true/false) run mrf_insert calls in parallel to improve performance. See num_cores.
* num_cores: (int) number of cores to use with mrf_parallel. Recommended is 2-4, depending on number of input files.
* mrf_strict_palette: (true/false) Validate that the colors in input files match the MRF colormap. A warning is sent if there are mismatches. Defaults to "false".

These parameters are available but not used in the example above nor necessarily required.

* vrtnodata: The value to be used as "NoData" in the VRT (which propagates to the MRF). mrfgen builds uses a VRT of input tiles to generate the MRF. The rules for vrtnodata as the same as [gdalbuildvrt](http://www.gdal.org/gdalbuildvrt.html).
* overview_levels: The overview levels used in the MRF. This is the same as the "levels" used in [gdaladdo](http://www.gdal.org/gdaladdo.html). By default, mrfgen calculates the levels based on the output size of the MRF using powers of 2 (e.g., ```<overview_levels>2 4 8</overview_levels>```).
* overview_resampling: The resampling method to be used during overview building. Valid values are: nearest, average, gauss, cubic, average_mp, average_magphase, mode, avg.
* reprojection_resampling: The resampling method to be used with [gdalwarp](http://www.gdal.org/gdalwarp.html). This is used is ```<target_epsg>``` is specified.
* resize_resampling: If input imagery are different sizes, this option forces the input to be resized using [gdalwarp](http://www.gdal.org/gdalwarp.html) resampling methods. Use "none" if not desired.
* target_epsg: The EPSG code of the target projection. Providing this option will force the imagery to be reprojected.
* source_epsg: The EPSG code of the source projection. EPSG:4326 is assumed if not provided.
* extents: The extents of the complete source imagery.
* target_extents: The extents of the MRF after reprojection (only used when target_epsg is provided).
* mrf_name: The output naming convention of the MRF file (e.g., ``` <mrf_name>{$parameter_name}%Y%j_.mrf</mrf_name>```). Uses Python's [strftime formatting](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).
* colormap: The GIBS color map to be used if the MRF contains paletted PNGs ([example colormaps](https://gibs.earthdata.nasa.gov/colormaps/)).
* mrf_z_levels: The maximum number of z levels for the final MRF.
* mrf_z_key: The string key (e.g., time [YYYYMMDDhhmmss], elevation, band, style) used to map to a z level. See sample [here](../test/mrfgen_files/mrfgen_test_config4c.xml).
* mrf_data_scale: Scale value for the input data. mod_onearth can output this value in the HTTP header of a tile request.
* mrf_data_offset: Offset value for the input data. mod_onearth can output this value in the HTTP header of a tile request.
* mrf_data_units: The unit of measurement for the input data. mod_onearth can output this value in the HTTP header of a tile request.
* quality_prec: The quality for JPEG (defaults to 80) or precision for LERC (defaults to 0.001).
* source_url: The URL of the source data file.
* email_server: The SMTP server where email notifications are sent from.
* email_recipient: The recipient address(es) for email notifications. Use semi-colon ";" to separate recipients.
* email_sender: The sender address for email notifications.

Let's modify the previous sample configuration to reproject the imagery into Web Mercator (EPSG:3857), generate a larger output size, and utilize a colormap:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mrfgen_configuration>
 <date_of_data>20141004</date_of_data>
 <parameter_name>MYR4ODLOLLDY</parameter_name>
 <input_dir>test/MYR4ODLOLLDY</input_dir>
 <output_dir>test/output_dir</output_dir>
 <working_dir>test/working_dir</working_dir>
 <logfile_dir>test/logfile_dir</logfile_dir>
 <mrf_empty_tile_filename>empty_tiles/Blank_RGBA_512.png</mrf_empty_tile_filename>
 <mrf_blocksize>512</mrf_blocksize>
 <mrf_compression_type>PPNG</mrf_compression_type>
 <outsize>20480 20480</outsize>
 <overview_resampling>nearest</overview_resampling>
 <reprojection_resampling>near</reprojection_resampling> 
 <target_epsg>3857</target_epsg>
 <source_epsg>4326</source_epsg>
 <colormap>https://map1.vis.earthdata.nasa.gov/colormaps/MODIS_Aqua_Aerosol.xml</colormap>
</mrfgen_configuration>
```

### Execute mrfgen

Run mrfgen by calling the tool and passing in the configuration file:
```Shell
mrfgen.py -c mrfgen_test_config.xml
```

The MRF will be generated.  If successful, an "MRF created" message will be displayed at the end.

You can also use the -d, --data_only option to output only the MRF data, index, and header files:
```Shell
mrfgen.py -d -c mrfgen_test_config.xml
```

### SigEvent

mrfgen includes an email notification system. This is helpful for sending logs and error messages to an automated system. Use the -s, --send_email option to enable email notifications:
```Shell
mrfgen.py -c mrfgen_test_config.xml --send_email --email_server=EMAIL_SERVER --email_recipient=EMAIL_RECIPIENT --email_sender=EMAIL_SENDER
```

## mrfgen Processes

The following encoding steps occur in the mrfgen script:

* Seeding the MRF data file with a default empty tile
    * The empty tile is copied to MRF data file before it is built. The data file is modified by appending. See not about empty tile block.
* Creating a virtual mosaic
    * Input tiles are consolidated into a VRT file using [gdalbuildvrt](http://www.gdal.org/gdalbuildvrt.html) before conversion into MRF. E.g., ```gdalbuildvrt -te -180 -90 180 90 -input_file_list input_list.txt input.vrt```
* Converting the image data into the MRF data format
    * mrfgen uses [gdal_translate](http://www.gdal.org/gdal_translate.html) to convert the VRT into MRF. E.g., ```gdal_translate -of mrf -co BLOCKSIZE=512 -co COMPRESS=PPNG input.vrt output.mrf```
* Appending pyramid levels
    * mrfgen uses [gdaladdo](http://www.gdal.org/gdaladdo.html) to add overview levels. E.g., ```gdaladdo output.mrf -r average 2 4 8 16 ```

### Incremental updates to an MRF using mrfgen

mrfgen supports incremental updates to an existing MRF. This is useful for generating global near-real time imagery without the need to wait for all input tiles to be available.

This is done automatically if an MRF file is included in the ```<input_dir>``` or listed in ```<input_files>```.  This requires the [mrf_insert](https://github.com/nasa-gibs/mrf/tree/master/src/gdal_mrf/mrf_apps) tool to be installed.

### Empty Tile Block

The MRF format has another efficiency, which is the empty block. The empty block is a single block of the same size as the other internal blocks and is entirely the color of no data. The color of no data is usually black, white, or transparent. The empty block may be any image, but must be the same size as the internal blocks. The advantage gained by using the empty block is to speed the loading of that block when many instances are expected. If your data is sparse, then as the internal tiling is parceled out and the pyramid is built, there will be likely be many instances where an internal block contains no data. In those cases, the actual block is omitted from the MRF. Instead, it is flagged in the index file as an empty block. When the server requests a block that is flagged, the server will use the already-cached empty block. This eliminates one block request, which can add up to a lot of savings depending on how many empty blocks are in the data.

Adding an empty block to the MRF can be done two ways. First is to seed the MRF with the empty block. To seed the MRF with the empty block, copy the empty block to the name of the MRF output before running gdal_translate. The second method is to append the empty block to the end of the MRF. Appending should be done after adding the pyramid. The location of the empty block will be configured when the system is set up.

**When using the OnEarth system to serve palette color images to a Google Earth client:** Where the empty block is transparent, the color vectors and transparency vector must all be 256 elements. Otherwise the transparent empty block will appear opaque black.

### Optimizing the Input Size

The input image dimensions are not restricted, per se, but may need to be optimized. For example, clients built on OpenLayers will require that all data layers have nested dimensions, where the full resolution data of each layer is the same size as one of the pyramid levels of the highest resolution data layer. This constraint is imposed by the OpenLayers software, and unmatched layers will not overlay correctly. This constraint may be further constrained by the image data with the hightest resolution, where it may be undesireable to resample due to a very large size. If the data with the highest resolution (using the MODIS case) has dimensions of 163840 x 81920, then that should become the standard to which other layers must abide. A lower resolution layer might have a native resolution of 16384 x 8192, which could be changed to 20480 x 10240 to match the third pyramid level of the highest resolution data layer. Notice that the new size is increased to the next largest pyramid level in order preserve all of the native information. Here is the layout of the pyramid levels (for this example):

```
163840 x 81920 highest resolution data layer
81920 x 40960 first pyramid level
40960 x 20480 second pyramid level
20480 x 10240 third pyramid level
10240 x 5120
5120 x 2560
2560 x 1280
1280 x 640
640 x 320 final pyramid level
```

Another example would be for an input data layer with a custom overall size, such as 16000 x 8000. Increasing the resolution to 16384 x 8192 will enable the internal tiling size of 512 (or 256) to nest perfectly with the image dimension, with no partial blocks. Partial blocks can cause unwanted edge effects where the global image wraps around. Optimization of the input image dimensions (or the overall size of the input tile set) is generally recommended, but should be evaluated on a case-by-case basis.

## mrfgen Tests

The [test_mrfgen.py](../test/test_mrfgen.py) script may be used to test basic functionalities of mrfgen.

```Shell
cd test/
./test_mrfgen.py
```

## RGBApng2Palpng

The RGBApng2Palpng tool converts an RGBA PNG image to a Paletted PNG image using a GIBS color map or lookup table of comma-separated RGBA values.

### Compile

To compile the tool:
```Shell
gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng
```

### Usage

```Shell
Usage: RGBApng2Palpng [-v] -lut=<ColorMap file (must contain RGBA)> -fill=<LUT index value> -of=<output palette PNG file> <input RGBA PNG file>
```
* -v: Verbose print mode
* -lut: [GIBS color map](https://map1.vis.earthdata.nasa.gov/colormaps/) or lookup table of comma-separated RGBA values to be used as the PNG palette
* -fill: The fill value, used to fill the remaining palette of colors
* -of: The Paletted PNG output file

Example execution:
```Shell
./RGBApng2Palpng -v -lut=colormap.xml -fill=0 -of=pal_output.png rgba_input.png
```

If the RGBApng2Palpng tool detects colors in the image that are not in the colormap, they will be printed out to the command line at the end of the script. The number of missing colors is used as the exit code.

This tool is utilized by mrfgen.py.

## oe_validate_palette.py

oe_validate_palette.py is a tool for validating an image palette with a GIBS colormap. The output includes a summary of colors matched and the colors unique to the colormap and image. Mismatches are displayed if there are any. The system exit code will be one of the following values:
* 0 - Successful
* 1 - Mismatched colors found in the image palette only
* 2 - Mismatched colors found in the colormap only
* 3 - Mismatched colors found in both the image palette _and_ colormap


```Shell
Usage: oe_validate_palette.py --colormap [colormap.xml] --input [input.png] --verbose

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COLORMAP_FILENAME, --colormap=COLORMAP_FILENAME
                        Full path of colormap filename.
  -f FILL_VALUE, --fill_value=FILL_VALUE
                        Fill value for colormaps. Default: "0,0,0,0"
  -i INPUT_FILENAME, --input=INPUT_FILENAME
                        Full path of input image
  -n, --no_index        Do not check for matching index location
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value)
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value)
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value)
  --email_logging_level=EMAIL_LOGGING_LEVEL
                        Logging level for email notifications: ERROR, WARN, or
                        INFO.  Default: ERROR
  -v, --verbose         Print out detailed log messages
  -x IGNORE_COLORS, --ignore_colors=IGNORE_COLORS
                        List of RGBA color values to ignore in image palette
                        separated by "|"
```


## colormap2vrt.py

colormap2vrt.py is a tool for converting SLD ColorMaps to a VRT ColorTable template.

```Shell
Usage: colormap2vrt.py --colormap [colormap.xml] --output [output.vrt] --merge [merge.vrt] --transparent

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COLORMAP_FILENAME, --colormap=COLORMAP_FILENAME
                        Full path of colormap filename.
  -m MERGE_FILENAME, --merge=MERGE_FILENAME
                        Full path of VRT in which to merge colormap
  -o OUTPUT_FILENAME, --output=OUTPUT_FILENAME
                        Full path of the final output VRT
  -t, --transparent     Use transparent alpha value as default
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value)
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value)
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value)
  --email_logging_level=EMAIL_LOGGING_LEVEL
                        Logging level for email notifications: ERROR, WARN, or
                        INFO.  Default: ERROR
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
 
