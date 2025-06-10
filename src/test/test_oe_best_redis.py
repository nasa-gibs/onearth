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
# Tests for oe_best_redis.py
#

import os
import sys
import unittest
import xmlrunner
from optparse import OptionParser
from subprocess import Popen
import time
import shutil
from datetime import datetime
import redis

# Copy required files to test directory
shutil.copyfile("/home/oe2/onearth/src/modules/time_service/utils/oe_redis_utl.py", os.getcwd() + '/oe_redis_utl.py')
shutil.copyfile("/home/oe2/onearth/src/modules/time_service/utils/oe_best_redis.py", os.getcwd() + '/oe_best_redis.py')

from oe_best_redis import calculate_layer_best
from oe_redis_utl import create_redis_client

def redis_running():
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        return r.ping()
    except redis.exceptions.ConnectionError:
        return False

class TestOEBestRedis(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # Start redis
        if not redis_running():
            Popen(['redis-server'])
        time.sleep(2)
        if not redis_running():
            print("WARNING: Can't access Redis server. Tests may fail.")
        self.host = 'localhost'
        self.port = 6379
        self.redis_client = create_redis_client(self.host, self.port, debug=True)
        if not self.redis_client:
            raise Exception("Failed to create Redis client")
    
    @classmethod
    def tearDown(self):
        # Clean up Redis after each test.
        if self.redis_client:
            self.redis_client.flushdb()


    def test_calculate_layer_best_with_new_datetime(self):
        """
        Test calculate_layer_best with new datetime
        """
        layer_key = "test:source_layer"
        best_layer = "best_layer"
        new_datetime = "2024-01-01T00:00:00"
        
        # Set up test data
        self.redis_client.set(f"{layer_key}:best_layer", best_layer)
        self.redis_client.zadd(f"test:{best_layer}:best_config", {"source_layer": 0})
        self.redis_client.zadd(f"{layer_key}:dates", {new_datetime: 0})
        # Run the function
        calculate_layer_best(self.redis_client, layer_key, new_datetime)
        
        # Verify results
        best_value = self.redis_client.hget(f"test:{best_layer}:best", new_datetime + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "source_layer")
        self.assertTrue(self.redis_client.zscore(f"test:{best_layer}:dates", new_datetime) == 0)

    def test_calculate_layer_best_with_no_best_layer(self):
        """
        Test calculate_layer_best when no best layer exists (should make itself be the best layer)
        """
        layer_key = "test:layer"
        new_datetime = "2024-01-01T00:00:00"
        self.redis_client.set(f"{layer_key}:best_layer", "layer")
        self.redis_client.zadd(f"{layer_key}:dates", {new_datetime: 0})
        
        # Run the function
        calculate_layer_best(self.redis_client, layer_key, new_datetime)
        
        # Verify results
        best_value = self.redis_client.hget(f"{layer_key}:best", new_datetime + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "layer")
        self.assertTrue(self.redis_client.zscore(f"{layer_key}:dates", new_datetime) == 0)

    def test_calculate_layer_best_with_multiple_source_layers(self):
        """
        Test calculate_layer_best with multiple source layers in best_config
        """
        layer_key1 = "test:source_layer1"
        layer_key2 = "test:source_layer2"
        best_layer = "best_layer"
        
        # Set up test data with two source layers
        self.redis_client.set(f"{layer_key1}:best_layer", best_layer)
        self.redis_client.set(f"{layer_key2}:best_layer", best_layer)
        self.redis_client.zadd(f"test:{best_layer}:best_config", {
            "source_layer1": 1,  # Higher priority
            "source_layer2": 0   # Lower priority
        })
        
        # Add dates to both source layers
        date1 = "2024-01-01T00:00:00"
        date2 = "2024-01-02T00:00:00"
        self.redis_client.zadd(f"{layer_key1}:dates", {date1: 0})
        self.redis_client.zadd(f"{layer_key2}:dates", {date2: 0})
        
        # Run the function
        calculate_layer_best(self.redis_client, layer_key1, date1)
        calculate_layer_best(self.redis_client, layer_key2, date2)
        
        # Verify results - should use source_layer1 since it has higher priority
        best_value = self.redis_client.hget(f"test:{best_layer}:best", date1 + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "source_layer1")
        best_value = self.redis_client.hget(f"test:{best_layer}:best", date2 + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "source_layer2")

    def test_calculate_layer_best_with_recalculation(self):
        """
        Test calculate_layer_best with recalculation when new_datetime is None
        """
        layer_key1 = "test:source_layer1"
        layer_key2 = "test:source_layer2"
        best_layer = "best_layer"
        
        # Set up test data with two source layers
        self.redis_client.set(f"{layer_key1}:best_layer", best_layer)
        self.redis_client.set(f"{layer_key2}:best_layer", best_layer)
        self.redis_client.zadd(f"test:{best_layer}:best_config", {
            "source_layer1": 1,  # Higher priority
            "source_layer2": 0   # Lower priority
        })
        
        # Add dates to both source layers
        date1 = "2024-01-01T00:00:00"
        date2 = "2024-01-02T00:00:00"
        self.redis_client.zadd(f"{layer_key1}:dates", {date1: 0})
        self.redis_client.zadd(f"{layer_key2}:dates", {date1: 0})
        self.redis_client.zadd(f"{layer_key2}:dates", {date2: 0})
        
        # Add some initial best values
        self.redis_client.hmset(f"test:{best_layer}:best", {
            date1 + 'Z': 'source_layer2',  # This should be overwritten
            date2 + 'Z': 'source_layer2'   # This should be overwritten
        })
        self.redis_client.zadd(f"test:{best_layer}:dates", {date1: 0, date2: 0})
        
        # Run the function with no datetime to trigger recalculation
        calculate_layer_best(self.redis_client, f"test:{best_layer}", None)
        
        # Verify results - best values should be recalculated based on priority
        best_value = self.redis_client.hget(f"test:{best_layer}:best", date1 + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "source_layer1")
        best_value = self.redis_client.hget(f"test:{best_layer}:best", date2 + 'Z')
        self.assertEqual(best_value.decode('utf-8'), "source_layer2")
        
        # Verify dates are still present
        self.assertTrue(self.redis_client.zscore(f"test:{best_layer}:dates", date1) == 0)
        self.assertTrue(self.redis_client.zscore(f"test:{best_layer}:dates", date2) == 0)

    def test_calculate_layer_best_with_missing_date(self):
        """
        Test calculate_layer_best when a date is missing from source layers
        """
        layer_key = "test:layer"
        best_layer = "best_layer"
        new_datetime = "2024-01-01T00:00:00Z"
        
        # Set up test data without the date in source layer
        self.redis_client.set(f"{layer_key}:best_layer", best_layer)
        self.redis_client.zadd(f"test:{best_layer}:best_config", {"source_layer": 0})
        
        # Run the function
        calculate_layer_best(self.redis_client, layer_key, new_datetime)
        
        # Verify the date was not added to best keys
        self.assertFalse(self.redis_client.hexists(f"test:{best_layer}:best", new_datetime))
        self.assertFalse(self.redis_client.zscore(f"test:{best_layer}:dates", new_datetime))



if __name__ == '__main__':
    # Parse options before running tests
    parser = OptionParser()
    parser.add_option('-o', '--output', action='store', type='string', dest='outfile',
                      default='test_results.xml',
                      help='Specify XML output file (default: test_results.xml)')
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
