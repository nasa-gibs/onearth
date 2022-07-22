#!/usr/bin/env python3

import argparse
import requests
import sys
import yaml
import shutil
import time
import re
from lxml import etree
from pathlib import Path
from decimal import Decimal

MAPFILE_TEMPLATE = 'template.map'
APACHE_CONFIG = '/etc/httpd/conf.d/oe2_wms.conf'
APACHE_CONFIG_TEMPLATE = """<Directory {redirect_endpoint}>
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
            {shapefile_validation}
        END
"""
STR_BYTES_REMOVAL = re.compile(r"^b'(.*)'$")


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

def strip_decode_bytes_format(string):
    # interpret any bytes in the string
    string = string.encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8')
    match = STR_BYTES_REMOVAL.match(string)
    if match:
        return match.group(match.lastindex)
    return string

def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], str(item[1]))
    return out_str

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
            if filepath.is_file() and filepath.name.endswith('.yaml')
        ]

def get_gc(url):
    # Get source GetCapabilities
    print('Fetching ' + url)
    attempt = 1
    retries = 10
    duration = 30 # in seconds
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print("Can't get GetCapabilities file from url " + gc_url)
            sys.exit()

        return r.content
    except:
        while attempt < retries:
            time.sleep(duration)
            attempt = attempt + 1
            print("Failed attempt " + str(attempt) + " to connect to " + gc_url)
            try:
                r = requests.get(gc_url)
                if r.status_code == 200:
                    break
            except Exception as e:
                print("ERROR:", e)
        if attempt == retries:
            print("Can't get GetCapabilities file from url " + gc_url)
            sys.exit()

# Parse arguments
parser = argparse.ArgumentParser(description='Make WMS endpoint.')
parser.add_argument('endpoint_config', type=str, help='an endpoint config YAML file')
parser.add_argument('--shapefile_bucket', dest='shapefile_bucket', type=str, default='', help='S3 bucket used for shapefiles')
args = parser.parse_args()
endpoint_config = yaml.safe_load(Path(args.endpoint_config).read_text())
print('Using endpoint config ' + args.endpoint_config)
if args.shapefile_bucket != '':
    print('Using shapefile bucket ' + args.shapefile_bucket)
    shapefile_bucket = '/vsis3/' + args.shapefile_bucket
else:
    shapefile_bucket = ''
outfilename = Path(endpoint_config['mapserver']['mapfile_location'])
header = Path(endpoint_config['mapserver']['mapfile_header'])
redirect_endpoint = Path(strip_trailing_slash(endpoint_config['mapserver']['redirect_endpoint']))
epsg_code = endpoint_config['epsg_code']

# Get layer configs
layer_configs = get_layer_configs(endpoint_config)

# Get source GetCapabilities
gc_url = endpoint_config['mapserver']['source_wmts_gc_uri']
# Replace matching host names with local Docker host IP http://172.17.0.1 so that connections stay local
if endpoint_config['mapserver'].get('replace_with_local'):
    replace_with_local = endpoint_config['mapserver']['replace_with_local']
    gc_url = gc_url.replace(replace_with_local, 'http://172.17.0.1:8080')

gc_content = get_gc(gc_url)

