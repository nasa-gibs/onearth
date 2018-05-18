# OnEarth Configuration

This documentation will go through the steps needed to configure OnEarth with imagery layers.

## Configurations Used

1. OnEarth YAML Endpoint Configuration Files
	* An OnEarth YAML endpoint configuration file exists for every desired endpoint. Default location:

1. OnEarth YAML Layer Configuration Files
	* OnEarth YAML layer configuration files exist for active layers. Default location:

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

```
date_service_uri: "" (mod_wmts, mod_twms, gc_service)
tms_defs_file: "/etc/onearth/tilematrixsets.xml" (gc_service)
gc_header_file: "/etc/onearth/headers/header_gc_best_4326.xml" (gc_service)
gts_header_file: "/etc/onearth/headers/header_gts_best_4326.xml" (gc_service)
layer_config_source: "" (mod_wmts, mod_twms, gc_service)
apache_config_location: "" (mod_wmts, mod_twms, gc_service)
endpoint_config_base_location: "/var/www/html" (mod_wmts, mod_twms, gc_service)
base_uri_gc: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/" (gc_service)
base_uri_gts: "https://gibs.earthdata.nasa.gov/twms/epsg4326/best/" (gc_service)
epsg_code: "EPSG:4326" (gc_service)
gc_endpoint: "/gc" (gc_service)
gts_endpoint: "/gts" (gc_service)
target_epsg_code: (gc_service)
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
 
 