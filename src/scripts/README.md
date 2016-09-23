## OnEarth Scripts

A set of helper scripts for OnEarth.

## colorMapToSLD.py

The colorMapToSLD.py script converts an OnEarth XML ColorMap into an SLD document.  The output is printed to the screen and can be piped to an output file.  The output SLD may be formatted in either the version 1.0.0 or 1.1.0 specification version. Note that if the output is to be version 1.1.0, the input XML Colormap must have two _ColorMap_ elements.  The first, for the "No Data" transparent entry.  The second, for opaque data values. 

### Usage


```Shell
Usage: colorMapToSLD.py -c <colormap> -l <layer> -r <rgb_order> -s <version>

Options:
  -h, --help             show this help message and exit
  -c COLORMAP_FILE, --colormap COLORMAP_FILE
							Path to colormap file to be converted
  -l LAYER_NAME, --layer LAYER_NAME
							Value to be placed in the NamedLayer/Name element
  -r RGBA_ORDER , --rgba_order RGBA_ORDER
    						The RGBA ordering to be used when generating the fallbackValue.
    						The alpha value is optional.  Sample values "RGB", "ARGB"
  -s SLD_SPEC_VERSION, --spec_version SLD_SPEC_VERSION
  						SLD specification version: "1.0.0" or "1.1.0"
```
Example execution:
```Shell
./colorMapToSLD.py -c path/to/colormap.xml -l DATA_LAYER_NAME -r RGBA -s 1.0.0
```


## colorMapToHTML.py

The colorMapToHTML.py script converts an OnEarth XML ColorMap into an HTML document.  The output is printed to the screen and can be piped to an output file.  The HTML file is best viewed with the [resources](../colormaps/resources) folder present in the same parent directory as the HTML file.

```Shell
Usage: colorMaptoHTML.py -c <colormap>

Options:
  -h, --help                show this help message and exit
  -c COLORMAP_FILE, --colormap COLORMAP_FILE
						    Path to colormap file to be converted
```

Example execution:
```Shell
./colorMaptoHTML.py -c path/to/colorap.xml
```

## oe_validate_palette.py
oe_validate_palette.py is a tool for validating an image palette with a GIBS colormap. The output includes a summary of colors matched and the colors unique to the colormap and image. Mismatches are displayed if there are any. The system exit code is the number of colors in the image not found in the color table.

```Shell
Usage: oe_validate_palette.py --colormap [colormap.xml] --input [input.png] --sigevent_url [url] --verbose

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c COLORMAP_FILENAME, --colormap=COLORMAP_FILENAME
                        Full path of colormap filename.
  -i INPUT_FILENAME, --input=INPUT_FILENAME
                        Full path of input image
  -u SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
  -v, --verbose         Print out detailed log messages
```


## read_idx.py

The read_idx.py tool reads an MRF index file and outputs the contents to a CSV file.

```Shell
Usage: read_idx.py --index [index_file] --output [output_file]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INDEX, --index=INDEX
                        Full path of the MRF index file
  -l, --little_endian   Use little endian instead of big endian (default)
  -o OUTPUT, --output=OUTPUT
                        Full path of output CSV file
  -v, --verbose         Verbose mode
```


## read_mrf.py

The read_mrf.py tool reads MRF files and outputs the contents as an image.

```Shell
Usage: read_mrf.py --input [mrf_file] --output [output_file] (--tilematrix INT --tilecol INT --tilerow INT) OR (--offset INT --size INT) OR (--tile INT)

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Full path of the MRF data file
  -f OFFSET, --offset=OFFSET
                        data offset
  -l, --little_endian   Use little endian instead of big endian (default)
  -o OUTPUT, --output=OUTPUT
                        Full path of output image file
  -s SIZE, --size=SIZE  data size
  -t TILE, --tile=TILE  tile within index file
  -v, --verbose         Verbose mode
  -w TILEMATRIX, --tilematrix=TILEMATRIX
                        Tilematrix (zoom level) of tile
  -x TILECOL, --tilecol=TILECOL
                        The column of tile
  -y TILEROW, --tilerow=TILEROW
                        The row of tile
  -z ZLEVEL, --zlevel=ZLEVEL
                        the z-level of the data
```


## read_mrfdata.py

The read_mrfdata.py tool reads an MRF data file from a specified index and offset and outputs the contents as an image.

```Shell
Usage: read_mrfdata.py --input [mrf_data_file] --output [output_file] (--offset INT --size INT) OR (--index [index_file] --tile INT)

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -i INPUT, --input=INPUT
                        Full path of the MRF data file
  -f OFFSET, --offset=OFFSET
                        data offset
  -l, --little_endian   Use little endian instead of big endian (default)
  -n INDEX, --index=INDEX
                        Full path of the MRF index file
  -o OUTPUT, --output=OUTPUT
                        Full path of output image file
  -s SIZE, --size=SIZE  data size
  -t TILE, --tile=TILE  tile within index file
  -v, --verbose         Verbose mode
```


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


## SLDtoColorMap.py

The SLDtoColorMap.py script converts an SLD into an OnEarth XML Colormap.  The output is printed to the screen and can be piped to an output file.  The input SLD may be formatted in either the version 1.0.0 or 1.1.0 specification version.


```Shell
Usage: SLDtoColorMap.py -s <sld> -l <layer> -u <units> -o <offset> -f <factor> -r <rgba_order>

Options:
  -h, --help                show this help message and exit
  -s SLD_FILE, --sld SLD_FILE
							Path to SLD file to be converted
  -l LAYER_NAME, --layer LAYER_NAME
							Value to be placed in the NamedLayer/Name element
  -u UNITS, --units UNITS
							Units to be appended to data values when generating labels.  (Optional)
  -o OFFSET, --offset OFFSET
							Floating point value used as an offset when calculating raw data values from SLD values.  (Optional)
  -f FACTOR, --factor FACTOR
							Floating point value used as factor when calculating raw data values from SLD values.  (Optional)
  -r RGBA_ORDER , --rgba_order RGBA_ORDER
							The RGBA ordering to be used when parsing the SLD v1.1.0 fallbackValue.
							The alpha value is optional.  Sample values "RGB", "ARGB"
```

Example execution:
```Shell
./SLDtoColorMap.py -s path/to/sld.xml -l DATA_LAYER_NAME -r RGBA -u K
```


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
