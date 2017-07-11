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
Test suite to make sure that mod_reproject is properly handling WMTS errors.
"""

import os
import sys
import unittest2 as unittest
import xmlrunner
from oe_test_utils import file_text_replace, restart_apache, test_wmts_error
from optparse import OptionParser

base_url = 'http://localhost'
apache_conf_dir = '/etc/httpd/conf.d'


class TestModWmtsWrapperErrorHandling(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # Get paths for test files
        test_config_path = os.path.join(os.getcwd(), 'mod_wmts_wrapper_test_data/test_wmts_err')
        base_apache_config = os.path.join(test_config_path, 'test_wmts_err_apache.conf')
        self.output_apache_config = os.path.join(apache_conf_dir, 'test_wmts_err_apache.conf')

        try:
            file_text_replace(base_apache_config, self.output_apache_config, '{testpath}', test_config_path)
        except IOError as e:
            print "Can't write file: {0}. Error: {1}".format(self.output_apache_config, e)

        restart_apache()

    # REST tests
    def test_REST_bad_layer(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/bogus_layer/default/default/0/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'LAYER', 'LAYER does not exist')

    def test_REST_bad_style(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/bogus_style/default/0/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'STYLE', 'STYLE is invalid for LAYER')

    def test_REST_bad_tilematrixset_date(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/default/bogus_tilematrixset/0/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIXSET', 'TILEMATRIXSET is invalid for LAYER')

    def test_REST_bad_tilematrixset_nodate(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/bogus_tilematrixset/0/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIXSET', 'TILEMATRIXSET is invalid for LAYER')

    def test_REST_invalid_tilematrix(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/10/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIX', 'Invalid TILEMATRIX')

    def test_REST_bad_tilematrix_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/bogus/0/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIX', 'TILEMATRIX is not a valid integer')

    def test_REST_row_out_of_range(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/0/1/0.png'
        test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILEROW', 'TILEROW is out of range, maximum value is 0')

    def test_REST_bad_tilerow_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/0/bogus/0.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEROW', 'TILEROW is not a valid integer')

    def test_REST_tilecol_out_of_range(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/0/0/1.png'
        test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILECOL', 'TILECOL is out of range, maximum value is 0')

    def test_REST_bad_tilecol_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/0/0/bogus.png'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILECOL', 'TILECOL is not a valid integer')

    def test_REST_bad_date_format(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/test_layer/default/GoogleMapsCompatible_Level6/0/0/1.bogus'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'FORMAT', 'FORMAT is invalid for LAYER')

    # KvP Tests

    # Missing parameters
    def test_kvp_missing_request(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'REQUEST', 'Missing REQUEST parameter')

    def test_kvp_missing_service(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'SERVICE', 'Missing SERVICE parameter')

    def test_kvp_missing_version(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'VERSION', 'Missing VERSION parameter')

    def test_kvp_missing_layer(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'LAYER', 'Missing LAYER parameter')

    def test_kvp_missing_format(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'FORMAT', 'Missing FORMAT parameter')

    def test_kvp_missing_tilematrixset(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'TILEMATRIXSET', 'Missing TILEMATRIXSET parameter')

    def test_kvp_missing_tilematrix(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'TILEMATRIX', 'Missing TILEMATRIX parameter')

    def test_kvp_missing_tilerow(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'TILEROW', 'Missing TILEROW parameter')

    def test_kvp_missing_tilecol(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0'
        test_wmts_error(self, test_url, 400, 'MissingParameterValue', 'TILECOL', 'Missing TILECOL parameter')

    # Invalid parameters
    def test_kvp_bad_service(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=tmnt&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'SERVICE', 'Unrecognized service')

    def test_kvp_bad_request(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=getschwifty&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 501, 'OperationNotSupported', 'REQUEST', 'The request type is not supported')

    def test_kvp_bad_version(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=3.2.1&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'VERSION', 'VERSION is invalid')

    def test_kvp_bad_layer(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=bogus_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'LAYER', 'LAYER does not exist')

    def test_kvp_bad_style(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0&style=shaolin'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'STYLE', 'STYLE is invalid for LAYER')

    def test_kvp_bad_format(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/jpeg&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'FORMAT', 'FORMAT is invalid for LAYER')

    def test_kvp_bad_tilematrixset(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level43&tilematrix=0&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIXSET', 'TILEMATRIXSET is invalid for LAYER')

    def test_kvp_bad_tilematrix_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=morpheus&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIX', 'TILEMATRIX is not a valid integer')

    def test_kvp_bad_tilerow_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=rowrowyourboat&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEROW', 'TILEROW is not a valid integer')

    def test_kvp_bad_tilecol_value(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=infirth'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILECOL', 'TILECOL is not a valid integer')

    def test_kvp_invalid_tilematrix_(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=43&tilerow=0&tilecol=0'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TILEMATRIX', 'Invalid TILEMATRIX')

    def test_kvp_tilerow_out_of_range(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=5&tilecol=0'
        test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILEROW', 'TILEROW is out of range, maximum value is 0')

    def test_kvp_tilecol_out_of_range(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=5'
        test_wmts_error(self, test_url, 400, 'TileOutOfRange', 'TILECOL', 'TILECOL is out of range, maximum value is 0')

    def test_kvp_bad_time_format(self):
        test_url = base_url + '/test_mod_reproject_wmts_err/wmts.cgi?layer=test_layer&version=1.0.0&service=wmts&request=gettile&format=image/png&tilematrixset=GoogleMapsCompatible_Level6&tilematrix=0&tilerow=0&tilecol=0&time=86753-09'
        test_wmts_error(self, test_url, 400, 'InvalidParameterValue', 'TIME', 'Invalid time format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ')

    @classmethod
    def tearDownClass(self):
        # Delete Apache test config
        os.remove(self.output_apache_config)
        restart_apache()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_mod_wmts_wrapper_err_results.xml',
                      help='Specify XML output file (default is test_mod_wmts_wrapper_err_results.xml')
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
        TestModWmtsWrapperErrorHandling.setUpClass(options.conf_location)
        sys.exit('Apache has been loaded with the test configuration. No tests run.')

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
