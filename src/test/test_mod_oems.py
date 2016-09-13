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
# Tests for mod_oems with mod_oemstime
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

from oe_test_utils import check_tile_request, restart_apache, check_response_code, test_snap_request, file_text_replace, make_dir_tree, run_command, get_url, check_valid_mvt

DEBUG = False

class TestModOEMS(unittest.TestCase):

    # SETUP

    @classmethod
    def setUpClass(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        testdata_path = os.path.join(os.getcwd(), 'mod_onearth_test_data')
        wmts_configs = ('wmts_cache_configs', 'wmts_cache_staging', 'test_imagery/cache_all_wmts.config')
        twms_configs = ('twms_cache_configs', 'twms_cache_staging', 'test_imagery/cache_all_twms.config')
        self.image_files_path = os.path.join(testdata_path, 'test_imagery')
        self.test_apache_config = os.path.join(testdata_path, 'oe_test.conf')
        self.mapfile = os.path.join(testdata_path, 'epsg4326.map')
        
        # create links for mapserv
        mapserver_location = '/usr/bin/mapserv'
        if os.path.isfile(mapserver_location):
            if os.path.islink(testdata_path + '/wms_endpoint/mapserv') == False:
                os.symlink(mapserver_location, testdata_path + '/wms_endpoint/mapserv')
            if os.path.islink(testdata_path + '/wfs_endpoint/mapserv') == False:
                os.symlink(mapserver_location, testdata_path + '/wfs_endpoint/mapserv')
        else:
            raise IOError(mapserver_location + 'does not exist')
        
        for template_dir, staging_dir, cache_config in (wmts_configs, twms_configs):
            # Make staging cache files dir
            template_path = os.path.join(testdata_path, template_dir)
            staging_path = os.path.join(testdata_path, staging_dir)
            cache_path = os.path.join(testdata_path, cache_config)
            make_dir_tree(staging_path)

            # Copy XML/MRF files to staging cache files dir, swapping in the location of the imagery files
            for file in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
                file_text_replace(os.path.join(template_path, file), os.path.join(staging_path, file),
                                  '{cache_path}', self.image_files_path)

            # Run oe_create_cache_config to make the cache config files
            cmd = 'oe_create_cache_config -cbd {0} {1}'.format(staging_path, cache_path)
            run_command(cmd)
            rmtree(staging_path)

        # Put the correct path into the mapfile
        file_text_replace(self.mapfile + ".default", self.mapfile, '{cache_path}', testdata_path)

        # Put the correct path into the Apache config (oe_test.conf)
        file_text_replace(self.test_apache_config, os.path.join('/etc/httpd/conf.d', os.path.basename(self.test_apache_config)),
                          '{cache_path}', testdata_path)
        restart_apache()

        # URL that will be used to create the snap test requests
        self.snap_test_url_template = 'http://localhost/onearth/test/{2}/mapserv?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng&TRANSPARENT=true&LAYERS={0}&CRS=EPSG%3A4326&STYLES=&WIDTH=1536&HEIGHT=636&BBOX=-111.796875%2C-270%2C111.796875%2C270&TIME={1}'
        
    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_wms_no_time_jpg(self):
        """
        1. Request current (no time) JPEG via WMS

        All the tile tests follow this template.
        """
        # Reference MD5 hash value -- the one that we're testing against
        ref_hash = '7c995c069a1a0325b9eba00470227613'

        layer_name = 'test_static_jpg'
        req_date = ''
        service = 'wms'

        # The URL of the tile to be requested
        req_url = self.snap_test_url_template.format(layer_name, req_date, service)

        # Debug message (if DEBUG is set)
        if DEBUG:
            print '\nTesting: Request current (no TIME) JPG via WMS'
            print 'URL: ' + req_url

        # Downloads the tile and checks it against the reference hash.
        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(check_result, 'Current (no TIME) WMS JPG Request does not match what\'s expected. URL: ' + req_url)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(os.path.join('/etc/httpd/conf.d/' + os.path.basename(self.test_apache_config)))
        restart_apache()
        os.remove(os.path.join(self.image_files_path, 'cache_all_wmts.config'))
        os.remove(os.path.join(self.image_files_path, 'cache_all_twms.config'))
        os.remove(self.mapfile)

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
        TestModOnEarth.setUpClass()
        sys.exit('Apache has been loaded with the test configuration. No tests run.')
    
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
