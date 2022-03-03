## OnEarth Scripts

A set of helper scripts for OnEarth.


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
  -e, --epsg            The EPSG code for projection.
                        Supports EPSG:4326 (default), EPSG:3857, EPSG:3031, EPSG:3413
  -T, --tilesize        Override the tilesize value decided by the EPSG code
```

## wmts2twmsbox.py

Converts WMTS row and column to equivalent TWMS bounding box.  Assumes EPSG:4326 projection.

```
Usage: wmts2twmsbox.py --col [TILECOL] --row [TILEROW] --scale_denominator [value] OR --top_left_bbox [bbox]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -e, --epsg            The EPSG code for projection.
                        Supports EPSG:4326 (default), EPSG:3857, EPSG:3031, EPSG:3413
  -c COL, --col=COL     WMTS TILECOL value.
  -r ROW, --row=ROW     WMTS TILEROW value.
  -s SCALE_DENOMINATOR, --scale_denominator=SCALE_DENOMINATOR
                        WMTS scale denominator value from getCapabilities.
  -t TOP_LEFT_BBOX, --top_left_bbox=TOP_LEFT_BBOX
                        The TWMS bounding box for the top-left corner tile
                        (e.g., "-180,81,-171,90").
  -T, --tilesize        Override the tilesize value decided by the EPSG code
```


## oe_sync_s3_configs.py

This script synchronizes OnEarth config files on S3 with those on a file system.
Files on S3 will always act as the 'master' (i.e., files found on S3 that are not on the file system 
will be downloaded, while files found on the file system but not on S3 will be deleted).
File modifications are not detected. Use --force to overwrite existing files.

```
Usage: oe_sync_s3_configs.py [-h] [-b BUCKET] [-d DIR] [-f] [-c] [-n] [-p PREFIX]
                             [-s S3_URI]

Downloads OnEarth layer configurations from S3 bucket contents.

optional arguments:
  -h, --help            show this help message and exit
  -b BUCKET, --bucket BUCKET
                        bucket name
  -d DIR, --dir DIR     Directory on file system to sync
  -f, --force           Force update even if file exists
  -n, --dry-run         Perform a trial run with no changes made
  -p PREFIX, --prefix PREFIX
                        S3 prefix to use
  -s S3_URI, --s3_uri S3_URI
                        S3 URI -- for use with localstack testing
```


## oe_sync_s3_idx.py

This script synchronizes IDX files on S3 with those on a file system.
Files on S3 will always act as the 'master' (i.e., files found on S3 that are not on the file system 
will be downloaded, while files found on the file system but not on S3 will be deleted).
File modifications are not detected. Use --force to overwrite existing files. Use --checksum to determine whether
existing files should be overwritten based on a mismatching checksum with S3 object.

```
Usage: oe_sync_s3_idx.py [-h] [-b BUCKET] [-d DIR] [-f] [-n] [-p PREFIX]
                         [-s S3_URI]

Rebuilds IDX files on system from S3 bucket contents.

optional arguments:
  -h, --help            show this help message and exit
  -b BUCKET, --bucket BUCKET
                        bucket name
  -d DIR, --dir DIR     Directory on file system to sync
  -f, --force           Force update even if file exists
  -c, --checksum        Evaluate checksum of local file against s3 object and 
                        update even mismatched
  -n, --dry-run         Perform a trial run with no changes made
  -p PREFIX, --prefix PREFIX
                        S3 prefix to use
  -s S3_URI, --s3_uri S3_URI
                        S3 URI -- for use with localstack testing
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
