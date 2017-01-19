# oe_vectorgen

`oe_vectorgen` is a tool that can be used to process vector datasets into a form that can be served by OnEarth. It currently supports ESRI Shapefiles and GeoJSON files as input.

### oe_vectorgen command syntax

`oe_vectorgen -c LAYER_CONFIG_XML -s SIGEVENT_URL`

The `-c` option is required. `-s` is optional.

### The `oe_vectorgen` XML configuration file
Similar to with `mrfgen`, `oe_vectorgen` uses options specified in an XML file to determine its output. The tags are as follows:

**`<date_of_data>` (required)** - In YYYYMMDD format.

**`<time_of_data>`** - In HH:MM:SS for subdaily data.

**`<parameter_name>` (required)** - Basename for the output files. This is also used as the layer name in MVT tiles.

**`<input_files>` or `<input_dir>` (required)** - Specify input Shapefile or GeoJSON files. When using `<input_files>`, each filename must be contained within a `<file>` element inside the `<input_files>` block.

**`<output_dir>` (required)** - Final destination for the files produced by `oe_vectorgen`.

**`<working_dir>` (required)** - Temporary directory for files produced by `oe_vectorgen`.

**`<logfile_dir>`** - Location for log files produced by `oe_vectorgen`.

**`<output_name>`** - Name for files created by `oe_vectorgen`. Defauts to `{$parameter_name}%Y%j_`.

**`<output_format>`** - Currently supports "MVT" and "ESRI Shapefile".

**`<target_epsg>`** - Specify the EPSG code of the output projection. 

**`<source_epsg>`** - Specify the EPSG code of the input projection. 

**`<target_x>` (MVT only)** - Pixel width of the highest zoom level (i.e., the bottom of the pyramid). Note that vector layers don't have a concept of pixels -- we use them as a way to describe the dimensions of the tile matrices and match them up with raster layer tile matrices. For example, if you select a `target_x` of 2048 and `tile_size` of 256, the highest zoom level will be 8 tiles wide (2048/256).

Please note that because the dimensions of the vector pyramid are arbitrary, this option is required and must be the exact dimension of the bottom of the pyramid. The easiest way to calculate this dimension is to multiply the desired tile pixel size by the width (in tiles) of the lowest level of the tile matrix set you wish to match up to.

**`<target_y>` (MVT only)** - Same as above, but for height. If this dimension is omitted, a square (i.e. 1x1) tile matrix will be assumed for projected layers and a rectangular matrix.

**`<extents>` (MVT only)** - The extents of the projection you're using in the units of that projection. Defaults to -180, -90, 180, 90 (degrees).

**`<overview_levels>` (MVT only)** - By default, overview levels are calculated as powers of 2. You can list a comma separated list of overview levels if you prefer.

**`<tile_size>` (MVT only)** - The tile size, in pixels relative to `<target_x>`. Match this up to any raster layers you wish to use these tiles with.

**`<feature_reduce_rate>` (MVT only)** - In order to increase performance and reduce tile size, `oe_vectorgen` can drop features from lower zoom levels. For example, with a rate of 2.5, all the features in the overview zoom level (i.e., the highest) will be retained. For each successive zoom level, 1 feature (chosen randomly) will be retained for every 2.5 in the previous zoom level.

For dense datasets, this option can help improve client performance, as the topmost zoom levels won't have the entire dataset crammed into one or two tiles.

**Note that feature reduction currently only works on Point datasets.**

**`<cluster_reduce_rate>` (MVT only)** - Another way to optimize tile size and performance, this option culls points that are within one pixel of each other. For example, at a rate of 2, any group of points within 1px of each other will be reduced (by random selection) to the square root of their previous number. No cluster reduction is done on the highest (overview) zoom level.