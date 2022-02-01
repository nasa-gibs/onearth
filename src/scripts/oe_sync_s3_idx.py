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
This script synchronizes IDX files inside S3 tar balls with those on a file system.
Files on S3 will always act as the 'master' (i.e., files found on S3 that are not on the file system
will be downloaded, while files found on the file system but not on S3 will be deleted).
File modifications are not detected. Use --force to overwrite existing files.
"""
import os
import boto3, botocore
from functools import reduce
from pathlib import Path
import argparse
import threading
import re
import hashlib


def keyMapper(acc, obj):
    keyElems = obj['Key'].split("/")

    filename = keyElems[-1]
    if len(keyElems) > 1:
        proj = keyElems[0]
        if len(keyElems) > 2:
            layer_name = keyElems[1]
        else:
            layer_name = None
        if len(keyElems) > 3:
            year = keyElems[2]
            if len(keyElems) > 4:
                day = keyElems[3]
            else:
                day = None
        else:
            year = None
            day = None

        if layer_name is not None:
            if not acc.get(proj):
                acc[proj] = {}

            if not acc[proj].get(layer_name):
                acc[proj][layer_name] = {'idx': set([])}

            if filename.endswith('.idx'):
                idx = (year + '/' if year is not None else '') + (day + '/' if day is not None else '') + filename
                acc[proj][layer_name]['idx'].add(idx)

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


def listAllFiles(dir_proj_layer, prefix):
    prefixElems = prefix.split("/") if prefix is not None else []

    # If there are 1 or 2 prefix elements, then we're not filtering the object year or "file" name, so take them all
    if len(prefixElems) <= 2:
        fs_list = list(Path(dir_proj_layer).rglob("*.[iI][dD][xX]"))

    # Else if there are 3 prefix elements, then we're filtering on the object year
    elif len(prefixElems) == 3:
        fs_list = list(Path(os.path.join(dir_proj_layer, prefixElems[2])).rglob("*.[iI][dD][xX]"))

    # Else if there are 4 prefix elements, then we're filtering on the object year _and_ "file" name
    elif len(prefixElems) == 4:
        fs_list = list(Path(os.path.join(dir_proj_layer, prefixElems[2])).rglob(prefixElems[3] + "*.[iI][dD][xX]"))

    return [str(f).replace(dir_proj_layer + '/', '') for f in fs_list]


def calculate_s3_etag(file_path, chunk_size=8 * 1024 * 1024):
    md5s = []

    with open(file_path, 'rb') as fp:
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            md5s.append(hashlib.md5(data))

    if len(md5s) < 1:
        return '"{}"'.format(hashlib.md5().hexdigest())

    if len(md5s) == 1:
        return '"{}"'.format(md5s[0].hexdigest())

    digests = b''.join(m.digest() for m in md5s)
    digests_md5 = hashlib.md5(digests)
    return '"{}-{}"'.format(digests_md5.hexdigest(), len(md5s))


def syncIdx(bucket,
            dir,
            prefix,
            force,
            checksum,
            dry_run,
            s3_uri=None):

    session = boto3.session.Session()

    aws_config = botocore.config.Config(
        connect_timeout=10,
        read_timeout=30,
        max_pool_connections=10,
        retries=dict(max_attempts=2))

    s3 = session.client(service_name='s3', endpoint_url=s3_uri, config=aws_config)

    if bucket.startswith('http'):
        bucket = bucket.split('/')[2].split('.')[0]
    objects = reduce(keyMapper, getAllKeys(s3, bucket, prefix), {})

    sync_threads    = []
    sync_semaphore  = threading.BoundedSemaphore(10)


    def match_checksums(idx_prefix, idx_filepath):
        response = s3.head_object(Bucket=bucket, Key=idx_prefix)
        s3_cksum = response["ETag"].replace("\"","").strip()

        m = re.match("[a-f0-9]*-([0-9]*)", s3_cksum)
        if m:
            bytesPerPart   = float(os.stat(idx_filepath).st_size) / float(m.group(1))
            bytesChunkSize = bytesPerPart + 1048576.0 - (bytesPerPart % 1048576.0)
            mbChunkSize    = int(bytesChunkSize / float(1024 *  1024))

            '''
            print("Calculating multi-part checksum with " + m.group(1) + \
                  " parts and " + str(mbChunkSize) + "MB chunk size for file of size " + \
                  str(os.stat(idx_filepath).st_size) + " bytes")
            '''

            file_cksum = calculate_s3_etag(idx_filepath, mbChunkSize * 1024 * 1024).replace("\"","").strip()
        else:
            with open(idx_filepath, 'rb') as idxFile:
                file_cksum = hashlib.md5(idxFile.read()).hexdigest().replace("\"","").strip()

        return file_cksum == s3_cksum

    def copyObject(idx_prefix, idx_filepath):
        try:
            print("Downloading {0} to {1}".format(idx_prefix, idx_filepath))
            if not dry_run:
                s3.download_file(bucket, idx_prefix, idx_filepath)
        except botocore.exceptions.ClientError as e:
            print(e)
        finally:
            sync_semaphore.release()


    def deleteObject(idx_filepath):
        try:
            if os.path.isfile(idx_filepath):
                print("Deleting file not found on S3: {0}".format(idx_filepath))
                if not dry_run:
                    os.remove(idx_filepath)
        finally:
            sync_semaphore.release()


    for proj, layers in objects.items():
        print(f'Configuring projection: {proj}')

        dir_proj = os.path.join(dir, proj)
        if not os.path.isdir(dir_proj) and not dry_run:
            os.makedirs(dir_proj)

        for layer, data in layers.items():
            print(f'Configuring layer: {layer}')
            dir_proj_layer = os.path.join(dir, proj, layer)

            if not os.path.isdir(dir_proj_layer) and not dry_run:
                os.makedirs(dir_proj_layer)

            # Find existing files on file system
            fs_files = listAllFiles(dir_proj_layer, prefix)

            # Build list of S3 index files
            s3_objects = [v for v in data['idx']]

            # Determine what needs to be sync'd. Note we don't care about existing files when forcing overwrite
            if force:
                idx_to_sync = s3_objects
            else:
                idx_to_sync = list(set(s3_objects) - set(fs_files))

            idx_to_delete = list(set(fs_files) - set(s3_objects))

            # Copy files from S3 that aren't on file system
            for s3_object in idx_to_sync:
                idx_filepath = os.path.join(dir_proj_layer, s3_object)
                idx_prefix = "{0}/{1}/{2}".format(proj, layer, s3_object).replace('//', '/')

                idx_filedir = os.path.dirname(idx_filepath)
                if not os.path.isdir(idx_filedir) and not dry_run:
                    os.makedirs(idx_filedir)

                sync_semaphore.acquire()
                t = threading.Thread(target=copyObject, args=(idx_prefix, idx_filepath))
                t.start()
                sync_threads.append(t)

            # Delete files from file system that aren't on S3
            for fs_file in idx_to_delete:
                idx_filepath = os.path.join(dir_proj_layer, fs_file)

                sync_semaphore.acquire()
                t = threading.Thread(target=deleteObject, args=(idx_filepath,))
                t.start()
                sync_threads.append(t)

            # Evaluate checksum of non-deleted index files already on disk against S3 object, if not forcing and
            # user has requested checksum comparison
            if not force and checksum:
                for fs_file in list(set(fs_files) - set(idx_to_delete)):
                    idx_filepath = os.path.join(dir_proj_layer, fs_file)
                    idx_prefix = "{0}/{1}/{2}".format(proj, layer, fs_file).replace('//', '/')

                    if not match_checksums(idx_prefix, idx_filepath):
                        sync_semaphore.acquire()
                        t = threading.Thread(target=copyObject, args=(idx_prefix, idx_filepath))
                        t.start()
                        sync_threads.append(t)

    # Wait for all threads to complete
    while len(sync_threads) > 0:
        completed = []

        for t in sync_threads:
            if not t.is_alive():
                completed.append(t)
            else:
                t.join(10)

        for t in completed:
            sync_threads.remove(t)


# Routine when run from CLI

parser = argparse.ArgumentParser(
    description='Rebuilds IDX files on system from S3 bucket contents.')
parser.add_argument(
    '-b',
    '--bucket',
    default='gitc-deployment-mrf-archive',
    dest='bucket',
    help='bucket name',
    action='store')
parser.add_argument(
    '-d',
    '--dir',
    default='/onearth/idx',
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
    '-c',
    '--checksum',
    default=False,
    dest='checksum',
    help='Evaluate checksum of local file against s3 object and update even mismatched',
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

syncIdx(args.bucket,
        args.dir,
        args.prefix,
        args.force,
        args.checksum,
        args.dry_run,
        s3_uri=args.s3_uri)