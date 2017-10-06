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
# Tests for oe_configure_layer.py
#

import os
import sys
import unittest
from shutil import copy, rmtree
import datetime
import xmlrunner
import sqlite3
import itertools
from optparse import OptionParser
import re
import hashlib

import oe_test_utils as testutils
from oe_test_utils import make_dir_tree, find_string, get_layer_config, run_command, file_text_replace

DEBUG = False


class TestLayerConfig(unittest.TestCase):
    
    def setUp(self):
        # Get the path of the test data -- we assume that the script is in the parent dir of the data dir
        config_template_path = os.path.join(os.getcwd(), 'layer_config_files/config_templates')

        # This is that path that will be created to hold all our dummy files
        self.testfiles_path = os.path.join(os.getcwd(), 'oe_configure_layer_test_artifacts')

        # Make dir for the test config XML files and text-replace the templates with the proper location
        make_dir_tree(os.path.join(self.testfiles_path, 'conf'))
        for file in [f for f in os.listdir(config_template_path) if os.path.isfile(os.path.join(config_template_path, f))]:
            file_text_replace(os.path.join(config_template_path, file), os.path.join(self.testfiles_path, 'conf/' + file),
                              '{testfile_dir}', self.testfiles_path)

        # Set the location of the archive XML config file used by all tests
        self.archive_config = os.path.join(self.testfiles_path, 'conf/test_archive_config.xml')
        self.projection_config = os.path.join(self.testfiles_path, 'conf/projection.xml')
        self.tilematrixset_config = os.path.join(self.testfiles_path, 'conf/tilematrixsets.xml')
        self.badtilematrixset_config = os.path.join(self.testfiles_path, 'conf/badtilematrixsets.xml')

    def test_layer_config_default(self):
        # Set config files and reference hash for checking empty tile
        layer_config = os.path.join(self.testfiles_path, 'conf/test_default_behavior.xml')

        config = get_layer_config(layer_config, self.archive_config)

        # Make test dirs
        make_dir_tree(config['archive_location'])
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['legend_location'])

        # Copy colormaps
        colormap_location = config['colormap_locations'][0].firstChild.nodeValue
        colormap = config['colormaps'][0].firstChild.nodeValue
        make_dir_tree(colormap_location)
        copy(os.path.join(self.testfiles_path, 'conf/' + colormap), colormap_location)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)
   
        # Get all the test results before running the assertions. We do this because a failure ends the test and makes it impossible to clean up
        wmts_cache_xml = os.path.join(config['archive_basepath'], 'cache_all_wmts.xml')
        wmts_cache_file = os.path.join(config['archive_basepath'], 'cache_all_wmts.config')
        wmts_cache = os.path.isfile(wmts_cache_file)
        wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
        wmts_gc = os.path.isfile(os.path.join(config['wmts_gc_path'], 'getCapabilities.xml'))
        wmts_staging_file = os.path.join(config['wmts_staging_location'], config['prefix'] + '.xml')
        wmts_staging = os.path.isfile(wmts_staging_file)
        twms_cache_xml = os.path.join(config['archive_basepath'], 'cache_all_twms.xml')
        twms_cache_file = os.path.join(config['archive_basepath'], 'cache_all_twms.config')
        twms_cache = os.path.isfile(twms_cache_file)
        twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')
        twms_gc = os.path.isfile(twms_gc_file)
        twms_ts_file = os.path.join(config['twms_gc_path'], 'getTileService.xml')
        twms_ts = os.path.isfile(twms_ts_file)
        twms_staging_file = os.path.join(config['twms_staging_location'], config['prefix'] + '_gc.xml')
        twms_staging = os.path.isfile(twms_staging_file)
        twms_staging_gts_file = os.path.join(config['twms_staging_location'], config['prefix'] + '_gts.xml')
        twms_staging_gts = os.path.exists(twms_staging_gts_file)
        twms_staging_mrf_file = os.path.join(config['twms_staging_location'], config['prefix'] + '.mrf')
        twms_staging_mrf = os.path.exists(twms_staging_mrf_file)

        self.assertTrue(wmts_cache, "Default layer config test -- cache_all_wmts.config not created")
        self.assertTrue(wmts_gc, 'Default layer config test -- WMTS getCapabilities.xml does not exist')
        self.assertTrue(wmts_staging, 'Default layer config test -- staging file ' + wmts_staging_file + ' does not exist in WMTS staging area')
        self.assertTrue(twms_cache, 'Default layer config test -- cache_all_twms.config does not exist')
        self.assertTrue(twms_gc, 'Default layer config test -- TWMS getCapabilities.xml does not exist')
        self.assertTrue(twms_ts, 'Default layer config test -- TWMS getTileService.xml does not exist')
        self.assertTrue(twms_staging, 'Default layer config test -- staging file ' + twms_staging_file + ' does not exist in TWMS staging area')
        self.assertTrue(twms_staging_gts, 'Default layer config test -- staging file ' + twms_staging_gts_file + ' does not exist in TWMS staging area')
        self.assertTrue(twms_staging_mrf, 'Default layer config test -- staging file ' + twms_staging_mrf_file + ' does not exist in TWMS staging area')

        rmtree(config['legend_location'])
        rmtree(colormap_location)

        # String searches in the GC and config filenames
        search_string = '<ows:Identifier>' + config['identifier'] + '</ows:Identifier>'
        contains_layer = find_string(wmts_gc_file, search_string)
        os.remove(wmts_gc_file)
        os.remove(wmts_cache_xml)
        self.assertTrue(contains_layer, 'Default layer config test -- WMTS GetCapabilities does not contain layer')

        # Unicode weirdness in the binary configs necessitates running str() on the search strings
        search_string = str('SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=' + config['identifier'] + '&STYLE=(default)?&TILEMATRIXSET=EPSG3413_500m&TILEMATRIX=[0-9]*&TILEROW=[0-9]*&TILECOL=[0-9]*&FORMAT=image%2Fjpeg')
        contains_layer = find_string(wmts_cache_file, search_string)
        os.remove(wmts_cache_file)
        os.remove(twms_cache_xml)
        self.assertTrue(contains_layer, 'Default layer config test -- WMTS cache configuration does not contain layer')

        search_string = '<Name>' + config['identifier'] + '</Name>'
        contains_layer = find_string(twms_gc_file, search_string)
        os.remove(twms_gc_file)
        self.assertTrue(contains_layer, 'Default layer config test -- TWMS GetCapabilities does not contain layer')

        search_string = '<Name>' + config['tiled_group_name'] + '</Name>'
        contains_layer = find_string(twms_ts_file, search_string)
        os.remove(twms_ts_file)
        self.assertTrue(contains_layer, 'Default layer config test -- GetTileService does not contain layer')

        search_string = str('request=GetMap&layers=' + config['prefix'] + '&srs=EPSG:3413&format=image%2Fjpeg&styles=&width=512&height=512&bbox=[-,\.0-9+Ee]')
        contains_layer = find_string(twms_cache_file, search_string)
        os.remove(twms_cache_file)
        self.assertTrue(contains_layer, 'Default layer config test -- TWMS cache configuration does not contain layer')

        rmtree(config['archive_location'])
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])

    def test_layer_config_legends(self):
        # Set config files and reference hash for checking empty tile
        layer_config = os.path.join(self.testfiles_path, 'conf/test_legend_generation.xml')
        h_legend_ref_hash = '45223e22a673700d52f17c6658eac7e0'
        v_legend_ref_hash = 'cf9b632f30fbdbea466a489ecf363d76'

        config = get_layer_config(layer_config, self.archive_config)

        # Create legend, archive, and colormap dirs
        make_dir_tree(config['legend_location'])
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        make_dir_tree(config['archive_location'])
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])

        # Copy colormap to colormaps dir
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l{0} --skip_empty_tiles -g -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        """Get hashes of generated legends
        Note that matplotlib 1.5.1 generates unique ID values for style references, making each new file different.
        We strip these unique references before hashing the file so we can have a baseline for testing.
        """
        hasher = hashlib.md5()
        stripped_file = ''
        try:
            with open(os.path.join(config['legend_location'], config['prefix'] + '_H.svg'), 'r') as f:
                file_str = f.read()
                stripped_file = re.sub('(id="[#A-Za-z0-9]{11}")', '', file_str)
                stripped_file = re.sub('(xlink:href="[#A-Za-z0-9]{12}")', '', stripped_file)
                stripped_file = re.sub('(clip-path="url\([#A-Za-z0-9]{12}\)")', '', stripped_file)
                hasher.update(stripped_file)
                h_legend_hash = hasher.hexdigest()
        except OSError:
            raise ValueError('Horizontal legend not generated')
        try:
            with open(os.path.join(config['legend_location'], config['prefix'] + '_V.svg'), 'r') as f:
                file_str = f.read()
                stripped_file = re.sub('(id="[#A-Za-z0-9]{11}")', '', file_str)
                stripped_file = re.sub('(xlink:href="[#A-Za-z0-9]{12}")', '', stripped_file)
                stripped_file = re.sub('(clip-path="url\([#A-Za-z0-9]{12}\)")', '', stripped_file)
                hasher.update(stripped_file)
                v_legend_hash = hasher.hexdigest()
        except OSError:
            raise ValueError('Vertical legend not generated')

        # Cleanup
        rmtree(config['wmts_gc_path'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['legend_location'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])

        # Check if hashes are kosher
        self.assertEqual(h_legend_ref_hash, h_legend_hash, 'Horizontal legend generated does not match expected.')
        self.assertEqual(v_legend_ref_hash, v_legend_hash, 'Vertical legend generated does not match expected.')

    def test_versioned_colormaps(self):
        # Set locations of the config files we're using for this test
        layer_config = os.path.join(self.testfiles_path, 'conf/test_versioned_colormaps.xml')

        test_metadata = ('<ows:Metadata xlink:type="simple" xlink:role="http://earthdata.nasa.gov/gibs/metadata-type/colormap" xlink:href="http://localhost/colormaps/2.0/MODIS_Aqua_Aerosol-GIBS_2.0.xml" xlink:title="GIBS Color Map: Data - RGB Mapping"/>',
                         '<ows:Metadata xlink:type="simple" xlink:role="http://earthdata.nasa.gov/gibs/metadata-type/colormap/1.0" xlink:href="http://localhost/colormaps/1.0//MODIS_Aqua_Aerosol-GIBS_1.0.xml" xlink:title="GIBS Color Map: Data - RGB Mapping"/>'
                         '<ows:Metadata xlink:type="simple" xlink:role="http://earthdata.nasa.gov/gibs/metadata-type/colormap/2.0" xlink:href="http://localhost/colormaps/2.0//MODIS_Aqua_Aerosol-GIBS_2.0.xml" xlink:title="GIBS Color Map: Data - RGB Mapping"/>')
        
        config = get_layer_config(layer_config, self.archive_config)

        # Create colormap locations and copy colormap test file
        for location in config['colormap_locations']:
            make_dir_tree(location.firstChild.nodeValue)
            colormap = next(colormap.firstChild.nodeValue for colormap in config['colormaps'] if colormap.attributes['version'].value == location.attributes['version'].value)
            copy(os.path.join(self.testfiles_path, 'conf/' + colormap), location.firstChild.nodeValue)
            
        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} --skip_empty_tiles -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Check to see if all required metadata lines are in the getCapabilities
        gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
        metadata_pass = all(line for line in test_metadata if find_string(gc_file, line))
        self.assertTrue(metadata_pass, "Can't find all the proper versioned colormap metadata in the WMTS GetCapabilities file or GC file was not created.")

        # Cleanup
        [rmtree(path) for path in [path.firstChild.nodeValue for path in config['colormap_locations']]]
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])

    def test_empty_tile_generation(self):
        # Set config files and reference hash for checking empty tile
        layer_config = os.path.join(self.testfiles_path, 'conf/test_empty_tile_generation.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def test_continuous_period_detection(self):
        if DEBUG:
            print '\nTESTING CONTINUOUS PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_period_detection.xml')

        # Pick the start time for the dates that will be generated
        start_datetime = datetime.datetime(2014, 6, 1)

        # Set the various period units and lengths we'll be testing
        test_periods = (('days', 1), ('days', 5), ('months', 1), ('years', 1))

        config = get_layer_config(layer_config, self.archive_config)

        for period_unit, period_length in test_periods:
            # We test detection with both year and non-year directory setups
            for year_dir in (True, False):
                make_dir_tree(config['wmts_gc_path'])
                make_dir_tree(config['twms_gc_path'])
                make_dir_tree(config['wmts_staging_location'])
                make_dir_tree(config['twms_staging_location'])

                # Generate the empty test files
                test_dates = testutils.create_continuous_period_test_files(
                    config['archive_location'], period_unit, period_length, 5, start_datetime, prefix=config['prefix'], suffix='_.idx', make_year_dirs=year_dir)

                # Run layer config command for daily test days
                cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
                run_command(cmd, ignore_warnings=True)

                # Check to see if proper period in GetCapabilities
                wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
                twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

                # Build GC search string
                search_string = "<Value>" + test_dates[0].date().isoformat() + "/" + test_dates[-1].date().isoformat() + "/P{0}{1}</Value>".format(period_length, period_unit[0].upper())

                # Create debug output message
                if DEBUG:
                    print 'Testing with {0} {1} periods'.format(period_length, period_unit)
                    print 'Creating dates: '
                    for date in test_dates:
                        print date.isoformat()
                    print '\n' + 'Searching for string in GetCapabilities: ' + search_string

                # Check to see if string exists in the GC files
                wmts_error = "{0} {1} continuous period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
                test_result = find_string(wmts_gc_file, search_string)
                # twms_error = "{0} {1} period detection failed -- not found in TMWS GetCapabilities".format(period_length, period_unit)
                # self.assertTrue(find_string(twms_gc_file, search_string), twms_error)

                # Cleanup -- make sure to get rid of staging files
                rmtree(config['wmts_gc_path'])
                rmtree(config['wmts_staging_location'])
                rmtree(config['twms_staging_location'])
                rmtree(config['archive_location'])

                # Check result
                self.assertTrue(test_result, wmts_error)

    def test_intermittent_period_detection(self):
        if DEBUG:
            print '\nTESTING INTERMITTENT PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_period_detection.xml')

        # Pick the start time for the dates that will be generated
        start_datetime = datetime.datetime(2014, 6, 1)

        # Set the various period units and lengths we'll be testing
        test_periods = (('days', 1), ('days', 5), ('months', 1), ('years', 1))
        
        config = get_layer_config(layer_config, self.archive_config)

        for period_unit, period_length in test_periods:
            # We test detection with both year and non-year directory setups
            for year_dir in (True, False):
                make_dir_tree(config['wmts_gc_path'])
                make_dir_tree(config['twms_gc_path'])
                make_dir_tree(config['wmts_staging_location'])
                make_dir_tree(config['twms_staging_location'])

                # Generate the empty test files
                test_intervals = testutils.create_intermittent_period_test_files(
                    config['archive_location'], period_unit, period_length, 5, start_datetime, prefix=config['prefix'], make_year_dirs=year_dir)

                # Run layer config command for daily test days
                cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
                run_command(cmd, ignore_warnings=True)

                # Check to see if proper period in GetCapabilities
                wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
                twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

                # Build a list GC search strings
                search_strings = []
                for interval in test_intervals:
                    search_string = "<Value>" + interval[0].isoformat() + "/" + interval[-1].isoformat() + \
                        "/P{0}{1}</Value>".format(period_length, period_unit[0].upper())
                    search_strings.append(search_string)

                # Create debug output message
                if DEBUG:
                    print '\n' + 'Creating dates: '
                    dates = [date for date in interval for interval in test_intervals]
                    for date in dates:
                        print date.isoformat()
                    print '\n' + 'Searching for string(s) in GetCapabilities: '
                    for string in search_strings:
                        print search_string

                # Check to see if string exists in the GC files
                wmts_error = "{0} {1} intermittent period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
                # twms_error = "{0} {1} period detection failed -- not found in TMWS GetCapabilities".format(period_length, period_unit)
                # self.assertTrue(find_string(twms_gc_file, search_string), twms_error)

                search_result = all(string for string in search_strings if find_string(wmts_gc_file, string))
                
                # Cleanup -- make sure to get rid of staging files
                rmtree(config['wmts_gc_path'])
                rmtree(config['wmts_staging_location'])
                rmtree(config['twms_staging_location'])
                rmtree(config['archive_location'])

                # Check result
                self.assertTrue(search_result, wmts_error)

    def test_continuous_zlevel_period_detection(self):
        """
        Checks that the start and end periods of a z-level file are being correctly detected.
        """
        if DEBUG:
            print '\nTESTING CONTINUOUS Z-LEVEL PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_zindex_detect.xml')
        test_periods = (('minutes', 1), ('minutes', 5), ('hours', 1))
        start_datetime = datetime.datetime(2014, 6, 1, 12, 0, 0)
        start_datestring = str(start_datetime.year) + str(start_datetime.timetuple().tm_yday).zfill(3)

        config = get_layer_config(layer_config, self.archive_config)

        for period_unit, period_length in test_periods:
            # Make archive location dir
            archive_location = os.path.join(config['archive_location'], str(start_datetime.year))
            make_dir_tree(archive_location)

            # Make temp GC and archive directories and dummy MRF
            make_dir_tree(config['wmts_gc_path'])
            make_dir_tree(config['twms_gc_path'])
            make_dir_tree(config['wmts_staging_location'])
            make_dir_tree(config['twms_staging_location'])
            dummy_mrf = os.path.join(archive_location, config['prefix'] + start_datestring + '_.idx')
            open(dummy_mrf, 'a').close()

            # Create a ZDB file for seeding with the dates we're looking for
            zdb_path = os.path.join(archive_location, config['prefix'] + start_datestring + '_.zdb')
            conn = sqlite3.connect(zdb_path)

            # Create ZINDEX table, generate test dates, and populate ZDB file
            conn.execute('CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT);')
            test_dates = testutils.create_continuous_period_test_files(
                config['archive_location'], period_unit, period_length, 5, start_datetime, prefix=config['prefix'], no_files=True)

            # Create debug output message
            if DEBUG:
                print 'Testing with {0} {1} periods'.format(period_length, period_unit)
                print 'Creating ZDB with dates: '
                for date in test_dates:
                    print date.isoformat()

            # Populate the dates in the ZDB
            for i, date in enumerate(test_dates):
                z_key = date.strftime('%Y%m%d%H%M%S')
                sql = 'INSERT INTO ZINDEX(z, key_str) VALUES ({0}, {1})'.format(i, z_key)
                conn.execute(sql)
                conn.commit()

            # Close ZDB and run layer config
            conn.close()
            cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
            run_command(cmd, ignore_warnings=True)

            # Check to see if proper period in GetCapabilities
            wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
            twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

            # Build GC search string
            search_string = "<Value>" + test_dates[0].isoformat() + "Z/" + test_dates[-1].isoformat() + "Z</Value>"
            if DEBUG:
                print '\n' + 'Searching for string in GetCapabilities: ' + search_string

            # Check to see if string exists in the GC files
            error = "{0} {1} continuous z-level period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
            check_result = find_string(wmts_gc_file, search_string)

            # Cleanup
            conn.close()
            rmtree(config['wmts_gc_path'])
            rmtree(config['wmts_staging_location'])
            rmtree(config['twms_staging_location'])
            rmtree(config['archive_location'])
            
            # Check result
            self.assertTrue(check_result, error)

    def test_intermittent_zlevel_period_detection(self):
        """
        Checks that the start and end periods of a z-level file are being correctly detected.
        """
        if DEBUG:
            print '\nTESTING INTERMITTENT Z-LEVEL PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_zindex_detect.xml')
        test_periods = (('minutes', 1), ('minutes', 5), ('hours', 1))
        start_datetime = datetime.datetime(2014, 6, 1, 12, 0, 0)
        start_datestring = str(start_datetime.year) + str(start_datetime.timetuple().tm_yday).zfill(3)

        config = get_layer_config(layer_config, self.archive_config)

        for period_unit, period_length in test_periods:
            # Make archive location dir
            archive_location = os.path.join(config['archive_location'], str(start_datetime.year))
            make_dir_tree(archive_location)

            # Make temp GC and archive directories and dummy MRF
            make_dir_tree(config['wmts_gc_path'])
            make_dir_tree(config['twms_gc_path'])
            make_dir_tree(config['wmts_staging_location'])
            make_dir_tree(config['twms_staging_location'])
            dummy_mrf = os.path.join(archive_location, config['prefix'] + start_datestring + '_.mrf')
            open(dummy_mrf, 'a').close()

            # Create a ZDB file for seeding with the dates we're looking for
            zdb_path = os.path.join(archive_location, config['prefix'] + start_datestring + '_.zdb')
            conn = sqlite3.connect(zdb_path)

            # Create ZINDEX table, generate test dates, and populate ZDB file
            conn.execute('CREATE TABLE ZINDEX(z INTEGER PRIMARY KEY AUTOINCREMENT, key_str TEXT);')
            test_intervals = testutils.create_intermittent_period_test_files(
                config['archive_location'], period_unit, period_length, 5, start_datetime, prefix=config['prefix'], no_files=True)

            # Create debug output message (flatten array w/ itertools)
            if DEBUG:
                print 'Testing with {0} {1} periods'.format(period_length, period_unit)
                print 'Creating ZDB with dates: '
                for date in itertools.chain.from_iterable(test_intervals):
                    print date.isoformat()

            # Populate the dates in the ZDB (flatten array w/ itertools)
            for i, date in enumerate(itertools.chain.from_iterable(test_intervals)):
                z_key = date.strftime('%Y%m%d%H%M%S')
                sql = 'INSERT INTO ZINDEX(z, key_str) VALUES ({0}, {1})'.format(i, z_key)
                conn.execute(sql)
                conn.commit()

            # Close ZDB and run layer config
            conn.close()

            # Run layer config command
            cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
            run_command(cmd, ignore_warnings=True)

            # Check to see if proper period in GetCapabilities
            wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
            twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

            # Build GC search string
            search_strings = []
            for interval in test_intervals:
                search_string = "<Value>" + interval[0].isoformat() + "Z/" + interval[-1].isoformat() + "Z</Value>"
                search_strings.append(search_string)

            if DEBUG:
                print '\n' + 'Searching for strings in GetCapabilities: '
                for string in search_strings:
                    print string

            # Check to see if string exists in the GC files
            error = "{0} {1} intermittent z-level period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
            check_result = all(string for string in search_strings if find_string(wmts_gc_file, string))

            # Cleanup
            conn.close()
            rmtree(config['wmts_gc_path'])
            rmtree(config['wmts_staging_location'])
            rmtree(config['twms_staging_location'])
            rmtree(config['archive_location'])

            # Check result
            self.assertTrue(check_result, error)

    def test_legacy_subdaily_continuous(self):
        """
        Checks that layer config tool is correctly detecting the period and interval
        of subdaily layers that have the datetime in their filenames as opposed to
        the z-index.
        """
        if DEBUG:
            print '\nTESTING LEGACY SUBDAILY CONTINUOUS PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_subdaily_detect.xml')
        start_datetime = datetime.datetime(2014, 6, 1, 12)
        config = get_layer_config(layer_config, self.archive_config)
        
        # Set the various period units and lengths we'll be testing
        test_periods = (('hours', 1), ('hours', 5), ('minutes', 1), ('minutes', 5), ('seconds', 1), ('seconds', 5))

        # Test continuous periods
        for period_unit, period_length in test_periods:
            for year_dir in (True, False):
        
                # Make the GC dirs
                make_dir_tree(config['wmts_gc_path'])
                make_dir_tree(config['twms_gc_path'])
                make_dir_tree(config['wmts_staging_location'])
                make_dir_tree(config['twms_staging_location'])

                # Create a continuous set of period files for each time interval
                test_dates = testutils.create_continuous_period_test_files(config['archive_location'], period_unit, period_length, 4, start_datetime, prefix=config['prefix'], suffix='_.idx', make_year_dirs=year_dir)

                # Create debug output message
                if DEBUG:
                    print '\nTesting with {0} {1} periods'.format(period_length, period_unit)
                    print 'Creating legacy subdaily files with dates: '
                    for date in test_dates:
                        print date.isoformat()

                # Run layer config command
                cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
                run_command(cmd, ignore_warnings=True)

                # Check to see if proper period in GetCapabilities
                wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
                twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

                # Build search strings
                time_string = testutils.get_time_string(start_datetime, test_dates[-1], config)
                search_string = "<Value>" + time_string + "/PT{0}{1}</Value>".format(period_length, period_unit[0].upper())
                search_result = find_string(wmts_gc_file, search_string)

                if DEBUG:
                    print '\n' + 'Searching for string in GetCapabilities: ' + search_string

                # Cleanup
                rmtree(config['wmts_gc_path'])
                rmtree(config['wmts_staging_location'])
                rmtree(config['twms_staging_location'])
                rmtree(config['archive_location'])

                # Check result
                error = "{0} {1} continuous subdaily legacy period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
                self.assertTrue(search_result, error)

    def test_legacy_subdaily_intermittent(self):
        """
        Checks that layer config tool is correctly detecting the period and interval
        of subdaily layers that have the datetime in their filenames as opposed to
        the z-index.
        """
        if DEBUG:
            print '\nTESTING LEGACY SUBDAILY INTERMITTENT PERIOD DETECTION...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_subdaily_detect.xml')
        start_datetime = datetime.datetime(2014, 6, 1, 12)
        config = get_layer_config(layer_config, self.archive_config)
        
        # Set the various period units and lengths we'll be testing
        test_periods = (('hours', 1), ('hours', 5), ('minutes', 1), ('minutes', 5), ('seconds', 1), ('seconds', 5))

        # Test intermittent periods
        for period_unit, period_length in test_periods:
            for year_dir in (True, False):
                # Make the GC dirs
                make_dir_tree(config['wmts_gc_path'])
                make_dir_tree(config['twms_gc_path'])
                make_dir_tree(config['wmts_staging_location'])
                make_dir_tree(config['twms_staging_location'])


                test_intervals = testutils.create_intermittent_period_test_files(config['archive_location'], period_unit, period_length, 5, start_datetime, prefix=config['prefix'], make_year_dirs=year_dir)

                # Create debug output message (flatten array w/ itertools)
                if DEBUG:
                    print '\nTesting with {0} {1} periods'.format(period_length, period_unit)
                    print 'Creating legacy subdaily files with dates: '
                    for date in itertools.chain.from_iterable(test_intervals):
                        print date.isoformat()

                # Run layer config command
                cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
                run_command(cmd, ignore_warnings=True)

                # Check to see if proper period in GetCapabilities
                wmts_gc_file = os.path.join(config['wmts_gc_path'], 'getCapabilities.xml')
                twms_gc_file = os.path.join(config['twms_gc_path'], 'getCapabilities.xml')

                search_strings = []
                for interval in test_intervals:
                    time_string = testutils.get_time_string(interval[0], interval[-1], config)
                    search_string = "<Value>" + time_string + "/PT{0}{1}</Value>".format(period_length, period_unit[0].upper())
                    search_strings.append(search_string)

                if DEBUG:
                    print '\n' + 'Searching for strings in GetCapabilities: '
                    for string in search_strings:
                        print string

                # Check to see if string exists in the GC files
                error = "{0} {1} continuous subdaily legacy period detection failed -- not found in WMTS GetCapabilities".format(period_length, period_unit)
                check_result = all(string for string in search_strings if find_string(wmts_gc_file, string))

                # Cleanup
                rmtree(config['wmts_gc_path'])
                rmtree(config['wmts_staging_location'])
                rmtree(config['twms_staging_location'])
                rmtree(config['archive_location'])

                # Check result
                self.assertTrue(check_result, error)

    def test_vector_mapfile_style_inclusion(self):
        """
        Checks that the style snippet file indicated by <VectorStyleFile> is included
        in the output Mapfile.
        """
        if DEBUG:
            print '\nTESTING THAT VECTOR STYLES ARE INCLUDED IN GENERATED MAPFILE...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_vector_mapfile_style_inclusion.xml')
        config = get_layer_config(layer_config, self.archive_config)

        make_dir_tree(config['mapfile_staging_location'])
        cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4} -n -w -x --create_mapfile'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd, ignore_warnings=True)

        output_mapfile = os.path.join(config['mapfile_location'], config['mapfile_location_basename'] + '.map')

        self.assertTrue(os.path.exists(output_mapfile), "Vector Mapfile Style addition test -- mapfile not created")

        with open(output_mapfile) as mapfile:
            with open(os.path.join(self.testfiles_path, config['vector_style_file'])) as style_file:
                styles_exist = style_file.read() in mapfile.read()
        self.assertTrue(styles_exist, 'Style file stuff not found in output mapfile')

    def test_vector_data_type_inclusion(self):
        """
        Checks that the <VectorType> tag is being read and included in the output Mapfile.
        """
        if DEBUG:
            print '\nTESTING THAT VECTOR DATA TYPE IS INCLUDED IN GENERATED MAPFILE...'

        layer_config = os.path.join(self.testfiles_path, 'conf/test_vector_mapfile_type_inclusion.xml')
        config = get_layer_config(layer_config, self.archive_config)

        make_dir_tree(config['mapfile_staging_location'])
        cmd = 'oe_configure_layer -l {0} -z -e -a {1} -c {2} -p {3} -m {4} -n -w -x --create_mapfile'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd, ignore_warnings=True)

        output_mapfile = os.path.join(config['mapfile_location'], config['mapfile_location_basename'] + '.map')

        self.assertTrue(os.path.exists(output_mapfile), "Vector Mapfile Type addition test -- mapfile not created")

        with open(output_mapfile) as mapfile:
            mapfile_type_string = str('TYPE\t' + config['vector_type'].upper())
            type_string_exists = mapfile_type_string in mapfile.read()
        self.assertTrue(type_string_exists, 'Style file stuff not found in output mapfile')

    def test_invalid_config(self):
        # Set config files for invalid compression
        if DEBUG:
            print '\nTESTING INVALID COMPRESSION...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_invalid_compression.xml')
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify error
        if os.path.isfile('oe_configure_layer.err'):
            search_string = 'Compression> must be either JPEG, PNG, TIF, LERC, PBF, or MVT'
            contains_error = find_string('oe_configure_layer.err', search_string)


        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove('oe_configure_layer.err')

        # Check result
        self.assertTrue(contains_error, 'Invalid config test -- Unsupported compression type is specified')

        # Set config files for invalid file path
        if DEBUG:
            print '\nTESTING INVALID FILE PATH1...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_invalid_path1.xml')
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify error
        if os.path.isfile('oe_configure_layer.err'):
            search_string = 'No such file or directory'
            contains_error = find_string('oe_configure_layer.err', search_string)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove('oe_configure_layer.err')

        # Check result
        self.assertTrue(contains_error, 'Invalid config test -- Empty tile path does not exist')

        # Set config files for invalid file path
        if DEBUG:
            print '\nTESTING INVALID FILE PATH2...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_invalid_path2.xml')
        config = get_layer_config(layer_config, self.archive_config)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify error
        if os.path.isfile('oe_configure_layer.err'):
            search_string = 'Cannot read environment configuration file'
            contains_error = find_string('oe_configure_layer.err', search_string)

        # Cleanup -- make sure to get rid of staging files
        os.remove('oe_configure_layer.err')

        # Check result
        self.assertTrue(contains_error, 'Invalid config test -- Environment file path does not exist')

        # Set config files for invalid tilematrixset
        if DEBUG:
            print '\nTESTING INVALID TILEMATRIXSET...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_empty_tile_generation.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.badtilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def test_mrf_configuration(self):
        # Set config files and reference hash for checking empty tile
        if DEBUG:
            print '\nTESTING MRF CONFIGURATION...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_mrf_configuration.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def test_mrf_header(self):
        # Set config files and reference hash for checking empty tile
        if DEBUG:
            print '\nTESTING MRF HEADER...'
        layer_config = os.path.join(self.testfiles_path, 'conf/test_mrf_header.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def test_empty_tile_generation(self):
        # Set config files and reference hash for checking empty tile
        layer_config = os.path.join(self.testfiles_path, 'conf/test_empty_tile_generation.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def test_empty_tile_generation(self):
        # Set config files and reference hash for checking empty tile
        layer_config = os.path.join(self.testfiles_path, 'conf/test_empty_tile_generation.xml')
        ref_hash = "e6dc90abcc221cb2f473a0a489b604f6"
        config = get_layer_config(layer_config, self.archive_config)

        # Create paths for data and GC
        make_dir_tree(config['wmts_gc_path'])
        make_dir_tree(config['twms_gc_path'])
        make_dir_tree(config['archive_location'])

        # Copy the demo colormap
        make_dir_tree(config['colormap_locations'][0].firstChild.nodeValue)
        copy(os.path.join(self.testfiles_path, 'conf/' + config['colormaps'][0].firstChild.nodeValue), config['colormap_locations'][0].firstChild.nodeValue)

        # Run layer config tool
        cmd = 'oe_configure_layer -l {0} -a {1} -c {2} -p {3} -m {4}'.format(self.testfiles_path, self.archive_config, layer_config, self.projection_config, self.tilematrixset_config)
        run_command(cmd)

        # Verify hash
        with open(config['empty_tile'], 'r') as f:
            tile_hash = testutils.get_file_hash(f)

        # Cleanup -- make sure to get rid of staging files
        rmtree(config['wmts_gc_path'])
        rmtree(config['wmts_staging_location'])
        rmtree(config['twms_staging_location'])
        rmtree(config['colormap_locations'][0].firstChild.nodeValue)
        rmtree(config['archive_location'])
        os.remove(config['empty_tile'])

        # Check result
        self.assertEqual(ref_hash, tile_hash, "Generated empty tile does not match what's expected.")

    def tearDown(self):
        rmtree(self.testfiles_path)

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_layer_config_results.xml',
                      help='Specify XML output file (default is test_layer_config_results.xml')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Display verbose debugging messages')
    (options, args) = parser.parse_args()
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print '\nStoring test results in "{0}"'.format(options.outfile)
        unittest.main(
            testRunner=xmlrunner.XMLTestRunner(output=f)
        )
