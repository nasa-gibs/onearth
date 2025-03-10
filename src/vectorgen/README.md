# oe_vectorgen

`oe_vectorgen` is a tool that can be used to process vector datasets into a form that can be served by OnEarth. It currently supports ESRI Shapefiles and GeoJSON files as input.

### oe_vectorgen command syntax

`oe_vectorgen -c LAYER_CONFIG_XML [options]`

```
Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -c CONFIGURATION_FILENAME, --configuration_filename=CONFIGURATION_FILENAME
                        Full path of configuration filename.  Default:
                        ./vectorgen_configuration_file.xml
  -s, --send_email      Send email notification for errors and warnings.
  --email_server=EMAIL_SERVER
                        The server where email is sent from (overrides
                        configuration file value)
  --email_recipient=EMAIL_RECIPIENT
                        The recipient address for email notifications
                        (overrides configuration file value)
  --email_sender=EMAIL_SENDER
                        The sender for email notifications (overrides
                        configuration file value)
  --email_logging_level=EMAIL_LOGGING_LEVEL
                        Logging level for email notifications: ERROR, WARN, or
                        INFO.  Default: ERROR
```

The `-c` option is required.

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

**`<output_format>`** - Currently supports "MVT-MRF" and "ESRI Shapefile".

**`<target_epsg>`** - Specify the EPSG code of the output projection. 

**`<source_epsg>`** - Specify the EPSG code of the input projection. 

