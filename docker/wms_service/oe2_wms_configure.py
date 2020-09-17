#!/bin/python

import argparse
import requests
import sys
import yaml
import shutil
import time
from lxml import etree
from pathlib import Path
from decimal import Decimal

MAPFILE_TEMPLATE = 'template.map'
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

def get_map_bounds(bbox, epsg, scale_denominator, tilesize, matrix_width, matrix_height):
    upper_left_x, lower_right_y, lower_right_x, upper_left_y = bbox
    pixelsize = Decimal(str(0.00028))
    if epsg == "EPSG:4326":
        units = Decimal(str(111319.490793274)) # convert to meters
    else:
        units = Decimal(str(1))
    size = round((tilesize*2)*(scale_denominator/units)*(pixelsize/2),8)
    lower_right_y = str((-1*size*matrix_height) + Decimal(upper_left_y))
    lower_right_x = str(Decimal(upper_left_x) + size*matrix_width)
    return [upper_left_x, lower_right_y, lower_right_x, upper_left_y]

def get_tile_level(tms, tilematrixsets):
    tile_level = 0
    for tilematrixset in tilematrixsets:
        if tilematrixset.findtext('{*}Identifier') == tms:
            tile_level = len(tilematrixset.findall('{*}TileMatrix')) - 1
    return str(tile_level)

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
projection = endpoint_config['epsg_code']

# Get source GetCapabilities
gc_url = endpoint_config['mapserver']['source_wmts_gc_uri']
print('Fetching ' + gc_url)
attempt = 1
retries = 10
duration = 30 # in seconds
try:
    r = requests.get(gc_url)
    if r.status_code != 200:
        print("Can't get GetCapabilities file from url " + gc_url)
        sys.exit()
except:
    while attempt < retries:
        time.sleep(duration)
        attempt = attempt + 1
        try:
            r = requests.get(gc_url)
            if r.status_code == 200:
                break
        except:
            print("Failed attempt " + str(attempt) + " to connect to " + gc_url)
    if attempt == retries:
        print("Can't get GetCapabilities file from url " + gc_url)
        sys.exit()

# Read GetCapabilities
root = etree.fromstring(r.content)
layers = root.find('{*}Contents').findall('{*}Layer')
layer_strings = []

tilematrixsets = root.find('{*}Contents').findall('{*}TileMatrixSet')
tm = tilematrixsets[0].findall('{*}TileMatrix')
scale_denominator = Decimal(tm[0].findtext('{*}ScaleDenominator'))
tile_width = int(tm[0].findtext('{*}TileWidth'))
tile_height = int(tm[0].findtext('{*}TileHeight'))
matrix_width = int(tm[0].findtext('{*}MatrixWidth'))
matrix_height = int(tm[0].findtext('{*}MatrixHeight'))

for layer in layers:
    layer_name = layer.findtext('{*}Identifier')
    tms = layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')
    bbox = layer.find('{*}BoundingBox')
    if bbox is None:
        bbox = layer.find('{*}WGS84BoundingBox')

    upper_left_x = bbox.findtext('{*}LowerCorner').split(' ')[0]
    upper_left_y = bbox.findtext('{*}UpperCorner').split(' ')[1]
    lower_right_x = bbox.findtext('{*}UpperCorner').split(' ')[0]
    lower_right_y = bbox.findtext('{*}LowerCorner').split(' ')[1]
    
    bounds = get_map_bounds([upper_left_x, lower_right_y, lower_right_x, upper_left_y], projection, scale_denominator, tile_width, matrix_width, matrix_height)

    resource_url = layer.find('{*}ResourceURL')
    bands_count = 4 if resource_url.get('format') == 'image/png' else 3
    template_string = resource_url.get('template')
    # Replace matching host names with local Docker host IP http://172.17.0.1 so that connections stay local
    if endpoint_config['mapserver'].get('replace_with_local'):
        replace_with_local = endpoint_config['mapserver']['replace_with_local']
        template_string = template_string.replace(replace_with_local, 'http://172.17.0.1:8080')

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
            if attributes['{http://www.w3.org/1999/xlink}role'].endswith("horizontal"):
                style_info = STYLE_TEMPLATE.replace('{width}', attributes["width"]).replace('{height}', attributes["height"]).replace('{href}', attributes['{http://www.w3.org/1999/xlink}href']).replace(".svg",".png")

    out_root = etree.Element('GDAL_WMS')

    service_element = etree.SubElement(out_root, 'Service')
    service_element.set('name', 'TMS')
    etree.SubElement(service_element, 'ServerUrl').text = template_string.replace(
        '{TileMatrixSet}', tms).replace('{Time}', '%time%').replace('{TileMatrix}', '${z}').replace('{TileRow}', '${y}').replace('{TileCol}', '${x}')

    data_window_element = etree.SubElement(out_root, 'DataWindow')
    etree.SubElement(data_window_element, 'UpperLeftX').text = str(bounds[0])
    etree.SubElement(data_window_element, 'UpperLeftY').text = str(bounds[3])
    etree.SubElement(data_window_element, 'LowerRightX').text = str(bounds[2])
    etree.SubElement(data_window_element, 'LowerRightY').text = str(bounds[1])
    etree.SubElement(data_window_element, 'TileLevel').text = get_tile_level(tms, tilematrixsets)
    etree.SubElement(data_window_element, 'TileCountX').text = str(matrix_width)
    etree.SubElement(data_window_element, 'TileCountY').text = str(matrix_height)
    etree.SubElement(data_window_element, 'YOrigin').text = 'top'

    etree.SubElement(out_root, 'Projection').text = projection
    etree.SubElement(out_root, 'BlockSizeX').text = str(tile_width)
    etree.SubElement(out_root, 'BlockSizeY').text = str(tile_height)
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

with open(str(outfilename)+'_tmp', 'w+', encoding='utf-8') as outfile:
    outfile.write(header_string)
    for layer_string in layer_strings:
        outfile.write(layer_string)
        outfile.write('\n')
    outfile.write('END')
shutil.move(str(outfilename)+'_tmp', outfilename)
print('Generated ' + str(outfilename))

with open(APACHE_CONFIG, 'r+', encoding='utf-8') as apache_config:
    config_string = apache_config.read()
    directory_string = APACHE_CONFIG_TEMPLATE.replace('{internal_endpoint}', str(internal_endpoint)).replace('{mapfile_location}', str(outfilename))
    if not directory_string in config_string:
        apache_config.write(directory_string)
        apache_config.write('\n')
        print('Updated ' + APACHE_CONFIG)