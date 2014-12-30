# OnEarth Configuration

## Imagery Layers

Dependent RPMs: 
* gibs-gdal?
* onearth-config?

Steps:
1. Generate MRF metadata file
2. Generate Empty Tile (Optional)
3. Generate Legend Images (Optional)
4. Generate ColorMap
5. Update/Create OnEarth [Layer Configuration](config_layer.md) file
6. Update/Create OnEarth [Support Configuration](config_support.md) files
7. Execute layer configuration tool 
8. Restart Apache

## Imagery Endpoint

Dependent RPMs: 
* onearth

Steps:
1. [Configure Endpoint](config_endpoint)
2. [Configure Apache](config_apache)
3. Generate Cache Configuration File
4. Restart Apache
