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

#
# Tests for mod_reproject
#

import os
import sys
import unittest
import xmlrunner
from optparse import OptionParser
from oe_test_utils import restart_apache, make_dir_tree, get_file_hash, check_tile_request
import shutil

APACHE_CONFIG_DIR = "/etc/httpd/conf.d"

START_SERVER = False

MOD_MRF_APACHE_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !receive_module>
    LoadModule receive_module modules/mod_receive.so
</IfModule>

<Directory /build/test/ci_tests/tmp>
 Require all granted
</Directory>

Alias /{alias} {config_path}

<Directory {config_path}>
    MRF_ConfigurationFile {config_file_path}
    MRF_RegExp {alias}
</Directory>
"""

MOD_REPROJECT_APACHE_TEMPLATE = """<IfModule !retile_module>
   LoadModule retile_module modules/mod_retile.so
</IfModule>

Alias /{alias} {config_path}

<Directory {config_path}>
    Retile_ConfigurationFiles {src_config} {dest_config}
    Retile_RegExp {alias}
    Retile_Source /{source_path} {source_postfix}
</Directory>
"""

MOD_MRF_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
    PageSize {tile_size_x} {tile_size_y} 1 {bands}
    SkippedLevels {skipped_levels}
    IndexFile {idx_path}
    {data_config}
"""

MOD_REPROJECT_SRC_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
    PageSize {tile_size_x} {tile_size_y} 1 {bands}
    SkippedLevels {skipped_levels}
    Projection {projection}
    BoundingBox {bbox}
"""

MOD_REPROJECT_DEST_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
    Nearest Off
    PageSize {tile_size_x} {tile_size_y} 1 {bands}
    SkippedLevels {skipped_levels}
    Projection {projection}
    BoundingBox {bbox}
    MimeType {mime}    
    Oversample On
    ExtraLevels 3
"""

