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
"""
Test suite for mod_wmts_wrapper.
"""

import os
import sys
import unittest2 as unittest
import xmlrunner
from oe_test_utils import file_text_replace, restart_apache, test_wmts_error, make_dir_tree, check_tile_request, redis_running, seed_redis_data, seed_redis_best_data, remove_redis_layer, bulk_replace, check_response_code, get_url, check_layer_headers
from optparse import OptionParser
import shutil
from subprocess import Popen, PIPE
import redis
import requests
import time

base_url = 'http://localhost'
apache_conf_dir = '/etc/httpd/conf.d'

BASE_APACHE_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !receive_module>
    LoadModule receive_module modules/mod_receive.so
</IfModule>

<IfModule !retile_module>
    LoadModule retile_module modules/mod_retile.so
</IfModule>

<IfModule !wmts_wrapper_module>
    LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<Directory /build/test/ci_tests/tmp>
 Require all granted
</Directory>

Alias /{alias} {endpoint_path}
Alias /{reproj_alias} {reproj_endpoint_path}

<Directory {endpoint_path}>
    WMTSWrapperRole root
</Directory>

<Directory {reproj_endpoint_path}>
    WMTSWrapperRole root
</Directory>
"""

MOD_MRF_NODATE_APACHE_TEMPLATE = """<Directory {endpoint_path}/{layer_name}>
    WMTSWrapperRole layer
    WMTSWrapperMimeType image/jpeg
</Directory>

<Directory {endpoint_path}/{layer_name}/default>
    WMTSWrapperRole style
</Directory>

<Directory {endpoint_path}/{layer_name}/default/{tilematrixset}>
    WMTSWrapperRole tilematrixset
    MRF_ConfigurationFile {config_file_path}
    MRF_RegExp {alias}
</Directory>
"""

MOD_MRF_DATE_APACHE_TEMPLATE = """<Directory {endpoint_path}/{layer_name}>
    WMTSWrapperRole layer
    WMTSWrapperMimeType image/jpeg
</Directory>

<Directory {endpoint_path}/{layer_name}/default>
    WMTSWrapperRole style
    WMTSWrapperEnableTime On
    WMTSWrapperTimeLookupUri /date_service/date_service
</Directory>

<Directory {endpoint_path}/{layer_name}/default/{tilematrixset}>
    WMTSWrapperRole tilematrixset
    WMTSWrapperEnableYearDir {year_dir}
    WMTSWrapperLayerAlias {layer_name}
    MRF_ConfigurationFile {config_file_path}
    MRF_RegExp {layer_name}
</Directory>
"""

MOD_REPROJECT_NODATE_APACHE_TEMPLATE = """<Directory {endpoint_path}/{layer_name}>
    WMTSWrapperRole layer
    WMTSWrapperMimeType image/jpeg
</Directory>

<Directory {endpoint_path}/{layer_name}/default>
    WMTSWrapperRole style
</Directory>

<Directory {endpoint_path}/{layer_name}/default/{tilematrixset}>
    WMTSWrapperRole tilematrixset
    Retile_ConfigurationFiles {src_config} {dest_config}
    Retile_RegExp {layer_name}
    Retile_Source {src_path} {src_postfix}
</Directory>
"""

MOD_REPROJECT_DATE_APACHE_TEMPLATE = """<Directory {endpoint_path}/{layer_name}>
    WMTSWrapperRole layer
    WMTSWrapperMimeType image/jpeg
</Directory>

<Directory {endpoint_path}/{layer_name}/default>
    WMTSWrapperEnableTime On
    WMTSWrapperTimeLookupUri /date_service/date_service
    WMTSWrapperRole style
</Directory>

<Directory {endpoint_path}/{layer_name}/default/{tilematrixset}>
    WMTSWrapperRole tilematrixset
    Retile_ConfigurationFiles {src_config} {dest_config}
    Retile_RegExp {layer_name}
    Retile_Source {src_path} {src_postfix}
</Directory>
"""

DATE_SERVICE_LUA_TEMPLATE = """local onearthTimeService = require "onearthTimeService"
handler = onearthTimeService.timeService({handler_type="redis", host="127.0.0.1"}, {filename_format="basic"})
"""

DATE_SERVICE_APACHE_TEMPLATE = """Alias /date_service {config_path}

<IfModule !ahtse_lua>
        LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>

<Directory {config_path}>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
        AHTSE_lua_RegExp date_service
        AHTSE_lua_Script {config_path}/date_service.lua
        AHTSE_lua_Redirect On
        AHTSE_lua_KeepAlive On
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
    PageSize {tile_size_x} {tile_size_y} 1 {bands}
    Nearest Off
    SkippedLevels {skipped_levels}
    Projection {projection}
    BoundingBox {bbox}
    MimeType {mime}
    Oversample On
    ExtraLevels 3
