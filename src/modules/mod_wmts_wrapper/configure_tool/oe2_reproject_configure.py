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
from urllib.parse import urlsplit

EARTH_RADIUS = 6378137.0

MIME_TO_EXTENSION = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/tiff': '.tiff',
    'image/lerc': '.lerc',
    'application/x-protobuf;type=mapbox-vector': '.pbf',
    'application/vnd.mapbox-vector-tile': '.mvt'
}

MOD_REPROJECT_APACHE_TEMPLATE = """<Directory {endpoint_path}/{layer_id}>
        WMTSWrapperRole layer
</Directory>

<Directory {endpoint_path}/{layer_id}/default>
        WMTSWrapperRole style
        WMTSWrapperEnableTime {time_enabled}
</Directory>

<Directory {endpoint_path}/{layer_id}/default/{tilematrixset}>
        Reproject_ConfigurationFiles {endpoint_path}/{layer_id}/default/{tilematrixset}/source.config {endpoint_path}/{layer_id}/default/{tilematrixset}/reproject.config
        Reproject_RegExp {layer_id}
        WMTSWrapperRole tilematrixset
</Directory>
"""

MOD_REPROJECT_SOURCE_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
Projection {projection}
BoundingBox {bbox}
"""

MOD_REPROJECT_REPRO_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
Nearest {nearest}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
Projection {projection}
BoundingBox {bbox}
SourcePath {source_path}
SourcePostfix {postfix}
MimeType {mimetype}
Oversample On
ExtraLevels 3
"""

MAIN_APACHE_CONFIG_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !wmts_wrapper_module>
        LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<IfModule !receive_module>
        LoadModule receive_module modules/mod_receive.so
</IfModule>

<IfModule !reproject_module>
        LoadModule reproject_module modules/mod_reproject.so
</IfModule>

<IfModule !proxy_module>
    LoadModule proxy_module modules/mod_proxy.so
</IfModule>

<Directory {endpoint_path}>
        WMTSWrapperRole root
</Directory>

Alias "/oe2-wmts-endpoint" "{endpoint_path}"
"""

PROXY_TEMPLATE = """SSLProxyEngine on
ProxyPass {local_endpoint} {remote_endpoint}
ProxyPassReverse {local_endpoint} {remote_endpoint}
"""

PROXY_PREFIX = '/oe2-reproject-proxy'

MOD_TWMS_CONFIG_TEMPLATE = """<Directory {endpoint_path}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {endpoint_path}/twms/{layer}/twms.config
</Directory>
"""

TWMS_MODULE_TEMPLATE = """<IfModule !twms_module>
    LoadModule twms_module modules/mod_twms.so
