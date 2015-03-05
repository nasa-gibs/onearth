## mrfgen.py

This tool is used to help automate the generation of MRF files. It takes in a list of image files or a single global image and generates an MRF output that is configured for use with the OnEarth server.

## Installation

Yum install
```Shell
sudo yum -y install onearth-mrfgen-*.el6.x86_64.rpm
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
  -s SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
```

## Samples

* [Sample mrfgen configuration file](mrfgen_configuration_sample.xml)
* [mrfgen configuration schema](mrfgen_configuration.xsd)

## Instructions

Sample imagery and configurations may be found [here](test/).

### Prepare Imagery

* Gather image files for generating the MRF.  Imagery must be PNG, JPEG, or GeoTIFF.  ESRI [world files](http://en.wikipedia.org/wiki/World_file) may be used for geo-referencing.

* Bit depth must be 24-bit true color or-bit indexed color; alpha channel is optional.

* A single global image or a set of tiles may be used as input.

### Create Configuration File

Prepare an MRF configuration file.  This [file](test/mrfgen_test_config.xml) may be used as an example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mrfgen_configuration>
 <date_of_data>20141004</date_of_data>
 <parameter_name>MYR4ODLOLLDY</parameter_name>
 <input_dir>test/MYR4ODLOLLDY</input_dir>
 <output_dir>test/output_dir</output_dir>
 <working_dir>test/working_dir</working_dir>
 <logfile_dir>test/logfile_dir</logfile_dir>
 <mrf_empty_tile_filename>empty_tiles/transparent.png</mrf_empty_tile_filename>
 <mrf_blocksize>512</mrf_blocksize>
 <mrf_compression_type>PPNG</mrf_compression_type>
 <target_x>4096</target_x>
</mrfgen_configuration>
```

#### Parameters

* date_of_data: Denotes the actual date of the file, which will be appended to the resulting MRF filename.  ```<time_of_data>``` may be used for sub-daily imagery.
* parameter_name: The layer name, which is also used as the suffix of the file name.
* input_dir: The location of the input tiles. Individual tiles may be alternatively specified using ```<input_files>```
* output_dir: The location of the resulting MRF.
* working_dir: The staging directory for generating the MRF. This should NOT be the same as the input or output directory as files will be deleted.
* logfile_dir: The location of the log files.
* mrf_empty_tile_filename: The file to be used for when there is a request for a tile with that is empty or contains all NoData values. It should be in the same file format as the MRF.
* mrf_blocksize: The MRF tile size. All tiles are square.
* mrf_compression_type: The internal image of the MRF. Valid values are JPEG, PNG (for RGBA PNGs), or PPNG (for 256 color paletted PNGs).
* target_x: The full x output size of the MRF image. The y value is half of x when not provided using ```<target_y>```.  ```<outsize>``` may be used to specify both x and y output size as one parameter.  

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
* mrf_name: The output naming convention of the MRF file (e.g., ``` <mrf_name>{$parameter_name}%Y%j_.mrf</mrf_name>```). Uses Python's [strftime formatting](https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior).
* colormap: The GIBS color map to be used if the MRF contains paletted PNGs ([example colormaps](https://map1.vis.earthdata.nasa.gov/colormaps/)).

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
 <mrf_empty_tile_filename>empty_tiles/transparent.png</mrf_empty_tile_filename>
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
mrfgen.py -c test/mrfgen_test_config.xml
```

The MRF will be generated.  If successful, an "MRF created" message will be displayed at the end.

You can also use the -d, --data_only option to output only the MRF data, index, and header files:
```Shell
mrfgen.py -d -c test/mrfgen_test_config.xml
```

### SigEvent

mrfgen is compatible with the SigEvent reporting server. This is helpful for sending logs and error messages to an automated system. Use the -s, --sigevent_url to enable SigEvent services:
```Shell
mrfgen.py -c test/mrfgen_test_config.xml -s http://localhost:8100/sigevent/events/create
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
 