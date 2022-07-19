#!/usr/bin/env python3

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

MAIN_APACHE_CONFIG_TEMPLATE = """{gc_service_block}
<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !wmts_wrapper_module>
    LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<IfModule !receive_module>
    LoadModule receive_module modules/mod_receive.so
</IfModule>

<Directory {internal_endpoint}>
    WMTSWrapperRole root
</Directory>

{alias_block}
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
ProxyPass {local_data_file_uri} {data_file_uri} nomain
ProxyPassReverse {local_data_file_uri} {data_file_uri}
"""

LAYER_APACHE_CONFIG_TEMPLATE = """<Directory {internal_endpoint}/{layer_id}>
    WMTSWrapperRole layer
</Directory>

<Directory {internal_endpoint}/{layer_id}/default>
        WMTSWrapperRole style
        WMTSWrapperEnableTime {time_enabled}
</Directory>

<Directory {internal_endpoint}/{layer_id}/default/{tilematrixset}>
        {mrf_or_convert_configs}     
        WMTSWrapperRole tilematrixset
        WMTSWrapperEnableYearDir {year_dir}
        WMTSWrapperLayerAlias {alias}
        WMTSWrapperMimeType {mime_type}
        {cache_expiration_block}
</Directory>

{proxy_exemption_block}
"""

MOD_TWMS_CONFIG_TEMPLATE = """Alias {external_endpoint} {internal_endpoint}
<Directory {internal_endpoint}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {internal_endpoint}/{layer}/twms.config
</Directory>
"""

LAYER_MOD_MRF_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
IndexFile {idx_path}"""

LAYER_MOD_CONVERT_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
BoundingBox {bbox}
SourcePath {source_path}
SourcePostfix {source_postfix}
"""

GC_SERVICE_TEMPLATE = """# Redirects for GC service
RewriteEngine on
RewriteCond %{REQUEST_FILENAME} ^{external_endpoint}/(.*)$ [NC]
RewriteCond %{QUERY_STRING} request=getcapabilities [NC]
RewriteRule ^(.*)$ {gc_service_uri}/gc_service?request=wmtsgetcapabilities [P,L]

RewriteEngine on
RewriteCond %{REQUEST_FILENAME} ^{external_endpoint}/1.0.0/WMTSCapabilities.xml(.*)$ [NC]
RewriteRule ^(.*)$ {gc_service_uri}/gc_service?request=wmtsgetcapabilities [P,L]
"""

