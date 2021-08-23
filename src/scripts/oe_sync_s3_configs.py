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
This script synchronizes OnEarth config files on S3 with those on a file system.
Files on S3 will always act as the 'master' (i.e., files found on S3 that are not on the file system
will be downloaded, while files found on the file system but not on S3 will be deleted).
File modifications are not detected. Use --force to overwrite existing files.
"""
import argparse
import os
import boto3
from botocore.exceptions import ClientError
from functools import reduce
from pathlib import Path


def keyMapper(acc, obj):
    keyElems = obj['Key'].split("/")
    filename = keyElems[-1]

    if not acc.get('config'):
        acc = {'config': set([])}

    # works with yaml/xml/json/html configs or images (e.g., empty tiles)
    ext = ['.yaml', '.xml', '.html', '.jpeg', '.jpg', '.png', '.svg', '.header', '.txt', '.sym', '.json']
    if filename.endswith(tuple(ext)):
        acc['config'].add(filename)

    return acc


# https://alexwlchan.net/2017/07/listing-s3-keys/
def getAllKeys(conn, bucket, prefix):
    keys = []
    kwargs = {'Bucket': bucket, 'Prefix': prefix}

    while True:
        resp = conn.list_objects_v2(**kwargs)
        keys = keys + (resp['Contents'] if 'Contents' in resp else [])

        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break
    return keys


def syncConfigs(bucket,
                dir,
                prefix,
                force,
                dry_run,
                s3_uri=None):
    session = boto3.session.Session()
    s3 = session.client(service_name='s3', endpoint_url=s3_uri)

    if bucket.startswith('http'):
        bucket = bucket.split('/')[2].split('.')[0]
    if prefix.endswith('/'):
        prefix = prefix[:-1]
    objects = reduce(keyMapper, getAllKeys(s3, bucket, prefix), {})

    for data, config in objects.items():
        print(f'Loading configs from: {prefix}')

        # Find existing files on file system
        if force:  # we don't care about existing files when forcing overwrite
            fs_files = []
        else:
            fs_list = list(Path(dir).rglob("*.[yY][aA][mM][lL]"))
            fs_files = [str(f).split('/')[-1] for f in fs_list]
        s3_files = [v for v in config]

        # Copy files from S3 that aren't on file system
        for s3_file in list(set(s3_files) - set(fs_files)):
            if dir.endswith('index.html') and s3_file == ('index.html'):  # avoid issues with index.html files
                s3_file = ''
            else:
                s3_file = '/' + s3_file
            filename = dir + s3_file
            print(f'Downloading file: {prefix}{s3_file}')

            if not dry_run:
                try:
                    s3.download_file(bucket, prefix + s3_file, filename)
                except ClientError as e:  # we want to continue if a file download fails
                    print(e)

        # Delete files from file system that aren't on S3
        for fs_file in list(set(fs_files) - set(s3_files)):
            if os.path.isfile(fs_file):
                print(f'Deleting file not found on S3: {fs_file}')

                if not dry_run:
                    os.remove(fs_file)


# Routine when run from CLI

parser = argparse.ArgumentParser(
    description='Downloads OnEarth layer configurations from S3 bucket contents.')
parser.add_argument(
    '-b',
    '--bucket',
    default='gitc-dev-onearth-configs',
    dest='bucket',
    help='bucket name',
    action='store')
parser.add_argument(
    '-d',
    '--dir',
    default='/etc/onearth/config',
    dest='dir',
    help='Directory on file system to sync',
    action='store')
parser.add_argument(
    '-f',
    '--force',
    default=False,
    dest='force',
    help='Force update even if file exists',
    action='store_true')
parser.add_argument(
    '-n',
    '--dry-run',
    default=False,
    dest='dry_run',
    help='Perform a trial run with no changes made',
    action='store_true')
parser.add_argument(
    '-p',
    '--prefix',
    dest='prefix',
    action='store',
    default='',
    help='S3 prefix to use')
parser.add_argument(
    '-s',
    '--s3_uri',
    dest='s3_uri',
    action='store',
    help='S3 URI -- for use with localstack testing')

args = parser.parse_args()

syncConfigs(args.bucket,
            args.dir,
            args.prefix,
            args.force,
            args.dry_run,
            s3_uri=args.s3_uri)
