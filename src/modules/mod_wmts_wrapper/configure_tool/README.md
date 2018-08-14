# OnEarth 2 Layer WMTS/TWMS Configuration Tools

## Tools Included:

* oe2_wmts_configure.py -- Configures WMTS and TWMS endpoints for layers to be
  served in their native projection.
* oe2_reproject_configure.py -- Configures WMTS and TWMS endpoints for
  reprojected layers.

---

## oe2_wmts_configure.py

This tool creates the necessary Apache configurations to serve MRF layers via
WMTS and TWMS, using the OnEarth Apache modules (`mod_wmts_wrapper, mod_mrf,
mod_twms`). It allows for both local and remote (i.e., S3) data files to be
used.

## Requirements

* Python 3.6
* OnEarth 2 modules (`mod_wmts_wrapper, mod_mrf, mod_receive, mod_twms`)
  compiled and installed.
* `mod_proxy` installed.

#### Running the tool

`oe2_wmts_configure.py endpoint_config {--make_twms}`

This tool requires 2 configuration files to work:

* endpoint config -- contains information about how the WMTS and TWMS endpoints
  should be set up in Apache.
* layer config(s) -- contains information about each of the layers to be
  configured.

Note that Apache must be restarted for new configurations to take effect. This
command may need to be run as `sudo` depending on the permission settings for
your Apache directories.

#### TWMS Configurations

If the tool is run with the `--make_twms` option set, it will create TWMS
configurations for the layers. The TWMS endpoint will be available as
`{endpoint}/twms.cgi`.

#### Endpoint Configuration

The endpoint configuration should be a YAML file in the following format:

```
endpoint_config_base_location: /var/www/html/wmts
layer_config_source: layer_configs
base_idx_path: /var/www/idx
date_service_uri: "http://127.0.0.1:8090/date"
apache_config_location: "/etc/httpd/conf.d"
```

##### Configuration Options:

`endpoint_config_base_location` (required) -- This is the path on disk where the
configuration files should be stored _for this endpoint_. This needs to be a
publicly-accessible path on the web server, such as `/var/www/wmts/epsg4326`,
etc. _Each endpoint should have its own unique path!_

`layer_config_source` (required) -- This can be a path either to a single layer
configuration YAML file, or a directory containing multiple layer config files.
In the case of a directory, the tool will parse all files in that directory with
a `.yaml` extension. _Note that the tool will not recurse the contents of
subdirectories if they are present._

`base_idx_path` (optional) -- If all the IDX files for your layers are container
in a base location on disk -- and if the layer configs themselves list IDX paths
as relative paths from that location, make sure this is included. Otherwise,
leave it out. (Read on to the layer configuration section for more information.)

`date_service_uri` (optional) -- If you are using dynamic layers, put the URL of
the OnEarth 2 date service here.

`apache_config_location` (optional) -- Location that the main Apache
configuration files will be stored (this will need to be somewhere Apache is
configured to read when it starts up). Defaults to `/etc/httpd/conf.d`

`date_service_keys` (optional) -- Array of keys to be used with the date
service. Keys will be positioned in the order configured.

#### Layer Configuration

The layer configurations contain all the necessary information for each layer
you intend to make accessible. They should be a YAML file in the following
format:

```
layer_id: "AMSR2_Snow_Water_Equivalent"
static: true
tilematrixset: "EPSG4326_2km"
source_mrf:
  size_x: 8192
  size_y: 4096
  bands: 3
  tile_size_x: 512
  tile_size_y: 512
  idx_path: "static_test.idx"
  data_file_uri: "http://127.0.0.1/data/static_test.pjg"
  year_dir: false
  bbox: -180,-90,180,90
mime_type: "image/jpeg"
```

### Configuration Options

`layer_id` (required) -- This is the layer name string that be used for
WMTS/TWMS requests.

`static` (optional) -- Indicates whether or not the layer allows for the TIME
dimension. Defaults to 'false'.

`tilematrixset` (required) -- The name of the Tile Matrix Set to be used with
this layer.

`source_mrf` (required) -- Subsection with information about the source MRF for
this layer.

`size_x` (required) -- MRF width in pixels.

`size_y` (required) -- MRF height in pixels.

`bands` (required) -- Number of bands in the MRF imagery. (JPEG usually 3, PNG
usually 4)

