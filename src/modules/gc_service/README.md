# OnEarth 2 GetCapabilities Service

This service creates a GetCapabilities/GetTileService file on the fly from the
same YAML configuration files used by other OnEarth 2 services.

## Requirements

* Lua 5.1
* luarocks
* mod_ahtse_lua

## Installation

First make sure that the `mod_ahtse_lua` module is installed.

Next, use `luarocks` to install the OnEarth 2 GetCapabilities service module and
its dependencies:

`luarocks make onearth_gc_gts-0.1-1`

---

### The Configuration Tool

The GetCapabilities service can be fairly easily configured by hand, but a
configuration tool has been provided to make it a bit easier. For more in-depth
information about configuring the module, see the end of this document.

The syntax for running the configuration tool is:

`lua make_gc_endpoint.lua endpoint_config {--no_gc, --make_gts}`

This tool requires a few different configuration files to work:

* endpoint config -- contains information about how the GC/GTS endpoint should
  be set up in Apache
* layer config(s) -- contains information about each of the layers to be
  included in the GC/GTS files.

Note that Apache must be restarted for new configurations to take effect. This
command may need to be run as `sudo` depending on the permission settings for
your Apache directories.

##### Options

`--no_gc` -- Don't configure the GetCapabilities service

`--make_gc` -- Configure the GetTileService service (off by default)

#### Endpoint Configuration

The endpoint configuration should be a YAML file in the following format:

```
date_service_uri: "http://137.79.29.45:8090/date"
tms_defs_file: "/etc/onearth/tilematrixsets.xml"
gc_header_file: "/etc/onearth/headers/header_gc.xml"
gts_header_file: "/etc/onearth/headers/header_gts.xml"
layer_config_source: "/tmp/layer_config.yaml"
apache_config_location: "/etc/httpd/conf.d/gc.conf"
endpoint_config_base_location: "/var/www/html"
base_uri_gc: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
epsg_code: "EPSG:4326"
target_epsg_code: "EPSG:3857"
gc_endpoint: "/gc"
gts_endpoint: "/gts"
```

##### Configuration Options:

**Note that all file paths must be accessible to Apache!**

`date_service_uri` (optional) -- If you are using dynamic layers, put the URL of
the OnEarth 2 date service here.

`tms_defs_file` (required) -- The path to a Tile Matrix Set definition XML file.
One is included with this package (`tilematrixsets.xml`).

`gc_header_file` (required) -- the GC service generates all the of the layer
information dynamically (basically, everything outside of `<Contents>`), but
you'll need to provide a header with everything else. An example file is
included in `endpoint_stuff/`

`gts_header_file` (required) -- the GTS service generates all the of the layer
information dynamically, but you'll need to provide a header with everything
else. An example file is included in `endpoint_stuff/`.

`layer_config_source` (required) -- This can be a path either to a single layer
configuration YAML file, or a directory containing multiple layer config files.
In the case of a directory, the tool will parse all files in that directory with
a `.yaml` extension. _Note that the tool will not recurse the contents of
subdirectories if they are present._

`apache_config_location` (optional) -- Location that the main Apache
configuration files will be stored (this will need to be somewhere Apache is
configured to read when it starts up). Defaults to `/etc/httpd/conf.d`

`endpoint_config_base_location` (required) -- This is the path on disk where the
configuration files should be stored _for this endpoint_. This needs to be a
publicly-accessible path on the web server, such as `/var/www/wmts/gc_service`,
etc. _Each endpoint should have its own unique path!_

`base_uri_gc` (required) -- The base URL to be used when forming `<ResourceURL>`
templates for each layer.

`epsg_code` (required) -- The EPSG code of the layers for this GC/GTS file.

`target_epsg_code` (optional) -- The destination EPSG code of the layers for
this GC/GTS file. To be used in conjunction with `mod_reproject`. The outgoing
GC/GTS files will contain layers that have been reprojected to the target
projection.

`gc_endpoint` (required for GetCapabilities service) -- The location beneath the
base endpoint where the GC service should be available.

`gts_endpoint` (required for GetTileService service) -- The location beneath the
base endpoint where the GTS service should be available.

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
    gc_header_loc="gc_header_location",
    date_service_uri="date_service_uri",
    epsg_code="epsg_code",
    gts_service=true,
    gc_header_file="gc_header_file_path",
    gts_header_file="gts_header_file_path",
    base_uri_gc="base_uri_for_gc",
    target_epsg_code="target_epsg_code"
}
handler = onearth_gc_gts.handler(config)
```