**`<cloud_optimized_shapefile>` (shapefile only)** - When set to `true`, uses MapServer's [`shptree`](https://mapserver.org/utilities/shptree.html) command to create a spatial index file (`.qix`), then use MapServer's [`coshp`](https://mapserver.org/utilities/coshp.html) command to sort the shapefile and its `.qix` file to create a "cloud-optimized shapefile."

**`<target_x>` (MVT only)** - Pixel width of the highest zoom level (i.e., the bottom of the pyramid). Note that vector layers don't have a concept of pixels -- we use them as a way to describe the dimensions of the tile matrices and match them up with raster layer tile matrices. For example, if you select a `target_x` of 2048 and `tile_size` of 256, the highest zoom level will be 8 tiles wide (2048/256).

Please note that because the dimensions of the vector pyramid are arbitrary, this option is required and must be the exact dimension of the bottom of the pyramid. The easiest way to calculate this dimension is to multiply the desired tile pixel size by the width (in tiles) of the lowest level of the tile matrix set you wish to match up to.

**`<target_y>` (MVT only)** - Same as above, but for height. If this dimension is omitted, a square (i.e. 1x1) tile matrix will be assumed for projected layers and a rectangular matrix.

**`<target_extents>` (MVT only)** - The extents of the projection you're using in the units of that projection. Defaults to -180, -90, 180, 90 (degrees).

**`<overview_levels>` (MVT only)** - By default, overview levels are calculated as powers of 2. You can list a comma separated list of overview levels if you prefer.

**`<tile_size>` (MVT only)** - The tile size, in pixels relative to `<target_x>`. Match this up to any raster layers you wish to use these tiles with.

**`<feature_id>` (MVT only)** - The property name which contains a unique identifier for features in the input file(s). Defaults to `UID`.
- A **create** attribute indicates whether the property should be created during processing.  Defaults to `true` if `<feature_id>` is not provided; Defaults to `false` if `<feature_id>` is provided.  If created, value will be an integer counter.

**`<feature_reduce_rate>` (MVT only)** - In order to increase performance and reduce tile size, `oe_vectorgen` can drop features from lower zoom levels. For example, with a rate of 2.5, all the features in the overview zoom level (i.e., the highest) will be retained. For each successive zoom level, 1 feature (chosen randomly) will be retained for every 2.5 in the previous zoom level.

For dense datasets, this option can help improve client performance, as the topmost zoom levels won't have the entire dataset crammed into one or two tiles.

**Note that feature reduction currently only works on Point datasets.**

**`<cluster_reduce_rate>` (MVT only)** - Another way to optimize tile size and performance, this option culls points that are within one pixel of each other. For example, at a rate of 2, any group of points within 1px of each other will be reduced (by random selection) to the square root of their previous number. No cluster reduction is done on the highest (overview) zoom level.

**buffer_size** - The buffer size around each tile to avoid cutting off features and styling elements such as labels.
Default is 5 (pixel size in map units at each zoom level) which allows enough room for most styling.  
- An **edges** attribute indicates whether the buffering should be applied to the edges of the tile matrix.

**email_server** - The SMTP server where email notifications are sent from.

**email_recipient** - The recipient address for email notifications.

**email_recipient** - The recipient address(es) for email notifications. Use semi-colon ";" to separate recipients.

### Feature Filtering (MVT only)
vectorgen can be configured to pass all the features in a dataset through a set of filters. Features whose metadata passes the filters will be added to the output MVT MRF.

Here is a sample set of feature filters:

```
<feature_filters>
    <filter_block logic="OR">
        <equals name="id" value="some_value"/>
        <notEquals name="datetime" regexp="^should_not_start_with"/>
    </filter_block>
</feature_filters>
<overview_filters>
    <filter_block logic="AND" zoom="0">
        <lt name="RFP" value="some_numeric_value"/>
        <ge name="RFP" value="some_numeric_value"/>
    </filter_block>
</overview_filters>
```

**`<feature_filters>`** - This element should appear only once.  It contains one or more `filter_block` elements that specify filter tests that are applied to all feature data. A feature will be added to the MVT MRF only if it passes **all** the <filter_block> elements.

**`<overview_filters>`** - This element should appear only once.  It contains one or more `filter_block` elements that specify filter tests that are applied to feature data that have passed the `feature_filters`. A feature will be added to the specified MVT MRF TileMatrixLevel (e.g. 'zoom') only if it passes **all** the corresponding <filter_block> elements.

**`<filter_block>`** - Defines a single filter set and the logic used to evaluate it. The `logic` attribute is a boolean parameter (`OR` or `AND`) used to combine all the results of the tests (e.g. `equals`).  Filter blocks within a `overview_filters` element must also provide the `zoom` attribute, which is the value of the TileMatrixSet level to which the filter will be applied.

**Filter Tests** - One or more of the following tests are provided within the `filter_block` element.  The `value` attribute is required to specify the corresponding metadata property to which tests are applied.  Either the `value` or `regexp` attributes may be provided for string properties, only `value` is supported for numerical properties.  Regular expression strings must be valid Python regexps.
  1. `equals` - An `equals` test will pass if the metadata property with the given `name` is equal to the given `value` or passes the given `regexp` (if both are present, the regexp is used).
  2. `notEquals` -  A `notEquals` test does the opposite of `equals`. 
  3. `lt` - A `lt` test will pass if the value of the metadata property with the given `name` is less than the given `value`. (Values are converted to floats for comparison)
  4. `le` - A `le` test will pass if the value of the metadata property with the given `name` is less than or equal to the given `value`. (Values are converted to floats for comparison)
  5. `gt` - A `gt` test will pass if the value of the metadata property with the given `name` is greater than the given `value`. (Values are converted to floats for comparison)
  6. `ge` - A `ge` test will pass if the value of the metadata property with the given `name` is greater than or equal to the given `value`. (Values are converted to floats for comparison)

# oe_json_to_uvtile

To support the creation of vector flow visualizations in Worldview, the `oe_json_to_uvtile` can be used as a pre-processing step to create PNG or GeoTIFF mosaics from GeoJSON wind/ocean vector data. Currently, the script is primarily intended to support OSCAR data, but ASCAT support may be added later. The UV Tile mosaics can then be ingested into mrfgen to create MRFs that could be used in a special type of raster layer. Worldview will need to implement a new type of layer leveraging the new Flow feature of OpenLayers to properly display this raster layer as a vector flow visualization. 

### oe_json_to_uvtile syntax

`oe_json_to_uvtile.py [-h] [-o FILE] [--resolution RESOLUTION] [--format {png,tiff,tif}] FILE`

```
Convert GeoJSON UV direction vectors to PNG or TIFF images for WebGL shaders

positional arguments:
  FILE                  Path to input GeoJSON file containing UV direction vectors

options:
  -h, --help            show this help message and exit
  -o FILE, --output FILE
                        Path to save output tile. Default is same location/filename as input with png/tif extension
  --resolution RESOLUTION
                        Override the auto-detected grid resolution (in degrees)
  --format {png,tiff,tif}
                        Output format: 'png' for 8-bit quantized or 'tiff'/'tif' for 32-bit float (default: png)
```

### Example usage

Within an `onearth_test` or `onearth_tools` container:
```bash
oe_json_to_uvtile oscar_currents_final_uv_20200101.json -o /mrfgen/data/oscar_currents_uv_20200101_1440x720.png
```

`oscar_currents_final_uv_20200101.json` is a GeoJSON file produced by HyBIG representing regularly gridded uv components of ocean currents at a global extent. The default resolution of this data 0.25 degrees and will be inferred from the data. In general, you can override the resolution with the `--resolution` option, for example `--resolution 1` would result in a 1 degree/pixel resolution. Downscaling is not supported, so the specified resolution override may not exceed the inferred resolution of the data itself.

### Processing with MRFgen

When outputting a PNG, the data must be converted to GeoTIFF first. From our previous example, we need to run this command:
```bash
gdal_translate -of GTiff -a_srs EPSG:4326 -a_ullr -180 90 180 -90 /mrfgen/data/oscar_currents_uv_20200101_1440x720.png /mrfgen/data/oscar_currents_uv_20200101_1440x720.tiff
```

Our mrfgen config would like this:
```xml
<?xml version="1.0"?>
<mrfgen_configuration>
  <parameter_name>OSCAR_UV_v1</parameter_name>
  <date_of_data>20200102</date_of_data>
  <input_files>
    <file>/mrfgen/data/oscar_currents_uv_20200102_1440x720.tiff</file>
  </input_files>
  <output_dir>/mrfgen/output</output_dir>
  <working_dir>/mrfgen/work</working_dir>
  <logfile_dir>/mrfgen/log</logfile_dir>
  <mrf_compression_type>PNG</mrf_compression_type>
  <mrf_name>OSCAR_UV_v1-20200102000000.mrf</mrf_name>
  <source_epsg>4326</source_epsg>
  <target_epsg>4326</target_epsg>
  <extents>-180,-90,180,90</extents>
  <target_extents>-180,-90,180,90</target_extents>
  <!--As with other types of MRFs, the output size is determined by the nearest number of whole tiles to fit the input data-->
  <target_x>1536</target_x>
  <target_y>1024</target_y>
  <mrf_blocksize>512</mrf_blocksize>
  <overview_levels>2 4 8 16 32 64 128 256 512</overview_levels>
  <overview_resampling>nnb</overview_resampling>
  <resize_resampling>average</resize_resampling>
  <mrf_empty_tile_filename>/mrfgen/empty_tiles/Blank_RGBA_512.png</mrf_empty_tile_filename>
  <vrtnodata>0</vrtnodata>
  <mrf_nocopy>true</mrf_nocopy>
  <mrf_merge>false</mrf_merge>
</mrfgen_configuration>
```
