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


## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
