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


## oe_configure_reproject_layer.py

Utility script to generate configurations for mod_reproject/mod_wmts_wrapper. Typically used by `oe_configure_layer` but can be used as a separate tool.

```
Usage: oe_configure_reproject_layer.py --conf_file [layer_configuration_file.xml] --lcdir [$LCDIR] --no_xml --no_twms --no_wmts

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c LAYER_CONFIG_PATH, --conf_file=LAYER_CONFIG_PATH
                        Full path of layer configuration filename.
  -l LCDIR, --lcdir=LCDIR
                        Full path of the OnEarth Layer Configurator
                        (layer_config) directory.  Default: $LCDIR
  -m TILEMATRIXSETS_CONFIG_PATH, --tilematrixset_config=TILEMATRIXSETS_CONFIG_PATH
                        Full path of TileMatrixSet configuration file.
                        Default: $LCDIR/conf/tilematrixsets.xml
  -n, --no_twms         Do not use configurations for Tiled-WMS
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value
  -w, --no_wmts         Do not use configurations for WMTS.
  -x, --no_xml          Do not generate getCapabilities and getTileService
                        XML.
  -z, --stage_only      Do not move configurations to final location; keep
                        configurations in staging location only.
  --debug               Produce verbose debug messages
```


## oe_validate_configs.py

Utility script to validate OnEarth layer and Apache configurations.

```
Usage: oe_validate_configs.py --input [input file] --verbose

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d DIFF_FILENAME, --diff_file=DIFF_FILENAME
                        Full path existing configuration file to diff
  -e ENVIRONMENT_FILENAME, --environment=ENVIRONMENT_FILENAME
                        Full path of OnEarth environment configuration file
  -i INPUT_FILENAME, --input=INPUT_FILENAME
                        Full path of input configuration file
  -r, --replace         Replace diff_file (after backup) with input if no
                        errors are reported
  -t CONFIG_TYPE, --type=CONFIG_TYPE
                        Type of input file: apache or oe_layer
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value
  -v, --verbose         Print out detailed log messages
  -S, --ignore_staged_files
                        Do not validate configurations in staging location
  -F, --ignore_final_files
                        Do not validate configurations in final config
                        locations; evaluate staged files only
```


## oe_sync_s3_idx.py

This script synchronizes IDX files inside S3 tar balls with those on a file system.
Files on S3 will always act as the 'master' (i.e., files found on S3 that are not on the file system 
will be downloaded, while files found on the file system but not on S3 will be deleted).
File modifications are not detected. Use --force to overwrite existing files.

```
Usage: oe_sync_s3_idx.py [-h] [-b BUCKET] [-d DIR] [-f] [-p PREFIX]
                         [-s S3_URI]

Rebuilds IDX files on system from S3 bucket contents.

optional arguments:
  -h, --help            show this help message and exit
  -b BUCKET, --bucket BUCKET
                        bucket name
  -d DIR, --dir DIR     Directory on file system to sync
  -f, --force           Force update even if file exists
  -p PREFIX, --prefix PREFIX
                        S3 prefix to use
  -s S3_URI, --s3_uri S3_URI
                        S3 URI -- for use with localstack testing
```

## Contact

Contact us by sending an email to
[support@earthdata.nasa.gov](mailto:support@earthdata.nasa.gov)
