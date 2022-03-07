#!/usr/bin/env python3

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

# Tests for RgbPngToPalPg.py

import os
import sys
import glob
import subprocess
import unittest2 as unittest
import xmlrunner
import filecmp
import shutil
from optparse import OptionParser
from oe_test_utils import make_dir_tree
import xml.etree.ElementTree as xmlet

def commonFunction(self, fileName):
    try:
        config_file=open(fileName, 'r')
    except Exception as e:
        print('Cannot open configuration file ' + filename + ': ' + e)
        sys.exit(-1)

    # Make XML tree.
    try:
        cfgTree = xmlet.parse(config_file)
    except Exception as e:
        print('Parse error for file ' + config_file + ': ' + e)
        sys.exit(-1)

    # Parse XML.
    for e in cfgTree.iter():
        if e.tag == 'input_img':
            inputImg = self.testDir + '/' + e.text
        if e.tag == 'colormap':
            colormap = self.testDir + '/' + e.text
        if e.tag == 'fill_value':
            fillValue = e.text
        if e.tag == 'verbose':
            verbose = e.text
        if e.tag == 'compare_img':
            compareImg = self.testDir + '/' + e.text
        if e.tag == 'compare_code':
            compareCode = e.text
        if e.tag == 'output_img':
            outputImg = self.testDir + '/' + e.text

    # Run RgbPngToPalPng.py
    cmd = '/usr/bin/python3 /usr/bin/RgbPngToPalPng.py -v -c ' + colormap + ' -i ' + inputImg + ' -o ' + outputImg + ' -f ' + str(fillValue)
    print(cmd)
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print('Subprocess error: ' + e)

    proc.wait()

    # Check output code.
    outputCode = str(proc.returncode)
    print('Process: ' + fileName + ' code: ' + outputCode)

    # Test code.
    if DEBUG:
        print('Compare: ' + outputCode + ' to ' + compareCode)
    self.assertEqual(outputCode, compareCode, "Code doesn't match for: " + fileName )
        
    # Test image.
    if os.path.exists(outputImg):
        if DEBUG:
            print("Compare: " + outputImg + " to " + compareImg)
        self.assertTrue(filecmp.cmp(outputImg, compareImg), "Image doesn't match for: " + fileName)

DEBUG = False
SAVE_RESULTS = False

class TestRgbToPal(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.testDir=os.getcwd()

        # Input configuration file directory.
        self.configPath = self.testDir + '/rgb_to_pal_files/config'

        # Output image directory.
        self.outputPath = self.testDir + '/rgb_to_pal_files/output'

        # Make outputPath directory.
        try: 
            make_dir_tree(self.outputPath)
        except Exception as e:
            print('Cannot make directory: ' + self.outputPath + ': ' + e)
            sys.exit(-1)

    def test_large_image(self):
        fileName = self.configPath + '/rgbtopal_test_config1.xml'
        commonFunction(self, fileName)
    def test_small_image(self):
        fileName = self.configPath + '/rgbtopal_test_config2.xml'
        commonFunction(self, fileName)
    def test_rgbapal_image(self):
        fileName = self.configPath + '/rgbtopal_test_config3.xml'
        commonFunction(self, fileName)
    def test_rgb_image_one_missing_color(self):
        fileName = self.configPath + '/rgbtopal_test_config4.xml'
        commonFunction(self, fileName)
    def test_small_image_one_missing_color(self):
        fileName = self.configPath + '/rgbtopal_test_config5.xml'
        commonFunction(self, fileName)
    def test_small_image_multiple_missing_colors(self):
        fileName = self.configPath + '/rgbtopal_test_config6.xml'
        commonFunction(self, fileName)
    def test_small_image_no_matching_color(self):
        fileName = self.configPath + '/rgbtopal_test_config7.xml'
        commonFunction(self, fileName)
    def test_small_image_mismatched_transparency(self):
        fileName = self.configPath + '/rgbtopal_test_config8.xml'
        commonFunction(self, fileName)
    def test_small_image_invalid_fill_value(self):
        fileName = self.configPath + '/rgbtopal_test_config9.xml'
        commonFunction(self, fileName)
    def test_geotiff_image(self):
        fileName = self.configPath + '/rgbtopal_test_config10.xml'
        commonFunction(self, fileName)

    @classmethod
    def tearDownClass(self):
        if not SAVE_RESULTS:
            shutil.rmtree(self.outputPath)
        else:
            print("Outputs in : " + self.outputPath)

if __name__ == '__main__':

    print('Start test_rgb_to_pal.')

    tests = {
        'rgb_to_pal': TestRgbToPal
    }

    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='result', help='Result file')
    (options, args) = parser.parse_args()

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    [suite.addTests(loader.loadTestsFromTestCase(test_case)) for test_case in list(tests.values())]

    with open(options.result, 'wb') as f:
        print('Result in "{0}"'.format(options.result))
        test_runner = xmlrunner.XMLTestRunner(output=f)
        test_runner.run(suite)

    print('Complete test_rgb_to_pal.')

