#!/bin/env python

# Copyright (c) 2002-2016, California Institute of Technology.
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
# Tests for mod_reproject
#

import os
import sys
import unittest2 as unittest
import random
import xmlrunner
import xml.dom.minidom
from shutil import move, rmtree
from optparse import OptionParser
import datetime

from oe_test_utils import check_tile_request, restart_apache, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command, get_url, check_valid_mvt

DEBUG = False


class TestModReproject(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        oedata_path = os.path.join(os.getcwd(), 'mod_onearth_test_data')
        testdata_path = os.path.join(os.getcwd(), 'mod_reproject_test_data')
        wmts_configs = ('wmts_cache_configs', 'wmts_cache_staging', 'test_imagery/cache_all_wmts.config')
        twms_configs = ('twms_cache_configs', 'twms_cache_staging', 'test_imagery/cache_all_twms.config')
        self.image_files_path = os.path.join(oedata_path, 'test_imagery')
        self.test_oe_config = os.path.join(oedata_path, 'oe_test.conf')
        self.test_apache_config = os.path.join(testdata_path, 'reproject_test.conf')
        
        for template_dir, staging_dir, cache_config in (wmts_configs, twms_configs):
            # Make staging cache files dir
            template_path = os.path.join(oedata_path, template_dir)
            staging_path = os.path.join(oedata_path, staging_dir)
            cache_path = os.path.join(oedata_path, cache_config)
            make_dir_tree(staging_path)

            # Copy XML/MRF files to staging cache files dir, swapping in the location of the imagery files
            for file in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
                file_text_replace(os.path.join(template_path, file), os.path.join(staging_path, file),
                                  '{cache_path}', self.image_files_path)

            # Run oe_create_cache_config to make the cache config files
            cmd = 'oe_create_cache_config -cbd {0} {1}'.format(staging_path, cache_path)
            run_command(cmd)
            rmtree(staging_path)

        # Put the correct path into the Apache config (oe_test.conf)
        file_text_replace(self.test_oe_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_oe_config)),
                          '{cache_path}', oedata_path)
        restart_apache()

        # Set reproject conf for Apache config (reproject_test.conf)
        file_text_replace(self.test_apache_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_config)),                           '{cache_path}', testdata_path)

        # Update configuration for mod_reproject
        # remove .cgi
        if os.path.isfile(os.path.join(testdata_path, 'wmts_endpoint/wmts.cgi')):
            move(os.path.join(testdata_path, 'wmts_endpoint/wmts.cgi'), os.path.join(testdata_path, 'wmts_endpoint/wmts.cgi.bak'))
        #if os.path.isfile(os.path.join(testdata_path, 'twms_endpoint/twms.cgi')):
            #move(os.path.join(testdata_path, 'twms_endpoint/twms.cgi'), os.path.join(testdata_path, 'twms_endpoint/twms.cgi.bak'))

        # Set reprojection layer
        file_text_replace(os.path.join(testdata_path, 'layer_configuration_file_reproject.xml'), '/etc/onearth/config/layers/layer_configuration_file_reproject.xml', '{cache_path}', testdata_path)
        #file_text_replace(os.path.join(testdata_path, 'environment_reproject.xml.orig'), os.path.join(testdata_path, 'environment_reproject.xml.oe'), '{cache_path}', oedata_path)
        file_text_replace(os.path.join(testdata_path, 'environment_reproject.xml.orig'), os.path.join(testdata_path, 'environment_reproject.xml'), '{cache_path}', testdata_path)

        # Run oe_config_layer to make the cache config files
        cmd = 'oe_configure_layer --create_mapfile --layer_dir=/etc/onearth/config/layers/ --lcdir=/etc/onearth/config --skip_empty_tiles --generate_links'
        run_command(cmd)

        restart_apache()

        # Set some handy constant values
        self.tile_hashes = {'3d5280b13cbabc41676973d26844f310': '1948-03-01',
                            '210964547845bbeb357f62c214128215': '1990-01-01',
                            '403705d851af424b3bf9cafbbf869d0c': '2000-01-01',
                            '4832d6edeed31fad0bd59bbc26d92275': '2000-06-01',
                            '7ea2038a74af2988dc432a614ec94187': '2000-07-03',
                            '03b3cc7adc929dd605d617b7066b30ae': '2000-08-01',
                            '4f24774e71560e15b5ed43fcace2cb29': '2000-09-03',
                            'fd9e3aa7c12fbf823bd339b92920784e': '2000-12-01',
                            '24f90bd216f6b7ee25501155fcc8ece4': '2001-01-01',
                            '3d12e06c60b379efc41f4b8021ce1e29': '2001-05-09',
                            'e16d97b41cbb408d2a285788dfc9e3b8': '2002-01-01',
                            'b64066bafe897f0d2c0fc4a41ae7e052': '2002-12-27',
                            '21634316da8d6e0af3ee4f24643bd72c': '2002-12-01',
                            'b3639da9334ca5c13072012f9422a03c': '2003-12-01',
                            '172ba954906b3d4f5d6583b3ad88460f': '2004-12-01',
                            'f4426ab405ce748b57b34859b3811bf6': '2005-01-01',
                            '65e2446b2f779b963d0127f374a36fba': '2005-12-01',
                            'faf5788ab8e006bbcfe18be80d472840': '2006-12-01',
                            'd834056e48a95e39f55401eb61f710cd': '2007-12-01',
                            '9a3cf29a5df271c41eefc5c989fd690d': '2008-01-01',
                            'd03e3e3cdfef2b6e3d1870f26a88fe53': '2008-12-01',
                            '59692a541429c929117c854fe9e423c9': '2009-12-01',
                            '84eba8cdbb26444dbc97e119c0b76728': '2010-01-01',
                            '91206f8c5a4f6fcdcab366ea00a1f53c': '2010-01-09',
                            '9aa3115cde41a8b9c68433741d98a8b4': '2010-12-01',
                            'dae12a917a5d672c4cce4fdaf4788bf3': '2011-12-01',
                            '5346e958989b57c45919604ecf909f43': '2012-03-11',
                            '92e5d5eef4dc6866b636a49bfae3e463': '2015-01-01',
                            '5d91fa0c5273b2b58c486a15c91b2e78': '2015-01-02',
                            '81b8d855e38e6783f14899ff89a2c878': '2015-10-01',
                            '7f2992ac0986784c28d93840b1e984c4': '2016-02-29',
                            '1571c4d601dfd871e7680e279e6fd39c': '2015-01-12',
                            'b69307895d6cb654b98d247d710dd806': '2015-12-01',
                            'ba366ccd45a8f1ae0ed2b65cf67b9787': '2016-01-01',
                            '5e11f1220da2bb6f92d3e1c998f20bcf': 'black'}

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_wmts_no_time_jpg(self):
        """
        1. Request current (no time) JPG tile via WMTS

        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'

        # The URL of the tile to be requested
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'

        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG tile via WMTS'
            print 'URL: ' + req_url

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_no_time_jpg(self):
        """
        1B. Request current (no time) JPG tile via WMTS (REST)

        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'

        # The URL of the tile to be requested
        # {wmtsBaseUrl}/{layer}/{style}/{dimension1}/.../{dimensionN}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}{formatExtension}
        req_url = 'http://localhost/reproject/test/wmts/test_weekly_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'

        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG tile via WMTS REST'
            print 'URL: ' + req_url

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS REST JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_no_time_png(self):
        """
        2 .Request current (no time) PNG tile via WMTS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no time) PNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_no_time_png(self):
        """
        2B. Request current (no time) PNG tile via WMTS REST
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/test_daily_png/default/GoogleMapsCompatible_Level3/0/0/0.png'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no time) PNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS REST PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_no_time_ppng(self):
        """
        3. Request current (no time) PPNG tile via WMTS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no time) PPNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_no_time_ppng(self):
        """
        3B. Request current (no time) PPNG tile via WMTS REST
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/test_daily_png/default/GoogleMapsCompatible_Level3/0/0/0.png'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no time) PPNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMTS REST PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_jpg(self):
        """
        4. Request current (time=default) JPEG tile via WMTS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (time=default) JPG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_default_time_jpg(self):
        """
        4B. Request current (time=default) JPEG tile via WMTS REST
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        # https://gibs/earrthdata.nasa.gov/wmts/epsg{EPSG:Code}/best/{ProductName}/default/{time}/{TileMatrixSet}/{ZoomLevel}/{TileRow}/{TileColumn}.png
        req_url = 'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (time=default) JPG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS REST JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_png(self):
        """
        5. Request current (time=default) PNG tile via WMTS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        if DEBUG:
            print '\nTesting: Request current (time=default) PNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_default_time_png(self):
        """
        5B. Request current (time=default) PNG tile via WMTS REST
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/test_daily_png/default/default/GoogleMapsCompatible_Level3/0/0/0.png'
        if DEBUG:
            print '\nTesting: Request current (time=default) PNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS REST PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_ppng(self):
        """
        6. Request current (time=default) PPNG tile via WMTS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_daily_png&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        if DEBUG:
            print '\nTesting: Request current (time=default) PPNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_default_time_ppng(self):
        """
        6B. Request current (time=default) PPNG tile via WMTS REST
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/wmts/test_daily_png/default/default/GoogleMapsCompatible_Level3/0/0/0.png'
        if DEBUG:
            print '\nTesting: Request current (time=default) PPNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS REST PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_jpg(self):
        """
        7. Request current (no time) JPEG tile via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
#http://localhost:4000/reproject/test/twms/twms.cgi?request=GetMap&layers=test_nonyear_jpg&srs=EPSG:3857&format=image/jpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&time=2012-02-29
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&amp;layers=test_nonyear_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nNEED TIME SPECIFIED!!! Testing: Request current (no TIME) JPG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current JPG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_png(self):
        """
        8. Request current (no time) PNG tile via TWMS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:3857&format=image%2Fpng&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nTesting: Request current (no TIME) PNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_ppng(self):
        """
        9. Request current (no time) PPNG tile via TWMS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:3857&format=image%2Fpng&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nTesting: Request current (no TIME) PPNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PPNG request does not match what\'s expected. URL: ' + req_url)

    # REQUEST WITH DATE/TIME AND STATIC TESTS

    def test_request_wmts_date_from_year_layer(self):
        """
        10. Request tile with date from "year" layer via WMTS
        """
        ref_hash = '7c7fcdfaea0faf91afdd690eb7fe4dea'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-22'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_date_from_year_layer(self):
        """
        10B. Request tile with date from "year" layer via WMTS (REST)
        """
        ref_hash = '7c7fcdfaea0faf91afdd690eb7fe4dea'
        req_url = 'http://localhost/reproject/test/wmts/test_weekly_jpg/default/2012-02-22/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_from_year_layer(self):
        """
        10C. Request tile with date from "year" layer via TWMS
        """
        ref_hash = '7c7fcdfaea0faf91afdd690eb7fe4dea'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&TIME=2012-02-22'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_date_from_noyear_layer(self):
        """
        11. Request tile with date  from "non-year" layer via WMTS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date  from "non-year layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_date_from_noyear_layer(self):
        """
        11B. Request tile with date  from "non-year" layer via WMTS (REST)
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/test_nonyear_jpg/default/2012-02-29/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date  from "non-year layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_from_noyear_layer(self):
        """
        11C. Request tile with date from "non-year" layer via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
