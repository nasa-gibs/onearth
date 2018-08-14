#!/usr/bin/env python

# Copyright (c) 2002-2018, California Institute of Technology.
# All rights reserved.  Based on Government Sponsored Research under contracts NAS7-1407 and/or NAS7-03001.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#   3. Neither the name of the California Institute of Technology (Caltech), its operating division the Jet Propulsion Laboratory (JPL),
#      the National Aeronautics and Space Administration (NASA), nor the names of its contributors may be used to
#      endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE CALIFORNIA INSTITUTE OF TECHNOLOGY BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
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
This script configures WMTS and TWMS layers for use with the OnEarth 2 Apache modules.
"""

import os
import re
import sys
import argparse
import yaml
from pathlib import Path
from urllib.parse import urlsplit, urlparse
import requests

# Config templates

PROXY_PATH = '/oe2-tile-service-proxy'

MAIN_APACHE_CONFIG_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !wmts_wrapper_module>
        LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<IfModule !receive_module>
        LoadModule receive_module modules/mod_receive.so
</IfModule>

<Directory {endpoint_path}>
        WMTSWrapperRole root
</Directory>
"""

TWMS_MODULE_TEMPLATE = """<IfModule !twms_module>
    LoadModule twms_module modules/mod_twms.so
</IfModule>
"""

PROXY_MODULE_TEMPLATE = """<IfModule !proxy_module>
    LoadModule proxy_module modules/mod_proxy.so
</IfModule>
"""

DATE_SERVICE_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_date_service_uri} {date_service_uri}
ProxyPassReverse {local_date_service_uri} {date_service_uri}
"""

DATA_FILE_PROXY_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_data_file_uri} {data_file_uri}
ProxyPassReverse {local_data_file_uri} {data_file_uri}
"""

LAYER_APACHE_CONFIG_TEMPLATE = """<Directory {endpoint_path}/{layer_id}>
    WMTSWrapperRole layer
</Directory>

<Directory {endpoint_path}/{layer_id}/default>
        WMTSWrapperRole style
        WMTSWrapperEnableTime {time_enabled}
</Directory>

<Directory {endpoint_path}/{layer_id}/default/{tilematrixset}>
        MRF On
        MRF_ConfigurationFile {config_file_path}
        MRF_RegExp {alias}
        WMTSWrapperRole tilematrixset
        WMTSWrapperEnableYearDir {year_dir}
        WMTSWrapperLayerAlias {alias}
</Directory>
"""

MOD_TWMS_CONFIG_TEMPLATE = """<Directory {endpoint_path}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {endpoint_path}/twms/${layer}/twms.config
</Directory>
"""

