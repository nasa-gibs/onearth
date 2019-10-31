#!/bin/python

import argparse
import requests
import sys
import yaml
from lxml import etree
from pathlib import Path

MAPFILE_TEMPLATE = 'template.map'
TILE_LEVELS = {'2km': '5', '1km': '6', '500m': '7', '250m': '8',
               '125m': '9', '62.5m': '10', '31.25m': '11', '15.625m': '12'}
APACHE_CONFIG = '/etc/httpd/conf.d/oe2_wms.conf'
APACHE_CONFIG_TEMPLATE = """<Directory {internal_endpoint}>
        SetHandler fcgid-script
        Options ExecCGI
        SetEnv MS_MAPFILE {mapfile_location}
</Directory>
"""
DIMENSION_TEMPLATE = """"wms_timeextent" "{periods}"
                "wms_timeitem" "TIME"
                "wms_timedefault" "{default}"
                "wms_timeformat" "YYYY-MM-DD, YYYY-MM-DDTHH:MM:SSZ"
"""
STYLE_TEMPLATE = """"wms_style" "default"
                "wms_style_default_legendurl_width" "{width}"
                "wms_style_default_legendurl_height" "{height}"
                "wms_style_default_legendurl_format" "image/png"
                "wms_style_default_legendurl_href" "{href}"
"""
VALIDATION_TEMPLATE = """
        VALIDATION
            "time"                  "^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z|[0-9]{4}-[0-9]{2}-[0-9]{2})|(default)$"
            "default_time"          "{default}"
        END
"""

def strip_trailing_slash(string):
    if string.endswith('/'):
        string = string[:-1]
    return string

# Parse arguments
parser = argparse.ArgumentParser(description='Make WMS endpoint.')
parser.add_argument('endpoint_config', type=str, help='an endpoint config YAML file')
args = parser.parse_args()
endpoint_config = yaml.safe_load(Path(args.endpoint_config).read_text())
print('Using endpoint config ' + args.endpoint_config)
outfilename = Path(endpoint_config['mapserver']['mapfile_location'])
header = Path(endpoint_config['mapserver']['mapfile_header'])
internal_endpoint = Path(strip_trailing_slash(endpoint_config['mapserver']['internal_endpoint']))
tms_defs_file = Path(endpoint_config['tms_defs_file'])
projection = endpoint_config['epsg_code']

# Get source GetCapabilities
gc_url = endpoint_config['mapserver']['source_wmts_gc_uri']
print('Fetching ' + gc_url)                   
r = requests.get(gc_url)
if (r.status_code != 200):
    print("Cant' get GC file from url" + gc_url)
    sys.exit()

# Read GetCapabilities
root = etree.fromstring(r.content)
layers = root.find('{*}Contents').findall('{*}Layer')
layer_strings = []

for layer in layers:
    layer_name = layer.findtext('{*}Identifier')
    tms = layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')
    bbox = layer.find('{*}WGS84BoundingBox')

    upper_left_x = bbox.findtext('{*}LowerCorner').split(' ')[0]
    upper_left_y = bbox.findtext('{*}UpperCorner').split(' ')[1]
    lower_right_x = bbox.findtext('{*}UpperCorner').split(' ')[0]
    lower_right_y = bbox.findtext('{*}LowerCorner').split(' ')[1]

    resource_url = layer.find('{*}ResourceURL')
    bands_count = 4 if resource_url.get('format') == 'image/png' else 3
    template_string = resource_url.get('template')

    dimension_info = ''
    validation_info = ''
    style_info = ''
    
    dimension = layer.find('{*}Dimension')
    has_time = dimension is not None and dimension.findtext('{*}Identifier') == 'Time' or False
    if has_time:
        default_datetime = dimension.findtext('{*}Default')
        period_str = ','.join(elem.text for elem in dimension.findall("{*}Value"))
        dimension_info = DIMENSION_TEMPLATE.replace('{periods}', period_str).replace('{default}', default_datetime)
        validation_info = VALIDATION_TEMPLATE.replace('{default}', default_datetime)
        
        legendUrlElems = []
        for styleElem in layer.findall('{*}Style'):
           legendUrlElems.extend(styleElem.findall('{*}LegendURL'))
        for legendUrlElem in legendUrlElems:
            attributes = legendUrlElem.attrib
            if attributes[xlink + 'role'].endswith("horizontal"):
                style_info = STYLE_TEMPLATE.replace('{width}', attributes["width"]).replace('{height}', attributes["height"]).replace('{href}', attributes[xlink + 'href']).replace(".svg",".png")

    out_root = etree.Element('GDAL_WMS')

    service_element = etree.SubElement(out_root, 'Service')
    service_element.set('name', 'TMS')
    etree.SubElement(service_element, 'ServerUrl').text = template_string.replace(
        '{TileMatrixSet}', tms).replace('{Time}', '%time%').replace('{TileMatrix}', '${z}').replace('{TileRow}', '${y}').replace('{TileCol}', '${x}')

    data_window_element = etree.SubElement(out_root, 'DataWindow')
    etree.SubElement(data_window_element, 'UpperLeftX').text = '-180.0'
    etree.SubElement(data_window_element, 'UpperLeftY').text = '90'
    etree.SubElement(data_window_element, 'LowerRightX').text = '396.0'
    etree.SubElement(data_window_element, 'LowerRightY').text = '-198'
    etree.SubElement(data_window_element, 'TileLevel').text = TILE_LEVELS[tms]
    etree.SubElement(data_window_element, 'TileCountX').text = '2'
    etree.SubElement(data_window_element, 'TileCountY').text = '1'
    etree.SubElement(data_window_element, 'YOrigin').text = 'top'

    etree.SubElement(out_root, 'Projection').text = projection
    etree.SubElement(out_root, 'BlockSizeX').text = '512'
    etree.SubElement(out_root, 'BlockSizeY').text = '512'
    etree.SubElement(out_root, 'BandsCount').text = str(bands_count)

    etree.SubElement(out_root, 'Cache')
    etree.SubElement(out_root, 'ZeroBlockHttpCodes').text = '404,400'
    etree.SubElement(out_root, 'ZeroBlockOnServerException').text = 'true'

    with open(MAPFILE_TEMPLATE, 'r', encoding='utf-8') as f:
        template_string = f.read()
    template_string = template_string.replace('${layer_name}', layer_name).replace('${dimension_info}', dimension_info).replace('${style_info}', style_info).replace(
        '${data_xml}', etree.tostring(out_root).decode()).replace('${epsg_code}', projection.lower()).replace('${validation_info}', validation_info)

    layer_strings.append(template_string)

with open(header, 'r', encoding='utf-8') as f:
    header_string = f.read()

with open(outfilename, 'w+', encoding='utf-8') as outfile:
    outfile.write(header_string)
    for layer_string in layer_strings:
        outfile.write(layer_string)
        outfile.write('\n')
    outfile.write('END')
    print('Generated ' + str(outfilename))

with open(APACHE_CONFIG, 'r+', encoding='utf-8') as apache_config:
    config_string = apache_config.read()
    directory_string = APACHE_CONFIG_TEMPLATE.replace('{internal_endpoint}', str(internal_endpoint)).replace('{mapfile_location}', str(outfilename))
    if not directory_string in config_string:
        apache_config.write(directory_string)
        apache_config.write('\n')
        print('Updated ' + APACHE_CONFIG)