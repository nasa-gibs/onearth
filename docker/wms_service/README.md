# OnEarth 2 WMS Service Container

This container uses Mapserver/GDAL to serve GIBS layers in WMS format. It uses
the GDAL WMS driver to create imagery from existing GIBS WMTS sources.

## Configuration tool

This container includes a basic tool to set up all the layers specified in a
particular GetCapabilities file.

The syntax is: `oe2_wms_configure.py {endpoint_config}`.

## Default container setup

The default container WMS endpoint is at `http://localhost:8083/wms/epsg4326/best/wms.cgi`. Currently, it
configures all the layers available at the
`https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/` endpoint.

Sample url:
http://localhost:8083/wms/epsg4326/best/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=MODIS_Terra_SurfaceReflectance_Bands121&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=768&BBOX=-135%2C-270%2C135%2C270&time=2012-01-01
