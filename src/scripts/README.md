## OnEarth Scripts

A set of helper scripts for OnEarth.


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
