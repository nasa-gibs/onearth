local onearth = {}

local posix = require "posix"
local posix_time = require "posix.time"

posix.setenv("TZ", "UTC") -- Have to set this as gmtime only uses local timezone

local dateTemplate = "%d%d%d%d%-%d%d?%-%d%d?$"
local dateTimeTemplate = "%d%d%d%d%-%d%d?%-%d%d?T%d%d?:%d%d?:%d%d?$"
local dateFormat = "%Y-%m-%d"
local dateTimeFormat = "%Y-%m-%dT&H:&M:&S"

-- Utility functions
local function split (sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results+1] = value
    end
    return results
end

local function getQueryParam (param, queryString)
    local queryParts = split("&", queryString)
    local dateString = nil;
    for _, part in pairs(queryParts) do
        local queryPair = split("=", part)
        if string.lower(queryPair[1]) == param then
            return queryPair[2]
        end
    end
    return dateString
end

local function sendResponse (code, msgString)
   return msgString,
      {
        ["Content-Type"] = "application/json"
      },
      code
end

-- Date utility functions

-- Verify date string, returning epoch, subdaily (bool) if valid, false if not
local function parseDate (dateString)
    if string.match(dateString, dateTemplate) then
        local date = posix_time.strptime(dateString, dateFormat)
        return posix_time.mktime(date), false
    elseif string.match(dateString, dateTimeTemplate) then
        local date = posix_time.strptime(dateString, dateTimeFormat)
        return posix_time.mktime(date), true
    else
        return false
    end
end

local function addInterval (dateEpoch, intervalLength, intervalSize)
    local date = posix_time.gmtime(dateEpoch)
    if intervalSize == "Y" then
        date.tm_year = date.tm_year + intervalLength
    elseif intervalSize == "M" then
        date.tm_mon = date.tm_mon + intervalLength
    end
    return posix_time.mktime(date)
end