`tile_size_x` (required) -- Width of each tile in pixels.

`tile_size_y` (required) -- Height of each tile in pixels.

`idx_path` (required) -- Path on disk to this layer's IDX file. If the endpoint
configuration contains a `base_idx_path`, this path will be assumed to be
relative to that path.

`data_file_path` (optional) -- Path on disk to this layer's MRF data file.

`data_file_uri` (optional) -- Remote URI to this layer's MRF data file. If this
layer has a TIME dimension, just enter the path of the data file up to the year
directory (if it has one). `mod_wmts_wrapper` will calculate the filename using
the date service.

`year_dir` (optional) -- For dynamic layers, if the data and IDX files are
contianed in separate directories by year, set this to 'true'. This will cause
the OnEarth modules to append the year of the requested tile to the path of the
IDX and data files when they are accessed. Defaults to 'false'.

`bbox` (required for TWMS) -- Bounding box of the source MRF in the projection's
native units.

`mime_type` (required) -- MIME type of the tiles in this MRF.

Example: `date_service_keys: ["epsg4326", "std"]` will cause date lookups for
this layer to use the following format:
`{date_service_uri}/date?key1=epsg4326&key2=std`

---

## oe2_reproject_configure.py

This script creates WMTS and TWMS endpoints that use `mod_reproject` to
reproject imagery.

## Requirements

* Python 3.6
* OnEarth 2 modules (`mod_wmts_wrapper, mod_reproject, mod_receive, mod_twms`)
  compiled and installed.
* `mod_proxy` installed.

## Source Imagery

`mod_reproject` is designed to reproject tiles that are already available via a
WMTS endpoint. **It does not use MRFs!** If you want to reproject MRFs, first
use `oe2_wmts_configure.py` to make those MRFs available via a WMTS endpoint.

Note that this configuration tool uses the GetCapabilities file of a WMTS
endpoint to create its configurations.

#### Running the tool

`oe2_reproject_configure.py endpoint_config {--make_twms, --tms_defs}`

This tool requires 2 configuration files to work:

* endpoint config -- contains information about how the WMTS and TWMS endpoints
  should be set up in Apache.

Note that Apache must be restarted for new configurations to take effect. This
command may need to be run as `sudo` depending on the permission settings for
your Apache directories.

#### Tile Matrix Set definitions

This tool requires an XML Tile Matrix Set definitions file in order to work. A
file including the most commonly used Tile Matrix Sets is included
(`tilematrixsets.xml`), which this tool uses by default. The `--tms_defs` option
can be used to point the tool to a different file.

#### TWMS Configurations

If the tool is run with the `--make_twms` option set, it will create TWMS
configurations for the layers. The TWMS endpoint will be available as
`{endpoint}/twms.cgi`.

#### Endpoint Configuration

The endpoint configuration should be a YAML file in the following format:

```
endpoint_config_base_location: "/var/www/html"
source_gc_uri: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"
target_epsg_code: "EPSG:3857"
date_service_uri: "http://137.79.29.45:8090/date"
tms_defs_file: "/etc/oe2/tilematrixsets.xml"
apache_config_location: "/etc/httpd/conf.d/oe2-reproject-service.conf"
```

##### Configuration Options:

`endpoint_config_base_location` (required) -- This is the path on disk where the
configuration files should be stored _for this endpoint_. This needs to be a
publicly-accessible path on the web server, such as `/var/www/wmts/epsg3857`,
etc. _Each endpoint should have its own unique path!_

`source_gc_uri` (required) -- The URI of the GetCapabilities file that will be
used as the source for this endpoint. By default, all the layers present in this
file will be configured.

`target_epsg_code` (required) -- The projection that your source imagery will be
reprojected to. Note that this projection must have Tile Matrix Sets configured
in the Tile Matrix Set definition file.

`date_service_uri` (optional) -- If you are using dynamic layers, put the URL of
the OnEarth 2 date service here.

`tms_defs_file` (optional) -- If using a Tile Matrix Sets file different from
the one bundled with the script, you can define it here instead of using the
command line parameter.

`apache_config_location` (optional) -- Location that the main Apache
configuration files will be stored (this will need to be somewhere Apache is
configured to read when it starts up). Defaults to `/etc/httpd/conf.d`
