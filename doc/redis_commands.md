# OnEarth Redis Commands

Example commands for viewing and manipulating OnEarth time metadata in Redis. Note these need to be run on a system with access to the Redis host, usually within the time-service container.

```
# Log into Redis DB
/usr/bin/redis-cli -h $REDIS_HOST
 
# Set the default date for a layer
localhost:6379> SET epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default "2018-12-31"
OK
 
# Retrieve the default date for a layer
localhost:6379> MGET epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:default
 
# Add periods for a layer
localhost:6379> SADD epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2000-01-01/2012-09-01/P1D"
(integer) 1
localhost:6379> SADD epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods "2012-09-03/2018-12-31/P1D"
(integer) 1
 
# Retrieve periods for a layer
localhost:6379> SMEMBERS epsg4326:layer:MODIS_Aqua_CorrectedReflectance_Bands721:periods
1) "2012-09-03/2018-12-31/P1D"
2) "2000-01-01/2012-09-01/P1D"
 
localhost:6379> exit
 
 
# Add dates to a layer and automatically calculate periods - requires periods.lua script
# Load the periods.lua script
cd onearth/src/modules/time_service/utils/
/usr/bin/redis-cli -h $REDIS_HOST SCRIPT LOAD "$(cat periods.lua)"
 
"b86900dbf358533f2fcffdf279b5a048acb8e935"
 
# Add dates (at least 3 datetime values are required to determine a period vs. lone dates)
/usr/bin/redis-cli -h $REDIS_HOST ZADD epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:dates 0 "2012-09-10"
(integer) 1
/usr/bin/redis-cli -h $REDIS_HOST ZADD epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:dates 0 "2012-09-11"
(integer) 1
/usr/bin/redis-cli -h $REDIS_HOST ZADD epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:dates 0 "2012-09-12"
(integer) 1
 
# Invoke periods.lua script
/usr/bin/redis-cli -h $REDIS_HOST EVALSHA b86900dbf358533f2fcffdf279b5a048acb8e935 1 epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending
(nil)
 
# View dates
/usr/bin/redis-cli -h $REDIS_HOST ZRANGE epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:dates 0 -1
1) "2012-09-10T00:00:00"
2) "2012-09-11T00:00:00"
3) "2012-09-12T00:00:00"
 
# View periods
/usr/bin/redis-cli -h $REDIS_HOST SMEMBERS epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:periods
1) "2012-09-10/2012-09-12/P1D"
 
# View default date
/usr/bin/redis-cli -h $REDIS_HOST MGET epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:default
1) "2012-09-12"

# Regenerate :best and :dates keys for a best layer - requires best.lua script
# Load the best.lua script
cd onearth/src/modules/time_service/utils/
/usr/bin/redis-cli -h $REDIS_HOST SCRIPT LOAD "$(cat best.lua)"
 
"cd45a7aba09c5b6b59044efd92b0d627d63b04c4"

# Invoke best.lua script
/usr/bin/redis-cli -h $REDIS_HOST EVALSHA cd45a7aba09c5b6b59044efd92b0d627d63b04c4 epsg4326:layer:SMAP_L1_Passive_Faraday_Rotation_Aft
(nil)

# View best layers data
/usr/bin/redis-cli -h $REDIS_HOST hgetall epsg4326:layer:SMAP_L1_Passive_Faraday_Rotation_Aft:best
1) "2022-06-21T00:00:00"
2) "SMAP_L1_Passive_Faraday_Rotation_Aft_v5_NRT"
3) "2022-06-27T00:00:00"
4) "SMAP_L1_Passive_Faraday_Rotation_Aft_v5_NRT"
5) "2022-06-28T00:00:00"
6) "SMAP_L1_Passive_Faraday_Rotation_Aft_v5_NRT"

# Delete a date
/usr/bin/redis-cli -h $REDIS_HOST ZREM epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:dates "2012-09-12"
(integer) 1
 
# Delete period
/usr/bin/redis-cli -h $REDIS_HOST SREM epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:periods "2012-09-10/2012-09-12/P1D"
(integer) 1
 
# Delete default date
/usr/bin/redis-cli -h $REDIS_HOST DEL epsg4326:layer:SSMI_Cloud_Liquid_Water_Over_Oceans_Ascending:default
(integer) 1
```