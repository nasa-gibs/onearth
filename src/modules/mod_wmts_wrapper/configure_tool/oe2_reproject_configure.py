#!/usr/bin/env python3

# Copyright (c) 2002-2020, California Institute of Technology.
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
This script creates mod_reproject Apache configurations using a remote GetCapabilities file. It can be used on its own or
with oe_configure_layer.
"""

import argparse
import yaml
from pathlib import Path
from lxml import etree
import sys
import requests
from functools import partial, reduce
import re
import math
from urllib.parse import urlsplit, urlparse
import png
from io import BytesIO
import time

EARTH_RADIUS = 6378137.0

MIME_TO_EXTENSION = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tiff',
    'image/lerc': '.lerc',
    'application/x-protobuf;type=mapbox-vector': '.pbf',
    'application/vnd.mapbox-vector-tile': '.mvt'
}

MOD_REPROJECT_APACHE_TEMPLATE = """<Directory {internal_endpoint}/{layer_id}>
        WMTSWrapperRole layer
</Directory>

<Directory {internal_endpoint}/{layer_id}/default>
        WMTSWrapperRole style
        WMTSWrapperEnableTime {time_enabled}
</Directory>

<Directory {internal_endpoint}/{layer_id}/default/{tilematrixset}>
        Retile_ConfigurationFiles {internal_endpoint}/{layer_id}/default/{tilematrixset}/source.config {internal_endpoint}/{layer_id}/default/{tilematrixset}/reproject.config
        Retile_RegExp {layer_id}
        Retile_Source {source_path} {postfix}
        WMTSWrapperRole tilematrixset
        {cache_expiration_block}
</Directory>
"""

MOD_REPROJECT_SOURCE_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
Projection {projection}
BoundingBox {bbox}
{format}
"""

MOD_REPROJECT_REPRO_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
Nearest {nearest}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
Projection {projection}
BoundingBox {bbox}
Oversample On
ExtraLevels 3
{format}
"""

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

<IfModule !retile_module>
        LoadModule retile_module modules/mod_retile.so
</IfModule>

<IfModule !proxy_module>
    LoadModule proxy_module modules/mod_proxy.so
</IfModule>

{twms_block}
<Directory {internal_endpoint}>
        WMTSWrapperRole root
</Directory>

{alias_block}
"""

PROXY_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_endpoint} {remote_endpoint}
ProxyPassReverse {local_endpoint} {remote_endpoint}
SetEnv proxy-nokeepalive 1
"""

PROXY_PREFIX = '/oe2-reproject-proxy'

MOD_TWMS_CONFIG_TEMPLATE = """Alias {external_endpoint} {internal_endpoint}
<Directory {internal_endpoint}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {internal_endpoint}/{layer}/twms.config
</Directory>
"""

TWMS_MODULE_TEMPLATE = """<IfModule !twms_module>
    LoadModule twms_module modules/mod_twms.so
</IfModule>
"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
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

