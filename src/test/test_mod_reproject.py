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
import unittest2 as unittest
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
            0: '5f7056b7b8c98fa736231364f4058859'
        }
    },
    1: {
        0: {
            0: '1af170cdf1f7e29f8a595b392a24dc97',
            1: '3208e7745f7323a38d05d5a53ae5124b'
        },
        1: {
            0: '1b151324b1079c362786283d2170aa7e',
            1: '015a227e52a8d50b4ed54d2b14f4c67d'
        }
    },
    2: {
        0: {
            0: '8de85756af92a3e3fa8c997d208c59db',
            1: 'df5a72b66d02e797dbda12f5899ad8f9',
            2: '7791a01e047ebbe71a43167761975824',
            3: 'd3fa6c2849dd58884faf6625098b0f01'
        },
        1: {
            0: 'bea9f3b7d6c74200be0a59ff05f9b2a1',
            1: 'cf1959fd14e658e75ed12f107f005147',
            2: '228cdb6d42ca752279adfe267ea178d3',
            3: '78e3dd6084f74fdf06901a14c14ba19f'
        },
        2: {
            0: '8cf1b00f3bbaf19eea5023b65f672385',
            1: 'd5c7d591a9c1074c6dcc50e6c8a97844',
            2: '99a139cbd3d3a08d7094afd176c39c0e',
            3: '5645b1e0be0757b9f390c7a65bb8a295'
        },
        3: {
            0: 'a9c735589d1460558fb1ec576ff691a3',
            1: '4358188d6b274c9e2b806bdf49f590bf',
            2: 'eae5e32cdd508a3876f296cd07185a49',
            3: '5efa21b5c8f76f41cfa8a62ce24fcb04'
        }
    },
    3: {
        0: {
            0: 'a1d0cfaaedfcb8d1961437d6d76b36c2',
            1: '11e991ae67b71c0191f847c966010ed3',
            2: '5c90d660d218ea250b4b2b9a0af3df57',
            3: '5f8aed249a57d9c1cdb69ccd735bbea1',
            4: 'c6817ad226c09fceea25b5ac6975e922',
            5: '2319c7adce7b80e1712916eb55d5e14a',
            6: '44e0628006805898aa5b199a8d9d6763',
            7: '2190d818b401ad9322017ef98e7e6df8'
        },
        1: {
            0: '9fe0523963b98cea21f52ad3b04e4b68',
            1: '670a4a2c4511aa7dcb830907302c2f8f',
            2: '750c725a90a80a9be6ab8104b2a0b7b5',
            3: 'c2fe267497806c057932f6d1ef4ef1fe',
            4: 'e09130069c364a106915ebb37ad76685',
            5: '4990766aace05b2a90d1798c10c15c94',
            6: 'dde74eb535a0042450893db518c3cc2b',
            7: '7a50c24bf10e27acf0f523b8a3aefdfc'
        },
        2: {
            0: '0ce5ff3f2ddce554d614fd8538364766',
            1: 'b2cd4d7daea7c055b191bad602e64075',
            2: 'd49abaeeeff542e51f8b6c807b8a5b48',
            3: '65d7b5b1059e59bdb815a8a0048b6ce4',
            4: 'f118bff09f9350a76dec4a4b6414a628',
            5: '97c4f920f3a7dd4762c8728d13bdc3e5',
            6: 'c5baf2bf89bf4bb6ec08aabb02d140df',
            7: 'afec3d8757a41f0652de35551da57e0d'
        },
        3: {
            0: '06b00da9b3aca40db86af0803141a1d5',
            1: 'e9f06bb7ea5b2db749c22a5e974e96fb',
            2: 'a9b9834dc0ec65dc6c35f26b61c2e6a9',
            3: 'c5a68b04aed3f4447996a29f24ec279e',
            4: '478901ac3038249f6d017f7ccf665bd1',
            5: '06d85ed3b76da2df4fa64e4ab52db816',
            6: '8bfdbcbe5d167fd2fcf900e15080cc20',
            7: '7c685ee561a2d42d1cacc665fe6ea711'
        },
        4: {
            0: 'd2b493ad9484ebe4b50babd7937e2105',
            1: 'dea08ef8686b9783cd79b79b361c7dbd',
            2: 'b5fce883b0f812a6b436713c53ab9cd7',
            3: 'c2bde3ad67004cea728af3ce8b0cedf3',
            4: '6617a26e02dec80fd15230aa1cfdb83c',
            5: 'ee14b7c910bc7766d6fed672dc0d2d73',
            6: 'fb5f5c8fe1ece02e21dd1b85c5e913ef',
            7: '188299db721809096dccec94be50dc5c'
        },
        5: {
            0: '400ecd853db0fa5e72baa7cde406d532',
            1: 'a53cf6e7d92190fc6626874b700753c5',
            2: 'fa9a4afd82fbb6adb1d72fc26a8a3a27',
            3: '304e5e08e11549eb5c61adb58468d65a',
            4: '38c735c094c387af4811db59aa653bbd',
            5: 'cb4b90ed0e9ddad9420613887c435a06',
            6: '64a72d44670805716d99b402a51cc91d',
            7: '681365328983749c836d5740c91b66de'
        },
        6: {
            0: '271b7f83a557bfc6db2aab0b80f92220',
            1: '84f5d7ccecc73b6b2e4f30f5cc01de5d',
            2: 'a2d36cb92b4593824227b6fc718d6b47',
            3: '17d554bf7cdc53b59f28b7c13b5d6107',
            4: 'fbf81484b14577dea0941dc791ed935d',
            5: 'e774c7bcb1bbddef65c46dca93c9c441',
            6: 'ccfec62798e131b7acc3601b40258cd6',
            7: '6191ddbc86403f496446f65a1718fd8a'
        },
        7: {
            0: '32974802f6f41d9d2b5c0e57897c7e79',
            1: '8cbaa0d5253713f8e859d6cbad08a62e',
            2: '4bb77b2f7701c8e14217f90aae82a9ff',
            3: 'e845b8a47cf24a8dd688fa625250cd5e',
            4: 'c5c6bc985657e1792fcee8fd10d44152',
            5: 'a3fe65cec2e370b66c869cc0e905121a',
            6: '6ae69b91722fee02b99696318767c52d',
            7: '448f58361a1d4a7120fd8ed262930d6b'
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

        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
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

        # Now configure the reproject stuff.
        mod_reproject_src_config = bulk_replace(
            MOD_REPROJECT_SRC_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{skipped_levels}', '1'), ('{projection}', 'EPSG:4326'),
             ('{bbox}', '-180.0,-90.0,180.0,90.0')])

        with open(self.reproj_src_config_path, 'w+') as f:
            f.write(mod_reproject_src_config)

        reprojected_size = 2048
        reprojected_tile_size = 256
        mod_reproject_dest_config = bulk_replace(
            MOD_REPROJECT_DEST_CONFIG_TEMPLATE,
            [('{size_x}', reprojected_size), ('{size_y}', reprojected_size),
             ('{bands}', 4 if image_type == 'png' else 3),
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
