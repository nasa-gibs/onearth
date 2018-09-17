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
# Tests for layer config
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
import filecmp
import apacheconfig

DEBUG = False


class TestLayerConfig(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        self.testdata_path = os.path.join(os.getcwd(), 'ci_tests')
        httpd_config = os.path.join(self.testdata_path, 'httpd.conf')
        dateservice_path = os.path.join(self.testdata_path, 'date_service')
        date_config = os.path.join(dateservice_path, 'oe2_test_date_service.conf')

        # Override default dir for httpd (httpd.conf)
        file_text_replace(httpd_config, os.path.join('/etc/httpd/conf', os.path.basename(httpd_config)), '{nonexistant_path}', self.testdata_path)

        # Set up date_service config
        file_text_replace(date_config, os.path.join('/etc/httpd/conf.d', os.path.basename(date_config)), '{nonexistant_path}', dateservice_path)

        self.staging_area = os.path.join(os.getcwd(), 'layer_config_test_data')
        self.config_endpoint_area = os.path.realpath('/etc/onearth/config/endpoint')
        self.config_layers_area = os.path.realpath('/etc/onearth/config/layers')

        # Make dirs for layer config
        make_dir_tree(self.staging_area)
#        make_dir_tree(self.config_endpoint_area)
#        make_dir_tree(self.config_layers_area)

        copytree_x(os.path.join(self.testdata_path, 'configs/endpoint'), self.config_endpoint_area, exist_ok=True)
        copytree_x(os.path.join(self.testdata_path, 'configs/layers'), self.config_layers_area, exist_ok=True)

        # Create GC Service with lua
        if DEBUG:
            print "Generating GC Service config files: "
        gc_service_lua = os.path.realpath('/home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua')
        layer_gc = os.path.join(self.config_endpoint_area, "layer_config_gc.yaml")
        #run_command('lua ' + self.gc_service_lua + ' ' + self.layer_gc + ' --make_gts', show_output=DEBUG)
        run_command('lua ' + gc_service_lua + ' ' + layer_gc + ' --make_gts')

        # Create reproject GC Service with lua
        if DEBUG:
            print "Generating reproject GC Service config files: "
        #self.gc_service_lua = os.path.realpath('/home/oe2/onearth/src/modules/gc_service/make_gc_endpoint.lua')
        reproject_layer_gc = os.path.join(self.config_endpoint_area, "layer_config_reproject_gc.yaml")
        #run_command('lua ' + self.gc_service_lua + ' ' + self.reproject_layer_gc + ' --make_gts', show_output=DEBUG)
        run_command('lua ' + gc_service_lua + ' ' + reproject_layer_gc + ' --make_gts')

        restart_apache()
        
        # Create layer config files
        if DEBUG:
            print "Generating layer config files: "
        layer = os.path.join(self.config_endpoint_area, "layer_config.yaml")
        #run_command('python3.6 /usr/bin/oe2_wmts_configure.py ' + self.layer, show_output=DEBUG)
        run_command('python3.6 /usr/bin/oe2_wmts_configure.py ' + layer + ' --make_twms') 

        restart_apache()
        
        # Set up the redis config
        restart_redis()

        run_command('redis-cli -n 0 DEL layer:test_daily_png')
        run_command('redis-cli -n 0 SET layer:test_daily_png:default "2012-02-29"')
        run_command('redis-cli -n 0 SADD layer:test_daily_png:periods "2012-02-29/2012-02-29/P1D"')
        run_command('redis-cli -n 0 DEL layer:test_legacy_subdaily_jpg')
        run_command('redis-cli -n 0 SET layer:test_legacy_subdaily_jpg:default "2012-02-29T14:00:00Z"')
        run_command('redis-cli -n 0 SADD layer:test_legacy_subdaily_jpg:periods "2012-02-29T12:00:00Z/2012-02-29T14:00:00Z/PT2H"')
        run_command('redis-cli -n 0 DEL layer:test_versioned_colormaps')
        run_command('redis-cli -n 0 SET layer:test_versioned_colormaps:default "2012-02-29"')
        run_command('redis-cli -n 0 SADD layer:test_versioned_colormaps:periods "2012-02-29/2012-02-29/P1D"')
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

        # Create reproject layer config files
        if DEBUG:
            print "Generating reproject layer config files: "
        reproject_layer = os.path.join(self.config_endpoint_area, "layer_config_reproject.yaml")
        #run_command('python3.6 /usr/bin/oe2_reproject_configure.py ' + self.reproject_layer, show_output=DEBUG)
        run_command('python3.6 /usr/bin/oe2_reproject_configure.py ' + reproject_layer + ' --make_twms') 

        restart_apache()
        
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
        self.snap_test_url_template = 'http://localhost/layer_config_endpoint/wmts.cgi?layer={0}&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&TIME={1}'

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_get_capabilities(self):
        """
        1. Request WMTS GetCapabilities

        All the tile tests follow this template.
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/layer_config_endpoint/wmts.cgi?Request=GetCapabilities'
        #req_url = 'http://localhost/layer_config_endpoint/1.0.0/GetCapabilities.xml'
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

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/layer_config_endpoint/baseline/GetCapabilities.1.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WMTS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

        # Request reproject WMTS GetCapabilitis
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        req_url = 'http://localhost/layer_config_reproject_endpoint/wmts.cgi?Request=GetCapabilities'
        #req_url = 'http://localhost/layer_config_reproject_endpoint/1.0.0/GetCapabilities.xml'
        if DEBUG:
            print '\nTesting Reproject WMTS GetCapablities'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'Reproject GetCapabilities response is not a valid XML file. URL: ' + req_url)

        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/layer_config_reproject_endpoint/baseline/GetCapabilities.1.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'Reproject WMTS Get GetCapabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_wmts_rest_get_capabilities(self):
        """
        2. Request WMTS (REST) GetCapabilities
        """
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        #req_url = 'http://localhost/layer_config_endpoint/1.0.0/WMTSCapabilities.xml'
        req_url = 'http://localhost/layer_config_endpoint/1.0.0/GetCapabilities.xml'
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
#        ElementTree.ElementTree(XMLroot).write("temp1.xml", xml_declaration=True, encoding='utf-8')
        #refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/mrf_endpoint/1.0.0/WMTSCapabilities.xml'))
        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/layer_config_endpoint/baseline/GetCapabilities.1.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

#        ElementTree.ElementTree(refXMLroot).write("temp2.xml", xml_declaration=True, encoding='utf-8')
#        if XMLdict == refXMLdict:
#            print "XML is same"
#        else:
#            print "XML different"
        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'WMTS (REST) Get Capabilities Request does not match what\'s expected. URL: ' + req_url)

        # Request reproject WMTS (REST) GetCapabilities
        ref_hash = 'b49538ed143340f11230eac8b8f9ecca'
        #req_url = 'http://localhost/layer_config_endpoint/1.0.0/WMTSCapabilities.xml'
        req_url = 'http://localhost/layer_config_reproject_endpoint/1.0.0/GetCapabilities.xml'
        if DEBUG:
            print '\nTesting Reproject WMTS (REST) GetCapablities'
            print 'URL: ' + req_url
        response = get_url(req_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            XMLdict = XmlDictConfig(XMLroot)
            xml_check = True
        except:
            xml_check = False
        self.assertTrue(xml_check, 'Reproject GetCapabilities response is not a valid XML file. URL: ' + req_url)

        #refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/mrf_endpoint/1.0.0/WMTSCapabilities.xml'))
        refXMLtree = ElementTree.parse(os.path.join(os.getcwd(), 'ci_tests/layer_config_reproject_endpoint/baseline/GetCapabilities.1.0.0.xml'))
        refXMLroot = refXMLtree.getroot()
        refXMLdict = XmlDictConfig(refXMLroot)

        check_result = check_dicts(XMLdict, refXMLdict)
        self.assertTrue(check_result, 'Reproject WMTS (REST) Get Capabilities Request does not match what\'s expected. URL: ' + req_url)

    def test_layer_daily_png(self):
        """
        3. test_daily_png layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_daily_png layer configuration'

        # Verify auto generated files
        layer_config = os.path.join(self.testdata_path, 'layer_config_endpoint/test_daily_png/default/16km/mod_mrf.config')
        cmp_result = filecmp.cmp(layer_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/test_daily_png/mod_mrf.config'), False)
        self.assertTrue(cmp_result, 'Generated layer config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_endpoint/twms/test_daily_png/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/twms/test_daily_png/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_layer_legacy_subdaily_jpg(self):
        """
        4. test_legacy_subdaily_jpg layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_legacy_subdaily_jpg layer configuration'

        # Verify auto generated files
        layer_config = os.path.join(self.testdata_path, 'layer_config_endpoint/test_legacy_subdaily_jpg/default/16km/mod_mrf.config')
        cmp_result = filecmp.cmp(layer_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/test_legacy_subdaily_jpg/mod_mrf.config'), False)
        self.assertTrue(cmp_result, 'Generated layer config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_endpoint/twms/test_legacy_subdaily_jpg/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/twms/test_legacy_subdaily_jpg/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_layer_static_jpg(self):
        """
        5. test_static_jpg layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_static_jpg layer configuration'

        # Verify auto generated files
        layer_config = os.path.join(self.testdata_path, 'layer_config_endpoint/test_static_jpg/default/16km/mod_mrf.config')
        cmp_result = filecmp.cmp(layer_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/test_static_jpg/mod_mrf.config'), False)
        self.assertTrue(cmp_result, 'Generated layer config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_endpoint/twms/test_static_jpg/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/twms/test_static_jpg/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_layer_versioned_colormaps(self):
        """
        6. test_versioned_colormaps layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_versioned_colormaps layer configuration'

        # Verify auto generated files
        layer_config = os.path.join(self.testdata_path, 'layer_config_endpoint/test_versioned_colormaps/default/2km/mod_mrf.config')
        cmp_result = filecmp.cmp(layer_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/test_versioned_colormaps/mod_mrf.config'), False)
        self.assertTrue(cmp_result, 'Generated layer config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_endpoint/twms/test_versioned_colormaps/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/twms/test_versioned_colormaps/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_reproject_layer_daily_png(self):
        """
        7. test_daily_png reproject layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_daily_png reproject layer configuration'

        # Verify auto generated files
        source_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_daily_png/default/GoogleMapsCompatible_Level3/source.config')
        reproject_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_daily_png/default/GoogleMapsCompatible_Level3/reproject.config')
        cmp_result = filecmp.cmp(source_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_daily_png/source.config'), False)
        self.assertTrue(cmp_result, 'Generated source config does not match what\'s expected.')
        cmp_result = filecmp.cmp(reproject_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_daily_png/reproject.config'), False)
        self.assertTrue(cmp_result, 'Generated reproject config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/twms/test_daily_png/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/twms/test_daily_png/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_reproject_layer_legacy_subdaily_jpg(self):
        """
        8. test_legacy_subdaily_jpg reproject layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_legacy_subdaily_jpg reproject layer configuration'

        # Verify auto generated files
        source_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_legacy_subdaily_jpg/default/GoogleMapsCompatible_Level3/source.config')
        reproject_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_legacy_subdaily_jpg/default/GoogleMapsCompatible_Level3/reproject.config')
        cmp_result = filecmp.cmp(source_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_legacy_subdaily_jpg/source.config'), False)
        self.assertTrue(cmp_result, 'Generated source config does not match what\'s expected.')
        cmp_result = filecmp.cmp(reproject_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_legacy_subdaily_jpg/reproject.config'), False)
        self.assertTrue(cmp_result, 'Generated reproject config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/twms/test_legacy_subdaily_jpg/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/twms/test_legacy_subdaily_jpg/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_reproject_layer_static_jpg(self):
        """
        9. test_static_jpg reproject layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_static_jpg reproject layer configuration'

        # Verify auto generated files
        source_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_static_jpg/default/GoogleMapsCompatible_Level3/source.config')
        reproject_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_static_jpg/default/GoogleMapsCompatible_Level3/reproject.config')
        cmp_result = filecmp.cmp(source_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_static_jpg/source.config'), False)
        self.assertTrue(cmp_result, 'Generated source config does not match what\'s expected.')
        cmp_result = filecmp.cmp(reproject_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_static_jpg/reproject.config'), False)
        self.assertTrue(cmp_result, 'Generated reproject config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/twms/test_static_jpg/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/twms/test_static_jpg/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_reproject_layer_versioned_colormaps(self):
        """
        10. test_versioned_colormaps reproject layer configuration
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test_versioned_colormaps reproject layer configuration'

        # Verify auto generated files
        source_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_versioned_colormaps/default/GoogleMapsCompatible_Level6/source.config')
        reproject_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/test_versioned_colormaps/default/GoogleMapsCompatible_Level6/reproject.config')
        cmp_result = filecmp.cmp(source_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_versioned_colormaps/source.config'), False)
        self.assertTrue(cmp_result, 'Generated source config does not match what\'s expected.')
        cmp_result = filecmp.cmp(reproject_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/test_versioned_colormaps/reproject.config'), False)
        self.assertTrue(cmp_result, 'Generated reproject config does not match what\'s expected.')
        layer_twms_config = os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/twms/test_versioned_colormaps/twms.config')
        cmp_result = filecmp.cmp(layer_twms_config, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/twms/test_versioned_colormaps/twms.config'), False)
        self.assertTrue(cmp_result, 'Generated TWMS layer config does not match what\'s expected.')

    def test_apache_conf(self):
        """
        11. test auto generated apache conf files
        """
        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: test auto generated apache conf files'

        # Verify auto generated conf files
        layer_gc_conf = '/etc/httpd/conf.d/oe2_layer_config_gc.conf'
        layer_conf = '/etc/httpd/conf.d/oe2_layer_config.conf'
#        cmp_result = filecmp.cmp(layer_gc_conf, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/oe2_layer_config_gc.conf'), False)
#        self.assertTrue(cmp_result, 'Generated layer config GC conf does not match what\'s expected.')

#        cmp_result = filecmp.cmp(layer_conf, os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/oe2_layer_config.conf'), False)
#        self.assertTrue(cmp_result, 'Generated layer config conf does not match what\'s expected.')

        layer_reproject_gc_conf = '/etc/httpd/conf.d/oe2_layer_config_reproject_gc.conf'
        layer_reproject_conf = '/etc/httpd/conf.d/oe2_layer_config_reproject.conf'
#        cmp_result = filecmp.cmp(layer_reproject_gc_conf, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/oe2_layer_config_reproject_gc.conf'), False)
#        self.assertTrue(cmp_result, 'Generated reproject layer config GC conf does not match what\'s expected.')
#        cmp_result = filecmp.cmp(layer_reproject_conf, os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/oe2_layer_config_reproject.conf'), False)
#        self.assertTrue(cmp_result, 'Generated reproject layer config conf does not match what\'s expected.')

        with apacheconfig.make_loader() as loader:
            gc_config = loader.load(layer_gc_conf)
            config = loader.load(layer_conf)
            reproject_gc_config = loader.load(layer_reproject_gc_conf)
            reproject_config = loader.load(layer_reproject_conf)
            gc_base = loader.load(os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/oe2_layer_config_gc.conf'))
            base = loader.load(os.path.join(self.testdata_path, 'layer_config_endpoint/baseline/oe2_layer_config.conf'))
            reproject_gc_base = loader.load(os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/oe2_layer_config_reproject_gc.conf'))
            reproject_base = loader.load(os.path.join(self.testdata_path, 'layer_config_reproject_endpoint/baseline/oe2_layer_config_reproject.conf'))
        
        check_result = check_dicts(gc_config, gc_base)
        self.assertTrue(check_result, 'Generated layer config GC conf does not match what\'s expected.')

        check_result = check_dicts(config, base)
        self.assertTrue(check_result, 'Generated layer config conf does not match what\'s expected.')

        check_result = check_dicts(reproject_gc_config, reproject_gc_base)
        self.assertTrue(check_result, 'Generated layer config reproject GC conf does not match what\'s expected.')

        check_result = check_dicts(reproject_config, reproject_base)
        self.assertTrue(check_result, 'Generated layer config reproject conf does not match what\'s expected.')

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(os.path.join('/etc/httpd/conf.d/' + 'oe2_test_date_service.conf'))
        os.remove(os.path.join('/etc/httpd/conf.d/' + 'oe2_layer_config_gc.conf'))
        os.remove(os.path.join('/etc/httpd/conf.d/' + 'oe2_layer_config.conf'))
        os.remove(os.path.join('/etc/httpd/conf.d/' + 'oe2_layer_config_reproject_gc.conf'))
        os.remove(os.path.join('/etc/httpd/conf.d/' + 'oe2_layer_config_reproject.conf'))
        rmtree(self.staging_area)
        rmtree(self.config_endpoint_area)
        rmtree(self.config_layers_area)
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_configure_layer_results.xml',
                      help='Specify XML output file (default is test_configure_layer_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestLayerConfig.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
