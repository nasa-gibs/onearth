# OnEarth Configuration

This documentation will go through the steps needed to configure an OnEarth container to serve visualization products.


## Containers
The following Containers are deployed to provide OnEarth services within a deployment.

1. onearth-tile-services: Image containing OnEarth services for WMTS (KVP GetMap / REST z/y/x tile) and TWMS (KVP GetTile)
2. onearth-time-service: Image containing the OnEarth Time Service
3. onearth-reproject: Image containing OnEarth Reproject Service
4. onearth-wms: Image containing OnEarth WMS and MapServer
5. onearth-capabilities: Image containing OnEarth WMTS/TWMS GetCapabilities/GetTileService services


## Configuration File Locations
The following configuration files are to be placed in the specified location within a container, when required for an OnEarth service.

1. OnEarth YAML Endpoint Configuration
    * Contains information about how endpoints should be set up in Apache
    * Default location: `/etc/onearth/config/endpoint/`
2. OnEarth YAML Layer Configuration
    * Contains information about how each of the layers will be configured 
    * Default location: `/etc/onearth/config/layers/`
3. TileMatrixSets Definitions
    * Contains definitions for WMTS tile matrix sets used in GetCapabilities
    * Default location: `/etc/onearth/config/conf/tilematrixsets.xml`
4. GetCapabilities Header
    * The common XML GetCapabilities "header" to be used for each endpoint
    * Default location: `/etc/onearth/config/conf/`
5. GetTileService Header (for Tiled WMS only)
    * The common XML GetTileService "header" to be used for each endpoint
    * Default location: `/etc/onearth/config/conf/`
6. Colormap XML Files
    * The colormap XML file used for each layer
    * Default location: `/etc/onearth/colormaps/`
7. Legend Images
    * Static legend images used for each layer
    * Default location: `/etc/onearth/legends/`
8. Empty Tile Images
    * Static empty tile images used for each layer when no data is available
    * Default location: `/etc/onearth/empty_tiles/`
9. Mapfile Header (for WMS only)
    * The common mapfile "header" used for all layers in the endpoint
    * Default location: `/etc/onearth/config/mapserver/`
10. Mapfile Style Sheets (for WMS only)
    * Styles for Shapefile datasets used by MapServer
    * Not yet implemented in OnEarth v2.x
11. Vector Style Sheets (for Vectors only)
    * Reference JSON styles to be used by map clients for vector layers
    * Not yet implemented in OnEarth v2.x
    
## Container Configuration Variables

OnEarth Docker containers accept the following environment variables. Use the `--env`, `-e` or `--env-file` options when starting the container with Docker. Amazon ECS also supports environment variables.

### onearth-capabilities
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)

### onearth-reproject
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)

### onearth-tile-services
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* IDX_SYNC: `true/false` (defaults `false`) whether to sync IDX files on local disk with those found in the S3 URL
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)

