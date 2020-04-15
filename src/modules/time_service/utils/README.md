# OnEarth Date Configurator Tools

## `periods.lua` -- Lua period generator script

This script analyzes the list of dates for a given layer (`layer:layer_name:dates`) and generates a corresponding list of periods
(`layer:layer_name:periods`). It's intended to be run as a script within the Lua database itself.

The script takes a single keyword, which is the entire layer prefix, i.e. `epsg4326:layer:layer_name`.

**Example Command Line Usage**

`redis-cli --eval periods.lua epsg4326:layer:layer_name`

## `oe_scrape_time.py` -- Database regeneration tool

This tool will first search for the bucket's S3 inventory CSV logs. If the CSV logs are present, it will grab the most recent CSV log, and parse the csv file to generate time service entries for each layer. If no S3 Inventory data exists, the tool scrapes the bucket with MRF imagery and generates time service entries for each layer. 

#### S3 Inventory

To start S3 inventory, use aws console to find the source S3 bucket (bucket you want an inventory of). Select the "Management" tab, then click the "Inventory" botton. Select the "+Add new" bottom. 

For "Inventory name" input "entire", for "Destination bucket" select Buckets in this account, and find your destination bucket. We are currently using the same bucket for destination and source. For "Destination prefix" input inventory. For "Frequency" set to Daily. Select CSV for output format. Click "Save" and S3 will start within 48 hours.

Make sure you have the correct S3 inventory "Premissions" "Bucket Policy" set, users need S3 bucket policy, and VPCE policy for this tool to work. 

#### Python Dependencies

-   `boto3`
-   `redis-py`

#### Usage

The script accepts the following options:

-   `-b` indicates the bucket to be scraped. Default is `gitc-deployment-mrf-archive`
-   `-c` indicates whether to skip scraping for times if the database already exists. This is determined by a custom "created" key in Redis. 
-   `-p` indicates the port of the Redis time service database. Default is `6379`.
-   `-s` indicates the uri of the S3 service. Useful when you're using a localstack configuration for testing instead of an actual AWS S3 bucket.
-   `-t` indicates a tag (srt, best) to be used in tagging the dates.
-   `REDIS_URI` (argument)
