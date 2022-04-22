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
# Tests for mod_mrf
#

import os
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
import random
from PIL import Image
import numpy as np
import io
import struct
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

Alias /test_mod_mrf {config_path}

<Directory {config_path}>
    MRF_ConfigurationFile {config_file_path}
    MRF_RegExp {alias}
</Directory>
"""

MOD_MRF_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
    PageSize {tile_size_x} {tile_size_y} 1 {bands}
    SkippedLevels {skipped_levels}
    IndexFile {idx_path}
    {data_config}
"""


def bulk_replace(source_str, replace_list):
    out_str = source_str
    for item in replace_list:
        out_str = out_str.replace(item[0], str(item[1]))
    return out_str


def make_random_image(size_x, size_y, image_type):
    img_ary = np.random.randint(256, size=(int(size_x), int(size_y), 3))
    return Image.fromarray(img_ary.astype('uint8'))


def make_randomized_mrf(size_x, size_y, tile_size, image_type, output_prefix,
                        output_path):
    # Make base randomized images
    pyramid = []
    last_size_x = size_x
    last_size_y = size_y
    while last_size_y / tile_size >= 1:
        pyramid.append(((last_size_x, last_size_y),
                        make_random_image(last_size_x, last_size_y,
                                          image_type)))
        last_size_x = last_size_x / 2
        last_size_y = last_size_y / 2

    # Write out tiles to an MRF
    mrf_idx = open(os.path.join(output_path, output_prefix + '.idx'), 'wb')
    mrf_ext = '.ppg' if image_type == 'png' else '.pjg'
    mrf_data = open(os.path.join(output_path, output_prefix + mrf_ext), 'wb')

    tile_store = {}
    tile_offset = 0

    z_levels = list(reversed(range(len(pyramid))))
    for idx, data in enumerate(pyramid):
        zidx = z_levels[idx]
        tile_store[zidx] = {}
        dims = data[0]
        image = data[1]
        for y in range(int(dims[1] / tile_size)):
            tile_store[zidx][y] = {}
            for x in range(int(dims[0] / tile_size)):
                tile_data = image.crop(
                    (x * tile_size, y * tile_size, x * tile_size + tile_size,
                     y * tile_size + tile_size))

                tile_io = io.BytesIO()
                tile_data.save(
                    tile_io,
                    format=image_type
                    if image_type.lower() != 'jpg' else 'jpeg')

                tile = tile_io.getvalue()

                # with open('{}.{}.{}.jpeg'.format(zidx, y, x), 'w+') as f:
                #     f.write(tile)

                mrf_data.write(tile)
                mrf_idx.write(struct.pack('!QQ', tile_offset, len(tile)))
                tile_offset += len(tile)
                tile_store[zidx][y][x] = tile_io

    mrf_idx.close()
    mrf_data.close()

    return tile_store


class TestModMrf(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Set test paths and install base Apache configuration
        self.config_file_prefix = 'test_mod_mrf'
        self.test_mod_mrf_config_dest_path = '/build/test/ci_tests/tmp/mod_mrf_test'

        make_dir_tree(self.test_mod_mrf_config_dest_path, ignore_existing=True)

        apache_config = bulk_replace(
            MOD_MRF_APACHE_TEMPLATE,
            [('{config_path}', self.test_mod_mrf_config_dest_path),
             ('{config_file_path}',
              os.path.join(self.test_mod_mrf_config_dest_path,
                           self.config_file_prefix + '.config')),
             ('{alias}', self.config_file_prefix)])

        self.apache_config_path = os.path.join(
            APACHE_CONFIG_DIR, self.config_file_prefix + '.conf')
        with open(self.apache_config_path, 'w+') as f:
            f.write(apache_config)

    def test_local_tile_request(self):
        # Build a randomized MRF and check that mod_mrf serves the expected tile.
        size_x = 4096
        size_y = 4096
        tile_size = 512
        image_type = 'jpeg'
        test_name = 'test_local_tile_request'

        # Build mod_mrf config and restart Apache
        idx_path = os.path.join(self.test_mod_mrf_config_dest_path,
                                test_name + '.idx')
        data_config = 'DataFile ' + os.path.join(
            self.test_mod_mrf_config_dest_path, test_name + '.pjg')

        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{idx_path}', idx_path), ('{data_config}', data_config),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])

        mod_mrf_config_path = os.path.join(self.test_mod_mrf_config_dest_path,
                                           self.config_file_prefix + '.config')
        with open(mod_mrf_config_path, 'w+') as f:
            f.write(mod_mrf_config)

        restart_apache()

        # Generate tiles and then test them against randomly-generated requests.
        tiles = make_randomized_mrf(size_x, size_y, tile_size, 'jpg',
                                    'test_local_tile_request',
                                    self.test_mod_mrf_config_dest_path)
        # Test all tiles against hash reference
        for z in range(len(tiles)):
            for y in range(len(tiles[z])):
                for x in range(len(tiles[z][y])):
                    ref_tile = tiles[z][y][x]
                    ref_tile.seek(0)
                    ref_hash = get_file_hash(ref_tile)

                    tile_url = 'http://localhost/{}/{}/{}/{}.{}'.format(
                        self.config_file_prefix, z, y, x, image_type)

                    errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
                        tile_url)
                    self.assertTrue(
                        check_tile_request(tile_url, ref_hash), errstring)

    @classmethod
    def tearDownClass(self):
        if not START_SERVER:
            os.remove(self.apache_config_path)
            shutil.rmtree(self.test_mod_mrf_config_dest_path)


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
