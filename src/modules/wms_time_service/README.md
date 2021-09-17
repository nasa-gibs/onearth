# OnEarth 2 GetCapabilities Service

This service creates a GetCapabilities/GetTileService file on the fly from the
same YAML configuration files used by other OnEarth 2 services.

## Requirements

- Lua 5.1
- luarocks
- mod_ahtse_lua
- openssl-devel
- libyaml-devel

## Installation

First make sure that the `mod_ahtse_lua` module is installed.

Next, use `luarocks` to install the OnEarth 2 GetCapabilities service module and
its dependencies:

`luarocks make onearth_gc_gts-0.1-1.rockspec`

---

### Using the service

The GetCapabilities can output each of the following types of files:

- WMTS GetCapabilities
- TWMS GetCapabilities
- TWMS GetTileService

To request a specific file, use the `request=` url parameter. Valid options are `wmtsgetcapabilities`, `twmsgetcapabilities`, and `gettileservice`.

For example, the following request would produce a WTMS GetCapabilities file:
`http://endpoint/gc_service/gc_service?request=wmtsgetcapabilities`

### The Configuration Tool

The GetCapabilities service can be fairly easily configured by hand, but a
configuration tool has been provided to make it a bit easier. For more in-depth
information about configuring the module, see the end of this document.

The syntax for running the configuration tool is:

`lua make_gc_endpoint.lua endpoint_config`

This tool requires a few different configuration files to work:

- endpoint config -- contains information about how the GC/GTS endpoint should
  be set up in Apache
- layer config(s) -- contains information about each of the layers to be
  included in the GC/GTS files.

Note that Apache must be restarted for new configurations to take effect. This
command may need to be run as `sudo` depending on the permission settings for
your Apache directories.

#### Endpoint Configuration

The endpoint configuration should be a YAML file in the following format:

```
time_service_uri: "http://localhost/time_service/time"
tms_defs_file: "/etc/onearth/config/conf/tilematrixsets.xml"
tms_limits_defs_file: "/etc/onearth/config/conf/tilematrixsetlimits.xml"
layer_config_source: "/etc/onearth/layers/layer_config.yaml"
apache_config_location: "/etc/httpd/conf.d"
base_uri_gc: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
base_uri_gts: "https://gibs.earthdata.nasa.gov/twms/epsg4326/best/"
epsg_code: "EPSG:4326"
endpoint: "/gc_service"
gc_service:
  internal_endpoint: "/var/www/html/"
  external_endpoint: "/gc"
  config_prefix: "onearth_gc_service"
  gc_header_file: "/etc/onearth/config/conf/header_gc.xml"
  gts_header_file: "/etc/onearth/config/conf/header_gts.xml"
  twms_gc_header_file: "/etc/onearth/config/conf/header_twms_gc.xml"
reproject:
  target_epsg_code: "EPSG:3857"
```

##### Configuration Options:

**Note that all file paths must be accessible to Apache!**

`time_service_uri` (optional) -- If you are using dynamic layers, put the URL of
the OnEarth 2 date service here.

`tms_defs_file` (required) -- The path to a Tile Matrix Set definition XML file.
One is included with this package (`tilematrixsets.xml`).

`tms_limits_defs_file` (optional): The path to a Tile Matrix Set Limits definition XML file.
One is included with this package (`tilematrixsetslimits.xml`).

`layer_config_source` (required) -- This can be a path either to a single layer
configuration YAML file, or a directory containing multiple layer config files.
In the case of a directory, the tool will parse all files in that directory with
a `.yaml` extension. _Note that the tool will not recurse the contents of
subdirectories if they are present._

`apache_config_location` (optional) -- Location that the main Apache
configuration files will be stored (this will need to be somewhere Apache is
configured to read when it starts up). Defaults to `/etc/httpd/conf.d`

`base_uri_gc` (required) -- The base URL to be used when forming `<ResourceURL>`
templates for each layer.

`epsg_code` (required) -- The EPSG code of the layers for this GC/GTS file.

**reproject config options (optional)**

