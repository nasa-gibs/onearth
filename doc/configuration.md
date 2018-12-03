# OnEarth Configuration

This documentation will go through the steps needed to configure OnEarth with imagery layers.

## Configurations Used

1. OnEarth YAML Endpoint Configuration Files
	* An OnEarth YAML endpoint configuration file exists for every desired endpoint. Default location: `/etc/onearth/config/endpoint/`

1. OnEarth YAML Layer Configuration Files
	* OnEarth YAML layer configuration files exist for active layers. Default location: `/etc/onearth/config/layers/`

1. TileMatrixSets config

1. GetCapabilities Header

1. GetTileService Header (for Tiled WMS only)

1. Colormap XML Files

1. Legend Images

1. Empty Tile Images

1. Vector Style Sheets (for Vectors only)

1. Mapfile Style Sheets (for WMS only)

1. Mapfile Header/Footer (for WMS only)


## OnEarth YAML Endpoint Configuration

The Endpoint Configuration is used by multiple OnEarth tools. See documentation for each specific tool for more information:

* [mod_wmts_wrapper configure tools](../src/modules/mod_wmts_wrapper/configure_tool/README.md)
* [gc_service](../src/modules/gc_service/README.md)

Sample configuration:
```
time_service_uri: "http://onearth-time-service/time_service/time"
time_service_keys: ["epsg3857", "best"]
gc_service_uri: "/wmts/epsg3857/best/gc"
tms_defs_file: "/etc/onearth/config/conf/tilematrixsets.xml"
layer_config_source: "/etc/onearth/config/layers/epsg4326/"
apache_config_location: "/etc/httpd/conf.d/"
base_uri_gc: "http://localhost/wmts/epsg3857/best/"
base_uri_gts: "http://localhost/twms/epsg3857/best/"
epsg_code: "EPSG:4326"
target_epsg_code: "EPSG:3857" # For mod_reproject only
source_gc_uri: "http://localhost/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml" # For mod_reproject only
gc_service:
  internal_endpoint: "/var/www/html/wmts/epsg3857/best"
  external_endpoint: "/wmts/epsg3857/best/gc"
  config_prefix: "epsg3857_best_gc_service"
  gc_header_file: "/etc/onearth/config/conf/header_gc.xml"
  gts_header_file: "/etc/onearth/config/conf/header_gts.xml"
  twms_gc_header_file: "/etc/onearth/config/conf/header_twms_gc.xml"
wmts_service:
  internal_endpoint: "/var/www/html/wmts/epsg3857/best"
  external_endpoint: "/wmts/epsg3857/best"
  config_prefix: "epsg3857_best"
twms_service:
  internal_endpoint: "/var/www/html/twms/epsg3857/best"
  external_endpoint: "/twms/epsg3857/best"
```


## OnEarth YAML Layer Configuration

### WMTS/TWMS

```
Layer_id: ""
layer_title: “Layer title text -- not identifier”
projection: "EPSG:code"
tilematrixset: “tilematrixset identifier”
mime_type: “outgoing MIME type for tiles and type used in GetCapabilities”
static: “boolean indicating if layer has a TIME dimension”
projection: "EPSG:CODE"
```

-- REQUIRED ONLY BY GC/GTS SERVICE
```
metadata: 
    - {
       "xlink:type": "simple", 
       "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap", 
       "xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/layer_name.xml", 
       "xlink:title": "GIBS Color Map: Data - RGB Mapping"
      }
layer_name: “layer name for GTS”
abstract: "GTS abstract"
```

-- REQUIRED ONLY BY MOD\_WMTS/MOD\_TWMS
```
source_mrf: 
  size_x: "Base resolution of source MRF in pixels"
  size_y: "''"
  bands: "Number of bands in source image file"
  tile_size_x: "Tile size in pixels"
  tile_size_y: "''"
  idx_path: "Path to the IDX file. This can probably be relative to the root of where we store all the IDX files."
  base_data_file_uri: "Base URI to the data file, relative from the root of the S3 bucket.  (e.g. http://gibs_s3_bucket/epsg4326/MODIS­_Aqua­_Layer_ID/)"
  static: "Boolean, whether or not this layer includes a TIME dimension"
  empty_tile: "The empty tile to use for the layer"
```

### WMS

```
apache_config_location: "/etc/httpd/conf.d/gc.conf"
endpoint_config_base_location: "/var/www/html"
gts_header_file: "/.../header_gts.xml"
base_uri_gc: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/"
base_uri_gts: "https://gibs.earthdata.nasa.gov/twms/epsg4326/best/"
```
 
 