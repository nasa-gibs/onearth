#!/usr/bin/env python3

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
# Tests for oe_generate_empty_tile.py
#

import filecmp
import json
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
from oe_test_utils import run_command
import os
import hashlib

SCRIPT_PATH = "/usr/bin/oe_generate_empty_tile.py"

class TestGenerateEmptyTile(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.testdata_path = os.path.join(os.getcwd(), 'empty_tiles_test_data/')
        self.colormaps_json = os.path.join(self.testdata_path, "colormaps.json")
        self.new_colormaps_json = os.path.join(self.testdata_path, "new_colormaps.json")
        test_config = open(self.colormaps_json, "r")
        self.colormaps = eval(test_config.read())
        self.colormap_files = []
        test_config.close()

    def test_generate_empty_tile(self):
        new_colormaps = self.colormaps.copy()
        hasher = hashlib.md5()
        for key, value in self.colormaps.items():
            colormap = os.path.join(self.testdata_path, value['colormap'])

            # download colormap if it is not stored locally
            if not os.path.isfile(colormap):
                colormap = "{}.xml".format(key)
                run_command("curl -o {0} {1}".format(colormap, value['colormap']))

            # run the command
            filename = "{}.png".format(os.path.join(self.testdata_path, key))
            cmd = "python3 {0} -c {1} -o {2} {3}".format(SCRIPT_PATH, colormap, filename, value["options"])
            run_command(cmd)
            run_command("gdalinfo {}".format(filename))
            # hash
            tile_hash = value["empty_tile_png"]
            tile_file = open(filename, "rb")
            hasher.update(tile_file.read())
            new_colormaps[key]["empty_tile_png"] = hasher.hexdigest()
            tile_file.close()

            if tile_hash != new_colormaps[key]["empty_tile_png"]:
                print("Empty tile generated for test {0} does not match expected".format(key))
        
        new_config = open(self.new_colormaps_json, "w")
        json.dump(new_colormaps, new_config, sort_keys=True, indent=4)
        new_config.close()
        self.assertTrue(filecmp.cmp(self.colormaps_json, self.new_colormaps_json), "Inconsistent empty tiles found")
    
    @classmethod
    def tearDownClass(self):
        if filecmp.cmp(self.colormaps_json, self.new_colormaps_json):
            os.remove(self.new_colormaps_json)
        else:
            f = open(self.new_colormaps_json, 'r')
            print("\nResults:\n")
            print(f.read())
            f.close()

if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_generate_empty_tile_results.xml',
        help='Specify XML output file (default is test_generate_empty_tile_results.xml')
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Load test configuration into Apache and quit (for debugging)')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestGenerateEmptyTile.setUpClass()
        sys.exit(
            'Apache has been loaded with the test configuration. No tests run.'
        )

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
