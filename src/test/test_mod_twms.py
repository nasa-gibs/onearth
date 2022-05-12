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
# Tests for mod_twms
#

import os
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
import time
import shutil
from subprocess import Popen, PIPE
from oe_test_utils import bulk_replace, redis_running, make_dir_tree, seed_redis_data, restart_apache, check_tile_request, remove_redis_layer, check_response_code

base_url = 'http://localhost'
apache_conf_dir = '/etc/httpd/conf.d'

BASE_APACHE_TEMPLATE = """<IfModule !mrf_module>
   LoadModule mrf_module modules/mod_mrf.so
</IfModule>

<IfModule !twms_module>
   LoadModule twms_module modules/mod_twms.so
</IfModule>

<IfModule !wmts_wrapper_module>
    LoadModule wmts_wrapper_module modules/mod_wmts_wrapper.so
</IfModule>

<IfModule !receive_module>
    LoadModule receive_module modules/mod_receive.so
</IfModule>

<Directory /build/test/ci_tests/tmp>
 Require all granted
</Directory>

Alias /{alias} {endpoint_path}
Alias /{twms_alias} {twms_endpoint_path}

<Directory {endpoint_path}>
    WMTSWrapperRole root
</Directory>

<Directory {twms_endpoint_path}>
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

MOD_TWMS_CONFIG_TEMPLATE = """
<Directory {internal_endpoint}>
        tWMS_RegExp twms.cgi
        tWMS_ConfigurationFile {internal_endpoint}/{layer}/twms.config
