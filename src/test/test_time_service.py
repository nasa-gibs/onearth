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
# Tests for time service
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
from oe_test_utils import restart_apache, make_dir_tree, seed_redis_data, seed_redis_best_data

DEBUG = False

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


def redis_running():
    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        return r.ping()
    except redis.exceptions.ConnectionError:
        return False


def remove_redis_layer(layer, db_keys=None):
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    db_keystring = ''
    if db_keys:
        for key in db_keys:
            db_keystring += key + ':'
    r.delete('{0}layer:{1}:default'.format(db_keystring, layer[0]))
    r.delete('{0}layer:{1}:periods'.format(db_keystring, layer[0]))


class TestDateService(unittest.TestCase):
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

    def test_get_all_records(self):
        # Tests that a blank inquiry to the date service returns all records.
        test_layers = [('test1_all_records', '2012-01-01',
                        '2012-01-01/2016-01-01/P1Y'),
                       ('test2_all_records', '2015-02-01T12:00:00',
                        '2012-01-01T00:00:00/2016-01-01T23:59:59/PT1S')]

        seed_redis_data(test_layers)

        r = requests.get(self.date_service_url)
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
                remove_redis_layer(layer)

    def test_year_snap(self):
        test_layers = [('test1_year_snap', '2012-01-01',
                        '2012-01-01/2016-01-01/P1Y', '2013-06-06',
                        '2013-01-01T00:00:00Z'),
                       ('test2_year_snap', '2000-01-01',
                        '2000-01-01/2010-01-01/P5Y', '2006-05-05',
                        '2005-01-01T00:00:00Z')]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_day_snap(self):
        test_layers = [
            # Snap to beginning
            ('test1_day_snap', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2012-01-02', '2012-01-01T00:00:00Z'),
            # Snap to interval
            ('test2_day_snap', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2012-01-09', '2012-01-08T00:00:00Z'),
            # Snap across month
            ('test3_day_snap', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2012-02-02', '2012-01-29T00:00:00Z'),
            # Snap to a leap day
            ('test4_day_snap', '2012-02-19', '2012-02-19/2016-01-01/P10D',
             '2012-03-01', '2012-02-29T00:00:00Z'),
            ('test5_day_snap', '2013-02-19', '2013-02-19/2016-01-01/P10D',
             '2013-03-01', '2013-03-01T00:00:00Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_month_snap(self):
        test_layers = [
            # Snap to beginning
            ('test1_month_snap', '2012-01-01', '2012-01-01/2016-01-01/P1M',
             '2012-01-06', '2012-01-01T00:00:00Z'),
            # Snap to interval
            ('test2_month_snap', '2012-01-01', '2012-01-01/2016-01-01/P2M',
             '2012-04-09', '2012-03-01T00:00:00Z'),
            # Snap across year
            ('test3_year_snap', '2012-01-01', '2012-12-01/2016-01-01/P2M',
             '2013-01-01', '2012-12-01T00:00:00Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_hour_snap(self):
        test_layers = [
            # Snap to beginning
            ('test1_hour_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT2H',
             '2012-01-01T01:30:00Z', '2012-01-01T00:00:00Z'),
            # Snap to interval
            ('test2_hour_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT2H',
             '2012-01-01T02:30:00Z', '2012-01-01T02:00:00Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_minute_snap(self):
        test_layers = [
            # Snap to beginning
            ('test1_minute_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT6M',
             '2012-01-01T00:05:00Z', '2012-01-01T00:00:00Z'),
            # Snap to interval
            ('test2_minute_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT6M',
             '2012-01-01T00:14:00Z', '2012-01-01T00:12:00Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_second_snap(self):
        test_layers = [
            # Snap to beginning
            ('test1_second_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT11S',
             '2012-01-01T00:00:10Z', '2012-01-01T00:00:00Z'),
            # Snap to interval
            ('test2_second_snap', '2012-01-01T00:00:00',
             '2012-01-01T00:00:00/2016-01-01T00:00:00/PT11S',
             '2012-01-01T00:00:12Z', '2012-01-01T00:00:11Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    def test_bad_layer_error(self):
        r = requests.get(self.date_service_url +
                         'layer=hack_blowfist&datetime=2000-10-01')
        res = r.json()
        err_msg = res['err_msg']
        expected_err = 'Invalid Layer'
        self.assertEqual(
            err_msg, expected_err,
            'Incorrect error message returned for nonexistent layer: was {0}, should be {1}'
            .format(err_msg, expected_err))

    def test_bad_date_error(self):
        test_layer = ('test1_bad_date', '2012-01-01T00:00:00',
                      '2012-01-01T00:00:00/2016-01-01T00:00:00/PT2H',
                      '2012-01-01T01:30:00', '2012-01-01T00:00:00Z')

        seed_redis_data([test_layer])

        r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                         format(test_layer[0], test_layer[3]))
        res = r.json()
        err_msg = res['err_msg']
        expected_err = 'Invalid Date'
        self.assertEqual(
            err_msg, expected_err,
            'Incorrect error message bad date format: was {0}, should be {1}'.
            format(err_msg, expected_err))

        if not DEBUG:
            remove_redis_layer(test_layer)

    def test_out_of_range_error(self):
        test_layers = [
            # Before date range
            ('test1_out_of_range_err', '2012-01-01',
             '2012-01-01/2016-01-01/P1Y', '2010-01-01', None),
            # After date range
            ('test2_out_of_range_err', '2012-01-01',
             '2012-01-01/2016-01-01/P10D', '2016-01-11', None),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            err_msg = res['err_msg']
            expected_err = 'Date out of range'
            self.assertEqual(
                err_msg, expected_err,
                'Incorrect error message bad date format: was {0}, should be {1}'
                .format(err_msg, expected_err))

    def test_single_db_keys(self):
        test_layers = [('test1_year_snap', '2012-01-01',
                        '2012-01-01/2016-01-01/P1Y', '2013-06-06',
                        '2013-01-01T00:00:00Z'),
                       ('test2_year_snap', '2000-01-01',
                        '2000-01-01/2010-01-01/P5Y', '2006-05-05',
                        '2005-01-01T00:00:00Z')]

        db_keys = ['test_db_key_1', 'test_db_key_2']

        for key in db_keys:
            seed_redis_data(test_layers, db_keys=[key])
            # Test data
            for test_layer in test_layers:
                r = requests.get(self.date_service_url +
                                 'layer={0}&datetime={1}&key1={2}'.format(
                                     test_layer[0], test_layer[3], key))
                res = r.json()
                returned_date = res['date']
                if not DEBUG:
                    remove_redis_layer(test_layer, db_keys=[key])
                self.assertEqual(
                    returned_date, test_layer[4],
                    'Error with date snapping: for with key {0}, date {1} was requested and date {2} was returned. Should be {3}'
                    .format(key, test_layer[3], returned_date, test_layer[4]))


    def test_best_layer(self):
        test_layers = [('test1_year_snap', '2012-01-01',
                        '2012-01-01/2016-01-01/P1Y', '2013-06-06',
                        '2013-01-01T00:00:00Z'),
                       ('test2_year_snap', '2000-01-01',
                        '2000-01-01/2010-01-01/P5Y', '2006-05-05',
                        '2005-01-01T00:00:00Z')]

        db_keys = ['test_db_key_1', 'test_db_key_2']

        best_filename = 'filename_v6_STD'
        
        for key in db_keys:
            seed_redis_data(test_layers, db_keys=[key])
            seed_redis_best_data(test_layers, best_filename, db_keys=[key])
            # Test data
            for test_layer in test_layers:
                r = requests.get(self.date_service_url +
                                 'layer={0}&datetime={1}&key1={2}'.format(
                                     test_layer[0], test_layer[3], key))
                res = r.json()
                print(f'res = {res}')
                returned_date = res['date']
                returned_prefix = res['prefix']
                if not DEBUG:
                    remove_redis_layer(test_layer, db_keys=[key])
                self.assertEqual(
                    returned_prefix, best_filename,
                    f'Error with date snapping: for with key {key}, date {test_layer[3]} was requested and date {returned_prefix} was returned. Should be {best_filename}')
                self.assertEqual(
                    returned_date, test_layer[4],
                    'Error with date snapping: for with key {0}, date {1} was requested and date {2} was returned. Should be {3}'
                    .format(key, test_layer[3], returned_date, test_layer[4]))
                self.assertRegex(res['filename'], best_filename)


    def test_multiple_db_keys(self):
        test_layers = [('test1_year_snap', '2012-01-01',
                        '2012-01-01/2016-01-01/P1Y', '2013-06-06',
                        '2013-01-01T00:00:00Z'),
                       ('test2_year_snap', '2000-01-01',
                        '2000-01-01/2010-01-01/P5Y', '2006-05-05',
                        '2005-01-01T00:00:00Z')]

        db_keys = [
            'test_db_key_1', 'test_db_key_2', 'test_db_key_3', 'test_db_key_4',
            'test_db_key_5'
        ]

        seed_redis_data(test_layers, db_keys=db_keys)
        # Test data
        for test_layer in test_layers:
            r = requests.get(
                self.date_service_url +
                'layer={0}&datetime={1}&key1={2}&key2={3}&key3={4}&key4={5}&key5={6}'
                .format(test_layer[0], test_layer[3], db_keys[0], db_keys[1],
                        db_keys[2], db_keys[3], db_keys[4]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer, db_keys=db_keys)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for with keys {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(db_keys, test_layer[3], returned_date, test_layer[4]))

    def test_multiple_periods(self):
        test_layers = [
            ('test1_multiple_snap', '2000-12-01', [
                '2000-07-03/2000-07-03/P1M', '2000-01-01/2000-06-01/P1M',
                '2000-08-01/2000-12-01/P1M'
            ], '2000-08-01', '2000-08-01T00:00:00Z'),
            ('test2_multiple_snap', '2012-01-01',
             ['2001-01-01/2001-12-27/P8D', '2002-01-01/2002-12-27/P8D'],
             '2002-01-01', '2002-01-01T00:00:00Z'),
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))
            
    def test_static_best(self):
        test_layers = [
            ('test1_static_best', '2899-12-31', [
                '1900-01-01/2899-12-31/P1000Y',
            ], '2000-08-01', '1900-01-01T00:00:00Z')
        ]

        seed_redis_data(test_layers)

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}'.
                             format(test_layer[0], test_layer[3]))
            res = r.json()
            returned_date = res['date']
            returned_filename = res['filename']
            filename = test_layer[0]        
            if not DEBUG:
                remove_redis_layer(test_layer)            
            self.assertEqual(
                returned_filename, filename,
                f'Error with static best: date {test_layer[3]} was requested and filename {returned_filename} was returned. Should be {filename}')
            self.assertEqual(
                returned_date, test_layer[4],
                'Error with date snapping: for period {0}, date {1} was requested and date {2} was returned. Should be {3}'
                .format(test_layer[2], test_layer[3], returned_date,
                        test_layer[4]))

    @classmethod
    def tearDownClass(self):
        if not DEBUG:
            os.remove(self.test_config_dest_path)
            os.remove(self.test_lua_config_location)


if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option(
        '-o',
        '--output',
        action='store',
        type='string',
        dest='outfile',
        default='test_time_service_results.xml',
        help='Specify XML output file (default is test_time_service_results.xml'
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
