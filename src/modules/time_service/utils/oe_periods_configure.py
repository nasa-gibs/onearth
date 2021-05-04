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
This script loads custom period configurations from layer configuration files.
"""

import re
import sys
import argparse
import yaml
import redis
import os
from pathlib import Path


# Utility functions

def strip_trailing_slash(string):
    return re.sub(r'/$', '', string)


def format_time_key(time_string):
    return int(''.join(filter(str.isdigit, time_string)))


def get_layer_config(layer_config_path):
    print(f"Reading {layer_config_path}")
    with layer_config_path.open() as f:
        config = yaml.load(f.read())
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
        layer_configs = []
        for filepath in sorted(layer_source.iterdir()):
            if filepath.is_file() and filepath.name.endswith('.yaml'):
                try:
                    layer_configs.append(get_layer_config(filepath))
                except Exception as e:
                    print(f"Can't read layer config: {layer_source} \n{e}")
        return layer_configs


# Main configuration functions

def load_time_configs(layer_configs, redis_uri, redis_port, tag=None, generate_periods=False):
    r = redis.Redis(host=redis_uri, port=redis_port)
    with open(os.path.dirname(os.path.realpath(__file__)) + '/periods.lua',
              'r') as f:
        lua_script = f.read()
    date_script = r.register_script(lua_script)
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
            key = tag_str + 'layer:' + str(layer_config['config']['layer_id'])
            key_config = key + ':config'
            key_config_wm = key_config.replace('epsg4326', 'epsg3857')
            # check whether we have a single string or list of values
            if isinstance(layer_config['config']['time_config'], str):
                time_configs = [layer_config['config']['time_config']]
            else:
                time_configs = layer_config['config']['time_config']

            # clear out existing time configs for layer
            r.delete(key_config)
            if 'epsg4326' in key:
                # delete key for reproject as well
                r.delete(key_config_wm)

            # add all time configs for layer
            for time_config in time_configs:
                print('Adding ' + time_config + ' to ' + key_config)
                r.sadd(key_config, time_config)
                # duplicate config for epsg3857 for reproject
                if 'epsg4326' in key:
                    print('Adding ' + time_config + ' to ' + key_config_wm)
                    r.sadd(key_config_wm, time_config)

            # refresh time periods in redis
            if generate_periods:
                print('Generating periods for ' + key)
                date_script(keys=[key])
                # generate periods for reproject as well
                if 'epsg4326' in key:
                    key_wm = key.replace('epsg4326', 'epsg3857')
                    print('Generating periods for ' + key_wm)
                    date_script(keys=[key_wm])
        else:
            print('No time configuration found for ' +
                  str(layer_config['path'].absolute()))

        if 'best_config' in layer_config['config'].keys():
            best_config = key + ':best'
            best_config_wm = best_config.replace('epsg4326', 'epsg3857')
            print('Processing best_config', best_config)

            # clear out existing time configs for layer
            r.delete(best_config)
            if 'epsg4326' in key:
                # delete key for reproject as well
                r.delete(best_config_wm)

            # process each best_config item
            for key, value in layer_config['config']['best_config'].items():
                print('Adding ' + f'{key}: {value}' + ' to ' + best_config)
                r.zadd(best_config, {value: format_time_key(key)})
                # duplicate config for epsg3857 for reproject
                if 'epsg4326' in key:
                    print('Adding ' + f'{key}: {value}' + ' to ' + best_config_wm)
                    r.zadd(best_config_wm, {value: format_time_key(key)})


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Loads custom period configurations')
    parser.add_argument('-g', '--generate_periods',
                        dest='generate_periods',
                        default=False,
                        help='Generate periods for each layer based on config values',
                        action='store_true')
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
                      args.tag,
                      args.generate_periods)
