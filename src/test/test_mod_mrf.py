#!/bin/env python

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

#
# Tests for mod_mrf
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
from xml.etree import cElementTree as ElementTree
import urllib2
from oe_test_utils import check_tile_request, restart_apache, restart_redis, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command, get_url, XmlDictConfig, check_dicts, check_valid_mvt

DEBUG = False


class TestModMrf(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        testdata_path = os.path.join(os.getcwd(), 'ci_tests')
        httpd_config = os.path.join(testdata_path, 'httpd.conf')
        self.image_files_path = os.path.join(testdata_path, 'test_imagery')
#        self.daily_png_config = os.path.join(testdata_path, 'layer_configs/test_mod_mrf_daily_png.config')
        self.test_apache_config = os.path.join(testdata_path, 'mrf_test.conf')
        dateservice_path = os.path.join(testdata_path, 'date_service')
        date_config = os.path.join(dateservice_path, 'oe2_test_date_service.conf')
        
        # Override default dir for httpd (httpd.conf)
        file_text_replace(httpd_config, os.path.join('/etc/httpd/conf', os.path.basename(httpd_config)), '{nonexistant_path}', testdata_path)

        # Set up date_service config
        file_text_replace(date_config, os.path.join('/etc/httpd/conf.d', os.path.basename(date_config)), '{nonexistant_path}', dateservice_path)

        # Set up the Apache config (mrf_test.conf)
        file_text_replace(self.test_apache_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_config)),
                          '{nonexistant_path}', testdata_path)
        restart_apache()

        # Set up the redis config
        restart_redis()

        run_command('redis-cli -n 0 DEL layer:test_daily_png')
        run_command('redis-cli -n 0 SET layer:test_daily_png:default "2012-02-29"')
        run_command('redis-cli -n 0 SADD layer:test_daily_png:periods "2012-02-29/2012-02-29/P1D"')
        run_command('redis-cli -n 0 DEL layer:test_legacy_subdaily_jpg')
        run_command('redis-cli -n 0 SET layer:test_legacy_subdaily_jpg:default "2012-02-29T14:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:test_legacy_subdaily_jpg:periods "2012-02-29T12:00:00Z/2012-02-29T14:00:00Z/PT2H"')
        run_command('redis-cli -n 0 DEL layer:test_nonyear_jpg')
        run_command('redis-cli -n 0 SET layer:test_nonyear_jpg:default "2012-02-29"')
        run_command('redis-cli -n 0 SADD layer:test_nonyear_jpg:periods "2012-02-29/2012-02-29/P1D"')
        run_command('redis-cli -n 0 DEL layer:test_weekly_jpg')
        run_command('redis-cli -n 0 SET layer:test_weekly_jpg:default "2012-02-29"')
        run_command('redis-cli -n 0 SADD layer:test_weekly_jpg:periods "2012-02-22/2012-02-29/P7D"')
        run_command('redis-cli -n 0 DEL layer:snap_test_1a')
        run_command('redis-cli -n 0 SET layer:snap_test_1a:default "2016-02-29"')
        run_command('redis-cli -n 0 SADD layer:snap_test_1a:periods "2015-01-01/2016-12-31/P1D"')

        run_command('redis-cli -n 0 DEL layer:snap_test_2a')
        run_command('redis-cli -n 0 SET layer:snap_test_2a:default "2015-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_2a:periods "2015-01-01/2015-01-10/P1D"')
        run_command('redis-cli -n 0 SADD layer:snap_test_2a:periods "2015-01-12/2015-01-31/P1D"')

        run_command('redis-cli -n 0 DEL layer:snap_test_3a')
        run_command('redis-cli -n 0 SET layer:snap_test_3a:default "2015-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_3a:periods "2015-01-01/2016-01-01/P1M"')
        run_command('redis-cli -n 0 SADD layer:snap_test_3a:periods "1948-01-01/1948-03-01/P1M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_3b')
        run_command('redis-cli -n 0 SET layer:snap_test_3b:default "2015-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_3b:periods "2015-01-01/2016-01-01/P3M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_3c')
        run_command('redis-cli -n 0 SET layer:snap_test_3c:default "2000-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_3c:periods "1990-01-01/2016-01-01/P1Y"')

        run_command('redis-cli -n 0 DEL layer:snap_test_3d')
        run_command('redis-cli -n 0 SET layer:snap_test_3d:default "2010-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_3d:periods "2010-01-01/2012-03-11/P8D"')

        run_command('redis-cli -n 0 DEL layer:snap_test_4a')
        run_command('redis-cli -n 0 SET layer:snap_test_4a:default "2000-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4a:periods "2000-01-01/2000-06-01/P1M"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4a:periods "2000-07-03/2000-07-03/P1M"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4a:periods "2000-08-01/2000-12-01/P1M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_4b')
        run_command('redis-cli -n 0 SET layer:snap_test_4b:default "2001-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4b:periods "2001-01-01/2001-12-27/P8D"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4b:periods "2002-01-01/2002-12-27/P8D"')

        run_command('redis-cli -n 0 DEL layer:snap_test_4c')
        run_command('redis-cli -n 0 SET layer:snap_test_4c:default "2010-01-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_4c:periods "2010-01-01/2010-01-01/P385D"')

        run_command('redis-cli -n 0 DEL layer:snap_test_5a')
        run_command('redis-cli -n 0 SET layer:snap_test_5a:default "2011-12-01"')
        run_command('redis-cli -n 0 SADD layer:snap_test_5a:periods "2002-12-01/2011-12-01/P1Y"')

        run_command('redis-cli -n 0 DEL layer:snap_test_year_boundary')
        run_command('redis-cli -n 0 SET layer:snap_test_year_boundary:default "2000-09-03"')
        run_command('redis-cli -n 0 SADD layer:snap_test_year_boundary:periods "2000-09-03/2000-09-03/P144D"')

        run_command('redis-cli -n 0 SAVE')

        # Set some handy constant values
        self.tile_hashes = {'aeec77fbba62d53d539da0851e4b9324': '1948-03-01',
                            '40d78f32acdfd866a8b0faad24fda69b': '1990-01-01',
                            'd5ae95bd567813c3e431b55de12f5d3e': '2000-01-01',
                            '57ef9f162328774860ef0e8506a77ebe': '2000-06-01',
                            '7ea2038a74af2988dc432a614ec94187': '2000-07-03',
                            '03b3cc7adc929dd605d617b7066b30ae': '2000-08-01',
                            '32d82aa3c58c3b1053edd7d63a98864e': '2000-09-03',
                            'fd9e3aa7c12fbf823bd339b92920784e': '2000-12-01',
                            '0c8db77de136a725e6bf4c83555d30cc': '2001-01-01',
                            '1b1b7fb57258d76fa4304172d3d21d0b': '2001-05-09',
                            'e96f02519c5eeb7f9caf5486385152e4': '2002-01-01',
                            'b64066bafe897f0d2c0fc4a41ae7e052': '2002-12-27',
                            '1a4769087f67f1b6cc8d6e43f5595929': '2002-12-01',
                            '938998efa5cf312a7dcf0744c6402413': '2003-12-01',
                            'af5d2e1dfe64ebb6fc3d3414ea7b5318': '2004-12-01',
                            'baf3bb568373cb41e88674073b841f18': '2005-01-01',
                            'c5050539a8c295a1359f43c5cad0844d': '2005-12-01',
                            '28192f1788af1c9a0844f48ace629344': '2006-12-01',
                            'b8bd38e7b971166cb6014b72bcf7b03f': '2007-12-01',
                            '6bb1a6e9d56ef5aec03a377d923512d9': '2008-01-01',
                            '71835e22811ffb94a48d47e9f164e337': '2008-12-01',
                            '40edd34da910b317870005e1fcf2ab59': '2009-12-01',
                            '84777459ff0e823c01fb534c5a3c1648': '2010-01-01',
                            '66efbcc6df6d087df89dfebff1bfafe2': '2010-01-09',
                            'a47002642da81c038bfb37e7de1dc561': '2010-12-01',
                            'a363f215b5f33e5e2990298c329ab8b3': '2011-12-01',
                            'bbfaad71b35dc42b7ea462de75b7308e': '2012-03-11',
                            '170b8cce84c29664e62f732f00942619': '2015-01-01',
                            'aad46b0afac105b93b00fc95c95c7c30': '2015-01-02',
                            '51f485fa236d8b26a1d7c81a9ffc9d4f': '2015-10-01',
                            '91f3e175621955796245d2d0a6589aad': '2016-02-29',
                            '1571c4d601dfd871e7680e279e6fd39c': '2015-01-12',
                            'b69307895d6cb654b98d247d710dd806': '2015-12-01',
                            '8f6b00c6a817ca6907882d26c50b8dec': '2016-01-01',
                            '5e11f1220da2bb6f92d3e1c998f20bcf': 'black'}

        # URL that will be used to create the snap test requests
        self.snap_test_url_template = 'http://localhost/mrf_endpoint/wmts.cgi?layer={0}&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME={1}'

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_wmts_no_time_jpg(self):
        """
        1. Request current (no time) JPG tile via WMTS

        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'

        # The URL of the tile to be requested
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'

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
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'

        # The URL of the tile to be requested
        # {wmtsBaseUrl}/{layer}/{style}/{dimension1}/.../{dimensionN}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}{formatExtension}
        req_url = 'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/0.jpeg'

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
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
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
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/test_daily_png/default/default/EPSG4326_16km/0/0/0.png'
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
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0'
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
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/test_daily_png/default/default/EPSG4326_16km/0/0/0.png'
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
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'
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
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        # https://gibs/earrthdata.nasa.gov/wmts/epsg{EPSG:Code}/best/{ProductName}/default/{time}/{TileMatrixSet}/{ZoomLevel}/{TileRow}/{TileColumn}.png
        req_url = 'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/0.jpeg'
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
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        if DEBUG:
            print '\nTesting: Request current (time=default) PNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_default_time_png(self):
        """
        5B. Request current (time=default) PNG tile via WMTS REST
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/test_daily_png/default/default/EPSG4326_16km/0/0/0.png'
        if DEBUG:
            print '\nTesting: Request current (time=default) PNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS REST PNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_default_time_ppng(self):
        """
        6. Request current (time=default) PPNG tile via WMTS
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_daily_png&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fpng&TileMatrix=0&TileCol=0&TileRow=0&TIME=default'
        if DEBUG:
            print '\nTesting: Request current (time=default) PPNG tile via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_default_time_ppng(self):
        """
        6B. Request current (time=default) PPNG tile via WMTS REST
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/mrf_endpoint/test_daily_png/default/default/EPSG4326_16km/0/0/0.png'
        if DEBUG:
            print '\nTesting: Request current (time=default) PPNG tile via WMTS REST'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (TIME=default) WMTS REST PPNG Tile Request does not match what\'s expected. URL: ' + req_url)

    # REQUEST WITH DATE/TIME AND STATIC TESTS

    def test_request_wmts_date_from_year_layer(self):
        """
        10. Request tile with date from "year" layer via WMTS
        """
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-22'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_date_from_year_layer(self):
        """
        10B. Request tile with date from "year" layer via WMTS (REST)
        """
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        req_url = 'http://localhost/mrf_endpoint/test_weekly_jpg/default/2012-02-22/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_date_from_noyear_layer(self):
        """
        11. Request tile with date  from "non-year" layer via WMTS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date  from "non-year layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_date_from_noyear_layer(self):
        """
        11B. Request tile with date  from "non-year" layer via WMTS (REST)
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/test_nonyear_jpg/default/2012-02-29/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date  from "non-year layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_legacy_datetime_from_year_layer(self):
        """
        12. Request tile with date and time (sub-daily) from "year" layer via WMTS
        """
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_legacy_datetime_from_year_layer(self):
        """
        12B. Request tile with date and time (sub-daily) from "year" layer via WMTS (REST)
        """
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        req_url = 'http://localhost/mrf_endpoint/test_legacy_subdaily_jpg/default/2012-02-29T12:00:00Z/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_nodate_from_year_layer(self):
        """
        14. Request tile with no date from "year" layer via WMTS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_nodate_from_year_layer(self):
        """
        14B. Request tile with no date from "year" layer via WMTS (REST)
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_nodate_from_noyear_layer(self):
        """
        15. Request tile with no date from "non-year" layer via WMTS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_nonyear_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile with no date from "non-year layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_nodate_from_noyear_layer(self):
        """
        15B. Request tile with no date from "non-year" layer via WMTS (REST)
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/test_nonyear_jpg/default/default/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with no date from "non-year layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_legacy_nodate_from_year_layer(self):
        """
        16. Request tile with no date and time (sub-daily) from "year" layer via WMTS
        """
        ref_hash = '3affdef85d2c83cbbb9d010296f1b5f2' 
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_legacy_subdaily_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile with no date and time (legacy sub-daily) from "year" layer via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_legacy_nodate_from_year_layer(self):
        """
        16B. Request tile with no date and time (sub-daily) from "year" layer via WMTS (REST)
        """
        ref_hash = '3affdef85d2c83cbbb9d010296f1b5f2' 
        req_url = 'http://localhost/mrf_endpoint/test_legacy_subdaily_jpg/default/default/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile with no date and time (legacy sub-daily) from "year" layer via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_static_notime(self):
        """
        18. Request tile from static layer with no time via WMTS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_static_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via WMTS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_wmts_rest_static_notime(self):
        """
        18B. Request tile from static layer with no time via WMTS (REST)
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/test_static_jpg/default/EPSG4326_16km/0/0/0.jpeg'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via WMTS (REST)'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'WMTS (REST) static notime request does not match what\'s expected. URL: ' + req_url)

    # GETCAPABILITIES AND GETTILESERVICE REQUEST TESTS

    def test_wmts_get_capabilities(self):
        """
        23. Request WMTS GetCapabilities
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting WMTS GetCapablities'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'GetCapabilities response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/GetCapabilities.1.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WTMTS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_rest_get_capabilities(self):
        """
        24. Request WMTS (REST) GetCapabilities
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/mrf_endpoint/1.0.0/WMTSCapabilities.xml'
        if DEBUG:
            print '\nTesting WMTS (REST) GetCapablities'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'GetCapabilities response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/mrf_endpoint/1.0.0/WMTSCapabilities.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WTMTS (REST) Get Capabilities Request does not match what\'s expected. URL: ' + req_url)

    # REQUEST SYNTAX TESTS (capitalization, parameter ordering, error handling, REST)

    def test_url_parameter_case_insensitivity(self):
        """
        27. URL Parameter Case Insensitivity
        """
        # Randomly capitalizes and lower-cases parameters and checks the tile resulting from the request. Tries 10 different combinations.
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
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
            req_url = 'http://localhost/mrf_endpoint/wmts.cgi?' + '&'.join(test_params)
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_url_parameter_reordering(self):
        """
        28. URL Parameter Reordering
        """
        # Test 20 random permutations of the given param strings
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        params = ['layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'request=GetTile', 'version=1.0.0',
                  'time=default', 'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0']
        if DEBUG:
            print 'Testing URL Parameter Reordering'
        for _ in range(20):
            random.shuffle(params)
            param_string = '&'.join(params)
            req_url = 'http://localhost/mrf_endpoint/wmts.cgi?' + param_string
            if DEBUG:
                print 'Trying URL: ' + req_url
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'URL parameter case insensitivity request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_error_handling(self):
        """
        29. WMTS Error handling
        """
        # MissingParameterValue test
        params = ('layer=test_weekly_jpg', 'TileMatrix=0', 'Service=WMTS', 'version=1.0.0',
                  'TileMatrixSet=EPSG4326_16km', 'format=image%2Fjpeg', 'tilecol=0', 'tilerow=0')
        if DEBUG:
            print '\nTesting WMTS Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/mrf_endpoint/wmts.cgi?request=GetTile&time=default&' + '&'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'

            if DEBUG:
                print '\nTesting Missing Parameters'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find(response_value)
            error = 'The WMTS response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad SERVICE value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Service=bad_value',
            # Bad VERSION value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&Version=bad_value',
            # Bad LAYER value
            'http://localhost/mrf_endpoint/wmts.cgi?tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&layer=bad_layer_value',
            # Bad STYLE value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&style=bad_value',
            # Bad FORMAT value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&TileMatrix=0&TileCol=0&TileRow=0&time=default&Format=fake_image',
            # Bad TILEMATRIXSET value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default&tilematrixset=fake_tilematrixset',
            # Bad (non-positive integer) TILEMATRIX value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=-20',
            # Bad (non-positive integer) TILEROW value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&time=default&TileRow=-20',
            # Bad (non-positive integer) TILECOL value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileRow=0&time=default&TileCol=-20',
            # Invalid TILEMATRIX value
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileCol=0&TileRow=0&time=default&TileMatrix=20',
            # Invalid TIME format
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-290'
        )
        for req_url in invalid_parameter_urls:
            if DEBUG:
                print '\nTesting Invalid Parameters'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find(response_value)
            error = 'The WMTS response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

        # OperationNotSupported tests
        response_code = 501
        response_value = 'OperationNotSupported'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetLegendGraphic&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=default'

        if DEBUG:
            print '\nTesting Operation Not Supported'
            print req_url

        try:
            response = urllib2.urlopen(req_url)
        except urllib2.HTTPError as e:
            response = e

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'WMTS response is not a valid XML file. URL: ' + req_url)

        try:
            exception = XMLroot.find('exceptionCode').text
        except AttributeError:
            exception = ''
        check_str = exception.find(response_value)
        error = 'The WMTS response does not match what\'s expected. URL: {0}'.format(req_url)
        self.assertTrue(check_str, error)

        # TileOutOfRange tests
        response_code = 400
        response_value = 'TileOutOfRange'
        tile_outofrange_urls = (
            # TileCol out of range
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=50&TileRow=0&time=default',
            # TileRow out of range
            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=50&time=default'
        )
        for req_url in tile_outofrange_urls:
            if DEBUG:
                print '\nTesting Tile Out Of Range'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find(response_value)
            error = 'The WMTS response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

        # Test if empty tile is served for out of time bounds request
