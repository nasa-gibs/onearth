local onearth = {}

local posix = require "posix"
local posix_time = require "posix.time"

posix.setenv("TZ", "UTC") -- Have to set this as gmtime only uses local timezone

local socket = require "socket"

local date_template = "%d%d%d%d%-%d%d?%-%d%d?$"
local date_time_template = "%d%d%d%d%-%d%d?%-%d%d?T%d%d?:%d%d?:%d%d?$"
local date_format = "%Y-%m-%d"
local date_time_format = "%Y-%m-%d_t&H:&M:&S"

-- Utility functions
local function split (sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results + 1] = value
    end
    return results
end

local function get_query_param (param, query_string)
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

local function send_response (code, msg_string)
    return msg_string,
    {
        ["Content-Type"] = "application/json"
    },
    code
end

-- Date utility functions

-- Verify date string, returning epoch, subdaily (bool) if valid, false if not
local function parse_date (date_string)
    if string.match(date_string, date_template) then
        local date = posix_time.strptime(date_string, date_format)
        return posix_time.mktime(date), false
    elseif string.match(date_string, date_time_template) then
        local date = posix_time.strptime(date_string, date_time_format)
        return posix_time.mktime(date), true
    else
        return false
    end
end

local function add_interval (date_epoch, interval_length, interval_size)
    local date = posix_time.gmtime(date_epoch)
    if interval_size == "Y" then
        date.tm_year = date.tm_year + interval_length
    elseif interval_size == "M" then
        date.tm_mon = date.tm_mon + interval_length
    end
    return posix_time.mktime(date)
end

local function find_snap_date_for_fixed_time_interval (start_epoch, req_epoch, end_epoch, interval_length, interval_size)
    local interval_in_sec = interval_size == "S" and interval_length
    or interval_size == "MM" and interval_length * 60
    or interval_size == "H" and interval_length * 60 * 60
    or interval_size == "D" and interval_length * 60 * 60 * 24
    or nil
    local closest_interval = math.floor((req_epoch - start_epoch) / interval_in_sec) * interval_in_sec + start_epoch
    return closest_interval < end_epoch and closest_interval or end_epoch
end


local function find_snap_date_for_non_fixed_time_interval (start_epoch, req_epoch, end_epoch, interval_length, interval_size)
    local previous_interval_epoch = start_epoch
    while true do
        local check_epoch = add_interval(previous_interval_epoch, interval_length, interval_size)
        if check_epoch > req_epoch then -- Found snap date
            return previous_interval_epoch
        end
        if check_epoch > end_epoch then -- Snap date isn't in this period
            break
        end
        previous_interval_epoch = check_epoch
    end
end

local function get_snap_epoch (start_epoch, req_epoch, end_epoch, interval_length, interval_size)
    if interval_size == "H" or interval_size == "MM" or interval_size == "S" or interval_size == "D" then
        return find_snap_date_for_fixed_time_interval(start_epoch, req_epoch, end_epoch, interval_length, interval_size)
    else
        return find_snap_date_for_non_fixed_time_interval(start_epoch, req_epoch, end_epoch, interval_length, interval_size)
    end
end

-- Handlers to get layer period and default date information
local function redis_get_all_layers (client)
    local layers = {}
    local cursor = "0"
    local results
    repeat
        cursor, results = unpack(client:scan(cursor, {match = "layer:*"}))
        for _, value in pairs(results) do
            local layer_name = split(":", value)[2]
            layers[layer_name] = not layers[layer_name] and {} or layers[layer_name]
            layers[layer_name].default = client:get("layer:" .. layer_name .. ":default")
            layers[layer_name].periods = client:smembers("layer:" .. layer_name .. ":periods")
        end
    until cursor == "0"
    return layers
end