##request=GetMap&layers=test_weekly_jpg&srs=EPSG:3857&format=image/jpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925
#request=GetMap&layers=test_nonyear_jpg&srs=EPSG:3857&format=image/jpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_nonyear_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date from "non-year layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_legacy_datetime_from_year_layer(self):
        """
        12. Request tile with date and time (sub-daily) from "year" layer via WMTS
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_legacy_datetime_from_year_layer(self):
        """
        12B. Request tile with date and time (sub-daily) from "year" layer via WMTS (REST)
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/wmts/test_legacy_subdaily_jpg/default/2012-02-29T12:00:00Z/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_legacy_datetime_from_year_layer(self):
        """
        12C. Request tile with date and time (sub-daily) from "year" layer via TWMS
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_legacy_subdaily_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_year_zlevel(self):
        """
        13. Request tile with date and time (z-level) from "year" layer via WMTS
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_zindex_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T16:00:00Z'
        if DEBUG:
            print '\nTIME FORMAT!!! Testing: Request tile with date and time (z-level) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS Z-Level JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_year_zlevel(self):
        """
        13B. Request tile with date and time (z-level) from "year" layer via WMTS (REST)
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/wmts/test_zindex_jpg/default/2012-02-29T16:00:00Z/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date and time (z-level) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) Z-Level JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_year_zlevel(self):
        """
        13C. Request tile with date and time (z-level) from "year" layer via TWMS
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_zindex_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&time=2012-02-29T16:00:00Z&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS Z-Level JPEG Tile request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_nodate_from_year_layer(self):
        """
        14. Request tile with no date from "year" layer via WMTS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_nodate_from_year_layer(self):
        """
        14B. Request tile with no date from "year" layer via WMTS (REST)
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/test_weekly_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_nodate_from_year_layer(self):
        """
        14C. Request tile with no date from "year" layer via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_nodate_from_noyear_layer(self):
        """
        15. Request tile with no date from "non-year" layer via WMTS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTIME NEEDED!!! Testing: Request tile with no date from "non-year layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_nodate_from_noyear_layer(self):
        """
        15B. Request tile with no date from "non-year" layer via WMTS (REST)
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/test_nonyear_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTIME NEEDED!!! Testing: Request tile with no date from "non-year layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_nodate_from_noyear_layer(self):
        """
        15C. Request tile with no date from "non-year" layer via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_nonyear_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nTIME NEEDED!!! Testing: Request tile with no date from "non-year layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_legacy_nodate_from_year_layer(self):
        """
        16. Request tile with no date and time (sub-daily) from "year" layer via WMTS
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nERROR!!! Testing: Request tile with no date and time (legacy sub-daily) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_legacy_nodate_from_year_layer(self):
        """
        16B. Request tile with no date and time (sub-daily) from "year" layer via WMTS (REST)
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/wmts/test_legacy_subdaily_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nERROR!!! Testing: Request tile with no date and time (legacy sub-daily) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_legacy_nodate_from_year_layer(self):
        """
        16C. Request tile with no date and time (sub-daily) from "year" layer via TWMS
        """
        ref_hash = 'fd4fe96d84e4f10e61029890293fa3c8'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_legacy_subdaily_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nERROR!!! Testing: Request tile with no date and time (legacy sub-daily) from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_nodate_year_zlevel(self):
        """
        17. Request tile with no date and time (z-level) from "year" layer via WMTS
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_zindex_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nERROR!!! Testing: Request tile with no date and time (z-level) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS Z-Level JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_nodate_year_zlevel(self):
        """
        17B. Request tile with no date and time (z-level) from "year" layer via WMTS (REST)
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/wmts/test_zindex_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nERROR!!! Testing: Request tile with no date and time (z-level) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) Z-Level JPG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_nodate_year_zlevel(self):
        """
        17C. Request tile with no date and time (z-level) from "year" layer via TWMS
        """
        ref_hash = '36bb79a33dbbe6173990103a8d6b67cb'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_zindex_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS Z-Level no date and time JPEG Tile request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_static_notime(self):
        """
        18. Request tile from static layer with no time via WMTS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_static_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_static_notime(self):
        """
        18B. Request tile from static layer with no time via WMTS (REST)
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/test_static_jpg/default/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_static_notime(self):
        """
        18C. Request tile from static layer with no time via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_static_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_default_jpg(self):
        """
        19. Request current (default time) JPEG tile via TWMS
        """
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&time=default'
        if DEBUG:
            print '\nTesting: Request current (default TIME) JPG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current JPG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_default_png(self):
        """
        20. Request current (default time) PNG tile via TWMS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:3857&format=image%2Fpng&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&time=default'
        if DEBUG:
            print '\nTesting: Request current (default TIME) PNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_default_ppng(self):
        """
        21. Request current (no time) PPNG tile via TWMS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:3857&format=image%2Fpng&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&time=default'
        if DEBUG:
            print '\nTesting: Request current (default TIME) PPNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PPNG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_png(self):
        """
        19. Request tile with date via TWMS
        """
        ref_hash = '6df00a0095f3df8586572988f6cb7e84'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:3857&format=image%2Fpng&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS PNG request with date does not match what\'s expected. URL: ' + req_url)

    # GETCAPABILITIES AND GETTILESERVICE REQUEST TESTS

    def test_wmts_get_capabilities(self):
        """
        20. ERROR!!! Request WMTS GetCapabilities
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting WMTS GetCapablities'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WTMTS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_rest_get_capabilities(self):
        """
        21. ERROR!!! Request WMTS (REST) GetCapabilities
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/reproject/test/wmts/1.0.0/WMTSCapabilities.xml'
        if DEBUG:
            print '\nTesting WMTS (REST) GetCapablities'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except ElementTree.ParseError:
            xml_check = False
        self.assertTrue(xml_check, 'GetCapabilities response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'mod_onearth_test_data/wmts_endpoint/1.0.0/WMTSCapabilities.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WTMTS (REST) Get Capabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_capabilities(self):
        """
        22. Request TWMS GetCapabilities
        """
        ref_hash = '8663c1e1d45e4be1cdaefc8e6749ead4'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting TWMS GetCapablities'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_tile_service(self):
        """
        23. Request TWMS GetTileService
        """
        ref_hash = '7555d5ad3cca96aa8cbc8a36f5e04f19'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?Request=GetTileService'
        if DEBUG:
            print '\nTesting TWMS GetTileService'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except ElementTree.ParseError:
            xml_check = False
        self.assertTrue(xml_check, 'GetTileService response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'mod_onearth_test_data/GetTileService.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'TWMS Get GetTileService Request does not match what\'s expected. URL: ' + req_url)

    # REQUEST SYNTAX TESTS (capitalization, parameter ordering, error handling, REST)

    def test_url_parameter_case_insensitivity(self):
        """
        24. URL Parameter Case Insensitivity
        """
        # Randomly capitalizes and lower-cases parameters and checks the tile resulting from the request. Tries 10 different combinations.
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=GoogleMapsCompatible_Level3', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        if DEBUG:
            print '\nTesting URL Parameter Insensitivity'
        for _ in range(10):
            test_params = []
            for param in params:
                param_split = param.split('=')
                case = random.randint(0, 1)
                if case:
                    param_split[0] = param_split[0].upper()
                else:
                    param_split[0] = param_split[0].lower()
                test_params.append('='.join(param_split))
            req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?' + '&'.join(test_params)
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_url_parameter_reordering(self):
        """
        25. URL Parameter Reordering
        """
        # Test 20 random permutations of the given param strings
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        params = ['layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=GoogleMapsCompatible_Level3', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0']
        if DEBUG:
            print 'Testing URL Parameter Reordering'
        for _ in range(20):
            random.shuffle(params)
            param_string = '&'.join(params)
            req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?' + param_string
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_error_handling(self):
        """
        26. WMTS Error handling
        """
        # MissingParameterValue test
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'version=1.0.0',
                  'TileMatrixSet=GoogleMapsCompatible_Level3', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        if DEBUG:
            print '\nTesting WMTS Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?request=GetTile&time=default&' + '&'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad SERVICE value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Service=bad_value',
            # Bad VERSION value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Version=bad_value',
            # Bad LAYER value
            'http://localhost/reproject/test/wmts/wmts.cgi?tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&layer=bad_layer_value',
            # Bad STYLE value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&style=bad_value',
            # Bad FORMAT value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&TileMatrix=0&TileCol=0&TileRow=0&time=default&Format=fake_image',
            # Bad TILEMATRIXSET value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&tilematrixset=fake_tilematrixset',
            # Bad (non-positive integer) TILEMATRIX value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=-20',
            # Bad (non-positive integer) TILEROW value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&time=default&TileRow=-20',
            # Bad (non-positive integer) TILECOL value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileRow=0&time=default&TileCol=-20',
            # Invalid TILEMATRIX value
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=20',
            # Invalid TIME format
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-290'
        )
        for req_url in invalid_parameter_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # OperationNotSupported tests
        response_code = 501
        response_value = 'OperationNotSupported'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetLegendGraphic&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
        if DEBUG:
            print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
        check_code = check_response_code(req_url, response_code, response_value)
        error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
        self.assertTrue(check_code, error)

        # TileOutOfRange tests
        response_code = 400
        response_value = 'TileOutOfRange'
        tile_outofrange_urls = (
            # TileCol out of range
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=50&TileRow=0&time=default',
            # TileRow out of range
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=50&time=default'
        )
        for req_url in tile_outofrange_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # Test if empty tile is served for out of time bounds request
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        empty_urls = (  # Date before range
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01',
            # Date after range
            'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-03-01'
        )
        for url in empty_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting empty tile'.format(url)
            check_result = check_tile_request(url, ref_hash)
            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=GoogleMapsCompatible_Level3&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-29&twoplustwo=five'
        if DEBUG:
            print 'Using URL: {0}, expecting bad parameter will be ignored'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Bad parameter request is not ignored. URL: ' + url)

    def test_wmts_rest_error_handling(self):
        """
        27. WMTS REST requests
        """
        # MissingParameterValue test
        params = ('test_weekly_jpg', 'default', 'GoogleMapsCompatible_Level3', '0', '0', '0.jpeg')
        if DEBUG:
            print '\nTesting WMTS REST Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/reproject/test/wmts/' + '/'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS REST response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad LAYER value
            'http://localhost/reproject/test/wmts/bad_layer_value/default/default/GoogleMapsCompatible_Level3/0/0/0.jpeg',
            # Bad STYLE value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/bad_value/default/GoogleMapsCompatible_Level3/0/0/0.jpeg',
            # Bad FORMAT value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/0/0.fake',
            # Bad TILEMATRIXSET value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/fake_tilematrixset/0/0/0.jpeg',
            # Bad (non-positive integer) TILEMATRIX value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/-20/0/0.jpeg',
            # Bad (non-positive integer) TILEROW value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/-20/0.jpeg',
            # Bad (non-positive integer) TILECOL value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/0/-20.jpeg',
            # Invalid TILEMATRIX value
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/20/0/0.jpeg',
            # Invalid TIME format
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/2012-02-290/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        )
        for req_url in invalid_parameter_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS REST response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # TileOutOfRange tests
        response_code = 400
        response_value = 'TileOutOfRange'
        tile_outofrange_urls = (
            # TileCol out of range
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/50/0.jpeg',
            # TileRow out of range
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/default/GoogleMapsCompatible_Level3/0/0/50.jpeg'
        )
        for req_url in tile_outofrange_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The WMTS REST response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # Test if empty tile is served for out of time bounds request
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        empty_urls = (  # Date before range
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/2012-01-01/GoogleMapsCompatible_Level3/0/0/0.jpeg',
            # Date after range
            'http://localhost/reproject/test/wmts/test_weekly_jpg/default/2012-03-01/GoogleMapsCompatible_Level3/0/0/0.jpeg'
        )
        for url in empty_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting empty tile'.format(url)
            check_result = check_tile_request(url, ref_hash)
            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
        ref_hash = '4e34c9517e0c30b1253bd499de4f8d12'
        req_url = 'http://localhost/reproject/test/wmts/test_weekly_jpg/default/2012-02-29/GoogleMapsCompatible_Level3/0/0/0.jpeg/five'
        if DEBUG:
            print 'Using URL: {0}, expecting bad parameter will be ignored'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Bad parameter request is not ignored. URL: ' + url)

    def test_twms_error_handling(self):
        """
        28. TWMS requests
        """
        # MissingParameterValue test
#request=GetMap&layers=test_weekly_jpg&srs=EPSG:3857&format=image%2Fjpeg&styles=&width=256&height=256&bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925&TME=2012-02-29
        params = ('layers=test_weekly_jpg', 'srs=EPSG:3857', 'format=image%2Fjpeg', 'styles=', 'width=256', 'height=256', 'bbox=-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925')
        if DEBUG:
            print '\nTesting TWMS Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&time=default&' + '&'.join(param_list)
            response_code = 400
            #response_value = 'MissingParameterValue'
            response_value = 'Bad'
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad LAYER value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=bad_layer_value&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=512&height=512&bbox=-180,-198,108,90',
            # Bad STYLE value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=bad_value&&width=512&height=512&bbox=-180,-198,108,90',
            # Bad FORMAT value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=fake_image&styles=&&width=512&height=512&bbox=-180,-198,108,90',
            # Bad SRS value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=fake_tilematrixset&format=image%2Fjpeg&styles=&&width=512&height=512&bbox=-180,-198,108,90',
            # Bad (non-positive integer) WIDTH value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=-512&height=512&bbox=-180,-198,108,90',
            # Bad (non-positive integer) HEIGHT value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=512&height=-512&bbox=-180,-198,108,90',
            # Bad (large integer) BBOX value
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=512&height=512&bbox=-180,-198,1080,900',
            # Invalid TIME format
            'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=512&height=512&bbox=-180,-198,108,90&time=2012-02-290'
        )
        for req_url in invalid_parameter_urls:
            if DEBUG:
                print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            check_code = check_response_code(req_url, response_code, response_value)
            error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            self.assertTrue(check_code, error)

        # Test if empty tile is served for Bad Time
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        req_url = 'http://localhost/reproject/test/twms/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&&width=512&height=512&bbox=-180,-198,108,90&time=2012-02-290'
        if DEBUG:
            print 'Using URL: {0}, expecting empty tile'.format(req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'The TWMS response for Bad Time does not match what\'s expected. URL: ' + req_url)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_oe_config)))
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_apache_config)))
        restart_apache()
        os.remove(os.path.join(self.image_files_path, 'cache_all_wmts.config'))
        os.remove(os.path.join(self.image_files_path, 'cache_all_twms.config'))
        ##move(os.path.join(testdata_path, 'wmts_endpoint/wmts.cgi.bak'), os.path.join(oedata_path, 'wmts_endpoint/wmts.cgi'))


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_reproject_results.xml',
                      help='Specify XML output file (default is test_mod_reproject_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModReproject.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