TILE_REF = {
    0: {
        0: {
            0: '0014655736ea54b495da5c7d657a862d'
        }
    },
    1: {
        0: {
            0: '40415cd98d46400e7b3f82dd2c250733',
            1: '6e3a2a421583a306799d5dfdff73478e'
        },
        1: {
            0: '455c163421921a1c4aad679a0b5f8e56',
            1: 'af5c4debd77f8f8dc9c52f06724b9399'
        }
    },
    2: {
        0: {
            0: '2527c92519b99e274ef54622611754c9',
            1: 'e17c5025c91091cd7f0e495800bf3b8d',
            2: 'ca0d6a027f7f2bdecb8d33ef58301f42',
            3: '502c2a00f92b866b360974731c596979'
        },
        1: {
            0: '1e3efd497d499d10821b31a143e3d16e',
            1: 'c1f695120d0903e620431e2b3d1ff91d',
            2: '666c311784ba3e5068cbdf99326bfcbb',
            3: '25993232aac71da8b51c85a76149f3c5'
        },
        2: {
            0: 'd71419fd8e1d161f6ea1216b1803e601',
            1: '63f91c97bbe30fc651f2fdb8f294020b',
            2: '547d143f25c777f71aa5a0bde281d001',
            3: 'fe8f61536fadd4f74f103e0ce3203725'
        },
        3: {
            0: '285b0d8acaf0530a6d37fcf0268059bd',
            1: '3b912639de2808c15dfb11e279e1efa4',
            2: 'df95fecb838d6cd1912b02c6f8f1dd56',
            3: 'b25641193263d7e4c99e224711f00966'
        }
    },
    3: {
        0: {
            0: 'dae04e9eaeeb99d7f5a992915eb73c81',
            1: 'ddbfb379a83dad59e55306c58a4ebf48',
            2: '13d58b71e37a4a114a2e3ee722ecac90',
            3: '5b264d6c4592a25e00f603f4db45f917',
            4: '069c8d261ac864ed29e6f6a940683441',
            5: '5ad03af395b32b554dabdcc4f354ad81',
            6: '1a108a5104310a0c13a3b1b0d56f847b',
            7: '25339fe6e82bee969bc3c611b57e8377'
        },
        1: {
            0: '1fac391af1c7b7cf6cfd0de102ad7146',
            1: 'a2a782a322872430c1ab89684ea0daab',
            2: 'd95a54b14177dedf1a5af16384186846',
            3: '681c9ea4cbb2656b8426e2745fe3a566',
            4: 'fe6a9cc6b932b2e22e878ea13fcdd6a9',
            5: '4a7951d7b3ae565c22aa292e0308ce3f',
            6: '18f8e1c956f95575f7488022ec787c91',
            7: '29e3110303d4a5203647cb4d21333392'
        },
        2: {
            0: '4ba7515706744b595527fb935c23c4f1',
            1: 'c506f42c1f65d3de56f1e1d2ce1957bc',
            2: 'f6ba6e6d90b76ee28c6fd634eed21bf9',
            3: '4f81e99980c350c506540d01e7bb969d',
            4: 'fa1f808ba80321a59fe6ccdb7f6f4c42',
            5: '7e850016ffaf7f20e0a45e4db52d012e',
            6: 'd7dbec52b6b250c5c8929a0c0fa5bd0d',
            7: '968a4cad1a406e6219bf527e56a9c7af'
        },
        3: {
            0: 'f53bc834485a28aff92fc6d287103103',
            1: '8effb39b8998aa95220f338a0016b493',
            2: '09824f11d6e4b1e115259cf259ac327a',
            3: 'c5bc2d4014a69e3c0ac3ddc8ef76c82d',
            4: '0ba21a5f76295f34b4a3344418ab9eac',
            5: 'a6a2e4fe9b06ac98a6066cf54e8e6cb0',
            6: 'eb2604e9d856f90a9247a46b27ebdb7b',
            7: '09a448089cd2d65810b38f4097d5c978'
        },
        4: {
            0: 'c4a438adbc00b5f7dc6d437f10784679',
            1: 'a78b37bbcfb2c4fdf3ca8c3ac7bf166e',
            2: 'c210cbb23943f5e61053985b69b3dcee',
            3: '228e8eb9fe7919a440231663b320b365',
            4: 'd4b8ed4954959900782b9dfc85bfae4d',
            5: '10d7f64424c12ce70649c030b854a55d',
            6: '1a1f8af2355818867776fb6e4b985c0d',
            7: '4505cc160f861de873ea02ca3db71b2e'
        },
        5: {
            0: 'c99accaa07a741cdf115479ab14e28d0',
            1: '4c809b7b1c4be344a72a3bbe7e93ee37',
            2: '596624b4e0e4aeb2c1a5927473dc654d',
            3: '72eb48e1cfd8424f08119d126f03a70f',
            4: '4c909ec9f3cce10b7f7a683636f64802',
            5: 'f1e58348a2f9586cff34a279a6571634',
            6: 'bc210e6ea7dd2639c669586ec79b0d34',
            7: '7eeaa310a8a100b944c716d170a85254'
        },
        6: {
            0: '67524acf383a6bc2374caf9f187226f1',
            1: 'e0be9257b04c3a2138d076a22dcd76f8',
            2: '523a6b2fd5484329b2dfc310c6f94386',
            3: 'ab5078c94f9a49c8b7e30a8d47036771',
            4: '936af61b78bbeb49df36c30e48140934',
            5: 'cd171105aa00592cd4ef6aea930837d4',
            6: '84229e160bd342810d94a67bdc0cb23d',
            7: '0864483f5eb81b70f161a0016bdc12ee'
        },
        7: {
            0: 'bf5002dae6e39e074b3f0baf04d46150',
            1: 'ad06e0b5f43f2e08cdeb3c3b26df46c7',
            2: '7da1f164196909c6f197a7dfbb070458',
            3: '3c30f3d835bcf873fae5a5ab003b2498',
            4: '0ad75570d1a6d2b150cb849a1758d8f5',
            5: '4d1d84910db32538b5854cd549d3fea0',
            6: 'ca42df03f1c0b34eb5e1cb4f30e6d993',
            7: 'b7bb9ee6b090f13783b8847413c21fa6'
        }
    }
}


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], str(item[1]))
    return out_str


