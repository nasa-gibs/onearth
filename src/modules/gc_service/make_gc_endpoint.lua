local lyaml = require "lyaml"
local lfs = require "lfs"
local argparse = require "argparse"

local apacheConfigHeaderTemplate = [[
<IfModule !ahtse_lua>
    LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>
]]

local apacheConfigTemplate = [[
<Directory ${dir}>
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
    gc_header_loc="${gc_header_loc}",
    date_service_uri="${date_service_uri}",
    epsg_code="${epsg_code}",
    gts_service=${gettileservicemode},
    gc_header_file=${gc_header_file},
    gts_header_file=${gts_header_file},
    base_uri_gc=${base_uri_gc},
    base_uri_gts=${base_uri_gts},
    target_epsg_code=${target_epsg_code},
    date_service_keys=${date_service_keys}
}
handler = onearth_gc_gts.handler(config)
]]

-- Utility functions
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

function map(func, array)
  local new_array = {}
  for i,v in ipairs(array) do
    new_array[i] = func(v)
  end
  return new_array
end

-- Create configuration

local function create_config(endpointConfigFilename, makeOptions)
    local endpointConfigFile = assert(io.open(endpointConfigFilename, "r"), "Can't open endpoint config file: " .. endpointConfigFilename)
    local endpointConfig = lyaml.load(endpointConfigFile:read("*all"))
    endpointConfigFile:close()

    local tmsDefsFilename = assert(endpointConfig["tms_defs_file"], "No 'tms_defs_file' specified in endpoint config.")
    local layerConfigSource = assert(endpointConfig["layer_config_source"], "No 'layer_config_source' specified in endpoint config.")
    local dateServiceUri = endpointConfig["date_service_uri"]

    local dateServiceKeyString = "{}"
    if endpointConfig["date_service_keys"] then
        dateServiceKeyString = "{" .. join(map(addQuotes, endpointConfig["date_service_keys"]), ",") .. "}"
    end

    local epsgCode = assert(endpointConfig["epsg_code"], "No 'epsg_code' specified in endpoint config.")

    local apacheConfigLocation = endpointConfig["apache_config_location"]
    if not apacheConfigLocation then
        apacheConfigLocation = "/etc/httpd/conf.d/gc_gts_service.conf"
        print("No Apache config location specified. Using '/etc/httpd/conf.d/" .. apacheConfigLocation .. "'")
    end

    local luaConfigBaseLocation = endpointConfig["endpoint_config_base_location"]
    if not luaConfigBaseLocation then
        print("No Lua config base location specified. Using '/var/www/html")
        luaConfigBaseLocation = "/var/www/html"
    end

    local endpoints = {}
    if makeOptions["gc"] then
        local gcHeaderFilename = assert(endpointConfig["gc_header_file"], "GetCapabilities creation selected but no gc_header_file in the endpoint config")
        local gc_endpoint = endpointConfig["gc_endpoint"]
        if not gc_endpoint then
            print("No GetCapabilities endpoint specified. Using /gc")
            gc_endpoint = "/gc"
        end
        endpoints[#endpoints + 1] = {path=gc_endpoint, isGts=false, headerFile=gcHeaderFilename}
    end

    if makeOptions["gts"] then
        local gtsHeaderFilename = assert(endpointConfig["gts_header_file"], "GetTileService creation selected but no gts_header_file in the endpoint config")
        local gts_endpoint = endpointConfig["gts_endpoint"]
        if not gts_endpoint then
            print("No GetTileService endpoint specified. Using /gts")
            gts_endpoint = "/gts"
        end
        endpoints[#endpoints + 1] = {path=gts_endpoint, isGts=true, headerFile=gtsHeaderFilename}
    end

    local apacheConfigs = {}
    for _, endpoint in ipairs(endpoints) do
        local regexp = endpoint["isGts"] and "GetTileService.xml" or "GetCapabilities.xml"
        local luaConfigLocation = luaConfigBaseLocation .. endpoint["path"] .. "/" .. (endpoint["isGts"] and "onearth_gts_service" or "onearth_gc_service") .. ".lua"

        -- Generate Apache config string
        apacheConfigs[#apacheConfigs + 1] = apacheConfigTemplate:gsub("${dir}", luaConfigBaseLocation .. endpoint["path"])
            :gsub("${regexp}", regexp)
            :gsub("${script_loc}", luaConfigLocation)

        -- Make and write Lua config
        local luaConfig = luaConfigTemplate:gsub("${config_loc}", layerConfigSource)
            :gsub("${tms_loc}", tmsDefsFilename)
            :gsub("${gc_header_loc}", endpoint["headerFile"])
            :gsub("${date_service_uri}", dateServiceUri)
            :gsub("${epsg_code}", epsgCode)
            :gsub("${gettileservicemode}", tostring(endpoint["isGts"]))
            :gsub("${gc_header_file}", (not endpoint["isGts"] and addQuotes(endpointConfig["gc_header_file"]) or "nil"))
            :gsub("${gts_header_file}", (endpoint["isGts"] and addQuotes(endpointConfig["gts_header_file"]) or "nil"))
            :gsub("${base_uri_gc}", (not endpoint["isGts"] and addQuotes(endpointConfig["base_uri_gc"]) or "nil"))
            :gsub("${base_uri_gts}", (endpoint["isGts"] and addQuotes(endpointConfig["base_uri_gts"]) or "nil"))
            :gsub("${target_epsg_code}", endpointConfig["target_epsg_code"] and addQuotes(endpointConfig["target_epsg_code"]) or "nil")
            :gsub("${date_service_keys}", dateServiceKeyString)
        lfs.mkdir(luaConfigBaseLocation .. endpoint["path"])
        local luaConfigFile = assert(io.open(luaConfigLocation, "w+", "Can't open Lua config file " 
            .. luaConfigLocation .. " for writing."))
        luaConfigFile:write(luaConfig)
        luaConfigFile:close()

        print((endpoint["isGts"] and "GetTileService" or "GetCapabilities") .. " service config has been saved to " .. luaConfigLocation)
    end

    local apacheConfigFile = assert(io.open(apacheConfigLocation, "w+"), "Can't open Apache config file "
        .. apacheConfigLocation .. " for writing.")
    apacheConfigFile:write(apacheConfigHeaderTemplate)
    for _, line in ipairs(apacheConfigs) do
        apacheConfigFile:write(line)
        apacheConfigFile:write("\n")
    end
    apacheConfigFile:close()

    print("Apache config has been saved to " .. apacheConfigLocation)
    print("Configuration complete!")
end

local parser = argparse("make_gc_endpoint.lua", "")
parser:argument("endpoint_config", "Endpoint config YAML.")
parser:flag("-n --no_gc", "Don't generate a GetCapabilities service")
parser:flag("-g --make_gts", "Generate a GetTileService service")
local args = parser:parse()

local makeOptions = {
    gc = not args["no_gc"],
    gts = args ["make_gts"]
}

create_config(args["endpoint_config"], makeOptions)