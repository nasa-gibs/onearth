local lyaml = require "lyaml"
local lfs = require "lfs"
local argparse = require "argparse"

local apacheConfigHeaderTemplate = [[
<IfModule !ahtse_lua>
    LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>
]]

local apacheConfigTemplate = [[
Alias ${external_endpoint} ${internal_endpoint}
<Directory ${internal_endpoint}>
        AHTSE_lua_RegExp ${regexp}
        AHTSE_lua_Script ${script_loc}
        AHTSE_lua_Redirect On
        AHTSE_lua_KeepAlive On
</Directory>
]]

local luaConfigTemplate = [[
local onearth_wms_time = require "onearth_wms_time"
local config = {
    layer_config_source="${config_loc}",
    time_service_uri="${time_service_uri}",
    time_service_keys=${time_service_keys}
}
handler = onearth_wms_time.handler(config)
]]

-- Utility functions
local function stripTrailingSlash(str)
    if string.sub(str, -1) == "/" then
        str = string.sub(str, 0, -2)
    end
    return str
end

local function split(sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results + 1] = value
    end
    return results
end

local function join(arr, sep)
    local outStr = ""
    for idx, value in ipairs(arr) do
        outStr = outStr .. tostring(value) .. (idx < #arr and sep or "")
    end
    return outStr
end

local function addQuotes(str)
    return '"' .. str .. '"'
end

local function map(func, array)
  local new_array = {}
  for i,v in ipairs(array) do
    new_array[i] = func(v)
  end
  return new_array
end

-- Create configuration

local function create_config(endpointConfigFilename)
    local endpointConfigFile = assert(io.open(endpointConfigFilename, "r"), "Can't open endpoint config file: " .. endpointConfigFilename)
    local endpointConfig = lyaml.load(endpointConfigFile:read("*all"))
    endpointConfigFile:close()

    local layerConfigSource = assert(endpointConfig["layer_config_source"], "No 'layer_config_source' specified in endpoint config.")
    local dateServiceUri = endpointConfig["time_service_uri"]

    local dateServiceKeyString = "{}"
    if endpointConfig["time_service_keys"] then
        dateServiceKeyString = "{" .. join(map(addQuotes, endpointConfig["time_service_keys"]), ",") .. "}"
    end

    local configPrefix = endpointConfig["mapserver"]["config_prefix"]
    if not configPrefix then
        print("No wms_time_service/config_filename specified. Using 'onearth_wms_time_service'")
        configPrefix = "onearth_wms_time_service"
    end        

    local apacheConfigLocation = endpointConfig["mapserver"]["apache_config_location"]
    if not apacheConfigLocation then
        apacheConfigLocation = "/etc/httpd/conf.d/" .. configPrefix .. ".conf"
        print("No Apache config location specified. Using '/etc/httpd/conf.d/'")
    end

    local internalEndpoint = endpointConfig["mapserver"]["internal_endpoint"]
    if not internalEndpoint then
        print("No mapserver/internal_endpoint specified. Using '/var/www/html")
        internalEndpoint = "/var/www/html"
    end
    internalEndpoint = stripTrailingSlash(internalEndpoint)

    local externalEndpoint = endpointConfig["mapserver"]["external_endpoint"]
    if not externalEndpoint then
        print("No mapserver/external_endpoint specified. Using /wms")
        externalEndpoint = "/wms"
    end
    externalEndpoint = stripTrailingSlash(externalEndpoint)

    local regexp = "wms"
    local luaConfigLocation = internalEndpoint .. "/" .. configPrefix .. ".lua"

    -- Generate Apache config string
    local apacheConfig = apacheConfigTemplate:gsub("${internal_endpoint}", internalEndpoint)
        :gsub("${external_endpoint}", externalEndpoint)
        :gsub("${regexp}", regexp)
        :gsub("${script_loc}", luaConfigLocation)

    -- Make and write Lua config
    local luaConfig = luaConfigTemplate:gsub("${config_loc}", layerConfigSource)
        :gsub("${time_service_uri}", dateServiceUri)
        :gsub("${time_service_keys}", dateServiceKeyString)
    lfs.mkdir(internalEndpoint)
    local luaConfigFile = assert(io.open(luaConfigLocation, "w+", "Can't open Lua config file " 
        .. luaConfigLocation .. " for writing."))
    luaConfigFile:write(luaConfig)
    luaConfigFile:close()

    print("WMS Time service config has been saved to " .. luaConfigLocation)

    local apacheConfigFile = assert(io.open(apacheConfigLocation, "w+"), "Can't open Apache config file "
        .. apacheConfigLocation .. " for writing.")
    apacheConfigFile:write(apacheConfigHeaderTemplate)
    apacheConfigFile:write(apacheConfig)
    apacheConfigFile:write("\n")
    apacheConfigFile:close()

    print("Apache config has been saved to " .. apacheConfigLocation)
    print("Configuration complete!")
end

local parser = argparse("make_wms_time_endpoint.lua", "")
parser:argument("endpoint_config", "Endpoint config YAML.")
local args = parser:parse()

create_config(args["endpoint_config"])