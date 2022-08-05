#!/usr/bin/env python3

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

#
# Tests for GetCapabilities service
#

import os
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
import subprocess
import time
import redis
import requests
from oe_test_utils import restart_apache, make_dir_tree
import shutil
from lxml import etree
import json
from formencode.doctest_xml_compare import xml_compare
import math
from functools import partial

DEBUG = False
START_SERVER = False

EARTH_RADIUS = 6378137.0

DATE_SERVICE_LUA_TEMPLATE = """local onearthTimeService = require "onearthTimeService"
handler = onearthTimeService.timeService({handler_type="redis", host="127.0.0.1"}, {filename_format="hash"})
"""

DATE_SERVICE_APACHE_TEMPLATE = """Alias /date_service {config_path}

<IfModule !ahtse_lua>
        LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>

<Directory {config_path}>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
        AHTSE_lua_RegExp date_service
        AHTSE_lua_Script {config_path}/date_service.lua
        AHTSE_lua_Redirect On
        AHTSE_lua_KeepAlive On
</Directory>
"""

GC_SERVICE_LAYER_CONFIG_TEMPLATE = """
layer_id: "{layer_id}"
layer_title: "{layer_title}"
layer_name: "{layer_name}"
projection: "{projection}"
tilematrixset: "{tilematrixset}"
mime_type: "{mime_type}"
static: {static}
metadata: {metadata}
abstract: "{abstract}"
"""

GC_SERVICE_LUA_TEMPLATE = """local onearth_gc_gts = require "onearth_gc_gts"
local config = {
    layer_config_source="{layer_config_path}",
    tms_defs_file="{tms_defs_path}",
    gc_header_loc="{gc_header_path}",
    time_service_uri="{date_service_uri}",
    epsg_code="{src_epsg}",
    gc_header_file="{gc_header_path}",
    twms_gc_header_file="{twms_gc_header_path}",
    gts_header_file="{gts_header_path}",
    base_uri_gc="{base_uri_gc}",
    base_uri_gts="{base_uri_gts}",
    target_epsg_code="{target_epsg}",
    time_service_keys={date_service_keys}
}
handler = onearth_gc_gts.handler(config)
"""

GC_SERVICE_APACHE_CONFIG_TEMPLATE = """Alias {endpoint} {gc_path}

<IfModule !ahtse_lua>
    LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>

<Directory {gc_path}>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
        AHTSE_lua_RegExp {regexp}
        AHTSE_lua_Script {gc_lua_path}
        AHTSE_lua_Redirect On
        AHTSE_lua_KeepAlive On
</Directory>
"""

TEST_LAYERS = {
    'test_1': {
        'layer_id':
        'AMSR2_Snow_Water_Equivalent',
        'layer_title':
        'AMSR2 Snow Water Equivalent tileset',
        'layer_name':
        'Snow Water Equivalent (AMSR2, GCOM-W1)',
        'projection':
        'EPSG:4326',
        'tilematrixset':
        '2km',
        'mime_type':
        'image/jpeg',
        'static':
        'true',
        'abstract':
        'AMSR2 Snow Water Equivalent abstract',
        'metadata': [
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.0/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.2","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.2/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.3","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}'
        ]
    },
    'test_2': {
        'layer_id':
        'AMSR2_Snow_Water_Equivalent_dynamic',
        'layer_title':
        'AMSR2 Snow Water Equivalent tileset',
        'layer_name':
        'Snow Water Equivalent (AMSR2, GCOM-W1)',
        'projection':
        'EPSG:4326',
        'tilematrixset':
        '2km',
        'mime_type':
        'image/jpeg',
        'static':
        'false',
        'abstract':
        'AMSR2 Snow Water Equivalent abstract',
        'metadata': [
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.0/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.2","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.2/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}',
            '{"xlink:type": "simple", "xlink:role": "http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.3","xlink:href": "https://gibs.earthdata.nasa.gov/colormaps/v1.3/AMSR2_Snow_Water_Equivalent.xml", "xlink:title": "GIBS Color Map: Data - RGB Mapping"}'
        ],
        'default':
        '2012-01-01',
        'periods': [
            '2012-01-01/2016-01-01/P1Y',
            '2016-01-01T12:00:00/2018-01-01T12:00:00/PT1S'
        ]
    }
}

PROJECTIONS = {
    "EPSG:3031": {
        'wkt':
        'PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]',
        'bbox84': {
            'crs': "urn:ogc:def:crs:OGC:2:84",
            'lowerCorner': {-180, -90},
            'upperCorner': {180, -38.941373}
        },
        'bbox': {
            'crs': "urn:ogc:def:crs:EPSG::3031",
            'lowerCorner': {-4194304, -4194304},
            'upperCorner': {194304, 4194304}
        }
    },
    "EPSG:3413": {
        'wkt':
        'PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]',
        'bbox84': {
            'crs': "urn:ogc:def:crs:OGC:2:84",
            'lowerCorner': {-180, 8.807151},
            'upperCorner': {180, 90}
        },
        'bbox': {
            'crs': "urn:ogc:def:crs:EPSG::3413",
            'lowerCorner': {-4194304, -4194304},
            'upperCorner': {4194304, 4194304}
        }
    },
    "EPSG:3857": {
        'wkt':
        'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]',
        'bbox84': {
            'crs': "urn:ogc:def:crs:OGC:2:84",
            'lowerCorner': {-180, -85},
            'upperCorner': {180, 85}
        },
        'bbox': {
            'crs': "urn:ogc:def:crs:EPSG::3857",
            'lowerCorner': {-20037508.34278925, -20037508.34278925},
            'upperCorner': {20037508.34278925, 20037508.34278925}
        }
    },
    "EPSG:4326": {
        'wkt':
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
        'bbox84': {
            'crs': "urn:ogc:def:crs:OGC:2:84",
            'lowerCorner': {-180, -90},
            'upperCorner': {180, 90}
        },
    }
}


def strip_ns(dom):
    for elem in dom.iter():
        elem.tag = etree.QName(elem).localname


def redis_running():
    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        return r.ping()
    except redis.exceptions.ConnectionError:
        return False


def seed_redis_data(layers, db_keys=None):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'
    for layer in layers:
        r.set('{0}layer:{1}:default'.format(db_keystring, layer[0]), layer[1])
        for period in layer[2]:
            r.sadd('{0}layer:{1}:periods'.format(db_keystring, layer[0]),
                   period)


def remove_redis_layer(layer, db_keys=None):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'
    r.delete('{0}layer:{1}:default'.format(db_keystring, layer[0]))
    r.delete('{0}layer:{1}:periods'.format(db_keystring, layer[0]))


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], item[1])
    return out_str


def make_tile_pattern(layer, epsg_code, bbox, matrix):
    widthInPx = math.ceil(
        2 * math.pi * EARTH_RADIUS /
        (float(matrix.findtext("{*}ScaleDenominator")) * 0.28E-3))
    heightInPx = widthInPx / 2 if epsg_code == "EPSG:4326" else widthInPx
    matrix_width = int(matrix.findtext('{*}MatrixWidth'))
    matrix_height = int(matrix.findtext('{*}MatrixHeight'))
    tile_width = int(matrix.findtext('{*}TileWidth'))
    tile_height = int(matrix.findtext('{*}TileHeight'))
    widthRatio = widthInPx / (tile_width * matrix_width)
    heightRatio = heightInPx / (tile_height * matrix_height)
    resx = math.ceil((bbox['upperCorner'][0] - bbox['lowerCorner'][0]) /
                     (matrix_width * widthRatio))
    resy = math.ceil((bbox["upperCorner"][1] - bbox["lowerCorner"][1]) /
                     (matrix_height * heightRatio))
    top_left = list(map(float, matrix.findtext('{*}TopLeftCorner').split(' ')))
    xmax = top_left[0] + resx
    ymax = top_left[1] - resy
    template = "request=GetMap&layers={layer}&srs={epsg_code}&format={mime_type}&styles={time}&width={width}&height={height}&bbox={bbox}"

    def make_uri(hasTime):
        time = "{time}" if hasTime else ""
        bbox_str = ",".join(
            map(lambda x: '0' if x < 1 and x > -1 else '{0:.6f}'.format(x),
                map(float, [top_left[0], ymax, xmax, top_left[1]])))
        return bulk_replace(template, [("{layer}", layer['layer_id']),
                                       ("{epsg_code}", epsg_code),
                                       ("{mime_type}", layer['mime_type']),
                                       ("{time}", time),
                                       ("{width}", str(tile_width)),
                                       ("{height}", str(tile_height)),
                                       ("{bbox}", bbox_str)])

    outString = make_uri(
        False) if layer['static'] else make_uri(True) + "\n" + make_uri(False)
    outString = "<![CDATA[" + outString + "]]>"
    return outString