### onearth-time-service
* S3_URL: HTTP URL to the public S3 bucket containing MRFs
    (e.g., http://gitc-test-imagery.s3.amazonaws.com)
* REDIS_HOST: Redis endpoint URL
    (e.g., gitc.0001.use1.cache.amazonaws.com)
* DEBUG_LOGGING: `true/false` (defaults `false`) whether to use DEBUG level logging for Apache HTTPD

### onearth-wms
* S3_CONFIGS: S3 bucket name used for configuration files (e.g., gitc-onearth-configs)

## Loading Configurations from S3

Configuration files for the `onearth-capabilities`, `onearth-reproject`, `onearth-tile-services`, and `onearth-wms` containers can be pulled down from an S3 bucket instead of from a file system mount. The containers are automatically configured to copy files from the bucket specified in the `S3_CONFIGS` environment variable if it is used.

The S3 bucket must be configured in the following manner (replace {s3-configs} with your S3 bucket name):

```
{s3-configs}/colormaps/ (optional)
  {s3-configs}/colormaps/v1.3/
{s3-configs}/config/
  {s3-configs}/config/conf/
  {s3-configs}/config/endpoint/
  {s3-configs}/config/layers/
  {s3-configs}/config/mapserver/
{s3-configs}/empty-tiles/
{s3-configs}/legends/ (optional)
```
Files found in these locations will be copied from `{s3-configs}` to `/etc/onearth/` within the appropriate containers.


## OnEarth YAML Endpoint Configuration

The Endpoint Configuration is used by multiple OnEarth tools. See documentation for each specific tool for more information:

* [GetCapabilities Service](../src/modules/gc_service/README.md)
* [WMS Time Service](../src/modules/wms_time_service/README.md)
* [Time Service](../src/modules/time_service/README.md)
* [WMS Service](../docker/wms_service/README.md)
* [WMTS/TWMS Services](../src/modules/mod_wmts_wrapper/configure_tool/README.md)

Configurations:

* **apache_config_location**: The output location of Apache HTTPD configurations
* **base_uri_gc**: The base URI of the endpoint for WMTS GetCapabilities layers
* **base_uri_gts**: The base URI of the endpoint for TWMS GetCapabilities/GetTileService layers
* **base_uri_meta**: The base URI of the endpoint for metadata files (e.g. colormaps, legends, styles) layers
* **epsg_code**: The EPSG code of the map projection of the layers (e.g. EPSG:4326)
* **gc_service_uri**: The URI of the WMTS GetCapabilities endpoint
* **layer_config_source**: Directory location of the layer configuration files
* **time_service_keys**: Array of keys to be used with the Time
Service; keys will be positioned in the order configured
* **time_service_uri**: The URI of the Time Service endpoint
* **tms_defs_file**: The location of the Tile Matrix Sets definition XML file
* **gc_service**: Configurations specific only to GetCapabilities Service
  * **config_prefix**: Filename prefix to be used for the Apache config that is generated
  * **internal_endpoint**: Location on disk where all the configuration files for the WMTS layers should be stored
  * **external_endpoint**: Relative URL that the endpoint should appear; the configuration tool will automatically build `Alias` configurations
  * **gc_header_file**: The location of the WMTS GetCapabilities header XML file
  * **gts_header_file**: The location of the TWMS GetTileService header XML file
  * **twms_gc_header_file**: The location of the TWMS GetCapabilities header XML file
* **wmts_service**: Configurations specific only to WMTS Service
  * **config_prefix**: Filename prefix to be used for the Apache config that is generated
  * **internal_endpoint**: Location on disk where all the configuration files for the WMTS layers should be stored
  * **external_endpoint**: Relative URL that the endpoint should appear; the configuration tool will automatically build `Alias` configurations
* **twms_service**: Configurations specific only to TWMS Service
  * **internal_endpoint**: Location on disk where all the configuration files for the WMTS layers should be stored
  * **external_endpoint**: Relative URL that the endpoint should appear; the configuration tool will automatically build `Alias` configurations
* **mapserver**: Configurations specific only to WMS Service (i.e., MapServer)
  * **redirect_endpoint**: The internal directory within the container for Apache HTTPD for mapserver
  * **internal_endpoint**: The internal directory within the container for Apache HTTPD
  * **config_prefix**: Filename prefix to be used for the WMS Time service Apache config that's generated.
  * **mapfile_header**: The common mapfile "header" used for all layers in the endpoint
  * **mapfile_location**: The output location of the mapfile.
  * **source_wmts_gc_uri**: The source WMTS GetCapabilities that is used to as the basis for WMS layers
  * **replace_with_local**: Replace matching host names with local Docker host IP 172.17.0.1 so that connections stay local
* **reproject**: Configurations specific only to reproject (i.e., mod_reproject)
  * **target_epsg_code**: If a reproject endpoint, this is the target projection that source imagery will be reprojected to
  * **source_gc_uri**: If a reproject endpoint, this is the URI of the source WMTS GetCapabilities endpoint
  * **replace_with_local**: Replace matching host names with local Docker host IP 172.17.0.1 so that connections stay local

Sample endpoint configuration:
```
apache_config_location: "/etc/httpd/conf.d/"
base_uri_gc: "http://localhost/wmts/epsg3857/best"
base_uri_gts: "http://localhost/twms/epsg3857/best"
base_uri_meta: "https://gibs.earthdata.nasa.gov"
epsg_code: "EPSG:4326"
gc_service_uri: "http://onearth-capabilities/wmts/epsg3857/best/gc"
layer_config_source: "/etc/onearth/config/layers/epsg4326/best/"
time_service_keys: ["epsg3857", "best"]
time_service_uri: "http://onearth-time-service/time_service/time"
tms_defs_file: "/etc/onearth/config/conf/tilematrixsets.xml"
gc_service:
  config_prefix: "epsg3857_best_gc_service"
  internal_endpoint: "/var/www/html/wmts/epsg3857/best"
  external_endpoint: "/wmts/epsg3857/best/gc"
  gc_header_file: "/etc/onearth/config/conf/epsg3857_best_header_gc.xml"
  gts_header_file: "/etc/onearth/config/conf/epsg3857_best_header_gts.xml"
  twms_gc_header_file: "/etc/onearth/config/conf/epsg3857_best_header_twms_gc.xml"
wmts_service:
  config_prefix: "epsg3857_best"
  internal_endpoint: "/var/www/html/wmts/epsg3857/best"
  external_endpoint: "/wmts/epsg3857/best"
twms_service:
  internal_endpoint: "/var/www/html/twms/epsg3857/best"
  external_endpoint: "/twms/epsg3857/best"
mapserver:
  redirect_endpoint: "/var/www/html/mapserver/epsg3857/best"
  external_endpoint: "/wms/epsg3857/best"
  internal_endpoint: "/var/www/html/wms/epsg3857/best"
  config_prefix: "epsg3857_best_wms_time_service"
  mapfile_header:  "/etc/onearth/config/mapserver/epsg3857.header"
  mapfile_location: "/etc/onearth/config/mapserver/epsg3857_best.map"
  source_wmts_gc_uri: "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml"
reproject:
  source_gc_uri: "http://localhost/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"
  target_epsg_code: "EPSG:3857"
  replace_with_local: "http://localhost"
```
See [docker/sample_configs/endpoint](../docker/sample_configs/endpoint) for more samples.


## OnEarth YAML Layer Configuration

### Common Layer Configurations

```
layer_id: "A unique identifier within an endpoint for the layer"
layer_title: "Layer title text -- not identifier"
tilematrixset: "TileMatrixSet identifier"
mime_type: "Outgoing MIME type for tiles and type used in GetCapabilities"
static: "Boolean indicating if layer has a TIME dimension"
projection: "EPSG:CODE"
alias: "Replace the user facing Layer ID with this name"
```

### Required for GetCapabilities/GetTileService
```
metadata: 
    - {
       "xlink:type": "simple", 
       "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap", 
       "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/layer_name.xml", 
       "xlink:title": "GIBS Color Map: Data - RGB Mapping"
      }
layer_name: "layer name for GTS"
abstract: "GTS abstract"
```

### Required for WMTS/TWMS
```
source_mrf: 
  size_x: "Base resolution of source MRF in pixels (x dimension)"
  size_y: "Base resolution of source MRF in pixels (y dimension)"
  bands: "Number of bands in source image file"
  tile_size_x: "Tile size in pixels (x dimension)"
  tile_size_y: "Tile size in pixels (y dimension)"
  idx_path: "Directory path to the IDX file. This can be relative to the root of where all the IDX files are stored."
  data_file_uri: "Base URI to the data file, relative from the root of the S3 bucket. (e.g. http://gibs_s3_bucket/epsg4326/MODIS­_Aqua­_Layer_ID/)"
  static: "Boolean, whether or not this layer includes a TIME dimension"
  bbox: "The geographic bounding box of the layer"
  empty_tile: "The empty tile to use for the layer"
  year_dir: "true/false" whether this layer contains a year subdirectory"
```
### Optional for WMTS/TWMS
```
Currently mod_convert need two layers to be setup. One will serve the source ZENJPEGS similar to a normal jpeg, while the second will convert the ZENJPEG. The second will have the following an extra config pointing to the first layer. 
convert_mrf: 
  convert_source: "layer_id and format (ie: GOES-East_ABI_Air_Mass_v0_NRT .jpeg) of the source zenjpeg. 
  
  This layer_id (convert_src_name) and format is used to generate the Convert_Source {external_endpoint}/{convert_src_name}/default/${{date}}/{tilematrixset}/ {format} for mod_convert configs. 

A best layer is made up of one virtual layer(best layer). The one best layer is mapped to many actual layers. 
On the config for the best layer there will be a:
best_config: lists the various layers and their priority(higher score, higher priority). 

On the config of each of actual layers that make up the best layer, there will be a: 
best_layer: which points to the virtual best layer(the presenese of this config will generate a best_layer key in redis). 
The presense of a best_layer key tells ingest and and oe-redis-update that this layer is a used by a best layer, and to call best.lua to update the virtual layer. Sample configs are show below.
```
### Optional for Time Service
```
time_config: Custom time period configuration for layer
best_config: Custom best available configuration for layer as a key value list of Z-score (higher number means higher priority) : Filename Prefix
best_layer: For a "non-best" layer (e.g., STD, NRT), this is the associated "best available" layer
```

See [doc/time_detection.md](time_detection.md) for time period configuration information.

See [src/modules/mod_wmts_wrapper/configure_tool/](../src/modules/mod_wmts_wrapper/configure_tool/README.md) for more details.

### Sample Layer Configurations
```
layer_id: "MODIS_Aqua_Brightness_Temp_Band31_Day"
layer_title: "Brightness Temperature (Band31, Day, v6, Standard, MODIS, Aqua)"
layer_name: "MODIS_Aqua_Brightness_Temp_Band31_Day tileset"
projection: "EPSG:4326"
tilematrixset: "1km"
mime_type: "image/jpeg"
static: false
abstract: "MODIS_Aqua_Brightness_Temp_Band31_Day abstract"
cache_expiration: 1500
time_config:
  - "2000-01-01/2009-12-31/P1D"
  - "2011-01-01/2017-06-04/P1D"
  - "2017-06-20/DETECT/P1D"
best_config:
  1: "MODIS_Aqua_Brightness_Temp_Band31_Day_v5_NRT"
  2: "MODIS_Aqua_Brightness_Temp_Band31_Day_v5_STD"
  3: "MODIS_Aqua_Brightness_Temp_Band31_Day_v6_NRT"
  4: "MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD"
metadata:
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap", "xlink:href": "{base_uri_meta}/colormaps/v1.3/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0", "xlink:href": "{base_uri_meta}/colormaps/v1.0/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.3", "xlink:href": "{base_uri_meta}/colormaps/v1.3/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
source_mrf:
  size_x: 40960
  size_y: 20480
  bands: 4
  tile_size_x: 512
  tile_size_y: 512
  idx_path: "/onearth/idx/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Day/"
  data_file_uri: "{S3_URL}/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Day/"
  year_dir: true
  bbox: -180,-90,180,90
  empty_tile: "/etc/onearth/empty_tiles/Blank_RGBA_512.png"
```
```
layer_id: "MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD"
layer_title: "Brightness Temperature (Band31, Day, v6, Standard, MODIS, Aqua)"
layer_name: "MODIS_Aqua_Brightness_Temp_Band31_Day tileset"
projection: "EPSG:4326"
tilematrixset: "1km"
mime_type: "image/png"
static: false
abstract: "MODIS_Aqua_Brightness_Temp_Band31_Day abstract"
time_config:
  - "DETECT/DETECT/P1D"
best_layer: "MODIS_Aqua_Brightness_Temp_Band31_Day"
metadata:
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap", "xlink:href": "{base_uri_meta}/colormaps/v1.3/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0", "xlink:href": "{base_uri_meta}/colormaps/v1.0/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.2", "xlink:href": "{base_uri_meta}/colormaps/v1.2/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
  - {"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.3", "xlink:href": "{base_uri_meta}/colormaps/v1.3/MODIS_Aqua_Brightness_Temp_Band31_Day.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}
source_mrf:
  size_x: 40960
  size_y: 20480
  bands: 1
  tile_size_x: 512
  tile_size_y: 512
  idx_path: "/onearth/idx/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/"
  data_file_uri: "{S3_URL}/epsg4326/MODIS_Aqua_Brightness_Temp_Band31_Day_v6_STD/"
  year_dir: true
  bbox: -180,-90,180,90
  empty_tile: "/etc/onearth/empty_tiles/Blank_RGBA_512.png"
```
See [docker/sample_configs/layers](../docker/sample_configs/layers) for more samples.
