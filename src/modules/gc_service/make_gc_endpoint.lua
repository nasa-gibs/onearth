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
local onearth_gc_gts = require "onearth_gc_gts"
local config = {
    layer_config_source="${config_loc}",
    tms_defs_file="${tms_loc}",
    tms_limits_defs_file="${tms_limits_loc}",
    time_service_uri="${time_service_uri}",
    epsg_code="${epsg_code}",
    gc_header_file=${gc_header_file},
    gts_header_file=${gts_header_file},
    twms_gc_header_file=${twms_gc_header_file},
    base_uri_gc=${base_uri_gc},
    base_uri_gts=${base_uri_gts},
    base_uri_meta=${base_uri_meta},
    target_epsg_code=${target_epsg_code},
    time_service_keys=${time_service_keys}
}
handler = onearth_gc_gts.handler(config)
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

    local tmsDefsFilename = assert(endpointConfig["tms_defs_file"], "No 'tms_defs_file' specified in endpoint config.")
    local layerConfigSource = assert(endpointConfig["layer_config_source"], "No 'layer_config_source' specified in endpoint config.")
    local dateServiceUri = endpointConfig["time_service_uri"]

    local tmsLimitsDefsFilename = endpointConfig["tms_limits_defs_file"]
    if not tmsLimitsDefsFilename then
        print("No 'tms_limits_defs_file' specified in endpoint config.")
    end
    local dateServiceKeyString = "{}"
    if endpointConfig["time_service_keys"] then
        dateServiceKeyString = "{" .. join(map(addQuotes, endpointConfig["time_service_keys"]), ",") .. "}"
    end

    local epsgCode = assert(endpointConfig["epsg_code"], "No 'epsg_code' specified in endpoint config.")

    local configPrefix = endpointConfig["gc_service"]["config_prefix"]
    if not configPrefix then
        print("No gc_service/config_filename specified. Using 'onearth_gc_service'")
        configPrefix = "onearth_gc_service"
    end        

    local apacheConfigLocation = endpointConfig["gc_service"]["apache_config_location"]
    if not apacheConfigLocation then
        apacheConfigLocation = "/etc/httpd/conf.d/" .. configPrefix .. ".conf"
        print("No Apache config location specified. Using '/etc/httpd/conf.d/'")
    end

    local internalEndpoint = endpointConfig["gc_service"]["internal_endpoint"]
    if not internalEndpoint then
        print("No gc_service/internal_endpoint specified. Using '/var/www/html")
        internalEndpoint = "/var/www/html"
    end
    internalEndpoint = stripTrailingSlash(internalEndpoint)

    local externalEndpoint = endpointConfig["gc_service"]["external_endpoint"]
    if not externalEndpoint then
        print("No gc_service/external_endpoint specified. Using /gc")
        externalEndpoint = "/gc"
    end
    externalEndpoint = stripTrailingSlash(externalEndpoint)

    local regexp = "gc_service"
    local luaConfigLocation = internalEndpoint .. "/" .. configPrefix .. ".lua"

    -- Generate Apache config string
    local apacheConfig = apacheConfigTemplate:gsub("${internal_endpoint}", internalEndpoint)
        :gsub("${external_endpoint}", externalEndpoint)
        :gsub("${regexp}", regexp)
        :gsub("${script_loc}", luaConfigLocation)

    -- Make and write Lua config
    local luaConfig = luaConfigTemplate:gsub("${config_loc}", layerConfigSource)
        :gsub("${tms_loc}", tmsDefsFilename)
        :gsub("${tms_limits_loc}", tmsLimitsDefsFilename or "nil")
        :gsub("${time_service_uri}", dateServiceUri)
        :gsub("${epsg_code}", epsgCode)
        :gsub("${gc_header_file}", addQuotes(endpointConfig["gc_service"]["gc_header_file"]) or "nil")
        :gsub("${gts_header_file}", addQuotes(endpointConfig["gc_service"]["gts_header_file"]) or "nil")
        :gsub("${twms_gc_header_file}", addQuotes(endpointConfig["gc_service"]["twms_gc_header_file"]) or "nil")
        :gsub("${base_uri_gc}", addQuotes(endpointConfig["base_uri_gc"]) or "nil")
        :gsub("${base_uri_gts}", addQuotes(endpointConfig["base_uri_gts"]) or "nil")
        :gsub("${base_uri_meta}", endpointConfig["base_uri_meta"] and addQuotes(endpointConfig["base_uri_meta"]) or "nil")
        :gsub("${target_epsg_code}", endpointConfig["reproject"] and (endpointConfig["reproject"]["target_epsg_code"] and addQuotes(endpointConfig["reproject"]["target_epsg_code"]) or "nil") or "nil")
        :gsub("${time_service_keys}", dateServiceKeyString)
    lfs.mkdir(internalEndpoint)
    local luaConfigFile = assert(io.open(luaConfigLocation, "w+", "Can't open Lua config file " 
        .. luaConfigLocation .. " for writing."))
    luaConfigFile:write(luaConfig)
    luaConfigFile:close()

    print("GetCapabilities" .. " service config has been saved to " .. luaConfigLocation)

    local apacheConfigFile = assert(io.open(apacheConfigLocation, "w+"), "Can't open Apache config file "
        .. apacheConfigLocation .. " for writing.")
    apacheConfigFile:write(apacheConfigHeaderTemplate)
    apacheConfigFile:write(apacheConfig)
    apacheConfigFile:write("\n")
    apacheConfigFile:close()

    print("Apache config has been saved to " .. apacheConfigLocation)
    print("Configuration complete!")
end

local parser = argparse("make_gc_endpoint.lua", "")
parser:argument("endpoint_config", "Endpoint config YAML.")
local args = parser:parse()

create_config(args["endpoint_config"])