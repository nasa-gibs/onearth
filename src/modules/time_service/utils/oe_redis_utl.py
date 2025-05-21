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

import redis
import logging



def create_redis_client(host, port, debug=False):
  logging.basicConfig(level= logging.DEBUG if debug else logging.INFO,
                    format='%(levelname)s - %(message)s')
  logger = logging.getLogger(__name__)
  client = None
  
  try:
    client = redis.RedisCluster(host, port)
  except redis.exceptions.RedisClusterException:
    logger.debug(f'Cluster not enabled, switch to non-clustered connection')
    client = redis.Redis(host, port)
  return client