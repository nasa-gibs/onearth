## oe_generate_legend.py

This tool generates a color legend image from a GIBS color map XML file.

```
Usage: oe_generate_legend.py --colormap [file] --output [file]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COLORMAP, --colormap=COLORMAP
                        Full path or URL of colormap filename.
  -f FORMAT, --format=FORMAT
                        Format of output file. Supported formats: eps, pdf,
                        pgf, png, ps, raw, rgba, svg (default), svgz.
  -o OUTPUT, --output=OUTPUT
                        The full path of the output file
  -r ORIENTATION, --orientation=ORIENTATION
                        Orientation of the legend: horizontal or vertical
                        (default)
  -u SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
  -v, --verbose         Print out detailed log messages
```

### Examples:

Generate classification type legend:
```
oe_generate_legend.py -c sample_classifications.xml -o sample_classifications.svg
```

Generate vertical legend with discrete values as svg with tooltips:
```
oe_generate_legend.py -c sample_discrete.xml -f svg -r vertical -o sample_discrete.svg
```

Generate horizontal legend with continuous range as png:
```
oe_generate_legend.py -c sample_MODIS.xml -f png -r horizontal -o sample_MODIS.png
```

Generate classifications with vertical data values:
```
oe_generate_legend.py -c sample_range_class.xml -r vertical -o sample_range_class.svg
```	

**For more color maps and the GIBS color map schema, visit: https://map1.vis.earthdata.nasa.gov/colormaps/**