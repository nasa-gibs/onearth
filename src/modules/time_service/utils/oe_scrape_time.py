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
    if Path(filename).suffix not in ['.ppg', '.pjg', '.ptf', '.pvt', '.lerc']:
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


def invenGetAllKeys(conn, bucket):
    if (bucket == 'test-bucket'):
        return False
    if (bucket != 'test-inventory'):
        keys = []
        kwargs = {'Bucket': bucket, 'Prefix': 'inventory/'+bucket+'/entire/data/'}
        respInv = conn.list_objects_v2(**kwargs)

        try:
            objects = respInv['Contents']
        except KeyError:
            return False
        print('Using S3 Inventory')
        lastest_inventory = max(objects, key=lambda x: x['LastModified'])
        if not lastest_inventory['Key'].endswith('csv.gz'):
            print('S3 Inventory csv file not found!')
            return False
        conn.download_file(bucket, lastest_inventory['Key'], 'tmpInventory.csv.gz')
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


def updateDateService(redis_uri,
                      redis_port,
                      bucket,
                      s3_uri=None,
                      layer_name=None,
                      reproject=False,
                      check_exists=False,
                      s3_inventory=False):
    r = redis.Redis(host=redis_uri, port=redis_port)
    created = r.mget('created')[0]
    if created is None:
        created_time = datetime.now().timestamp()
        r.set('created', created_time)
        print('New database created ' + str(created_time))
    elif check_exists:
        print(f'Data already exists - skipping time scrape')
        return

    # Use mock S3 if test
    if bucket == 'test-bucket':
        s3 = botocore.session.get_session().create_client('s3')
        stubber = Stubber(s3)
        stubber.add_response('list_objects_v2', TEST_RESPONSE)
        stubber.activate()
    else:
        session = boto3.session.Session()
        s3 = session.client(service_name='s3', endpoint_url=s3_uri)

    if bucket.startswith('http'):
        bucket = bucket.split('/')[2].split('.')[0]

    # delete date keys
    pattern = 'epsg????:layer:*:dates'
    count, keys = r.scan(cursor=0, match=pattern)
    if(len(keys) > 0):
        resp = r.unlink(*keys)
        print(f'{resp} of {len(keys)} keys unlinked {keys}')
    while count != 0:
        count, keys = r.scan(cursor=count, match=pattern)
        if(len(keys) > 0):
            resp = r.unlink(*keys)
            print(f'{resp} of {len(keys)} keys unlinked {keys}')

    if s3_inventory:
        invenKeys = invenGetAllKeys(s3, bucket)
        if(invenKeys):
            objects = reduce(keyMapper, invenKeys, {})
        else:
            objects = reduce(keyMapper, getAllKeys(s3, bucket), {})
    else:
        objects = reduce(keyMapper, getAllKeys(s3, bucket), {})

    with open(os.path.dirname(os.path.realpath(__file__)) + '/periods.lua',
              'r') as f:
        lua_script = f.read()
    date_script = r.register_script(lua_script)

    with open(os.path.dirname(os.path.realpath(__file__)) + '/best.lua',
              'r') as f:
        lua_script2 = f.read()
    best_script = r.register_script(lua_script2)

    scrape_threads    = []
    scrape_semaphore  = threading.BoundedSemaphore(10)

    def updateRedis(proj, layer, sorted_parsed_dates):
        try:
            print(f'Configuring layer: {layer}')

            for date in sorted_parsed_dates:
                r.zadd(f'{proj}:layer:{layer}:dates', {date.isoformat(): 0})
                best_script(keys=[f'{proj}:layer:{layer}'], args=[date.isoformat()])
                if reproject and str(proj) == 'epsg4326':
                    r.zadd(f'epsg3857:layer:{layer}:dates', {date.isoformat(): 0})
                    best_script(keys=[f'epsg3857:layer:{layer}'], args=[date.isoformat()])

            date_script(keys=[f'{proj}:layer:{layer}'])
            if reproject and str(proj) == 'epsg4326':
                date_script(keys=[f'epsg3857:layer:{layer}'])

            # check for best layer
            bestLayer=r.get(f'{proj}:layer:{layer}:best_layer')
            print("Best Layer: ", bestLayer)
            if bestLayer is not None:
                bestLayer=bestLayer.decode("utf-8")
                date_script(keys=[f'{proj}:layer:{bestLayer}'])
                if reproject and str(proj) == 'epsg4326':
                    date_script(keys=[f'epsg3857:layer:{bestLayer}'])

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
    '--s3_uri',
    dest='s3_uri',
    action='store',
    help='S3 URI -- for use with localstack testing')
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
    s3_uri=args.s3_uri,
    layer_name=args.layer,
    reproject=args.reproject,
    check_exists=args.check_exists,
    s3_inventory=args.s3_inventory)
