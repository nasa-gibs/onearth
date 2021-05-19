redis.replicate_commands()
-- REDIS SYNTAX == EVAL {script} layer_prefix:layer_name , date_time
-- Routine called by Redis. If best_layer exists, script will update :best key
-- GITC mod: Add new date and only update if there was a change
if ARGV[1] ~= nil then
  local result = 0
  if ARGV[1]:match("(%d+)-(%d+)-(%d+)") then
    result = redis.call("ZADD", KEYS[1] .. ":dates", 0, ARGV[1])
  end
  if result == 0 then
    --return
  end
end
-- End GITC mod

if redis.call("EXISTS", KEYS[1] .. ":best_layer") == 1 and ARGV[1] ~= nil then
  local best_layer = redis.call("GET", KEYS[1] .. ":best_layer")
  local index = KEYS[1]:match("^.*():")
  local layerPrefix = KEYS[1]:sub(1,index)
  local best_key = layerPrefix .. best_layer
  redis.call("ZADD", best_key .. "_BEST:dates", 0, ARGV[1])
  local layers = redis.call("ZREVRANGE", best_key .. ":best_config", 0, -1)
  local found = false
  for i, layer in ipairs(layers) do
    if redis.call("ZRANK", layerPrefix .. layer, ARGV[1]) ~= nil then
      redis.call("HMSET", best_key .. "_BEST:best", ARGV[1], layer) 
      found = true
      break
    end
  end
  if not found then
    redis.call("HDEL", best_key .. "_BEST:best", ARGV[1])
    redis.call("ZREM", best_key .. "_BEST:dates", ARGV[1])
  end
end