local function redis_handler (options)
    local redis = require 'redis'
    local client = redis.connect(options.host, options.port or 6379)
    return function (layer_name, uuid)
        local returnValue
        local start_db_request = socket.gettime() * 1000
        if layer_name then
            local default = client:get("layer:" .. layer_name .. ":default")
            local periods = client:smembers("layer:" .. layer_name .. ":periods")
            if default and periods then
                returnValue = {[layer_name] = {
                    default = default,
                    periods = periods
                }}
            else
                returnValue = {err_msg = "Layer not found!"}
            end
        else
            -- If no layer name specified, dump all data
            returnValue = redis_get_all_layers(client)
        end
        print(string.format("step=time_database_request duration=%d uuid=%s", socket.gettime() * 1000 - start_db_request, uuid))
        return returnValue
    end
end

-- Handlers to format output filenames

local function strftime_formatter (options)
    return function (layer_name, date_epoch, subdaily)
        return layer_name .. posix_time.strftime(subdaily and options.date_time_format
        or options.date_format, posix_time.gmtime(date_epoch))
    end
end

local function epoch_formatter (_)
    return function (layer_name, date_epoch, _)
        return layer_name .. date_epoch
    end
end

-- Main date snapping handler -- this returns a function that's intended to be called by mod_ahtse_lua
function onearth.date_snapper (layer_handler_options, filename_options)
    local JSON = require("JSON")
    local layer_handler = layer_handler_options.type == "redis" and redis_handler(layer_handler_options) or nil
    local filename_handler = filename_options.type == "strftime" and strftime_formatter(filename_options)
        or filename_options.type == "epoch" and epoch_formatter(filename_options)
        or nil
    return function (query_string, headers, _)
        local uuid = headers["UUID"] or "none"
        local start_timestamp = socket.gettime() * 1000
        local layer_name = query_string and get_query_param("layer", query_string) or nil

        -- A blank query returns the entire list of layers and periods
        if not query_string or not layer_name then
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(layer_handler(nil, uuid)))
        end

        -- A layer but no date returns the default date and available periods for that layer
        local request_date_string = get_query_param("datetime", query_string)
        local layer_datetime_info = layer_handler(layer_name, uuid)
        if not request_date_string then
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(layer_datetime_info))
        end

        -- If it's a default request, return the default date and associated period
        if string.lower(request_date_string) == "default" then
            local out_msg = {
                date = layer_datetime_info[layer_name].default,
                filename = filename_handler(layer_name, parse_date(layer_datetime_info[layer_name].default))}
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Send error message if date is in a bad format
        local req_epoch, subdaily = parse_date(request_date_string)
        if not req_epoch then
            local out_msg = {
                err_msg = "Invalid Date"
            }
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Find snap date if date request is valid
        local snap_epoch
        for _, period in ipairs(layer_datetime_info[layer_name].periods) do
            local parsed_period = split("/", period)
            local start_date = subdaily and posix_time.strptime(parsed_period[1], date_time_format)
            or posix_time.strptime(parsed_period[1], date_format)
            local start_epoch = posix_time.mktime(start_date)
            local end_date = subdaily and posix_time.strptime(parsed_period[2], date_time_format)
            or posix_time.strptime(parsed_period[2], date_format)
            local end_epoch = posix_time.mktime(end_date)
            if req_epoch == start_epoch then
                snap_epoch = req_epoch
                break
            end
            if req_epoch > start_epoch then
                local interval_length = tonumber(string.match(parsed_period[3], "%d+"))
                local interval_size = string.match(parsed_period[3], "%a+$")
                snap_epoch = get_snap_epoch(start_epoch, req_epoch, end_epoch, interval_length, interval_size)
                break
            end
        end

        -- Return snap date and error if none is found
        if snap_epoch then
            local snap_date_string = posix_time.strftime(subdaily and date_time_format
            or date_format, posix_time.gmtime(snap_epoch))
            local out_msg = {
                date = snap_date_string,
                filename = filename_handler(layer_name, snap_epoch, subdaily)}
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        else
            local out_msg = {
                err_msg = "Date out of range"
            }
            print(string.format("step=timesnap_request duration=%u uuid=%s", socket.gettime() * 1000 - start_timestamp, uuid))
            return send_response(200, JSON:encode(out_msg))
        end
    end
end
return onearth