local function findSnapDateForFixedTimeinterval (startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
    local intervalInSec = intervalSize == "S" and intervalLength
    or intervalSize == "MM" and intervalLength * 60
    or intervalSize == "H" and intervalLength * 60 * 60
    or intervalSize == "D" and intervalLength * 60 * 60 * 24
    or nil
    local closestInterval = math.floor((reqEpoch - startEpoch) / intervalInSec) * intervalInSec + startEpoch
    return closestInterval < endEpoch and closestInterval or endEpoch
end


local function findSnapDateForNonFixedTimeInterval (startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
    local previousIntervalEpoch = startEpoch
    while true do
        local checkEpoch = addInterval(previousIntervalEpoch, intervalLength, intervalSize)
        if checkEpoch > reqEpoch then -- Found snap date
            return previousIntervalEpoch
        end
        if checkEpoch > endEpoch then -- Snap date isn't in this period
            break
        end
        previousIntervalEpoch = checkEpoch
    end
end

local function getSnapEpoch (startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
    if intervalSize == "H" or intervalSize == "MM" or intervalSize == "S" or intervalSize == "D" then
        return findSnapDateForFixedTimeinterval(startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
    else
        return findSnapDateForNonFixedTimeInterval(startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
    end
end

-- Handlers to get layer period and default date information
local function redisGetAllLayers (client)
    local layers = {}
    local cursor = 0
    local results = {}
    repeat     
        cursor, results = unpack(client:scan(cursor, {match="layer*"}))
        for key, value in pairs(results) do
            local layerName = split(":", value)[2]
            layers[layerName] = not layers[layerName] and {} or layers[layerName]
            layers[layerName].default = client:get("layer:" .. layerName .. ":default")
            layers[layerName].periods = client:lrange("layer:" .. layerName .. ":periods", 0, -1)
        end
    until cursor == "0"
    return layers
end

local function redisHandler (options)
    local redis = require 'redis'
    local client = redis.connect(options.ip, options.port or 6379)
    return function (layerName) 
        if layerName then
            local default = client:get("layer:" .. layerName .. ":default")
            local periods = client:lrange("layer:" .. layerName .. ":periods", 0, -1)
            if default and periods then
                return {[layerName] = {
                        default = default,
                        periods = periods
                    }
                }
            end
            return {err_msg = "Layer not found!"}
        end
        -- If no layer name specified, dump all data
        return redisGetAllLayers(client)
    end
end

-- Handlers to format output filenames

local function strftimeFormatter (options)
    return function (layerName, dateEpoch, subdaily)
        return layerName .. posix_time.strftime(subdaily and options.dateTimeFormat or options.dateFormat, posix_time.gmtime(dateEpoch))
    end    
end

-- Main date snapping handler -- this returns a function that's intended to be called by mod_ahtse_lua
function onearth.dateSnapper (layerHandlerOptions, filenameOptions)
    local JSON = require("JSON")
    local layerHandler = layerHandlerOptions.type == "redis" and redisHandler(layerHandlerOptions) or nil
    local filenameHandler = filenameOptions.type == "strftime" and strftimeFormatter(filenameOptions) or nil
    
    return function (queryString, headers_in, notes)
        
        local layerName = queryString and getQueryParam("layer", queryString) or nil
        
        -- -- A blank query returns the entire list of layers and periods
        if not queryString or not layerName then
            return sendResponse(200, JSON:encode(layerHandler()))
        end
        
        -- A layer but no date returns the default date and available periods for that layer
        local requestDateString = getQueryParam("datetime", queryString)
        local layerDatetimeInfo = layerHandler(layerName)
        if not requestDateString then
            return sendResponse(200, JSON:encode(layerDatetimeInfo))
        end


        -- If it's a default request, return the default date and associated period
        if string.lower(requestDateString) == "default" then
            local outMsg = {
                date = layerDatetimeInfo[layerName].default,
                filename = filenameHandler(layerName, parseDate(layerDatetimeInfo[layerName].default))
            }
            return sendResponse(200, JSON:encode(outMsg))
        end

        -- Send error message if date is in a bad format
        local reqEpoch, subdaily = parseDate(requestDateString)
        if not reqEpoch then
            local outMsg = {
                err_msg = "Invalid Date"
            }
            return sendResponse(200, JSON:encode(outMsg))
        end      

        -- Find snap date if date request is valid
        for _, period in ipairs(layerDatetimeInfo[layerName].periods) do
            local parsedPeriod = split("/", period)
            local startDate = subdaily and posix_time.strptime(parsedPeriod[1], dateTimeFormat)
                or posix_time.strptime(parsedPeriod[1], dateFormat)
            local startEpoch = posix_time.mktime(startDate)
            local endDate = subdaily and posix_time.strptime(parsedPeriod[2], dateTimeFormat)
                or posix_time.strptime(parsedPeriod[2], dateFormat)
            local endEpoch = posix_time.mktime(endDate)
            if reqEpoch == startEpoch then
                snapEpoch = reqEpoch
                break
            end
            if reqEpoch > startEpoch then
                local intervalLength = tonumber(string.match(parsedPeriod[3], "%d+"))
                local intervalSize = string.match(parsedPeriod[3], "%a+$")
                snapEpoch = getSnapEpoch(startEpoch, reqEpoch, endEpoch, intervalLength, intervalSize)
                break
            end
        end

        -- Return snap date and error if none is found
        if snapEpoch then
            local snapDateString = posix_time.strftime(subdaily and dateTimeFormat or dateFormat, posix_time.gmtime(snapEpoch))
            local outMsg = {
                date = snapDateString,
                filename = filenameHandler(layerName, snapEpoch, subdaily)
            }
            return sendResponse(200, JSON:encode(outMsg))
        else
            local outMsg = {
                err_msg = "Date out of range"
            }
            return sendResponse(200, JSON:encode(outMsg))
        end
    end
end
return onearth