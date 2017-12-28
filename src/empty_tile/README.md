## oe_generate_empty_tile.py

This tool generates an empty (nodata) tile for mod_onearth. It is used by oe_configure_layer.py, which passes in a specified colormap from the layer configuration file and sets the width and height to match the proper MRF tiles.

```
Usage: oe_generate_empty_tile.py --colormap [file] --output [file] --height [int] --width [int] 

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COLORMAP, --colormap=COLORMAP
                        Full path or URL of colormap filename.
  -f FORMAT, --format=FORMAT
                        Format of output file. Supported formats: png
  -i INDEX, --index=INDEX
                        The index of the color map to be used as the empty
                        tile palette entry, overrides nodata value
  -o OUTPUT, --output=OUTPUT
                        The full path of the output file
  -t TYPE, --type=TYPE  The image type: rgba or palette. Default: palette
  -v, --verbose         Print out detailed log messages
  -x WIDTH, --width=WIDTH
                        Width of the empty tile  (default: 512)
  -y HEIGHT, --height=HEIGHT
                        Height of the empty tile (default: 512)
```

### Examples:

Generate empty tile using URL (local path may be used as well).
```
oe_generate_empty_tile.py --colormap https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_Combined_Value_Added_AOD_v6.xml --output empty_tile.png
```
Generate empty tile with custom dimensions.
```
oe_generate_empty_tile.py --colormap https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_Combined_Value_Added_AOD_v6.xml --output empty_tile.png --height 256 --width 256
```
You will notice that this empty tile is transparent when viewed. Use GDAL to verify that the colormap in the empty tile matches the colormap XML.
```
gdalinfo empty_tile.png
```
By default, the first colormap entry with nodata="true" is the color used for the empty tile. In the previous example, the first (0) entry happens to be used: rgb="220,220,255". Use the `--index` option to pick another index, say (5) for example. This will produce a light yellow color for the empty tile.
```
oe_generate_empty_tile.py --colormap https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_Combined_Value_Added_AOD_v6.xml --output empty_tile.png --index 5
```
To change between a PNG with a palette and RGBA, use the `--type` option. `gdalinfo` will show that a palette is no longer available when `rgba` is specified, but the correct color for the empty tile is seen when viewed.
```
oe_generate_empty_tile.py --colormap https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_Combined_Value_Added_AOD_v6.xml --output empty_tile.png --index 5 --type rgba
```
Add the `--verbose` option to print detailed log messages.
```
oe_generate_empty_tile.py --colormap https://gibs.earthdata.nasa.gov/colormaps/v1.3/MODIS_Combined_Value_Added_AOD_v6.xml --output empty_tile.png --index 5 --type rgba --verbose
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
