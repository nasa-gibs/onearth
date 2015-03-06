## OnEarth Scripts

A set of helper scripts for OnEarth.

## RGBApng2Palpng

The RGBApng2Palpng tool converts an RGBA PNG image to a Paletted PNG image using a GIBS color map or lookup table of comma-separated RGBA values.

### Compile

To compile the tool:
```Shell
gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng
```

### Usage

```Shell
Usage: RGBApng2Palpng [-v] -lut=<ColorMap file (must contain RGBA)> -fill=<LUT index value> -of=<output palette PNG file> <input RGBA PNG file>
```
* -v: Verbose print mode
* -lut: [GIBS color map](https://map1.vis.earthdata.nasa.gov/colormaps/) or lookup table of comma-separated RGBA values to be used as the PNG palette
* -fill: The fill value, used to fill the remaining palette of colors
* -of: The Paletted PNG output file

Example execution:
```Shell
./RGBApng2Palpng -v -lut=colormap.xml -fill=0 -of=pal_output.png rgba_input.png
```

If the RGBApng2Palpng tool detects colors in the image that are not in the colormap, they will be printed out to the command line at the end of the script. The number of missing colors is used as the exit code.

This tool is utilized by [mrfgen.py](../mrfgen/README.md).

## twmsbox2wmts.py

Converts TWMS bounding box to WMTS tile.  Assumes EPSG:4326 projection.

```
Usage: twmsbox2wmts.py --bbox [bbox]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -b REQUEST_BBOX, --bbox=REQUEST_BBOX
                        The requested TWMS bounding box to be translated
                        (e.g., "-81,36,-72,45").
```

## wmts2twmsbox.py

Converts WMTS row and column to equivalent TWMS bounding box.  Assumes EPSG:4326 projection.

```
Usage: wmts2twmsbox.py --col [TILECOL] --row [TILEROW] --scale_denominator [value] OR --top_left_bbox [bbox]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COL, --col=COL     WMTS TILECOL value.
  -r ROW, --row=ROW     WMTS TILEROW value.
  -s SCALE_DENOMINATOR, --scale_denominator=SCALE_DENOMINATOR
                        WMTS scale denominator value from getCapabilities.
  -t TOP_LEFT_BBOX, --top_left_bbox=TOP_LEFT_BBOX
                        The TWMS bounding box for the top-left corner tile
                        (e.g., "-180,81,-171,90").
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
