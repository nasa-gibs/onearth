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

function findLast(s, str)
    local i=s:match(".*"..str.."()")
    if i==nil then return nil else return i-1 end
end

local function sendErrorResponse(code, locator, msg_string)
	local return_msg = '<?xml version="1.0" encoding="UTF-8"?>\n'
	return_msg = return_msg .. '<ExceptionReport xmlns="http://www.opengis.net/ows/1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd" version="1.1.0" xml:lang="en">\n'
        return_msg = return_msg .. '<Exception exceptionCode="' .. code .. '" locator="' .. locator .. '">\n'
	return_msg = return_msg .. '<ExceptionText>' .. msg_string .. '</ExceptionText></Exception>\n'
	return_msg = return_msg .. '</ExceptionReport>\n'

    return return_msg,
    {
        ["Content-Type"] = "text/xml"
    },
    200
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
    print("Calling time_service uri: " .. dateServiceUri)
    local headers, stream = assert(request.new_from_uri(dateServiceUri):go(5))
    local body = assert(stream:get_body_as_string())
    print("time_service output: " .. body)
    if headers:get ":status" ~= "200" then
        print("Error contacting date service: " .. body)
        return {}
    end

    local dateList = JSON:decode(body)
    return dateList or {}
end

function validate_time(time)
    local n = string.len(time)
    if n == 10 or n == 20 then
        -- Example 1: 2021-09-23
        -- Example 2: 2021-09-23T20:05:08Z
        local y = tonumber(string.sub(time, 0, 4))
        if string.sub(time, 5, 5) ~= '-' then
            return false
        end
        local m = tonumber(string.sub(time, 6, 7))
        if string.sub(time, 8, 8) ~= '-' then
            return false
        end
        local d = tonumber(string.sub(time, 9, 10))
        if y == nil or y < 1900 or m == nil or m < 0 or m > 12 or d == nil or d < 0 or d > 31 then
            return false
        end
        if n == 10 then
            return true
        end
    end
    if n == 20 then
        if string.sub(time, 11, 11) ~= 'T' then
            return false
        end
        local h = tonumber(string.sub(time, 12, 13))
        if string.sub(time, 14, 14) ~= ':' then
            return false
        end
        local m = tonumber(string.sub(time, 15, 16))
        if string.sub(time, 17, 17) ~= ':' then
            return false
        end
        local s = tonumber(string.sub(time, 18, 19))
        if string.sub(time, 20, 20) ~= 'Z' then
            return false
        end
        if h == nil or h < 0 or h > 23 or m == nil or m < 0 or m > 59 or s == nil or s < 0 or s > 59 then
            return false
        end
        return true
    end
    return false
end

-- Pass-through all requests to mapserver, except "getmap" requests should append
-- each layer's <layer_name>_PREFIX and <layer_name>_SHAPEFILE variables to URL
function onearth_wms_time_service.handler(endpointConfig)
    return function(query_string, headers_in, notes)
        local req = get_query_param("request", query_string)
        local time_string = get_query_param("time", query_string)

        if not req then
            return sendResponse(200, 'No REQUEST parameter specified')
        end

        if time_string then
            if time_string ~= "default" and validate_time(time_string) == false then
                return sendErrorResponse("InvalidParameterValue", "TIME", "Invalid time format, must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ")
            end
        else
            time_string = "default"
        end

        local redirect_url = notes["URI"]:gsub("wms", "mapserver", 1) .. "?" .. query_string
        req = req:lower()
        if req == "getmap" then
            local layers_string = get_query_param("layers", query_string)
            local layers_url = ""

            if layers_string then
                local layers = split(",", layers_string)

                for _, layer in pairs(layers) do
                    local time_service_output = getTimeServiceOutput(endpointConfig, layer, time_string)

                    if time_service_output["date"] and time_service_output["prefix"] then
                        local year = string.sub(time_service_output["date"], 0, 4)

                        layers_url = layers_url .. "&" .. layer .. "_PREFIX=" .. time_service_output["prefix"] .. "%2F" .. year .. "%2F"

                        if string.find(layer, "OrbitTracks") then
                            -- Add Lines and Points layer PREFIXES also
                            layers_url = layers_url .. "&" .. layer .. "_Lines_PREFIX=" .. time_service_output["prefix"] .. '_Lines' .. "%2F" .. year .. "%2F"
                            layers_url = layers_url .. "&" .. layer .. "_Points_PREFIX=" .. time_service_output["prefix"] .. '_Points' .. "%2F" .. year .. "%2F"
                        end
                    end

                    if time_service_output["filename"] then
                        layers_url = layers_url .. "&" .. layer .. "_SHAPEFILE=" .. time_service_output["filename"]

                        if string.find(layer, "OrbitTracks") then
                            -- Add Lines and Points layer SHAPEFILES also
                            local index = findLast(time_service_output["filename"], "-")

                            if index then
                                local layer_root = string.sub(time_service_output["filename"], 0, index-1)
                                local date_str = string.sub(time_service_output["filename"], index)

                                layers_url = layers_url .. "&" .. layer .. "_Lines_SHAPEFILE=" .. layer_root .. '_Lines' .. date_str
                                layers_url = layers_url .. "&" .. layer .. "_Points_SHAPEFILE=" .. layer_root .. '_Points' .. date_str
                            end
                        end
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
