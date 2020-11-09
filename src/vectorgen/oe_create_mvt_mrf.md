# oe_create_mvt_mrf -- Convert Shapefiles to GeoJSON and MVT tile MRFs.

## Dependencies
- libxml2
- libxslt
- libspatialindex 
- Python dependencies listed in requirements.txt

## Installation

#### Install libspatialindex, libxslt, and libxml2

*Note that this software requires libspatialindex v1.7 or higher. If installing in CentOS6, for example, you'll need to install from source: https://libspatialindex.github.io/.*

`yum install spatialindex-devel libxml2-devel libxslt-devel`

#### Install Python dependencies with pip
`pip3 install -r requirements.txt`

## Making MVT MRFs

### From the Command Line:
`oe_create_mvt_mrf.py [options] INPUT_SHAPEFILE TILEMATRIXSET`

Use `-h` for information on additional options.

### From another Python script
This script has one main function (create_vector_mrf) that can be used in other scripts. Check the source for implementation details.