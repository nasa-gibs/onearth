#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script converts :periods keys from unsorted sets to sorted zsets and vice versa.
"""

import sys
import redis
import argparse

def convert_keys(redis_uri, redis_port, dest_type, layer_filter, verbose):
    r = redis.Redis(host=redis_uri, port=redis_port)
    pattern = '*layer:{}:periods'.format(layer_filter if layer_filter else '*')
    keys = list(r.scan_iter(match=pattern))
    converted = 0

    print("Found {0} periods keys matching pattern {1}.".format(len(keys), pattern))

    # Convert unsorted sets to sorted zsets
    if dest_type == 'zset':
        print("Beginning conversion to zset keys...")
        for key in keys:
            if verbose:
                print("Considering key", key)
            if r.type(key) == b'set':
                if verbose:
                    print(" - Converting from set to zset".format(key))
                # Use ZADD to first add all the key's periods to a temporary zset key
                key_temp = key + b'_temp'
                for period in r.sscan_iter(key):
                    r.zadd(key_temp, {period: 0})
                # Replace the existing unsorted set :periods key with the new zset key and delete the temp key
                r.copy(key_temp, key, replace=True)
                r.delete(key_temp)
                converted += 1
    
    # Convert sorted sets to unsorted sets
    elif dest_type == 'set':
        print("Beginning conversion to set keys...")
        for key in keys:
            if verbose:
                print("Considering key", key)
            if r.type(key) == b'zset':
                if verbose:
                    print(" - Converting from zset to set".format(key))
                # Use SADD to first add all the key's periods to a temporary set key
                key_temp = key + b'_temp'
                for period in r.zscan_iter(key):
                    r.sadd(key_temp, period[0])
                # Replace the existing sorted zset :periods key with the new set key and delete the temp key
                r.copy(key_temp, key, replace=True)
                r.delete(key_temp)
                converted += 1
    
    else:
        print("ERROR: Invalid --destination_type. Must be either 'set' or 'zset'.")
        sys.exit(1)
    
    print("SUCCESS: converted {0} keys to {1}. {2} keys were already the correct type.".format(converted, dest_type, len(keys) - converted))
    sys.exit(0)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Loads custom period configurations')
    parser.add_argument('-t', '--destination_type',
                        dest='destination_type',
                        type=str,
                        default='zset',
                        help='Type that the :periods keys should be converted to (zset or set)')
    parser.add_argument('-l', '--layer_filter',
                        dest='layer_filter',
                        default='*',
                        metavar='LAYER_FILTER',
                        type=str,
                        help='Unix style pattern to filter layer names')
    parser.add_argument('-p', '--port',
                        dest='port',
                        action='store',
                        default=6379,
                        help='Redis port for database')
    parser.add_argument('-r', '--redis_uri',
                        dest='redis_uri',
                        metavar='REDIS_URI',
                        type=str,
                        help='URI for the Redis database')
    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        dest="verbose", 
                        default=False,
                        help="Print out detailed log messages")
    args = parser.parse_args()
    convert_keys(args.redis_uri,
                    args.port,
                    args.destination_type,
                    args.layer_filter,
                    args.verbose)
