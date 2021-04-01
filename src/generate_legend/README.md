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
  -v, --verbose         Print out detailed log messages
```

### Examples:

Generate sample legend
```
oe_generate_legend.py -c onearth/src/colormaps/samples/ColorMap_v1.2_Sample.xml -o sample.svg
```

Generate horizontal PNG legend with discrete values
```
oe_generate_legend.py -c onearth/src/colormaps/samples/SampleColorMap_v1.2_Discrete.xml -r horizontal -f png -o sample_discrete.png 
```

Generate horizontal PNG legend with discrete values and white text with black stroke
```
oe_generate_legend.py -c onearth/src/colormaps/samples/SampleColorMap_v1.2_Discrete.xml -r horizontal -f png -l white -s black -o sample_discrete.png 
```

Generate vertical SVG (including tooltips) legend with continuous values
```
oe_generate_legend.py -c onearth/src/colormaps/samples/SampleColorMap_v1.2_ContinuousLinear.xml -r vertical -f svg -o sample_continuous.svg
```

Generate horizontal PNG legend with continuous values and classifications verbosely
```
oe_generate_legend.py -c onearth/src/colormaps/samples/SampleColorMap_v1.2_ContinuousAndClass.xml -r horizontal -f png -v -o sample_continuousclass.png
```

**For more color maps and the GIBS color map schema, checkout [colormaps](../colormaps/).**