`target_epsg_code` (optional) -- The destination EPSG code of the layers for
this GC/GTS file. To be used in conjunction with `mod_reproject`. The outgoing
GC/GTS files will contain layers that have been reprojected to the target
projection.

**gc_service config options**

`internal_endpoint` -- location on disk for the gc_service files. Must be accessible by Apache.

`external_endpoint` -- relative URI under which the GC service should be accessible. The configuration tool automatically creates "Alias" blocks.

`config_prefix` -- Filename prefix to be used for the Apache config that's generated.

`gc_header_file` (required for WMTS GC service) -- the GC service generates all the of the layer
information dynamically (basically, everything outside of `<Contents>`), but
you'll need to provide a header with everything else. An example file is
included in `conf/`

`gts_header_file` (required for TWMS GTS service) -- the GTS service generates all the of the layer
information dynamically, but you'll need to provide a header with everything
else. An example file is included in `conf/`.

`twms_gc_header_file` (required for TWMS GC service) -- the TWMS GC service generates all the of the layer information dynamically, but you'll need to provide a header with everything else. An example file is included in `conf/`.

#### Layer Configuration

The layer configurations contain all the necessary information for each layer
you intend to make accessible. They should be a YAML file in the following
format:

```
layer_id: "AMSR2_Snow_Water_Equivalent"
layer_title: "AMSR2 Snow Water Equivalent tileset"
layer_name: "Snow Water Equivalent (AMSR2, GCOM-W1)"
projection: "EPSG:4326"
tilematrixset: "EPSG4326_2km"
mime_type: "image/jpeg"
static: false
metadata:
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap", "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0", "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.0/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.2", "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.2/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.3", "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
abstract: "AMSR2 Snow Water Equivalent abstract"
```

### Configuration Options

`layer_id` (required) -- This is the layer id string that be used for WMTS/TWMS
requests.

`layer_title` (optional) -- Layer title to be used in GetTileService file.

`layer_name` (optional) -- Layer name to be used in GC/GTS.

`projection` (required) -- EPSG code of the layer projection

`static` (optional) -- Indicates whether or not the layer allows for the TIME
dimension. Defaults to 'false'.

`tilematrixset` (required) -- The name of the Tile Matrix Set to be used with
this layer. _Note that this tilematrixset name must correspond to a
tilematrixset that's defined in the endpoint configuration `tms_defs_file`_

`tilematrixset_limits_id` (optional) -- The id of the Tile Matrix Set Limits to be used with
this layer. _Note that this tilematrixsetlimitsid must correspond to a
tilematrixsetlimitsid that's defined in the endpoint configuration `tms_limits_defs_file`_

`metadata` (required) -- Metadata values to be provided for this layer. Each key
in the table will be used as an attribute name, and the value for that key will
be used as the attribute value. I.e. `{'attr': 'value'}` will appear in the XML
as `attr=value`.

`mime_type` (required) -- MIME type of the tiles in this MRF.

---

### Apache Configuration

The GetCapabilities service uses the `mod_ahtse_lua` module, which allows Lua
scripts to be run from within Apache. Refer to that module's README for more
information on how to set up that module and point it to a Lua script.

### Service Configuration

Here's a sample Lua configuration script. This file should be what the
`AHTSE_lua_Script` directive in your Apache configuration points to.

```
local onearth_gc_gts = require "onearth_gc_gts"
local config = {
    layer_config_source="config_location",
    tms_defs_file="tms_defs_location",
    tms_limits_defs_file="tms_limits_defs_location",
    gc_header_loc="gc_header_location",
    time_service_uri="time_service_uri",
    epsg_code="epsg_code",
    gts_service=true,
    gc_header_file="gc_header_file_path",
    gts_header_file="gts_header_file_path",
    twms_gc_header_file: "/etc/onearth/config/conf/header_twms_gc.xml",
    base_uri_gc="base_uri_for_gc",
    target_epsg_code="target_epsg_code"
}
handler = onearth_gc_gts.handler(config)
```