# TORHT        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
#        empty_urls = (  # Date before range
#            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-01-01',
            # Date after range
#            'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-03-07'
#        )
#        for url in empty_urls:
#            if DEBUG:
#                print 'Using URL: {0}, expecting empty tile'.format(url)
#            check_result = check_tile_request(url, ref_hash)
#            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/mrf_endpoint/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-29&twoplustwo=five'
        if DEBUG:
            print 'Using URL: {0}, expecting bad parameter will be ignored'
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Bad parameter request is not ignored. URL: ' + req_url)

    def test_wmts_rest_error_handling(self):
        """
        30. WMTS REST requests
        """
        # MissingParameterValue test
        params = ('test_weekly_jpg', 'default/default', 'EPSG4326_16km', '0', '0', '0.jpeg')
        if DEBUG:
            print '\nTesting WMTS REST Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/mrf_endpoint/' + '/'.join(param_list)
            response_code = 400
            response_value = 'MissingParameterValue'

            if DEBUG:
                print '\nTesting WMTS REST Error Missing Parameters'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS REST response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find(response_value)
            error = 'The WMTS REST response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

        # InvalidParameterValue tests
        response_code = 400
        response_value = 'InvalidParameterValue'
        invalid_parameter_urls = (
            # Bad LAYER value
            'http://localhost/mrf_endpoint/bad_layer_value/default/default/EPSG4326_16km/0/0/0.jpeg',
            # Bad STYLE value
            'http://localhost/mrf_endpoint/test_weekly_jpg/bad_value/EPSG4326_16km/0/0/0.jpeg',
            # Bad FORMAT value
# TORHT            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/0.png',
            # Bad TILEMATRIXSET value
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/fake_tilematrixset/0/0/0.jpeg',
            # Bad (non-positive integer) TILEMATRIX value
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/-20/0/0.jpeg',
            # Bad (non-positive integer) TILEROW value
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/-20/0.jpeg',
            # Bad (non-positive integer) TILECOL value
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/-20.jpeg',
            # Invalid TILEMATRIX value
# TORHT            'http://localhost/mrf_endpoint/test_weekly_jpg/default/EPSG4326_16km/20/0/0.jpeg',
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/20/0/0.jpeg',
            # Invalid TIME format
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/2012-02-290/EPSG4326_16km/0/0/0.jpeg'
        )
        for req_url in invalid_parameter_urls:
            #if DEBUG:
                #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(req_url, response_code, response_value)
            if DEBUG:
                print '\nTesting WTMS REST Error Invalid Parameters'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS REST response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find('InvalidParameterValue')
            error = 'The WMTS REST response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

            #check_code = check_response_code(req_url, response_code, response_value)
            #error = 'The WMTS REST response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(req_url, response_code)
            #self.assertTrue(check_code, error)

        # TileOutOfRange tests
        response_code = 400
        response_value = 'TileOutOfRange'
        tile_outofrange_urls = (
            # TileCol out of range
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/50/0.jpeg',
            # TileRow out of range
            'http://localhost/mrf_endpoint/test_weekly_jpg/default/default/EPSG4326_16km/0/0/50.jpeg'
        )
        for req_url in tile_outofrange_urls:
            if DEBUG:
                print '\nTesting WMTS REST Error Tile Out Of Range'
                print req_url

            try:
                response = urllib2.urlopen(req_url)
            except urllib2.HTTPError as e:
                response = e

            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'WMTS REST response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find(response_value)
            error = 'The WMTS REST response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

        # Test if empty tile is served for out of time bounds request
