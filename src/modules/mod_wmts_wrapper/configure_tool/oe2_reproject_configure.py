import argparse
import yaml
from pathlib import Path
from lxml import etree
import sys
import requests
from functools import partial, reduce
import re
import math

EARTH_RADIUS = 6378137.0
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


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str


def get_matrix(matrix):
    return {
        'scale_denominator': float(matrix.findtext('{*}ScaleDenominator')),
        'top_left_corner': map(float, matrix.findtext(
            '{*}TopLeftCorner').split(' ')),
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
        return 'ESPG:4326'
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


def parse_layer_gc_xml(target_proj, source_tms_defs, target_tms_defs, layer_xml):
    src_size = get_src_size(source_tms_defs, layer_xml)
    source_tms = get_source_tms(source_tms_defs, layer_xml)
    return {
        'layer_id': layer_xml.findtext('{*}Identifier'),
        'source_url_template': layer_xml.find('{*}ResourceURL').attrib.get('template'),
        'mimetype': layer_xml.find('{*}ResourceURL').attrib.get('format'),
        'time_enabled': any(len(dimension)for dimension in layer_xml.findall('{*}Dimension') if dimension.findtext('{*}Identifier') == 'time'),
        'tilematrixset': get_reprojected_tilematrixset(
            target_proj, source_tms_defs, target_tms_defs, layer_xml),
        'src_size_x': src_size[0],
        'src_size_y': src_size[1],
        'tile_size_x': source_tms['matrices'][0]['tile_width'],
        'tile_size_y': source_tms['matrices'][0]['tile_height'],
        'projection': source_tms['projection'],
        'bbox': (matrices[0]['top_left_corner'][0], matrices[0]['top_left_corner'][1], matrices[0]['top_left_corner'][0] * -1, matrices[0]['top_left_corner'][1] * -1)

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


def make_apache_layer_config(endpoint_config, layer_config):
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
                              ('{projection}', layer_config['projection'])])
    return src_config


def build_configs(endpoint_config):
    try:
        target_proj = endpoint_config['target_epsg_code']
        source_gc_uri = endpoint_config['source_gc_uri']
        endpoint_config['endpoint_config_base_location']
        endpoint_config['date_service_uri']
    except KeyError as err:
        print(f"Endpoint config is missing required config element {err}")

    target_tms_defs = list(parse_tms_xml(args.tms_defs, target_proj))
    gc_xml = get_gc_xml(source_gc_uri)
    source_tms_defs = list(map(parse_tms_set_xml, gc_xml.find(
        '{*}Contents').findall('{*}TileMatrixSet')))
    layers = map(partial(parse_layer_gc_xml, target_proj, source_tms_defs,
                         target_tms_defs), gc_xml.iter('{*}Layer'))
    layer_apache_configs = map(
        partial(make_apache_layer_config, endpoint_config), layers)
    layer_module_configs = map(
        partial(make_mod_reproject_configs, endpoint_config), layers)

    for layer in layer_module_configs:
        print(layer)

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
    build_configs(endpoint_config)