LAYER_MOD_MRF_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
IndexFile {idx_path}"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
BoundingBox {bbox}
SourcePath {source_path}
SourcePostfix {source_postfix}
"""

MIME_TO_EXTENSION = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tiff',
    'image/lerc': '.lerc',
    'application/x-protobuf;type=mapbox-vector': '.pbf',
    'application/vnd.mapbox-vector-tile': '.mvt'
}

MIME_TO_MRF_EXTENSION = {
    'image/png': '.ppg',
    'image/jpeg': '.pjg',
    'image/tiff': '.ptf',
    'image/lerc': '.lerc',
    'application/x-protobuf;type=mapbox-vector': '.pvt',
    'application/vnd.mapbox-vector-tile': '.pvt'
}

# Utility functions


def format_date_service_uri(uri):
    return '/oe2-date-service-proxy-' + bulk_replace(urlparse(uri).netloc, ((':', '-'), ('.', '-')))


def generate_string_from_set(sep, string_set):
    strings = []
    for pair in string_set:
        if pair[1]:
            strings.append(pair[0])
    return sep.join(strings)


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str


def get_proxy_paths(layers):
    proxy_paths = []
    for layer_config in layers:
        data_file_uri = layer_config['config'][
            'source_mrf'].get('data_file_uri')
        if not data_file_uri:
            continue
        url_parts = urlsplit(data_file_uri)
        remote_path = f'{url_parts.scheme}://{url_parts.netloc}'
        if not any(path for path in proxy_paths if path['remote_path'] == remote_path):
            proxy_paths.append({'local_path': f'{PROXY_PATH}-{url_parts.netloc.replace(".", "-")}', 'remote_path': remote_path})
    return proxy_paths


def make_proxy_config(proxy_path):
    return bulk_replace(DATA_FILE_PROXY_TEMPLATE, [
        ('{data_file_uri}', proxy_path['remote_path']),
        ('{local_data_file_uri}', proxy_path['local_path'])])


def format_source_uri_for_proxy(uri, proxy_paths):
    for proxy_path in proxy_paths:
        if proxy_path['remote_path'] in uri:
            return uri.replace(proxy_path['remote_path'], proxy_path['local_path'])


# Main configuration functions

def make_apache_config(endpoint_config, layer_configs):
    # Only set up the date service proxy if there are non-static layers
    date_service_needed = any(layer_config.get('static') is False
                              for layer_config in layer_configs)

    datafile_proxy_needed = any(
        layer_config.get('data_file_uri') for layer_config in layer_configs)

    try:
        endpoint_path = endpoint_config['endpoint_config_base_location']
        if date_service_needed:
            date_service_uri = endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    # Set up proxies for date service and data files (if needed)
    proxy_config = ''
    proxy_needed = date_service_needed or datafile_proxy_needed
    if proxy_needed:
        proxy_config = PROXY_MODULE_TEMPLATE

    date_service_config = ''
    if date_service_needed:
        date_service_config = DATE_SERVICE_TEMPLATE.replace(
            '{date_service_uri}', date_service_uri).replace('{local_date_service_uri}', format_date_service_uri(date_service_uri))

    datafile_proxy_config = ''
    if datafile_proxy_needed:
        datafile_proxy_config = '\n'.join(
            [make_proxy_config(config) for config in endpoint_config['proxy_paths']])

    main_apache_config = MAIN_APACHE_CONFIG_TEMPLATE.replace(
        '{endpoint_path}', endpoint_path)

    layer_config_snippets = '\n'.join([layer_config['apache_config']
                                       for layer_config in layer_configs])

    # Add TWMS if there are any TWMS layers
    twms = any(layer_config.get('twms_config', None)
               for layer_config in layer_configs)
    twms_config = None
    if twms:
        twms_config = bulk_replace(MOD_TWMS_CONFIG_TEMPLATE, [
            ('{endpoint_path}', endpoint_path)])

    return generate_string_from_set('\n', ((proxy_config, proxy_needed), (date_service_config, date_service_needed), (datafile_proxy_config, datafile_proxy_needed), (main_apache_config, True), (layer_config_snippets, True), (TWMS_MODULE_TEMPLATE, twms), (twms_config, twms)))


def write_apache_config(endpoint_config, apache_config):
    apache_config_path = Path('/etc/httpd/conf.d/oe2-tile-service.conf')
    try:
        apache_config_path = Path(endpoint_config['apache_config_location'])
    except KeyError:
        print(f'\n"apache_config_location" not found in endpoint config, saving Apache config to {apache_config_path}')
        pass

    # Write out the Apache config
    Path(apache_config_path.parent).mkdir(parents=True, exist_ok=True)
    apache_config_path.write_text(apache_config)
    print(f'\nApache config written to {apache_config_path.as_posix()}')


def make_layer_config(endpoint_config, layer, make_twms=False):
    layer_config_path = layer['path']
    layer_config = layer['config']
    # Make sure we have what we need from the layer config
    try:
        layer_id = layer_config['layer_id']
        static = layer_config['static']
        projection = layer_config['projection']
        tilematrixset = layer_config['tilematrixset']
        size_x = layer_config['source_mrf']['size_x']
        size_y = layer_config['source_mrf']['size_y']
        tile_size_x = layer_config['source_mrf']['tile_size_x']
        tile_size_y = layer_config['source_mrf']['tile_size_y']
        bands = layer_config['source_mrf']['bands']
        idx_path = layer_config['source_mrf']['idx_path']
        mimetype = layer_config['mime_type']
    except KeyError as err:
        print(f"\n{layer_config_path} is missing required config element {err}")
        sys.exit()

    # Parse optional stuff in layer config
    year_dir = layer_config['source_mrf'].get('year_dir', False)
    alias = layer_config.get('alias', layer_id)
    empty_tile = layer_config['source_mrf'].get('empty_tile', None)

    data_file_path = layer_config['source_mrf'].get('data_file_path', None)
    data_file_uri = layer_config['source_mrf'].get('data_file_uri', None)
    if not data_file_path and not data_file_uri:
        print(f'\nWARNING: No "data_file_path" or "data_file_uri" configured in layer configuration: {layer_config_path}')

    # Make sure we have what we need from the endpoint config
    try:
        endpoint_path = endpoint_config['endpoint_config_base_location']
        if not static:
            date_service_uri = endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"\nEndpoint config is missing required config element {err}")

    base_idx_path = endpoint_config.get('base_idx_path', None)
    if base_idx_path:
        idx_path = base_idx_path + '/' + idx_path

    date_service_keys = endpoint_config.get('date_service_keys')

    # # Check to see if and data files exist and warn if not
    # if static and not Path(idx_path).exists():
    #     print(f"\nWARNING: Can't find IDX file specified: {idx_path}")

    # if static and data_file_path and not Path(data_file_path).exists():
    #     print(f"\nWARNING: Can't find data file specified: {data_file_path}")

    # if static and requests.head(data_file_uri).status_code != 200:
    #     print(f"\nWARNING: Can't access data file uri: {data_file_uri}")

    config_file_path = Path(
        endpoint_path, layer_id, "default", tilematrixset, 'mod_mrf.config')

    # Create Apache snippet

    # Proxy setup for data file (if needed)
    if data_file_uri:
        data_file_uri = format_source_uri_for_proxy(
            data_file_uri, endpoint_config['proxy_paths'])

    # Apache <Directory> stuff
    apache_config = bulk_replace(LAYER_APACHE_CONFIG_TEMPLATE, [
        ('{endpoint_path}', endpoint_path), ('{layer_id}', layer_id),
        ('{time_enabled}', 'Off' if static else 'On'),  ('{year_dir}',
                                                         'On' if year_dir else 'Off'),
        ('{alias}', alias), ('{tilematrixset}',
                             tilematrixset), ('{config_file_path}', config_file_path.as_posix())])

    # Insert time stuff if applicable (using a regexp to stick it in the
    # <Directory> block)
    if not static:
        date_service_snippet = f'\n        WMTSWrapperTimeLookupUri "{format_date_service_uri(date_service_uri)}"'
        if date_service_keys:
            date_service_snippet += f'\n        WMTSWrapperDateServiceKeys {" ".join(date_service_keys)}'
        apache_config = re.sub(r'(WMTSWrapperEnableTime.*)',
                               r'\1' + date_service_snippet, apache_config)

    # Bundle it all into a data structure
    layer_config_out = {}
    layer_config_out['static'] = static
    layer_config_out['data_file_uri'] = data_file_uri
    layer_config_out['apache_config'] = apache_config

    data_path_str = ''
    if data_file_uri:
        data_path_str = f'Redirect {data_file_uri}'
    elif data_file_path:
        data_path_str = f'DataFile {data_file_path}'

    # Add in substitution strings for mod_wmts_wrapper for non-static layers
    if not static:
        if year_dir:
            if not data_path_str.endswith('/'):
                data_path_str += '/'
            data_path_str += '${YYYY}'
            if not data_path_str.endswith('/'):
                idx_path += '/'
            idx_path += '${YYYY}'
        data_path_str += '/${filename}'
        data_path_str += MIME_TO_MRF_EXTENSION[mimetype]
        idx_path += '/${filename}.idx'

    main_wmts_config = bulk_replace(LAYER_MOD_MRF_CONFIG_TEMPLATE, [
        ('{size_x}', str(size_x)),
        ('{size_y}', str(size_y)),
        ('{tile_size_x}', str(tile_size_x)),
        ('{tile_size_y}', str(tile_size_y)),
        ('{bands}', str(bands)),
        ('{idx_path}', idx_path),
        ('{skipped_levels}', '1' if 'EPSG:4326' in projection else '0')])

    # Handle optionals like EmptyTile
    empty_tile_config = None
    if empty_tile:
        empty_tile_config = f'EmptyTile {empty_tile}'

    wmts_config = generate_string_from_set('\n', ((main_wmts_config, True), (
        data_path_str, data_file_uri or data_file_path), (empty_tile_config, empty_tile)))

    # Create mod_mrf configuration file
    layer_config_out['mod_mrf_config'] = {
        'path': config_file_path, 'contents': wmts_config}

    # Build the TWMS config if that's selected
    if make_twms:
        try:
            bbox = layer_config['source_mrf']['bbox']
        except KeyError as err:
            print(f'\n{layer_config_filename} is missing required config element {err}')

        source_path = Path(endpoint_path, layer_id,
                           'default', '${date}' if not static else '', tilematrixset)
        source_postfix = MIME_TO_EXTENSION[mimetype]
        twms_config = bulk_replace(LAYER_MOD_TWMS_CONFIG_TEMPLATE, [('{size_x}', str(size_x)), ('{size_y}', str(size_y)), (
            '{tile_size_x}', str(tile_size_x)), ('{tile_size_y}', str(tile_size_y)), ('{bands}', str(bands)), ('{source_postfix}', source_postfix), ('{source_path}', source_path.as_posix()), ('{bbox}', bbox),
            ('{skipped_levels}', '1' if 'EPSG4326' in tilematrixset else '0')])

        layer_config_out['twms_config'] = {'path': Path(
            endpoint_path, 'twms', layer_id, 'twms.config'), 'contents': twms_config}

    return layer_config_out


def get_layer_config(layer_config_path):
    with layer_config_path.open() as f:
        config = yaml.load(f.read())
    return {'path': layer_config_path, 'config': config}


def get_layer_configs(endpoint_config, make_twms=False):
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
        return [get_layer_config(filepath) for filepath in layer_source.iterdir() if filepath.is_file() and filepath.name.endswith('.yaml')]


def write_layer_configs(layer_configs):
    # Write out mod_mrf config files
    for layer_config in layer_configs:
        Path.mkdir(layer_config['mod_mrf_config']['path'].parent,
                   parents=True, exist_ok=True)
        layer_config['mod_mrf_config']['path'].write_text(
            layer_config['mod_mrf_config']['contents'])
        print(f'\nWTMS layer config written to: {layer_config["mod_mrf_config"]["path"]}')

        # Write out TWMS config if included
        if layer_config.get('twms_config', None):
            Path.mkdir(layer_config['twms_config'][
                       'path'].parent, parents=True, exist_ok=True)
            layer_config['twms_config']['path'].write_text(
                layer_config['twms_config']['contents'])
            print(f'\nTWMS layer config written to: {layer_config["twms_config"]["path"]}')

# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure mod_wmts_wrapper.')
    parser.add_argument('endpoint_config', type=str,
                        help='an endpoint config YAML file')
    parser.add_argument('-t', '--make_twms', action='store_true',
                        help='Generate TWMS configurations')
    args = parser.parse_args()

    endpoint_config = yaml.load(Path(args.endpoint_config).read_text())

    # Build all configs
    layer_input_configs = get_layer_configs(endpoint_config)
    endpoint_config['proxy_paths'] = get_proxy_paths(
        layer_input_configs)
    layer_output_configs = [make_layer_config(endpoint_config,
                                              layer, make_twms=args.make_twms) for layer in layer_input_configs]

    apache_config = make_apache_config(endpoint_config, layer_output_configs)

    # Write all configs
    write_layer_configs(layer_output_configs)
    write_apache_config(endpoint_config, apache_config)
    print('\nAll configurations written. Restart Apache for changes to take effect.')
