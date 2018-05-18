# OnEarth Vector Handling

Vector support is being revised in OnEarth 2.x. Please use OnEarth versions 1.x for vector support.

## Supported geometry types
Common geometry types such as points, lines, and polygons are supported.

**MVT-MRF**

GeoJSON input

* Point
* LineString
* Polygon

Shapefile input

* Point
* Polyline
* Polygon

**Shapefile**

GeoJSON input

* GeometryCollection is NOT supported.

Shapefile input

* All Shapefile geometries supported by MapServer.

Note: OnEarth does not serve from GeoJSON files; they must be converted to MVT-MRF or Shapefile.


