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
# Tests for oe_generate_legend.py
#

import os
import sys
import unittest2 as unittest
import xmlrunner
import filecmp
import re
import hashlib
import json
import platform
from optparse import OptionParser
from oe_test_utils import mrfgen_run_command as run_command

DEBUG = False

oe_generate_legend = "oe_generate_legend.py"

class TestOELegends(unittest.TestCase):
    
    def setUp(self):
        self.colormaps_json = "colormaps.json"
        self.testdata_path = os.path.join(os.getcwd(), 'legends_test_data/')
        test_config = open(self.testdata_path + self.colormaps_json, "r")
        self.colormaps = eval(test_config.read())
        self.colormap_files = []
        test_config.close()
        for key, value in self.colormaps.items():
            colormap = self.testdata_path + key + ".xml"
            self.colormap_files.append(colormap)
            if os.path.isfile(colormap) == False:
                run_command("curl -o " + colormap + " " + value['colormap'])
            
    def test_generate_mrf(self):
        new_colormaps = self.colormaps.copy()
        hasher = hashlib.md5()
        for key, value in self.colormaps.items():
            colormap = self.testdata_path + key + ".xml"
            filename = os.path.splitext(colormap)[0]
            png_v = oe_generate_legend + " -c " + colormap + " -f png -r vertical -o " + filename + "_v.png"
            png_h = oe_generate_legend + " -c " + colormap + " -f png -r horizontal -o " + filename + "_h.png"
            svg_v = oe_generate_legend + " -c " + colormap + " -f svg -r vertical -o " + filename + "_v.svg"
            svg_h = oe_generate_legend + " -c " + colormap + " -f svg -r horizontal -o " + filename + "_h.svg"
            run_command(png_v)
            run_command(png_h)
            run_command(svg_v)
            run_command(svg_h)
            
            png_v_hash = value["png_v"]
            png_h_hash = value["png_h"]
            svg_v_hash = value["svg_v"]
            svg_h_hash = value["svg_h"]
            png_v_file = open(filename + "_v.png", "rb")
            png_h_file = open(filename + "_h.png", "rb")
            svg_v_file = open(filename + "_v.svg", "r")
            svg_v_file_str = ""
            svg_v_file_str = re.sub('(id="[#A-Za-z0-9]{11,15}")', '', svg_v_file.read())
            svg_v_file_str = re.sub('(xlink:href="[#A-Za-z0-9]{12}")', '', svg_v_file_str)
            svg_v_file_str = re.sub(r'(clip-path="url\([#A-Za-z0-9]{12}\)")', '', svg_v_file_str)

            svg_h_file = open(filename + "_h.svg", "r")
            svg_h_file_str = ""
            svg_h_file_str = re.sub('(id="[#A-Za-z0-9]{11,15}")', '', svg_h_file.read())
            svg_h_file_str = re.sub('(xlink:href="[#A-Za-z0-9]{12}")', '', svg_h_file_str)
            svg_h_file_str = re.sub(r'(clip-path="url\([#A-Za-z0-9]{12}\)")', '', svg_h_file_str)
            hasher.update(png_v_file.read())
            new_colormaps[key]["png_v"] = hasher.hexdigest()
            hasher.update(png_h_file.read())
            new_colormaps[key]["png_h"] = hasher.hexdigest()
            hasher.update(svg_v_file_str.encode('utf-8'))
            new_colormaps[key]["svg_v"] = hasher.hexdigest()
            hasher.update(svg_h_file_str.encode('utf-8'))
            new_colormaps[key]["svg_h"] = hasher.hexdigest()
            png_v_file.close()
            png_h_file.close()
            svg_v_file.close()
            svg_h_file.close()
            
            if png_v_hash != new_colormaps[key]["png_v"]:
                print('Vertical PNG legend for ' + key + ' does not match expected.')
            if png_h_hash != new_colormaps[key]["png_h"]:
                print('Horizontal PNG legend for ' + key + ' does not match expected.')
            if new_colormaps[key]["svg_v"] != svg_v_hash:
                print('Vertical SVG legend for ' + key + ' does not match expected.')
            if new_colormaps[key]["svg_h"] != svg_h_hash:
                print('Horizontal SVG legend for ' + key + ' does not match expected.')

        new_config = open(self.testdata_path + 'new_colormaps.json', 'w')
        json.dump(new_colormaps, new_config, sort_keys=True, indent=4)
        new_config.close()
        self.assertTrue(filecmp.cmp(self.testdata_path + self.colormaps_json, self.testdata_path + 'new_colormaps.json'), 'Inconsistent legends found')

    def tearDown(self):
        if filecmp.cmp(self.testdata_path + self.colormaps_json, self.testdata_path + 'new_colormaps.json'):
            os.remove(self.testdata_path + 'new_colormaps.json')
        else:
            f = open(self.testdata_path + 'new_colormaps.json', 'r')
            print("\nResults:\n")
            print(f.read())
            f.close()

if __name__ == '__main__':
    # Parse options before running tests
    test_help_text = 'Tests for legend generation'
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile', default='test_legends_results.xml',
                      help='Specify XML output file (default is test_legends_results.xml')
    parser.add_option('-d', '--debug', action='store_true', dest='debug', help='Display verbose debugging messages')
    (options, args) = parser.parse_args()
    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    main_test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    main_test_suite.addTests(test_loader.loadTestsFromTestCase(TestOELegends))

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        test_runner = xmlrunner.XMLTestRunner(output=f)
        test_runner.run(main_test_suite)
