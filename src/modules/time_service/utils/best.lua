redis.replicate_commands()
-- REDIS SYNTAX == EVAL {script} layer_prefix:layer_name , date_time
-- Routine called by Redis. If best_layer exists, script will update :best key

local index = KEYS[1]:match("^.*():")
local layerPrefix = KEYS[1]:sub(1,index) -- remove provided layers name
local sourceLayerName = KEYS[1]:sub(index + 1,-1)
local layerNames = { sourceLayerName }
local cursor = "0"

-- Also set up :best key for the layers listed in copy_periods, if applicable.
-- Relevant for ZenJPEG layers.
repeat
  local scan = redis.call("SSCAN", KEYS[1] .. ":copy_periods", cursor)
  for _, value in ipairs(scan[2]) do
    table.insert(layerNames, value)
  end
  cursor = scan[1]
until cursor == "0"

for _, name in ipairs(layerNames) do
  if redis.call("EXISTS", layerPrefix .. name .. ":best_layer") == 1 and ARGV[1] ~= nil then
    local best_layer = redis.call("GET", layerPrefix .. name .. ":best_layer")
    local best_key = layerPrefix .. best_layer -- concat best_layer to layer prefix

    local layers = redis.call("ZREVRANGE", best_key .. ":best_config", 0, -1) -- get layers in reverse, higher score have priority
    local found = false
    for i, layer in ipairs(layers) do
      if name == sourceLayerName then
        if redis.call("ZSCORE", layerPrefix .. layer .. ":dates", ARGV[1]) then -- loops through best_config layers, checks if date exist
          redis.call("HMSET", best_key .. ":best", ARGV[1] .. "Z", layer) -- update :best hset with date and best layer
          redis.call("ZADD", best_key .. ":dates", 0, ARGV[1]) -- add date to best_layer:dates zset
          found = true
          break
        end
      else -- Layers listed in copy_periods should use the dates of the layer they're copying from
        if redis.call("ZSCORE", KEYS[1] .. ":dates", ARGV[1]) then -- loops through best_config layers, checks if date exist
          redis.call("HMSET", best_key .. ":best", ARGV[1] .. "Z", name) -- update :best hset with date and best layer
          redis.call("ZADD", best_key .. ":dates", 0, ARGV[1]) -- add date to best_layer:dates zset
          found = true
          break
        end
      end
    end
    if not found then -- if the date is not found within layers of best_config key or the key was deleted
      redis.call("HDEL", best_key .. ":best", ARGV[1] .. "Z") -- :best dates have a Z
      redis.call("ZREM", best_key .. ":dates", ARGV[1])
      redis.call("ECHO","*** Warn: Deleted or not configured, removing Best LAYER: " .. best_key .. " DATE: " .. ARGV[1])
    end
  end
end