</IfModule>
"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
SkippedLevels {skipped_levels}
BoundingBox {bbox}
SourcePath {endpoint_path}/{layer_id}/default/${date}/{tilematrixset}
SourcePostfix {source_postfix}
"""


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str


def get_matrix(matrix):
    return {
        'scale_denominator': float(matrix.findtext('{*}ScaleDenominator')),
        'top_left_corner': list(map(float, matrix.findtext(
            '{*}TopLeftCorner').split(' '))),
        'width': int(matrix.findtext('{*}TileWidth')),
        'height': int(matrix.findtext('{*}TileHeight')),
        'matrix_width': int(matrix.findtext('{*}MatrixWidth')),
        'matrix_height': int(matrix.findtext('{*}MatrixHeight')),
        'tile_width': int(matrix.findtext('{*}TileWidth')),
        'tile_height': int(matrix.findtext('{*}TileHeight')),
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

    tms_sets = next(elem.findall('{*}TileMatrixSet') for elem in main_xml.findall(
        '{*}Projection') if elem.attrib.get("id") == target_proj)
    return map(parse_tms_set_xml, tms_sets)


def get_max_scale_denominator(tms):
    return sorted([matrix['scale_denominator']
                   for matrix in tms['matrices']])[0]


def get_reprojected_tilematrixset(target_proj, source_tms_defs, target_tms_defs, layer_xml):
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    base_scale_denom = get_max_scale_denominator(source_tms)

    def get_closest_tms(acc, tms):
        if not acc or get_max_scale_denominator(acc) > get_max_scale_denominator(tms) > base_scale_denom:
            return tms
        return acc
    return reduce(get_closest_tms, target_tms_defs)


def get_source_tms(source_tms_defs, layer_xml):
    tms_id = layer_xml.find(
        '{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')
    return next(tms for tms in source_tms_defs if tms[
        'identifier'] == tms_id)


def get_src_size(source_tms_defs, layer_xml):
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    width = math.ceil(2 * math.pi * EARTH_RADIUS /
                      (get_max_scale_denominator(source_tms) * 0.28E-3))
    height = width
    if source_tms['matrices'][0]['matrix_width'] / source_tms['matrices'][0]['matrix_height'] == 2:
        height = width // 2
    return [width, height]


def format_source_url(source_url, reproj_tms):
    return re.sub(r'(.*{TileMatrixSet})(.*)', r'\1', source_url).replace('{Time}', '${date}').replace('{TileMatrixSet}', reproj_tms['identifier'])


def make_proxy_config(proxy_path):
    return bulk_replace(PROXY_TEMPLATE, [
        ('{remote_endpoint}', proxy_path['remote_path']),
        ('{local_endpoint}', proxy_path['local_path'])])


def format_source_uri_for_proxy(uri, proxy_paths):
    for proxy_path in proxy_paths:
        if proxy_path['remote_path'] in uri:
            return uri.replace(proxy_path['remote_path'], proxy_path['local_path'])


def parse_layer_gc_xml(target_proj, source_tms_defs, target_tms_defs, layer_xml):
    src_size = get_src_size(source_tms_defs, layer_xml)
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    reproj_tms = get_reprojected_tilematrixset(
        target_proj, source_tms_defs, target_tms_defs, layer_xml)
    return {
        'layer_id': layer_xml.findtext('{*}Identifier'),
        'source_url_template': format_source_url(layer_xml.find('{*}ResourceURL').attrib.get('template'), source_tms),
        'mimetype': layer_xml.find('{*}ResourceURL').attrib.get('format'),
        'time_enabled': any(len(dimension)for dimension in layer_xml.findall('{*}Dimension') if dimension.findtext('{*}Identifier') == 'time'),
        'tilematrixset': reproj_tms,
        'src_size_x': src_size[0],
        'src_size_y': src_size[1],
        'reproj_size_x': reproj_tms['matrices'][-1]['matrix_width'] * reproj_tms['matrices'][-1]['tile_width'],
        'reproj_size_y': reproj_tms['matrices'][-1]['matrix_height'] * reproj_tms['matrices'][-1]['tile_height'],
        'tile_size_x': source_tms['matrices'][0]['tile_width'],
        'tile_size_y': source_tms['matrices'][0]['tile_height'],
        'reproj_tile_size_x': reproj_tms['matrices'][0]['tile_width'],
        'reproj_tile_size_y': reproj_tms['matrices'][0]['tile_height'],
        'projection': source_tms['projection'],
        'reproj_projection': reproj_tms['projection'],
        'bbox': (source_tms['matrices'][0]['top_left_corner'][0], source_tms['matrices'][0]['top_left_corner'][1] * -1, source_tms['matrices'][0]['top_left_corner'][0] * -1, source_tms['matrices'][0]['top_left_corner'][1]),
        'reproj_bbox': (reproj_tms['matrices'][0]['top_left_corner'][0], reproj_tms['matrices'][0]['top_left_corner'][1] * -1, reproj_tms['matrices'][0]['top_left_corner'][0] * -1, reproj_tms['matrices'][0]['top_left_corner'][1])
    }


def get_gc_xml(source_gc_uri):
    r = requests.get(source_gc_uri)
    if r.status_code != 200:
        print(f"Can't get source GetCapabilities file: {source_gc_uri}")
        sys.exit()

    try:
        gc_xml = etree.fromstring(r.content)
    except etree.XMLSyntaxError:
        print('Problem with source GetCapabilities file -- not valid XML')
        sys.exit()
    return gc_xml


def make_apache_layer_config(endpoint_config, layer_config, make_twms=False):
    apache_config = bulk_replace(MOD_REPROJECT_APACHE_TEMPLATE, [
                                 ('{time_enabled}', 'On' if layer_config[
                                  'time_enabled'] else 'Off'),
                                 ('{endpoint_path}', endpoint_config[
                                  'endpoint_config_base_location']),
                                 ('{layer_id}', layer_config['layer_id']),
                                 ('{tilematrixset}', layer_config['tilematrixset']['identifier'])])
    if layer_config['time_enabled']:
        date_service_uri = endpoint_config['date_service_uri']
        date_service_snippet = f'\n        WMTSWrapperTimeLookupUri "{date_service_uri}"'
        apache_config = re.sub(r'(WMTSWrapperEnableTime.*)',
                               r'\1' + date_service_snippet, apache_config)
    if make_twms:
        twms_config = bulk_replace(MOD_TWMS_CONFIG_TEMPLATE, [('{endpoint_path}', endpoint_config[
            'endpoint_config_base_location'])])
        apache_config += '\n' + twms_config

    return apache_config


def make_mod_reproject_configs(endpoint_config, layer_config):
    src_config = bulk_replace(MOD_REPROJECT_SOURCE_TEMPLATE, [
        ('{size_x}', str(layer_config['src_size_x'])),
        ('{size_y}', str(layer_config['src_size_y'])),
        ('{bands}', "4" if layer_config[
            'mimetype'] == 'image/png' else "3"),
        ('{tile_size_x}', str(
            layer_config['tile_size_x'])),
        ('{tile_size_y}', str(
            layer_config['tile_size_y'])),
        ('{projection}', layer_config['projection']),
        ('{bbox}', ','.join(
            map(str, layer_config['bbox']))),
        ('{skipped_levels}', '1' if layer_config['projection'] == 'EPSG:4326' else '0')])

    reproj_config = bulk_replace(MOD_REPROJECT_REPRO_TEMPLATE, [
        ('{size_x}', str(layer_config['reproj_size_x'])),
        ('{size_y}', str(
            layer_config['reproj_size_y'])),
        ('{bands}', "4" if layer_config[
            'mimetype'] == 'image/png' else "3"),
        ('{tile_size_x}', str(
            layer_config['reproj_tile_size_x'])),
        ('{tile_size_y}', str(
            layer_config['reproj_tile_size_y'])),
        ('{projection}', str(
            layer_config['reproj_projection'])),
        ('{mimetype}', layer_config["mimetype"]),
        ('{bbox}', ','.join(map(str, layer_config['reproj_bbox']))),
        ('{postfix}', MIME_TO_EXTENSION[layer_config['mimetype']]),
        ('{source_path}', format_source_uri_for_proxy(layer_config[
         'source_url_template'], endpoint_config['proxy_paths'])),
        ('{nearest}', 'Off' if mimetype == 'image/jpeg' else 'On')])

    twms_config = bulk_replace(
        LAYER_MOD_TWMS_CONFIG_TEMPLATE, [
            ('{size_x}', str(layer_config['reproj_size_x'])),
            ('{size_y}', str(
                layer_config['reproj_size_y'])),
            ('{bands}', "4" if layer_config[
                'mimetype'] == 'image/png' else "3"),
            ('{tile_size_x}', str(
                layer_config['reproj_tile_size_x'])),
            ('{tile_size_y}', str(
                layer_config['reproj_tile_size_y'])),
            ('{skipped_levels}', '1' if layer_config[
             'projection'] == 'EPSG:4326' else '0'),
            ('{bbox}', ','.join(map(str, layer_config[
             'reproj_bbox']))),
            ('{endpoint_path}', '/oe2-wmts-endpoint'),
            ('{layer_id}', layer_config['layer_id']),
            ('{tilematrixset}', layer_config['tilematrixset']['identifier']),
            ('{source_postfix}', MIME_TO_EXTENSION[layer_config['mimetype']]),
        ])
    if not layer_config['time_enabled']:
        twms_config.replace('${date}/', '')

    return {'layer_id': layer_config['layer_id'],
            'tilematrixset': layer_config['tilematrixset']['identifier'],
            'src_config': src_config, 'reproj_config': reproj_config, 'twms_config': twms_config}


def get_proxy_paths(layers):
    proxy_paths = []
    for layer_config in layers:
        data_file_uri = re.sub(r'(.*)\/\${date}', r'\1',
                               layer_config['source_url_template'])
        url_parts = urlsplit(data_file_uri)
        remote_path = f'{url_parts.scheme}://{url_parts.netloc}'
        if not any(path for path in proxy_paths if path['remote_path'] == remote_path):
            proxy_paths.append({'local_path': f'{PROXY_PREFIX}-{url_parts.scheme}-{url_parts.netloc.replace(".", "-")}', 'remote_path': remote_path})
    return proxy_paths


def build_configs(endpoint_config, make_twms=False):
    # Check endpoint configs for necessary stuff
    try:
        target_proj = endpoint_config['target_epsg_code']
        source_gc_uri = endpoint_config['source_gc_uri']
        endpoint_config_base_location = endpoint_config[
            'endpoint_config_base_location']
        endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    # Get output TMS definitions (provided by local file)
    if not endpoint_config.get('tms_defs_file'):
        print('\nNo Tile Matrix Set definition file defined by endpoint config or command line parameters. Using ./tilematrixsets.xml')
        endpoint_config['tms_defs_file'] = 'tilematrixsets.xml'

    target_tms_defs = list(parse_tms_xml(
        endpoint_config['tms_defs_file'], target_proj))

    # Download and parse the source GC file, getting the layers and their
    # tilematrixsets
    gc_xml = get_gc_xml(source_gc_uri)
    source_tms_defs = list(map(parse_tms_set_xml, gc_xml.find(
        '{*}Contents').findall('{*}TileMatrixSet')))

    layers = list(map(partial(parse_layer_gc_xml, target_proj, source_tms_defs,
                              target_tms_defs), gc_xml.iter('{*}Layer')))

    # Build configs for each layer
    endpoint_config['proxy_paths'] = get_proxy_paths(layers)

    layer_apache_configs = map(
        partial(make_apache_layer_config, endpoint_config, make_twms=make_twms), layers)
    layer_module_configs = map(
        partial(make_mod_reproject_configs, endpoint_config), layers)

    # Write out layer configs
    for layer_config in layer_module_configs:
        config_path = Path(endpoint_config_base_location,
                           layer_config['layer_id'], 'default', layer_config['tilematrixset'])
        config_path.mkdir(parents=True, exist_ok=True)
        Path(config_path,
             'source.config').write_text(layer_config['src_config'])
        Path(config_path, 'reproject.config').write_text(
            layer_config['reproj_config'])
        if make_twms:
            config_path = Path(endpoint_config_base_location,
                               'twms', layer_config['layer_id'])
            config_path.mkdir(parents=True, exist_ok=True)
            Path(config_path, 'twms.config'). write_text(
                layer_config['twms_config'])

    print(f'\nLayer configs written to {endpoint_config_base_location}\n')

    # Write out Apache config
    apache_config_path = Path('/etc/httpd/conf.d/oe2-reproject-service.conf')
    try:
        apache_config_path = Path(endpoint_config['apache_config_location'])
    except KeyError:
        print(f'"apache_config_location" not found in endpoint config, saving Apache config to {apache_config_path}\n')
        pass

    Path(apache_config_path.parent).mkdir(parents=True, exist_ok=True)
    apache_config_str = MAIN_APACHE_CONFIG_TEMPLATE.replace(
        '{endpoint_path}', endpoint_config_base_location)
    print(make_proxy_config(endpoint_config['proxy_paths'][0]))
    apache_config_str += '\n' + '\n'.join(make_proxy_config(proxy_path)
                                          for proxy_path in endpoint_config['proxy_paths'])
    if make_twms:
        apache_config_str += '\n' + TWMS_MODULE_TEMPLATE
    apache_config_str += '\n' + '\n'.join(layer_apache_configs)
    apache_config_path.write_text(apache_config_str)
    print(f'Apache config written to {apache_config_path.as_posix()}\n')

    print('All configurations written. Restart Apache for the changes to take effect.')


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Configure mod_reproject.')
    parser.add_argument('endpoint_config', type=str,
                        help='an endpoint config YAML file')
    parser.add_argument('-t', '--make_twms', action='store_true',
                        help='Generate TWMS configurations')
    parser.add_argument('-x', '--tms_defs', type=str,
                        help='TileMatrixSets definition XML file')
    args = parser.parse_args()

    endpoint_config = yaml.load(Path(args.endpoint_config).read_text())
    if args.tms_defs:
        endpoint_config['tms_defs_file'] = args.tms_defs
    build_configs(endpoint_config, make_twms=args.make_twms)
