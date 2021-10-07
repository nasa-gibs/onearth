# OnEarth 2 WMS Service

This container uses Mapserver to provide WMS access to visualization layers available through WMTS endpoints separately configured and deployed.  Specifically, Mapserver utilizes the GDAL WMS driver with WMTS sources.

## Configuration Tool

This container includes a basic tool to configure a WMS service endpoint.  The inputs to the configuration tool are found in an OnEarth endpoint configuration file.  

The syntax for the configuration tool is: `oe2_wms_configure.py {endpoint_config}`

### Endpoint Configuration
The following entries are found in the `mapserver` section of the endpoint configuration file and are used by the configuration tool.

* **redirect_endpoint**: The internal directory within the container for mapserver
* **internal_endpoint**: The internal directory within the container for Apache HTTPD
* **external_endpoint**: The relative URI under which the mapserver should be accessible.
* **config_prefix**: The filename prefix to be used for the Apache config that's generated for WMS layers.
* **mapfile_header**: The common mapfile "header" used for all layers in the endpoint
* **mapfile_location**: The output location of the mapfile within the container
* **source_wmts_gc_uri**: The source WMTS GetCapabilities that is used to as the basis for WMS layers
* **replace_with_local**: Replace this part of the source pattern with the Docker host so that connections stay local

"epsg_code" is required as a top-level endpoint configuration item.

* **epsg_code**: The EPSG code associated with the map projection for the endpoint (e.g. EPSG:4326)

Example:
```
mapserver:
  redirect_endpoint: "/var/www/html/mapserver/epsg4326/best"
  external_endpoint: "/wms/epsg4326/best"
  internal_endpoint: "/var/www/html/wms/epsg4326/best"
  config_prefix: "epsg4326_best_wms_time_service"
  mapfile_header:  "/etc/onearth/config/mapserver/epsg4326.header"
  mapfile_location: "/etc/onearth/config/mapserver/epsg4326_best.map"
  source_wmts_gc_uri: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"
epsg_code: "EPSG:4326"
 ```
See [OnEarth Configuration](../../doc/configuration.md) for more information about OnEarth configuration files.

## Default Container Setup

The default container WMS endpoint is at `http://localhost:8083/wms/epsg4326/best/wms.cgi`. Currently, it
configures all the layers available at the
`https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/` endpoint, which is the sample value provided in the repo.

Sample url:
http://localhost:8083/wms/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=MODIS_Terra_SurfaceReflectance_Bands121&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=768&BBOX=-90%2C-180%2C90%2C180&time=2019-09-01
