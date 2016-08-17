# oe_create_mvt_mrf -- Convert Shapefiles to GeoJSON and MVT tile MRFs.

## Dependencies
- GDAL (ogr2ogr)
- Tippecanoe (https://github.com/mapbox/tippecanoe)

## Installation

#### Install GDAL
GDAL's `ogr2ogr` program is needed to convert shapefiles to GeoJSON.

#### Install Tippecanoe
Tippecanoe converts GeoJSON files to Vector Tiles. It performs decimation as well.

1. Clone the Tippecanoe repo:
`git clone https://github.com/mapbox/tippecanoe.git`

2. Make and install Tippecanoe:
`make && make install`

## Making MVT MRFs

### From the Command Line:
`perry.py [options] INPUT_SHAPEFILE OUTPUT_FILE_PREFIX`

Use `-h` for information on additional options.

The script detects whether the input file is a GeoJSON or Shapefile based on its extension.
 
### From another Python script
You can also directly use the functions in this script in your own scripts. There are only two functions (GeoJSON -> MRF and Shapefile -> MRF) and they are extensively documented within the script itself. 