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
  -u SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
  -v, --verbose         Print out detailed log messages
  -x WIDTH, --width=WIDTH
                        Width of the empty tile
  -y HEIGHT, --height=HEIGHT
                        Height of the empty tile
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
