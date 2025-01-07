# OnEarth Date Configurator Tools

## `periods.lua` -- Lua period generator script

This script analyzes the list of dates for a given layer (`layer:layer_name:dates`) and generates a corresponding list of periods
(`layer:layer_name:periods`). It's intended to be run as a script within the Lua database itself.

The script takes a single keyword, which is the entire layer prefix, i.e. `epsg4326:layer:layer_name`.

It can also be run with the following optional positional arguments after the keyword:

`{date_to_be_added} {start_datetime} {end_datetime} {keep_existing_periods}`

- `date_to_be_added`: The script will add this date for the layer before recalculating the layer's periods if there's a change.
- `start_datetime`: Only dates that take place after this value will be considered while calculating periods
- `end_datetime`: Only dates that take place before this value will be considered while calculating periods
- `keep_existing_periods`: Don't delete existing periods at `:periods` before adding the newly calculated periods. Note that this can lead to overlapping periods. Most useful when using `start_datetime` and `end_datetime`.

Any of these arguments can be skipped by passing in `false`.

Although OnEarth still supports the `:periods` key being represented by an unsorted `set` in redis, this script will set the periods key to be a sorted `zset` by default when regenerating the `:periods` key. It can, however, correctly handle adding to existing unsorted `set` `:periods` keys using `keep_existing_periods`.

### Example Command Line Usage

`redis-cli --eval periods.lua epsg4326:layer:layer_name`

## `best.lua` -- Best layer generator script

This script will check if the layer provided is part of a best layer, by checking to see if layer has `best_layer` key in redis. If one exist, best.lua it will retrieve the best layers' `best_config:`. The `best_config` will contain all the real layers that make up the virtual best layer, along with the prority of each layer. Best.lua will check from highest priority to lowest with the date provided. This first layer with a valid date will the best layer and will be added to the the best layer :best HMSET. This :best HMSET will have a date as a key and layer as value, so the date will point to the highest prority layer that exist. This date will also be added to the best layers dates for periods generation.   

Execution syntax:

```EVAL best.lua layer_prefix:source_layer_name date_time```

This script can also be used to regenerate the `:best` and `:dates` keys for a best layer. To do this, run the script while giving it only the name of the best layer without a date time:

```EVAL best.lua layer_prefix:best_layer_name```

best.lua is used by ingest, oe-redis-update, and oe_scrape_time.

## `oe_periods_configure.py` -- Custom time configuration loader

This tool will load custom time period configurations as specified in a layer configuration file's `time_config` item into Redis for evaluation when the periods.lua script is executed. The tool will also load custom best available configurations as specified in a layer configuration file's `best_config` item into Redis.
Configurations are loaded into the `prefix_tags:layer:layer_name:config` keyword. This script should be executed before periods.lua is run.
The `-g` or `--generate_periods` option will automatically generate the periods for each layer by running periods.lua.
Best available configurations are loaded into the `prefix_tags:layer:layer_name:best` keyword. The `-t` or `--tag` option with an empty string will generated “endpoint-agnostic” keys. 

### Python Dependencies

- `yaml`
- `redis-py`

### Usage

The script accepts the following options:

- `-h, --help` display help message and exit.
- `-g, --generate_periods` Generate periods for each layer based on config values
- `-e ENDPOINT_CONFIG, --endpoint_config ENDPOINT_CONFIG` an endpoint config YAML file to load layers
- `-l LAYER_FILTER, --layer_filter LAYER_FILTER` Unix style pattern to filter layer names
- `-p PORT, --port PORT` redis port for database
- `-r REDIS_URI, --redis_uri REDIS_URI` URI for the Redis database
- `-t TAG, --tag TAG` Classification tag (nrt, best, std, etc.)

## `oe_scrape_time.py` -- Database regeneration tool

This tool will first check whether the s3_inventory option has been flagged. If the -i flag is present, the tool will search for the bucket's S3 Inventory CSV logs. If the CSV logs are present, it will parse the most recent CSV file to generate time service entries for each layer. If no S3 Inventory data exists or the -i flag isn't declared. The tool scrapes the bucket containing MRF imagery and generates time service entries for each layer. It also supports scraping times from a local directory in place of an S3 bucket.

### S3 Inventory

To start S3 inventory, use the AWS console to find the source S3 bucket (the bucket that you want to inventory). Select the "Management" tab, and then click the "Inventory" button. Select the "+Add new" button.

For "Inventory name" input `entire`, for "Destination bucket" select `Buckets in this account`, and find your destination bucket. We are currently using the same bucket for destination and source. For "Destination prefix" input `inventory`. For "Frequency" set to `Daily`. Select `CSV` for output format. Click "Save" and S3 will start within 48 hours.

Make sure you have an appropriate bucket policy configured to allow for S3 Inventory.

### Python Dependencies

- `boto3`
- `redis-py`

### Usage

The script accepts the following options:

- `-b` indicates the bucket to be scraped.
- `-c` indicates whether to skip scraping for times if the database already exists. This is determined by a custom "created" key in Redis. 
- `-p` indicates the port of the Redis time service database. Default is `6379`.
- `-s` indicates the uri of the S3 service (useful when you're using a localstack configuration for testing instead of an actual AWS S3 bucket), or a path to a local directory to use instead of an S3 bucket.
- `-t` indicates a tag (srt, best) to be used in tagging the dates.
- `-i` indicates whether to use s3 inventory CSV logs for time scrapping.
- `REDIS_URI` (argument)


## `oe_periods_key_converter.py` -- Redis `:periods` key set type converter tool

This tool converts the `:periods` key for layers between the unsorted `set` type and the sorted `zset` type. OnEarth supports both types, but the sorted `zset` results in more efficient time service requests since the periods do not need to be sorted when each request takes place.

### Python Dependencies

- `redis-py`

This script accepts the following options:

- `-h, --help`: Shows help message and exits.
- `-t DEST_TYPE, --destination_type DEST_TYPE`: Type that the `:periods` keys should be converted to. Must be `zset` or `set`. Default is `zset`.
- `-l LAYER_FILTER, --layer_filter LAYER_FILTER`: Unix style pattern to filter layer names.
- `-p PORT, --port PORT`: indicates the port of the Redis time service database. Default is `6379`.
- `-r REDIS_URI, --redis_uri REDIS_URI`: URI for the Redis database
- `-v, --verbose`: Print out detailed log messages
