## OnEarth Layer Configurator

This is a set of tools used to configure imagery layers for the OnEarth server.

## oe_configure_layer.py

```
Usage: oe_configure_layer.py --conf_file [layer_configuration_file.xml] --layer_dir [$LCDIR/layers/] --lcdir [$LCDIR] --projection_config [projection.xml] --sigevent_url [url] --time [ISO 8601] --restart_apache --no_xml --no_cache --no_twms --no_wmts --generate_legend --skip_empty_tiles

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -a ARCHIVE_CONFIGURATION, --archive_config=ARCHIVE_CONFIGURATION
                        Full path of archive configuration file.  Default:
                        $LCDIR/conf/archive.xml
  -c LAYER_CONFIG_FILENAME, --conf_file=LAYER_CONFIG_FILENAME
                        Full path of layer configuration filename.
  -d LAYER_DIRECTORY, --layer_dir=LAYER_DIRECTORY
                        Full path of directory containing configuration files
                        for layers.  Default: $LCDIR/layers/
  -e, --skip_empty_tiles
                        Do not generate empty tiles for layers using color
                        maps in configuration.
  -g, --generate_legend
                        Generate legends for layers using color maps in
                        configuration.
  -l LCDIR, --lcdir=LCDIR
                        Full path of the OnEarth Layer Configurator
                        (layer_config) directory.  Default: $LCDIR
  -m TILEMATRIXSET_CONFIGURATION, --tilematrixset_config=TILEMATRIXSET_CONFIGURATION
                        Full path of TileMatrixSet configuration file.
                        Default: $LCDIR/conf/tilematrixsets.xml
  -n, --no_twms         Do not use configurations for Tiled-WMS
  -p PROJECTION_CONFIGURATION, --projection_config=PROJECTION_CONFIGURATION
                        Full path of projection configuration file.  Default:
                        $LCDIR/conf/projection.xml
  -r, --restart_apache  Restart the Apache server on completion (requires
                        sudo).
  -s SIGEVENT_URL, --sigevent_url=SIGEVENT_URL
                        Default:  http://localhost:8100/sigevent/events/create
  -t TIME, --time=TIME  ISO 8601 time(s) for single configuration file
                        (conf_file must be specified).
  -w, --no_wmts         Do not use configurations for WMTS.
  -x, --no_xml          Do not generate getCapabilities and getTileService
                        XML.
  -z, --no_cache        Do not copy cache configuration files to cache
                        location.
```

## oe_create_cache_config

```
TWMS configuration tool
twms_tool [MODE] [OPTION]... [INPUT] [OUTPUT]
   MODE can be one of:
       h : Help (default)
       c : Configuration
       p : TiledWMSPattern



   Options:

   x : With mode c, generate XML
   b : With mode c, generate binary
       x and b are mutually exclusive

   INPUT and OUTPUT default to stdin and stdout respectively


  Options in the MRF header:
  <Raster>
       <Size> - x, y [1,1]
       <PageSize> - x, y and c [512,512,1]
       <Orientation> - TL or BL, only TL works
       <Compression> - [PNG]
  <Rsets>
       checks model=uniform attribute for levels
       checks scale=N attribute for powers of overviews
       <IndexFileName> Defaults to mrf basename + .idx
       <DataFileName>  Default to mrf basename + compression dependent extension
  <GeoTags>
       <BoundingBox> minx,miny,maxx,maxy [-180,-90,180,90]
  <TWMS>
       <Levels> Defaults to all
       <EmptyInfo> size,offset [0,0]
       <Pattern> One or more, enclose in <!CDATA[[ ]]>, the first one is used for pattern generation
       <Time> One or more, ISO 8601 time range for the product layer
```

## oe_generate_empty_tile.py

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
