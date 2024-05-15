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
            if not DEBUG:
                remove_redis_layer(test_layer)
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

    def test_periods_begin_limit(self):
        # Test data
        limit = 100
        num_periods = 1000
        periods = []
        for i in range(0,num_periods):
            periods += ['{0}-01-01/{0}-01-01/P1Y'.format(str(i + 2000))]
        
        test_layers = [('test_begin_limit', '2012-01-01',
                        periods, '2013-06-06',
                        '2013-01-01T00:00:00Z')]
        seed_redis_data(test_layers)

        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}'.
                             format(test_layer[0], limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                len(returned_periods), abs(limit),
                'Error with using the \'limit\' option: {0} periods were returned, when there should have been {1}'
                .format(len(returned_periods), abs(limit)))
            self.assertEqual(
                returned_periods, periods[:limit],
                'Error with using the \'limit\' option: the periods in the returned list were not the {0} first periods in ascending order.'.format(abs(limit)))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], num_periods,
                'Error: the returned value for \'periods_in_range\' was {0} when it should have been {1}.'.format(res[test_layer[0]]['periods_in_range'], num_periods)
            )

    def test_periods_end_limit(self):
        # Test data
        limit = -100
        num_periods = 1000
        periods = []
        for i in range(0,num_periods):
            periods += ['{0}-01-01/{0}-01-01/P1Y'.format(str(i + 2000))]
        
        test_layers = [('test_end_limit', '2012-01-01',
                        periods, '2013-06-06',
                        '2013-01-01T00:00:00Z')]
        seed_redis_data(test_layers)

        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}'.
                             format(test_layer[0], limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                len(returned_periods), abs(limit),
                'Error with using the \'limit\' option: {0} periods were returned, when there should have been {1}'
                .format(len(returned_periods), abs(limit)))
            self.assertEqual(
                returned_periods, periods[limit:],
                'Error with using the \'limit\' option: the periods in the returned list were not the {0} most recent periods in ascending order.'.format(abs(limit)))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], num_periods,
                'Error: the returned value for \'periods_in_range\' was {0} when it should have been {1}.'.format(res[test_layer[0]]['periods_in_range'], num_periods)
            )

    def test_periods_larger_begin_limit(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        limit = 50
        test_layers = [('test_larger_begin_limit', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}'.
                             format(test_layer[0], limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, periods,
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, periods))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )

    def test_periods_larger_end_limit(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        limit = -50
        test_layers = [('test_larger_end_limit', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}'.
                             format(test_layer[0], limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, periods,
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, periods))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )

    def test_periods_skip(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        skip = 4
        test_layers = [('test_periods_skip', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&skip={1}'.
                             format(test_layer[0], skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, periods[skip:],
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, periods[skip + 1:]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )

    def test_periods_skip_all(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        skip = 20
        test_layers = [('test_periods_skip_all', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&skip={1}'.
                             format(test_layer[0], skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, [],
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, []))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )

    def test_periods_begin_limit_skip(self):
        # Test data
        limit = 100
        skip = 50
        num_periods = 1000
        periods = []
        for i in range(0,num_periods):
            periods += ['{0}-01-01/{0}-01-01/P1Y'.format(str(i + 2000))]
        
        test_layers = [('test_begin_limit_skip', '2012-01-01',
                        periods, '2013-06-06',
                        '2013-01-01T00:00:00Z')]
        seed_redis_data(test_layers)

        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}&skip={2}'.
                             format(test_layer[0], limit, skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                len(returned_periods), abs(limit),
                'Error with using the \'limit\' option with the \'skip\' option: {0} periods were returned, when there should have been {1}'
                .format(len(returned_periods), abs(limit)))
            self.assertEqual(
                returned_periods, periods[skip:skip + limit],
                'Error with using the \'limit\' option with the \'skip\' option: the periods in the returned list were not the periods between indices {0} and {1} in ascending order.'.format(skip, skip + limit, abs(limit)))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], num_periods,
                'Error: the returned value for \'periods_in_range\' was {0} when it should have been {1}.'.format(res[test_layer[0]]['periods_in_range'], num_periods)
            )

    def test_periods_end_limit_skip(self):
        # Test data
        limit = -100
        skip = 50
        num_periods = 1000
        periods = []
        for i in range(0,num_periods):
            periods += ['{0}-01-01/{0}-01-01/P1Y'.format(str(i + 2000))]
        
        test_layers = [('test_end_limit', '2012-01-01',
                        periods, '2013-06-06',
                        '2013-01-01T00:00:00Z')]
        seed_redis_data(test_layers)

        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}&skip={2}'.
                             format(test_layer[0], limit, skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                len(returned_periods), abs(limit),
                'Error with using the \'limit\' option: {0} periods were returned, when there should have been {1}'
                .format(len(returned_periods), abs(limit)))
            self.assertEqual(
                returned_periods, periods[limit - skip:-skip],
                'Error with using the \'limit\' option: the periods in the returned list were not the periods between indices {0} and {1} in ascending order.'.format(len(periods) + limit - skip, len(periods) - skip))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], num_periods,
                'Error: the returned value for \'periods_in_range\' was {0} when it should have been {1}.'.format(res[test_layer[0]]['periods_in_range'], num_periods)
            )

    def test_periods_larger_begin_limit_skip(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        limit = 50
        skip = 4
        test_layers = [('test_larger_begin_limit_skip', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}&skip={2}'.
                             format(test_layer[0], limit, skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, periods[skip:],
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, periods[skip + 1:]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )

    def test_periods_larger_end_limit_skip(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        limit = -50
        skip = 4
        test_layers = [('test_larger_end_limit_skip', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&limit={1}&skip={2}'.
                             format(test_layer[0], limit, skip))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, periods[:len(periods) - skip],
                'Error with requesting periods: got {0}, expected {1}.'.format(returned_periods, periods[:len(periods) - skip]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(periods),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(periods))
            )
    
    def test_periods_range(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P1D',
                    '2024-01-11/2024-01-17/P1D']
        start_date = '2024-01-03'
        end_date = '2024-01-14'
        expected_periods = ['2024-01-03/2024-01-07/P1D',
                            '2024-01-11/2024-01-14/P1D']
        test_layers = [('test_range', '2014-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_on_bounds(self):
        # Test data
        periods = ['2023-01-01/2023-12-01/P1D',
                    '2024-01-01/2024-12-01/P1D',
                    '2025-01-01/2025-12-01/P1D',
                    '2026-01-01/2026-12-01/P1D',
                    '2027-01-01/2027-12-01/P1D',
                    '2028-01-01/2028-12-01/P1D',
                    '2029-01-01/2029-12-01/P1D',
                    '2030-01-01/2030-12-01/P1D',]
        start_date = '2024-01-01'
        end_date = '2028-01-01'
        expected_periods = ['2024-01-01/2024-12-01/P1D',
                            '2025-01-01/2025-12-01/P1D',
                            '2026-01-01/2026-12-01/P1D',
                            '2027-01-01/2027-12-01/P1D',
                            '2028-01-01/2028-01-01/P1D']
        test_layers = [('test_range_on_bounds', '2030-12-01',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_single_period(self):
        # Test data
        periods = ['2024-01-01/2024-01-17/P1D']
        start_date = '2024-01-03'
        end_date = '2024-01-14'
        expected_periods = ['2024-01-03/2024-01-14/P1D']
        test_layers = [('test_range_single_period', '2014-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
    
    def test_periods_range_single_period_single_day(self):
        # Test data
        periods = ['2021-07-03/2021-07-03/P1D']
        start_date = '2021-07-01'
        end_date = '2021-07-14'
        expected_periods = ['2021-07-03/2021-07-03/P1D']
        test_layers = [('test_range_single_period_single_day', '2021-07-03',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
        
    def test_periods_range_start_only(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P1D',
                    '2024-01-11/2024-01-17/P1D']
        start_date = '2024-01-03'
        expected_periods = ['2024-01-03/2024-01-07/P1D',
                            '2024-01-11/2024-01-17/P1D']
        test_layers = [('test_range_start_only', '2014-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}'.
                             format(test_layer[0], start_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_end_only(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P1D',
                    '2024-01-11/2024-01-17/P1D']
        end_date = '2024-01-14'
        expected_periods = ['2024-01-01/2024-01-07/P1D',
                            '2024-01-11/2024-01-14/P1D']
        test_layers = [('test_range_end_only', '2014-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_end={1}'.
                             format(test_layer[0], end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_out_of_range(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P1D',
                    '2024-01-11/2024-01-17/P1D']
        start_date = '2004-01-03'
        end_date = '2004-01-14'
        expected_periods = []
        expected_default = ''
        test_layers = [('test_out_of_range', '2014-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            returned_default = res[test_layers[0][0]]['default']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods out-of-range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
            self.assertEqual(
                returned_default, expected_default,
                'Error with the returned default value for out-of-range periods: got {0}, expected {1}.'.format(returned_default, expected_default))

    def test_periods_range_snap(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D']
        start_date = '2024-01-02'
        end_date = '2024-01-14'
        expected_periods = ['2024-01-03/2024-01-07/P2D',
                            '2024-01-11/2024-01-13/P2D']
        test_layers = [('test_range', '2024-01-17',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_snap_time(self):
        # Test data
        periods = ['2024-01-01T00:00:00Z/2024-01-07T00:10:00Z/PT1M',
                    '2024-01-11T00:00:00Z/2024-01-17T21:22:20Z/PT10S']
        start_date = '2024-01-02T00:12:34Z'
        end_date = '2024-01-14T12:23:37Z'
        expected_periods = ['2024-01-02T00:13:00Z/2024-01-07T00:10:00Z/PT1M',
                            '2024-01-11T00:00:00Z/2024-01-14T12:23:30Z/PT10S']
        test_layers = [('test_range', '2024-01-17T21:22:20Z',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_snap_between_period_odd(self):
        # Test data
        periods = ['2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D']
        start_date = '2024-01-09'
        end_date = '2024-02-03'
        expected_periods = ['2024-01-11/2024-01-17/P2D']
        test_layers = [('test_range_between_period_odd', '2024-02-19',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(expected_periods),
                'Error: the returned value for \'periods_in_range\' was {0} when it should have been {1}.'.format(res[test_layer[0]]['periods_in_range'], len(expected_periods))
            )

    def test_periods_range_snap_between_period_even(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D']
        start_date = '2024-01-09'
        end_date = '2024-02-03'
        expected_periods = ['2024-01-11/2024-01-17/P2D']
        test_layers = [('test_range_between_period_even', '2024-02-19',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_no_data_between_range(self):
        # Test data
        periods = ['2023-01-01/2023-01-11/P10D']
        start_date = '2024-01-03'
        end_date = '2024-01-07'
        expected_periods = []
        test_layers = [('test_periods_no_data_between_range', '2024-01-11',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}'.
                             format(test_layer[0], start_date, end_date))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods where there is no data within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))

    def test_periods_range_all_layers(self):
        # Test data
        layer_1_periods = ['2023-02-05/2023-02-09/P2D',
                            '2024-01-01/2024-01-07/P2D',
                            '2024-01-11/2024-01-17/P2D',
                            '2024-02-13/2024-02-19/P2D',
                            '2024-03-05/2024-04-07/P1D',
                            '2024-04-12/2024-05-25/P1D']
        layer_2_periods = ['2023-01-01/2024-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-04-11/2024-04-17/P1D',
                            '2024-05-13/2024-05-19/P2D',
                            '2025-02-23/2025-07-12/P1D']
        layer_3_periods = ['2023-01-01/2023-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-05-03/2024-05-09/P1D',
                            '2025-02-23/2025-07-12/P1D']                            
        start_date = '2024-02-14'
        end_date = '2024-05-16'
        layer_1_expected_periods = ['2024-02-15/2024-02-19/P2D',
                                    '2024-03-05/2024-04-07/P1D',
                                    '2024-04-12/2024-05-16/P1D']
        layer_1_expected_default = '2024-02-15'
        layer_2_expected_periods = ['2024-03-01/2024-04-01/P1M',
                                    '2024-04-05/2024-04-09/P2D',
                                    '2024-04-11/2024-04-17/P1D',
                                    '2024-05-13/2024-05-15/P2D']
        layer_2_expected_default = '2024-05-15'
        layer_3_expected_periods = ['2024-04-05/2024-04-09/P2D',
                                    '2024-05-03/2024-05-09/P1D']
        layer_3_expected_default = '2024-05-09'
        test_layers = [('test_range_layer_1', '2024-02-05',
                        layer_1_periods, layer_1_expected_default,
                        layer_1_expected_periods),
                        ('test_range_layer_2', '2025-07-12',
                        layer_2_periods, layer_2_expected_default,
                         layer_2_expected_periods),
                        ('test_range_layer_3', '2024-05-09',
                        layer_3_periods, layer_3_expected_default,
                        layer_3_expected_periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'periods_start={0}&periods_end={1}'.
                             format(start_date, end_date))
            res = r.json()
            returned_periods = res[test_layer[0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, test_layer[4],
                'Error with requesting periods within a range: for layer {0}, got {1}, expected {2}.'.format(test_layer[0], returned_periods, test_layer[4]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(test_layer[4]),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(test_layer[4]))
            )
            self.assertEqual(
                res[test_layer[0]]['default'], test_layer[3],
                'Error: the returned value for \'default\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['default'], test_layer[3])
            )

    def test_periods_begin_limit_all_layers(self):
        # Test data
        layer_1_periods = ['2023-02-05/2023-02-09/P2D',
                            '2024-01-01/2024-01-07/P2D',
                            '2024-01-11/2024-01-17/P2D',
                            '2024-02-13/2024-02-19/P2D',
                            '2024-03-05/2024-04-07/P1D',
                            '2024-04-12/2024-05-25/P1D']
        layer_2_periods = ['2023-01-01/2024-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-04-11/2024-04-17/P1D',
                            '2024-05-13/2024-05-19/P2D',
                            '2025-02-23/2025-07-12/P1D']
        layer_3_periods = ['2023-01-01/2023-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-05-03/2024-05-09/P1D',
                            '2025-02-23/2025-07-12/P1D']                            
        limit = 2
        layer_1_expected_periods = ['2023-02-05/2023-02-09/P2D',
                                    '2024-01-01/2024-01-07/P2D']
        layer_1_expected_default = '2024-05-25'
        layer_2_expected_periods = ['2023-01-01/2024-04-01/P1M',
                                    '2024-04-05/2024-04-09/P2D']
        layer_2_expected_default = '2025-07-12'
        layer_3_expected_periods = ['2023-01-01/2023-04-01/P1M',
                                    '2024-04-05/2024-04-09/P2D']
        layer_3_expected_default = '2025-07-12'
        test_layers = [('test_begin_limit_layer_1', '2024-05-25',
                        layer_1_periods, layer_1_expected_default,
                        layer_1_expected_periods),
                        ('test_begin_limit_layer_2', '2025-07-12',
                        layer_2_periods, layer_2_expected_default,
                         layer_2_expected_periods),
                        ('test_begin_limit_layer_3', '2025-07-12',
                        layer_3_periods, layer_3_expected_default,
                        layer_3_expected_periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'limit={0}'.
                             format(limit))
            res = r.json()
            returned_periods = res[test_layer[0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            print("returned_periods:", returned_periods)
            print("test_layer[4]", test_layer[4])
            self.assertEqual(
                returned_periods, test_layer[4],
                'Error with requesting periods within a range: for layer {0}, got {1}, expected {2}.'.format(test_layer[0], returned_periods, test_layer[4]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(test_layer[2]),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(test_layer[2]))
            )
            self.assertEqual(
                res[test_layer[0]]['default'], test_layer[3],
                'Error: the returned value for \'default\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['default'], test_layer[3])
            )

    def test_periods_end_limit_all_layers(self):
        # Test data
        layer_1_periods = ['2023-02-05/2023-02-09/P2D',
                            '2024-01-01/2024-01-07/P2D',
                            '2024-01-11/2024-01-17/P2D',
                            '2024-02-13/2024-02-19/P2D',
                            '2024-03-05/2024-04-07/P1D',
                            '2024-04-12/2024-05-25/P1D']
        layer_2_periods = ['2023-01-01/2024-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-04-11/2024-04-17/P1D',
                            '2024-05-13/2024-05-19/P2D',
                            '2025-02-23/2025-07-12/P1D']
        layer_3_periods = ['2023-01-01/2023-04-01/P1M',
                            '2024-04-05/2024-04-09/P2D',
                            '2024-05-03/2024-05-09/P1D',
                            '2025-02-23/2025-07-12/P1D']                            
        limit = -2
        layer_1_expected_periods = ['2024-03-05/2024-04-07/P1D',
                                    '2024-04-12/2024-05-25/P1D']
        layer_1_expected_default = '2024-05-25'
        layer_2_expected_periods = ['2024-05-13/2024-05-19/P2D',
                                    '2025-02-23/2025-07-12/P1D']
        layer_2_expected_default = '2025-07-12'
        layer_3_expected_periods = ['2024-05-03/2024-05-09/P1D',
                                    '2025-02-23/2025-07-12/P1D']
        layer_3_expected_default = '2025-07-12'
        test_layers = [('test_end_limit_layer_1', '2024-05-25',
                        layer_1_periods, layer_1_expected_default,
                        layer_1_expected_periods),
                        ('test_end_limit_layer_2', '2025-07-12',
                        layer_2_periods, layer_2_expected_default,
                         layer_2_expected_periods),
                        ('test_end_limit_layer_3', '2025-07-12',
                        layer_3_periods, layer_3_expected_default,
                        layer_3_expected_periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'limit={0}'.
                             format(limit))
            res = r.json()
            returned_periods = res[test_layer[0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            print("returned_periods:", returned_periods)
            print("test_layer[4]", test_layer[4])
            self.assertEqual(
                returned_periods, test_layer[4],
                'Error with requesting periods within a range: for layer {0}, got {1}, expected {2}.'.format(test_layer[0], returned_periods, test_layer[4]))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], len(test_layer[2]),
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], len(test_layer[2]))
            )
            self.assertEqual(
                res[test_layer[0]]['default'], test_layer[3],
                'Error: the returned value for \'default\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['default'], test_layer[3])
            )

    def test_periods_range_begin_limit(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D']
        start_date = '2024-01-09'
        end_date = '2024-05-22'
        periods_in_range = 3
        expected_periods = ['2024-01-11/2024-01-17/P2D',
                            '2024-02-13/2024-02-19/P2D']
        limit = 2
        test_layers = [('test_range_begin_limit', '2024-06-29',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}&limit={3}'.
                             format(test_layer[0], start_date, end_date, limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], periods_in_range,
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], periods_in_range)
            )

    def test_periods_range_end_limit(self):
        # Test data
        periods = ['2023-01-01/2023-01-07/P2D',
                    '2024-01-01/2024-01-07/P2D',
                    '2024-01-11/2024-01-17/P2D',
                    '2024-02-13/2024-02-19/P2D',
                    '2024-05-12/2024-05-29/P1D',
                    '2024-06-23/2024-06-29/P1D',
                    '2024-07-24/2024-08-12/P1D']
        start_date = '2024-01-09'
        end_date = '2024-06-25'
        periods_in_range = 4
        expected_periods = ['2024-05-12/2024-05-29/P1D',
                            '2024-06-23/2024-06-25/P1D']
        limit = -2
        test_layers = [('test_range_end_limit', '2024-08-12',
                        periods)]
        seed_redis_data(test_layers)
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&periods_start={1}&periods_end={2}&limit={3}'.
                             format(test_layer[0], start_date, end_date, limit))
            res = r.json()
            returned_periods = res[test_layers[0][0]]['periods']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                returned_periods, expected_periods,
                'Error with requesting periods within a range: got {0}, expected {1}.'.format(returned_periods, expected_periods))
            self.assertEqual(
                res[test_layer[0]]['periods_in_range'], periods_in_range,
                'Error: the returned value for \'periods_in_range\' for layer {0} was {1} when it should have been {2}.'.format(test_layer[0], res[test_layer[0]]['periods_in_range'], periods_in_range)
            )

    def test_day_snap_range(self):
        test_layers = [
            # Snap date is before range
            ('test1_day_snap_range', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2012-01-02', 'Date out of range'),
            # Snap date is in range
            ('test2_day_snap_range', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2014-01-09', '2014-01-05T00:00:00Z'),
            # Snap date is after range
            ('test3_day_snap_range', '2012-01-01', '2012-01-01/2016-01-01/P7D',
             '2017-02-02', 'Date out of range')
        ]
        seed_redis_data(test_layers)

        periods_start = '2014-01-01'
        periods_end = '2015-01-01'

        # Test data
        for test_layer in test_layers:
            r = requests.get(self.date_service_url + 'layer={0}&datetime={1}&periods_start={2}&periods_end={3}'.
                             format(test_layer[0], test_layer[3], periods_start, periods_end))
            res = r.json()
            try:
                result = res['date']
            except:
                result = res['err_msg']
            if not DEBUG:
                remove_redis_layer(test_layer)
            self.assertEqual(
                result, test_layer[4],
                'Error with date snapping with a time range for layer {0}: for period {1}, date {2} was requested and date {3} was returned. Should be {4}'
                .format(test_layer[0], test_layer[2], test_layer[3], result,
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