class TestDateService(unittest.TestCase):
    @classmethod
    def write_config_for_test_layer(self, layer):
        replacement_strs = [('{' + key + '}', value)
                            for key, value in layer.items()
                            if key not in ['metadata', 'default', 'periods']]
        metadata = '\n' + '\n'.join(['  - ' + m for m in layer['metadata']])
        replacement_strs.append(['{metadata}', metadata])
        layer_config = bulk_replace(GC_SERVICE_LAYER_CONFIG_TEMPLATE,
                                    replacement_strs)
        layer_config_path = os.path.join(self.layer_config_base_path,
                                         layer['layer_id'] + '.yaml')
        with open(layer_config_path, 'w+') as f:
            f.write(layer_config)

        return layer_config_path

    @classmethod
    def set_up_date_service(self):
        # Check if mod_ahtse_lua is installed
        apache_path = '/etc/httpd/modules/'
        if not os.path.exists(os.path.join(apache_path, 'mod_ahtse_lua.so')):
            print("WARNING: Can't find mod_ahtse_lua installed in: {0}. Tests may fail.".format(apache_path))

        # Check if onearth Lua stuff has been installed
        try:
            output = subprocess.check_output(['luarocks', 'list'],
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            print(
                "WARNING: Error running Luarocks. Make sure lua and luarocks are installed and that the OnEarth lua package is also installed. Tests may fail."
            )

        if 'onearth' not in str(output):
            print(
                "WARNING: OnEarth luarocks package not installed. Tests may fail."
            )

        # Start redis
        if not redis_running():
            os.system('redis-server &')
        time.sleep(2)
        if not redis_running():
            print("WARNING: Can't access Redis server. Tests may fail.")

        # Copy Lua config
        test_lua_config_dest_path = '/build/test/ci_tests/tmp/date_service_test'
        test_lua_config_filename = 'date_service.lua'
        self.test_lua_config_location = os.path.join(test_lua_config_dest_path,
                                                     test_lua_config_filename)

        make_dir_tree(test_lua_config_dest_path, ignore_existing=True)
        with open(self.test_lua_config_location, 'w+') as f:
            f.write(DATE_SERVICE_LUA_TEMPLATE)

        # Copy Apache config
        self.date_service_test_config_dest_path = os.path.join(
            '/etc/httpd/conf.d', 'oe2_test_date_service.conf')
        with open(self.date_service_test_config_dest_path, 'w+') as dest:
            dest.write(
                DATE_SERVICE_APACHE_TEMPLATE.replace(
                    '{config_path}', test_lua_config_dest_path))

        self.date_service_url = 'http://localhost/date_service/date?'

        restart_apache()

        r = requests.get(self.date_service_url)
        if r.status_code != 200:
            print(
                "WARNING: Can't access date service at url: {}. Tests may fail"
            ).format(self.date_service_url)

    @classmethod
    def set_up_gc_service(self, test_name, target_proj,
                          date_service_keys=None):
        gc_service_base_url = 'http://localhost/gc_service_' + test_name
        gc_layer_base_url = 'http://localhost/wmts'
        gts_layer_base_url = 'http://localhost/twms'

        # Configure config paths and dependency files
        gc_test_config_dest_path = os.path.join(self.test_config_base_path,
                                                'gc_service_test', test_name)
        make_dir_tree(gc_test_config_dest_path, ignore_existing=True)

        # Copy dependency files
        dependency_path = os.path.join(os.getcwd(), 'gc_service_test_files')
        tms_defs_path = os.path.join(dependency_path, 'tilematrixsets.xml')
        gc_header_path = os.path.join(dependency_path, 'header_gc.xml')
        gts_header_path = os.path.join(dependency_path, 'header_gts.xml')
        twms_gc_header_path = os.path.join(dependency_path,
                                           'header_twms_gc.xml')
        dependency_paths = [
            tms_defs_path, gc_header_path, gts_header_path, twms_gc_header_path
        ]
        for path in dependency_paths:
            shutil.copy(path, gc_test_config_dest_path)

        date_service_str = '{}' if not date_service_keys else '{{{}}}'.format(
            ','.join(map(lambda x: "'{}'".format(x), date_service_keys)))

        # Format and write the Lua config files
        gc_config = bulk_replace(
            GC_SERVICE_LUA_TEMPLATE,
            [('{layer_config_path}', self.layer_config_base_path),
             ('{tms_defs_path}', tms_defs_path),
             ('{gc_header_path}', gc_header_path),
             ('{gts_header_path}', gts_header_path),
             ('{twms_gc_header_path}', twms_gc_header_path),
             ('{date_service_uri}', self.date_service_url),
             ('{src_epsg}', 'EPSG:4326'), ('{base_uri_gc}', gc_layer_base_url),
             ('{base_uri_gts}', gts_layer_base_url),
             ('{target_epsg}', target_proj),
             ('{date_service_keys}', date_service_str)])

        test_gc_config_location = os.path.join(gc_test_config_dest_path,
                                               'gc_service.lua')
        with open(test_gc_config_location, 'w+') as f:
            f.write(gc_config)

        # Format and write the Apache config file
        apache_config = bulk_replace(
            GC_SERVICE_APACHE_CONFIG_TEMPLATE,
            [('{gc_lua_path}', test_gc_config_location),
             ('{gc_path}', gc_test_config_dest_path),
             ('{endpoint}', '/' + gc_service_base_url.split('/')[-1]),
             ('{regexp}', 'gc_service')])
        gc_apache_path = os.path.join(
            '/etc/httpd/conf.d',
            'oe2_test_gc_service_{}.conf'.format(test_name))
        self.test_apache_configs.append(gc_apache_path)
        with open(gc_apache_path, 'w+') as f:
            f.write(apache_config)

        restart_apache()

        return {
            'endpoint': gc_service_base_url + '/gc_service',
            'gc_header_path': gc_header_path,
            'twms_gc_header_path': twms_gc_header_path,
            'gts_header_path': gts_header_path,
            'tms_path': tms_defs_path,
            'gc_base_url': gc_layer_base_url,
            'gts_base_url': gts_layer_base_url
        }

    @classmethod
    def setUpClass(self):
        self.set_up_date_service()

        self.test_config_base_path = '/build/test/ci_tests/tmp'

        # Create directory for layer config files (generated by the tests
        # individually)
        self.layer_config_base_path = os.path.join(self.test_config_base_path,
                                                   'layer_configs')
        make_dir_tree(self.layer_config_base_path, ignore_existing=True)

        self.test_apache_configs = []

    def test_gc_layer_info(self):
        # Check that <Layer> block for a static layer is being generated
        # correctly

        apache_config = self.set_up_gc_service('test_gc_layer_info',
                                               'EPSG:4326')

        # Create and write layer config
        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)

        # Download GC file
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        contents_elem = gc_dom.find('{*}Contents')
        layer_elems = contents_elem.findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        # self.assertEqual(len(
        # layer_elems), 1, 'Incorrect number of <Layer> elements found - should
        # only be 1. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        title_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            'Title not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url: {}'.format(
                layer['layer_title'], title_elems[0].text, url))

        bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}WGS84BoundingBox')
        self.assertNotEqual(
            len(bbox_elems), 0,
            '<WGS84BoundingBox> not found in generated GC file. Url: {}'.
            format(url))
        self.assertEqual(
            len(bbox_elems), 1,
            'Incorrect number of < WGS84BoundingBox > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'urn:ogc:def:crs:OGC:2:84'
        found = bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <WGS84BoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        lower_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "-180 -90"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '< LowerCorner > element incorrect, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        upper_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "180 90"
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '< UpperCorner > element incorrect, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        identifier_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(identifier_elems), 0,
            '<Identifier> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(identifier_elems), 1,
            'Incorrect number of <Identifier> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_id']
        found = identifier_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Identifier>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        style_elems = layer_elem.findall('{*}Style')
        self.assertNotEqual(
            len(style_elems), 0,
            '<Style> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of < Style > elements found - - should only be 1. Url: {}'
            .format(url))

        expected = 'true'
        found = style_elems[0].get('isDefault')
        self.assertEqual(
            found, expected,
            'Incorrect "isDefault" attribute for <Style>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        title_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file <Style> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of < Title > elements found - - should only be 1. Url: {}'
            .format(url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect "lang" attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'default'
        found = title_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        style_id_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Identifier> not found in generated GC file <Style> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Identifier > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'default'
        found = style_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Identifier>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        format_elems = layer_elem.findall('{*}Format')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Format> not found in generated GC file <Layer> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of <Format> elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = format_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Format>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        tms_link_elems = layer_elem.findall('{*}TileMatrixSetLink')
        self.assertNotEqual(
            len(tms_link_elems), 0,
            '<TileMatrixSetLink> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_link_elems), 1,
            'Incorrect number of <TileMatrixSetLink> elements found - should only be 1. Url: {}'
            .format(url))

        tms_elems = tms_link_elems[0].findall('{*}TileMatrixSet')
        self.assertNotEqual(
            len(tms_elems), 0,
            '<TileMatrixSet> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_elems), 1,
            'Incorrect number of < TileMatrixSet > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['tilematrixset']
        found = tms_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <TileMatrixSet>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        resource_url_elems = layer_elem.findall('{*}ResourceURL')
        self.assertNotEqual(
            len(resource_url_elems), 0,
            '<ResourceURL> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(resource_url_elems), 2,
            'Incorrect number of < ResourceURL > elements found - should only be 2. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'tile'
        found = resource_url_elems[0].get('resourceType')
        self.assertEqual(
            found, expected,
            'Incorrect "resourceType" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = apache_config['gc_base_url'] + '/' + \
            layer['layer_id'] + \
            '/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg'
        found = resource_url_elems[0].get('template')
        self.assertEqual(
            found, expected,
            'Incorrect "template" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        layer_metadata_strs = [m.replace("'", '"') for m in layer['metadata']]
        layer_metadata = [json.loads(m) for m in layer_metadata_strs]
        metadata_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Metadata')
        expected = len(layer_metadata)
        found = len(metadata_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Metadata> elements, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        for md_elem in metadata_elems:
            role = md_elem.get('{http://www.w3.org/1999/xlink}role')
            src_md = next(
                md for md in layer_metadata if md['xlink:role'] == role)
            all_match = all(
                key for key, value in src_md.items() if md_elem.get(
                    key.replace('xlink:', '{http://www.w3.org/1999/xlink}')))
            self.assertTrue(
                all_match,
                'Metadata elements missing from <Layer> element. Url: {}'.
                format(url))

    def test_gc_layer_info_reproject(self):
        # Check that <Layer> block for a static layer is being generated
        # and reprojected correctly
        target_epsg = 'EPSG:3857'
        target_tms = 'GoogleMapsCompatible_Level6'

        apache_config = self.set_up_gc_service('test_gc_layer_info_reproject',
                                               target_epsg)

        # Create and write layer config
        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)

        # Download GC file
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        contents_elem = gc_dom.find('{*}Contents')
        layer_elems = contents_elem.findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        # self.assertEqual(len(
        # layer_elems), 1, 'Incorrect number of <Layer> elements found - should
        # only be 1. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        title_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            'Title not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url: {}'.format(
                layer['layer_title'], title_elems[0].text, url))

        wgs84_bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}WGS84BoundingBox')
        self.assertNotEqual(
            len(wgs84_bbox_elems), 0,
            '<WGS84BoundingBox> not found in generated GC file. Url: {}'.
            format(url))
        self.assertEqual(
            len(wgs84_bbox_elems), 1,
            'Incorrect number of <WGS84BoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'urn:ogc:def:crs:OGC:2:84'
        found = wgs84_bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <WGS84BoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        lower_corner_elems = wgs84_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "-180 -85.051129"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        upper_corner_elems = wgs84_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = '180 85.051129'
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        native_bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}BoundingBox')
        self.assertNotEqual(
            len(native_bbox_elems), 0,
            '<BoundingBox> not found in generated GC file. Url: {}'.
                format(url))
        self.assertEqual(
            len(native_bbox_elems), 1,
            'Incorrect number of <BoundingBox> elements found - should only be 1. Url: {}'
                .format(url))

        expected = 'urn:ogc:def:crs:EPSG::3857'
        found = native_bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <BoundingBox>. Expected {}, found {}. Url: {}'
                .format(expected, found, url))

        lower_corner_elems = native_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = "-20037508.34278925 -20037508.34278925"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        upper_corner_elems = native_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = '20037508.34278925 20037508.34278925'
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        identifier_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(identifier_elems), 0,
            '<Identifier> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(identifier_elems), 1,
            'Incorrect number of <Identifier> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_id']
        found = identifier_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Identifier>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        style_elems = layer_elem.findall('{*}Style')
        self.assertNotEqual(
            len(style_elems), 0,
            '<Style> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of < Style > elements found - - should only be 1. Url: {}'
            .format(url))

        expected = 'true'
        found = style_elems[0].get('isDefault')
        self.assertEqual(
            found, expected,
            'Incorrect "isDefault" attribute for <Style>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        title_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file <Style> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of < Title > elements found - - should only be 1. Url: {}'
            .format(url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect "lang" attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'default'
        found = title_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        style_id_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Identifier> not found in generated GC file <Style> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of <Identifier> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'default'
        found = style_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Identifier>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        format_elems = layer_elem.findall('{*}Format')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Format> not found in generated GC file <Layer> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of <Format> elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = format_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Format>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        tms_link_elems = layer_elem.findall('{*}TileMatrixSetLink')
        self.assertNotEqual(
            len(tms_link_elems), 0,
            '<TileMatrixSetLink> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_link_elems), 1,
            'Incorrect number of <TileMatrixSetLink> elements found - should only be 1. Url: {}'
            .format(url))

        tms_elems = tms_link_elems[0].findall('{*}TileMatrixSet')
        self.assertNotEqual(
            len(tms_elems), 0,
            '<TileMatrixSet> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_elems), 1,
            'Incorrect number of < TileMatrixSet > elements found - should only be 1. Url: {}'
            .format(url))

        expected = target_tms
        found = tms_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <TileMatrixSet>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        resource_url_elems = layer_elem.findall('{*}ResourceURL')
        self.assertNotEqual(
            len(resource_url_elems), 0,
            '<ResourceURL> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(resource_url_elems), 2,
            'Incorrect number of < ResourceURL > elements found - should only be 2. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'tile'
        found = resource_url_elems[0].get('resourceType')
        self.assertEqual(
            found, expected,
            'Incorrect "resourceType" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = apache_config['gc_base_url'] + '/' + \
            layer['layer_id'] + \
            '/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg'
        found = resource_url_elems[0].get('template')
        self.assertEqual(
            found, expected,
            'Incorrect "template" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        layer_metadata_strs = [m.replace("'", '"') for m in layer['metadata']]
        layer_metadata = [json.loads(m) for m in layer_metadata_strs]
        metadata_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Metadata')
        expected = len(layer_metadata)
        found = len(metadata_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Metadata> elements, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        for md_elem in metadata_elems:
            role = md_elem.get('{http://www.w3.org/1999/xlink}role')
            src_md = next(
                md for md in layer_metadata if md['xlink:role'] == role)
            all_match = all(
                key for key, value in src_md.items() if md_elem.get(
                    key.replace('xlink:', '{http://www.w3.org/1999/xlink}')))
            self.assertTrue(
                all_match,
                'Metadata elements missing from <Layer> element. Url: {}'.
                format(url))

    def test_dynamic_layer_xml(self):
        # Check that <Layer> block for a dynamic layer is being generated
        # correctly

        apache_config = self.set_up_gc_service('test_dynamic_layer_xml',
                                               'EPSG:4326')

        # Create and write layer config
        layer = TEST_LAYERS['test_2']
        layer_config_path = self.write_config_for_test_layer(layer)

        redis_info = None
        if layer.get('static') == 'false':
            redis_info = [
                layer['layer_id'], layer['default'], layer['periods']
            ]
            seed_redis_data([redis_info])

        # Download GC file
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not START_SERVER:
            os.remove(layer_config_path)
            if redis_info:
                remove_redis_layer(redis_info)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        contents_elem = gc_dom.find('{*}Contents')
        layer_elems = contents_elem.findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        # self.assertEqual(len(
        # layer_elems), 1, 'Incorrect number of <Layer> elements found - should
        # only be 1. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        title_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url: {}'.format(
                layer['layer_title'], title_elems[0].text, url))

        bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}WGS84BoundingBox')
        self.assertNotEqual(
            len(bbox_elems), 0,
            '<WGS84BoundingBox> not found in generated GC file. Url: {}'.
            format(url))
        self.assertEqual(
            len(bbox_elems), 1,
            'Incorrect number of <WGS84BoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'urn:ogc:def:crs:OGC:2:84'
        found = bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <WGS84BoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        lower_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "-180 -90"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        upper_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "180 90"
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        identifier_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(identifier_elems), 0,
            '<Identifier> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(identifier_elems), 1,
            'Incorrect number of <Identifier> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_id']
        found = identifier_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Identifier>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        style_elems = layer_elem.findall('{*}Style')
        self.assertNotEqual(
            len(style_elems), 0,
            '<Style> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of < Style > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'true'
        found = style_elems[0].get('isDefault')
        self.assertEqual(
            found, expected,
            'Incorrect "isDefault" attribute for <Style>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        title_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file <Style> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect "lang" attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'default'
        found = title_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        style_id_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Identifier> not found in generated GC file <Style> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Identifier > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'default'
        found = style_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Identifier>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        format_elems = layer_elem.findall('{*}Format')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Format> not found in generated GC file <Layer> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Format > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = format_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Format>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        tms_link_elems = layer_elem.findall('{*}TileMatrixSetLink')
        self.assertNotEqual(
            len(tms_link_elems), 0,
            '<TileMatrixSetLink> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_link_elems), 1,
            'Incorrect number of < TileMatrixSetLink > elements found - should only be 1. Url: {}'
            .format(url))

        tms_elems = tms_link_elems[0].findall('{*}TileMatrixSet')
        self.assertNotEqual(
            len(tms_elems), 0,
            '<TileMatrixSet> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_elems), 1,
            'Incorrect number of < TileMatrixSet > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['tilematrixset']
        found = tms_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <TileMatrixSet>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        resource_url_elems = layer_elem.findall('{*}ResourceURL')
        self.assertNotEqual(
            len(resource_url_elems), 0,
            '<ResourceURL> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(resource_url_elems), 3,
            'Incorrect number of < ResourceURL > elements found - should only be 3. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'tile'
        found = resource_url_elems[0].get('resourceType')
        self.assertEqual(
            found, expected,
            'Incorrect "resourceType" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = apache_config['gc_base_url'] + '/' + \
            layer['layer_id'] + \
            '/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg'
        found = resource_url_elems[0].get('template')
        self.assertEqual(
            found, expected,
            'Incorrect "template" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        layer_metadata_strs = [m.replace("'", '"') for m in layer['metadata']]
        layer_metadata = [json.loads(m) for m in layer_metadata_strs]
        metadata_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Metadata')
        expected = len(layer_metadata)
        found = len(metadata_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Metadata> elements, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        for md_elem in metadata_elems:
            role = md_elem.get('{http://www.w3.org/1999/xlink}role')
            src_md = next(
                md for md in layer_metadata if md['xlink:role'] == role)
            all_match = all(
                key for key, value in src_md.items() if md_elem.get(
                    key.replace('xlink:', '{http://www.w3.org/1999/xlink}')))
            self.assertTrue(
                all_match,
                'Metadata elements missing from < Layer > element.Url: {}'.
                format(url))

        dimension_elems = layer_elem.findall('{*}Dimension')
        self.assertNotEqual(
            len(dimension_elems), 0,
            '<Dimension> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_elems), 1,
            'Incorrect number of < Dimension > elements found - should only be 1. Url: {}'
            .format(url))

        dimension_id_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(dimension_id_elems), 0,
            '<Identifier> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_id_elems), 1,
            'Incorrect number of < Identifier > elements found in < Dimension > element - - should only be 1. Url: {}'
            .format(url))

        expected = 'Time'
        found = dimension_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Identifier> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_uom_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UOM')
        self.assertNotEqual(
            len(dimension_uom_elems), 0,
            '<UOM> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_uom_elems), 1,
            'Incorrect number of < UOM > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'ISO8601'
        found = dimension_uom_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <UOM> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_default_elems = dimension_elems[0].findall('{*}Default')
        self.assertNotEqual(
            len(dimension_default_elems), 0,
            '<Default> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_default_elems), 1,
            'Incorrect number of < Default > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = layer['default']
        found = dimension_default_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Default> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_current_elems = dimension_elems[0].findall('{*}Current')
        self.assertNotEqual(
            len(dimension_current_elems), 0,
            '<Current> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_current_elems), 1,
            'Incorrect number of < Current > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'false'
        found = dimension_current_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Current> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_value_elems = dimension_elems[0].findall('{*}Value')
        expected = len(layer['periods'])
        found = len(dimension_value_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Value> elements found in <Dimension> element -- expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = [period for period in layer['periods']].sort()
        found = [elem.text for elem in dimension_value_elems].sort()
        self.assertEqual(
            found, expected,
            'Incorrect values for <Value> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

    def test_dynamic_layer_xml_reprojected(self):
        # Check that <Layer> block for a dynamic layer is being generated
        # and reprojected correctly

        target_epsg = 'EPSG:3857'
        target_tms = 'GoogleMapsCompatible_Level6'
        apache_config = self.set_up_gc_service(
            'test_dynamic_layer_xml_reprojected', target_epsg)

        # Create and write layer config
        layer = TEST_LAYERS['test_2']
        layer_config_path = self.write_config_for_test_layer(layer)

        redis_info = None
        if layer.get('static') == 'false':
            redis_info = [
                layer['layer_id'], layer['default'], layer['periods']
            ]
            seed_redis_data([redis_info])

        # Download GC file
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not START_SERVER:
            os.remove(layer_config_path)
            if redis_info:
                remove_redis_layer(redis_info)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        contents_elem = gc_dom.find('{*}Contents')
        layer_elems = contents_elem.findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        # self.assertEqual(len(
        # layer_elems), 1, 'Incorrect number of <Layer> elements found - should
        # only be 1. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        title_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url: {}'.format(
                layer['layer_title'], title_elems[0].text, url))

        wgs84_bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}WGS84BoundingBox')
        self.assertNotEqual(
            len(wgs84_bbox_elems), 0,
            '<WGS84BoundingBox> not found in generated GC file. Url: {}'.
                format(url))
        self.assertEqual(
            len(wgs84_bbox_elems), 1,
            'Incorrect number of <WGS84BoundingBox> elements found - should only be 1. Url: {}'
                .format(url))

        expected = 'urn:ogc:def:crs:OGC:2:84'
        found = wgs84_bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <WGS84BoundingBox>. Expected {}, found {}. Url: {}'
                .format(expected, found, url))

        lower_corner_elems = wgs84_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = "-180 -85.051129"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        upper_corner_elems = wgs84_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = '180 85.051129'
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        native_bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}BoundingBox')
        self.assertNotEqual(
            len(native_bbox_elems), 0,
            '<BoundingBox> not found in generated GC file. Url: {}'.
                format(url))
        self.assertEqual(
            len(native_bbox_elems), 1,
            'Incorrect number of <BoundingBox> elements found - should only be 1. Url: {}'
                .format(url))

        expected = 'urn:ogc:def:crs:EPSG::3857'
        found = native_bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <BoundingBox>. Expected {}, found {}. Url: {}'
                .format(expected, found, url))

        lower_corner_elems = native_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = "-20037508.34278925 -20037508.34278925"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        upper_corner_elems = native_bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
                .format(url))
        expected = '20037508.34278925 20037508.34278925'
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
                format(expected, found, url))

        identifier_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(identifier_elems), 0,
            '<Identifier> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(identifier_elems), 1,
            'Incorrect number of <Identifier> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_id']
        found = identifier_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Identifier>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        style_elems = layer_elem.findall('{*}Style')
        self.assertNotEqual(
            len(style_elems), 0,
            '<Style> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of < Style > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'true'
        found = style_elems[0].get('isDefault')
        self.assertEqual(
            found, expected,
            'Incorrect "isDefault" attribute for <Style>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        title_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file <Style> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect "lang" attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'default'
        found = title_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        style_id_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Identifier> not found in generated GC file <Style> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Identifier > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'default'
        found = style_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Identifier>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        format_elems = layer_elem.findall('{*}Format')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Format> not found in generated GC file <Layer> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Format > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = format_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Format>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        tms_link_elems = layer_elem.findall('{*}TileMatrixSetLink')
        self.assertNotEqual(
            len(tms_link_elems), 0,
            '<TileMatrixSetLink> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_link_elems), 1,
            'Incorrect number of < TileMatrixSetLink > elements found - should only be 1. Url: {}'
            .format(url))

        tms_elems = tms_link_elems[0].findall('{*}TileMatrixSet')
        self.assertNotEqual(
            len(tms_elems), 0,
            '<TileMatrixSet> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_elems), 1,
            'Incorrect number of < TileMatrixSet > elements found - should only be 1. Url: {}'
            .format(url))

        expected = target_tms
        found = tms_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <TileMatrixSet>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        resource_url_elems = layer_elem.findall('{*}ResourceURL')
        self.assertNotEqual(
            len(resource_url_elems), 0,
            '<ResourceURL> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(resource_url_elems), 3,
            'Incorrect number of < ResourceURL > elements found - should be 3. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'tile'
        found = resource_url_elems[0].get('resourceType')
        self.assertEqual(
            found, expected,
            'Incorrect "resourceType" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = apache_config['gc_base_url'] + '/' + \
            layer['layer_id'] + \
            '/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg'
        found = resource_url_elems[0].get('template')
        self.assertEqual(
            found, expected,
            'Incorrect "template" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        layer_metadata_strs = [m.replace("'", '"') for m in layer['metadata']]
        layer_metadata = [json.loads(m) for m in layer_metadata_strs]
        metadata_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Metadata')
        expected = len(layer_metadata)
        found = len(metadata_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Metadata> elements, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        for md_elem in metadata_elems:
            role = md_elem.get('{http://www.w3.org/1999/xlink}role')
            src_md = next(
                md for md in layer_metadata if md['xlink:role'] == role)
            all_match = all(
                key for key, value in src_md.items() if md_elem.get(
                    key.replace('xlink:', '{http://www.w3.org/1999/xlink}')))
            self.assertTrue(
                all_match,
                'Metadata elements missing from < Layer > element.Url: {}'.
                format(url))

        dimension_elems = layer_elem.findall('{*}Dimension')
        self.assertNotEqual(
            len(dimension_elems), 0,
            '<Dimension> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_elems), 1,
            'Incorrect number of < Dimension > elements found - should only be 1. Url: {}'
            .format(url))

        dimension_id_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(dimension_id_elems), 0,
            '<Identifier> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_id_elems), 1,
            'Incorrect number of < Identifier > elements found in < Dimension > element - - should only be 1. Url: {}'
            .format(url))

        expected = 'Time'
        found = dimension_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Identifier> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_uom_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UOM')
        self.assertNotEqual(
            len(dimension_uom_elems), 0,
            '<UOM> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_uom_elems), 1,
            'Incorrect number of < UOM > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'ISO8601'
        found = dimension_uom_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <UOM> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_default_elems = dimension_elems[0].findall('{*}Default')
        self.assertNotEqual(
            len(dimension_default_elems), 0,
            '<Default> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_default_elems), 1,
            'Incorrect number of < Default > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = layer['default']
        found = dimension_default_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Default> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_current_elems = dimension_elems[0].findall('{*}Current')
        self.assertNotEqual(
            len(dimension_current_elems), 0,
            '<Current> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_current_elems), 1,
            'Incorrect number of < Current > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'false'
        found = dimension_current_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Current> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_value_elems = dimension_elems[0].findall('{*}Value')
        expected = len(layer['periods'])
        found = len(dimension_value_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Value> elements found in <Dimension> element -- expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = [period for period in layer['periods']].sort()
        found = [elem.text for elem in dimension_value_elems].sort()
        self.assertEqual(
            found, expected,
            'Incorrect values for <Value> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

    def test_dynamic_layer_xml_date_service_keys(self):
        # Check that <Layer> block for a dynamic layer is being generated
        # correctly

        date_service_keys = ['test1', 'test2']
        apache_config = self.set_up_gc_service(
            'test_dynamic_layer_xml_date_service_keys',
            'EPSG:4326',
            date_service_keys=date_service_keys)

        # Create and write layer config
        layer = TEST_LAYERS['test_2']
        layer_config_path = self.write_config_for_test_layer(layer)

        redis_info = None
        if layer.get('static') == 'false':
            redis_info = [
                layer['layer_id'], layer['default'], layer['periods']
            ]
            seed_redis_data([redis_info], db_keys=date_service_keys)

        # Download GC file
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not START_SERVER:
            os.remove(layer_config_path)
            if redis_info:
                remove_redis_layer(redis_info, db_keys=date_service_keys)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        contents_elem = gc_dom.find('{*}Contents')
        layer_elems = contents_elem.findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        # self.assertEqual(len(
        # layer_elems), 1, 'Incorrect number of <Layer> elements found - should
        # only be 1. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        title_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url: {}'.format(
                layer['layer_title'], title_elems[0].text, url))

        bbox_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}WGS84BoundingBox')
        self.assertNotEqual(
            len(bbox_elems), 0,
            '<WGS84BoundingBox> not found in generated GC file. Url: {}'.
            format(url))
        self.assertEqual(
            len(bbox_elems), 1,
            'Incorrect number of <WGS84BoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'urn:ogc:def:crs:OGC:2:84'
        found = bbox_elems[0].get("crs")
        self.assertEqual(
            found, expected,
            'Incorrect crs attribute for <WGS84BoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        lower_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}LowerCorner')
        self.assertNotEqual(
            len(lower_corner_elems), 0,
            '<LowerCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(lower_corner_elems), 1,
            'Incorrect number of <LowerCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "-180 -90"
        found = lower_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<LowerCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        upper_corner_elems = bbox_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UpperCorner')
        self.assertNotEqual(
            len(upper_corner_elems), 0,
            '<UpperCorner> not found in generated GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(upper_corner_elems), 1,
            'Incorrect number of <UpperCorner> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = "180 90"
        found = upper_corner_elems[0].text
        self.assertEqual(
            found, expected,
            '<UpperCorner> element incorrect, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        identifier_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(identifier_elems), 0,
            '<Identifier> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(identifier_elems), 1,
            'Incorrect number of <Identifier> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_id']
        found = identifier_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Identifier>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        style_elems = layer_elem.findall('{*}Style')
        self.assertNotEqual(
            len(style_elems), 0,
            '<Style> not found in generated GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of < Style > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'true'
        found = style_elems[0].get('isDefault')
        self.assertEqual(
            found, expected,
            'Incorrect "isDefault" attribute for <Style>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        title_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GC file <Style> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect "lang" attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'default'
        found = title_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        style_id_elems = style_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Title')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Identifier> not found in generated GC file <Style> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Identifier > elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'default'
        found = style_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Style>/<Identifier>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        format_elems = layer_elem.findall('{*}Format')
        self.assertNotEqual(
            len(style_id_elems), 0,
            '<Format> not found in generated GC file <Layer> element. Url: {}'.
            format(url))
        self.assertEqual(
            len(style_id_elems), 1,
            'Incorrect number of < Format > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = format_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Format>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        tms_link_elems = layer_elem.findall('{*}TileMatrixSetLink')
        self.assertNotEqual(
            len(tms_link_elems), 0,
            '<TileMatrixSetLink> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_link_elems), 1,
            'Incorrect number of < TileMatrixSetLink > elements found - should only be 1. Url: {}'
            .format(url))

        tms_elems = tms_link_elems[0].findall('{*}TileMatrixSet')
        self.assertNotEqual(
            len(tms_elems), 0,
            '<TileMatrixSet> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(tms_elems), 1,
            'Incorrect number of < TileMatrixSet > elements found - should only be 1. Url: {}'
            .format(url))

        expected = layer['tilematrixset']
        found = tms_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <TileMatrixSet>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        resource_url_elems = layer_elem.findall('{*}ResourceURL')
        self.assertNotEqual(
            len(resource_url_elems), 0,
            '<ResourceURL> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(resource_url_elems), 3,
            'Incorrect number of < ResourceURL > elements found - should only be 3. Url: {}'
            .format(url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = layer['mime_type']
        found = resource_url_elems[0].get('format')
        self.assertEqual(
            found, expected,
            'Incorrect "format" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = 'tile'
        found = resource_url_elems[0].get('resourceType')
        self.assertEqual(
            found, expected,
            'Incorrect "resourceType" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = apache_config['gc_base_url'] + '/' + \
            layer['layer_id'] + \
            '/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg'
        found = resource_url_elems[0].get('template')
        self.assertEqual(
            found, expected,
            'Incorrect "template" attribute for <ResourceURL>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        layer_metadata_strs = [m.replace("'", '"') for m in layer['metadata']]
        layer_metadata = [json.loads(m) for m in layer_metadata_strs]
        metadata_elems = layer_elem.findall(
            '{http://www.opengis.net/ows/1.1}Metadata')
        expected = len(layer_metadata)
        found = len(metadata_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Metadata> elements, expected {}, found {}. Url: {}'
            .format(expected, found, url))

        for md_elem in metadata_elems:
            role = md_elem.get('{http://www.w3.org/1999/xlink}role')
            src_md = next(
                md for md in layer_metadata if md['xlink:role'] == role)
            all_match = all(
                key for key, value in src_md.items() if md_elem.get(
                    key.replace('xlink:', '{http://www.w3.org/1999/xlink}')))
            self.assertTrue(
                all_match,
                'Metadata elements missing from < Layer > element.Url: {}'.
                format(url))

        dimension_elems = layer_elem.findall('{*}Dimension')
        self.assertNotEqual(
            len(dimension_elems), 0,
            '<Dimension> not found in generated GC file <Layer> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_elems), 1,
            'Incorrect number of < Dimension > elements found - should only be 1. Url: {}'
            .format(url))

        dimension_id_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}Identifier')
        self.assertNotEqual(
            len(dimension_id_elems), 0,
            '<Identifier> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_id_elems), 1,
            'Incorrect number of < Identifier > elements found in < Dimension > element - - should only be 1. Url: {}'
            .format(url))

        expected = 'Time'
        found = dimension_id_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Identifier> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_uom_elems = dimension_elems[0].findall(
            '{http://www.opengis.net/ows/1.1}UOM')
        self.assertNotEqual(
            len(dimension_uom_elems), 0,
            '<UOM> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_uom_elems), 1,
            'Incorrect number of <UOM> elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'ISO8601'
        found = dimension_uom_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <UOM> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_default_elems = dimension_elems[0].findall('{*}Default')
        self.assertNotEqual(
            len(dimension_default_elems), 0,
            '<Default> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_default_elems), 1,
            'Incorrect number of < Default > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = layer['default']
        found = dimension_default_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Default> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_current_elems = dimension_elems[0].findall('{*}Current')
        self.assertNotEqual(
            len(dimension_current_elems), 0,
            '<Current> not found in generated GC file <Dimension> element. Url: {}'
            .format(url))
        self.assertEqual(
            len(dimension_current_elems), 1,
            'Incorrect number of < Current > elements found in <Dimension> element - - should only be 1. Url: {}'
            .format(url))

        expected = 'false'
        found = dimension_current_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect value for <Current> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        dimension_value_elems = dimension_elems[0].findall('{*}Value')
        expected = len(layer['periods'])
        found = len(dimension_value_elems)
        self.assertEqual(
            expected, found,
            'Incorrect number of <Value> elements found in <Dimension> element -- expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = [period for period in layer['periods']].sort()
        found = [elem.text for elem in dimension_value_elems].sort()
        self.assertEqual(
            found, expected,
            'Incorrect values for <Value> in <Dimension>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

    def test_gc_header_equal(self):
        apache_config = self.set_up_gc_service('test_gc_header_equal',
                                               'EPSG:4326')

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)
        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and parse the header XML
        with open(apache_config['gc_header_path'], 'r') as f:
            header_dom = etree.fromstring(f.read())

        # Remove the <Contents>  element from the GC as it is dynamically
        # generated
        gc_dom.remove(gc_dom.find('{*}Contents'))

        xml_compare(gc_dom, header_dom, lambda e: self.fail(
            'Incorrect line found in GC header. Error {}. Url: {}'.format(e, url)))

    def test_gc_tms_native(self):
        apache_config = self.set_up_gc_service('test_gc_tms_native',
                                               'EPSG:4326')

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)

        redis_info = None
        if not layer.get('static'):
            redis_info = [
                layer['layer_id'], layer['default'], layer['periods']
            ]
            seed_redis_data([redis_info])

        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not START_SERVER:
            os.remove(layer_config_path)
            if redis_info:
                remove_redis_layer(redis_info)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        try:
            gc_dom = etree.fromstring(r.text.replace('', ''))
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and parse the tms XML
        with open(apache_config['tms_path'], 'rb') as f:
            tilematrixsets = etree.fromstring(f.read())

        tms_dom = next(
            tms for tms in tilematrixsets.findall("{*}Projection")
            if tms.attrib.get("id") == "EPSG:4326")

        # Strip namespaces as the tms definitions file and GC file have
        # separate NSs
        strip_ns(tms_dom)
        strip_ns(gc_dom)

        # Dump the TMSs into a separate XML doc so we can test their equality
        test_tms_dom = etree.Element('Projection', attrib={'id': 'EPSG:4326'})
        for tms in gc_dom.find('{*}Contents').findall('{*}TileMatrixSet'):
            test_tms_dom.append(tms)

        xml_compare(tms_dom, test_tms_dom, lambda e: self.fail(
            'Incorrect line found in GC TileMatrixSet definitions. Error {}. Url: {}'.format(e, url)))

    def test_gc_tms_reproject(self):
        target_epsg = 'EPSG:3857'
        apache_config = self.set_up_gc_service('test_gc_tms_reproject',
                                               target_epsg)

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)

        redis_info = None
        if not layer.get('static'):
            redis_info = [
                layer['layer_id'], layer['default'], layer['periods']
            ]
            seed_redis_data([redis_info])

        url = apache_config['endpoint'] + '?request=wmtsgetcapabilities'
        r = requests.get(url)

        if not START_SERVER:
            os.remove(layer_config_path)
            if redis_info:
                remove_redis_layer(redis_info)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        try:
            gc_dom = etree.fromstring(r.text.replace('', ''))
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and parse the tms XML
        with open(apache_config['tms_path'], 'rb') as f:
            tilematrixsets = etree.fromstring(f.read())

        tms_dom = next(
            tms for tms in tilematrixsets.findall("{*}Projection")
            if tms.attrib.get("id") == target_epsg)

        # Strip namespaces as the tms definitions file and GC file have
        # separate NSs
        strip_ns(tms_dom)
        strip_ns(gc_dom)

        # Dump the TMSs into a separate XML doc so we can test their equality
        test_tms_dom = etree.Element('Projection', attrib={'id': target_epsg})
        for tms in gc_dom.find('{*}Contents').findall('{*}TileMatrixSet'):
            test_tms_dom.append(tms)

        xml_compare(tms_dom, test_tms_dom, lambda e: self.fail(
            'Incorrect line found in GC TileMatrixSet definitions. Error {}. Url: {}'.format(e, url)))

    def test_gts_header(self):
        apache_config = self.set_up_gc_service('test_gts_header', 'EPSG:4326')

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)
        url = apache_config['endpoint'] + '?request=gettileservice'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetTileService file from url: {}.'.format(url))

        try:
            gts_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and parse the header XML
        with open(apache_config['gts_header_path'], 'r') as f:
            header_dom = etree.fromstring(f.read())

        # Remove the <TiledPatterns>  element from the GTS as it is dynamically
        # generated
        gts_dom.remove(gts_dom.find('{*}TiledPatterns'))

        xml_compare(gts_dom, header_dom, lambda e: self.fail(
            'Incorrect line found in GTS header. Error {}. Url: {}'.format(e, url)))

    def test_gts_layers(self):
        epsg_code = 'EPSG:4326'
        apache_config = self.set_up_gc_service('test_gts_layers', epsg_code)

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)
        url = apache_config['endpoint'] + '?request=gettileservice'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetTileService file from url: {}.'.format(url))

        try:
            gts_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        tp_elem = gts_dom.find('{*}TiledPatterns')

        # Get and parse the header XML
        with open(apache_config['gts_header_path'], 'r') as f:
            header_dom = etree.fromstring(f.read())

        # Check base TP stuff
        or_elems = tp_elem.findall('{*}OnlineResource')
        self.assertNotEqual(
            len(or_elems), 0,
            'OnlineResource not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <OnlineResource> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'simple'
        found = or_elems[0].get('{http://www.w3.org/1999/xlink}type')
        self.assertEqual(
            found, expected,
            'Incorrect type attribute for <OnlineResource>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = header_dom.find('{*}Service').find('{*}OnlineResource').get(
            '{http://www.w3.org/1999/xlink}href')
        found = or_elems[0].get('{http://www.w3.org/1999/xlink}href')
        self.assertEqual(
            found, expected,
            'Incorrect href attribute for <OnlineResource>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        bbox_elems = tp_elem.findall('{*}LatLonBoundingBox')
        self.assertNotEqual(
            len(or_elems), 0,
            'OnlineResource not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <LatLonBoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '-180'
        found = bbox_elems[0].get('minx')
        self.assertEqual(
            found, expected,
            'Incorrect minx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '-90'
        found = bbox_elems[0].get('miny')
        self.assertEqual(
            found, expected,
            'Incorrect miny attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '180'
        found = bbox_elems[0].get('maxx')
        self.assertEqual(
            found, expected,
            'Incorrect maxx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '90'
        found = bbox_elems[0].get('maxy')
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        # Check for per-layer groups
        tg_elems = tp_elem.findall('{*}TiledGroup')
        self.assertNotEqual(
            len(or_elems), 0,
            'TiledGroup not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <TiledGroup> elements found - should only be 1. Url: {}'
            .format(url))

        tg_elem = tg_elems[0]

        name_elems = tg_elem.findall('Name')
        self.assertNotEqual(
            len(name_elems), 0,
            '<Name> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(name_elems), 1,
            'Incorrect number of <Name> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_name']
        found = name_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Name>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        title_elems = tg_elem.findall('Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_title']
        found = title_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Title>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect lang attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        abstract_elems = tg_elem.findall('Abstract')
        self.assertNotEqual(
            len(abstract_elems), 0,
            '<Abstract> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(abstract_elems), 1,
            'Incorrect number of <Abstract> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['abstract']
        found = abstract_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Abstract>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        expected = 'en'
        found = abstract_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect lang attribute for <Abstract>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        proj_elems = tg_elem.findall('Projection')
        self.assertNotEqual(
            len(proj_elems), 0,
            '<Projection> not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(proj_elems), 1,
            'Incorrect number of <Projection> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = PROJECTIONS[layer['projection']]['wkt']
        found = proj_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Projection>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        pad_elems = tg_elem.findall('Pad')
        self.assertNotEqual(
            len(pad_elems), 0,
            '<Pad> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(pad_elems), 1,
            'Incorrect number of <Pad> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = '0'
        found = pad_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Pad>, expected {}, found {}. Url: {}'.format(
                expected, found, url))

        bands_elems = tg_elem.findall('Bands')
        self.assertNotEqual(
            len(bands_elems), 0,
            '<Bands> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(bands_elems), 1,
            'Incorrect number of <Bands> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = '3'
        found = bands_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Bands>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        bbox_elems = tg_elem.findall('{*}LatLonBoundingBox')
        self.assertNotEqual(
            len(or_elems), 0,
            '<LatLonBoundingBox> not found in generated GTS file. Url: {}'.
            format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <LatLonBoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '-180'
        found = bbox_elems[0].get('minx')
        self.assertEqual(
            found, expected,
            'Incorrect minx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '-90'
        found = bbox_elems[0].get('miny')
        self.assertEqual(
            found, expected,
            'Incorrect miny attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '180'
        found = bbox_elems[0].get('maxx')
        self.assertEqual(
            found, expected,
            'Incorrect maxx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '90'
        found = bbox_elems[0].get('maxy')
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        key_elems = tg_elem.findall('{*}Key')
        self.assertNotEqual(
            len(or_elems), 0,
            '<Key> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <Key> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '${time}'
        found = key_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <Key>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        # Check <TilePattern> stuff
        # Get and parse the TMS XML
        with open(apache_config['tms_path'], 'rb') as f:
            tms_dom = etree.fromstring(f.read())

        tms_list = next(
            proj.findall('{*}TileMatrixSet')
            for proj in tms_dom.findall('{*}Projection')
            if proj.get('id') == epsg_code)
        tms = next(
            tms for tms in tms_list
            if tms.findtext('{*}Identifier') == layer['tilematrixset'])

        bbox = {'lowerCorner': [-180, -90], 'upperCorner': [180, 90]}

        expected_patterns = list(map(
            partial(make_tile_pattern, layer, epsg_code, bbox),
            tms.findall('{*}TileMatrix')))
        found_patterns = [p.text for p in tg_elem.findall('{*}TilePattern')]

        for p in expected_patterns:
            if p not in found_patterns:
                self.fail(
                    '<TilePattern> expected but not found in GTS: {}. Url: {}'.
                    format(p, url))

        for p in found_patterns:
            if p not in expected_patterns:
                self.fail(
                    '<TilePattern> found but not expected in GTS: {}. Url: {}'.
                    format(p, url))

    def test_gts_layers_reprojected(self):
        epsg_code = 'EPSG:3857'
        target_tms = 'GoogleMapsCompatible_Level6'
        apache_config = self.set_up_gc_service('test_gts_layers_reprojected',
                                               epsg_code)

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)
        url = apache_config['endpoint'] + '?request=gettileservice'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetTileService file from url: {}.'.format(url))

        try:
            gts_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        tp_elem = gts_dom.find('{*}TiledPatterns')

        # Get and parse the header XML
        with open(apache_config['gts_header_path'], 'r') as f:
            header_dom = etree.fromstring(f.read())

        # Check base TP stuff
        or_elems = tp_elem.findall('{*}OnlineResource')
        self.assertNotEqual(
            len(or_elems), 0,
            'OnlineResource not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <OnlineResource> elements found - should only be 1. Url: {}'
            .format(url))

        expected = 'simple'
        found = or_elems[0].get('{http://www.w3.org/1999/xlink}type')
        self.assertEqual(
            found, expected,
            'Incorrect type attribute for <OnlineResource>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = header_dom.find('{*}Service').find('{*}OnlineResource').get(
            '{http://www.w3.org/1999/xlink}href')
        found = or_elems[0].get('{http://www.w3.org/1999/xlink}href')
        self.assertEqual(
            found, expected,
            'Incorrect href attribute for <OnlineResource>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        bbox_elems = tp_elem.findall('{*}LatLonBoundingBox')
        self.assertNotEqual(
            len(or_elems), 0,
            'OnlineResource not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <LatLonBoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '-20037508.342789'
        found = bbox_elems[0].get('minx')
        self.assertEqual(
            found, expected,
            'Incorrect minx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '-20037508.342789'
        found = bbox_elems[0].get('miny')
        self.assertEqual(
            found, expected,
            'Incorrect miny attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '20037508.342789'
        found = bbox_elems[0].get('maxx')
        self.assertEqual(
            found, expected,
            'Incorrect maxx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '20037508.342789'
        found = bbox_elems[0].get('maxy')
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        # Check for per-layer groups
        tg_elems = tp_elem.findall('{*}TiledGroup')
        self.assertNotEqual(
            len(or_elems), 0,
            'TiledGroup not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <TiledGroup> elements found - should only be 1. Url: {}'
            .format(url))

        tg_elem = tg_elems[0]

        name_elems = tg_elem.findall('Name')
        self.assertNotEqual(
            len(name_elems), 0,
            '<Name> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(name_elems), 1,
            'Incorrect number of <Name> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_name']
        found = name_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Name>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        title_elems = tg_elem.findall('Title')
        self.assertNotEqual(
            len(title_elems), 0,
            '<Title> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = layer['layer_title']
        found = title_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Title>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect lang attribute for <Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        abstract_elems = tg_elem.findall('Abstract')
        self.assertNotEqual(
            len(abstract_elems), 0,
            '<Abstract> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(abstract_elems), 1,
            'Incorrect number of <Abstract> elements found - should only be 1. Url: {}'
            .format(url))
        expected = layer['abstract']
        found = abstract_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Abstract>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        expected = 'en'
        found = abstract_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect lang attribute for <Abstract>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        proj_elems = tg_elem.findall('Projection')
        self.assertNotEqual(
            len(proj_elems), 0,
            '<Projection> not found in generated GTS file. Url: {}'.format(
                url))
        self.assertEqual(
            len(proj_elems), 1,
            'Incorrect number of <Projection> elements found -- should only be 1. Url: {}'
            .format(url))

        expected = PROJECTIONS[epsg_code]['wkt']
        found = proj_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Projection>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        pad_elems = tg_elem.findall('Pad')
        self.assertNotEqual(
            len(pad_elems), 0,
            '<Pad> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(pad_elems), 1,
            'Incorrect number of <Pad> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = '0'
        found = pad_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Pad>, expected {}, found {}. Url: {}'.format(
                expected, found, url))

        bands_elems = tg_elem.findall('Bands')
        self.assertNotEqual(
            len(bands_elems), 0,
            '<Bands> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(bands_elems), 1,
            'Incorrect number of <Bands> elements found -- should only be 1. Url: {}'
            .format(url))
        expected = '3'
        found = bands_elems[0].text
        self.assertEqual(
            expected, found,
            'Incorrect value for <Bands>, expected {}, found {}. Url: {}'.
            format(expected, found, url))

        bbox_elems = tg_elem.findall('{*}LatLonBoundingBox')
        self.assertNotEqual(
            len(or_elems), 0,
            '<LatLonBoundingBox> not found in generated GTS file. Url: {}'.
            format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <LatLonBoundingBox> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '-20037508.342789'
        found = bbox_elems[0].get('minx')
        self.assertEqual(
            found, expected,
            'Incorrect minx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '-20037508.342789'
        found = bbox_elems[0].get('miny')
        self.assertEqual(
            found, expected,
            'Incorrect miny attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '20037508.342789'
        found = bbox_elems[0].get('maxx')
        self.assertEqual(
            found, expected,
            'Incorrect maxx attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        expected = '20037508.342789'
        found = bbox_elems[0].get('maxy')
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        key_elems = tg_elem.findall('{*}Key')
        self.assertNotEqual(
            len(or_elems), 0,
            '<Key> not found in generated GTS file. Url: {}'.format(url))
        self.assertEqual(
            len(or_elems), 1,
            'Incorrect number of <Key> elements found - should only be 1. Url: {}'
            .format(url))

        expected = '${time}'
        found = key_elems[0].text
        self.assertEqual(
            found, expected,
            'Incorrect maxy attribute for <Key>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        # Check <TilePattern> stuff
        # Get and parse the TMS XML
        with open(apache_config['tms_path'], 'rb') as f:
            tms_dom = etree.fromstring(f.read())

        tms_list = next(
            proj.findall('{*}TileMatrixSet')
            for proj in tms_dom.findall('{*}Projection')
            if proj.get('id') == epsg_code)
        tms = next(
            tms for tms in tms_list
            if tms.findtext('{*}Identifier') == target_tms)

        bbox = {
            'lowerCorner': [-20037508.34278925, -20037508.34278925],
            'upperCorner': [20037508.34278925, 20037508.34278925]
        }

        expected_patterns = list(map(
            partial(make_tile_pattern, layer, epsg_code, bbox),
            tms.findall('{*}TileMatrix')))
        found_patterns = [p.text for p in tg_elem.findall('{*}TilePattern')]

        for p in expected_patterns:
            if p not in found_patterns:
                self.fail(
                    '<TilePattern> expected but not found in GTS: {}. Url: {}'.
                    format(p, url))

        for p in found_patterns:
            if p not in expected_patterns:
                self.fail(
                    '<TilePattern> found but not expected in GTS: {}. Url: {}'.
                    format(p, url))

    def test_twms_gc_header_equal(self):
        apache_config = self.set_up_gc_service('test_twms_gc_header_equal',
                                               'EPSG:4326')

        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)
        url = apache_config['endpoint'] + '?request=twmsgetcapabilities'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading TWMS GetCapabilities file from url: {}.'.format(
                url))

        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and parse the header XML
        with open(apache_config['twms_gc_header_path'], 'r') as f:
            header_dom = etree.fromstring(f.read())

        # Remove all the <Layer> elements beneath the top one as they are dynamically
        # generated
        base_layer_elem = gc_dom.find('{*}Capability').find('{*}Layer')
        for l in base_layer_elem.findall('{*}Layer'):
            base_layer_elem.remove(l)

        xml_compare(gc_dom, header_dom, lambda e: self.fail(
            'Incorrect line found in GC header. Error {}. Url: {}'.format(e, url)))

    def test_twms_gc_layer_info(self):
        # Check that <Layer> block for a static layer is being generated
        # correctly

        apache_config = self.set_up_gc_service('test_twms_gc_layer_info',
                                               'EPSG:4326')

        # Create and write layer config
        layer = TEST_LAYERS['test_1']
        layer_config_path = self.write_config_for_test_layer(layer)

        # Download GC file
        url = apache_config['endpoint'] + '?request=twmsgetcapabilities'
        r = requests.get(url)

        if not DEBUG:
            os.remove(layer_config_path)

        self.assertEqual(
            r.status_code, 200,
            'Error downloading GetCapabilities file from url: {}.'.format(url))

        # Parse the XML and verify the root element and its namespaces are
        # correct
        try:
            gc_dom = etree.fromstring(r.text)
        except etree.XMLSyntaxError as e:
            self.fail(
                'Response for url: {} is not valid xml. Error: {}'.format(
                    url, e))

        # Get and test XML for this layer
        capability_elem = gc_dom.find('{*}Capability')
        layer_elems = capability_elem.find('{*}Layer').findall('{*}Layer')
        self.assertNotEqual(
            len(layer_elems), 0,
            'Layer not found in generated GC file. Url: {}'.format(url))
        layer_elem = layer_elems[0]

        expected = '0'
        found = layer_elem.get('queryable')
        self.assertEqual(
            found, expected,
            'Incorrect "queryable" attribute for <Layer>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        name_elems = layer_elem.findall('Name')
        self.assertNotEqual(
            len(name_elems), 0,
            'Name not found in generated TWMS GC file. Url: {}'.format(url))
        self.assertEqual(
            len(name_elems), 1,
            'Incorrect number of <Name> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            name_elems[0].text, layer['layer_id'],
            '<Name> element incorrect, expected {}, found {}. Url:{}'.format(
                layer['layer_id'], name_elems[0].text, url))

        title_elems = layer_elem.findall('Title')
        self.assertNotEqual(
            len(title_elems), 0,
            'Title not found in generated TWMS GC file. Url: {}'.format(url))
        self.assertEqual(
            len(title_elems), 1,
            'Incorrect number of <Title> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            title_elems[0].text, layer['layer_title'],
            '<Title> element incorrect, expected {}, found {}. Url:{}'.format(
                layer['layer_title'], title_elems[0].text, url))

        expected = 'en'
        found = title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect attribute for <Title>. Expected {}, found {}. Url: {}'.
            format(expected, found, url))

        abstract_elems = layer_elem.findall('Abstract')
        self.assertNotEqual(
            len(abstract_elems), 0,
            'Abstract not found in generated TWMS GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(abstract_elems), 1,
            'Incorrect number of <Abstract> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            abstract_elems[0].text, layer['abstract'],
            '<Abstract> element incorrect, expected {}, found {}. Url:{}'.
            format(layer['abstract'], abstract_elems[0].text, url))

        expected = 'en'
        found = abstract_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect attribute for <Abstract>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        bbox_elems = layer_elem.findall('LatLonBoundingBox')
        self.assertNotEqual(
            len(bbox_elems), 0,
            'LatLonBoundingBox not found in generated TWMS GC file. Url: {}'.
            format(url))
        self.assertEqual(
            len(bbox_elems), 1,
            'Incorrect number of <LatLonBoundingBox> elements found -- should only be 1. Url: {}'
            .format(url))

        attrs = ['minx', 'miny', 'maxx', 'maxy']
        bbox = ['-180', '-90', '180', '90']
        for attr, expected in zip(attrs, bbox):
            found = bbox_elems[0].get(attr)
            self.assertEqual(
                found, expected,
                'Incorrect attribute for <LatLonBoundingBox>. Expected {}, found {}. Url: {}'
                .format(expected, found, url))

        style_elems = layer_elem.findall('Style')
        self.assertNotEqual(
            len(style_elems), 0,
            'Style not found in generated TWMS GC file. Url: {}'.format(url))
        self.assertEqual(
            len(style_elems), 1,
            'Incorrect number of <Style> elements found -- should only be 1. Url: {}'
            .format(url))

        style_name_elems = style_elems[0].findall('Name')
        self.assertNotEqual(
            len(style_name_elems), 0,
            'Style/Name not found in generated TWMS GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(style_name_elems), 1,
            'Incorrect number of Style/Name elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            style_name_elems[0].text, 'default',
            '<Name> element incorrect, expected {}, found {}. Url:{}'.format(
                'default', style_name_elems[0].text, url))

        style_title_elems = style_elems[0].findall('Title')
        self.assertNotEqual(
            len(style_title_elems), 0,
            'Style/Title not found in generated TWMS GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(style_title_elems), 1,
            'Incorrect number of Style/Title elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            style_title_elems[0].text, '(default) Default style',
            '<Title> element incorrect, expected {}, found {}. Url:{}'.format(
                '(default) Default style', style_title_elems[0].text, url))

        expected = 'en'
        found = style_title_elems[0].get(
            '{http://www.w3.org/XML/1998/namespace}lang')
        self.assertEqual(
            found, expected,
            'Incorrect attribute "lang" for <Style>/<Title>. Expected {}, found {}. Url: {}'
            .format(expected, found, url))

        scale_hint_elems = layer_elem.findall('ScaleHint')
        self.assertNotEqual(
            len(scale_hint_elems), 0,
            'ScaleHint not found in generated TWMS GC file. Url: {}'.format(
                url))
        self.assertEqual(
            len(scale_hint_elems), 1,
            'Incorrect number of ScaleHint elements found -- should only be 1. Url: {}'
            .format(url))

        attrs = ['min', 'max']
        values = ['10', '100']
        for attr, expected in zip(attrs, values):
            found = scale_hint_elems[0].get(attr)
            self.assertEqual(
                found, expected,
                'Incorrect attribute for <ScaleHint>. Expected {}, found {}. Url: {}'
                .format(expected, found, url))

        min_scale_denom_elems = layer_elem.findall('MinScaleDenominator')
        self.assertNotEqual(
            len(min_scale_denom_elems), 0,
            '<MinScaleDenominator> not found in generated TWMS GC file. Url: {}'
            .format(url))
        self.assertEqual(
            len(min_scale_denom_elems), 1,
            'Incorrect number of <MinScaleDenominator> elements found -- should only be 1. Url: {}'
            .format(url))
        self.assertEqual(
            min_scale_denom_elems[0].text, '100',
            '<MinScaleDenominator> element incorrect, expected {}, found {}. Url:{}'
            .format('100', min_scale_denom_elems[0].text, url))

    @classmethod
    def tearDownClass(self):
        if not START_SERVER:
            shutil.rmtree(self.test_config_base_path)
            for cfg in self.test_apache_configs:
                os.remove(cfg)


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_gc_service_results.xml',
        help='Specify XML output file (default is test_date_gc_results.xml')
    parser.add_option(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        help='Output verbose debugging messages')
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Start server with all sample configurations')
    (options, args) = parser.parse_args()

    DEBUG = options.debug
    START_SERVER = options.start_server

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
