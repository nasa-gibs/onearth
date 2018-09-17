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
# Tests for mod_twms
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
from oe_test_utils import check_tile_request, restart_apache, restart_redis, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command, get_url, XmlDictConfig, check_dicts, check_valid_mvt, copytree_x

DEBUG = False


class TestModTwms(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        testdata_path = os.path.join(os.getcwd(), 'ci_tests')
        httpd_config = os.path.join(testdata_path, 'httpd.conf')
#        self.image_files_path = os.path.join(testdata_path, 'test_imagery')

        # Make dir for layer config
        layer_config_path = os.path.join(testdata_path, 'layer_config_endpoint')
        copytree_x(os.path.join(testdata_path, 'layer_config_endpoint/baseline'), layer_config_path, exist_ok=True)

        self.test_apache_gc_config = os.path.join(testdata_path, 'layer_config_endpoint/oe2_layer_config_gc.conf')
        self.test_apache_config = os.path.join(testdata_path, 'layer_config_endpoint/oe2_layer_config.conf')
        dateservice_path = os.path.join(testdata_path, 'date_service')
        date_config = os.path.join(dateservice_path, 'oe2_test_date_service.conf')
        
        # Override default dir for httpd (httpd.conf)
        file_text_replace(httpd_config, os.path.join('/etc/httpd/conf', os.path.basename(httpd_config)), '{nonexistant_path}', testdata_path)

        # Set up date_service config
        file_text_replace(date_config, os.path.join('/etc/httpd/conf.d', os.path.basename(date_config)), '{nonexistant_path}', dateservice_path)

        # Set up the Apache GC config (oe2_layer_config_gc.conf)
        file_text_replace(self.test_apache_gc_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_gc_config)), '{nonexistant_path}', testdata_path)

        restart_apache()

        # Set up the Apache config (oe2_layer_config.conf)
        file_text_replace(self.test_apache_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_config)), '{nonexistant_path}', testdata_path)

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

        run_command('redis-cli -n 0 DEL layer:snap_test_6a')
        run_command('redis-cli -n 0 SET layer:snap_test_6a:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_6a:periods "2018-01-01T00:00:00Z/2018-01-01T23:55:00Z/PT5M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_6b')
        run_command('redis-cli -n 0 SET layer:snap_test_6b:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_6b:periods "2018-01-01T00:00:00Z/2018-01-01T23:54:00Z/PT6M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_6c')
        run_command('redis-cli -n 0 SET layer:snap_test_6c:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_6c:periods "2018-01-01T00:00:00Z/2018-01-01T23:59:00Z/PT60S"')

        run_command('redis-cli -n 0 DEL layer:snap_test_7a')
        run_command('redis-cli -n 0 SET layer:snap_test_7a:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_7a:periods "2018-01-01T00:00:00Z/2018-01-01T23:55:00Z/PT5M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_7b')
        run_command('redis-cli -n 0 SET layer:snap_test_7b:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_7b:periods "2018-01-01T00:00:00Z/2018-01-01T23:54:00Z/PT6M"')

        run_command('redis-cli -n 0 DEL layer:snap_test_7c')
        run_command('redis-cli -n 0 SET layer:snap_test_7c:default "2018-01-01T00:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:snap_test_7c:periods "2018-01-01T00:00:00Z/2018-01-01T23:59:00Z/PT60S"')

        run_command('redis-cli -n 0 DEL layer:snap_test_year_boundary')
        run_command('redis-cli -n 0 SET layer:snap_test_year_boundary:default "2000-09-03"')
        run_command('redis-cli -n 0 SADD layer:snap_test_year_boundary:periods "2000-09-03/2000-09-03/P144D"')

        run_command('redis-cli -n 0 SAVE')

        # Set some handy constant values
        self.tile_hashes = {'aeec77fbba62d53d539da0851e4b9324': '1948-03-01',
                            '40d78f32acdfd866a8b0faad24fda69b': '1990-01-01',
                            'd5ae95bd567813c3e431b55de12f5d3e': '2000-01-01',
                            '57ef9f162328774860ef0e8506a77ebe': '2000-06-01',
#                            '7ea2038a74af2988dc432a614ec94187': '2000-07-03',
                            'ea907f96808a168f0ca901f7e30cebc8': '2000-07-03',
                            '03b3cc7adc929dd605d617b7066b30ae': '2000-08-01',
                            '32d82aa3c58c3b1053edd7d63a98864e': '2000-09-03',
                            'fd9e3aa7c12fbf823bd339b92920784e': '2000-12-01',
                            '0c8db77de136a725e6bf4c83555d30cc': '2001-01-01',
                            '1b1b7fb57258d76fa4304172d3d21d0b': '2001-05-09',
                            'e96f02519c5eeb7f9caf5486385152e4': '2002-01-01',
                            '1a4769087f67f1b6cc8d6e43f5595929': '2002-12-01',
#                            'b64066bafe897f0d2c0fc4a41ae7e052': '2002-12-27',
                            'a512a061f962db7713cf3f99ef9b109a': '2002-12-27',
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
#                            '1571c4d601dfd871e7680e279e6fd39c': '2015-01-12',
                            '7105441f73978c183ea91edcc33d272f': '2015-01-12',
#                            'b69307895d6cb654b98d247d710dd806': '2015-12-01',
                            '2e8ec04783a71a89d4743c3aba57f22a': '2015-12-01',
#                            'ba366ccd45a8f1ae0ed2b65cf67b9787': '2016-01-01',
                            '8f6b00c6a817ca6907882d26c50b8dec': '2016-01-01',
                            '711ee4e1cbce8fa1af6f000dd9c5bcb6': '2018-01-01T00:00:00Z',
                            '4788acd411a5f0585a1d6bcdf2097e3e': '2018-01-01T00:01:00Z',
                            '625d2e1195c81c817641f703e6b23aec': '2018-01-01T10:00:00Z',
                            '4b7af84208c30f72dc1c639665343b9c': '2018-01-01T12:00:00Z',
                            '7858d61007e2040bd38a1f084e4ee73b': '2018-01-01T23:54:00Z',
                            '1d79dd99d0fe4fbd1d6f9f257cb7a49a': '2018-01-01T23:55:00Z',
                            'ea8a5b5a6d3a4dbee54bef2c82b874b9': '2018-01-01T23:59:00Z',
                            '75ee644a39f5da877d9268ca8b8397e4': '2018-01-01T00:00:00Z',
                            '555828c04f7c9db23bf6c6ca840daa0a': '2018-01-01T00:01:00Z',
                            '9fd6a8363ef01482c1f4351df5bf9e9f': '2018-01-01T10:00:00Z',
                            '17e56046b556ca780712fb62450f46b8': '2018-01-01T12:00:00Z',
                            'c603aff8a4493a2f9a510e1425cca13a': '2018-01-01T23:54:00Z',
                            '8e6e3a157075bb1bc8d6b25e652ecd52': '2018-01-01T23:55:00Z',
                            'fef9f04989867fff9dff6af7115ab4b6': '2018-01-01T23:59:00Z',
                            '5e11f1220da2bb6f92d3e1c998f20bcf': 'black',
                            'fb28bfeba6bbadac0b5bef96eca4ad12': 'black2',
                            '98ff3915cfdc2215ce262c3ed49805a6': 'black3'}

        # URL that will be used to create the snap test requests
        self.snap_test_url_template = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers={0}&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&TIME={1}'

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_twms_notime_jpg(self):
        """
        1. Request current (no time) JPEG tile via TWMS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current JPG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_png(self):
        """
        2. Request current (no time) PNG tile via TWMS
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:4326&format=image%2Fpng&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request current (no TIME) PNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PNG request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_notime_ppng(self):
        """
        3. Request current (no time) PPNG tile via TWMS
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:4326&format=image%2Fpng&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request current (no TIME) PPNG tile via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS current PPNG request does not match what\'s expected. URL: ' + req_url)

    # REQUEST WITH DATE/TIME AND STATIC TESTS

    def test_request_twms_date_from_year_layer(self):
        """
       4. Request tile with date from "year" layer via TWMS
        """
        ref_hash = '9b38d90baeeebbcadbc8560a29481a5e'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&TIME=2012-02-22'
        if DEBUG:
            print '\nTesting: Request tile with date from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_from_noyear_layer(self):
        """
        5. Request tile with date from "non-year" layer via TWMS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_nonyear_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date from "non-year layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_legacy_datetime_from_year_layer(self):
        """
        6. Request tile with date and time (sub-daily) from "year" layer via TWMS
        """
        ref_hash = '5a39c4e335d05295160a7bec4961002d'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_legacy_subdaily_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&TIME=2012-02-29T12:00:00Z'
        if DEBUG:
            print '\nTesting: Request tile with date and time (legacy sub-daily) from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS legacy subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_nodate_from_year_layer(self):
        """
        7. Request tile with no date from "year" layer via TWMS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request tile with no date from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS no date request from "year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_nodate_from_noyear_layer(self):
        """
        8. Request tile with no date from "non-year" layer via TWMS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_nonyear_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request tile with no date from "non-year layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS no date request from "non-year" layer does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_legacy_nodate_from_year_layer(self):
        """
        9. Request tile with no date and time (sub-daily) from "year" layer via TWMS
        """
        ref_hash = '3affdef85d2c83cbbb9d010296f1b5f2'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_legacy_subdaily_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request tile with no date and time (legacy sub-daily) from "year" layer via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS legacy no date and time subdaily request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_static_notime(self):
        """
        10. Request tile from static layer with no time via TWMS
        """
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_static_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print '\nTesting: Request tile from static layer with no time via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS static notime request does not match what\'s expected. URL: ' + req_url)

    def test_request_twms_date_png(self):
        """
        11. Request tile with date via TWMS
        """
        ref_hash = '944c7ce9355cb0aa29930dc16ab03db6'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_daily_png&srs=EPSG:4326&format=image%2Fpng&styles=&width=512&height=512&bbox=-180,-198,108,90&TIME=2012-02-29'
        if DEBUG:
            print '\nTesting: Request tile with date via TWMS'
            print 'URL: ' + req_url
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'TWMS PNG request with date does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_capabilities(self):
        """
        12. Request TWMS GetCapabilities
        """
        ref_hash = 'd2536cb2c0681c56b005eb9d60336326'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?Request=GetCapabilities'
        if DEBUG:
            print '\nTesting TWMS GetCapablities'
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

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), '/GetCapabilities_TWMS.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'TWMS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_twms_get_tile_service(self):
        """
        13. Request TWMS GetTileService
        """
        ref_hash = '7555d5ad3cca96aa8cbc8a36f5e04f19'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?Request=GetTileService'
        if DEBUG:
            print '\nTesting TWMS GetTileService'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML                                                        
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'GetTileService response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), '/GetTileService.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'TWMS Get GetTileService Request does not match what\'s expected. URL: ' + req_url)

    # REQUEST SYNTAX TESTS (capitalization, parameter ordering, error handling, REST)

    def test_twms_error_handling(self):
        """
        14. TWMS requests
        """
        # MissingParameterValue test
        params = ('layers=test_weekly_jpg', 'srs=EPSG:4326', 'width=512', 'height=512', 'bbox=-180,-198,108,90')
        if DEBUG:
            print '\nTesting TWMS Error Handling'
        for i in range(len(params)):
            param_list = list(params)
            param_list.pop(i)
            req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&time=default&format=image%2Fjpeg&styles=&' + '&'.join(param_list)

            # check for empty tile
            ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
            if DEBUG:
                print 'Using URL: {0}, expecting empty tile'.format(req_url)
            if 'bbox' in req_url:
                check_result = check_tile_request(req_url, ref_hash)
            else:
                # Validate XML for Missing BBOX
                response = get_url(req_url)

                # Check if the response is valid XML
                try:
                    XMLroot = ElementTree.XML(response.read())
                    XMLdict = XmlDictConfig(XMLroot)
                    xml_check = True
                except:
                    xml_check = False
                    self.assertTrue(xml_check, 'Missing BBOX response is not a valid XML file. URL: ' + req_url)

                refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), '/MissingBBOX.xml'))
                refXMLroot = refXMLtree.getroot()
                refXMLdict = XmlDictConfig(refXMLroot)

                check_result = check_dicts(XMLdict, refXMLdict)
            self.assertTrue(check_result, 'The TWMS response for Missing Parameter does not match what\'s expected. URL: ' + req_url)

        # InvalidParameterValue tests
        invalid_parameter_urls = (
            # Bad LAYER value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=bad_layer_value&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90',
            # Bad STYLE value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=bad_value&width=512&height=512&bbox=-180,-198,108,90',
            # Bad SRS value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=fake_tilematrixset&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90',
            # Bad (non-positive integer) WIDTH value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=-512&height=512&bbox=-180,-198,108,90',
            # Bad (non-positive integer) HEIGHT value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=-512&bbox=-180,-198,108,90',
            # Bad (large integer) BBOX value
            'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,1080,900'
        )
        for req_url in invalid_parameter_urls:
            # check for empty tile
            ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
            if DEBUG:
                print 'Using URL: {0}, expecting empty tile'.format(req_url)
            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(check_result, 'The TWMS response for Invalid Parameter does not match what\'s expected. URL: ' + req_url)

        # Test Invalid time format for Bad Time
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time=2012-02-290'
        if DEBUG:
            print 'Using URL: {0}, expecting XML error message'.format(req_url)
            response = get_url(req_url)
            # Check if the response is valid XML                                                    
            try:
                XMLroot = ElementTree.XML(response.read())
                XMLdict = XmlDictConfig(XMLroot)
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'Invalid TIME response is not a valid XML file. URL: ' + req_url)

        # Test if PNG empty tile is served for Missing FORMAT Value
        ref_hash = '8dd7e330d7ab0ead5ee71e7179c170d1'
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print 'Using URL: {0}, expecting empty transparent tile'.format(req_url)
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'The TWMS response for Missing FORMAT does not match what\'s expected. URL: ' + req_url)

        # Test format is Invalid for Bad FORMAT Value
        req_url = 'http://localhost/layer_config_endpoint/twms.cgi?request=GetMap&layers=test_weekly_jpg&srs=EPSG:4326&format=image%2Fblah&styles=&width=512&height=512&bbox=-180,-198,108,90'
        if DEBUG:
            print 'Using URL: {0}, expecting XML error message'.format(req_url)
            response = get_url(req_url)
            # Check if the response is valid XML
            try:
                XMLroot = ElementTree.XML(response.read())
                XMLdict = XmlDictConfig(XMLroot)
                xml_check = True
            except:
                xml_check = False
            self.assertTrue(xml_check, 'Invalid FORMAT response is not a valid XML file. URL: ' + req_url)

            try:
                exception = XMLroot.find('exceptionCode').text
            except AttributeError:
                exception = ''
            check_str = exception.find('InvalidParameterValue')
            error = 'The Invalid Format response does not match what\'s expected. URL: {0}'.format(req_url)
            self.assertTrue(check_str, error)

    # DATE/TIME SNAPPING REQUESTS

    def test_snapping_1a(self):
        # This is the layer name that will be used in the WMTS request
        layer_name = 'snap_test_1a'

        # Tests are tuples with order of (request date, expected date)
        # Note that date/hash pairs must exist in self.tile_hashes dict
        tests = (('2015-01-01', '2015-01-01'),
                 ('2015-01-02', '2015-01-02'),
                 ('2016-02-29', '2016-02-29'))
