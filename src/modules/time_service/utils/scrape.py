import boto3
from functools import reduce
from datetime import datetime
import redis
import argparse


def keyMapper(acc, obj):
    keyElems = obj['Key'].split("/")

    if len(keyElems) == 3:  # Don't do anything with static layers
        return acc

    proj = keyElems[0]
    layer_name = keyElems[1]
    year = keyElems[2]
    day = len(keyElems) == 4 and keyElems[3] or None
    filename = keyElems[-1]

    if not acc.get(proj):
        acc[proj] = {}

    if not acc[proj].get(layer_name):
        acc[proj][layer_name] = {'dates': set([])}

    date = filename.split("-")[-1].split(".")[0]

    acc[proj][layer_name]['dates'].add(date)

    return acc


def updateDateService(redis_uri, redis_port, bucket, s3_uri=None):
    session = boto3.session.Session()

    s3 = session.client(service_name='s3', endpoint_url=s3_uri)

    objects = reduce(keyMapper,
                     s3.list_objects_v2(Bucket=bucket)['Contents'], {})

    r = redis.Redis(host=redis_uri, port=redis_port)

    for proj, layers in objects.items():
        print(f'Configuring projection: {proj}')
        for layer, data in layers.items():
            sorted_parsed_dates = list(
                map(lambda date: datetime.strptime(date, '%Y%j%H%M%S'),
                    sorted(list(data['dates']))))

            # Set default to latest date
            default = sorted_parsed_dates[-1].isoformat()

            print(f'Configuring layer: {layer}')

            r.set(f'{proj}:layer:{layer}:default', default)
            for date in sorted_parsed_dates:
                r.sadd(f'{proj}:layer:{layer}:dates', date.isoformat())

            with open('periods.lua', 'r') as f:
                lua_script = f.read()

            date_script = r.register_script(lua_script)
            date_script(keys=[f'{proj}:layer:{layer}'])


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

args = parser.parse_args()

updateDateService(
    args.redis_uri[0], args.port, args.bucket, s3_uri=args.s3_uri)