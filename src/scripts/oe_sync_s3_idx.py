#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
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
import boto3
from functools import reduce
from datetime import datetime
from pathlib import Path
import argparse
import tarfile
import shutil

def keyMapper(acc, obj):
    keyElems = obj['Key'].split("/")

    filename = keyElems[-1]
    if len(keyElems) > 1:
        proj = keyElems[0]
        if len(keyElems) > 2:
            layer_name = keyElems[1]
        else:
            layer_name = ''
        if len(keyElems) > 3:
            year = keyElems[2]
            if len(keyElems) > 4:
                day = keyElems[3]
            else:
                day = None
        else:
            year = None
            day = None

        if not acc.get(proj):
            acc[proj] = {}
            
        if not acc[proj].get(layer_name):
            acc[proj][layer_name] = {'idx': set([])}
    
        if filename.endswith('.idx.tgz') or filename.endswith('.idx'):
            idx = (year + '/' if year is not None else '') + (day + '/' if day is not None else '') + filename
            acc[proj][layer_name]['idx'].add(idx)

    return acc


# https://alexwlchan.net/2017/07/listing-s3-keys/
def getAllKeys(conn, bucket, prefix):
    keys = []
    kwargs = {'Bucket': bucket, 'Prefix': prefix}

    while True:
        resp = conn.list_objects_v2(**kwargs)
        keys = keys + resp['Contents']

        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break
    return keys


def syncIdx(bucket,
            dir,
            prefix,
            force,
            s3_uri=None):
    session = boto3.session.Session()
    s3 = session.client(service_name='s3', endpoint_url=s3_uri)

    if bucket.startswith('http'):
        bucket = bucket.split('/')[2].split('.')[0]
    objects = reduce(keyMapper, getAllKeys(s3, bucket, prefix), {})

    for proj, layers in objects.items():
        print(f'Configuring projection: {proj}')
        dir_proj = dir + '/' + proj
        if os.path.isdir(dir_proj) == False:
            os.makedirs(dir_proj)
            
        for layer, data in layers.items():
            print(f'Configuring layer: {layer}')
            dir_proj_layer = dir + '/' + proj + '/' + layer
            if os.path.isdir(dir_proj_layer) == False:
                os.makedirs(dir_proj_layer)
                
            # Find existing files on file system
            if force: # we don't care about existing files when forcing overwrite
                fs_files = []
            else:
                fs_list = list(Path(dir_proj_layer).rglob("*.[iI][dD][xX]"))
                fs_files = [str(f).replace(dir_proj_layer+'/','') for f in fs_list]
            s3_files = [v for v in data['idx']]
            # We need another list for the extracted names
            s3_files_idx = [v.replace('.tgz','') for v in data['idx']]
            
            # Copy files from S3 that aren't on file system
            for s3_file in list(set(s3_files_idx) - set(fs_files)):
                if s3_file + '.tgz' in s3_files:
                    s3_file = s3_file + '.tgz'
                filepath = os.path.dirname(dir_proj_layer + '/' + s3_file)
                if os.path.isdir(filepath) == False:
                    os.makedirs(filepath)
                print(f'Downloading file: {proj}/{layer}/{s3_file}')
                filename = dir_proj_layer + '/' + s3_file
                s3.download_file(bucket, str(proj + '/' + layer + '/' + s3_file).replace('//','/'), filename)
                if filename.endswith('.tgz'):
                    print(f'Extracting file: {filename}')
                    tar = tarfile.open(filename, "r:gz")
                    os.mkdir(filepath+'/tmp')
                    tar.extractall(path=filepath+'/tmp')
                    tar.close()
                    try:
                        os.rename(filepath+'/tmp/'+os.listdir(filepath+'/tmp')[0], filename.replace('.tgz',''))
                    except Exception as e:
                        print(f'ERROR extracting file: {filename}')
                    shutil.rmtree(filepath+'/tmp')
                    os.remove(filename)
                
            # Delete files from file system that aren't on S3
            for fs_file in list(set(fs_files) - set(s3_files_idx)):
                fs_idx = dir_proj_layer + '/' + fs_file.replace('.tgz','')
                if os.path.isfile(fs_idx):
                    print(f'Deleting file not found on S3: {fs_idx}')
                    os.remove(fs_idx)
                

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
    s3_uri=args.s3_uri)