# OnEarth 2 WMS Time Service

This service passes through all requests to mapserver, except "getmap" requests should append
each layer's <layer_name>_PREFIX and <layer_name>_SHAPEFILE variables to URL 
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

`luarocks make onearth_wms_time-0.1-1.rockspec`

---

### Using the service

Access any normal wms URI and it gets forwarded to the wms_time_service.  Once there the service will redirect to
a mapserver URL.  If the request is getmap then it will append the PREFIX and SHAPEFILE variables for each input layer.

e.g. 1:
   Accessing: http://localhost/wms/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities
   Redirects to:  http://localhost/mapserver/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities

e.g. 2:
   Accessing: http://localhost/wms/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=768&BBOX=-90%2C-180%2C90%2C180&time=2019-02-10
   Redirects to:  
   http://localhost/mapserver/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=768&BBOX=-90%2C-180%2C90%2C180&time=2019-02-10&MODIS_Terra_CorrectedReflectance_TrueColor_PREFIX=MODIS_Terra_CorrectedReflectance_TrueColor_Day%2F2011%2F&MODIS_Terra_CorrectedReflectance_TrueColor_SHAPEFILE=MODIS_Terra_CorrectedReflectance_TrueColor_Day-2011244000000

### The Configuration Tool

The WMS Time service can be fairly easily configured by hand, but a
configuration tool has been provided to make it a bit easier. For more in-depth
information about configuring the module, see the end of this document.

The syntax for running the configuration tool is:

`lua make_wms_time_endpoint.lua endpoint_config`

This tool requires a few different configuration files to work:

- endpoint config -- contains information about how the WMS Time endpoint should
  be set up in Apache
- layer config(s) -- contains information about each of the layers to be
  included in the WMS Time files.

Note that Apache must be restarted for new configurations to take effect. This
command may need to be run as `sudo` depending on the permission settings for
your Apache directories.

#### Endpoint Configuration

The endpoint configuration should be a YAML file in the following format:

```
time_service_uri: "http://localhost/time_service/time"
layer_config_source: "/etc/onearth/layers/layer_config.yaml"
apache_config_location: "/etc/httpd/conf.d"
mapserver:
  redirect_endpoint: "/var/www/html/mapserver/epsg3857/std"
  external_endpoint: "/wms/epsg3857/std"
  internal_endpoint: "/var/www/html/wms/epsg3857/std"
  config_prefix: "epsg3857_std_wms_time_service"
  ...
```

##### Configuration Options:

**Note that all file paths must be accessible to Apache!**

`time_service_uri` (required) -- If you are using dynamic layers, put the URL of
the OnEarth 2 date service here.

`layer_config_source` (required) -- This can be a path either to a single layer
configuration YAML file, or a directory containing multiple layer config files.
In the case of a directory, the tool will parse all files in that directory with
a `.yaml` extension. _Note that the tool will not recurse the contents of
subdirectories if they are present._

`apache_config_location` (optional) -- Location that the main Apache
configuration files will be stored (this will need to be somewhere Apache is
configured to read when it starts up). Defaults to `/etc/httpd/conf.d`

**mapserver config options**

`redirect_endpoint` -- location on disk for the mapserver files. Must be accessible by Apache.

`internal_endpoint` -- location on disk for the endpoint config for Apache.

`external_endpoint` -- relative URI under which the wms time service should be accessible.

`config_prefix` -- Filename prefix to be used for the WMS Time service Apache config that's generated.

### Apache Configuration

The WMS Time service uses the `mod_ahtse_lua` module, which allows Lua
scripts to be run from within Apache. Refer to that module's README for more
information on how to set up that module and point it to a Lua script.

### Service Configuration

Here's a sample Lua configuration script. This file should be what the
`AHTSE_lua_Script` directive in your Apache configuration points to.

```
local onearth_wms_time = require "onearth_wms_time"
local config = {
    layer_config_source="config_location",
    time_service_uri="time_service_uri",
    time_service_keys="time_service_keys"
}
handler = onearth_wms_time.handler(config)
```