# Commented out until GITC-795 is implemented
#                 ('2016-02-29', '2016-02-29'),
#                 ('2017-01-01', 'black'),
#                 ('2014-12-31', 'black'))
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
# Commented out until GITC-795 is implemented
#                 ('2015-01-11', 'black'),
                 ('2015-01-12', '2015-01-12'))
# Commented out until GITC-795 is implemented
#                 ('2015-01-12', '2015-01-12'),
#                 ('2015-02-01', 'black'),
#                 ('2014-12-31', 'black'))
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
                 ('2016-01-20', '2016-01-01'))
# Commented out until GITC-795 is implemented
#                 ('2016-01-20', '2016-01-01'),
#                 ('2016-02-01', 'black'),
#                 ('2014-12-31', 'black'))
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
                 ('2016-01-20', '2016-01-01'))
# Commented out until GITC-795 is implemented
#                 ('2016-01-20', '2016-01-01'),
#                 ('2016-04-01', 'black'),
#                 ('2014-12-31', 'black'))
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
                 ('2016-11-20', '2016-01-01'))
# Commented out until GITC-795 is implemented
#                 ('2016-11-20', '2016-01-01'),
#                 ('2017-01-01', 'black'),
#                 ('1989-12-31', 'black'))
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
                 ('2012-03-14', '2012-03-11'))
