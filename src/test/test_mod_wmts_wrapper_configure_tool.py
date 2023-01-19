import os
import sys
import subprocess
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
from oe_test_utils import run_command


class TestModWmtsWrapperConfigureTool(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.test_data_path = os.path.join(
            os.getcwd(), 'mod_wmts_wrapper_configure_tool_test_data')

    def cleanup_configure_tool_stdout(self, output):
        configs = output.split(" layer config written to: ")
        configs_dict = {
            "WTMS": [],
            "TWMS": [],
            "Apache": [],
        }
        # remove the odd man out
        current_entry_key = configs[0].split("\n")[1]
        del configs[0]
        current_entry_value = ""
        for i in configs:
            split_str = i.split("\n\n")
            current_entry_value = split_str[0]
            configs_dict[current_entry_key].append(current_entry_value)
            current_entry_key = split_str[1]
            if "Apache" in i:
                configs_dict["Apache"].append(
                    split_str[1].split("Apache config written to ")[1])
                break
        return configs_dict

    def test_modwmtswrapperconfiguretool(self):
        stdout = run_command(
            f"python3.6 /bin/oe2_wmts_configure.py {self.test_data_path}/test_endpoint.yaml"
        )
        configs = self.cleanup_configure_tool_stdout(stdout)
        for type in configs:
            for config in configs[type]:
                file_name = "_".join(config.split("/")[1:])
                with open(f"{self.test_data_path}/configs/{type.lower()}/{file_name}", "r") as conf_file, open(f"{config}", "r") as gen_file:
                    conf_str = conf_file.read()
                    gen_str = gen_file.read()

                    split_conf_str = conf_str.split("\n")
                    split_conf_str.remove("")
                    split_gen_str = gen_str.split("\n")
                    split_gen_str.remove("")
                    
                    for i in range(0, len(split_conf_str)):
                        try:
                            self.assertEqual(split_gen_str[i], split_conf_str[i],
                                        f"{config} == {file_name}")
                        except Exception as e:
                            print(e)
                    else:
                        self.assertEqual(conf_str, gen_str, f"{config} == {file_name}")


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_mod_mrf_results.xml',
        help='Specify XML output file (default is test_mod_mrf_results.xml'
    )

    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Start server but do not clean up')
    (options, args) = parser.parse_args()

    START_SERVER = options.start_server

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
