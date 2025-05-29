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

import logging
import redis

def create_redis_client(host, port=6379, debug=False):
    '''Create a Redis client that can connect to a Redis cluster or a standalone Redis instance.
    Args:
      host (str): The hostname or IP address of the Redis server.
      port (int): The port number of the Redis server. Default is 6379.
      debug (bool): If True, set logging level to DEBUG, otherwise INFO.
    Returns:
      redis.Redis or redis.RedisCluster: A Redis client instance.
    '''
    logging.basicConfig(level= logging.DEBUG if debug else logging.INFO,
                    format='%(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    client = None

    try:
        client = redis.RedisCluster(host, port)
    except redis.exceptions.RedisClusterException:
        logger.debug('Cluster not enabled, switch to non-clustered connection')
        client = redis.Redis(host, port)
    return client