# Commented out until GITC-795 is implemented
#                 ('2012-03-14', '2012-03-11'),
#                 ('2012-03-19', 'black'),
#                 ('2009-12-31', 'black'))
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
# Commented out until GITC-795 is implemented
#                 ('2000-07-01', 'black'),
#                 ('2000-07-02', 'black'),
                 ('2000-07-03', '2000-07-03'),
                 ('2000-07-20', '2000-07-03'),
                 ('2000-08-01', '2000-08-01'),
                 ('2000-08-10', '2000-08-01'),
                 ('2000-12-31', '2000-12-01'))
# Commented out until GITC-795 is implemented
#                 ('2000-12-31', '2000-12-01'),
#                 ('1999-12-31', 'black'),
#                 ('2001-01-01', 'black'))
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
# Commented out until GITC-795 is implemented
#                 ('2000-12-31', 'black'),
                 ('2003-01-01', '2002-12-27'))
# Commented out until GITC-795 is implemented
#                 ('2003-01-01', '2002-12-27'),
#                 ('2003-01-04', 'black'))
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
                 ('2011-01-20', '2010-01-01'))
# Commented out until GITC-795 is implemented
#                 ('2011-01-20', '2010-01-01'),
#                 ('2009-12-31', 'black'),
#                 ('2011-01-21', 'black'))
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

    def test_snapping_6a(self):
        layer_name = 'snap_test_6a'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T10:00:00Z', '2018-01-01T10:00:00Z'),
                 ('2018-01-01T23:55:00Z', '2018-01-01T23:55:00Z'),
                 ('2018-01-01T00:01:00Z', '2018-01-01T00:00:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T00:01:00Z', '2018-01-01T00:00:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black2'),
