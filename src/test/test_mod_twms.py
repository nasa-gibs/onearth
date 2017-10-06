#!/bin/env python

# Copyright (c) 2002-2017, California Institute of Technology.
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

"""
Test suite to make sure that mod_twms is properly handling TWMS errors.
"""

import os
import sys
import unittest2 as unittest
import xmlrunner
from shutil import rmtree
from xml.etree import cElementTree as ElementTree
from oe_test_utils import check_response_code, check_tile_request, file_text_replace, get_url, make_dir_tree, restart_apache, run_command
from optparse import OptionParser

base_url = 'http://localhost'
apache_conf_dir = '/etc/httpd/conf.d'


class TestModTwmsErrorHandling(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # Get paths for test files
        test_config_path = os.path.join(os.getcwd(), 'mod_twms_test_data/test_twms_err')
        twms_configs = ('twms_cache_configs', 'twms_cache_staging', 'test_imagery/cache_all_twms.config')
        self.image_files_path = os.path.join(test_config_path, 'test_imagery')
        base_apache_config = os.path.join(test_config_path, 'test_twms_err_apache.conf')
        self.output_apache_config = os.path.join(apache_conf_dir, 'test_twms_err_apache.conf')

        (template_dir, staging_dir, cache_config) = twms_configs
        # Make staging cache files dir
        template_path = os.path.join(test_config_path, template_dir)
        staging_path = os.path.join(test_config_path, staging_dir)
        cache_path = os.path.join(test_config_path, cache_config)
        make_dir_tree(staging_path)

        # Copy XML/MRF files to staging cache files dir, swapping in the location of the imagery files
        for file in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
            file_text_replace(os.path.join(template_path, file), os.path.join(staging_path, file), '{cache_path}', self.image_files_path)

        # Run oe_create_cache_config to make the cache config files
        cmd = 'oe_create_cache_config -cbd {0} {1}'.format(staging_path, cache_path)
        run_command(cmd)
        rmtree(staging_path)

        try:
            #file_text_replace(base_apache_config, self.output_apache_config, '{testpath}', test_config_path)
            file_text_replace(base_apache_config, self.output_apache_config, '{cache_path}', test_config_path)
        except IOError as e:
            print "Can't write file: {0}. Error: {1}".format(self.output_apache_config, e)

        restart_apache()

    # KVP Tests
    # http://localhost/onearth/test/wmts/wmts.cgi?layer=test_weekly_jpg&tilematrixset=EPSG4326_16km&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image%2Fjpeg&TileMatrix=0&TileCol=0&TileRow=0&time=2012-02-22
    # http://localhost/onearth/test/twms/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90&TIME=2012-02-22
    # Missing parameters
    def test_missing_request(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_missing_layer(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_missing_format(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_missing_tilematrixset(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_missing_heightwidth(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_missing_bbox(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512'
        response = get_url(test_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            xml_check = True
        except ElementTree.ParseError:
            xml_check = False
        self.assertTrue(xml_check, 'TWMS response is not a valid XML file. URL: ' + test_url)

        exception = XMLroot.find('ServiceException').text
        print exception
        check_str = exception.find('WMS parameter bbox format incorrect')
        error = 'The TWMS response does not match what\'s expected. URL: {0}'.format(test_url)
        self.assertTrue(check_str, error)

    # Invalid parameters
    def test_bad_request(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=NOTEXIST&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_layer(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=bogus_layer&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_style(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=shaolin&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_format(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fppng&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_tilematrixset(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4328&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_heightwidth_value(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=0&amp;height=-5&amp;bbox=-180,-198,108,90'
        response_code = 500
        response_value = 'Internal Server Error'
        #if DEBUG:
            #print 'Using URL: {0}, expecting response code of {1} and response value of {2}'.format(test_url, response_code, response_value)
        check_code = check_response_code(test_url, response_code, response_value)
        error = 'The TWMS response code does not match what\'s expected. URL: {0}, Expected Response Code: {1}'.format(test_url, response_code)
        self.assertTrue(check_code, error)

    def test_bad_bbox_value(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,10'
        response = get_url(test_url)

        # Check if the response is valid XML
        try:
            XMLroot = ElementTree.XML(response.read())
            xml_check = True
        except ElementTree.ParseError:
            xml_check = False
        self.assertTrue(xml_check, 'TWMS response is not a valid XML file. URL: ' + test_url)

        exception = XMLroot.find('ServiceException').text
        print exception
        check_str = exception.find('WMS parameter bbox format incorrect')
        error = 'The TWMS response does not match what\'s expected. URL: {0}'.format(test_url)
        self.assertTrue(check_str, error)

    #def test_kvp_tilerow_out_of_range(self):
        #test_url = base_url + '/test_mod_twms_err/twms.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=5&tilecol=0'
        #test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILEROW', 'TILEROW is out of range, maximum value is 0')

    #def test_kvp_tilecol_out_of_range(self):
        #test_url = base_url + '/test_mod_twms_err/twms.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=5'
        #test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILECOL', 'TILECOL is out of range, maximum value is 0')

    def test_bad_time_format(self):
        test_url = base_url + '/test_mod_reproject_twms_err/twms.cgi?request=GetMap&amp;layers=test_weekly_jpg&amp;srs=EPSG:4326&amp;format=image%2Fjpeg&amp;styles=&amp;&amp;width=512&amp;height=512&amp;bbox=-180,-198,108,90&amp;time=86753-09'
        ref_hash = 'fb28bfeba6bbadac0b5bef96eca4ad12'
        check_result = check_tile_request(test_url, ref_hash)
        self.assertTrue(check_result, 'Bad time TWMS request does not match what\'s expected. URL: ' + test_url)

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(self.output_apache_config)
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_twms_err_results.xml',
                      help='Specify XML output file (default is test_mod_twms_err_results.xml')
    parser.add_option('-s', '--start_server', action='store_true', dest='start_server', help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option('-l', '--conf_location', action='store', dest='apache_conf_dir',
                      help='Apache config location to install test files to (default is /etc/httpd/conf.d)',
                      default=apache_conf_dir)
    parser.add_option('-u', '--base_url', action='store', dest='base_url',
                      help='Base url for the Apache install on this machine (default is http://localhost)', default=base_url)
    (options, args) = parser.parse_args()

    # Set the globals for these tests
    apache_conf_dir = options.apache_conf_dir
    base_url = options.base_url

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModTwmsErrorHandling.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
