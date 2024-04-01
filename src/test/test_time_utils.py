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
# Tests for time utilities
#

import os
import sys
import unittest2 as unittest
import xmlrunner
from optparse import OptionParser
from subprocess import Popen, PIPE
import time
import redis
import requests
import shutil
from oe_test_utils import restart_apache, make_dir_tree, mrfgen_run_command as run_command
import datetime
from dateutil.relativedelta import relativedelta

DEBUG = False

DATE_SERVICE_LUA_TEMPLATE = """local onearthTimeService = require "onearthTimeService"
handler = onearthTimeService.timeService({handler_type="redis", host="127.0.0.1"}, {filename_format="hash"})
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


def redis_running():
    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        return r.ping()
    except redis.exceptions.ConnectionError:
        return False


def seed_redis_data(layers, db_keys=None):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'

    # Don't require there to be dates added to a layer in order to run periods.lua
    if len(layers[0]) > 1:
        for layer in layers:
            r.zadd('{0}layer:{1}:dates'.format(db_keystring, layer[0]), {layer[1]:0})

    with open('periods.lua', 'r') as f:
        lua_script = f.read()
    date_script = r.register_script(lua_script)
    date_script(keys=['{0}layer:{1}'.format(db_keystring, layers[0][0])])


def remove_redis_layer(layer, db_keys=None):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'
    r.delete('{0}layer:{1}:default'.format(db_keystring, layer[0]))
    r.delete('{0}layer:{1}:periods'.format(db_keystring, layer[0]))
    r.delete('{0}layer:{1}:config'.format(db_keystring, layer[0]))


def add_redis_config(layers, db_keys, config):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'
    r.sadd('{0}layer:{1}:config'.format(db_keystring, layers[0][0]), config)


class TestTimeUtils(unittest.TestCase):
    @classmethod
    def setUpClass(self):
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
        self.test_config_dest_path = os.path.join(
            '/etc/httpd/conf.d', 'oe2_test_date_service.conf')
        with open(self.test_config_dest_path, 'w+') as dest:
            dest.write(
                DATE_SERVICE_APACHE_TEMPLATE.replace(
                    '{config_path}', test_lua_config_dest_path))

        self.date_service_url = 'http://localhost/date_service/date?'

        restart_apache()

        shutil.copyfile("/home/oe2/onearth/src/modules/time_service/utils/periods.lua", os.getcwd() + '/periods.lua')

    def test_time_scrape_s3_keys(self):
        # Test scraping S3 keys
        test_layers = [('Test_Layer', '2017-01-04',
                        '2017-01-01/2017-01-04/P1D')]

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_scrape_time.py -r -b test-bucket 127.0.0.1"
        run_command(cmd, True)
        db_keys = ['epsg4326']
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[1], layer_res['default'],
                'Layer {0} has incorrect "default" value -- got {1}, expected {2}'
                .format(layer[0], layer[1], layer_res['default']))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_time_scrape_s3_inventory(self):
        # Test scraping S3 inventory file
        test_layers = [('MODIS_Aqua_CorrectedReflectance_TrueColor', '2017-01-15',
                        ['2017-01-01/2017-01-15/P1D']),
                       ('MODIS_Aqua_Aerosol', '2017-01-15',
                       ['2017-01-01T00:00:00Z/2017-01-01T00:00:11Z/PT11S',
                       '2017-01-02T00:00:00Z/2017-01-02T00:00:00Z/PT11S',
                       '2017-01-03T00:00:00Z/2017-01-03T00:00:00Z/PT11S',
                       '2017-01-04T00:00:00Z/2017-01-04T00:00:00Z/PT11S',
                       '2017-01-05T00:00:00Z/2017-01-05T00:00:00Z/PT11S',
                       '2017-01-06T00:00:00Z/2017-01-06T00:00:00Z/PT11S',
                       '2017-01-07T00:00:00Z/2017-01-07T00:00:00Z/PT11S',
                       '2017-01-08T00:00:00Z/2017-01-08T00:00:00Z/PT11S',
                       '2017-01-09T00:00:00Z/2017-01-09T00:00:00Z/PT11S',
                       '2017-01-10T00:00:00Z/2017-01-10T00:00:00Z/PT11S',
                       '2017-01-11T00:00:00Z/2017-01-11T00:00:00Z/PT11S',
                       '2017-01-12T00:00:00Z/2017-01-12T00:00:00Z/PT11S',
                       '2017-01-13T00:00:00Z/2017-01-13T00:00:00Z/PT11S',
                       '2017-01-15T00:00:00Z/2017-01-15T00:00:00Z/PT11S'])]

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_scrape_time.py -i -r -b test-inventory 127.0.0.1"
        run_command(cmd, True)
        db_keys = ['epsg4326']
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[1], layer_res['default'],
                'Layer {0} has incorrect "default" value -- got {2}, expected {1}'
                .format(layer[0], layer[1], layer_res['default']))
            self.assertEqual(
                layer[2], layer_res['periods'],
                'Layer {0} has incorrect "period" value -- got {2}, expected {1}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_time_config(self):
        # Test loading of time configs by endpoint
        source_dir = '/home/oe2/onearth/docker/sample_configs/layers/epsg4326/best/'
        layer_dir = '/etc/onearth/config/layers/epsg4326/best/'
        if os.path.exists(layer_dir) is False:
            os.makedirs(layer_dir)
        file_names = os.listdir(source_dir)
        for file_name in file_names:
            shutil.move(os.path.join(source_dir, file_name), os.path.join(layer_dir, file_name))

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_periods_configure.py -e /home/oe2/onearth/docker/sample_configs/endpoint/epsg4326_best.yaml"
        run_command(cmd, True)

        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        configs = r.smembers('epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:config')
        self.assertEqual(configs.pop(), b'DETECT/DETECT/P1D')

    def test_time_config_layer(self):
        # Test loading of time configs by individual layers
        source_dir = '/home/oe2/onearth/docker/sample_configs/layers/epsg4326/best/'
        layer_dir = '/etc/onearth/config/layers/epsg4326/best/'
        if os.path.exists(layer_dir) is False:
            os.makedirs(layer_dir)
        file_names = os.listdir(source_dir)
        for file_name in file_names:
            shutil.move(os.path.join(source_dir, file_name), os.path.join(layer_dir, file_name))

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_periods_configure.py -e /home/oe2/onearth/docker/sample_configs/endpoint/epsg4326_best.yaml -l '*Bands721'"
        run_command(cmd, True)

        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        configs = r.smembers('epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:config')
        self.assertEqual(configs.pop(), b'DETECT/DETECT/P1D')

    def test_best_config(self):
        # Test loading of best configs
        source_dir = '/home/oe2/onearth/docker/sample_configs/layers/epsg4326/best/'
        layer_dir = '/etc/onearth/config/layers/epsg4326/best/'
        if os.path.exists(layer_dir) is False:
            os.makedirs(layer_dir)
        file_names = os.listdir(source_dir)
        for file_name in file_names:
            shutil.move(os.path.join(source_dir, file_name), os.path.join(layer_dir, file_name))

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_periods_configure.py -e /home/oe2/onearth/docker/sample_configs/endpoint/epsg4326_best.yaml"
        run_command(cmd, True)

        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        configs = r.zrange('epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:best_config', 0, -1, withscores=True)
        self.assertEqual(configs.pop(), (b'MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD', 4.0))
        self.assertEqual(configs.pop(), (b'MODIS_Aqua_CorrectedReflectance_Bands721_v6_NRT', 3.0))
        self.assertEqual(configs.pop(), (b'MODIS_Aqua_CorrectedReflectance_Bands721_v5_STD', 2.0))
        self.assertEqual(configs.pop(), (b'MODIS_Aqua_CorrectedReflectance_Bands721_v5_NRT', 1.0))

    def test_best_layer(self):
        # Test loading of best layer
        source_dir = '/home/oe2/onearth/docker/sample_configs/layers/epsg4326/std/'
        layer_dir = '/etc/onearth/config/layers/epsg4326/std/'
        if os.path.exists(layer_dir) is False:
            os.makedirs(layer_dir)
        file_names = os.listdir(source_dir)
        for file_name in file_names:
            shutil.move(os.path.join(source_dir, file_name), os.path.join(layer_dir, file_name))

        cmd = "python3 /home/oe2/onearth/src/modules/time_service/utils/oe_periods_configure.py -e /home/oe2/onearth/docker/sample_configs/endpoint/epsg4326_std.yaml"
        run_command(cmd, True)

        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        best_layer = r.get('epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721_v6_STD:best_layer')
        self.assertEqual(best_layer, b'MODIS_Aqua_CorrectedReflectance_Bands721')

    def test_periods_single_date(self):
        # Test adding layer with single date
        test_layers = [('Test_Single', '2019-01-15',
                        '2019-01-15/2019-01-15/P1D')]

        db_keys = ['epsg4326']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[1], layer_res['default'],
                'Layer {0} has incorrect "default" value -- got {1}, expected {2}'
                .format(layer[0], layer[1], layer_res['default']))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_double_date(self):
        # Test adding layer with two dates
        test_layers = [('Test_Double', '2019-01-15',
                        '2019-01-15/2019-01-16/P1D'),
                        ('Test_Double', '2019-01-16',
                        '2019-01-15/2019-01-16/P1D')]

        db_keys = ['epsg4326']
        config = 'DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_multiple_periods_one_config(self):
        # Test adding layer with one config but multiple periods
        test_layers = [('Test_Multiple_Periods_One_Config', '2022-06-21',
                        '2022-06-21/2022-06-21/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-06-27',
                        '2022-06-27/2022-06-29/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-06-28',
                        '2022-06-27/2022-06-29/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-06-29',
                        '2022-06-27/2022-06-29/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-10-07',
                        '2022-10-07/2022-10-10/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-10-08',
                        '2022-10-07/2022-10-10/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-10-09',
                        '2022-10-07/2022-10-10/P1D'),
                        ('Test_Multiple_Periods_One_Config', '2022-10-10',
                        '2022-10-07/2022-10-10/P1D')]

        periods = ['2022-06-21/2022-06-21/P1D', '2022-06-27/2022-06-29/P1D', '2022-10-07/2022-10-10/P1D']

        db_keys = ['epsg4326']
        config = 'DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for i, layer in enumerate(test_layers):
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_subdaily(self):
        # Test subdaily period
        test_layers = [('Test_Subdaily', '2020-01-01T00:00:00Z',
                        '2020-01-01T00:00:00Z/2020-01-01T00:00:01Z/PT1S')]

        db_keys = ['epsg4326']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[1], layer_res['default'],
                'Layer {0} has incorrect "default" value -- got {1}, expected {2}'
                .format(layer[0], layer[1], layer_res['default']))

            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_multiday(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_Multiday', '2019-01-01',
                        '2019-01-01/2019-01-19/P6D'),
                       ('Test_Multiday', '2019-01-07',
                        '2019-01-01/2019-01-19/P6D'),
                       ('Test_Multiday', '2019-01-13',
                        '2019-01-01/2019-01-19/P6D'),
                       ('Test_Multiday', '2019-01-19',
                        '2019-01-01/2019-01-19/P6D')]

        db_keys = ['epsg4326']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_monthly(self):
        # Test adding layer with multiple months
        test_layers = [('Test_Monthly', '2019-01-01',
                        '2019-01-01/2019-04-01/P1M'),
                       ('Test_Monthly', '2019-02-01',
                        '2019-01-01/2019-04-01/P1M'),
                       ('Test_Monthly', '2019-03-01',
                        '2019-01-01/2019-04-01/P1M'),
                       ('Test_Monthly', '2019-04-01',
                        '2019-01-01/2019-04-01/P1M')]

        db_keys = ['epsg4326']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
    
    def test_periods_monthly_2dates_DETECT(self):
        # Test adding layer with multiple months
        test_layers = [('Test_Monthly_2dates_DETECT', '2023-02-01T00:00:00',
                        '2023-02-01/2023-03-01/P1M'),
                        ('Test_Monthly_2dates_DETECT', '2023-03-01T00:00:00',
                        '2023-02-01/2023-03-01/P1M')]
        
        db_keys = ['epsg4326']
        config = 'DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer[2], layer_res['periods'][0]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_monthly_3dates_DETECT(self):
        # Test adding layer with three months
        test_layers = [('Test_Monthly_3dates_DETECT', '2023-01-01T00:00:00',
                        '2023-01-01/2023-03-01/P1M'),
                        ('Test_Monthly_3dates_DETECT', '2023-02-01T00:00:00',
                        '2023-01-01/2023-03-01/P1M'),
                        ('Test_Monthly_3dates_DETECT', '2023-03-01T00:00:00',
                        '2023-01-01/2023-03-01/P1M')]
        
        db_keys = ['epsg4326']
        config = 'DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_DETECT(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_DETECT', '2019-01-01',
                        '2019-01-01/2019-01-13/P6D'),
                       ('Test_DETECT', '2019-01-07',
                        '2019-01-01/2019-01-13/P6D'),
                       ('Test_DETECT', '2019-01-13',
                        '2019-01-01/2019-01-13/P6D')]
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_DETECTDETECT(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_DETECTDETECT', '2019-01-01',
                        '2019-01-01/2019-01-13/P6D'),
                       ('Test_DETECTDETECT', '2019-01-07',
                        '2019-01-01/2019-01-13/P6D'),
                       ('Test_DETECTDETECT', '2019-01-13',
                        '2019-01-01/2019-01-13/P6D')]
        db_keys = ['epsg4326']
        config = 'DETECT/DETECT'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_DETECTDETECTP5D(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_DETECTDETECTP5D', '2019-01-01',
                        '2019-01-01/2019-01-11/P5D'),
                       ('Test_DETECTDETECTP5D', '2019-01-06',
                        '2019-01-01/2019-01-11/P5D'),
                       ('Test_DETECTDETECTP5D', '2019-01-11',
                        '2019-01-01/2019-01-11/P5D')]
        db_keys = ['epsg4326']
        config = 'DETECT/DETECT/P5D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_DETECTP10D(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_DETECTP10D', '2019-01-01',
                        '2019-01-01/2019-01-21/P10D'),
                       ('Test_DETECTP10D', '2019-01-11',
                        '2019-01-01/2019-01-21/P10D'),
                       ('Test_DETECTP10D', '2019-01-21',
                        '2019-01-01/2019-01-21/P10D')]
        db_keys = ['epsg4326']
        config = 'DETECT/P10D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_all(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_ForceAll', '2019-01-01',
                        '2019-01-07/2020-12-01/P8D'),
                       ('Test_ForceAll', '2019-01-07',
                        '2019-01-07/2020-12-01/P8D'),
                       ('Test_ForceAll', '2019-01-13',
                        '2019-01-07/2020-12-01/P8D')]
        db_keys = ['epsg4326']
        config = '2019-01-07/2020-12-01/P8D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_all_nodates(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_Force_All_No_Dates')]
        db_keys = ['epsg4326']
        config = '1900-01-01/2899-12-31/P1000Y'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                '1900-01-01/2899-12-31/P1000Y', layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_start(self):
        # Tests using force_start to forcibly select the first date
        test_layers = [('Test_ForceStart', '2019-01-01',
                        '2019-02-01/2019-03-01/P1M'),
                       ('Test_ForceStart', '2019-02-01',
                        '2019-02-01/2019-03-01/P1M'),
                       ('Test_ForceStart', '2019-03-01',
                        '2019-02-01/2019-03-01/P1M')]
        db_keys = ['epsg4326']
        config = '2019-02-01/DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_start_nodate(self):
        # Tests when there's no data for the forced start date (should still force the start date)
        test_layers = [('Test_ForceStart_NoDate', '2019-01-01',
                        '2017-01-01/2019-03-01/P1M'),
                       ('Test_ForceStart_NoDate', '2019-02-01',
                        '2017-01-01/2019-03-01/P1M'),
                       ('Test_ForceStart_NoDate', '2019-03-01',
                        '2017-01-01/2019-03-01/P1M')]
        db_keys = ['epsg4326']
        config = '2017-01-01/DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
    
    def test_periods_config_force_start_nodate_after_force_start(self):
        # Tests when there's no data for the forced start date (should still force the start date)
        test_layers = [('Test_ForceStart_NoDate_After_ForceStart', '2019-01-01',
                        '2017-01-01/2019-03-01/P1M'),
                       ('Test_ForceStart_NoDate_After_ForceStart', '2019-02-01',
                        '2017-01-01/2019-03-01/P1M'),
                       ('Test_ForceStart_NoDate_After_ForceStart', '2019-03-01',
                        '2017-01-01/2019-03-01/P1M')]
        db_keys = ['epsg4326']
        config = '2019-01-01/2019-03-01/P1M'
        add_redis_config(test_layers, db_keys, config)
        config = '2021-01-01/DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)

        periods = ['2019-01-01/2019-03-01/P1M']

        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_end(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_ForceEnd', '2018-12-01',
                        '2018-12-01/2020-12-01/P1M'),
                       ('Test_ForceEnd', '2019-01-01',
                        '2018-12-01/2020-12-01/P1M'),
                       ('Test_ForceEnd', '2019-02-01',
                        '2018-12-01/2020-12-01/P1M')]
        db_keys = ['epsg4326']
        config = 'DETECT/2020-12-01/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_latest_all(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_Latest', '2019-01-01',
                        '2018-12-29/2019-01-13/P1D',),
                       ('Test_Latest', '2019-01-07',
                        '2018-12-29/2019-01-13/P1D'),
                       ('Test_Latest', '2019-01-13',
                        '2018-12-29/2019-01-13/P1D')]
        db_keys = ['epsg4326']
        config = 'LATEST-15D/LATEST/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                f'Layer {layer[0]} not found in list of all layers')
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                f'Layer {layer[0]} has incorrect "period" value -- got {layer_res["periods"][0]}, expected {layer[2]}')
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_latest_start(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_Latest_Start', '2019-01-01',
                        ['2018-12-06/2019-01-03/P1D', 
                        '2019-01-05/2019-01-05/P1D']),
                        ('Test_Latest_Start', '2019-01-02',
                        ['2018-12-06/2019-01-03/P1D', 
                        '2019-01-05/2019-01-05/P1D']),
                        ('Test_Latest_Start', '2019-01-03',
                        ['2018-12-06/2019-01-03/P1D', 
                        '2019-01-05/2019-01-05/P1D']),
                        ('Test_Latest_Start', '2019-01-05',
                        ['2018-12-06/2019-01-03/P1D', 
                        '2019-01-05/2019-01-05/P1D'])]
        db_keys = ['epsg4326']
        config = 'LATEST-30D/DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                f'Layer {layer[0]} not found in list of all layers')
            self.assertEqual(
                layer[2], layer_res['periods'],
                f'Layer {layer[0]} has incorrect "period" value -- got {layer_res["periods"]}, expected {layer[2]}')
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_force_latest_end(self):
        # Test adding layer with multiple dates
        test_layers = [('Test_Latest_End', '2019-01-01',
                        ['2019-01-01/2019-01-02/P1D', 
                        '2019-01-05/2019-01-05/P1D']),
                       ('Test_Latest_End', '2019-01-02',
                        ['2019-01-01/2019-01-02/P1D', 
                        '2019-01-05/2019-01-05/P1D']),
                       ('Test_Latest_End', '2019-01-05',
                        ['2019-01-01/2019-01-02/P1D', 
                        '2019-01-05/2019-01-05/P1D'])]
        db_keys = ['epsg4326']
        config = 'DETECT/LATEST/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                f'Layer {layer[0]} not found in list of all layers')
            self.assertEqual(
                layer[2], layer_res['periods'],
                f'Layer {layer[0]} has incorrect "period" value -- got {layer_res["periods"]}, expected {layer[2]}')
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_multiple(self):
        # Test adding layer with multiple configs
        test_layers = [('Test_Multiple', '2019-01-01',
                        '2019-01-01/2019-01-01/P1D'),
                       ('Test_Multiple', '2019-01-02',
                        '2019-01-01/2019-01-04/P1D'),
                       ('Test_Multiple', '2019-01-03',
                        '2019-01-02/2019-01-04/P1D'),
                       ('Test_Multiple', '2019-01-04',
                        '2019-01-04/2022-12-01/P1M')]
        db_keys = ['epsg4326']
        # forced period
        config = '2019-01-01/2019-01-01/P1D'
        add_redis_config(test_layers, db_keys, config)
        # detect 2019-01-01 as start
        config = 'DETECT/2019-01-04/P1D'
        add_redis_config(test_layers, db_keys, config)
        # detect 2019-01-04 as end
        config = '2019-01-02/DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)
        # forced period
        config = '2019-01-04/2022-12-01/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for i, layer in enumerate(test_layers):
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][i],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][i], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_multiple_subdaily(self):
        # Test multiple configs on subdaily times
        num_dates = 127400
        date_start = datetime.datetime(2021, 1, 26, 10, 40, 0, 0)
        # calculate the datetimes between 2021-01-26T10:40:00 and 2023-06-30T03:50:00
        date_lst = [str((date_start + datetime.timedelta(minutes=idx * 10))) for idx in range(num_dates)]
        # add the "T" between the date and the time
        for i in range(len(date_lst)):
            date_lst[i] = date_lst[i][:10] + 'T' + date_lst[i][11:]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Multiple_Config_Subdaily', date_entry))
        db_keys = ['epsg4326']
        config = '2021-09-13T09:50:00/2021-09-14T09:20:00/PT10M'
        add_redis_config(test_layers, db_keys, config)
        config = '2021-09-30T16:00:00/2021-09-30T16:00:00/PT10M'
        add_redis_config(test_layers, db_keys, config)
        config = '2021-12-19T00:00:00/2022-01-17T00:00:00/PT10M'
        add_redis_config(test_layers, db_keys, config)
        config = '2023-02-21T00:00:00/2023-02-28T23:50:00/PT10M'
        add_redis_config(test_layers, db_keys, config)
        config = 'LATEST-90D/LATEST/PT10M'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2021-09-13T09:50:00Z/2021-09-14T09:20:00Z/PT10M',
                    '2021-09-30T16:00:00Z/2021-09-30T16:00:00Z/PT10M',
                    '2021-12-19T00:00:00Z/2022-01-17T00:00:00Z/PT10M',
                    '2023-02-21T00:00:00Z/2023-02-28T23:50:00Z/PT10M',
                    '2023-04-01T03:50:00Z/2023-06-30T03:50:00Z/PT10M'
                    ]
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_config_latest_no_dates(self):
        # Tests that using LATEST when there are no dates available will successfully return no periods
        layer_name = 'Test_Periods_Config_Latest_No_Dates'
        db_keys = ['epsg4326']
        config = 'LATEST-90D/LATEST/PT10M'
        add_redis_config([[layer_name]], db_keys, config)
        seed_redis_data([[layer_name]], db_keys=db_keys)
        
        periods = []
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        layer_res = res.get(layer_name)
        self.assertIsNotNone(
            layer_res,
            'Layer {0} not found in list of all layers'.format(layer_name))
        self.assertEqual(
            periods, layer_res['periods'],
            'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
            .format(layer_name, layer_res['periods'], periods))
        if not DEBUG:
            remove_redis_layer([layer_name], db_keys)
    
    def test_periods_config_multiple_force_latest_subdaily(self):
        # Test multiple configs on subdaily times with forced periods
        num_dates = 127400
        date_start = datetime.datetime(2021, 5, 29, 0, 0, 0, 0)
        # calculate the datetimes between 2021-01-26T10:40:00 and 2023-06-30T03:50:00
        date_lst = [str((date_start + datetime.timedelta(minutes=idx * 10))) for idx in range(num_dates)]
        # add the "T" between the date and the time, and also remove some entries to test whether its looking for breaks in periods
        date_lst_filtered = []
        for i in range(len(date_lst)):
            # arbitrarily remove every 10th and every 11th entries
            if i % 10 == 0 or i % 11 == 0:
                date_lst_filtered.append(date_lst[i][:10] + 'T' + date_lst[i][11:])
        test_layers = []
        for date_entry in date_lst_filtered:
            test_layers.append(('Test_Multiple_Config_Force_Latest_Subdaily', date_entry))
        db_keys = ['epsg4326']
        config = '2021-05-29T05:00:00/2022-01-16T23:50:00/PT10M'
        add_redis_config(test_layers, db_keys, config)
        config = '2022-01-17T00:00:00/LATEST/PT10M'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2021-05-29T05:00:00Z/2022-01-16T23:50:00Z/PT10M',
                    '2022-01-17T00:00:00Z/2023-10-30T15:50:00Z/PT10M'
                    ]
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
    
    def test_periods_lone_start_date_detect_all_days(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        num_dates = 30
        date_start = datetime.datetime(2022, 6, 27)
        # calculate the datetimes between 2022-06-27 and 2023-07-26
        date_lst = [str((date_start + datetime.timedelta(days=idx)).date()) for idx in range(num_dates)]
        date_lst = ["2022-06-21"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_Days', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2022-06-21/2022-06-21/P1D',
                    '2022-06-27/2022-07-26/P1D']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_4_days(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        # and it should be detected to be a 4-day period
        num_dates = 30
        date_start = datetime.datetime(2022, 6, 27)
        # calculate the datetimes between 2022-06-27 and 2022-10-21
        date_lst = [str((date_start + datetime.timedelta(days=idx * 4)).date()) for idx in range(num_dates)]
        date_lst = ["2022-06-21"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_4_Days', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2022-06-21/2022-06-21/P4D',
                    '2022-06-27/2022-10-21/P4D']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_8_days(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        # and it should be detected to be an 8-day period
        num_dates = 30
        date_start = datetime.datetime(2022, 6, 27)
        # calculate the datetimes between 2022-06-27 and 2023-02-14
        date_lst = [str((date_start + datetime.timedelta(days=idx * 8)).date()) for idx in range(num_dates)]
        date_lst = ["2022-06-10"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_8_Days', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2022-06-10/2022-06-10/P8D',
                    '2022-06-27/2023-02-14/P8D']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_16_days(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        # and it should be detected to be an 16-day period
        num_dates = 30
        date_start = datetime.datetime(2022, 6, 27)
        # calculate the datetimes between 2022-06-27 and 2023-10-04
        date_lst = [str((date_start + datetime.timedelta(days=idx * 16)).date()) for idx in range(num_dates)]
        date_lst = ["2022-06-01"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_16_Days', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2022-06-01/2022-06-01/P16D',
                    '2022-06-27/2023-10-04/P16D']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_months(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        num_dates = 30
        date_start = datetime.datetime(2020, 6, 1)
        # calculate the datetimes between 2020-06-01 and 2023-07-26
        date_lst = [str((date_start + relativedelta(months=idx)).date()) for idx in range(num_dates)]
        date_lst = ["2020-01-01"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_Months', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2020-01-01/2020-01-01/P1M',
                    '2020-06-01/2022-11-01/P1M']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_3_months(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        num_dates = 30
        date_start = datetime.datetime(2020, 6, 1)
        # calculate the datetimes between 2020-06-01 and 2027-09-01
        date_lst = [str((date_start + relativedelta(months=idx * 3)).date()) for idx in range(num_dates)]
        date_lst = ["2020-01-01"] + date_lst
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_3_Months', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2020-01-01/2020-01-01/P3M',
                    '2020-06-01/2027-09-01/P3M']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_seconds(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        num_dates = 30
        date_start = datetime.datetime(2021, 1, 26, 10, 40, 0, 0)
        # calculate the datetimes between 2021-01-26T10:40:00 and 2021-01-26T10:40:30
        date_lst = [str((date_start + datetime.timedelta(seconds=idx))) for idx in range(num_dates)]
        # add the "T" between the date and the time
        for i in range(len(date_lst)):
            date_lst[i] = date_lst[i][:10] + 'T' + date_lst[i][11:]
        date_lst = ["2021-01-26T10:00:00"] + date_lst + ["2021-01-26T10:41:00"]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_seconds', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2021-01-26T10:00:00Z/2021-01-26T10:00:00Z/PT1S',
                    '2021-01-26T10:40:00Z/2021-01-26T10:40:29Z/PT1S',
                    '2021-01-26T10:41:00Z/2021-01-26T10:41:00Z/PT1S']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_lone_start_date_detect_all_minutes(self):
        # Test when there's a gap between the earliest date and the rest of the dates
        # and there's no period interval duration specified in the time config
        num_dates = 30
        date_start = datetime.datetime(2021, 1, 26, 10, 40, 0, 0)
        # calculate the datetimes between 2021-01-26T10:40:00 and 2021-01-26T15:30:00
        date_lst = [str((date_start + datetime.timedelta(seconds=idx * 600))) for idx in range(num_dates)]
        # add the "T" between the date and the time
        for i in range(len(date_lst)):
            date_lst[i] = date_lst[i][:10] + 'T' + date_lst[i][11:]
        date_lst = ["2021-01-26T10:00:00"] + date_lst + ["2021-01-27T10:40:00"]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Lone_Start_Date_Detect_All_minutes', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2021-01-26T10:00:00Z/2021-01-26T10:00:00Z/PT10M',
                    '2021-01-26T10:40:00Z/2021-01-26T15:30:00Z/PT10M',
                    '2021-01-27T10:40:00Z/2021-01-27T10:40:00Z/PT10M']
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
    
    def test_periods_force_detect_8_days(self):
        # Test when we force many periods and then detect the last one for 8-day periods
        num_years = 23
        num_dates_per_year = 45
        date_lst = []
        for i in range(num_years):
            date_start = datetime.datetime(2000 + i, 1, 1)
            date_lst = date_lst + [str((date_start + datetime.timedelta(days=idx * 8)).date()) for idx in range(num_dates_per_year)]
        date_lst = date_lst + [str((datetime.datetime(2023, 1, 1) + datetime.timedelta(days=idx * 8)).date()) for idx in range(32)]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('test_periods_force_detect_8_days', date_entry))
        db_keys = ['epsg4326']
        
        config = '2000-02-26/2000-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2001-01-01/2001-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2002-01-01/2002-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2003-01-01/2003-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2004-01-01/2004-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2005-01-01/2005-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2006-01-01/2006-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2007-01-01/2007-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2008-01-01/2008-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2009-01-01/2009-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2010-01-01/2010-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2011-01-01/2011-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2012-01-01/2012-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2013-01-01/2013-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2014-01-01/2014-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2015-01-01/2015-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2016-01-01/2016-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2017-01-01/2017-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2018-01-01/2018-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2019-01-01/2019-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2020-01-01/2020-12-26/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2021-01-01/2021-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2022-01-01/2022-12-27/P8D'
        add_redis_config(test_layers, db_keys, config)
        config = '2023-01-01/DETECT/P8D'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2000-02-26/2000-12-26/P8D',
                    '2001-01-01/2001-12-27/P8D',
                    '2002-01-01/2002-12-27/P8D',
                    '2003-01-01/2003-12-27/P8D',
                    '2004-01-01/2004-12-26/P8D',
                    '2005-01-01/2005-12-27/P8D',
                    '2006-01-01/2006-12-27/P8D',
                    '2007-01-01/2007-12-27/P8D',
                    '2008-01-01/2008-12-26/P8D',
                    '2009-01-01/2009-12-27/P8D',
                    '2010-01-01/2010-12-27/P8D',
                    '2011-01-01/2011-12-27/P8D',
                    '2012-01-01/2012-12-26/P8D',
                    '2013-01-01/2013-12-27/P8D',
                    '2014-01-01/2014-12-27/P8D',
                    '2015-01-01/2015-12-27/P8D',
                    '2016-01-01/2016-12-26/P8D',
                    '2017-01-01/2017-12-27/P8D',
                    '2018-01-01/2018-12-27/P8D',
                    '2019-01-01/2019-12-27/P8D',
                    '2020-01-01/2020-12-26/P8D',
                    '2021-01-01/2021-12-27/P8D',
                    '2022-01-01/2022-12-27/P8D',
                    '2023-01-01/2023-09-06/P8D']

        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
        
    def test_periods_force_start_skip_gaps(self):
        # Test that periods are detected properly when the start date is forced,
        # the end date is DETECT, and there are gaps in the dates that are being skipped by "force start"
        num_groups = 23
        num_dates_per_group = 25
        date_lst = []
        for i in range(num_groups):
            date_start = datetime.datetime(2000 + i, 1, 1)
            date_lst = date_lst + [str((date_start + datetime.timedelta(days=idx + i)).date()) for idx in range(num_dates_per_group)]
        date_lst = date_lst + [str((datetime.datetime(2023, 1, 1) + datetime.timedelta(days=idx)).date()) for idx in range(33)]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('test_periods_force_start_skip_gaps', date_entry))
        db_keys = ['epsg4326']

        config = '2023-01-01/DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)

        periods = ['2023-01-01/2023-02-02/P1D']

        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                periods, layer_res['periods'],
                'Layer {0} has incorrect "periods" -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'], periods))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_truncate(self):
        # Test that the list of periods is truncated to the most recent 100 if there are more than 100 periods
        num_dates = 150
        date_start = datetime.datetime(2010, 6, 1)
        # calculate 100 datetimes
        date_lst = [str((date_start + relativedelta(months=idx)).date()) for idx in range(num_dates)]
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Truncate', date_entry))
        db_keys = ['epsg4326']
        config = 'DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)

        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                100, len(layer_res['periods']),
                'Layer {0} has incorrect number of "periods" -- got {1}, expected 100'
                .format(layer[0], len(layer_res['periods'])))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_stress_days(self):
        # Test adding a huge amount of dates
        num_dates = 100000
        date_start = datetime.datetime(2000, 1, 1)
        date_lst = [str((date_start + datetime.timedelta(days=idx)).date()) for idx in range(num_dates)]
        period = str(date_start.date()) + '/' + date_lst[-1] + '/P1D'
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Stress_Days', date_entry, period))
        db_keys = ['epsg4326']
        config = 'DETECT/DETECT/P1D'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)

    def test_periods_stress_months(self):
        # Test adding a huge amount of dates
        num_dates = 10000
        date_start = datetime.datetime(1970, 1, 1)
        date_lst = [str((date_start + relativedelta(months=idx)).date()) for idx in range(num_dates)]
        period = str(date_start.date()) + '/' + date_lst[-1] + '/P1M'
        test_layers = []
        for date_entry in date_lst:
            test_layers.append(('Test_Stress_Months', date_entry, period))
        db_keys = ['epsg4326']
        config = 'DETECT/DETECT/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in test_layers:
            layer_res = res.get(layer[0])
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                layer[2], layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
   
    def test_copy_periods(self):
        # Test copy_periods
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        copy_destinations = ['Copy_Destination_1', 'Copy_Destination_2']
        for dest in copy_destinations:
            r.sadd('epsg4326:layer:Test_CopyPeriods:copy_periods', dest)

        test_layers = [('Test_CopyPeriods', '2018-12-01',
                        '2018-12-01/2020-12-01/P1M'),
                       ('Test_CopyPeriods', '2019-01-01',
                        '2018-12-01/2020-12-01/P1M'),
                       ('Test_CopyPeriods', '2019-02-01',
                        '2018-12-01/2020-12-01/P1M')]
        db_keys = ['epsg4326']
        config = 'DETECT/2020-12-01/P1M'
        add_redis_config(test_layers, db_keys, config)
        seed_redis_data(test_layers, db_keys=db_keys)
        r = requests.get(self.date_service_url + 'key1=epsg4326')
        res = r.json()
        for layer in copy_destinations + ['Test_CopyPeriods']:
            layer_res = res.get(layer)
            self.assertIsNotNone(
                layer_res,
                'Layer {0} not found in list of all layers'.format(layer[0]))
            self.assertEqual(
                '2018-12-01/2020-12-01/P1M', layer_res['periods'][0],
                'Layer {0} has incorrect "period" value -- got {1}, expected {2}'
                .format(layer[0], layer_res['periods'][0], layer[2]))
            if not DEBUG:
                remove_redis_layer(layer, db_keys)
    
    @classmethod
    def tearDownClass(self):
        if not DEBUG:
            os.remove(self.test_config_dest_path)
            os.remove(self.test_lua_config_location)
            os.remove(os.getcwd() + '/periods.lua')


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_time_utils_results.xml',
        help='Specify XML output file (default is test_time_utils_results.xml'
    )
    parser.add_option(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        help='Output verbose debugging messages')
    (options, args) = parser.parse_args()

    DEBUG = options.debug

    # Have to delete the arguments as they confuse unittest
    del sys.argv[1:]

    with open(options.outfile, 'wb') as f:
        print('\nStoring test results in "{0}"'.format(options.outfile))
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=f))