"""


class TestModWmtsWrapper(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.base_tmp_path = '/build/test/ci_tests/tmp'
        self.endpoint_path = '/build/test/ci_tests/tmp/mod_wmts_wrapper_mrf'
        self.endpoint_prefix_mrf = 'mod_wmts_wrapper_mrf'
        self.reproj_endpoint_path = '/build/test/ci_tests/tmp/mod_wmts_wrapper_reproject'
        self.endpoint_prefix_reproject = 'mod_wmts_wrapper_reproject'
        self.redis_layers = []

        base_apache_config = bulk_replace(
            BASE_APACHE_TEMPLATE,
            [('{endpoint_path}', self.endpoint_path),
             ('{alias}', self.endpoint_prefix_mrf),
             ('{reproj_endpoint_path}', self.reproj_endpoint_path),
             ('{reproj_alias}', self.endpoint_prefix_reproject)])

        self.base_apache_path = os.path.join(
            apache_conf_dir, 'mod_wmts_wrapper_test_base.conf')
        with open(self.base_apache_path, 'w+') as f:
            f.write(base_apache_config)

        self.mrf_prefix = 'test_mrf'

        if not redis_running():
            Popen(['redis-server'])
        time.sleep(2)
        if not redis_running():
            print("WARNING: Can't access Redis server. Tests may fail.")

        self.setup_mrf_nodate()
        self.setup_mrf_date()
        self.setup_date_service()
        self.setup_mrf_date_yeardir()
        self.setup_mrf_reproject_nodate()
        self.setup_mrf_reproject_date()

        restart_apache()

    @classmethod
    def setup_date_service(self):
        # Check if mod_ahtse_lua is installed
        apache_path = '/etc/httpd/modules/'
        if not os.path.exists(os.path.join(apache_path, 'mod_ahtse_lua.so')):
            print("WARNING: Can't find mod_ahtse_lua installed in: {0}. Tests may fail.".format(apache_path))

        # Check if onearth Lua stuff has been installed
        lua = Popen(['luarocks', 'list'], stdout=PIPE)
        (output, _) = lua.communicate()
        p_status = lua.wait()
        if p_status:
            print("WARNING: Error running Luarocks. Make sure lua and luarocks are installed and that the OnEarth lua package is also installed. Tests may fail.")
        if 'onearth' not in str(output):
            print("WARNING: OnEarth luarocks package not installed. Tests may fail.")

        # Start redis
        if not redis_running():
            Popen(['redis-server'])
        time.sleep(2)
        if not redis_running():
            print("WARNING: Can't access Redis server. Tests may fail.")

        # Copy Lua config
        test_lua_config_dest_path = '/build/test/ci_tests/tmp/date_service_test'
        test_lua_config_filename = 'date_service.lua'
        self.test_lua_config_location = os.path.join(test_lua_config_dest_path,
                                                     test_lua_config_filename)

        make_dir_tree(test_lua_config_dest_path, ignore_existing=True)
        with open(self.test_lua_config_location, 'w+') as f:
            f.write(DATE_SERVICE_LUA_TEMPLATE)

        # Copy Apache config
        self.date_service_apache_path = os.path.join(
            '/etc/httpd/conf.d', 'oe2_test_date_service.conf')
        with open(self.date_service_apache_path, 'w+') as dest:
            dest.write(
                DATE_SERVICE_APACHE_TEMPLATE.replace(
                    '{config_path}', test_lua_config_dest_path))

    @classmethod
    def setup_mrf_nodate(self):
        # Configure mod_mrf setup
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = "jpeg"
        tilematrixset = '16km'

        config_prefix = self.mrf_prefix + '_nodate'

        # Add Apache config for base imagery layer to be served by mod_mrf
        layer_path = '{}/default/{}'.format(config_prefix, tilematrixset)
        self.mrf_endpoint_path_nodate = os.path.join(self.endpoint_path,
                                                     layer_path)
        self.mrf_url_nodate = '{}/{}/{}'.format(
            base_url, self.endpoint_prefix_mrf, config_prefix)

        apache_config = bulk_replace(
            MOD_MRF_NODATE_APACHE_TEMPLATE,
            [('{config_path}', config_prefix),
             ('{config_file_path}',
              os.path.join(self.mrf_endpoint_path_nodate,
                           config_prefix + '.config')),
             ('{alias}', self.endpoint_prefix_mrf),
             ('{endpoint_path}', self.endpoint_path),
             ('{layer_name}', config_prefix),
             ('{tilematrixset}', tilematrixset),
             ('{tilematrixset}', tilematrixset)])

        self.mod_mrf_apache_config_path_nodate = os.path.join(
            apache_conf_dir, config_prefix + '.conf')
        with open(self.mod_mrf_apache_config_path_nodate, 'w+') as f:
            f.write(apache_config)

        # Copy test imagery
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_wmts_wrapper_test_data')
        make_dir_tree(self.mrf_endpoint_path_nodate, ignore_existing=True)
        idx_path = os.path.join(self.mrf_endpoint_path_nodate,
                                config_prefix + '.idx')
        data_path = os.path.join(self.mrf_endpoint_path_nodate,
                                 config_prefix + '.pjg')
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.idx'), idx_path)
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.pjg'), data_path)

        # Build layer config
        data_config = 'DataFile ' + data_path
        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{idx_path}', idx_path), ('{data_config}', data_config),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])

        mod_mrf_config_path = os.path.join(self.mrf_endpoint_path_nodate,
                                           config_prefix + '.config')

        with open(mod_mrf_config_path, 'w+') as f:
            f.write(mod_mrf_config)

    @classmethod
    def setup_mrf_date(self):
        # Configure mod_mrf setup
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = "jpeg"
        tilematrixset = '16km'

        config_prefix = 'test_mrf_date'

        # Add Apache config for base imagery layer to be served by mod_mrf
        layer_path = '{}/default/{}'.format(config_prefix, tilematrixset)
        self.mrf_endpoint_path_date = os.path.join(self.endpoint_path,
                                                   layer_path)
        self.mrf_url_date = '{}/{}/{}'.format(
            base_url, self.endpoint_prefix_mrf, config_prefix)
        apache_config = bulk_replace(
            MOD_MRF_DATE_APACHE_TEMPLATE,
            [('{config_path}', self.mrf_endpoint_path_date),
             ('{config_file_path}',
              os.path.join(self.mrf_endpoint_path_date,
                           config_prefix + '.config')),
             ('{alias}', self.endpoint_prefix_mrf),
             ('{endpoint_path}', self.endpoint_path),
             ('{layer_name}', config_prefix),
             ('{tilematrixset}', tilematrixset), ('{year_dir}', 'Off')])

        self.mod_mrf_apache_config_path_date = os.path.join(
            apache_conf_dir, config_prefix + '.conf')
        with open(self.mod_mrf_apache_config_path_date, 'w+') as f:
            f.write(apache_config)

        # Copy test imagery
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_wmts_wrapper_test_data')
        make_dir_tree(self.mrf_endpoint_path_date, ignore_existing=True)

        for date in ['2012001000000', '2015001000000']:
            date_idx_path = os.path.join(self.mrf_endpoint_path_date,
                                         config_prefix + '-' + date + '.idx')
            date_data_path = os.path.join(self.mrf_endpoint_path_date,
                                          config_prefix + '-' + date + '.pjg')
            shutil.copy(
                os.path.join(test_imagery_path,
                             config_prefix + '-' + date + '.idx'),
                date_idx_path)
            shutil.copy(
                os.path.join(test_imagery_path,
                             config_prefix + '-' + date + '.pjg'),
                date_data_path)

        idx_path = os.path.join(self.mrf_endpoint_path_date, '${filename}.idx')
        data_path = os.path.join(self.mrf_endpoint_path_date,
                                 '${filename}.pjg')
        # Build layer config
        data_config = 'DataFile ' + data_path
        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{idx_path}', idx_path), ('{data_config}', data_config),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])

        mod_mrf_config_path = os.path.join(self.mrf_endpoint_path_date,
                                           config_prefix + '.config')

        with open(mod_mrf_config_path, 'w+') as f:
            f.write(mod_mrf_config)

        redis_data = [
            ('test_mrf_date', '2012-01-01', '2012-01-01/2016-01-01/P1Y',
             '2013-06-06', '2013-01-01T00:00:00Z'),
        ]
        seed_redis_data(redis_data)
        self.redis_layers.append(redis_data)

        # Create test "best" data files for test_mod_mrf_best_tile_headers test
        best_filename = 'test_mrf_date-BEST'
        seed_redis_best_data(redis_data, best_filename, db_keys=[])

        date = '2012001000000'
        new_date = '2013001000000'
        shutil.copy(
            os.path.join(test_imagery_path,
                            config_prefix + '-' + date + '.idx'),
            os.path.join(self.mrf_endpoint_path_date,
                            best_filename + '-' + new_date + '.idx'))
        shutil.copy(
            os.path.join(test_imagery_path,
                            config_prefix + '-' + date + '.pjg'),
            os.path.join(self.mrf_endpoint_path_date,
                            best_filename + '-' + new_date + '.pjg'))

    @classmethod
    def setup_mrf_date_yeardir(self):
        # Configure mod_mrf setup
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = "jpeg"
        tilematrixset = '16km'
        year = '2012'

        config_prefix = 'test_mrf_date_yeardir'

        # Add Apache config for base imagery layer to be served by mod_mrf
        layer_path = '{}/default/{}'.format(config_prefix, tilematrixset)
        self.mrf_endpoint_path_date_yeardir = os.path.join(
            self.endpoint_path, layer_path)
        self.mrf_url_date = '{}/{}/{}'.format(
            base_url, self.endpoint_prefix_mrf, config_prefix)
        apache_config = bulk_replace(
            MOD_MRF_DATE_APACHE_TEMPLATE,
            [('{config_path}', self.mrf_endpoint_path_date_yeardir),
             ('{config_file_path}',
              os.path.join(self.mrf_endpoint_path_date_yeardir,
                           config_prefix + '.config')),
             ('{alias}', self.endpoint_prefix_mrf),
             ('{endpoint_path}', self.endpoint_path),
             ('{layer_name}', config_prefix),
             ('{tilematrixset}', tilematrixset), ('{year_dir}', 'On')])

        self.mod_mrf_apache_config_path_date_yeardir = os.path.join(
            apache_conf_dir, config_prefix + '.conf')
        with open(self.mod_mrf_apache_config_path_date_yeardir, 'w+') as f:
            f.write(apache_config)

        # Copy test imagery
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_wmts_wrapper_test_data')
        make_dir_tree(
            self.mrf_endpoint_path_date_yeardir, ignore_existing=True)

        for date in ['2012001000000', '2015001000000']:
            yeardir = os.path.join(self.mrf_endpoint_path_date_yeardir,
                                   date[:4])

            make_dir_tree(yeardir, ignore_existing=True)

            date_idx_path = os.path.join(yeardir,
                                         config_prefix + '-' + date + '.idx')
            date_data_path = os.path.join(yeardir,
                                          config_prefix + '-' + date + '.pjg')
            shutil.copy(
                os.path.join(test_imagery_path,
                             config_prefix + '-' + date + '.idx'),
                date_idx_path)
            shutil.copy(
                os.path.join(test_imagery_path,
                             config_prefix + '-' + date + '.pjg'),
                date_data_path)

        idx_path = os.path.join(self.mrf_endpoint_path_date_yeardir,
                                '${YYYY}/${filename}.idx')
        data_path = os.path.join(self.mrf_endpoint_path_date_yeardir,
                                 '${YYYY}/${filename}.pjg')

        # Build layer config
        data_config = 'DataFile ' + data_path
        mod_mrf_config = bulk_replace(
            MOD_MRF_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{idx_path}', idx_path), ('{data_config}', data_config),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])

        mod_mrf_config_path = os.path.join(self.mrf_endpoint_path_date_yeardir,
                                           config_prefix + '.config')

        with open(mod_mrf_config_path, 'w+') as f:
            f.write(mod_mrf_config)

        redis_data = [
            ('test_mrf_date_yeardir', '2012-01-01',
             '2012-01-01/2016-01-01/P1Y', '2013-06-06',
             '2013-01-01T00:00:00Z'),
        ]
        seed_redis_data(redis_data)
        self.redis_layers.append(redis_data)

    @classmethod
    def setup_mrf_reproject_nodate(self):
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = 'jpeg'
        src_tilematrixset = '16km'
        tilematrixset = 'GoogleMapsCompatible_Level3'

        config_prefix = 'test_reproject_nodate'
        src_path = '/{}/test_mrf_nodate/default/{}'.format(
            self.endpoint_prefix_mrf, src_tilematrixset)
        # Add Apache config for base imagery layer to be served by mod_mrf
        layer_path = '{}/default/{}'.format(config_prefix, tilematrixset)
        self.reproj_endpoint_path_nodate = os.path.join(
            self.reproj_endpoint_path, layer_path)
        self.reproject_url_nodate = '{}/{}/{}'.format(
            base_url, self.endpoint_prefix_reproject, config_prefix)
        src_config_path = os.path.join(self.reproj_endpoint_path_nodate,
                                       config_prefix + '_src.config')
        dest_config_path = os.path.join(self.reproj_endpoint_path_nodate,
                                        config_prefix + '_dest.config')
        apache_config = bulk_replace(
            MOD_REPROJECT_NODATE_APACHE_TEMPLATE,
            [('{config_path}', self.reproj_endpoint_path_nodate),
             ('{src_config}', src_config_path),
             ('{dest_config}', dest_config_path),
             ('{alias}', self.endpoint_prefix_reproject),
             ('{endpoint_path}', self.reproj_endpoint_path),
             ('{layer_name}', config_prefix),
             ('{tilematrixset}', tilematrixset), ('{year_dir}', 'Off'),
             ('{src_postfix}', '.jpg'),
             ('{src_path}', src_path)])

        self.mod_reproj_apache_config_path_nodate = os.path.join(
            apache_conf_dir, config_prefix + '.conf')
        with open(self.mod_reproj_apache_config_path_nodate, 'w+') as f:
            f.write(apache_config)

        # Copy test imagery
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_wmts_wrapper_test_data')
        make_dir_tree(self.reproj_endpoint_path_nodate, ignore_existing=True)
        idx_path = os.path.join(self.reproj_endpoint_path_nodate,
                                config_prefix + '.idx')
        data_path = os.path.join(self.reproj_endpoint_path_nodate,
                                 config_prefix + '.pjg')
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.idx'), idx_path)
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.pjg'), data_path)

        # Build layer config
        mod_reproj_src_config = bulk_replace(
            MOD_REPROJECT_SRC_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{skipped_levels}', '0' if size_x == size_y else '1'),
             ('{projection}', 'EPSG:4326'),
             ('{bbox}', '-180.0,-90.0,180.0,90.0')])

        mod_reproj_src_config_path = os.path.join(
            self.reproj_endpoint_path_nodate, config_prefix + '.config')

        with open(src_config_path, 'w+') as f:
            f.write(mod_reproj_src_config)

        reproj_size_x = 2048
        reproj_size_y = 2048
        reproj_tile_size = 256
        mod_reproj_dest_config = bulk_replace(
            MOD_REPROJECT_DEST_CONFIG_TEMPLATE,
            [('{size_x}', reproj_size_x), ('{size_y}', reproj_size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', reproj_tile_size),
             ('{tile_size_y}', reproj_tile_size),
             ('{skipped_levels}', '0' if size_x == size_y else '1'),
             ('{projection}', 'EPSG:3857'),
             ('{bbox}',
              '-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'), 
             ('{mime}', 'image/jpeg')])

        mod_reproj_dest_config_path = os.path.join(
            self.reproj_endpoint_path_nodate, config_prefix + '.config')

        with open(dest_config_path, 'w+') as f:
            f.write(mod_reproj_dest_config)

    @classmethod
    def setup_mrf_reproject_date(self):
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = 'jpeg'
        src_tilematrixset = '16km'
        tilematrixset = 'GoogleMapsCompatible_Level3'

        config_prefix = 'test_reproject_date'
        src_path = '/{}/test_mrf_date/default/{}/{}'.format(
                    self.endpoint_prefix_mrf, '${date}', src_tilematrixset)
        # Add Apache config for base imagery layer to be served by mod_mrf
        layer_path = '{}/default/{}'.format(config_prefix, tilematrixset)
        self.reproj_endpoint_path_date = os.path.join(
            self.reproj_endpoint_path, layer_path)
        self.reproject_url_date = '{}/{}/{}'.format(
            base_url, self.endpoint_prefix_reproject, config_prefix)
        src_config_path = os.path.join(self.reproj_endpoint_path_date,
                                       config_prefix + '_src.config')
        dest_config_path = os.path.join(self.reproj_endpoint_path_date,
                                        config_prefix + '_dest.config')
        apache_config = bulk_replace(
            MOD_REPROJECT_DATE_APACHE_TEMPLATE,
            [('{config_path}', self.reproj_endpoint_path_date),
             ('{src_config}', src_config_path),
             ('{dest_config}', dest_config_path),
             ('{alias}', self.endpoint_prefix_reproject),
             ('{endpoint_path}', self.reproj_endpoint_path),
             ('{layer_name}', config_prefix),
             ('{tilematrixset}', tilematrixset), ('{year_dir}', 'Off'),
             ('{src_postfix}', '.jpg'),
             ('{src_path}', src_path)])

        self.mod_reproj_apache_config_path_date = os.path.join(
            apache_conf_dir, config_prefix + '.conf')
        with open(self.mod_reproj_apache_config_path_date, 'w+') as f:
            f.write(apache_config)

        # Copy test imagery
        test_imagery_path = os.path.join(os.getcwd(),
                                         'mod_wmts_wrapper_test_data')
        make_dir_tree(self.reproj_endpoint_path_date, ignore_existing=True)
        idx_path = os.path.join(self.reproj_endpoint_path_date,
                                config_prefix + '.idx')
        data_path = os.path.join(self.reproj_endpoint_path_date,
                                 config_prefix + '.pjg')
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.idx'), idx_path)
        shutil.copy(
            os.path.join(test_imagery_path, config_prefix + '.pjg'), data_path)

        # Build layer config
        mod_reproj_src_config = bulk_replace(
            MOD_REPROJECT_SRC_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{skipped_levels}', '0' if size_x == size_y else '1'),
             ('{projection}', 'EPSG:4326'),
             ('{bbox}', '-180.0,-90.0,180.0,90.0')])

        mod_reproj_src_config_path = os.path.join(
            self.reproj_endpoint_path_date, config_prefix + '.config')

        with open(src_config_path, 'w+') as f:
            f.write(mod_reproj_src_config)

        reproj_size_x = 2048
        reproj_size_y = 2048
        reproj_tile_size = 256
        mod_reproj_dest_config = bulk_replace(
            MOD_REPROJECT_DEST_CONFIG_TEMPLATE,
            [('{size_x}', reproj_size_x), ('{size_y}', reproj_size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', reproj_tile_size),
             ('{tile_size_y}', reproj_tile_size),
             ('{skipped_levels}',
              '0' if reproj_size_x == reproj_size_y else '1'),
             ('{projection}', 'EPSG:3857'),
             ('{bbox}',
              '-20037508.34278925,-20037508.34278925,20037508.34278925,20037508.34278925'
              ), ('{mime}', 'image/jpeg')])

        mod_reproj_dest_config_path = os.path.join(
            self.reproj_endpoint_path_nodate, config_prefix + '.config')

        with open(dest_config_path, 'w+') as f:
            f.write(mod_reproj_dest_config)

    # REST tests
    def test_REST_bad_layer(self):
        for module in ('mrf', 'reproject'):
            module_url = 'mod_wmts_wrapper_' + module
            test_url = '{}/{}/bogus_layer/default/default/0/0/0.png'.format(
                base_url, module_url)
            test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                            'LAYER', 'LAYER does not exist')

    def test_REST_bad_style(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/bogus_style/{}/{}/0/0/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'STYLE', 'STYLE is invalid for LAYER')

    def test_REST_bad_tilematrixset(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                test_url = '{}/{}/{}/default/{}/bad_tms/0/0/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default')

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEMATRIXSET',
                                'TILEMATRIXSET is invalid for LAYER')

    def test_REST_invalid_tilematrix(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/10/0/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(
                    self, test_url, 400, 'TileOutOfRange', 'TILEMATRIX',
                    'TILEMATRIX is out of range, maximum value is 3')

    def test_REST_bad_tilematrix_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/bogus/0/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEMATRIX',
                                'TILEMATRIX is not a valid integer')

    def test_REST_bad_tilematrix_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/10/0/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'TileOutOfRange',
                                'TILEMATRIX',
                                'TILEMATRIX is out of range, maximum value is 3')

    def test_REST_row_out_of_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/0/1/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'TileOutOfRange',
                                'TILEROW',
                                'TILEROW is out of range, maximum value is 0')

    def test_REST_bad_tilerow_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/0/bogus/0.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEROW', 'TILEROW is not a valid integer')

    def test_REST_tilecol_out_of_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/0/0/10.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                errmsg = 'TILECOL is out of range, maximum value is {}'.format(
                    '0' if module == 'reproject' else '1')
                test_wmts_error(self, test_url, 400, 'TileOutOfRange',
                                'TILECOL', errmsg)

    def test_REST_bad_tilecol_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/0/0/bogus.jpg'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILECOL', 'TILECOL is not a valid integer')

    def test_REST_bad_format(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/{}/default/{}/{}/0/0/0.bogus'.format(
                    base_url, module_url, layer_name,
                    '' if fmt == 'nodate' else 'default', tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'FORMAT', 'FORMAT is invalid for LAYER')
                
    def test_REST_bad_url(self):
        for module in ('mrf', 'reproject'):
            module_url = 'mod_wmts_wrapper_' + module
            test_url = '{}/{}/0.png'.format(
                base_url, module_url)
            test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                            'LAYER', 'LAYER does not exist')

    # KvP Tests

    # Missing parameters
    def test_kvp_missing_request(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?layer={}&version=1.0.0&service=wmts&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'REQUEST', 'Missing REQUEST parameter')

    def test_kvp_missing_service(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?layer={}&version=1.0.0&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'SERVICE', 'Missing SERVICE parameter')

    def test_kvp_missing_version(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'VERSION', 'Missing VERSION parameter')

    def test_kvp_missing_layer(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'LAYER', 'Missing LAYER parameter')

    def test_kvp_missing_format(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'FORMAT', 'Missing FORMAT parameter')

    def test_kvp_missing_tilematrixset(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'TILEMATRIXSET',
                                'Missing TILEMATRIXSET parameter')

    def test_kvp_missing_tilematrix(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'TILEMATRIX', 'Missing TILEMATRIX parameter')

    def test_kvp_missing_tilerow(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'TILEROW', 'Missing TILEROW parameter')

    def test_kvp_missing_tilecol(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'MissingParameterValue',
                                'TILECOL', 'Missing TILECOL parameter')

    # # Invalid parameters
    def test_kvp_bad_service(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=tmnt&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'SERVICE', 'Unrecognized service')

    def test_kvp_bad_request(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=a_reasonable&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 501, 'OperationNotSupported',
                                'REQUEST', 'The request type is not supported')

    def test_kvp_bad_version(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=3.2.1&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'VERSION', 'VERSION is invalid')

    def test_kvp_bad_layer(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'bogus'

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'LAYER', 'LAYER does not exist')

    def test_kvp_bad_style(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0&style=shaolin'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'STYLE', 'STYLE is invalid for LAYER')

    def test_kvp_bad_format(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/png&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'FORMAT', 'FORMAT is invalid for LAYER')

    def test_kvp_bad_tilematrixset(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level34' if module == 'reproject' else '19km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEMATRIXSET',
                                'TILEMATRIXSET is invalid for LAYER')

    def test_kvp_bad_tilematrix_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=morpheus&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEMATRIX',
                                'TILEMATRIX is not a valid integer')

    def test_kvp_bad_tilerow_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=ronan_farrow&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILEROW', 'TILEROW is not a valid integer')

    def test_kvp_bad_tilecol_value(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=colm_meany'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'InvalidParameterValue',
                                'TILECOL', 'TILECOL is not a valid integer')

    def test_kvp_invalid_tilematrix_(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=43&tilerow=0&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(
                    self, test_url, 400, 'TileOutOfRange', 'TILEMATRIX',
                    'TILEMATRIX is out of range, maximum value is 3')

    def test_kvp_tilerow_out_of_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=8&tilecol=0'.format(
                    base_url, module_url, layer_name, tms)

                test_wmts_error(self, test_url, 400, 'TileOutOfRange',
                                'TILEROW',
                                'TILEROW is out of range, maximum value is 0')

    def test_kvp_tilecol_out_of_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=5'.format(
                    base_url, module_url, layer_name, tms)

                errmsg = 'TILECOL is out of range, maximum value is {}'.format(
                    '0' if module == 'reproject' else '1')
                test_wmts_error(self, test_url, 400, 'TileOutOfRange',
                                'TILECOL', errmsg)

    def test_kvp_bad_time_format(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir', 'nodate'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0&time=86753-09'.format(
                    base_url, module_url, layer_name, tms)
                test_wmts_error(
                    self, test_url, 400, 'InvalidParameterValue', 'TIME',
                    'Invalid time format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ'
                )
                
    def test_kvp_bad_time_out_of_range(self):
        for module in ('mrf', 'reproject'):
            for fmt in ('date', 'date_yeardir'):
                if module == 'reproject' and fmt == 'date_yeardir':
                    continue

                module_url = 'mod_wmts_wrapper_' + module
                layer_name = 'test_{}_{}'.format(module, fmt)

                tms = 'GoogleMapsCompatible_Level3' if module == 'reproject' else '16km'
                test_url = '{}/{}/wmts.cgi?version=1.0.0&layer={}&service=wmts&request=gettile&format=image/jpeg&tilematrixset={}&tilematrix=0&tilerow=0&tilecol=0&time=2020-01-01'.format(
                    base_url, module_url, layer_name, tms)
                if module == 'reproject':
                    self.assertTrue(check_response_code(test_url, 200, 'Not Found'))
                else:
                    self.assertTrue(check_response_code(test_url, 404, 'Not Found'))

    # Tile Handling
    def test_mod_mrf_nodate_tile(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_nodate/default/16km/0/0/0.jpg'

        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
            tile_url)
        self.assertTrue(check_tile_request(tile_url, ref_hash), errstring)

    def test_mod_mrf_date_tile_default(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/default/16km/0/0/0.jpg'

        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
            tile_url)
        self.assertTrue(check_tile_request(tile_url, ref_hash), errstring)

    def test_mod_mrf_date_tile(self):
        for test in [('2012-01-01', '3f84501587adfe3006dcbf59e67cd0a3'),
                     ('2015-01-01', '9b38d90baeeebbcadbc8560a29481a5e')]:
            tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/{}/16km/0/0/0.jpg'.format(
                test[0])

            errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
                tile_url)
            self.assertTrue(check_tile_request(tile_url, test[1]), errstring)

    def test_mod_mrf_nodate_tile_headers(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_nodate/default/16km/0/0/0.jpg'

        response = get_url(tile_url)
        headers = response.getheaders()

        check_layer_headers(self, headers, 'test_mrf_nodate', 'test_mrf_nodate', 'default', '')

    def test_mod_mrf_defaultdate_tile_headers(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/default/16km/0/0/0.jpg'

        response = get_url(tile_url)
        headers = response.getheaders()

        check_layer_headers(self, headers, 'test_mrf_date', 'test_mrf_date', 'default', '2012-01-01T00:00:00Z')

    def test_mod_mrf_date_tile_headers(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/2012-03-11/16km/0/0/0.jpg'

        response = get_url(tile_url)
        headers = response.getheaders()

        check_layer_headers(self, headers, 'test_mrf_date', 'test_mrf_date', '2012-03-11', '2012-01-01T00:00:00Z')

    def test_mod_mrf_best_tile_headers(self):
        tile_url = f'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/2013-01-01/16km/0/0/0.jpg'

        response = get_url(tile_url)
        headers = response.getheaders()

        check_layer_headers(self, headers, 'test_mrf_date', 'test_mrf_date-BEST', '2013-01-01', '2013-01-01T00:00:00Z')

    def test_mod_mrf_date_tile_yeardir(self):
        for test in [('2012-01-01', '3f84501587adfe3006dcbf59e67cd0a3'),
                     ('2015-01-01', '9b38d90baeeebbcadbc8560a29481a5e')]:
            tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/{}/16km/0/0/0.jpg'.format(
                test[0])

            errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
                tile_url)
            self.assertTrue(check_tile_request(tile_url, test[1]), errstring)
            
    def test_mod_mrf_date_out_of_range(self):
        for test in [('2000-01-01','2020-01-01')]:
            tile_url = 'http://localhost/mod_wmts_wrapper_mrf/test_mrf_date/default/{}/16km/0/0/0.jpg'.format(
                test[0])
            self.assertTrue(check_response_code(tile_url, 404, 'Not Found'))

    def test_mod_reproject_nodate_tile(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_reproject/test_reproject_nodate/default/GoogleMapsCompatible_Level3/0/0/0.jpg'

        ref_hash = '1af170cdf1f7e29f8a595b392a24dc97'
        errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
            tile_url)
        self.assertTrue(check_tile_request(tile_url, ref_hash), errstring)

    def test_mod_reproject_default_tile(self):
        tile_url = 'http://localhost/mod_wmts_wrapper_reproject/test_reproject_date/default/default/GoogleMapsCompatible_Level3/0/0/0.jpg'

        ref_hash = '5f7056b7b8c98fa736231364f4058859'
        errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
            tile_url)
        self.assertTrue(check_tile_request(tile_url, ref_hash), errstring)

    def test_mod_reproject_date_tile(self):
        for test in [('2012-01-01', '5f7056b7b8c98fa736231364f4058859'),
                     ('2015-01-01', 'ba1e14d3fb2b924974054a9cac61a74c')]:
            tile_url = 'http://localhost/mod_wmts_wrapper_reproject/test_reproject_date/default/{}/GoogleMapsCompatible_Level3/0/0/0.jpg'.format(
                test[0])

            errstring = 'Tile at URL:{} was not the same as what was expected.'.format(
                tile_url)
            self.assertTrue(check_tile_request(tile_url, test[1]), errstring)

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.base_tmp_path)
        os.remove(self.mod_mrf_apache_config_path_date)
        os.remove(self.mod_mrf_apache_config_path_date_yeardir)
        os.remove(self.mod_mrf_apache_config_path_nodate)
        os.remove(self.mod_reproj_apache_config_path_date)
        os.remove(self.mod_reproj_apache_config_path_nodate)
        os.remove(self.date_service_apache_path)
        os.remove(self.base_apache_path)

        for layer in self.redis_layers:
            remove_redis_layer(layer)
        restart_apache()


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_mod_wmts_wrapper_err_results.xml',
        help=
        'Specify XML output file (default is test_mod_wmts_wrapper_err_results.xml'
    )
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Load test configuration into Apache and quit (for debugging)')
    parser.add_option(
        '-l',
        '--conf_location',
        action='store',
        dest='apache_conf_dir',
        help=
        'Apache config location to install test files to (default is /etc/httpd/conf.d)',
        default=apache_conf_dir)
    parser.add_option(
        '-u',
        '--base_url',
        action='store',
        dest='base_url',
        help=
        'Base url for the Apache install on this machine (default is http://localhost)',
        default=base_url)
    (options, args) = parser.parse_args()

    # Set the globals for these tests
    apache_conf_dir = options.apache_conf_dir
    base_url = options.base_url

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModWmtsWrapper.setUpClass()
        sys.exit(
            'Apache has been loaded with the test configuration. No tests run.'
        )

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