#                 ('2018-01-02T00:00:00Z', 'black2'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day'
            print 'Time Period: 2018-01-01T00:00:00Z/2018-01-01T23:55:00Z/PT5M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_6b(self):
        layer_name = 'snap_test_6b'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T12:00:00Z', '2018-01-01T12:00:00Z'),
                 ('2018-01-01T23:54:00Z', '2018-01-01T23:54:00Z'),
                 ('2018-01-01T00:01:00Z', '2018-01-01T00:00:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T00:01:00Z', '2018-01-01T00:00:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black2'),
#                 ('2018-01-02T00:00:00Z', 'black2'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day'
            print 'Time Period: 2018-01-01T00:00:00/2018-01-01T23:54:00/PT6M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_6c(self):
        layer_name = 'snap_test_6c'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T10:00:00Z', '2018-01-01T10:00:00Z'),
                 ('2018-01-01T23:59:00Z', '2018-01-01T23:59:00Z'),
                 ('2018-01-01T00:01:01Z', '2018-01-01T00:01:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T00:01:01Z', '2018-01-01T00:01:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black2'),
#                 ('2018-01-02T00:00:00Z', 'black2'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day'
            print 'Time Period: 2018-01-01T00:00:00/2018-01-01T23:59:00/PT60S'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_7a(self):
        layer_name = 'snap_test_7a'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T10:00:00Z', '2018-01-01T10:00:00Z'),
                 ('2018-01-01T23:55:00Z', '2018-01-01T23:55:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T23:55:00Z', '2018-01-01T23:55:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black3'),
