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
# Tests for oe_validate_palette.py
#

import subprocess
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
import os

SCRIPT_PATH = "/usr/bin/oe_validate_palette.py"

# Handles parsing the raw output of oe_validate_palette.py in the event of a failure.
# Returns a dictionary of the relevant results
def parse_failure_output(output, returncode):
    lines = output.split('\n')
    result_dict = { "returncode": returncode }
    for line in lines:
        if "Matched palette entries" in line:
            result_dict["Matched palette entries"] = int(line.split(':')[1])
        elif "Mismatched palette entries" in line:
            result_dict["Mismatched palette entries"] = int(line.split(':')[1])
        elif "Missing palette entries" in line:
            result_dict["Missing palette entries"] = int(line.split(':')[1])
        elif "Extra palette entries" in line:
            result_dict["Extra palette entries"] = int(line.split(': ')[1])
    return result_dict

# Takes dictionaries containing the expected and actual output values for validation failure.
# Returns a string 
def report_discrepencies(expected_out, actual_out):
    report_str = ""
    for key in expected_out:
        if expected_out[key] != actual_out.get(key):
            report_str += "- Expected {0}: {1}\n  Actual {0}: {2}\n".format(key,
                                                                            expected_out[key],
                                                                            actual_out.get(key, "NA (not listed in output)"))
    return report_str

# Runs oe_validate_palette.py for tests that intend for the validation to fail.
# Returns a string with the test failure details in the event that the validation doesn't fail correctly.
def run_failure_validation_test(cmd_lst, colormap_path, img_path, expected_out):
    try:
        subprocess.check_output(cmd_lst)
        fail_str = "oe_validate_palette.py incorrectly indicated that validation of {0} and {1} succeeded.".format(colormap_path, img_path)
    except subprocess.CalledProcessError as val_pal_except:
        fail_str_prefix = ("\noe_validate_palette.py correctly failed in validating {0} and {1},\n"
                            "but encountered the following problems:\n").format(colormap_path, img_path)
        val_pal_output = val_pal_except.output.decode("utf-8")
        result_out = parse_failure_output(val_pal_output, val_pal_except.returncode)
        fail_str = report_discrepencies(expected_out, result_out)
        if fail_str != "":
            fail_str = fail_str_prefix + fail_str
            fail_str += "\nThe following is the complete output of oe_validate_palette.py:\n\n{}".format(val_pal_output)
    return fail_str
            

