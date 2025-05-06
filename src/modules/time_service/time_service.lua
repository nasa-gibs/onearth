local onearthTimeService = {}

local md5 = require "md5"
local date_util = require "date"
local socket = require "socket"

local unpack = _G.unpack or table.unpack

local date_template = "%d%d%d%d%-%d%d?%-%d%d?$"
local datetime_template = "%d%d%d%d%-%d%d?%-%d%d?T%d%d?:%d%d?:%d%d?Z$"
local datetime_filename_format = "%Y%j%H%M%S"
local datetime_format = "%Y-%m-%dT%H:%M:%SZ"
local date_format = "%Y-%m-%d"


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

local function get_query_keys(query_string)
    local results = {}
    local query_parts = split("&", query_string)
    for _, part in pairs(query_parts) do
        local query_pair = split("=", part)
        if string.match(query_pair[1], "^key[0-5]$") then
            results[#results + 1] = query_pair[2]
        end
    end
    return results
end

local function send_response (code, msg_string)
    return msg_string,
    {
        ["Content-Type"] = "application/json"
    },
    code
end

-- Date utility functions
local function add_interval (date, interval_length, interval_size)
    if interval_size == "Y" then
        return date:addyears(interval_length)
    elseif interval_size == "M" then
        return date:addmonths(interval_length)
    end
end

local function find_snap_date_for_fixed_time_interval (start_date, req_date, end_date, interval_length, interval_size, snap_to_previous)
    local interval_in_sec = interval_size == "S" and interval_length
        or interval_size == "MM" and interval_length * 60
        or interval_size == "H" and interval_length * 60 * 60
        or interval_size == "D" and interval_length * 60 * 60 * 24
        or nil
    local date_diff = date_util.diff(req_date, start_date)
    local closest_interval_date
    if snap_to_previous then
        closest_interval_date = start_date:addseconds(math.floor(date_diff:spanseconds() / interval_in_sec) * interval_in_sec)
    else
        closest_interval_date = start_date:addseconds(math.ceil(date_diff:spanseconds() / interval_in_sec) * interval_in_sec)
    end
    if closest_interval_date <= end_date then
        return closest_interval_date
    end
end


local function find_snap_date_for_non_fixed_time_interval (start_date, req_date, end_date, interval_length, interval_size, snap_to_previous)
    local previous_interval_date = start_date
    while true do
        local check_date = add_interval(previous_interval_date:copy(), interval_length, interval_size)
        if check_date > req_date then -- Found snap date
            if snap_to_previous then
                return previous_interval_date
            elseif check_date <= end_date then 
                return check_date
            end
        end
        if check_date > end_date then -- Snap date isn't in this period
            break
        end
        previous_interval_date = check_date
    end
end

local function get_snap_date (start_date, req_date, end_date, interval_length, interval_size, snap_to_previous)
    if interval_size == "H" or interval_size == "MM" or interval_size == "S" or interval_size == "D" then
        return find_snap_date_for_fixed_time_interval(start_date, req_date, end_date, interval_length, interval_size, snap_to_previous)
    else
        return find_snap_date_for_non_fixed_time_interval(start_date, req_date, end_date, interval_length, interval_size, snap_to_previous)
    end
end

local function time_snap (req_date, periods, snap_to_previous)
    -- binary search for find snap date in periods
    local snap_date
    local snap_period_idx = 1
    local left, right, mid = 1, #periods, 0
    while left <= right do
        mid = left + math.floor( ( right - left ) / 2 )
        local parsed_period = split("/", periods[mid])
        local period_date = date_util(parsed_period[1])
    
        if req_date == period_date then
            snap_date = req_date
            snap_period_idx = mid
            break
        end
    
        local end_date
        if parsed_period[2] then -- this is a period, so look at both dates
            if req_date > period_date then
                local interval_length = tonumber(string.match(parsed_period[3], "%d+"))
                local interval_size = string.match(parsed_period[3], "%a+$")
                if string.sub(parsed_period[3], 1, 2) == "PT" and interval_size == "M" then
                    interval_size = "MM"
                end
                snap_date = get_snap_date(period_date:copy(), req_date, date_util(parsed_period[2]), interval_length, interval_size, snap_to_previous)
                snap_period_idx = mid
            end
        end
    
        if req_date < period_date then
            right = mid - 1
        else
            left = mid + 1
        end
    end
    return snap_date, snap_period_idx
end

local function period_sort(first, second)
    return date_util(split("/", first)[1]) > date_util(split("/", second)[1])
end

-- Trim to the specified number of periods and skip periods as needed
local function apply_skip_limit(layer_datetime_info, skip, specified_limit)
    local limit
    for key, value in pairs(layer_datetime_info) do
        limit = specified_limit and specified_limit or #value.periods
        if skip >= #value.periods then
            layer_datetime_info[key].periods = {}
        elseif #value.periods > math.abs(limit) or (skip > 0 and #value.periods >= skip) then
            local truncated = {}
            if limit < 0 then
                for i = #value.periods + limit + 1 - skip, #value.periods - skip do
                    truncated[#truncated+1] = value.periods[i]
                end
            else
                for i = 1 + skip, math.min(limit + skip, #value.periods) do
                    truncated[#truncated+1] = value.periods[i]
                end
            end
            layer_datetime_info[key].periods = truncated
        end
    end
    return layer_datetime_info
end

local function range_handler (default, all_periods, periods_start, periods_end)
    
    local periods_start_date = periods_start and date_util(periods_start) or nil
    local periods_end_date = periods_end and date_util(periods_end) or nil
    local first_period_start_date = #all_periods > 0 and date_util(split("/", all_periods[1])[1]) or nil
    local last_period_end_date = #all_periods > 0 and date_util(split("/", all_periods[#all_periods])[2]) or nil
    
    -- first, check if there's any data in the range
    if (periods_start_date and last_period_end_date and periods_start_date > last_period_end_date) or
        (periods_end_date and first_period_start_date and periods_end_date < first_period_start_date) then
        return "", {}
    end

    -- handle when we want periods and default between two dates
    local start_snap_date, start_snap_period_idx, end_snap_date, end_snap_period_idx
    if periods_start_date then
        start_snap_date, start_snap_period_idx = time_snap(periods_start_date, all_periods, false)
        -- if the periods start date doesn't fall within a period, then we need to skip the period that was last examined
        if start_snap_date == nil and #all_periods > 1 then
            start_snap_period_idx = start_snap_period_idx + 1
        end
    else
        start_snap_period_idx = 1
    end
    if periods_end then
        end_snap_date, end_snap_period_idx = time_snap(periods_end_date, all_periods, true)
    else
        end_snap_period_idx = #all_periods
    end
   
    local filtered_periods = {}
    -- Ensure that there's data between periods_start and periods_end.
    -- The start snap date taking place after end snap date would mean that there's no data within the bounds.
    if not (start_snap_date and end_snap_date and start_snap_date > end_snap_date) then
         -- trim the list of periods so that the period in which we found the snap date starts with the snap date
        for i = start_snap_period_idx, end_snap_period_idx do
            filtered_periods[#filtered_periods+1] = all_periods[i]
        end
        if start_snap_date then
            local parsed_period = split("/", filtered_periods[1])
            local start_snap_date_string
            if start_snap_date:gethours() > 0 or start_snap_date:getminutes() > 0 or start_snap_date:getseconds() > 0 then
                start_snap_date_string = start_snap_date:fmt(datetime_format)
            else
                start_snap_date_string = start_snap_date:fmt(date_format)
            end
            filtered_periods[1] = start_snap_date_string .. "/" .. parsed_period[2] .. "/" .. parsed_period[3]
        end
        if end_snap_date then
            local parsed_period = split("/", filtered_periods[#filtered_periods])
            local end_snap_date_string
            if end_snap_date:gethours() > 0 or end_snap_date:getminutes() > 0 or end_snap_date:getseconds() > 0 then
                end_snap_date_string = end_snap_date:fmt(datetime_format)
            else
                end_snap_date_string = end_snap_date:fmt(date_format)
            end
            filtered_periods[#filtered_periods] = parsed_period[1] .. "/" .. end_snap_date_string .. "/" .. parsed_period[3]
        end
    end

    -- Make sure default is within the final period range
    if #filtered_periods > 0 and default then
        local last_filtered_period_end_date = split("/", filtered_periods[#filtered_periods])[2]
        if date_util(default) > date_util(last_filtered_period_end_date) then
            default = last_filtered_period_end_date
        else
            local first_filtered_period_start_date = split("/", filtered_periods[1])[1]
            if date_util(default) < date_util(first_filtered_period_start_date) then
                default = first_filtered_period_start_date
            end
        end
    else
        default = ""
    end
    return default, filtered_periods
end

-- Handlers to get layer period and default date information
local function redis_get_all_layers (client, prefix_string, periods_start, periods_end)
    local layers = {}
    local cursor = "0"
    local results
    repeat
        cursor, results = unpack(client:scan(cursor, {match = prefix_string .. "layer:*"}))
        for _, value in pairs(results) do
            local value_parts = split(":", value)
            local layer_name = value_parts[#value_parts - 1]
            layers[layer_name] = not layers[layer_name] and {} or layers[layer_name]
            local default = client:get(prefix_string .. "layer:" .. layer_name .. ":default")
            local periods
            if client:type(prefix_string .. "layer:" .. layer_name .. ":periods") == "zset" then
                periods = client:zrange(prefix_string .. "layer:" .. layer_name .. ":periods", 0, -1)
            else
                periods = client:smembers(prefix_string .. "layer:" .. layer_name .. ":periods")
                if periods then
                    table.sort(periods)
                end
            end
            if periods then
                if periods_start or periods_end then
                    layers[layer_name].default, layers[layer_name].periods = range_handler(default, periods, periods_start, periods_end)
                else
                    layers[layer_name].default = default
                    layers[layer_name].periods = periods
                end
                layers[layer_name].periods_in_range = #layers[layer_name].periods
            end
        end
    until cursor == "0"
    return layers
end

local function redis_handler (options)
    local redis = require 'redis'
    --TBD: Handle connection error
    local client = redis.connect(options.host, options.port or 6379)
    closeFunc = function()
        client:quit()
    end
    return function (layer_name, uuid, lookup_keys, snap_date_string, periods_start, periods_end)
        local returnValue
        local start_db_request = socket.gettime() * 1000 * 1000
        local prefix_string = ""
        if lookup_keys then
            for _, value in pairs(lookup_keys) do
                prefix_string = prefix_string .. value .. ":"
            end
        end
        if layer_name then
            if snap_date_string then
                local ok_hget, best_layer_name = pcall(client.hget, client, prefix_string .. "layer:" .. layer_name .. ":best", snap_date_string)
                -- Handle Redis Error
                if not ok_hget then
                    print("ERROR querying Redis hget: " .. tostring(best_layer_name))
                    return send_response(503, JSON:encode({err_msg="Time database error"}))
                end
                if best_layer_name then 
                    returnValue = best_layer_name
                else 
                    returnValue = layer_name
                end
            else
                local ok_get, default_val = pcall(client.get, client, prefix_string .. "layer:" .. layer_name .. ":default")
                if not ok_get then
                    print("ERROR querying Redis get: " .. tostring(default_val)) -- default_val is the error here
                    return send_response(503, JSON:encode({err_msg="Time database error"}))
                end
                -- default is set to actual value or nil if not found
                local default = default_val

                local periods
                local ok, result = pcall(client.type, client, prefix_string .. "layer:" .. layer_name .. ":periods")
                if not ok then
                    -- Log the error: result contains error message
                    print("ERROR querying Redis type: " .. tostring(result))
                    -- Return a 5xx error or specific JSON error indicating Redis issue
                    return send_response(503, JSON:encode({err_msg="Time database error"}))
                end

                local key_type = result
                if key_type == "zset" then
                    ok, result = pcall(client.zrange, client, prefix_string .. "layer:" .. layer_name .. ":periods", 0, -1)
                    if not ok then
                        print("ERROR querying Redis zrange: " .. tostring(result))
                        return send_response(503, JSON:encode({err_msg="Time database error"}))
                    end
                    periods = result
                elseif key_type == "set" then
                    --  wrap smembers in pcall
                    ok, result = pcall(client.smembers, client, prefix_string .. "layer:" .. layer_name .. ":periods")
                    if not ok then
                        print("ERROR querying Redis smembers: " .. tostring(result))
                        return send_response(503, JSON:encode({err_msg="Time database error"}))
                    end
                    periods = result
                else
                    periods = nil -- Key doesn't exist or wrong type
                end

                 -- Handle Case of Data is legitimately missing 
                if not periods or #periods == 0 then
                    returnValue = {err_msg = "Invalid Layer"}
                else
                    -- process periods
                    table.sort(periods)
                    if periods_start or periods_end then
                        default, periods = range_handler(default, periods, periods_start, periods_end) 
                    end
                    if default and periods then
                        returnValue = {[layer_name] = {
                            default = default,
                            periods = periods,
                            periods_in_range = #periods
                        }}
                    end
                end -- process periods
            end
        else
            -- If no layer name specified, dump all data
            -- note: consider wrapping redis query calls in pcall
            returnValue = redis_get_all_layers(client, prefix_string, periods_start, periods_end)
        end
        -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
        print(string.format("step=time_database_request duration=%d uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_db_request + 0.5), uuid))
        return returnValue
    end
end

-- Handlers to format output filenames
local function basic_date_formatter (options)
    return function (layer_name, date)
        -- static layer hack
        if ((tonumber(date:fmt("%Y")) <= 1900) or (tonumber(date:fmt("%Y")) >= 2899)) then
            return layer_name
        else
            return layer_name .. "-" .. date:fmt(datetime_filename_format)
        end
    end
end

local function hash_formatter ()
    return function (layer_name, date)
        local date_string = date:fmt(datetime_filename_format)
        local base_filename_string = layer_name .. "-" .. date_string
        local hash = md5.sumhexa(base_filename_string):sub(0, 4)
        local filename_string = hash .. "-" .. layer_name .. "-" .. date_string
        return filename_string
    end
end

local function strftime_formatter (options)
    return function (layer_name, date)
        return layer_name .. date:fmt(options.options.format_str)
    end
end



-- Main date snapping handler -- this returns a function that's intended to be called by mod_ahtse_lua
function onearthTimeService.timeService (layer_handler_options, filename_options)
    local JSON = require("JSON")
    local layer_handler = layer_handler_options.handler_type == "redis" and redis_handler(layer_handler_options) or nil
    local filename_handler = not filename_options and basic_date_formatter(filename_options)
        or filename_options.filename_format == "hash" and hash_formatter(filename_options)
        or filename_options.filename_format == "strftime" and strftime_formatter(filename_options)
        or filename_options.filename_format == "basic" and basic_date_formatter(filename_options)
        or basic_date_formatter(filename_options)

    return function (query_string, headers, _)
        local uuid = headers["UUID"] or "none"
        local start_timestamp = socket.gettime() * 1000 * 1000
        local layer_name = query_string and get_query_param("layer", query_string) or nil
        local periods_start = query_string and get_query_param("periods_start", query_string) or nil
        local periods_end = query_string and get_query_param("periods_end", query_string) or nil
        local limit = query_string and tonumber(get_query_param("limit", query_string)) or nil
        local skip = query_string and tonumber(get_query_param("skip", query_string)) or 0
        local lookup_keys = query_string and get_query_keys(query_string) or nil

        -- A blank query returns the entire list of layers and periods
        if not query_string or not layer_name then
            -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
            print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
            local layer_datetime_info = layer_handler(nil, uuid, lookup_keys, nil, periods_start, periods_end)
            if limit or skip > 0 then
                layer_datetime_info = apply_skip_limit(layer_datetime_info, skip, limit)
            end
            return send_response(200, JSON:encode(layer_datetime_info))
        end

        local request_date_string = get_query_param("datetime", query_string)
        local layer_datetime_info = layer_handler(layer_name, uuid, lookup_keys, nil, periods_start, periods_end)
        if layer_datetime_info.err_msg then
            return send_response(200, JSON:encode(layer_datetime_info))
        end

        -- A layer but no date returns the default date and available periods for that layer
        if not request_date_string then
            -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
            print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
            if limit or skip > 0 then
                layer_datetime_info = apply_skip_limit(layer_datetime_info, skip, limit)
            end
            return send_response(200, JSON:encode(layer_datetime_info))
        end

        -- If it's a default request, return the default date, best layer name, and filename
        if string.lower(request_date_string) == "default" then
            local default_date = date_util(layer_datetime_info[layer_name].default)
            local best_layer_name = layer_handler(layer_name, uuid, lookup_keys, default_date:fmt(datetime_format))
            local out_msg = {
                prefix = best_layer_name,
                date = default_date:fmt(datetime_format),
                filename = filename_handler(best_layer_name, default_date)}
            -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
            print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Send error message if date is in a bad format
        if not string.match(request_date_string, date_template) and not string.match(request_date_string, datetime_template) then
            local out_msg = {
                err_msg = "Invalid Date"
            }
            -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
            print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Send error message if we can't parse the date for any other reason
        local pass, req_date = pcall(date_util, request_date_string)
        if not pass then
            local out_msg = {
                err_msg = "Invalid Date"
            }
            -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
            print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
            return send_response(200, JSON:encode(out_msg))
        end

        -- Find snap date if date request is valid
        local snap_date
        if not layer_datetime_info[layer_name] then
            local out_msg = {
                err_msg = "Invalid Layer"
            }
            return send_response(200, JSON:encode(out_msg))
        end

        local snap_date, _ = time_snap(req_date, layer_datetime_info[layer_name].periods, true)

        -- Return snap date and error if none is found
        local out_msg
        if snap_date then
            local snap_date_string = snap_date:fmt(datetime_format)

            -- Use "best" layer name if exists, otherwise just use layer_name
            local best_layer_name = layer_handler(layer_name, uuid, lookup_keys, snap_date_string)
            out_msg = {
                prefix = best_layer_name,
                date = snap_date_string,
                filename = filename_handler(best_layer_name, snap_date)}
        else
            out_msg = {
                err_msg = "Date out of range"
            }
        end
        -- use math.floor(a + 0.5) to round to the nearest integer to prevent "number has no integer representation" error
        print(string.format("step=timesnap_request duration=%u uuid=%s", math.floor(socket.gettime() * 1000 * 1000 - start_timestamp + 0.5), uuid))
        return send_response(200, JSON:encode(out_msg))
    end
end
return onearthTimeService
