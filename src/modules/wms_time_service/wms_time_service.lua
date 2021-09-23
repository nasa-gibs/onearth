local onearth_wms_time_service = {}

local lfs = require "lfs"
local lyaml = require "lyaml"
local request = require "http.request"
local JSON = require "JSON"
local xml = require "pl.xml"

-- Utility functions

local function split(sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results + 1] = value
    end
    return results
end

local function get_query_param(param, query_string)
    if not query_string then
        return nil
    end
    local query_parts = split("&", query_string)
    local date_string = nil;
    for _, part in pairs(query_parts) do
        local query_pair = split("=", part)
        if string.lower(query_pair[1]) == param then
            return query_pair[2]
        end
    end
    return date_string
end

local function sendResponse(code, msg_string)
    return "<html><body>" .. msg_string .. "</body></html>",
    {
        ["Content-Type"] = "text/html"
    },
    code
end

local function sendResponseRedirect(url)
    return url, {
        ["Location"] = url
    },
    308
end

local function getTimeServiceOutput(endpointConfig, layer, time)
    local dateServiceUri = endpointConfig["time_service_uri"]
    local dateServiceKeys = endpointConfig["time_service_keys"]
    if dateServiceKeys then
        local formattedKeys = {}
        for idx, value in ipairs(dateServiceKeys) do
            formattedKeys[#formattedKeys + 1] = "key" .. tostring(idx) .. "=" .. value
        end
        local keyString = table.concat(formattedKeys, "&")
        if string.sub(dateServiceUri, -1) ~= "?" then
            dateServiceUri = dateServiceUri .. "?"
        end
        dateServiceUri = dateServiceUri .. keyString
    end
    dateServiceUri = dateServiceUri .. "&layer=" .. layer .. "&datetime=" .. time
    local headers, stream = assert(request.new_from_uri(dateServiceUri):go(5))
    local body = assert(stream:get_body_as_string())
    if headers:get ":status" ~= "200" then
        print("Error contacting date service: " .. body)
        return {}
    end

    local dateList = JSON:decode(body)
    return dateList or {}
end

-- Pass-through all requests to mapserver, except "getmap" requests should append
-- each layer's <layer_name>_PREFIX and <layer_name>_SHAPEFILE variables to URL
function onearth_wms_time_service.handler(endpointConfig)
    return function(query_string, headers_in, notes)
        local req = get_query_param("request", query_string)
        if not req then
            return sendResponse(200, 'No REQUEST parameter specified')
        end

        local redirect_url = notes["URI"]:gsub("wms", "mapserver", 1) .. "?" .. query_string
        req = req:lower()
        if req == "getmap" then
            local layers_string = get_query_param("layers", query_string)
            local time_string = get_query_param("time", query_string)
            local layers_url = ""

            if layers_string and time_string then
                local layers = split(",", layers_string)

                for _, layer in pairs(layers) do
                    local time_service_output = getTimeServiceOutput(endpointConfig, layer, time_string)

                    if time_service_output["date"] and time_service_output["prefix"] then
                        local year = string.sub(time_service_output["date"], 0, 4)

                        layers_url = layers_url .. "&" .. layer .. "_PREFIX=" .. time_service_output["prefix"] .. "%2F" .. year .. "%2F"
                    end
					
                    if time_service_output["filename"] then
                        layers_url = layers_url .. "&" .. layer .. "_SHAPEFILE=" .. time_service_output["filename"]
                    end
                end
            end

            redirect_url = redirect_url .. layers_url
	    end

        return sendResponseRedirect(redirect_url)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_wms_time_service
else
    print("pcall - Call main method here")
end