class TestModReproject(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Set test paths and install base Apache configuration
        self.src_config_file_prefix = 'test_mod_reproject_src'
        self.test_mod_reproject_src_config_dest_path = '/build/test/ci_tests/tmp/mod_reproject_test_src'

        make_dir_tree(
            self.test_mod_reproject_src_config_dest_path, ignore_existing=True)

        # Add config for base imagery layer to be served by mod_reproject
        apache_config = bulk_replace(
            MOD_MRF_APACHE_TEMPLATE,
            [('{config_path}', self.test_mod_reproject_src_config_dest_path),
             ('{config_file_path}',
              os.path.join(self.test_mod_reproject_src_config_dest_path,
                           self.src_config_file_prefix + '.config')),
             ('{alias}', self.src_config_file_prefix)])

        self.mod_mrf_apache_config_path = os.path.join(
            APACHE_CONFIG_DIR, self.src_config_file_prefix + '.conf')
        with open(self.mod_mrf_apache_config_path, 'w+') as f:
            f.write(apache_config)

        # Add reproject config
        self.reproject_config_file_prefix = 'test_mod_reproject'
        self.test_mod_reproject_config_dest_path = '/build/test/ci_tests/tmp/mod_reproject_test'
        make_dir_tree(
            self.test_mod_reproject_config_dest_path, ignore_existing=True)

        self.reproj_src_config_path = os.path.join(
            self.test_mod_reproject_config_dest_path,
            self.reproject_config_file_prefix + '_src.config')
        self.reproj_dest_config_path = os.path.join(
            self.test_mod_reproject_config_dest_path,
            self.reproject_config_file_prefix + '_dest.config')

        apache_config = bulk_replace(
            MOD_REPROJECT_APACHE_TEMPLATE,
            [('{config_path}', self.test_mod_reproject_config_dest_path),
             ('{config_file_path}',
              os.path.join(self.test_mod_reproject_config_dest_path,
                           self.reproject_config_file_prefix + '.config')),
             ('{alias}', self.reproject_config_file_prefix),
             ('{src_config}', self.reproj_src_config_path),
             ('{source_path}', self.src_config_file_prefix),
             ('{source_postfix}', '.jpg'),
             ('{dest_config}', self.reproj_dest_config_path)])

        self.apache_config_path = os.path.join(
            APACHE_CONFIG_DIR, self.reproject_config_file_prefix + '.conf')
        with open(self.apache_config_path, 'w+') as f:
            f.write(apache_config)

    def test_local_tile_request(self):
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = 'jpeg'
        test_name = 'test_local_tile_request'
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_reproject_test_data')

        # Build mod_mrf config and restart Apache
        idx_path = os.path.join(self.test_mod_reproject_src_config_dest_path,
                                test_name + '.idx')
        data_path = os.path.join(self.test_mod_reproject_src_config_dest_path,
                                 test_name + '.pjg')

        data_config = 'DataFile ' + data_path

        bands = {'png': 4, 'lerc': 1, 'lrc': 1}.get(image_type, 3)
        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', bands),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{idx_path}', idx_path), ('{data_config}', data_config),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])

        mod_mrf_config_path = os.path.join(
            self.test_mod_reproject_src_config_dest_path,
            self.src_config_file_prefix + '.config')
        with open(mod_mrf_config_path, 'w+') as f:
            f.write(mod_mrf_config)

        # Copy test test_imagery_path
        shutil.copy(
            os.path.join(test_imagery_path,
                         self.src_config_file_prefix + '.idx'), idx_path)
        shutil.copy(
            os.path.join(test_imagery_path,
                         self.src_config_file_prefix + '.pjg'), data_path)
        bands = {'png': 4, 'lerc': 1, 'lrc': 1}.get(image_type, 3)
        # Now configure the reproject stuff.
        mod_reproject_src_config = bulk_replace(
            MOD_REPROJECT_SRC_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', bands),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{skipped_levels}', '1'), ('{projection}', 'EPSG:4326'),
             ('{bbox}', '-180.0,-90.0,180.0,90.0')])

        with open(self.reproj_src_config_path, 'w+') as f:
            f.write(mod_reproject_src_config)

        reprojected_size = 2048
        reprojected_tile_size = 256
        bands = {'png': 4, 'lerc': 1, 'lrc': 1}.get(image_type, 3)
        mod_reproject_dest_config = bulk_replace(
            MOD_REPROJECT_DEST_CONFIG_TEMPLATE,
            [('{size_x}', reprojected_size), ('{size_y}', reprojected_size),
             ('{bands}', bands),
             ('{tile_size_x}', reprojected_tile_size),
             ('{tile_size_y}', reprojected_tile_size),
             ('{skipped_levels}', '0'), ('{projection}', 'EPSG:3857'),
             ('{bbox}',
              '-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
              ), ('{mime}', 'image/jpeg')])

        with open(self.reproj_dest_config_path, 'w+') as f:
            f.write(mod_reproject_dest_config)

        restart_apache()

        # Verify that the mod_mrf endpoint is set up and working
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        tile_url = 'http://localhost/{}/{}/{}/{}.{}'.format(
            self.src_config_file_prefix, 0, 0, 0, image_type)
        errstring = 'Error setting up mod_mrf: Tile at URL:{} was not the same as what was expected. Check that mod_mrf is working.'.format(
            tile_url)
        self.assertTrue(check_tile_request(tile_url, ref_hash), errstring)

        # Test all tiles against hash reference
        for z in range(len(TILE_REF)):
            for y in range(len(TILE_REF[z])):
                for x in range(len(TILE_REF[z][y])):
                    tile_url = 'http://localhost/{}/{}/{}/{}.{}'.format(
                        self.reproject_config_file_prefix, z, y, x, image_type)

                    ref_hash = TILE_REF[z][y][x]

                    errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
                        tile_url)
                    self.assertTrue(
                        check_tile_request(tile_url, ref_hash), errstring)

    @classmethod
    def tearDownClass(self):
        if not START_SERVER:
            os.remove(self.mod_mrf_apache_config_path)
            os.remove(self.apache_config_path)
            shutil.rmtree(self.test_mod_reproject_src_config_dest_path)
            shutil.rmtree(self.test_mod_reproject_config_dest_path)


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_mod_reproject_results.xml',
        help='Specify XML output file (default is test_mod_reproject_results.xml'
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
