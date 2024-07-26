## OnEarth Colormaps


Contains tools for working with GIBS color maps.

## colorMapToSLD.py

The colorMapToSLD.py script converts an OnEarth XML ColorMap into an SLD document.  The output is printed to the screen and can be piped to an output file.  The output SLD may be formatted in either the version 1.0.0 or 1.1.0 specification version. Note that if the output is to be version 1.1.0, the input XML Colormap must have two _ColorMap_ elements.  One should be the "No Data" transparent entry.  The other, for opaque data values. 

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

The colorMapToHTML.py script converts an OnEarth XML ColorMap into an HTML document.  The output is printed to the screen and can be piped to an output file.  The HTML file is best viewed with the [resources](./resources) folder present in the same parent directory as the HTML file.

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

## SLDtoColorMap.py

The SLDtoColorMap.py script converts an SLD into an OnEarth XML Colormap.  The output is printed to the screen and can be piped to an output file.  The input SLD may be formatted in either the version 1.0.0 or 1.1.0 specification version.


```Shell
Usage: SLDtoColorMap.py -s <sld> -l <layer> -u <units> -o <offset> -f <factor> -r <rgba_order>

Options:
  -h, --help                show this help message and exit
  -s SLD_FILE, --sld SLD_FILE
							Path to SLD file to be converted
  -c COLORMAP_FILE, --sld COLORMAP_FILE
              Path to colormap file to be created.  If not provided, output is printed to stdout
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
  -p PRECISION, --precision PRECISION
              The number of decimal places to round values to plus the format specifier for floating point (f) or exponential (e).  Example: '2f' or '3e'  (Optional)
```

Example execution:
```Shell
./SLDtoColorMap.py -s path/to/sld.xml -l DATA_LAYER_NAME -r RGBA -u K
```

## colorMaptoTXT.py

The colorMaptoTXT.py script converts an OnEarth XML Colormap to the GDAL text-based colormap format. A reference for the usage of this type of colormap can be found here: [https://gdal.org/programs/gdaldem.html#color-relief](https://gdal.org/programs/gdaldem.html#color-relief). GDAL colormaps support a "round to the floor value" mode which is supported by this script via the `--round` command line argument. 

Note that `gdaldem` assumes that the input granule has already been unscaled and converted to the intended data type when applying the colormap via the `gdaldem color_relief` mode. Typically this is done by the data provider (such as PODAAC); however, if you are manually processing a netCDF or other type of scaled granule you will need to add the `-unscale -ot <intended_data_type>` options when using `gdal_translate`.

```
usage: colorMaptoTXT.py [-h] -c colormap [--scale SCALE] [--offset OFFSET] [-o outfile] [--round] [-p PRECISION]

optional arguments:
  -h, --help            show this help message and exit
  -c colormap           Path to colormap file to be converted.
  --scale SCALE         Optionally specify the scale factor for the output colormap. This can sometimes be found in the CMR variable metadata. For example, a colormap with percent units might need --scale 0.01 to appear correct.
  --offset OFFSET       Optionally specify the offset for the output colormap. This can sometimes be found in the CMR variable metadata. For example, a colormap in units of degC might need --scale 273.15 to convert to Kelvin.
  -o outfile            Output filename to use for the text file colormap. If unused, the colormap will be printed to stdout.
  --round               Create the colormap with a "round to the floor" mode, where the same color value is used across an entire quantization level, with no interpolation.
  -p PRECISION, --precision PRECISION
                        Digits of decimal precision to use for quantization levels in the colormap. Default is 2 (e.g., 99.00) for normal values and 4 (e.g., 1.3750e-05) for scientific notation values.
```

Example execution:
```Shell
./colorMaptoTXT.py -c path/to/colormap.xml -o path/to/output_colormap.txt
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