</Directory>
"""

LAYER_MOD_TWMS_CONFIG_TEMPLATE = """Size {size_x} {size_y} 1 {bands}
PageSize {tile_size_x} {tile_size_y} 1 {bands}
BoundingBox {bbox}
SourcePath {source_path}
SourcePostfix {source_postfix}
SkippedLevels {skipped_levels}
"""


class TestModTwms(unittest.TestCase):

    # SETUP
    @classmethod
    def setUpClass(self):
        self.base_tmp_path = '/build/test/ci_tests/tmp'
        self.mrf_endpoint_path = '/build/test/ci_tests/tmp/mod_twms_mrf'
        self.endpoint_prefix_mrf = 'mod_twms_mrf'
        self.twms_endpoint_path = '/build/test/ci_tests/tmp/test_twms'
        self.endpoint_prefix_twms = 'test_twms'
        self.redis_layers = []

        base_apache_config = bulk_replace(
            BASE_APACHE_TEMPLATE,
            [('{endpoint_path}', self.mrf_endpoint_path),
             ('{alias}', self.endpoint_prefix_mrf),
             ('{twms_endpoint_path}', self.twms_endpoint_path),
             ('{twms_alias}', self.endpoint_prefix_twms)])

        self.base_apache_path = os.path.join(apache_conf_dir,
                                             'mod_twms_test_base.conf')
        with open(self.base_apache_path, 'w+') as f:
            f.write(base_apache_config)

        self.mrf_prefix = 'test_mrf'

        if not redis_running():
            Popen(['redis-server'])
        time.sleep(2)
        if not redis_running():
            print('WARNING: Can\'t access Redis server. Tests may fail.')

        self.setup_mrf_nodate()
        self.setup_mrf_date()
        self.setup_date_service()
        self.setup_mod_twms_nodate()
        self.setup_mod_twms_date()

        restart_apache()

        # Verify that mod_mrf is up and running
        req_url = '{}/{}/test_mrf_nodate/default/16km/0/0/0.jpg'.format(
            base_url, self.endpoint_prefix_mrf)
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        check_result = check_tile_request(req_url, ref_hash)
        if not check_result:
            print('WARNING: mod_mrf doesn\'t appear to be running. URL: {}'.format(req_url))

        req_url = '{}/{}/test_mrf_date/default/default/16km/0/0/0.jpg'.format(
            base_url, self.endpoint_prefix_mrf)
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        check_result = check_tile_request(req_url, ref_hash)
        if not check_result:
            print('WARNING: mod_mrf doesn\'t appear to be running. URL: {}'.format(req_url))

    @classmethod
    def setup_mod_twms_nodate(self):
        # Copy Apache config
        config_prefix = self.endpoint_prefix_twms + '_nodate'
        self.twms_endpoint_path_nodate = os.path.join(self.twms_endpoint_path,
                                                      config_prefix)
        apache_config = bulk_replace(
            MOD_TWMS_CONFIG_TEMPLATE,
            [('{internal_endpoint}', self.twms_endpoint_path_nodate)])
        self.twms_apache_config_nodate = os.path.join(apache_conf_dir,
                                                      config_prefix + '.conf')
        with open(self.twms_apache_config_nodate, 'w+') as f:
            f.write(apache_config)

        # Copy layer config
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = 'jpeg'

        layer_config_path = os.path.join(self.twms_endpoint_path_nodate,
                                         'test')
        make_dir_tree(layer_config_path, ignore_existing=True)
        src_path = '{}/{}/test_mrf_nodate/default/16km'.format(
            base_url, self.endpoint_prefix_mrf)
        layer_config = bulk_replace(
            LAYER_MOD_TWMS_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{bbox}', '-180.0,-90.0,180.0,90.0'),
             ('{source_postfix}', '.' + image_type),
             ('{source_path}', src_path),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])
        with open(os.path.join(layer_config_path, 'twms.config'), 'w+') as f:
            f.write(layer_config)

    @classmethod
    def setup_mod_twms_date(self):
        # Copy Apache config
        config_prefix = self.endpoint_prefix_twms + '_date'
        self.twms_endpoint_path_date = os.path.join(self.twms_endpoint_path,
                                                    config_prefix)
        apache_config = bulk_replace(
            MOD_TWMS_CONFIG_TEMPLATE,
            [('{internal_endpoint}', self.twms_endpoint_path_date)])
        self.twms_apache_config_date = os.path.join(apache_conf_dir,
                                                    config_prefix + '.conf')
        with open(self.twms_apache_config_date, 'w+') as f:
            f.write(apache_config)

        # Copy layer config
        size_x = 2560
        size_y = 1280
        tile_size = 512
        image_type = 'jpeg'

        layer_config_path = os.path.join(self.twms_endpoint_path_date, 'test')
        make_dir_tree(layer_config_path, ignore_existing=True)
        src_path = '{}/{}/test_mrf_date/default/{}/16km'.format(
            base_url, self.endpoint_prefix_mrf, '${date}')
        layer_config = bulk_replace(
            LAYER_MOD_TWMS_CONFIG_TEMPLATE,
            [('{size_x}', size_x), ('{size_y}', size_y),
             ('{bands}', 4 if image_type == 'png' else 3),
             ('{tile_size_x}', tile_size), ('{tile_size_y}', tile_size),
             ('{bbox}', '-180.0,-90.0,180.0,90.0'),
             ('{source_postfix}', '.' + image_type),
             ('{source_path}', src_path),
             ('{skipped_levels}', '0' if size_x == size_y else '1')])
        with open(os.path.join(layer_config_path, 'twms.config'), 'w+') as f:
            f.write(layer_config)

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
        self.mrf_endpoint_path_nodate = os.path.join(self.mrf_endpoint_path,
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
             ('{endpoint_path}', self.mrf_endpoint_path),
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
        self.mrf_endpoint_path_date = os.path.join(self.mrf_endpoint_path,
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
             ('{endpoint_path}', self.mrf_endpoint_path),
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

    # DEFAULT TIME AND CURRENT TIME TESTS

    def test_request_twms_notime(self):
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_nodate')

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS current JPG request does not match what\'s expected. URL: ' +
            req_url)

    def test_request_twms_time(self):
        for date, ref_hash in [('2012-01-01',
                                '3f84501587adfe3006dcbf59e67cd0a3'),
                               ('2015-01-01',
                                '9b38d90baeeebbcadbc8560a29481a5e')]:
            req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
                base_url, self.endpoint_prefix_twms,
                self.endpoint_prefix_twms + '_date', date)

            check_result = check_tile_request(req_url, ref_hash)
            self.assertTrue(
                check_result,
                'TWMS JPG request does not match what\'s expected. URL: ' +
                req_url)

    def test_request_twms_time_default(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS JPG request does not match what\'s expected. URL: ' +
            req_url)
        
    def test_request_twms_time_out_of_range(self):
        date = '2020-01-01'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        self.assertTrue(check_response_code(req_url, 404, 'Not Found'))
        
    def test_request_twms_invalid_request(self):
        req_url = '{}/{}/{}/twms.cgi?request=GetNothing'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date')

        self.assertTrue(check_response_code(req_url, 400, 'Bad Request'))

    def test_request_twms_invalid_bbox(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-1800,-1980,1080,900&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        self.assertTrue(check_response_code(req_url, 400, 'Bad Request'))
        
    def test_request_twms_invalid_layers(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test_invalid&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        self.assertTrue(check_response_code(req_url, 400, 'Bad Request'))
        
    def test_request_twms_invalid_srs(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:99999&format=image%2Fjpeg&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS JPG request does not match what\'s expected. URL: ' +
            req_url)
        
    def test_request_twms_invalid_width(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=999&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS JPG request does not match what\'s expected. URL: ' +
            req_url)
        
    def test_request_twms_invalid_height(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fjpeg&styles=&width=512&height=999&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS JPG request does not match what\'s expected. URL: ' +
            req_url)
        
    def test_request_twms_invalid_format(self):
        date = '2012-01-01'
        ref_hash = '3f84501587adfe3006dcbf59e67cd0a3'
        req_url = '{}/{}/{}/twms.cgi?request=GetMap&layers=test&srs=EPSG:4326&format=image%2Fblah&styles=&width=512&height=512&bbox=-180,-198,108,90&time={}'.format(
            base_url, self.endpoint_prefix_twms,
            self.endpoint_prefix_twms + '_date', date)

        check_result = check_tile_request(req_url, ref_hash)
        self.assertTrue(
            check_result,
            'TWMS JPG request does not match what\'s expected. URL: ' +
            req_url)

    # TEARDOWN

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.base_tmp_path)
        os.remove(self.mod_mrf_apache_config_path_nodate)
        os.remove(self.mod_mrf_apache_config_path_date)
        os.remove(self.twms_apache_config_nodate)
        os.remove(self.twms_apache_config_date)
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
        default='test_mod_mrf_results.xml',
        help='Specify XML output file (default is test_mod_mrf_results.xml')
    parser.add_option(
        '-s',
        '--start_server',
        action='store_true',
        dest='start_server',
        help='Load test configuration into Apache and quit (for debugging)')
    (options, args) = parser.parse_args()

    # --start_server option runs the test Apache setup, then quits.
    if options.start_server:
        TestModTwms.setUpClass()
        sys.exit(
            'Apache has been loaded with the test configuration. No tests run.'
        )

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
