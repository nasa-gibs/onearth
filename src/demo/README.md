# OnEarth Demo

The OnEarth Demo or "Tile Client" includes the following:

WMTS Tile Clients that show off sample data, profiling imagery (for performance profiling), and reprojected profiling imagery.

WMTS Tile Clients for each projection (4326, 3857, 3413, 3031) that pulls imagery from S3.

Sample requests for WMTS GetCapabilities, TWMS GetTileService, and TWMS GetCapabilities.

The Tile Client automatically reads the GetCapabilities at its end point and loads all available layers. It also includes a time picker to change the time for the layer. The demo is available by default at http://localhost/demo/