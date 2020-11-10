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

#
# Tests for WMS/WFS
#

import os
import sys
import unittest2 as unittest
import random
import xmlrunner
import xml.dom.minidom
from shutil import rmtree
from optparse import OptionParser
import datetime
import json
from xml.etree import cElementTree as ElementTree

from oe_test_utils import check_tile_request, restart_apache, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command, get_url, XmlDictConfig, check_dicts, check_wmts_error

DEBUG = False

class TestMapserver(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        testdata_path = os.path.join(os.getcwd(), 'mapserver_test_data')

    def test_request_wms_no_time_jpg(self):
        """
        1. Request current (no time) JPEG via WMS
        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = 'f22eb8446a4411ba6843d24d3fbd3721'

        # The URL of the tile to be requested
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=test_static_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'

        # Debug message (if DEBUG is set)
        if DEBUG:
            print('\nTesting: Request current (no TIME) JPG via WMS')
            print('URL: ' + req_url)

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMS JPG Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wms_no_time_png(self):
        """
        2. Request current (no time) PNG via WMS
        """
        ref_hash = '2a14051fb08e4bd18cbe349dd51bcbba'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_static_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'
        if DEBUG:
            print('\nTesting: Request current (no TIME) PNG via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMS PNG Request does not match what\'s expected. URL: ' + req_url)
    
    def test_request_wms_default_time_jpg(self):
        """
        3. Request current (time=default) JPEG tile via WMS
        """
        ref_hash = 'f22eb8446a4411ba6843d24d3fbd3721'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fjpeg&TRANSPARENT=true&LAYERS=test_static_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=default'
        if DEBUG:
            print('\nTesting: Request current (time=default) JPEG tile via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Request current (time=default) JPEG tile via WMS does not match what\'s expected. URL: ' + req_url)    

    def test_request_wms_default_time_png(self):
        """
        4. Request current (time=default) PNG tile via WMS
        """
        ref_hash = '2a14051fb08e4bd18cbe349dd51bcbba'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_static_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=default'
        if DEBUG:
            print('\nTesting: Request current (time=default) PNG tile via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Request current (time=default) PNG tile via WMS does not match what\'s expected. URL: ' + req_url)

    def test_request_wms_date_layer(self):
        """
        5. Request tile with date from "year" layer via WMS
        """
        ref_hash = 'b66c0096d12f89b50623a8f2f9e86f24'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_weekly_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&time=2012-02-22'
        if DEBUG:
            print('\nTesting: Request tile with date from "year" layer via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_wms_get_capabilities_1_1_1(self):
        """
        8. Request WMS GetCapabilities 1.1.1
        """
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities'
        if DEBUG:
            print('\nTesting WMS GetCapablities 1.1.1')
            print('URL: ' + req_url)
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'WMS GetCapabilities 1.1.1 response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'mapserver_test_data/GetCapabilities.1.1.1.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WMS Get GetCapabilities 1.1.1 Request does not match what\'s expected. URL: ' + req_url)
        
    def test_wms_get_capabilities_1_3_0(self):
        """
        9. Request WMS GetCapabilities 1.3.0
        """
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities'
        if DEBUG:
            print('\nTesting WMS GetCapablities 1.3.0')
            print('URL: ' + req_url)
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False

        self.assertTrue(xml_check, 'WMS GetCapabilities 1.3.0 response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'mapserver_test_data/GetCapabilities.1.3.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WMS Get GetCapabilities Request 1.3.0 does not match what\'s expected. URL: ' + req_url)
        
    def test_wfs_get_capabilities_2_0_0(self):
        """
        10. Request WFS GetCapabilities 2.0.0
        """
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities'
        if DEBUG:
            print('\nTesting WFS GetCapablities 2.0.0')
            print('URL: ' + req_url)
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'WMS GetCapabilities 2.0.0 response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'mapserver_test_data/GetCapabilities.2.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WFS Get GetCapabilities Request 2.0.0 does not match what\'s expected. URL: ' + req_url)
 
    def test_request_wms_layer_error(self):
        """
        11. Request erroneous layer via WMS
        """
        ref_hash = '8ff06e9113d2ebbfebb2505c2c8e864e'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=blah&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'
        if DEBUG:
            print('\nTesting: Request erroneous layer via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Request erroneous layer via WMS does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_datetime_with_regular_time(self):
        """
        12. Request tile with date and time (sub-daily) and another layer with YYYY-MM-DD time via WMS
        """
        ref_hash = '8aa5908b251f3d9122a25ae93ec9fef2'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_weekly_jpg,test_legacy_subdaily_jpg&map.layer[test_legacy_subdaily_jpg]=OPACITY+50&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print('\nTesting: Request tile with date and time (sub-daily) and another layer with YYYY-MM-DD time via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS tile with date and time (sub-daily) and another layer with YYYY-MM-DD time does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_datesnap(self):
        """
        13. Request tile with multi-day period and snap to available date via WMS
        """
        ref_hash = '9b0659e9804de008e48093931fbe9e4b'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2015-01-15'
        if DEBUG:
            print('\nTesting: Request tile with multi-day period and snap to available date via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS tile with multi-day period and snap to available date does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_datesnap_multilayer(self):
        """
        14. Request multiple layers with multi-day period and snap to available date via WMS
        """
        ref_hash = 'ec5a4906f8a7498cbbc73dafd608b618'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&map.layer[snap_test_3b]=OPACITY+50&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2015-12-15'
        if DEBUG:
            print('\nTesting: Request  multiple layers with multi-day period and snap to available date via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers with multi-day period and snap to available date does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_datesnap_outofrange(self):
        """
        15. Request multiple layers with multi-day period and snap to date that is out of range via WMS
        """
        ref_hash = '3f935e491dc208f39c6a34b1db9caa65'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-04-02'
        if DEBUG:
            print('\nTesting: Request  multiple layers with multi-day period and snap to date that is out of range via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers with multi-day period and snap to date that is out of range does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_datesnap_some_layers_outofrange(self):
        """
        16. Request multiple layers with multi-day period and snap to date that is out of range for one of the layers via WMS
        """
        ref_hash = '64096bc3d66c6200ff45ee13930e3df7'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-03-02'
        if DEBUG:
            print('\nTesting: Request  multiple layers with multi-day period and snap to date that is out of range for one of the layers via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers with multi-day period and snap to date that is out of range for one of the layers does not match what\'s expected. URL: ' + req_url)
        
    # Waiting for "GITC-1327 Validate WMS time format" to be implemented. 
#     def test_request_wms_baddateformat(self):
#         """
#         17. Request multiple layers with bad date format via WMS
#         """
#         ref_hash = 'c8f9d083f85fca56a7c0539fc5813793'
#         req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-03'
#         if DEBUG:
#             print('\nTesting: Request multiple layers bad date format via WMS')
#             print('URL: ' + req_url)
#         check_result = check_wmts_error(req_url, 400, ref_hash)
#         self.assertTrue(check_result, 'WMS multiple layers bad date format does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_reprojection(self):
        """
        18. Request layer with date and reproject from EPSG:4326 to EPSG:3857 via WMS
        """
        ref_hash = 'bea72af03789933b7d7f5405522d58fc'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_weekly_jpg&CRS=EPSG%3A3857&STYLES=&WIDTH=1280&HEIGHT=1280&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34&time=2012-02-22'
        if DEBUG:
            print('\nTesting: Request layer with date and reproject from EPSG:4326 to EPSG:3857')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS request layer with date and reproject from EPSG:4326 to EPSG:3857 does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_reprojection_multilayer(self):
        """
        19. Request multiple layers and reproject from EPSG:4326 to EPSG:3857 via WMS
        """
        ref_hash = '2379ec819b6dc11e599a750ccc173ac0'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_static_jpg,snap_test_3a,snap_test_3b&map.layer[snap_test_3a]=OPACITY+50&map.layer[snap_test_3b]=OPACITY+50&CRS=EPSG:3857&STYLES=&WIDTH=1280&HEIGHT=1280&BBOX=-20037508.34,-20037508.34,20037508.34,20037508.34&TIME=2015-01-01'
        if DEBUG:
            print('\nTesting: Request multiple layers and reproject from EPSG:4326 to EPSG:3857 via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers and reproject from EPSG:4326 to EPSG:3857 does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_subdaily_timesnap(self):
        """
        20. Request tile with time (sub-daily) and snap to available date time via WMS
        """
        ref_hash = 'cd18076fca03c636843c5b664097c17f'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_legacy_subdaily_jpg&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print('\nTesting: Request tile with date and time (sub-daily) and another layer with YYYY-MM-DD time via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS tile with date and time (sub-daily) and another layer with YYYY-MM-DD time does not match what\'s expected. URL: ' + req_url)
        
    # KML contains unique identifiers    
#     def test_request_wms_kmz(self):
#         """
#         xx. Request current (no time) KMZ via WMS
#         """
#         ref_hash = '91445bf3909302f0593bf514bce1d523'
#         req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=application/vnd.google-earth.kmz&TRANSPARENT=true&LAYERS=test_static_jpg&CRS=EPSG:4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'
#         if DEBUG:
#             print('\nTesting: Request current (no time) KMZ via WMS')
#             print('URL: ' + req_url)
#         check_result = check_tile_request(req_url, ref_hash)
#         self.assertTrue(check_result, 'WMS KMZ does not match what\'s expected. URL: ' + req_url)

    def test_request_wms_from_vector(self):
        """
        21. Request image from vector source file with time via WMS
        """
        ref_hash = 'e014ec400b5807dc04cc8dbb5d9cebee'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=Terra_Orbit_Dsc_Dots&CRS=EPSG%3A4326&STYLES=&WIDTH=1024&HEIGHT=512&BBOX=-180,-90,180,90&TIME=2016-03-05'
        if DEBUG:
            print('\nTesting: Request image from vector source file with time via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS request from vector layer does not match what\'s expected. URL: ' + req_url)
 
    def test_request_wfs_geojson(self):
        """
        22. Request GeoJSON from vector source file via WFS
        """
        ref_hash = 'd28dab255366e4bf69d8eaf6d649d930'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=Terra_Orbit_Dsc_Dots&OUTPUTFORMAT=geojson'
        if DEBUG:
            print('\nTesting: Request GeoJSON from vector source file via WFS')
            print('URL: ' + req_url)
        response = get_url(req_url)
 
        # Check if the response is valid JSON
        try:
            JSONdict = json.loads(response.read().decode('utf-8'))
            JSON_check = True
        except:
            JSON_check = False
        self.assertTrue(JSON_check, 'WFS GeoJSON response is not a valid JSON file. URL: ' + req_url)
 
        with open(os.path.join(os.getcwd(), 'mapserver_test_data/wfs_geojson.txt')) as JSONfile:
            refJSONdict = json.load(JSONfile)
 
        check_result = check_dicts(JSONdict, refJSONdict)
        self.assertTrue(check_result, 'WMS request GeoJSON from vector source file via WFS does not match what\'s expected. URL: ' + req_url)
         
    def test_request_wfs_csv(self):
        """
        23. Request CSV from vector source file via WFS
        """
        ref_hash = '5e14e53eec6b21de6e22be093b5763e4'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=Terra_Orbit_Dsc_Dots&OUTPUTFORMAT=csv'
        if DEBUG:
            print('\nTesting: Request CSV from vector source file via WFS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS request CSV from vector source file via WFS does not match what\'s expected. URL: ' + req_url)
         
    def test_request_wfs_geojson_with_time(self):
        """
        24. Request GeoJSON from vector source file with time via WFS
        """
        ref_hash = 'd28dab255366e4bf69d8eaf6d649d930'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=Terra_Orbit_Dsc_Dots&OUTPUTFORMAT=geojson&TIME=2016-03-05'
        if DEBUG:
            print('\nTesting: Request GeoJSON from vector source file with time via WFS')
            print('URL: ' + req_url)
        response = get_url(req_url)
 
        # Check if the response is valid JSON
        try:
            JSONdict = json.loads(response.read().decode('utf-8'))
            JSON_check = True
        except:
            JSON_check = False
        self.assertTrue(JSON_check, 'WFS with time GeoJSON response is not a valid JSON file. URL: ' + req_url)
 
        with open(os.path.join(os.getcwd(), 'mapserver_test_data/wfs_geojson_time.txt')) as JSONfile:
            refJSONdict = json.load(JSONfile)
 
        check_result = check_dicts(JSONdict, refJSONdict)
        self.assertTrue(check_result, 'WMS request GeoJSON from vector source file with time via WFS does not match what\'s expected. URL: ' + req_url)
         
    def test_request_wfs_csv_with_time(self):
        """
        25. Request CSV from vector source file with time via WFS
        """
        ref_hash = '5e14e53eec6b21de6e22be093b5763e4'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAME=Terra_Orbit_Dsc_Dots&OUTPUTFORMAT=csv&TIME=2016-03-05'
        if DEBUG:
            print('\nTesting: Request CSV from vector source file with time via WFS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS request CSV from vector source file with time via WFS does not match what\'s expected. URL: ' + req_url)

    def test_request_wms_baddate(self):
        """
        26. Request multiple layers with bad date via WMS
        """
        ref_hash = '3f935e491dc208f39c6a34b1db9caa65'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-11-31'
        if DEBUG:
            print('\nTesting: Request multiple layers bad date via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers bad date does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_badtime(self):
        """
        27. Request multiple layers with bad time via WMS
        """
        ref_hash = '64096bc3d66c6200ff45ee13930e3df7'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-03-02T23:30:99Z'
        if DEBUG:
            print('\nTesting: Request multiple layers bad time via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers bad time does not match what\'s expected. URL: ' + req_url)
    
    # Waiting for "GITC-1327 Validate WMS time format" to be implemented. 
#     def test_request_wms_badtimeformat(self):
#         """
#         28. Request multiple layers with bad time format via WMS
#         """
#         ref_hash = 'c8f9d083f85fca56a7c0539fc5813793'
#         req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=snap_test_3a,snap_test_3b&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME=2016-03-02T23:30:59'
#         if DEBUG:
#             print('\nTesting: Request multiple layers bad time format via WMS')
#             print('URL: ' + req_url)
# 
#         check_result = check_wmts_error(req_url, 400, ref_hash)
#         self.assertTrue(check_result, 'WMS multiple layers bad time format does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_no_layer_error(self):
        """
        29. Request missing layers via WMS
        """
        ref_hash = '76453fe3c6c2490243d41595c964b2e8'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'
        if DEBUG:
            print('\nTesting: Request missing layers via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Request missing layers via WMS does not match what\'s expected. URL: ' + req_url)
        
    def test_request_wms_multilayer(self):
        """
        30. Request multiple layers in one request with no time
        """
        ref_hash = '3af983385aafa0323f410496f6e04453'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS=test_static_jpg,snap_test_3b&map.layer[snap_test_3b]=OPACITY+50&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270'
        if DEBUG:
            print('\nTesting: Request multiple layers in one request with no time via WMS')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS multiple layers with no time does not match what\'s expected. URL: ' + req_url)
       
    def test_request_wms_getlegendgraphic(self):
        """
        31. Test GetLegendGraphic request
        """
        ref_hash = '13b34c39c2fda83972a2df4cc2b5c394'
        req_url = 'http://localhost/wms/test/wms.cgi?SERVICE=WMS&VERSION=1.3.0&REQUEST=getlegendGRAPHIC&layer=Terra_Orbit_Dsc_Dots&FORMAT=image/png&SLD_VERSION=1.1.0'
        if DEBUG:
            print('\nTesting: Request WMS GetLegendGraphic')
            print('URL: ' + req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMS GetLegendGraphic does not match what\'s expected. URL: ' + req_url)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_oems_results.xml',
                      help='Specify XML output file (default is test_mod_onearth_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestMapserver.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )