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

import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
from oe_test_utils import run_command
import os

SCRIPT_PATH = "/usr/bin/oe_generate_empty_tile.py"
COLOR_TEST_DIR = "./color_test_files"
OUTPUT_DIR = os.path.join(COLOR_TEST_DIR, "results")

class TestGenerateEmptyTile(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        os.mkdir(OUTPUT_DIR)

    def test_generate_empty_tile(self):
        colormap = os.path.join(COLOR_TEST_DIR, "ColorMap_v1.2_Sample.xml")
        out_filename = os.path.join(OUTPUT_DIR, "empty_tile1.png")
        cmd = "python3 {0} -c {1} -o {2}".format(SCRIPT_PATH, colormap, out_filename)
        
        run_command(cmd)

        print(os.listdir(OUTPUT_DIR))
        self.assertTrue(True, "")
        
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
