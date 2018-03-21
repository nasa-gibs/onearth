#!/bin/python

import requests
import sys
from lxml import etree

GC_URL = 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml'
TEMPLATE = 'template.map'
HEADER = 'header.map'
TILE_LEVELS = {'2km': '5', '1km': '6', '500m': '7', '250m': '8',
               '125m': '9', '62.5m': '10', '31.25m': '11', '15.625m': '12'}

r = requests.get(GC_URL)

try:
    outfilename = sys.argv[1]
except IndexError:
    print 'No output file specified!'
    sys.exit()

if (r.status_code != 200):
    print "Cant' get GC file from url" + GC_URL
    sys.exit()

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

    dimension = layer.find('{*}Dimension')
    has_time = dimension is not None and dimension.findtext(
        '{*}Identifier') == 'time' or False

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

    etree.SubElement(out_root, 'Projection').text = 'EPSG:4326'
    etree.SubElement(out_root, 'BlockSizeX').text = '512'
    etree.SubElement(out_root, 'BlockSizeY').text = '512'
    etree.SubElement(out_root, 'BandsCount').text = str(bands_count)

    etree.SubElement(out_root, 'Cache')
    etree.SubElement(out_root, 'ZeroBlockHttpCodes').text = '404,400'
    etree.SubElement(out_root, 'ZeroBlockOnServerException').text = 'true'

    with open(TEMPLATE, 'r') as f:
        template_string = f.read()
    template_string = template_string.replace('${layer_name}', layer_name).replace(
        '${data_xml}', etree.tostring(out_root))

    layer_strings.append(template_string)

with open(HEADER, 'r') as f:
    header_string = f.read()

with open(outfilename, 'w+') as outfile:
    outfile.write(header_string)
    for layer_string in layer_strings:
        outfile.write(layer_string)
        outfile.write('\n')
    outfile.write('END')
