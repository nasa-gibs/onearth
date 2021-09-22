local onearth_gc_service = {}

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

local function get_query_param (param, query_string)
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
    return msg_string,
    {
        ["Content-Type"] = "text/xml"
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

function onearth_gc_service.handler(endpointConfig)
    return function(query_string, headers_in, notes)
        local req = get_query_param("request", query_string)
        if not req then
            return sendResponse(200, 'No REQUEST parameter specified')
        end

        req = req:lower()
        local redirect_url = notes["URI"]:gsub("wms", "mapserver", 1) .. "?" .. query_string
        local response
        if req == "getmap" then
            response = "BLAH1 "
            local layers_string = get_query_param("layers", query_string)

            local layers = split(",", layers_string)

            local layers_url = ""
            for _, layer in pairs(layers) do
                temp_layer = "MODIS_Aqua_Brightness_Temp_Band31_Day"
                temp_date = "2011-09-01"
                local time_service_output = getTimeServiceOutput(endpointConfig, temp_layer, temp_date)

                local json_as_string = JSON:encode(time_service_output)

                response = response .. "  json_as_string: " .. json_as_string

                --local wms_time_service_out = JSON:decode(time_service_output)

                if time_service_output["date"] then
                    local date = time_service_output["date"]
                    local shapefile = time_service_output["filename"]
                    local prefix = time_service_output["prefix"]
                    layers_url = layers_url .. "&" .. layer .. "_PREFIX=" .. prefix .. "%2F" .. string.sub(date, 0, 4) .. "%2F"

                    layers_url = layers_url .. "&" .. layer .. "_SHAPEFILE=" .. shapefile
                end
            end

--            response = response .. "   " .. layers_url .. "   HI HI HI THERE Unrecognized REQUEST parameter: '" .. req .. "'. Request must be one of: WMTSGetCapabilities, TWMSGetCapabilities, GetTileService"
            redirect_url = redirect_url .. layers_url
	    end

        return sendResponseRedirect(redirect_url)

           -- response = makeGC(endpointConfig)
    --    elseif req == "twmsgetcapabilities" then
    --        response = makeTWMSGC(endpointConfig)
    --    elseif req == "gettileservice" then
    --        response = makeGTS(endpointConfig)
--        end
--        return sendResponse(200, response)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_gc_service
else
    print("pcall - Call main method here")
end