DATE_SERVICE_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_date_service_uri} {date_service_uri}
ProxyPassReverse {local_date_service_uri} {date_service_uri}
"""


def strip_trailing_slash(string):
    if string.endswith('/'):
        string = string[:len(string) - 1]
    return string


def format_date_service_uri(uri):
    return '/oe2-time-service-proxy-' + bulk_replace(
        urlparse(uri).netloc, ((':', '-'), ('.', '-')))


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str


def get_date_service_info(endpoint_config, layer_configs):
    date_service_needed = any(
        layer_config.get('time_enabled') for layer_config in layer_configs)
    if not date_service_needed:
        return None
    return {
        'local': format_date_service_uri(endpoint_config['time_service_uri']),
        'remote': endpoint_config['time_service_uri']
    }


def get_matrix(matrix):
    return {
        'scale_denominator':
        float(matrix.findtext('{*}ScaleDenominator')),
        'top_left_corner':
        list(map(float,
                 matrix.findtext('{*}TopLeftCorner').split(' '))),
        'width':
        int(matrix.findtext('{*}TileWidth')),
        'height':
        int(matrix.findtext('{*}TileHeight')),
        'matrix_width':
        int(matrix.findtext('{*}MatrixWidth')),
        'matrix_height':
        int(matrix.findtext('{*}MatrixHeight')),
        'tile_width':
        int(matrix.findtext('{*}TileWidth')),
        'tile_height':
        int(matrix.findtext('{*}TileHeight')),
    }


def get_projection_from_crs(crs_string):
    suffix = crs_string.split(':')[-1]
    if suffix == 'CRS84':
        return 'EPSG:4326'
    return 'EPSG:' + suffix


def parse_tms_set_xml(tms):
    matrices = list(map(get_matrix, tms.findall('{*}TileMatrix')))
    return {
        'identifier': tms.findtext('{*}Identifier'),
        'matrices': matrices,
        'projection': get_projection_from_crs(tms.findtext('{*}SupportedCRS')),
    }


def parse_tms_xml(tms_xml_str, target_proj):
    try:
        main_xml = etree.parse(tms_xml_str)
    except etree.XMLSyntaxError:
        print('Problem with TileMatrixSets definition file -- not valid XML')
        sys.exit()

    tms_sets = next(
        elem.findall('{*}TileMatrixSet')
        for elem in main_xml.findall('{*}Projection')
        if elem.attrib.get("id") == target_proj)
    return map(parse_tms_set_xml, tms_sets)


def get_max_scale_denominator(tms):
    return sorted(
        [matrix['scale_denominator'] for matrix in tms['matrices']])[0]


def get_reprojected_tilematrixset(target_proj, source_tms_defs,
                                  target_tms_defs, layer_xml):
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    base_scale_denom = get_max_scale_denominator(source_tms)

    target_tms = target_tms_defs[0]
    minDiff = sys.maxsize
    target_tms = None
    for tms in target_tms_defs:
        diff = get_max_scale_denominator(tms) - base_scale_denom
        if diff > 0 and diff < minDiff:
            minDiff = diff
            target_tms = tms
    return target_tms


def get_source_tms(source_tms_defs, layer_xml):
    tms_id = layer_xml.find('{*}TileMatrixSetLink').findtext(
        '{*}TileMatrixSet')
    return next(tms for tms in source_tms_defs if tms['identifier'] == tms_id)


def get_src_size(source_tms_defs, layer_xml):
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    width = math.ceil(2 * math.pi * EARTH_RADIUS /
                      (get_max_scale_denominator(source_tms) * 0.28E-3))
    height = width
    if source_tms['matrices'][0]['matrix_width'] / source_tms['matrices'][0][
            'matrix_height'] == 2:
        height = width // 2
    return [width, height]


def format_source_url(source_url, reproj_tms):
    return re.sub(r'(.*{TileMatrixSet})(.*)', r'\1', source_url).replace(
        '{Time}', '${date}').replace('{TileMatrixSet}',
                                     reproj_tms['identifier'])


def make_proxy_config(proxy_path, replace_with_local):
    return bulk_replace(PROXY_TEMPLATE,
                        [('{remote_endpoint}', proxy_path['remote_path'].replace(str(replace_with_local), 'http://172.17.0.1') if replace_with_local else proxy_path['remote_path']),
                         ('{local_endpoint}', proxy_path['local_path'])])


def format_source_uri_for_proxy(uri, proxy_paths):
    for proxy_path in proxy_paths:
        if proxy_path['remote_path'] in uri:
            return uri.replace(proxy_path['remote_path'],
                               proxy_path['local_path'])


def get_layer_bands(identifier, mimetype, sample_tile_url):
    if mimetype == 'image/png':
        print('Checking for palette for PNG layer via ' + sample_tile_url)
        r = requests.get(sample_tile_url)
        if r.status_code != 200:
            if "Invalid time format" in r.text:  # Try taking out TIME if server doesn't like the request
                sample_tile_url = sample_tile_url.replace(
                    'default/default', 'default')
                r = requests.get(sample_tile_url)
                if r.status_code != 200:
                    mssg = 'Can\'t get sample PNG tile from URL: ' + sample_tile_url
                    print(mssg)
                    return '1'  # Assume PNG uses palette
            else:
                mssg = 'Can\'t get sample PNG tile from URL: ' + sample_tile_url
                print(mssg)
                return '1'  # Assume PNG uses palette
        sample_png = png.Reader(BytesIO(r.content))
        try:
            sample_png_read_info = sample_png.read()[3]
        except png.FormatError as err:
            print(err)
            return '3'  # default to 3 bands if not PNG
        try:
            if sample_png.palette():
                bands = 1
                print(identifier + ' contains palette')
        except png.FormatError:
            # No palette, check for greyscale
            if sample_png.asDirect()[3]['greyscale'] is True:
                bands = 1
                print(identifier + ' is greyscale')
            else:  # Check for alpha
                if sample_png_read_info['alpha'] is True:
                    bands = 4
                    print(identifier + ' is RGBA')
                else:
                    bands = 3
                    print(identifier + ' is RGB')
        return str(bands)
    else:
        return '3'  # default to 3 bands if not PNG


def parse_layer_gc_xml(target_proj, source_tms_defs, target_tms_defs, replace_with_local,
                       layer_xml):
    src_size = get_src_size(source_tms_defs, layer_xml)
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    reproj_tms = get_reprojected_tilematrixset(target_proj, source_tms_defs,
                                               target_tms_defs, layer_xml)
    if reproj_tms is None:
        layer_id = layer_xml.findtext('{*}Identifier')
        print(f"Unable to find matching tilematrixset for {layer_id}")
        return{}
    
    identifier = layer_xml.findtext('{*}Identifier')
    mimetype = layer_xml.find('{*}ResourceURL').attrib.get('format')
    sample_tile_url = format_source_url(
            layer_xml.find('{*}ResourceURL').attrib.get('template'),
            source_tms).replace('${date}', 'default') + '/0/0/0.png'
    if replace_with_local:
        sample_tile_url = sample_tile_url.replace(replace_with_local, 'http://172.17.0.1')
    
    bands = get_layer_bands(identifier, mimetype, sample_tile_url)
    return {
        'layer_id':
        layer_xml.findtext('{*}Identifier'),
        'source_url_template':
        format_source_url(
            layer_xml.findall('{*}ResourceURL')[-1].attrib.get('template'),
            source_tms), # Assume last ResourceURL would be the one containing {Time}
        'mimetype':
        layer_xml.find('{*}ResourceURL').attrib.get('format'),
        'time_enabled':
        any(
            len(dimension) for dimension in layer_xml.findall('{*}Dimension')
            if dimension.findtext('{*}Identifier') == 'Time'),
        'tilematrixset':
        reproj_tms,
        'src_size_x':
        src_size[0],
        'src_size_y':
        src_size[1],
        'reproj_size_x':
        reproj_tms['matrices'][-1]['matrix_width'] *
        reproj_tms['matrices'][-1]['tile_width'],
        'reproj_size_y':
        reproj_tms['matrices'][-1]['matrix_height'] *
        reproj_tms['matrices'][-1]['tile_height'],
        'tile_size_x':
        source_tms['matrices'][0]['tile_width'],
        'tile_size_y':
        source_tms['matrices'][0]['tile_height'],
        'reproj_tile_size_x':
        reproj_tms['matrices'][0]['tile_width'],
        'reproj_tile_size_y':
        reproj_tms['matrices'][0]['tile_height'],
        'projection':
        source_tms['projection'],
        'reproj_projection':
        reproj_tms['projection'],
        'bbox': (source_tms['matrices'][0]['top_left_corner'][0],
                 source_tms['matrices'][0]['top_left_corner'][1] * -1,
                 source_tms['matrices'][0]['top_left_corner'][0] * -1,
                 source_tms['matrices'][0]['top_left_corner'][1]),
        'reproj_bbox': (reproj_tms['matrices'][0]['top_left_corner'][0],
                        reproj_tms['matrices'][0]['top_left_corner'][1] * -1,
                        reproj_tms['matrices'][0]['top_left_corner'][0] * -1,
                        reproj_tms['matrices'][0]['top_left_corner'][1]),
        'bands':
        bands
    }


def get_gc_xml(source_gc_uri):
    attempt = 1
    retries = 10
    duration = 30 # in seconds
    try:
        r = requests.get(source_gc_uri)
        if r.status_code != 200:
            print(f"Can't get source GetCapabilities file: {source_gc_uri}")
            sys.exit()
    except:
        while attempt < retries:
            time.sleep(duration)
            attempt = attempt + 1
            try:
                r = requests.get(source_gc_uri)
                if r.status_code == 200:
                    break
            except:
                print("Failed attempt " + str(attempt) + " to connect to " + source_gc_uri)
        if attempt == retries:
            print(f"Can't get source GetCapabilities file: {source_gc_uri}")
            sys.exit()

    try:
        gc_xml = etree.fromstring(r.content)
    except etree.XMLSyntaxError:
        print('Problem with source GetCapabilities file -- not valid XML')
        sys.exit()
    return gc_xml


def make_apache_layer_config(endpoint_config, layer_config):
    if 'cache_expiration' in layer_config:
        cache_expiration = layer_config['cache_expiration']
        cache_expiration_block = f'Header Always Set Cache-Control "public, max-age={cache_expiration}"'
    else:
        cache_expiration_block = 'Header Always Set Pragma "no-cache"\n'
        cache_expiration_block += '        Header Always Set Expires "Thu, 1 Jan 1970 00:00:00 GMT"\n'
        cache_expiration_block += '        Header Always Set Cache-Control "max-age=0, no-store, no-cache, must-revalidate"\n'
        cache_expiration_block += '        Header Always Unset ETag\n'
        cache_expiration_block += '        FileETag None'

    apache_config = bulk_replace(
        MOD_REPROJECT_APACHE_TEMPLATE,
        [('{time_enabled}', 'On' if layer_config['time_enabled'] else 'Off'),
         ('{internal_endpoint}',
          strip_trailing_slash(
              endpoint_config['wmts_service']['internal_endpoint'])),
         ('{layer_id}', layer_config['layer_id']),
         ('{postfix}', MIME_TO_EXTENSION[layer_config['mimetype']]),
         ('{source_path}',
          format_source_uri_for_proxy(layer_config['source_url_template'],
                                      endpoint_config['proxy_paths'])),
         ('{tilematrixset}', layer_config['tilematrixset']['identifier']),
         ('{cache_expiration_block}', cache_expiration_block)])
    if layer_config['time_enabled'] and endpoint_config['date_service_info']:
        date_service_uri = endpoint_config['date_service_info']['local']
        date_service_snippet = f'\n        WMTSWrapperTimeLookupUri "{date_service_uri}"'
        apache_config = re.sub(r'(WMTSWrapperEnableTime.*)',
                               r'\1' + date_service_snippet, apache_config)

    return apache_config


def make_mod_reproject_configs(endpoint_config, layer_config):
    format = f'Format {layer_config["mimetype"]}' if layer_config["mimetype"].startswith('image') else ''

    src_config = bulk_replace(
        MOD_REPROJECT_SOURCE_TEMPLATE,
        [('{size_x}', str(layer_config['src_size_x'])),
         ('{size_y}', str(layer_config['src_size_y'])),
         ('{bands}', str(layer_config.get('bands', '3'))),
         ('{tile_size_x}', str(layer_config['tile_size_x'])),
         ('{tile_size_y}', str(layer_config['tile_size_y'])),
         ('{projection}', layer_config['projection']),
         ('{bbox}', ','.join(map(str, layer_config['bbox']))),
         ('{format}', format),
         ('{skipped_levels}',
          '1' if layer_config['projection'] == 'EPSG:4326' else '0')])

    reproj_config = bulk_replace(
        MOD_REPROJECT_REPRO_TEMPLATE,
        [('{size_x}', str(layer_config['reproj_size_x'])),
         ('{size_y}', str(layer_config['reproj_size_y'])),
         ('{bands}', str(layer_config.get('bands', '3'))),
         ('{tile_size_x}', str(layer_config['reproj_tile_size_x'])),
         ('{tile_size_y}', str(layer_config['reproj_tile_size_y'])),
         ('{projection}', str(layer_config['reproj_projection'])),
         ('{format}', format),
         ('{bbox}', ','.join(map(str, layer_config['reproj_bbox']))),
         ('{nearest}',
          'Off' if layer_config['mimetype'] == 'image/jpeg' else 'On')])

    # Add TWMS if TWMS endpoint is configured
    twms = endpoint_config.get('twms_service')
    twms_config = ''
    if twms:
        internal_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['internal_endpoint'])

        external_endpoint = strip_trailing_slash(
            endpoint_config['wmts_service']['external_endpoint'])

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

        source_path = '/'.join(
            (external_endpoint, layer_config['layer_id'],
             'default' + ('/${date}' if layer_config['time_enabled'] else ''),
             layer_config['tilematrixset']['identifier']))
        source_postfix = MIME_TO_EXTENSION[layer_config['mimetype']]

        twms_config = bulk_replace(
            LAYER_MOD_TWMS_CONFIG_TEMPLATE,
            [('{size_x}', str(layer_config['reproj_size_x'])),
             ('{size_y}', str(layer_config['reproj_size_y'])),
             ('{bands}', str(layer_config.get('bands', '3'))),
             ('{tile_size_x}', str(layer_config['reproj_tile_size_x'])),
             ('{tile_size_y}', str(layer_config['reproj_tile_size_y'])),
             ('{skipped_levels}',
              '1' if 'EPSG:4326' in layer_config['projection'] else '0'),
             ('{bbox}', ','.join(map(str, layer_config['reproj_bbox']))),
             ('{layer_id}', layer_config['layer_id']),
             ('{source_postfix}', source_postfix),
             ('{source_path}', source_path)])

    return {
        'layer_id': layer_config['layer_id'],
        'tilematrixset': layer_config['tilematrixset']['identifier'],
        'src_config': src_config,
        'reproj_config': reproj_config,
        'twms_config': twms_config
    }


def get_proxy_paths(layers):
    proxy_paths = []
    for layer_config in layers:
        try:
            data_file_uri = re.sub(r'(.*)\/\${date}', r'\1', layer_config['source_url_template'])
        except KeyError as err:
            print(f"{err} is missing")
            return proxy_paths
        url_parts = urlsplit(data_file_uri)
        remote_path = f'{url_parts.scheme}://{url_parts.netloc}'
        if not any(path for path in proxy_paths
                   if path['remote_path'] == remote_path):
            proxy_paths.append({
                'local_path':
                f'{PROXY_PREFIX}-{url_parts.scheme}-{url_parts.netloc.replace(".", "-")}',
                'remote_path':
                remote_path
            })
    return proxy_paths


def get_layer_config(layer_config_path):
    with layer_config_path.open() as f:
        config = yaml.safe_load(f.read())
    return {'path': str(layer_config_path), 'config': config}


def get_layer_configs(endpoint_config):
    try:
        layer_source = Path(endpoint_config['layer_config_source'])
    except KeyError:
        print("\nERROR: Must specify 'layer_config_source'!")
        sys.exit()

    # Find all source configs - traversing down a single directory level
    if not layer_source.exists():
        print(f"ERROR: Can't find specified layer config location: {layer_source}")
        sys.exit()
    if layer_source.is_file():
        return [get_layer_config(layer_source)]
    elif layer_source.is_dir():
        return [
            get_layer_config(filepath) for filepath in layer_source.iterdir()
            if filepath.is_file() and filepath.name.endswith('.yaml') and
                Path(filepath).name not in endpoint_config.get('exclude_layers', [])
        ]


def build_configs(endpoint_config):
    # Check endpoint configs for necessary stuff
    try:
        target_proj = endpoint_config['reproject']['target_epsg_code']
        source_gc_uri = endpoint_config['reproject']['source_gc_uri']
        endpoint_config['time_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")
    
    # Replace matching host names with local Docker host IP 172.17.0.1 so that connections stay local
    replace_with_local = None
    if endpoint_config['reproject']['replace_with_local']:
        replace_with_local = endpoint_config['reproject']['replace_with_local']
        source_gc_uri = source_gc_uri.replace(replace_with_local, 'http://172.17.0.1')
    else:
        print(
            '\nNo "replace_with_local" configured.'
        )

    # Get output TMS definitions (provided by local file)
    if not endpoint_config.get('tms_defs_file'):
        print(
            '\nNo Tile Matrix Set definition file defined by endpoint config or command line parameters. Using ./tilematrixsets.xml'
        )
        endpoint_config['tms_defs_file'] = 'tilematrixsets.xml'

    # Check that a GetCapabilies service has been configured
    if not endpoint_config.get('gc_service_uri'):
        print(
            '\nNo "gc_service_uri" configured. GetCapabilities/GetTileService will not be accessible'
        )

    target_tms_defs = list(
        parse_tms_xml(endpoint_config['tms_defs_file'], target_proj))

    # Download and parse the source GC file, getting the layers and their
    # tilematrixsets
    gc_xml = get_gc_xml(source_gc_uri)
    source_tms_defs = list(
        map(parse_tms_set_xml,
            gc_xml.find('{*}Contents').findall('{*}TileMatrixSet')))

    layer_list = gc_xml.iter('{*}Layer')
    if endpoint_config.get('include_layers'):
        layer_list = [
            layer for layer in layer_list if layer.findtext('{*}Identifier') in
            endpoint_config.get('include_layers')
        ]

    layers = list(
        map(
            partial(parse_layer_gc_xml, target_proj, source_tms_defs,
                    target_tms_defs, replace_with_local), layer_list))
    layers = [x for x in layers if x != {}] # remove layers we can't reproject
    # Filter out any layers in the "exclude_layers" list, if applicable
    layers = list(filter(lambda x: x['layer_id'] not in endpoint_config.get('exclude_layers', []), layers))
    # Build configs for each layer
    endpoint_config['proxy_paths'] = get_proxy_paths(layers)
    endpoint_config['date_service_info'] = get_date_service_info(
        endpoint_config, layers)

    # Get cache_expiration (if exists) from layer configs and add to each layer
    layer_configs = get_layer_configs(endpoint_config)

    for layer in layers:
        layer_config = next((lc for lc in layer_configs if layer['layer_id'] == lc['config']['layer_id']), False)

        if layer_config and 'cache_expiration' in layer_config['config']:
            layer['cache_expiration'] = layer_config['config']['cache_expiration']

    layer_apache_configs = map(
        partial(make_apache_layer_config, endpoint_config), layers)
    layer_module_configs = map(
        partial(make_mod_reproject_configs, endpoint_config), layers)

    internal_endpoint = strip_trailing_slash(
        endpoint_config['wmts_service']['internal_endpoint'])

    # Write out layer configs
    for layer_config in layer_module_configs:
        config_path = Path(internal_endpoint, layer_config['layer_id'],
                           'default', layer_config['tilematrixset'])
        config_path.mkdir(parents=True, exist_ok=True)
        Path(config_path,
             'source.config').write_text(layer_config['src_config'])
        Path(config_path,
             'reproject.config').write_text(layer_config['reproj_config'])

        if layer_config['twms_config']:
            try:
                twms_internal_endpoint = strip_trailing_slash(
                    endpoint_config['twms_service']['internal_endpoint'])
            except KeyError as err:
                print(
                    f"Endpoint config is missing required config element {err}"
                )

            config_path = Path(twms_internal_endpoint,
                               layer_config['layer_id'])
            config_path.mkdir(parents=True, exist_ok=True)
            Path(config_path,
                 'twms.config').write_text(layer_config['twms_config'])

    print(f'\nLayer configs written to {internal_endpoint}\n')

    try:
        apache_config_path = Path(endpoint_config['apache_config_location'])
    except KeyError:
        apache_config_path = Path("/etc/httpd/conf.d")
        print(
            f'\n"apache_config_location" not found in endpoint config, saving Apache config to {apache_config_path}'
        )
        pass

    try:
        apache_config_path = Path(
            apache_config_path,
            endpoint_config['wmts_service']['config_prefix'] + '.conf')
    except KeyError:
        apache_config_path = Path(apache_config_path,
                                  'oe2-wmts-reproject.conf')
        print(
            f'\n"wmts_service/config_prefix" not found in endpoint config, saving Apache config to {apache_config_path}'
        )
        pass

    # Write out the Apache config
    Path(apache_config_path.parent).mkdir(parents=True, exist_ok=True)

    external_endpoint = '/'
    try:
        external_endpoint = endpoint_config['wmts_service'][
            'external_endpoint']
    except KeyError:
        print('No wmts_service/external_endpoint configured. Using "/"')
        pass

    gc_service_block = ''
    try:
        gc_service_block = bulk_replace(
            GC_SERVICE_TEMPLATE,
            [('{gc_service_uri}', endpoint_config['gc_service_uri']),
             ('{external_endpoint}', external_endpoint)])
    except KeyError:
        print(
            '\nNo "gc_service_uri" configured. GetCapabilities/GetTileService will not be accessible'
        )
        pass

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

        twms_config = bulk_replace(
            MOD_TWMS_CONFIG_TEMPLATE,
            [('{internal_endpoint}', twms_internal_endpoint),
             ('{external_endpoint}', twms_external_endpoint)])

    internal_endpoint = strip_trailing_slash(
        endpoint_config['wmts_service']['internal_endpoint'])

    alias_block = ''
    if external_endpoint:
        alias_block = 'Alias {} {}'.format(external_endpoint,
                                           internal_endpoint)

    # The TWMS redirects need to go first so they don't interfere with the WMTS ones
    apache_config_str = ''
    if twms and endpoint_config.get('gc_service_uri'):
        apache_config_str += bulk_replace(
            TWMS_GC_SERVICE_TEMPLATE,
            [('{gc_service_uri}', endpoint_config['gc_service_uri']),
             ('{external_endpoint}', twms_external_endpoint)])
        apache_config_str += '\n'

    apache_config_str += bulk_replace(
        MAIN_APACHE_CONFIG_TEMPLATE,
        [('{internal_endpoint}', internal_endpoint),
         ('{gc_service_block}', gc_service_block),
         ('{twms_block}', twms_config), ('{alias_block}', alias_block),
         ('{gc_service_block}', gc_service_block)])

    apache_config_str += '\n' + '\n'.join(
        make_proxy_config(proxy_path, replace_with_local)
        for proxy_path in endpoint_config['proxy_paths'])
    if endpoint_config['date_service_info']:
        apache_config_str += '\n' + DATE_SERVICE_TEMPLATE.replace(
            '{date_service_uri}',
            endpoint_config['date_service_info']['remote']).replace(
                '{local_date_service_uri}',
                endpoint_config['date_service_info']['local'])
    if twms:
        apache_config_str += '\n' + TWMS_MODULE_TEMPLATE
    apache_config_str += '\n' + '\n'.join(layer_apache_configs)
    apache_config_path.write_text(apache_config_str)
    print(f'Apache config written to {apache_config_path.as_posix()}\n')

    print(
        'All configurations written. Restart Apache for the changes to take effect.'
    )


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configure mod_reproject.')
    parser.add_argument(
        'endpoint_config', type=str, help='an endpoint config YAML file')
    parser.add_argument(
        '-x',
        '--tms_defs',
        type=str,
        help='TileMatrixSets definition XML file')
    args = parser.parse_args()

    endpoint_config = yaml.safe_load(Path(args.endpoint_config).read_text())
    if args.tms_defs:
        endpoint_config['tms_defs_file'] = args.tms_defs
    build_configs(endpoint_config)
