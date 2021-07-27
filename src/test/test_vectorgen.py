#!/usr/bin/env python3

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
import subprocess
import unittest2 as unittest
import struct
import glob
import io
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

        print('main_artifact_path = ' + self.main_artifact_path)
        
        os.makedirs(self.main_artifact_path)

        print('dir exists = ' + str(os.path.isdir(self.main_artifact_path)))

        # Set config files for individual tests
        self.mrf_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf.xml')
        self.mrf_from_geojson_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_from_geojson.xml')
        self.mrf_multiple_shp_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_multiple_shp.xml')
        self.mrf_multiple_geojson_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_multiple_geojson.xml')
        self.mrf_overview_levels_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_overview_levels.xml')
        self.mrf_feat_reduce_rate_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_feat_reduce_rate.xml')
        self.mrf_clust_reduce_rate_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_clust_reduce_rate.xml')
        self.mrf_feature_filters_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_feature_filters.xml')
        self.mrf_overview_filters_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_overview_filters.xml')
        self.shapefile_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile.xml')
        self.shapefile_diff_proj_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile_diff_proj.xml')
        self.geojson_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_geojson.xml')
        self.shapefile_mult_geojson_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile_multiple_geojson.xml')
        self.shapefile_mult_geojson_input_dir_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile_multiple_geojson_input_dir.xml')
        self.shapefile_mult_shp_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_shapefile_multiple_shp.xml')
        self.mrf_diff_proj_test_config = os.path.join(self.test_data_path, 'vectorgen_test_create_mvt_mrf_diff_proj.xml')
        self.reproject_test_config = os.path.join(self.test_data_path, 'vectorgen_test_reproject.xml')

    # Utility function that parses a vectorgen config XML and creates necessary dirs/copies necessary files
    def parse_vector_config(self, vector_config, artifact_path):
        # Parse the config file to get relevant info on output directories and filenames
        with open(vector_config, 'r') as f:
            config_dom = xml.dom.minidom.parse(f)
        try:
            input_files = []
            input_dir = ""
            for infile in config_dom.getElementsByTagName('file'):
                input_files.append(infile.firstChild.nodeValue)
            if not input_files:
                input_dir = config_dom.getElementsByTagName('input_dir')[0].firstChild.nodeValue
        except IndexError:
            print('Problem reading {0} -- can\'t find "input_files" tag or "input_dir" tag. Aborting test.'.format(self.mrf_test_config))
            sys.exit()
        try:
            prefix = config_dom.getElementsByTagName('output_name')[0].firstChild.nodeValue
        except IndexError:
            print('Problem reading {0} -- can\'t find "output_name" tag. Aborting test.'.format(self.mrf_test_config))
            sys.exit()
        try:
            working_dir = config_dom.getElementsByTagName('working_dir')[0].firstChild.nodeValue
        except IndexError:
            print('Problem reading {0} -- can\'t find "working_dir" tag. Aborting test.'.format(self.mrf_test_config))
            sys.exit()
        try:
            output_dir = config_dom.getElementsByTagName('output_dir')[0].firstChild.nodeValue
        except IndexError:
            print('Problem reading {0} -- can\'t find "output_dir" tag. Aborting test.'.format(self.mrf_test_config))
            sys.exit()
        try:
            source_epsg = config_dom.getElementsByTagName('source_epsg')[0].firstChild.nodeValue
        except IndexError:
            source_epsg = None
        try:
            target_epsg = config_dom.getElementsByTagName('target_epsg')[0].firstChild.nodeValue
        except IndexError:
            target_epsg = None
        try:
            feature_filters = config_dom.getElementsByTagName('feature_filters')[0].firstChild.nodeValue
        except IndexError:
            feature_filters = None
        try:
            overview_filters = config_dom.getElementsByTagName('overview_filters')[0].firstChild.nodeValue
        except IndexError:
            overview_filters = None


        # Create artifact paths
        output_dir = os.path.join(artifact_path, output_dir)
        working_dir = os.path.join(artifact_path, working_dir)

        print("output_dir = " + output_dir)

        os.makedirs(artifact_path)
        os.makedirs(output_dir)
        os.makedirs(working_dir)

        # Copy config to artifact path
        shutil.copy(vector_config, artifact_path)

        # if we're using 'input_files'
        if input_files:
            # copy data to artifact path
            input_files_all = []
            for i in range(len(input_files)):
                input_file_prefix = os.path.splitext(input_files[i])[0]
                input_files_all.extend(glob.glob(os.path.join(self.test_data_path, input_file_prefix + '*')))
                input_files[i] = os.path.join(self.test_data_path, input_files[i])
            for file in input_files_all:
                shutil.copy(file, artifact_path)
            
            # Return values needed by the test routine (using 'input_files')
            config = {
                'prefix': prefix,
                'input_files': input_files,
                'output_dir': output_dir,
                'source_epsg': source_epsg,
                'target_epsg': target_epsg,
                'feature_filters': feature_filters,
                'overview_filters': overview_filters
            }
        # if we're using 'input_dir'
        else:
            # copy data to artifact path
            input_dir_path = os.path.join(self.test_data_path, input_dir)
            input_dir_artifact_path = os.path.join(artifact_path, input_dir)
            os.makedirs(input_dir_artifact_path)
            input_files = os.listdir(input_dir_path)
            for infile in input_files:
                shutil.copy(os.path.join(input_dir_path, infile), input_dir_artifact_path)

            # Return values needed by the test routine (using 'input_dir')
            config = {
                'prefix': prefix,
                'input_dir': input_dir,
                'output_dir': output_dir,
                'source_epsg': source_epsg,
                'target_epsg': target_epsg,
                'feature_filters': feature_filters,
                'overview_filters': overview_filters
            }

        return config

    # Tests that tiles from the MRF are valid gzipped MVT tiles. Alerts if the overview tiles contain no features.
    def test_MVT_MRF_generation(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf')
        config = self.parse_vector_config(self.mrf_test_config, test_artifact_path)
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                top_tile_feature_count += len(tile[list(tile.keys())[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles. Alerts if the overview tiles contain no features.
    def test_MVT_MRF_generation_from_geojson(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_from_geojson')
        config = self.parse_vector_config(self.mrf_from_geojson_test_config, test_artifact_path)
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_from_geojson_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                top_tile_feature_count += len(tile[list(tile.keys())[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for multiple .shp inputs.
    # Alerts if the overview tiles contain no features or don't have features from all inputs.
    def test_MVT_MRF_generation_multiple_shp(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_multiple_shp')
        config = self.parse_vector_config(self.mrf_multiple_shp_test_config, test_artifact_path)
        
        # Open input GeoJSON and get stats
        try:
            with fiona.open(config['input_files'][0]) as shapefile1, fiona.open(config['input_files'][1]) as shapefile2, fiona.open(config['input_files'][2]) as shapefile3:
                origin_num_features = len(list(shapefile1)) + len(list(shapefile2)) + len(list(shapefile3))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input shapefile {0} or {1} or {2}. Make sure they're valid.".format(config['input_files'][0], config['input_files'][1], config['input_files'][2]))

        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_multiple_shp_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                top_tile_feature_count += len(tile[list(tile.keys())[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")
        self.assertTrue(top_tile_feature_count == origin_num_features, "MVT is missing features from some of the input shapefiles")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when multiple geojson input files are used.
    # Alerts if the overview tiles contain no features or if the mvt_mrf doesn't contain features from both input geojson.
    def test_MVT_MRF_generation_multiple_geojson(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_multiple_geojson')
        config = self.parse_vector_config(self.mrf_multiple_geojson_test_config, test_artifact_path)
                
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_multiple_geojson_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        s2_feature_count = 0
        mgrs_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                tile_num_features = len(tile[list(tile.keys())[0]]['features'])
                top_tile_feature_count += tile_num_features
            # Make sure the feature filter worked correctly
            for layer in tile:
                for feature in tile[layer]['features']:
                    if feature['properties']['type'] == 'S2':
                        s2_feature_count += 1
                    elif feature['properties']['type'] == 'MGRS':
                        mgrs_feature_count += 1
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")
        self.assertTrue(s2_feature_count, "MRF is missing features from the S2 geojson")
        self.assertTrue(mgrs_feature_count, "MRF is missing features from the MGRS geojson")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when the overview levels are explicitly specified.
    # Alerts if the overview tiles contain no features.
    def test_MVT_MRF_generation_overview_levels(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_overview_levels')
        config = self.parse_vector_config(self.mrf_overview_levels_test_config, test_artifact_path)
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_overview_levels_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                top_tile_feature_count += len(tile[list(tile.keys())[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when the feature reduce rate is explicitly specified.
    # Alerts if the overview tiles contain no features or if they do not contain fewer features than the input shapefile.
    def test_MVT_MRF_generation_feat_reduce_rate(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_feat_reduce_rate')
        config = self.parse_vector_config(self.mrf_feat_reduce_rate_test_config, test_artifact_path)
        
        # Open input shapefile and get stats
        try:
            with fiona.open(config['input_files'][0]) as shapefile:
                origin_num_features = len(list(shapefile))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input shapefile {0}. Make sure it's valid.".format(config['input_files'][0]))

        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_feat_reduce_rate_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                tile_num_features = len(tile[list(tile.keys())[0]]['features'])
                top_tile_feature_count += tile_num_features
                # Check that the tiles have fewer features than the input shapefile had
                self.assertTrue(tile_num_features < origin_num_features, "Tile does not contain fewer features than the input shapefile, feature reduce rate likely didn't work")
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when the cluster reduce rate is explicitly specified.
    # Alerts if the overview tiles contain no features or if they do not contain fewer features than the input shapefile.
    def test_MVT_MRF_generation_clust_reduce_rate(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_clust_reduce_rate')
        config = self.parse_vector_config(self.mrf_clust_reduce_rate_test_config, test_artifact_path)
        
        # Open input shapefile and get stats
        try:
            with fiona.open(config['input_files'][0]) as shapefile:
                origin_num_features = len(list(shapefile))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input shapefile {0}. Make sure it's valid.".format(config['input_files'][0]))

        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_clust_reduce_rate_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                tile_num_features = len(tile[list(tile.keys())[0]]['features'])
                top_tile_feature_count += tile_num_features
                # Check that the tiles have fewer features than the input shapefile had
                self.assertTrue(tile_num_features < origin_num_features, "Tile does not contain fewer features than the input shapefile, cluster reduce rate likely didn't work")
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when feature filters are used.
    # Alerts if the overview tiles contain no features or if the feature filters did not work correctly.
    def test_MVT_MRF_generation_feature_filters(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_feature_filters')
        config = self.parse_vector_config(self.mrf_feature_filters_test_config, test_artifact_path)

        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_feature_filters_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                tile_num_features = len(tile[list(tile.keys())[0]]['features'])
                top_tile_feature_count += tile_num_features
            # Make sure the feature filter worked correctly
            for layer in tile:
                for feature in tile[layer]['features']:
                    self.assertTrue(feature['properties']['SATELLITE'] == 'A', "Feature filter failed to filter features.")
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")

    # Tests that tiles from the MRF are valid gzipped MVT tiles for when overview filters are used.
    # Alerts if the overview tiles contain no features or if the overview filters did not work correctly.
    def test_MVT_MRF_generation_overview_filters(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_overview_filters')
        config = self.parse_vector_config(self.mrf_overview_filters_test_config, test_artifact_path)
                
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_overview_filters_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Run mrf_read.py on each zoom level (tileset)
        for zoom_level in range(1,6):
            outtile_name = os.path.join(config['output_dir'], 'tilezoom{0}.gz'.format(str(zoom_level)))
            cmd = "python3 mrf_read.py --input " + os.path.join(config['output_dir'], config['prefix'] + ".mrf") + " --output " + outtile_name + " --tilematrix {0}".format(zoom_level) + " --tilecol 0 --tilerow 0"
            run_command(cmd)
            
            try:
                with gzip.open(outtile_name, 'rb') as f:
                    unzipped_tile_data = f.read()
            except IOError:
                self.fail("Invalid tile found in MRF -- can't be unzipped.")
            
            tiledata = mapbox_vector_tile.decode(unzipped_tile_data)

            for key in tiledata:
                for feature in tiledata[key]["features"]:
                    if zoom_level > 5:
                        self.assertTrue(feature['properties']['type'] == "S2", "Overview filter failed to filter features. Zoom {0} contains a feature of type {1}, which isn't 'S2'.".format(zoom_level, feature['type']))
                    else:
                        self.assertTrue(feature['properties']['type'] == "MGRS", "Overview filter failed to filter features. Zoom {0} contains a feature of type {1}, which isn't 'MGRS'.".format(zoom_level, feature['type']))
            
    # Tests the creation of a shapefile from a single input GeoJSON.
    # Alerts if shapefile has different number of features from the GeoJSON.
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
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

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

    # Tests that shapefiles are generated correctly from GeoJSON input when the source EPSG differs from the target EPSG.
    # Alerts if the output shapefile has a different number of features from the input GeoJSON.
    def test_shapefile_generation_diff_proj(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'shapefiles_diff_proj')
        config = self.parse_vector_config(self.shapefile_diff_proj_test_config, test_artifact_path)

        # Open input shapefile and get stats
        try:
            with fiona.open(config['input_files'][0]) as geojson:
                origin_num_features = len(list(geojson))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input geojson {0}. Make sure it's valid.".format(config['input_files'][0]))
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_diff_proj_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

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
    
    # Tests the creation of a GeoJSON file from a single GeoJSON input. Alerts if number of features differs between input and output GeoJSON.
    def test_geojson_generation(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'geojson')
        config = self.parse_vector_config(self.geojson_test_config, test_artifact_path)

        # Open input shapefile and get stats
        try:
            with fiona.open(config['input_files'][0]) as geojson:
                origin_num_features = len(list(geojson))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input geojson {0}. Make sure it's valid.".format(config['input_files'][0]))
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.geojson_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Check the output
        output_file = os.path.join(config['output_dir'], config['prefix'] + '.json')
        try:
            with fiona.open(output_file) as geojson:
                self.assertEqual(origin_num_features, len(list(geojson)),
                                 "Feature count between input GeoJSON {0} and output GeoJSON {1} differs. There is a problem with the conversion process."
                                 .format(config['input_files'][0], output_file))
        except IOError:
            self.fail("Expected output geojson file {0} doesn't appear to have been created.".format(output_file))
        except fiona.errors.FionaValueError:
            self.fail("Bad output geojson file {0}.".format(output_file))

    """
    # Tests creation of a shapefile from multiple GeoJSON inputs.
    # Alerts if output shapefile's number of features differs from the sum of the number of features in the input GeoJSONs.
    def test_shapefile_generation_multiple_geojson(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'shapefiles_multiple_geojson')
        config = self.parse_vector_config(self.shapefile_mult_geojson_test_config, test_artifact_path)

        # Open input GeoJSON and get stats
        try:
            with fiona.open(config['input_files'][0]) as geojson1, fiona.open(config['input_files'][1]) as geojson2:
                origin_num_features = len(list(geojson1)) + len(list(geojson2))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input geojson {0} or {1}. Make sure they're valid.".format(config['input_files'][0], config['input_files'][1]))
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_mult_geojson_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Check the output
        output_file = os.path.join(config['output_dir'], config['prefix'] + '.shp')
        try:
            with fiona.open(output_file) as shapefile:
                self.assertEqual(origin_num_features, len(list(shapefile)),
                                 "Feature count between the sum of input GeoJSONs {0} and {1} differs from that of output shapefile {2}. There is a problem with the conversion process."
                                 .format(config['input_files'][0], config['input_files'][1], output_file))
        except IOError:
            self.fail("Expected output geojson file {0} doesn't appear to have been created.".format(output_file))
        except fiona.errors.FionaValueError:
            self.fail("Bad output geojson file {0}.".format(output_file))
    """

    """
    # Tests creation of a shapefile from multiple GeoJSON inputs.
    # Alerts if output shapefile's number of features differs from the sum of the number of features in the input GeoJSONs.
    # This test uses the `input_dir` tag to specify input files rather than `input_files`
    def test_shapefile_generation_multiple_geojson_input_dir(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'shapefiles_multiple_geojson_input_dir')
        config = self.parse_vector_config(self.shapefile_mult_geojson_input_dir_test_config, test_artifact_path)
        
        input_dir_artifact_path = os.path.join(test_artifact_path, config['input_dir'])

        test_geojsons = os.listdir(input_dir_artifact_path)
        testfile1 = os.path.join(input_dir_artifact_path, test_geojsons[0])
        testfile2 = os.path.join(input_dir_artifact_path, test_geojsons[1])

        # Open input GeoJSON and get stats
        try:
            with fiona.open(testfile1) as geojson1, fiona.open(testfile2) as geojson2:
                origin_num_features = len(list(geojson1)) + len(list(geojson2))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input geojson {0} or {1}. Make sure they're valid.".format(testfile1, testfile2))
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_mult_geojson_input_dir_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Check the output
        output_file = os.path.join(config['output_dir'], config['prefix'] + '.shp')
        try:
            with fiona.open(output_file) as shapefile:
                self.assertEqual(origin_num_features, len(list(shapefile)),
                                 "Feature count between the sum of input GeoJSONs {0} and {1} differs from that of output shapefile {2}. There is a problem with the conversion process."
                                 .format(testfile1, testfile2, output_file))
        except IOError:
            self.fail("Expected output geojson file {0} doesn't appear to have been created.".format(output_file))
        except fiona.errors.FionaValueError:
            self.fail("Bad output geojson file {0}.".format(output_file))
    """

    """
    # Tests creation of a shapefile from multiple shapefile inputs.
    # Alerts if output shapefile's number of features differs from the sum of the number of features in the input shapefiles.
    def test_shapefile_generation_multiple_shp(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'shapefiles_multiple_shp')
        config = self.parse_vector_config(self.shapefile_mult_shp_test_config, test_artifact_path)

        # Open input shapefiles and get stats
        try:
            with fiona.open(config['input_files'][0]) as shapefile1, fiona.open(config['input_files'][1]) as shapefile2, fiona.open(config['input_files'][2]) as shapefile3:
                origin_num_features = len(list(shapefile1)) + len(list(shapefile2)) + len(list(shapefile3))
        except fiona.errors.FionaValueError:
            self.fail("Can't open input shapefile {0}, {1}, or {2}. Make sure it's valid."
                      .format(config['input_files'][0], config['input_files'][1], config['input_files'][2]))
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.shapefile_mult_shp_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Check the output
        output_file = os.path.join(config['output_dir'], config['prefix'] + '.shp')
        try:
            with fiona.open(output_file) as shapefile:
                self.assertEqual(origin_num_features, len(list(shapefile)),
                                 "Feature count between input shapefiles {0}, {1}, {2} and output shapefile {3} differs. There is a problem with the conversion process."
                                 .format(config['input_files'][0], config['input_files'][1], config['input_files'][2], output_file))
        except IOError:
            self.fail("Expected output shapefile {0} doesn't appear to have been created.".format(output_file))
        except fiona.errors.FionaValueError:
            self.fail("Bad output shapefile {0}.".format(output_file))
    """

    """
    # Tests that tiles from the MRF are valid gzipped MVT tiles for when the source EPSG differs from the target EPSG.
    # Alerts if the overview tiles contain no features.
    def test_MVT_MRF_generation_diff_proj(self):
        # Process config file
        test_artifact_path = os.path.join(self.main_artifact_path, 'mvt_mrf_diff_proj')
        config = self.parse_vector_config(self.mrf_diff_proj_test_config, test_artifact_path)
        
        # Run vectorgen
        prevdir = os.getcwd()
        os.chdir(test_artifact_path)
        cmd = 'oe_vectorgen -c ' + self.mrf_diff_proj_test_config
        run_command(cmd, ignore_warnings=True)
        os.chdir(prevdir)

        # Get index of first, second-to-last, and last tile in MRF
        with open(os.path.join(config['output_dir'], config['prefix'] + '.idx'), 'rb') as idx:
            first_byte = idx.read(16)
            idx.seek(-32, 2)
            penultimate_byte = idx.read(16)
            last_byte = idx.read(16)
        top_tile_feature_count = 0
        for byte in (first_byte, penultimate_byte, last_byte):
            tile_buffer = io.BytesIO()
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
                top_tile_feature_count += len(tile[list(tile.keys())[0]]['features'])
        self.assertTrue(top_tile_feature_count, "Top two files contain no features -- MRF likely was not created correctly.")
    """

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
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
