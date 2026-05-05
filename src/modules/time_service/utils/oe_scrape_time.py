#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script scrapes MRF files in S3 for time periods and then populates Redis for the OnEarth time service.
"""

import boto3
from functools import reduce
from datetime import datetime
import redis
import argparse
from pathlib import Path
import csv
import gzip
import botocore.session
from botocore.stub import Stubber
import os
import threading
import json
import re
from oe_redis_utl import create_redis_client
from periods import calculate_layer_periods
from oe_best_redis import calculate_layer_best

TEST_RESPONSE = {
    'IsTruncated': False,
    'Name': 'test-bucket',
    'MaxKeys': 1000, 'Prefix': '',
    'Contents': [
        {'Key': 'epsg4326/', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"0"', 'Size': 0, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017001000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"11"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017001000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"12"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017001000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"13"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017002000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"21"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017002000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"22"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017002000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"23"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017003000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"31"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017003000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"32"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017003000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"33"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017004000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"41"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017004000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"42"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Test_Layer/2017/Test_Layer-2017004000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"43"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017001000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"11"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017001000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"12"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017001000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"13"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017002000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"21"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017002000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"22"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017002000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"23"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017003000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"31"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017003000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"32"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017003000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"33"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017004000000.idx', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"41"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017004000000.mrf', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"42"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
        {'Key': 'epsg4326/Other_Test_Layer/2017/Test_Layer-2017004000000.ppg', 'LastModified': datetime(2020, 3, 5, 3, 44, 38), 
         'ETag': '"43"', 'Size': 5335951, 'StorageClass': 'STANDARD'
        },
    ],
    'EncodingType': 'url',
    'ResponseMetadata': {
        'RequestId': 'abc123',
        'HTTPStatusCode': 200,
        'HostId': 'abc123'
    }
}


def keyMapper(acc, obj):
    keyElems = obj.split("/")

    if len(keyElems) <= 3:  # Don't do anything with static layers
        return acc

    proj = keyElems[0]
    layer_name = keyElems[1]
    year = keyElems[2]
    day = len(keyElems) == 4 and keyElems[3] or None
    filename = keyElems[-1]
    if Path(filename).suffix not in ['.ppg', '.pjg', '.ptf', '.pvt', '.lerc', '.lrc']:
        # ignore non-MRF data files
        return acc

    if not acc.get(proj):
        acc[proj] = {}

    if not acc[proj].get(layer_name):
        acc[proj][layer_name] = {'dates': set([])}

    date = filename.split("-")[-1].split(".")[0]
    try:
        datetime.strptime(date, '%Y%j%H%M%S')
        acc[proj][layer_name]['dates'].add(date)
    except ValueError:
        print('Incorrect date format for ' + filename + ', should be YYYYDDDhhmmss')
        return acc

    return acc

def find_latest_inventory_folder(conn, bucket, inventory_prefix):
    """
    Find the most recent inventory date folder.

    Args:
        conn: S3 client connection
        bucket: S3 bucket name
        inventory_prefix: Path prefix to search for date folders

    Returns:
        str: Path to the latest inventory folder, or None if not found
    """
    kwargs = {'Bucket': bucket, 'Prefix': inventory_prefix, 'Delimiter': '/'}
    try:
        resp = conn.list_objects_v2(**kwargs)
    except Exception as e:
        print(f'Error listing inventory folders: {e}')
        return None

    if 'CommonPrefixes' not in resp:
        print('No inventory date folders found')
        return None

    date_folders = []
    # Pattern to match YYYY-MM-DD or YYYY-MM-DDTHH-MMZ format
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})(T\d{2}-\d{2}Z)?')

    for prefix_obj in resp['CommonPrefixes']:
        prefix = prefix_obj['Prefix']
        folder_name = prefix.rstrip('/').split('/')[-1]

        # Check if folder name contains a date
        match = date_pattern.search(folder_name)
        if match:
            try:
                date_str = match.group(1)
                timestamp_str = match.group(2)

                # Parse with timestamp if present, otherwise just date
                if timestamp_str:
                    # Convert T00-00Z format to T00:00 for parsing
                    timestamp_normalized = timestamp_str.replace('-', ':').rstrip('Z')
                    full_datetime_str = date_str + timestamp_normalized
                    parsed_date = datetime.strptime(full_datetime_str, '%Y-%m-%dT%H:%M')
                else:
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d')

                date_folders.append((parsed_date, prefix))
            except ValueError as e:
                # Not a valid date, skip
                print(f'Invalid date format for {folder_name}: {e}')
                continue

    if not date_folders:
        print('No valid date folders found in inventory')
        return None

    # Get the most recent date folder
    date_folders.sort(key=lambda x: x[0], reverse=True)
    latest_date, latest_prefix = date_folders[0]
    print(f'Using latest inventory from: {latest_prefix}')

    return latest_prefix


def read_manifest_csv_files(conn, bucket, manifest_key):
    """
    Download and parse manifest.json to get list of CSV file keys.

    Args:
        conn: S3 client connection
        bucket: S3 bucket name
        manifest_key: S3 key path to manifest.json

    Returns:
        list: List of CSV file keys, or None if error
    """
    try:
        print(f'Downloading manifest: {manifest_key}')
        conn.download_file(bucket, manifest_key, 'tmpManifest.json')
    except Exception as e:
        print(f'Error downloading manifest.json: {e}')
        return None

    try:
        with open('tmpManifest.json', 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        print(f'Error reading manifest.json: {e}')
        return None
    finally:
        # Clean up manifest file
        if os.path.exists('tmpManifest.json'):
            os.remove('tmpManifest.json')

    if 'files' not in manifest:
        print('No "files" array found in manifest.json')
        return None

    csv_files = [file_obj['key'] for file_obj in manifest['files']
                 if file_obj['key'].endswith('.csv.gz')]
    print(f'Found {len(csv_files)} CSV files in manifest')

    return csv_files


def process_csv_file(conn, bucket, csv_key):
    """
    Download and read a single CSV inventory file.

    Args:
        conn: S3 client connection
        bucket: S3 bucket name
        csv_key: S3 key path to CSV file

    Returns:
        list: List of keys from the CSV file, or empty list if error
    """
    tmp_file = f'tmpInventory_{os.path.basename(csv_key)}'
    try:
        print(f'Processing: {csv_key}')
        conn.download_file(bucket, csv_key, tmp_file)

        with gzip.open(tmp_file, mode='rt') as f:
            reader = csv.reader(f)
            keys = list(map(lambda x: x[1], reader))
            print(f'  Added {len(keys)} keys from {os.path.basename(csv_key)}')
            return keys
    except Exception as e:
        print(f'  Error processing {csv_key}: {e}')
        return []
    finally:
        # Clean up temp file
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


def invenGetAllKeys(conn, bucket):
    """
    Get all S3 keys from inventory manifest.json and associated CSV files.

    Args:
        conn: S3 client connection
        bucket: S3 bucket name

    Returns:
        list: Combined list of all keys from inventory CSV files, or False if error
    """
    if bucket == 'test-bucket':
        return False
    if bucket != 'test-inventory':
        # Find the latest inventory date folder
        inventory_prefix = f'inventory/{bucket}/entire/'
        print(f'Looking for manifest.json in {inventory_prefix}')

        latest_prefix = find_latest_inventory_folder(conn, bucket, inventory_prefix)
        if not latest_prefix:
            return False

        # Read manifest.json to get CSV file list
        manifest_key = f'{latest_prefix}manifest.json'
        csv_files = read_manifest_csv_files(conn, bucket, manifest_key)
        if not csv_files:
            return False

        # Process all CSV files and combine keys
        all_keys = []
        for csv_key in csv_files:
            keys = process_csv_file(conn, bucket, csv_key)
            all_keys.extend(keys)

        print(f'Total keys collected: {len(all_keys)}')
        return all_keys
    if bucket == 'test-inventory':
        with gzip.open('tmpInventory.csv.gz', mode='rt') as f:
            reader = csv.reader(f)
            keys = list(map(lambda x: x[1], reader))
        return keys

def getAllKeys(conn, bucket):
    # https://alexwlchan.net/2017/07/listing-s3-keys/   
    keys = []
    kwargs = {'Bucket': bucket}
    print('Using boto list_objects_v2')
    while True:
        resp = conn.list_objects_v2(**kwargs)
        for obj in resp['Contents']:
            keys.append(obj['Key'])

        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break
    return keys

def getAllFiles(root_path):
    keys = []
    for path, _, files in os.walk(root_path):
        for name in files:
            # the key should start with the "epsg????" directory rather than the root path
            new_key = os.path.join(path, name).removeprefix(root_path).removeprefix('/')
            keys.append(new_key)
    return keys

def updateDateService(redis_uri,
                      redis_port,
                      bucket,
                      uri=None,
                      layer_name=None,
                      reproject=False,
                      check_exists=False,
                      s3_inventory=False):
    r = create_redis_client(host=redis_uri, port=redis_port)
    created = r.mget('created')[0]
    if created is None:
        created_time = datetime.now().timestamp()
        r.set('created', created_time)
        print('New database created ' + str(created_time))
    elif check_exists:
        print(f'Data already exists - skipping time scrape')
        return
    
    # Determine if we should be using a local path to a directory instead of a bucket
    local_path = False
    if uri is not None and not any(x in uri for x in ['http://', 'https://']):
        local_path = True
    # Use mock S3 if test
    elif bucket == 'test-bucket':
        s3 = botocore.session.get_session().create_client('s3')
        stubber = Stubber(s3)
        stubber.add_response('list_objects_v2', TEST_RESPONSE)
        stubber.activate()
    else:
        session = boto3.session.Session()
        s3 = session.client(service_name='s3', endpoint_url=uri)

    if bucket.startswith('http'):
        bucket = bucket.split('/')[2].split('.')[0]

    # delete date keys
    pattern = 'epsg????:layer:{}:dates'.format(layer_name if layer_name else '*')
    # Use scan_iter() to handle cluster cursors automatically
    all_keys = list(r.scan_iter(match=pattern))
    if len(all_keys) > 0:
        resp = r.unlink(*all_keys)
        print(f'{resp} of {len(all_keys)} keys unlinked {all_keys}')

    if local_path:
        objects = reduce(keyMapper, getAllFiles(uri), {})
    elif s3_inventory:
        invenKeys = invenGetAllKeys(s3, bucket)
        if(invenKeys):
            objects = reduce(keyMapper, invenKeys, {})
        else:
            objects = reduce(keyMapper, getAllKeys(s3, bucket), {})
    else:
        objects = reduce(keyMapper, getAllKeys(s3, bucket), {})


    scrape_threads    = []
    scrape_semaphore  = threading.BoundedSemaphore(10)

    def updateRedis(proj, s3_layer, sorted_parsed_dates):
        try:
            layers_to_update = [s3_layer]
            copy_layer=r.get(f'{proj}:layer:{s3_layer}:copy_dates')
            if copy_layer is not None:
                copy_layer=copy_layer.decode("utf-8")
                layers_to_update.append(copy_layer)
            for layer in layers_to_update:
                print(f'Configuring layer: {layer}')
                if layer == copy_layer:
                    print(f'Copying dates from {s3_layer}')

                for date in sorted_parsed_dates:
                    r.zadd(f'{proj}:layer:{layer}:dates', {date.isoformat(): 0})
                    calculate_layer_best(redis_cli=r, layer_key=f'{proj}:layer:{layer}', new_datetime=date.isoformat())
                    if reproject and str(proj) == 'epsg4326':
                        r.zadd(f'epsg3857:layer:{layer}:dates', {date.isoformat(): 0})
                        calculate_layer_best(redis_cli=r, layer_key=f'epsg3857:layer:{layer}', new_datetime=date.isoformat())

                calculate_layer_periods(redis_cli=r, layer_key=f'{proj}:layer:{layer}')
                if reproject and str(proj) == 'epsg4326':
                    calculate_layer_periods(redis_cli=r, layer_key=f'epsg3857:layer:{layer}')

                # check for best layer
                bestLayer=r.get(f'{proj}:layer:{layer}:best_layer')
                print("Best Layer: ", bestLayer)
                if bestLayer is not None:
                    bestLayer=bestLayer.decode("utf-8")
                    calculate_layer_periods(redis_cli=r, layer_key=f'{proj}:layer:{bestLayer}')
                    if reproject and str(proj) == 'epsg4326':
                        calculate_layer_periods(redis_cli=r, layer_key=f'epsg3857:layer:{bestLayer}')

        finally:
            scrape_semaphore.release()


    for proj, layers in objects.items():
        print(f'Configuring projection: {proj}')
        for layer, data in layers.items():
            if layer_name and layer != layer_name:
                continue

            sorted_parsed_dates = list(
                map(lambda date: datetime.strptime(date, '%Y%j%H%M%S'),
                    sorted(list(data['dates']))))
            scrape_semaphore.acquire()
            t = threading.Thread(target=updateRedis, args=(proj, layer, sorted_parsed_dates))
            t.start()
            scrape_threads.append(t)

    # Wait for all threads to complete
    while len(scrape_threads) > 0:
        completed = []

        for t in scrape_threads:
            if not t.is_alive():
                completed.append(t)
            else:
                t.join(10)

        for t in completed:
            scrape_threads.remove(t)


# Routine when run from CLI

parser = argparse.ArgumentParser(
    description='Rebuild date service from bucket contents')
parser.add_argument(
    '-b',
    '--bucket',
    default='gitc-deployment-mrf-archive',
    dest='bucket',
    help='bucket name',
    action='store')
parser.add_argument(
    '-p',
    '--port',
    dest='port',
    action='store',
    default=6379,
    help='redis port for database')
parser.add_argument(
    'redis_uri',
    metavar='REDIS_URI',
    type=str,
    nargs=1,
    help='URI for the Redis database')
parser.add_argument(
    '-s',
    '--uri',
    dest='uri',
    action='store',
    help='S3 URI (for use with localstack testing), or path to local directory to scrape from')
parser.add_argument(
    '-l',
    '--layer',
    dest='layer',
    action='store',
    help='Layer name to filter on')
parser.add_argument(
    '-r',
    '--reproject',
    default=False,
    dest='reproject',
    help='If layer uses epsg4326, add a record for epsg3857 as well',
    action='store_true')
parser.add_argument(
    '-c',
    '--check_exists',
    default=False,
    dest='check_exists',
    help='Check if data already exists; if it does, then don\'t rebuild',
    action='store_true')
parser.add_argument(
    '-i',
    '--s3_inventory',
    default=False,
    dest='s3_inventory',
    help='Check if s3 inventory exist; if it does use keys from inventory',
    action='store_true')

args = parser.parse_args()

updateDateService(
    args.redis_uri[0],
    args.port,
    args.bucket,
    uri=args.uri,
    layer_name=args.layer,
    reproject=args.reproject,
    check_exists=args.check_exists,
    s3_inventory=args.s3_inventory)
