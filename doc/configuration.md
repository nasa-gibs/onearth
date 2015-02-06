# OnEarth Configuration

## Apache

Dependent RPMs: 
* onearth

Steps:
* [Configure Apache](config_apache.md)
* [Configure Endpoint](config_endpoint.md)

## Imagery Layers

Dependent RPMs: 
* gibs-gdal
* onearth-config

Steps:
* Generate MRF metadata file
* Generate Empty Tile (Optional) 
* Generate Legend Images (Optional) 
* Generate ColorMap 
* Update/Create OnEarth [Layer Configuration](config_layer.md) file 
* Update/Create OnEarth [Support Configuration](config_support.md) files 
* Execute layer configuration tool  
* Restart Apache 

## Log Metrics