# Read GetCapabilities
root = etree.fromstring(gc_content)
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
    web_mercator = None
    layer_name = layer.findtext('{*}Identifier')
    tms = layer.find('{*}TileMatrixSetLink').findtext('{*}TileMatrixSet')
    bbox = layer.find('{*}BoundingBox')
    if bbox is None:
        bbox = layer.find('{*}WGS84BoundingBox')

    upper_left_x = bbox.findtext('{*}LowerCorner').split(' ')[0]
    upper_left_y = bbox.findtext('{*}UpperCorner').split(' ')[1]
    lower_right_x = bbox.findtext('{*}UpperCorner').split(' ')[0]
    lower_right_y = bbox.findtext('{*}LowerCorner').split(' ')[1]
    
    bounds = get_map_bounds([upper_left_x, lower_right_y, lower_right_x, upper_left_y], epsg_code, scale_denominator, tile_width, matrix_width, matrix_height)

    resource_url = layer.findall('{*}ResourceURL')[0] # get first if multiple found
    bands_count = 4 if resource_url.get('format') == 'image/png' else 3
    template_string = resource_url.get('template')
    # Replace matching host names with local Docker host IP http://172.17.0.1 so that connections stay local
    if endpoint_config['mapserver'].get('replace_with_local'):
        replace_with_local = endpoint_config['mapserver']['replace_with_local']
        template_string = template_string.replace(replace_with_local, 'http://172.17.0.1:8080')

    dimension_info = ''
    validation_info = VALIDATION_TEMPLATE
    style_info = ''
    
    dimension = layer.find('{*}Dimension')
    has_time = dimension is not None and dimension.findtext('{*}Identifier') == 'Time' or False
    if has_time:
        default_datetime = dimension.findtext('{*}Default')
        period_str = ','.join(elem.text for elem in dimension.findall("{*}Value"))
        dimension_info = DIMENSION_TEMPLATE.replace('{periods}', period_str).replace('{default}', default_datetime)
        validation_info = VALIDATION_TEMPLATE.replace('{default}', default_datetime)

    # find the corresponding layer configuration and check the mime_type to see if it is vector data we should get from S3
    layer_config = next((lc for lc in layer_configs if layer_name + ".yaml" in lc['path']), False)
    wms_layer_group = ""
    if layer_config:
        try:
            wms_layer_group = '"wms_layer_group"       "{0}"'.format(layer_config['config']['wms_layer_group'])
        except KeyError:
            print("WARN: Layer config {0} has no field 'wms_layer_group'".format(layer_config['path']))
    else:
        print("WARN: Layer config for layer {0} not found".format(layer_name))

    wms_srs    = "{0}".format(epsg_code)
    if epsg_code == "EPSG:4326":
        if layer_config and 'web_mercator_config_path' in layer_config["config"]:
            gc_3857 = get_gc(gc_url.replace("4326", "3857"))
            root = etree.fromstring(gc_3857)

            tilematrixsets = root.find('{*}Contents').findall('{*}TileMatrixSet')
            tm = tilematrixsets[0].findall('{*}TileMatrix')
            scale_denominator = Decimal(tm[0].findtext('{*}ScaleDenominator'))
            tile_width = int(tm[0].findtext('{*}TileWidth'))
            tile_height = int(tm[0].findtext('{*}TileHeight'))
            matrix_width = int(tm[0].findtext('{*}MatrixWidth'))
            matrix_height = int(tm[0].findtext('{*}MatrixHeight'))

            wm_layer_config = get_layer_config(Path(layer_config["config"]["web_mercator_config_path"]))    
            web_mercator = False
            wms_extent = wm_layer_config["config"]["source_mrf"]["bbox"]
            wms_srs    = wm_layer_config["config"]["projection"]
            layer_proj = wms_srs.lower()
            bounds = wm_layer_config["config"]["source_mrf"]["bbox"].split(",")
            tms = wm_layer_config["config"]["tilematrixset"]
        else:
            wms_extent = "-180 -90 180 90"
            # Explicitly show that EPSG:4326 and EPSG:3857 requests are supported through an EPSG:4326 endpoint
            wms_srs    = "EPSG:4326 EPSG:3857"
            layer_proj = epsg_code.lower()
    elif epsg_code in ["EPSG:3031", "EPSG:3413"]:
        # Hard coded to GIBS TileMatrixSet values. These are not the projection's native extents. If that's a problem,
        # then the values could be read from the remote Capabilities
        wms_extent = "-4194304 -4194304 4194304 4194304"
        layer_proj = epsg_code.lower()
    elif epsg_code in ["EPSG:3857"]:
        # You would think this should be the EPSG:3857 extents, but that doesn't work. Instead, these are in the units
        # of the layer's projection... which is EPSG:4326
        wms_extent = "-180, -85.0511, 180, 85.0511"
        # Hard coded to be epsg:4326 because we are building Web Mercator off of an EPSG:4326 WMTS endpoint with
        # EPSG:4326 shapefiles. If that's a problem, then we could add a new property to the endpoint config to specify
        # the source WMTS' projection and also a new property to the source_shapefile indicating its projection.
        layer_proj = "epsg:4326"
    else:
        wms_extent = "{0}, {1}, {2}, {3}".format(upper_left_x, lower_right_y, lower_right_x, upper_left_y)
        layer_proj = epsg_code.lower()
        break

    # handle vector layers
    if layer_config and resource_url.get('format') == 'application/vnd.mapbox-vector-tile':
        style_info = '"wms_enable_request"    "GetLegendGraphic"'
        with open(MAPFILE_TEMPLATE, 'r', encoding='utf-8') as f:
            template_string = f.read()
        try:
            for shp_config in layer_config['config']['shapefile_configs']:
                try:
                    with open(shp_config['layer_style'], 'r', encoding='utf-8') as f:
                        class_style = f.read()
                except FileNotFoundError:
                    class_style = ''
                    print('ERROR: layer_style file not found', shp_config['layer_style'])

                prefix = '/%{0}_PREFIX%'.format(shp_config['layer_id'])
                shapefile = '%{0}_SHAPEFILE%.shp'.format(shp_config['layer_id'])
                data_file_uri = Path(shp_config['source_shapefile']['data_file_uri'].replace('{SHAPEFILE_BUCKET}', shapefile_bucket) + prefix + shapefile)

                shapefile_validation = '''"{0}_PREFIX"   "^."
            "default_{0}_PREFIX"          ""
            "{0}_SHAPEFILE"   "^."
            "default_{0}_SHAPEFILE"          ""
            '''.format(shp_config['layer_id'])
                validation_info = VALIDATION_TEMPLATE.replace('{shapefile_validation}', shapefile_validation)
                
                if default_datetime:
                    validation_info = validation_info.replace('{default}', default_datetime)

                new_layer_string = bulk_replace(template_string, [('${layer_name}', shp_config['layer_id']),
                                                                  ('${layer_type}', shp_config['source_shapefile']['feature_type']),
                                                                  ('${layer_title}', strip_decode_bytes_format(shp_config['layer_title'])),
                                                                  ('${wms_extent}', wms_extent),
                                                                  ('${wms_srs}', wms_srs),
                                                                  ('${wms_layer_group}', wms_layer_group),
                                                                  ('${dimension_info}', ''),
                                                                  ('${style_info}', style_info),
                                                                  ('${data_xml}', 'CONNECTIONTYPE OGR\n        CONNECTION    \'{0}\''.format(data_file_uri)),
                                                                  ('${epsg_code}', layer_proj),
                                                                  ('${validation_info}', validation_info),
                                                                  ('${class_style}', class_style)])
                layer_strings.append(new_layer_string)

        except KeyError:
            # TODO: format for properly logging an error
            print("WARN: Vector layer config {0} has no field 'shapefile_configs'".format(layer_config['path']))
    # handle raster layers
    else:
        validation_info = validation_info.replace('{shapefile_validation}', '')
        out_root = etree.Element('GDAL_WMS')

        service_element = etree.SubElement(out_root, 'Service')
        service_element.set('name', 'TMS')
        if web_mercator == False:
            template_string = template_string.replace('4326', '3857')
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

        if web_mercator == False:
            etree.SubElement(out_root, 'Projection').text = layer_proj.upper()
        else:
            etree.SubElement(out_root, 'Projection').text = epsg_code
        etree.SubElement(out_root, 'BlockSizeX').text = str(tile_width)
        etree.SubElement(out_root, 'BlockSizeY').text = str(tile_height)
        etree.SubElement(out_root, 'BandsCount').text = str(bands_count)

        etree.SubElement(out_root, 'ZeroBlockHttpCodes').text = '404,400'
        etree.SubElement(out_root, 'ZeroBlockOnServerException').text = 'true'

        legendUrlElems = []
        for styleElem in layer.findall('{*}Style'):
           legendUrlElems.extend(styleElem.findall('{*}LegendURL'))
        for legendUrlElem in legendUrlElems:
            attributes = legendUrlElem.attrib
            if attributes['{http://www.w3.org/1999/xlink}role'].endswith("horizontal"):
                style_info = STYLE_TEMPLATE.replace('{width}', attributes["width"]).replace('{height}', attributes["height"]).replace('{href}', attributes['{http://www.w3.org/1999/xlink}href']).replace(".svg",".png")
        
        with open(MAPFILE_TEMPLATE, 'r', encoding='utf-8') as f:
            template_string = f.read()

        template_string = bulk_replace(template_string, [('${layer_name}', layer_name),
                                                         ('${layer_title}', layer_name),
                                                         ('${layer_type}', 'RASTER'),
                                                         ('${wms_extent}', wms_extent),
                                                         ('${wms_srs}', wms_srs),
                                                         ('${wms_layer_group}', wms_layer_group),
                                                         ('${dimension_info}', dimension_info),
                                                         ('${style_info}', style_info),
                                                         ('${data_xml}', 'DATA    \'{0}\''.format(etree.tostring(out_root).decode())),
                                                         ('${class_style}', ''),
                                                         ('${validation_info}', validation_info),
                                                         ('${epsg_code}', layer_proj)])
    
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
    directory_string = APACHE_CONFIG_TEMPLATE.replace('{redirect_endpoint}', str(redirect_endpoint)).replace('{mapfile_location}', str(outfilename))
    if not directory_string in config_string:
        apache_config.write(directory_string)
        apache_config.write('\n')
        print('Updated ' + APACHE_CONFIG)