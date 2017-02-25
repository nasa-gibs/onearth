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
# Tests for mod_onearth
#

import os
import sys
import unittest2 as unittest
import struct
import glob
import StringIO
import gzip
import fiona
import fiona.crs
import xmlrunner
import xml.dom.minidom
import shutil
from optparse import OptionParser
import mapbox_vector_tile
# from osgeo import osr

from oe_test_utils import run_command

DEBUG = False


class TestVectorgen(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # Copy test files to the path where vectorgen will be run and artifacts created.
        # Unless DEBUG is set, the artifacts will be wiped when the test concludes.
        self.test_data_path = os.path.join(os.getcwd(), 'vectorgen_test_data')
        self.main_artifact_path = os.path.join(os.getcwd(), 'vectorgen_test_artifacts')
        os.makedirs(self.main_artifact_path)

        # Set config files for individual tests
        self.mrf_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf.xml')
        self.shapefile_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile.xml')
        self.reproject_test_config = os.path.join(self.test_data_path, 'vectorgen_test_reproject.xml')

    # Utility function that parses a vectorgen config XML and creates necessary dirs/copies necessary files
    def parse_vector_config(self, vector_config, artifact_path):
        # Parse the config file to get relevant info on output directories and filenames
        with open(vector_config, 'r') as f:
            config_dom = xml.dom.minidom.parse(f)
        try:
            input_file = config_dom.getElementsByTagName('file')[0].firstChild.nodeValue
        except IndexError:
            print 'Problem reading {0} -- can\'t find "input_files" tag. Aborting test.'.format(self.mrf_test_config)
            sys.exit()
        try:
            prefix = config_dom.getElementsByTagName('output_name')[0].firstChild.nodeValue
        except IndexError:
            print 'Problem reading {0} -- can\'t find "output_name" tag. Aborting test.'.format(self.mrf_test_config)
            sys.exit()
        try:
            working_dir = config_dom.getElementsByTagName('working_dir')[0].firstChild.nodeValue
        except IndexError:
            print 'Problem reading {0} -- can\'t find "working_dir" tag. Aborting test.'.format(self.mrf_test_config)
            sys.exit()
        try:
            output_dir = config_dom.getElementsByTagName('output_dir')[0].firstChild.nodeValue
        except IndexError:
            print 'Problem reading {0} -- can\'t find "output_dir" tag. Aborting test.'.format(self.mrf_test_config)
            sys.exit()
        try:
            source_epsg = config_dom.getElementsByTagName('source_epsg')[0].firstChild.nodeValue
        except IndexError:
            source_epsg = None
        try:
            target_epsg = config_dom.getElementsByTagName('target_epsg')[0].firstChild.nodeValue
        except IndexError:
            target_epsg = None


        # Create artifact paths
        output_dir = os.path.join(artifact_path, output_dir)
        working_dir = os.path.join(artifact_path, working_dir)
        os.makedirs(artifact_path)
        os.makedirs(output_dir)
        os.makedirs(working_dir)

        # Copy config and data files to artifact path
        shutil.copy(vector_config, artifact_path)
        input_file_prefix = os.path.splitext(input_file)[0]
        input_files = glob.glob(os.path.join(self.test_data_path, input_file_prefix + '*'))
        for file in input_files:
            shutil.copy(file, artifact_path)

        # Return values needed by the test routine
        config = {
            'prefix': prefix,
            'input_files': input_files,
            'output_dir': output_dir,
            'source_epsg': source_epsg,
            'target_epsg': target_epsg
        }
        return config

    # Tests that tiles from the MRF are valid gzipped MVT tiles. Alerts if the overview tiles contain no features.
    def test_MVT_MRF_generation(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf')
        config = self.parse_vector_config(self.mrf_test_config, test_artifact_path)
        
        # Run vectorgen
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_test_config
        run_command(cmd, ignore_warnings=True)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = StringIO.StringIO()
            offset = struct.unpack('>q', byte[0:8])[0]
            size = struct.unpack('>q', byte[8:16])[0]
            with open(os.path.join(config['output_dir'], config['prefix'] + '.pvt'), 'rb') as pvt:
                pvt.seek(offset)
                tile_buffer.write(pvt.read(size))
            tile_buffer.seek(0)
            # Check to see if extracted files are valid zip files and valid MVT tiles
            try:
                unzipped_tile = gzip.GzipFile(fileobj=tile_buffer)
                tile_data = unzipped_tile.read()
            except IOError:
                self.fail("Invalid tile found in MRF -- can't be unzipped.")
            try:
                tile = mapbox_vector_tile.decode(tile_data)
            except:
                self.fail("Can't decode MVT tile -- bad protobuffer or wrong MVT structure")
            # Check the top 2 tiles to see if they have any features (they should)
            if byte != first_byte:
                top_tile_feature_count += len(tile[tile.keys()[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    def test_shapefile_generation(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'shapefiles')
        config = self.parse_vector_config(self.shapefile_test_config, test_artifact_path)

        # Open input shapefile and get stats
        try:
            with fiona.open(config['input_files'][0]) as geojson:
                origin_num_features = len(list(geojson))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input geojson {0}. Make sure it's valid.".format(config['input_files'][0]))
        
        # Run vectorgen
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_test_config
        run_command(cmd, ignore_warnings=True)

        # Check the output
        output_file = os.path.join(config['output_dir'], config['prefix'] + '.shp')
        try:
            with fiona.open(output_file) as shapefile:
                self.assertEqual(origin_num_features, len(list(shapefile)),
                                 "Feature count between input GeoJSON {0} and output shapefile {1} differs. There is a problem with the conversion process."
                                 .format(config['input_files'][0], output_file))
        except IOError:
            self.fail("Expected output geojson file {0} doesn't appear to have been created.".format(output_file))
        except fiona.errors.FionaValueError:
            self.fail("Bad output geojson file {0}.".format(output_file))

    @classmethod
    def tearDownClass(self):
        if not DEBUG:
            shutil.rmtree(self.main_artifact_path)

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_vectorgen_results.xml',
                      help='Specify XML output file (default is test_vectorgen_results.xml')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
