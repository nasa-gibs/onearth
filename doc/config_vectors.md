# OnEarth Vector Handling

OnEarth and its associated tools are capable of handling and serving vector datasets in multiple forms.

## How OnEarth serves vectors

OnEarth supports a few different ways of accessing vector data. They are as follows:

**Rasters (JPEG and PNG) (via MapServer)**

OnEarth currently uses [MapServer](http://mapserver.org) to create raster images on-the-fly from vector datasets. The `oe_configure_layer` tool can be used to configure vector layers that will be served by MapServer, as well as the styles that determine how the vector data is rendered.

Currently, OnEarth uses ESRI Shapefiles as a source data format for vector layers to be served by MapServer. The `oe_vectorgen` tool can be used to convert GeoJSON to Shapefiles.

_Note that the OnEarth layer configuration tool assumes that all source imagery is in EPSG:4326 projection._

**Mapbox Vector Tiles (MVT) (via `mod_onearth`)**

MVT tiles are a vector tile format supported by mapping clients like OpenLayers. Because they are tiled and optimized while still retaining vector data, they allow for increased performance while still providing the flexibility of client-side styling and access to the underlying metadata for each vector feature.

The OnEarth `oe_vectorgen` utility can be used to create MRF-like files that contain an entire pyramid of MVT tiles, similar to raster MRFs. These can then be configured by `oe_configure_layer` and served by the `mod_onearth` Apache module in the same way as raster layers.

**GeoJSON (via MapServer)**

OnEarth can also serve vector data in GeoJSON format, using the Web Feature Service (WFS) protocol. Similar to WMS, WFS allows vector data to be filtered by bounding box, in addition to numerous other filtering features. OnEarth uses MapServer to provide access to vector data via WFS. The `oe_configure_layer` tool is able to build and modify MapServer configurations.

Currently, OnEarth uses ESRI Shapefiles as a source data format for vector layers to be served by MapServer. The `oe_vectorgen` tool can be used to convert GeoJSON to Shapefiles.

## Installing OnEarth's vector tools

The OnEarth distribution includes the `onearth-vectorgen` RPM, which installs the `oe_vectorgen` script and its associated dependencies.

## How to use OnEarth with vectors

### Configuring vector layers with MapServer (for Rasters and WFS)

**Make sure your data is in the ESRI Shapefile format.** The `oe_vectorgen` utility can be used to convert GeoJSON to Shapefile and reproject if necessary.

**Create a layer configuration XML** and use `oe_configure_layer` to configure the new vector layer.

Note that there are two vector-specific tags you'll need to use in your layer config -- `<VectorType>` refers to the type of vector data in your source file, i,e, Polygon, Line, Point, etc. and `<VectorStyleFile>` refers to a file containing the MapServer style configuration(s) you want to use with this layer. Refer to the MapServer [STYLE reference](http://mapserver.org/mapfile/style.html) for more information.

_Note that Points need to be represented by a global SYMBOL object within the MapServer config. You'll want to add this to the MapServer header files (refer to the `oe_configure_layer` docs. For more information refer to the MapServer [SYMBOL reference](http://mapserver.org/mapfile/symbol.html)._

### Configuring vector layers with `mod_onearth` (for MVT)

**Make sure your input data is in ESRI Shapefile or GeoJSON format.**

**Use the `oe_vectorgen` utility to create a MVT MRF** You'll need to create a `oe_vectorgen` configuration file that specifies the desired projection, the desired TileMatrixSet, and desired feature decimation parameters (if any).

**Configure the new layer using `oe_configure_layer`** Just like with raster layers, create a layer configuration XML. Make sure to specify 'MVT' in the `<Compression>` tag.

### Requesting vector tiles from `mod_onearth`

**Vector tiles may be requested from OnEarth via WMTS or Tiled WMS.** The following MIME type is supported as a `format` option: `application/vnd.mapbox-vector-tile`

For WMTS REST requests, use `mvt` as the file extension.

Vector tiles are returned compressed with `gzip` encoding.

## Supported geometry types

Common geometry types such as points, lines, and polygons are supported.

**MVT-MRF**

GeoJSON input

-   Point
-   LineString
-   Polygon

Shapefile input

-   Point
-   Polyline
-   Polygon

**Shapefile**

GeoJSON input

-   GeometryCollection is NOT supported.

Shapefile input

-   All Shapefile geometries supported by MapServer.

Note: OnEarth does not serve from GeoJSON files; they must be converted to MVT-MRF or Shapefile.