# TORHT        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
#        empty_urls = (  # Date before range
#            'http://localhost/mrf_endpoint/test_weekly_jpg/default/2012-01-01/EPSG4326_16km/0/0/0.jpeg',
            # Date after range
#            'http://localhost/mrf_endpoint/test_weekly_jpg/default/2012-03-07/EPSG4326_16km/0/0/0.jpeg'
#        )
#        for url in empty_urls:
#            if DEBUG:
#                print 'Using URL: {0}, expecting empty tile'.format(url)
#            check_result = check_tile_request(url, ref_hash)
#            self.assertTrue(check_result, 'Request for empty tile outside date range does not match what\'s expected. URL: ' + url)

        # Test if unknown parameter is ignored
# TORHT        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
#        req_url = 'http://localhost/mrf_endpoint/test_weekly_jpg/default/2012-02-29/EPSG4326_16km/0/0/0/five.jpeg'
#        if DEBUG:
#            print 'Using URL: {0}, expecting bad parameter will be ignored'
#        check_result = check_tile_request(req_url, ref_hash)
#        self.assertTrue(check_result, 'Bad parameter request is not ignored. URL: ' + url)

    # DATE/TIME SNAPPING REQUESTS

    def test_snapping_1a(self):
        # This is the layer name that will be used in the WMTS request
        layer_name = 'snap_test_1a'

        # Tests are tuples with order of (request date, expected date)
        # Note that date/hash pairs must exist in self.tile_hashes dict
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-02', '2015-01-02'),
                 ('2016-02-29', '2016-02-29'),
                 ('2017-01-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Daily date (P1D)'
            print 'Time Period 1a: 2015-01-01/2016-12-31/P1D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 1a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_2a(self):
        layer_name = 'snap_test_2a'
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-11', 'black'),
                 ('2015-01-12', '2015-01-12'),
                 ('2015-02-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Irregular Daily date (PID with gaps)'
            print 'Time Period 2a: 2015-01-01/2015-01-10/P1D, 2015-01-12/2015-01-31/P1D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 2a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3a(self):
        layer_name = 'snap_test_3a'
        tests = (('1948-03-01', '1948-03-01'),
                 ('2015-01-01', '2015-01-01'),
                 ('2015-01-20', '2015-01-01'),
                 ('2015-12-31', '2015-12-01'),
                 ('2016-01-01', '2016-01-01'),
                 ('2016-01-20', '2016-01-01'),
                 ('2016-02-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3a: 2015-01-01/2016-01-01/P1M & 1948-01-01/1948-03-01/P1M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3b(self):
        layer_name = 'snap_test_3b'
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-20', '2015-01-01'),
                 ('2015-12-31', '2015-10-01'),
                 ('2016-01-01', '2016-01-01'),
                 ('2016-01-20', '2016-01-01'),
                 ('2016-04-01', 'black'),
                 ('2014-12-31', 'black'))
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3b: 2015-01-01/2016-01-01/P3M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3b requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3c(self):
        layer_name = 'snap_test_3c'
        tests = (('1990-01-01', '1990-01-01'),
                 ('1990-05-20', '1990-01-01'),
                 ('2000-01-01', '2000-01-01'),
                 ('2000-05-20', '2000-01-01'),
                 ('2005-12-31', '2005-01-01'),
                 ('2008-10-01', '2008-01-01'),
                 ('2016-11-20', '2016-01-01'),
                 ('2017-01-01', 'black'),
                 ('1989-12-31', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3c: 1990-01-01/2016-01-01/P1Y'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3c requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_3d(self):
        layer_name = 'snap_test_3d'
        tests = (('2010-01-01', '2010-01-01'),
                 ('2010-01-04', '2010-01-01'),
                 ('2010-01-10', '2010-01-09'),
                 ('2012-03-11', '2012-03-11'),
                 ('2012-03-14', '2012-03-11'),
                 ('2012-03-19', 'black'),
                 ('2009-12-31', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Regular Multi-day date snapping (e.g. consistent 8-day, monthly, yearly cadence)'
            print 'Time Period 3d: 1990-01-01/2016-01-01/P1Y'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 3d requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_4a(self):
        layer_name = 'snap_test_4a'
        tests = (('2000-01-01', '2000-01-01'),
                 ('2000-01-20', '2000-01-01'),
                 ('2000-06-10', '2000-06-01'),
                 ('2000-07-01', 'black'),
                 ('2000-07-02', 'black'),
                 ('2000-07-03', '2000-07-03'),
                 ('2000-07-20', '2000-07-03'),
                 ('2000-08-01', '2000-08-01'),
                 ('2000-08-10', '2000-08-01'),
                 ('2000-12-31', '2000-12-01'),
                 ('1999-12-31', 'black'),
                 ('2001-01-01', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods'
            print 'Time Period 4a: 2000-01-01/2000-06-01/P1M,2000-07-03/2000-07-03/P1M,2000-08-01/2000-12-01/P1M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 4a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_4b(self):
        layer_name = 'snap_test_4b'
        tests = (('2001-01-01', '2001-01-01'),
                 ('2001-01-05', '2001-01-01'),
                 ('2001-05-14', '2001-05-09'),
                 ('2002-01-01', '2002-01-01'),
                 ('2000-12-31', 'black'),
                 ('2003-01-01', '2002-12-27'),
                 ('2003-01-04', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods'
            print 'Time Period 4b: 2001-01-01/2001-12-27/P8D, 2002-01-01/2002-12-27/P8D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 4b requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_4c(self):
        layer_name = 'snap_test_4c'
        tests = (('2010-01-01', '2010-01-01'),
                 ('2010-10-01', '2010-01-01'),
                 ('2011-01-10', '2010-01-01'),
                 ('2011-01-20', '2010-01-01'),
                 ('2009-12-31', 'black'),
                 ('2011-01-21', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Irregular Multi-day date snapping (e.g. irregular periods intermixed with consistent periods'
            print 'Time Period 4c: 2010-01-01/2010-01-01/P385D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test 4c requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_5a(self):
        layer_name = 'snap_test_5a'
        expected_date = datetime.date(2002, 12, 01)
        if DEBUG:
            print '\nTesting snapping test 5a'
        while (expected_date.year < 2012):
            end_date = expected_date.replace(year=expected_date.year + 1) + datetime.timedelta(days=-1)
            req_date = expected_date
            while (req_date < end_date):
                req_url = self.snap_test_url_template.format(layer_name, req_date)
                response_date = test_snap_request(self.tile_hashes, req_url)
                error = 'Snapping test 5a requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(req_date.isoformat(), expected_date.isoformat(), response_date, req_url)
                self.assertEqual(expected_date.isoformat(), response_date, error)
                req_date += datetime.timedelta(days=+1)
            expected_date = expected_date.replace(expected_date.year + 1)

    def test_year_boundary_snapping(self):
        layer_name = 'snap_test_year_boundary'
        tests = (('2000-09-03', '2000-09-03'),
                 ('2001-01-24', '2000-09-03'),
                 ('2000-01-25', 'black'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across a year boundary'
            print 'Time Period year boundary: 2000-09-03/2000-09-03/P144D'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods stretching across a year boundary requested date {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_apache_config)))
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_mrf_results.xml',
                      help='Specify XML output file (default is test_mod_mrf_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModMrf.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
