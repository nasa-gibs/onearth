#!/usr/bin/env python3

# Copyright (c) 2002-2020, California Institute of Technology.

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
This script loads custom period configurations from layer configuration files.
"""

import re
import sys
import argparse
import yaml
import redis
from pathlib import Path


# Utility functions

def strip_trailing_slash(string):
    return re.sub(r'/$', '', string)


def get_layer_config(layer_config_path):
    with layer_config_path.open() as f:
        config = yaml.safe_load(f.read())
    return {'path': layer_config_path, 'config': config}


def get_layer_configs(endpoint_config):
    try:
        layer_source = Path(endpoint_config['layer_config_source'])
    except KeyError:
        print("\nMust specify 'layer_config_source'!")
        sys.exit()

    # Build all source configs - traversing down a single directory level
    if not layer_source.exists():
        print(f"Can't find specified layer config location: {layer_source}")
        sys.exit()
    if layer_source.is_file():
        return [get_layer_config(layer_source)]
    elif layer_source.is_dir():
        return [
            get_layer_config(filepath) for filepath in layer_source.iterdir()
            if filepath.is_file() and filepath.name.endswith('.yaml')
        ]


# Main configuration functions

def load_time_configs(layer_configs, redis_uri, redis_port, tag=None):
    r = redis.Redis(host=redis_uri, port=redis_port)
    for layer_config in layer_configs:
        config_path = str(layer_config['path'].absolute())
        print(f'Adding time period configuration from {config_path}')
        if tag is None:
            # attempt to detect tags based on filepath if none provided
            if 'all/' in config_path:
                tag = ':all'
            elif 'best/' in config_path:
                tag = ':best'
            elif 'nrt/' in config_path:
                tag = ':nrt'
            elif 'std/' in config_path:
                tag = ':std'
            if tag is not None and \
               'projection' in layer_config['config'].keys():
                tag = str(layer_config['config']['projection']). \
                    lower().replace(':', '') + tag
        if 'time_config' in layer_config['config'].keys():
            tag_str = f'{tag}:' if tag else ''
            key = tag_str + 'layer:' + \
                str(layer_config['config']['layer_id']) + ':config'
            print('Adding ' +
                  str(layer_config['config']['time_config']) +
                  ' to ' + key)
            r.set(key, str(layer_config['config']['time_config']))
            # duplicate config for epsg3857 for reproject
            if 'epsg4326' in key:
                key = key.replace('epsg4326', 'epsg3857')
            print('Adding ' +
                  str(layer_config['config']['time_config']) +
                  ' to ' + key)
            r.set(key, str(layer_config['config']['time_config']))
        else:
            print('No time configuration found for ' +
                  str(layer_config['path'].absolute()))


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Loads custom period configurations')
    parser.add_argument('-e', '--endpoint_config',
                        dest='endpoint_config',
                        metavar='ENDPOINT_CONFIG',
                        type=str,
                        help='an endpoint config YAML file')
    parser.add_argument('-p', '--port',
                        dest='port',
                        action='store',
                        default=6379,
                        help='redis port for database')
    parser.add_argument('-r', '--redis_uri',
                        dest='redis_uri',
                        metavar='REDIS_URI',
                        type=str,
                        help='URI for the Redis database')
    parser.add_argument('-t', '--tag',
                        dest='tag',
                        action='store',
                        help='Classification tag (nrt, best, std, etc.)')
    args = parser.parse_args()
    print(f'Adding time configurations for endpoint {args.endpoint_config}')
    endpoint_config = yaml.safe_load(Path(args.endpoint_config).read_text())
    layer_configs = get_layer_configs(endpoint_config)
    load_time_configs(layer_configs,
                      args.redis_uri,
                      args.port,
                      args.tag)