class TestValidatePalette(unittest.TestCase):
    
    # Tests oe_validate_palette.py using a colormap with the corresponding image that matches the colormap.
    # Passes if the validation is successful.
    def test_validate_correct_palette(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/AIRS/AIRS_L2_SST_A_LL_v6_NRT_2019344.png")
        fail_str = ""
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path]
        try:
            subprocess.check_output(cmd_lst)
        except subprocess.CalledProcessError as val_pal_except:
            fail_str += "oe_validate_palette.py failed to correctly validate {0} and {1}\n".format(colormap_path, img_path)
            fail_str += "oe_validate_palette.py returned {} and produced the following output:\n\n".format(val_pal_except.returncode)
            fail_str += val_pal_except.output.decode("utf-8")

        self.assertTrue(fail_str == "", fail_str)

    # Tests oe_validate_palette.py using a colormap with the corresponding image that matches the colormap.
    # Uses the `-n` (`--no_index`) option.
    # Passes if the validation is successful.
    def test_validate_correct_palette_no_index(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/AIRS/AIRS_L2_SST_A_LL_v6_NRT_2019344.png")
        fail_str = ""
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-n']
        try:
            subprocess.check_output(cmd_lst)
        except subprocess.CalledProcessError as val_pal_except:
            fail_str += "oe_validate_palette.py failed to correctly validate {0} and {1}\n".format(colormap_path, img_path)
            fail_str += "oe_validate_palette.py returned {} and produced the following output:\n\n".format(val_pal_except.returncode)
            fail_str += val_pal_except.output.decode("utf-8")

        self.assertTrue(fail_str == "", fail_str)
    
    # Tests oe_validate_palette.py using a colormap with the corresponding image that matches the colormap.
    # Uses the `-x` (`--ignore_colors`) option.
    # Passes if the validation is successful.
    def test_validate_correct_palette_ignore_colors(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/AIRS/AIRS_L2_SST_A_LL_v6_NRT_2019344.png")
        ignored_colors = "146,111,169,255|145,114,160,255"
        fail_str = ""
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-x', ignored_colors]
        try:
            subprocess.check_output(cmd_lst)
        except subprocess.CalledProcessError as val_pal_except:
            fail_str += "oe_validate_palette.py failed to correctly validate {0} and {1}\n".format(colormap_path, img_path)
            fail_str += "oe_validate_palette.py returned {} and produced the following output:\n\n".format(val_pal_except.returncode)
            fail_str += val_pal_except.output.decode("utf-8")

        self.assertTrue(fail_str == "", fail_str)

    # Tests oe_validate_palette.py using a colormap with the corresponding image that matches the colormap.
    # Uses the `-f` (`--fill_value`) option.
    # Passes if the validation is successful.
    def test_validate_correct_palette_fill_value(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/AIRS/AIRS_L2_SST_A_LL_v6_NRT_2019344.png")
        fill_value = "146,111,169,255"
        fail_str = ""
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-f', fill_value]
        try:
            subprocess.check_output(cmd_lst)
        except subprocess.CalledProcessError as val_pal_except:
            fail_str += "oe_validate_palette.py failed to correctly validate {0} and {1}\n".format(colormap_path, img_path)
            fail_str += "oe_validate_palette.py returned {} and produced the following output:\n\n".format(val_pal_except.returncode)
            fail_str += val_pal_except.output.decode("utf-8")

        self.assertTrue(fail_str == "", fail_str)

    # Tests oe_validate_palette.py using a colormap with an image that doesn't match the colormap.
    # Passes if the validation fails and correct failure details are given.
    def test_validate_incorrect_palette(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/MYR4ODLOLLDY/MYR4ODLOLLDY_global_2014277_10km.png")
        expected_out = {
            "returncode": 3,
            "Matched palette entries": 0,
            "Mismatched palette entries": 22,
            "Missing palette entries": 231,
            "Extra palette entries": 0
        }
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path]
        fail_str = run_failure_validation_test(cmd_lst, colormap_path, img_path, expected_out)
        self.assertTrue(fail_str == "", fail_str)
    
    # Tests oe_validate_palette.py using a colormap with an image that doesn't match the colormap.
    # Uses the `-n` (`--no_index`) option.
    # Passes if the validation fails and correct failure details are given.
    def test_validate_incorrect_palette_no_index(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/MYR4ODLOLLDY/MYR4ODLOLLDY_global_2014277_10km.png")
        expected_out = {
            "returncode": 3,
            "Matched palette entries": 0,
            "Missing palette entries": 253,
            "Extra palette entries": 21
        }
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-n']
        fail_str = run_failure_validation_test(cmd_lst, colormap_path, img_path, expected_out)
        self.assertTrue(fail_str == "", fail_str)
    
    # Tests oe_validate_palette.py using a colormap with an image that doesn't match the colormap.
    # Uses the `-x` (`--ignore_colors`) option.
    # Passes if the validation fails and correct failure details are given.
    def test_validate_incorrect_palette_ignore_colors(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/MYR4ODLOLLDY/MYR4ODLOLLDY_global_2014277_10km.png")
        ignored_colors = "146,111,169,255|145,114,160,255|220,220,255,0"
        expected_out = {
            "returncode": 3,
            "Matched palette entries": 0,
            "Mismatched palette entries": 21,
            "Missing palette entries": 231,
            "Extra palette entries": 0
        }
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-x', ignored_colors]
        fail_str = run_failure_validation_test(cmd_lst, colormap_path, img_path, expected_out)
        self.assertTrue(fail_str == "", fail_str)

    # Tests oe_validate_palette.py using a colormap with an image that doesn't match the colormap.
    # Uses the `-f` (`--fill_value`) option.
    # Passes if the validation fails and correct failure details are given.
    def test_validate_incorrect_palette_fill_value(self):
        colormap_path = os.path.join(os.getcwd(), "mrfgen_files/colormaps/AIRS_Temperature.xml")
        img_path = os.path.join(os.getcwd(), "mrfgen_files/MYR4ODLOLLDY/MYR4ODLOLLDY_global_2014277_10km.png")
        fill_val = "145,114,160,255"
        expected_out = {
            "returncode": 3,
            "Matched palette entries": 0,
            "Mismatched palette entries": 253,
            "Missing palette entries": 0,
            "Extra palette entries": 3
        }
        cmd_lst = [SCRIPT_PATH, '-c', colormap_path, '-i', img_path, '-f', fill_val]
        fail_str = run_failure_validation_test(cmd_lst, colormap_path, img_path, expected_out)
        self.assertTrue(fail_str == "", fail_str)
        
if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_validate_palette_results.xml',
        help='Specify XML output file (default is test_validate_palette_results.xml')
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Load test configuration into Apache and quit (for debugging)')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestValidatePalette.setUpClass()
        sys.exit(
            'Apache has been loaded with the test configuration. No tests run.'
        )

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
