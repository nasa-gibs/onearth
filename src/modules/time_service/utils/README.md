# OnEarth Date Configurator Tools

## `periods.lua` -- Lua period generator script

This script analyzes the list of dates for a given layer (`layer:layer_name:dates`) and generates a corresponding list of periods
(`layer:layer_name:periods`). It's intended to be run as a script within the Lua database itself.

The script takes a single keyword, which is the entire layer prefix, i.e. `epsg4326:layer:layer_name`.

**Example Command Line Usage**

`redis-cli --eval periods.lua epsg4326:layer:layer_name`

## `oe_scrape_time.py` -- Database regeneration tool

This tool scrapes a bucket with MRF imagery and generates time service entries for each layer.

#### Python Dependencies

-   `boto3`
-   `redis-py`

#### Usage

The script accepts the following options:

-   `-b` indicates the bucket to be scraped. Default is `gitc-deployment-mrf-archive`
-   `-p` indicates the port of the Redis time service database. Default is `6379`.
-   `-s` indicates the uri of the S3 service. Useful when you're using a localstack configuration for testing instead of an actual AWS S3 bucket.
-   `-t` indicates a tag (srt, best) to be used in tagging the dates.
-   `REDIS_URI` (argument)
