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

import argparse
import re
import logging
from oe_redis_utl import create_redis_client

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Alternate syntax for regenerating :best and :dates keys for a best layer:
# This will clear existing :best and :dates keys for the best layer and regenerate them
# based on the :dates keys the layers specified by layer_prefix:best_layer_name:best_config.
def calculate_layer_best(redis_cli, layer_key, new_datetime, debug=False):
  logger.setLevel(logging.DEBUG if debug else logging.INFO)
  logger.info(f'Creating besting linking for {layer_key}')

  prefix_match = re.match(r'(.*):', layer_key)
  layer_prefix = prefix_match.group(1)

  if redis_cli.exists(f'{layer_key}:best_layer') and new_datetime is not None:
    best_layer = redis_cli.get(f'{layer_key}:best_layer').decode('utf-8')
    best_key = f'{layer_prefix}:{best_layer}'

    # If no best_config exists, then add this config as the only best_config
    if not redis_cli.exists(f'{best_key}:best_config'):
      redis_cli.zadd(f'{best_key}:best_config', {layer_key.split(':')[-1]: 0})
    
    # Get layers in reverse, higher score have priority 
    layers = redis_cli.zrevrange(f'{best_key}:best_config', 0, -1)
    logger.info(f'Checking layers for {best_key}:best_config is {layers}')
    found = False
    
    #Loops through best_config layers, checks if date exist
    for layer in layers:
      logger.info(f'Checking ZSCORE for {layer_prefix}:{layer.decode("utf-8")}:dates for {new_datetime}')
      score = redis_cli.zscore(f'{layer_prefix}:{layer.decode("utf-8")}:dates', new_datetime)
      if score is not None:
        # Update :best hset with date and best layer
        redis_cli.hmset(f'{best_key}:best', {f'{new_datetime}Z': layer.decode('utf-8')})
        # Add date to best_layer:dates zset
        redis_cli.zadd(f'{best_key}:dates', {new_datetime: 0})
        found = True
        break

    #if the date is not found within layers of best_config key or the key was deleted
    if not found:
      redis_cli.hdel(f'{best_key}:best', f'{new_datetime}Z') # best dates have a Z
      redis_cli.zrem(f'{best_key}:dates', new_datetime)
      logger.warning(f'Deleted or not configured, removing Best LAYER: {best_key} DATE: {new_datetime}')

  # if not best_layer, then recalculate :best and :dates keys for best layer based on the :dates keys of the layers listed in :best_config
  elif new_datetime is None:
    source_layers = redis_cli.zrange(f'{layer_key}:best_config', 0, -1)
    if source_layers:
      redis_cli.delete(f'{layer_key}::best')
      redis_cli.delete(f'{layer_key}:dates')
      for source_layer in source_layers:
        source_layer_key = f'{layer_prefix}:{source_layer.decode("utf-8")}'
        dates = redis_cli.zrange(f'{source_layer_key}:dates', 0, -1)
        for date in dates:
          redis_cli.hmset(f'{layer_key}:best', {date, source_layer.decode('utf-8')})
          redis_cli.zadd(f'{layer_key}:dates', {new_datetime: 0})


# Main routine to be run in CLI mode
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Loads custom period configurations')
    parser.add_argument('layer_key',
                        help='layer_prefix:layer_name that best should be calculated for best keys')
    parser.add_argument('-d', '--datetime',
                        dest='new_datetime',
                        metavar='NEW_DATETIME',
                        type=str,
                        help='New datetime that is to be added as a best keys for this layer')
    parser.add_argument('-p', '--port',
                        dest='port',
                        action='store',
                        default=6379,
                        help='redis port for database')
    parser.add_argument('-r', '--redis_uri',
                        dest='redis_uri',
                        metavar='REDIS_URI',
                        type=str,
                        help='URI for the Redis database')
    parser.add_argument('-v', '--verbose',
                        dest='debug',
                        action='store_true',
                        default=False,
                        help='Print additional log messages')
    args = parser.parse_args()

    redis_cli = create_redis_client(host=args.redis_uri, port=args.redis_port, debug=args.debug)

    calculate_layer_best(redis_cli,
                            args.layer_key,
                            args.new_datetime,
                            args.debug
                        )
    if redis_cli: redis_cli.close()