#                 ('2018-01-02T00:00:00Z', 'black3'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day (z-level)'
            print 'Time Period: 2018-01-01T00:00:00Z/2018-01-01T23:55:00Z/PT5M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_7b(self):
        layer_name = 'snap_test_7b'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T12:00:00Z', '2018-01-01T12:00:00Z'),
                 ('2018-01-01T23:54:00Z', '2018-01-01T23:54:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T23:54:00Z', '2018-01-01T23:54:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black3'),
#                 ('2018-01-02T00:00:00Z', 'black3'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day (z-level)'
            print 'Time Period: 2018-01-01T00:00:00Z/2018-01-01T23:54:00Z/PT6M'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_snapping_7c(self):
        layer_name = 'snap_test_7c'
        tests = (('2018-01-01T00:00:00Z', '2018-01-01T00:00:00Z'),
                 ('2018-01-01T10:00:00Z', '2018-01-01T10:00:00Z'),
                 ('2018-01-01T23:59:00Z', '2018-01-01T23:59:00Z'),
                 ('2018-01-01T00:01:00Z', '2018-01-01T00:01:00Z'))
# Commented out until GITC-795 is implemented
#                 ('2018-01-01T00:01:00Z', '2018-01-01T00:01:00Z'),
#                 ('2017-01-01T00:00:00Z', 'black3'),
#                 ('2018-01-02T00:00:00Z', 'black3'))
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
        if DEBUG:
            print '\nTesting Date Snapping: Periods stretching across one day (z-level)'
            print 'Time Period: 2018-01-01T00:00:00Z/2018-01-01T23:59:00Z/PT60S'
        for request_date, expected_date in tests:
            req_url = self.snap_test_url_template.format(layer_name, request_date)
            if DEBUG:
                print 'Requesting {0}, expecting {1}'.format(request_date, expected_date)
                print 'URL: ' + req_url
            response_date = test_snap_request(self.tile_hashes, req_url)
            error = 'Snapping test for periods during a day {0}, expected {1}, but got {2}. \nURL: {3}'.format(request_date, expected_date, response_date, req_url)
            self.assertEqual(expected_date, response_date, error)

    def test_year_boundary_snapping(self):
        layer_name = 'snap_test_year_boundary'
        tests = (('2000-09-03', '2000-09-03'),
                 ('2001-01-24', '2000-09-03'))
# Commented out until GITC-795 is implemented
#                 ('2001-01-24', '2000-09-03'),
#                 ('2000-01-25', 'black'))
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
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_apache_gc_config)))
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
        TestModTwms.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