TWMS_GC_SERVICE_TEMPLATE = """# Redirects for TWMS GC/GTS service
RewriteCond %{REQUEST_URI} ^{external_endpoint}/twms(.*)$ [NC]
RewriteCond %{QUERY_STRING} request=getcapabilities [NC]
RewriteRule ^(.*)$ {gc_service_uri}/gc_service?request=twmsgetcapabilities [P,L]

RewriteCond %{REQUEST_URI} ^{external_endpoint}/twms(.*)$ [NC]
RewriteCond %{QUERY_STRING} request=gettileservice [NC]
RewriteRule ^(.*)$ {gc_service_uri}/gc_service?request=gettileservice [P,L]
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


def strip_trailing_slash(string):
    return re.sub(r'/$', '', string)


def format_date_service_uri(uri):
    return '/oe2-time-service-proxy-' + bulk_replace(
        urlparse(uri).netloc, ((':', '-'), ('.', '-')))


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
        data_file_uri = layer_config['config']['source_mrf'].get(
            'data_file_uri')
        if not data_file_uri:
            continue
        url_parts = urlsplit(data_file_uri)
        remote_path = f'{url_parts.scheme}://{url_parts.netloc}'
        if not any(path for path in proxy_paths
                   if path['remote_path'] == remote_path):
            proxy_paths.append({
                'local_path':
                f'{PROXY_PATH}-{url_parts.netloc.replace(".", "-")}',
                'remote_path':
                remote_path
            })
    return proxy_paths


def make_proxy_config(proxy_path):
    return bulk_replace(DATA_FILE_PROXY_TEMPLATE,
                        [('{data_file_uri}', proxy_path['remote_path']),
                         ('{local_data_file_uri}', proxy_path['local_path'])])


def format_source_uri_for_proxy(uri, proxy_paths):
    for proxy_path in proxy_paths:
        if proxy_path['remote_path'] in uri:
            return uri.replace(proxy_path['remote_path'],
                               proxy_path['local_path'])


# Main configuration functions


def make_apache_config(endpoint_config, layer_configs):
    # Only set up the date service proxy if there are non-static layers
    date_service_needed = any(
        layer_config.get('static') is False for layer_config in layer_configs)

    datafile_proxy_needed = any(
        layer_config.get('data_file_uri') for layer_config in layer_configs)
    try:
        internal_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['internal_endpoint'])
        if date_service_needed:
            date_service_uri = endpoint_config['time_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    external_endpoint = "/wmts"
    try:
        external_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['external_endpoint'])
    except KeyError:
        print('No external_endpoint configured. Using "/wmts"')
        pass

    gc_service_uri = None
    if endpoint_config.get('gc_service_uri'):
        gc_service_uri = endpoint_config.get('gc_service_uri')
    elif endpoint_config.get('gc_service'):
        gc_service_uri = endpoint_config.get('gc_service').get(
            'external_endpoint')

    if gc_service_uri:
        gc_service_block = bulk_replace(
            GC_SERVICE_TEMPLATE, [('{internal_endpoint}', internal_endpoint),
                                  ('{gc_service_uri}', gc_service_uri),
                                  ('{external_endpoint}', external_endpoint)])
    else:
        gc_service_block = ''
        print(
            '\nNo "gc_service_uri" configured or gc_service configuration found. GetCapabilities/GetTileService will not be accessible'
        )

    # Set up proxies for date service and data files (if needed)
    proxy_config = ''
    proxy_needed = date_service_needed or datafile_proxy_needed
    if proxy_needed:
        proxy_config = PROXY_MODULE_TEMPLATE

    date_service_config = ''
    if date_service_needed:
        date_service_config = DATE_SERVICE_TEMPLATE.replace(
            '{date_service_uri}', date_service_uri).replace(
                '{local_date_service_uri}',
                format_date_service_uri(date_service_uri))

    datafile_proxy_config = ''
    if datafile_proxy_needed:
        datafile_proxy_config = '\n'.join([
            make_proxy_config(config)
            for config in endpoint_config['proxy_paths']
        ])

    alias_block = 'Alias {} {}'.format(external_endpoint, internal_endpoint)

    main_apache_config = bulk_replace(
        MAIN_APACHE_CONFIG_TEMPLATE,
        [('{internal_endpoint}', internal_endpoint),
         ('{gc_service_block}', gc_service_block),
         ('{alias_block}', alias_block),
         ('{external_endpoint}', external_endpoint)])

    layer_config_snippets = '\n'.join(
        [layer_config['apache_config'] for layer_config in layer_configs])

    # Add TWMS if TWMS endpoint is configured
    twms = endpoint_config.get('twms_service')
    twms_config = ''
    if twms:
        try:
            twms_internal_endpoint = strip_trailing_slash(
                endpoint_config['twms_service']['internal_endpoint'])
        except KeyError as err:
            print(f"Endpoint config is missing required config element {err}")

        try:
            twms_external_endpoint = strip_trailing_slash(
                endpoint_config['twms_service']['external_endpoint'])
        except KeyError:
            twms_external_endpoint = '/twms'
            print('No external_endpoint configured. Using {}'.format(
                twms_external_endpoint))
            pass

        twms_config = TWMS_MODULE_TEMPLATE
        twms_config += "\n\n"
        twms_config += bulk_replace(
            MOD_TWMS_CONFIG_TEMPLATE,
            [('{internal_endpoint}', twms_internal_endpoint),
             ('{external_endpoint}', twms_external_endpoint)])
        if endpoint_config.get('gc_service_uri'):
            twms_gc_config = bulk_replace(
                TWMS_GC_SERVICE_TEMPLATE,
                [('{gc_service_uri}', gc_service_uri),
                 ('{external_endpoint}', twms_external_endpoint)])
            main_apache_config = '\n'.join(
                [twms_gc_config, main_apache_config])

    return generate_string_from_set(
        '\n', ((proxy_config, proxy_needed),
               (date_service_config, date_service_needed),
               (datafile_proxy_config, datafile_proxy_needed),
               (main_apache_config, True), (layer_config_snippets, True),
               (twms_config, twms)))


def write_apache_config(endpoint_config, apache_config):
    try:
        apache_config_path = Path(
            endpoint_config['apache_config_location'],
            endpoint_config['wmts_service']['config_prefix'] + '.conf')
    except KeyError:
        apache_config_path = Path("/etc/httpd/conf.d/oe2_wmts_service.conf")
        print(
            f'\n"apache_config_location" not found in endpoint config, saving Apache config to {apache_config_path}'
        )
        pass

    # Write out the Apache config
    Path(apache_config_path.parent).mkdir(parents=True, exist_ok=True)
    apache_config_path.write_text(apache_config)
    print(f'\nApache config written to {apache_config_path.as_posix()}')


def make_layer_config(endpoint_config, layer):
    layer_config_path = layer['path']
    layer_config = layer['config']
    # Make sure we have what we need from the layer config
    try:
        layer_id = layer_config['layer_id']
        static = layer_config['static']
        projection = layer_config['projection']
        tilematrixset = layer_config['tilematrixset']
        try:
            cache_expiration = layer_config['cache_expiration']
        except:
            cache_expiration = None
        size_x = layer_config['source_mrf']['size_x']
        size_y = layer_config['source_mrf']['size_y']
        tile_size_x = layer_config['source_mrf']['tile_size_x']
        tile_size_y = layer_config['source_mrf']['tile_size_y']
        bands = layer_config['source_mrf']['bands'] if layer_config['source_mrf']['bands'] is not None else 1
        idx_path = layer_config['source_mrf']['idx_path']
        mimetype = layer_config['mime_type']
        convert_src = layer_config['convert_mrf'].get('convert_source', None) if 'convert_mrf' in layer_config else False
    except KeyError as err:
        print(
            f"\n{layer_config_path} is missing required config element {err}")
        sys.exit()

    # Parse optional stuff in layer config
    year_dir = layer_config['source_mrf'].get('year_dir', False)
    alias = layer_config.get('alias', layer_id)
    empty_tile = layer_config['source_mrf'].get('empty_tile', None)
    best = layer_config.get('best_config', None)

    # Override static if best available layer
    if best is not None:
        static = False

    # Check if empty_tile file exists, and if not use a default empty tile instead
    if empty_tile and not os.path.exists(empty_tile):
        default_empty_tile = "/etc/onearth/empty_tiles/Blank_RGB"
        if mimetype == "image/jpeg":
            default_empty_tile += "_" + str(tile_size_x) + ".jpg"
        else:
            default_empty_tile += "A_" + str(tile_size_x) + ".png"

        print(f"ERROR: empty_tile '{empty_tile}' not found!  Using default empty tile '{default_empty_tile}' instead.")
        empty_tile = default_empty_tile

    data_file_path = layer_config['source_mrf'].get('data_file_path', None)
    data_file_uri = layer_config['source_mrf'].get('data_file_uri', None)
    if not data_file_path and not data_file_uri:
        print(
            f'\nWARNING: No "data_file_path" or "data_file_uri" configured in layer configuration: {layer_config_path}'
        )

    # Make sure we have what we need from the endpoint config
    try:
        internal_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['internal_endpoint'])
        external_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['external_endpoint'])
        if not static:
            date_service_uri = endpoint_config['time_service_uri']
    except KeyError as err:
        print(f"\nEndpoint config is missing required config element {err}")

    base_idx_path = endpoint_config.get('base_idx_path', None)
    if base_idx_path:
        idx_path = base_idx_path + '/' + idx_path

    date_service_keys = endpoint_config.get('time_service_keys')

    # # Check to see if and data files exist and warn if not
    # if static and not Path(idx_path).exists():
    #     print(f"\nWARNING: Can't find IDX file specified: {idx_path}")

    # if static and data_file_path and not Path(data_file_path).exists():
    #     print(f"\nWARNING: Can't find data file specified: {data_file_path}")

    # if static and requests.head(data_file_uri).status_code != 200:
    #     print(f"\nWARNING: Can't access data file uri: {data_file_uri}")

    # Create Apache snippet

    # Proxy setup for data file (if needed)
    if data_file_uri:
        data_file_uri = format_source_uri_for_proxy(
            data_file_uri, endpoint_config['proxy_paths'])

    # static reproject layers require a proxy exemption to prevent traffic from being directly routed to reproject container
    proxy_exemption_block = ''
    if projection == 'EPSG:3857':
        try:
            wmts_exemption = f'ProxyPass {external_endpoint}/{layer_id} !'
            proxy_exemption_block += wmts_exemption
        except NameError as err:
            print(f"\nEndpoint config is missing required wmts config element {err}")
        try:
            twms_external_endpoint = strip_trailing_slash(
                endpoint_config['twms_service']['external_endpoint'])
            twms_exemption = f'\nProxyPass {twms_external_endpoint}/{layer_id} !'
            proxy_exemption_block += twms_exemption
        except KeyError as err:
            print(f"\nEndpoint config is missing required twms config element {err}")

    if cache_expiration:
        cache_expiration_block = f'Header Always Set Cache-Control "public, max-age={cache_expiration}"'
    else:
        cache_expiration_block = 'Header Always Set Pragma "no-cache"\n'
        cache_expiration_block += '        Header Always Set Expires "Thu, 1 Jan 1970 00:00:00 GMT"\n'
        cache_expiration_block += '        Header Always Set Cache-Control "max-age=0, no-store, no-cache, must-revalidate"\n'
        cache_expiration_block += '        Header Always Unset ETag\n'
        cache_expiration_block += '        FileETag None'

    config_file_path = Path(internal_endpoint, layer_id, "default",
                            tilematrixset, 'mod_mrf.config')

    mrf_or_convert_configs = ''
    if convert_src:
        convert_src_name , format = convert_src.split(" ")
        
        convert_file_path = Path(internal_endpoint, layer_id, "default",
                                tilematrixset, 'mod_convert.config')
        src_mrf_file_path = Path(internal_endpoint, convert_src_name, "default",
                            tilematrixset, 'mod_mrf.config')
        mrf_or_convert_configs = (
            f'Convert_RegExp {external_endpoint}/{alias}/\n'
            f'        Convert_Source {external_endpoint}/{convert_src_name}/default/${{date}}/{tilematrixset}/ {format}\n'
            f'        Convert_ConfigurationFiles {src_mrf_file_path} {convert_file_path}')
    else:
        mrf_or_convert_configs = (
            f'MRF_ConfigurationFile {config_file_path}\n'
            f'        MRF_RegExp {alias}')

    # Apache <Directory> stuff
    apache_config = bulk_replace(
        LAYER_APACHE_CONFIG_TEMPLATE,
        [('{internal_endpoint}', internal_endpoint), ('{layer_id}', layer_id),
         ('{time_enabled}', 'Off' if static else 'On'),
         ('{year_dir}', 'On' if year_dir else 'Off'), ('{alias}', alias),
         ('{tilematrixset}', tilematrixset),
         ('{cache_expiration_block}', cache_expiration_block),
         ('{proxy_exemption_block}', proxy_exemption_block),
         ('{mrf_or_convert_configs}', mrf_or_convert_configs),
         ('{config_file_path}', config_file_path.as_posix()),
         ('{mime_type}', mimetype)])

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
        data_path_str = f'DataFile :/{data_file_uri}'
    elif data_file_path:
        data_path_str = f'DataFile {data_file_path}'

    # Add in substitution strings for mod_wmts_wrapper for non-static layers
    if not static:
        # check for slashes
        if not data_path_str.endswith('/'):
            data_path_str += '/'
        if not idx_path.endswith('/'):
            idx_path += '/'
        # check for year_dir
        if year_dir:
            data_path_str += '${prefix}/${YYYY}/'
            idx_path += '${prefix}/${YYYY}/'
        else:
            data_path_str += '${prefix}/'
            idx_path += '${prefix}/'      
        # add filename
        data_path_str += '${filename}'
        data_path_str += MIME_TO_MRF_EXTENSION[mimetype]
        idx_path += '${filename}.idx'

    if convert_src:
        wmts_convert_config = bulk_replace(
        LAYER_MOD_CONVERT_CONFIG_TEMPLATE,
        [('{size_x}', str(size_x)), ('{size_y}', str(size_y)),
         ('{tile_size_x}', str(tile_size_x)),
         ('{tile_size_y}', str(tile_size_y)), ('{bands}', str(bands)),
         ('{skipped_levels}',
          '0' if projection == 'EPSG:3857' else '1')])

        convert_config = generate_string_from_set(
        '\n', [(wmts_convert_config, True)])

        layer_config_out['mod_convert_config'] = {
        'path': convert_file_path,
        'contents': convert_config
    }
    main_wmts_config = bulk_replace(
    LAYER_MOD_MRF_CONFIG_TEMPLATE,
    [('{size_x}', str(size_x)), ('{size_y}', str(size_y)),
        ('{tile_size_x}', str(tile_size_x)),
        ('{tile_size_y}', str(tile_size_y)), ('{bands}', str(bands)),
        ('{idx_path}', idx_path),
        ('{skipped_levels}',
        '0' if projection == 'EPSG:3857' else '1')])

    # Handle optionals like EmptyTile
    empty_tile_config = None
    if empty_tile:
        empty_tile_config = f'EmptyTile {empty_tile}'

    wmts_config = generate_string_from_set(
        '\n', ((main_wmts_config, True),
               (data_path_str, data_file_uri or data_file_path),
               (empty_tile_config, empty_tile)))

    # Create mod_mrf configuration file
    layer_config_out['mod_mrf_config'] = {
        'path': config_file_path,
        'contents': wmts_config
    }

    # Build the TWMS config if that's selected
    twms = endpoint_config.get('twms_service')
    if twms:
        try:
            bbox = layer_config['source_mrf']['bbox']
        except KeyError as err:
            print(
                f'\n{layer_config_filename} is missing required config element {err}'
            )

        source_path = '/'.join(
            (external_endpoint, layer_id,
             'default' + ('/${date}' if not static else ''), tilematrixset))
        source_postfix = MIME_TO_EXTENSION[mimetype]
        twms_config = bulk_replace(
            LAYER_MOD_TWMS_CONFIG_TEMPLATE,
            [('{size_x}', str(size_x)), ('{size_y}', str(size_y)),
             ('{tile_size_x}', str(tile_size_x)),
             ('{tile_size_y}', str(tile_size_y)), ('{bands}', str(bands)),
             ('{source_postfix}', source_postfix),
             ('{source_path}', source_path), ('{bbox}', bbox),
             ('{skipped_levels}',
              '0' if projection == 'EPSG:3857' else '1')])

        try:
            twms_internal_endpoint = strip_trailing_slash(
                endpoint_config['twms_service']['internal_endpoint'])
        except KeyError as err:
            print(f"Endpoint config is missing required config element {err}")

        layer_config_out['twms_config'] = {
            'path': Path(twms_internal_endpoint, layer_id, 'twms.config'),
            'contents': twms_config
        }

    return layer_config_out


def get_layer_config(layer_config_path):
    with layer_config_path.open() as f:
        config = yaml.safe_load(f.read())
    return {'path': layer_config_path, 'config': config}


def get_layer_configs(endpoint_config):
    layer_configs = []
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
        try:
            layer_config = get_layer_config(layer_source)
            layer_configs.append(layer_config)
        except yaml.constructor.ConstructorError as err:
            print(f'ERROR: Invalid YAML in layer configuration {err}')
    elif layer_source.is_dir():
        for filepath in layer_source.iterdir():
            if filepath.is_file() and filepath.name.endswith('.yaml'):
                try:
                    layer_config = get_layer_config(filepath)
                    layer_configs.append(layer_config)
                except yaml.constructor.ConstructorError as err:
                    print(f'ERROR: Invalid YAML in layer configuration {err}')
    return layer_configs


def write_layer_configs(layer_configs):
    # Write out mod_mrf config files
    for layer_config in layer_configs:
        Path.mkdir(
            layer_config['mod_mrf_config']['path'].parent,
            parents=True,
            exist_ok=True)
        layer_config['mod_mrf_config']['path'].write_text(
            layer_config['mod_mrf_config']['contents'])
        print(
            f'\nWTMS layer config written to: {layer_config["mod_mrf_config"]["path"]}'
        )

        # Write out TWMS config if included
        if layer_config.get('twms_config', None):
            Path.mkdir(
                layer_config['twms_config']['path'].parent,
                parents=True,
                exist_ok=True)
            layer_config['twms_config']['path'].write_text(
                layer_config['twms_config']['contents'])
            print(
                f'\nTWMS layer config written to: {layer_config["twms_config"]["path"]}'
            )

        # Write out mod_convert config if included
        if layer_config.get('mod_convert_config', None):
            Path.mkdir(
                layer_config['mod_convert_config']['path'].parent,
                parents=True,
                exist_ok=True)
            layer_config['mod_convert_config']['path'].write_text(
                layer_config['mod_convert_config']['contents'])
            print(
                f'\nConvert layer config written to: {layer_config["mod_convert_config"]["path"]}'
            )


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure mod_wmts_wrapper.')
    parser.add_argument(
        'endpoint_config', type=str, help='an endpoint config YAML file')

    args = parser.parse_args()

    endpoint_config = yaml.safe_load(Path(args.endpoint_config).read_text())

    # Build all configs
    layer_input_configs = get_layer_configs(endpoint_config)
    endpoint_config['proxy_paths'] = get_proxy_paths(layer_input_configs)
    layer_output_configs = [
        make_layer_config(endpoint_config, layer)
        for layer in layer_input_configs
    ]

    apache_config = make_apache_config(endpoint_config, layer_output_configs)

    # Write all configs
    write_layer_configs(layer_output_configs)
    write_apache_config(endpoint_config, apache_config)
    print(
        '\nAll configurations written. Restart Apache for changes to take effect.'
    )
