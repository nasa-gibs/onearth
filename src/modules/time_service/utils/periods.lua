local function concat(t1, t2)
  for _, val in ipairs(t2) do
    t1[#t1+1] = val
  end
  return t1
end

local function isLeapYear(year)
  return year % 4 == 0 and year % 100 ~= 0 or year % 400 == 0
end

local function getDaysInMonth(month, year)
  local daysRef = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}
  return month == 2 and (daysRef[2] + (isLeapYear(year) and 1 or 0)) or daysRef[month]
end

local function getDaysInYear(year)
  local days = 0
  local month = 1
  while month <= 12 do
    days = days + getDaysInMonth(month, year)
    month = month + 1
  end
  return days
end

local function calcDayOfYear(dateStr)
  local year = tonumber(dateStr:sub(1, 4))
  local month = tonumber(dateStr:sub(6, 7))
  local day = tonumber(dateStr:sub(9, 10))

  local counter = 1
  while counter < month do
    day = day + getDaysInMonth(counter, year)
    counter = counter + 1
  end
  return day
end

local function dayOfYearToDate(doy, year)
  local month = 1
  local dayCounter = 1

  local counting = true
  while counting do
    local daysInMonth = getDaysInMonth(month, year)
    if dayCounter + daysInMonth > doy then
      counting = false
    else
      dayCounter = dayCounter + daysInMonth
      month = month + 1
    end
  end

  local monthStr = tostring(month)
  if monthStr:len() < 2 then
    monthStr = "0" .. monthStr
  end

  local dayStr = tostring(doy - dayCounter + 1)
  if dayStr:len() < 2 then
    dayStr = "0" .. dayStr
  end

  return year .. "-" .. monthStr .. "-" .. dayStr
end

local function calcDayDelta(date1, date2)
  local dates = {}
  for i, dateStr in ipairs({date1, date2}) do
    local year = tonumber(dateStr:sub(1, 4))
    local month = tonumber(dateStr:sub(6, 7))
    local day = tonumber(dateStr:sub(9, 10))
    dates[i] = {year=year, month=month, day=day}
  end

  local doy1 = calcDayOfYear(date1)
  local doy2 = calcDayOfYear(date2)

  if dates[1]['year'] == dates[2]['year'] then
    return doy2 - doy1
  end

  local counter = getDaysInYear(dates[1]['year']) - doy1
  local yearCounter = dates[1]['year'] + 1
  while yearCounter < dates[2]['year'] do
    counter = counter + getDaysInYear(yearCounter)
    yearCounter = yearCounter + 1
  end

  return counter + doy2
end

local function dateToEpoch(dateStr)
  local year = tonumber(dateStr:sub(1, 4))
  local month = tonumber(dateStr:sub(6, 7))
  local day = tonumber(dateStr:sub(9, 10))
  local hour = tonumber(dateStr:sub(12, 13)) or 0
  local minute = tonumber(dateStr:sub(15, 16)) or 0
  local second = tonumber(dateStr:sub(18, 19)) or 0
  local doy = calcDayOfYear(dateStr)

  local yearSecCounter = 0
  local yearCounter = 1970
  while yearCounter < year do
    yearSecCounter = yearSecCounter + (isLeapYear(yearCounter) and 366 or 365) * 24 * 60 * 60
    yearCounter = yearCounter + 1
  end

  return yearSecCounter + ((doy - 1) * 86400) + (hour * 60 * 60)  + (minute * 60) + second
end

local function calcEpochDiff(epochDate, count, interval)
  local intervalInSec
  if interval == "Y" then intervalInSec = 31536000
  elseif interval == "D" then intervalInSec = 86400
  elseif interval == "H" then intervalInSec = 3600
  elseif interval == "MM" then intervalInSec = 60
  elseif interval == "S" then intervalInSec = 1
  end
  if epochDate and count and intervalInSec then 
    epochDate = epochDate + ( count * intervalInSec )
  end
  return epochDate
end

local function calcIntervalFromSeconds(interval)
  if interval % 31536000 == 0 then
    return math.floor(interval / 31536000), "year"
  elseif interval % 86400 == 0 then
    return math.floor(interval / 86400), "day"
  elseif interval % 3600 == 0 then
    return math.floor(interval / 3600), "hour"
  elseif interval % 60 == 0 then
    return math.floor(interval / 60), "minute"
  else
    return math.floor(interval), "second"
  end
end

local function padToLength(str, char, len, pos)
  while str:len() < len do
    if pos == "tail" then
      str = str .. char
    else
      str = char .. str
    end
  end
  return str
end

local function calcSecondsInYear(year)
  local days = isLeapYear(year) and 366 or 365
  return days * 24 * 60 * 60
end

local function epochToDate(epoch)
  local year = 1970
  local secCounter = epoch

  -- Get the year
  local loop = true
  repeat
    local secondsInYear = calcSecondsInYear(year)
    if secCounter >= secondsInYear then
      secCounter = secCounter - secondsInYear
      year = year + 1
    else
      loop = false
    end
  until not loop

  -- Get the date
  local doy = math.floor(secCounter / 86400) + 1
  local date = dayOfYearToDate(doy, year)
  secCounter = secCounter - ((doy - 1) * 86400)

  -- Get the time
  local hours = tostring(math.floor(secCounter / 3600))
  hours = padToLength(hours, "0", 2)
  secCounter = secCounter - hours * 3600

  local minutes = tostring(math.floor(secCounter / 60))
  minutes = padToLength(minutes, "0", 2)
  secCounter = secCounter - minutes * 60

  local seconds = padToLength(tostring(math.floor(secCounter)), "0", 2)

  return date .. "T" .. hours .. ":" .. minutes .. ":" .. seconds
end

local function addDaysToDate(date, days)
  local doy = calcDayOfYear(date)
  local year = tonumber(date:sub(1, 4))
  local daysInYear = getDaysInYear(year)
  if doy + days <= daysInYear then
    return dayOfYearToDate(doy + days, year)
  end
end

local function dateAtInterval(baseDate, interval, dateList, unit)
  if unit == "year" then
    local baseYear = baseDate:sub(1 ,4)
    for i, date in ipairs(dateList) do
      local year = tonumber(date:sub(1, 4))
      if year == baseYear + interval then
        return date
      end
    end
  end
  return false
end

local function dateAtFixedInterval(baseEpoch, intervalInSec, dateList)
  for i, date in ipairs(dateList) do
    local epoch = dateToEpoch(date)
    if epoch - baseEpoch == intervalInSec then
      return epoch
    end
  end
  return false
end

local function itemInList(item, list)
  for i, v in ipairs(list) do
    if v == item then
      return true
    end
  end
  return false
end


local function listContainsList(long, short)
  for i, v in ipairs(short) do
    if not itemInList(v, long) then
      return false
    end
  end
  return true
end

local function listEqualsList(list1, list2)
  if #list1 ~= #list2 then
    return false
  end
  for i, v in ipairs(list1) do
    if not itemInList(v, list2) then
      return false
    end
  end
  return true
end

local function getIntervalLetter(unit)
  if unit == "year" then
    return "Y"
  elseif unit == "month" then
    return "M"
  elseif unit == "day" then
    return "D"
  elseif unit == "hour" then
    return "H"
  elseif unit == "minute" then
    return "MM"
  elseif unit == "second" then
    return "S"
  end
end

local function getIntervalUnit(period)
  local letter = string.sub(period, -1)
  if period:sub(1, 2) == 'PT' then
    if letter == "H" then
      return "hour"
    elseif letter == "M" or letter == "MM" then
      return "minute"
    else
      return "second"
    end
  else
    if letter == "Y" then
      return "year"
    elseif letter == "M" then
      return "month"
    else
      return "day"
    end
  end
end

local function isValidPeriod(size, unit)
  if unit == "day" and size >= 365 then
    return false
  end
  return true
end

local function dateSort(a, b)
  return dateToEpoch(a) < dateToEpoch(b)
end

local function getLatestDate(dates)
  local maxEpoch = 0
  for i, date in ipairs(dates) do
    local epoch = dateToEpoch(date)
    maxEpoch = epoch > maxEpoch and epoch or maxEpoch
  end
  return epochToDate(maxEpoch)
end

local function epochListToDateList(epochList)
  local dateList = {}
  for _, epoch in ipairs(epochList) do
    dateList[#dateList + 1] = epochToDate(epoch)
  end
  return dateList
end

local function periodExists(size, unit, epochDateList, periods)
  for _, period in ipairs(periods) do
    if period["size"] == size and period["unit"] == unit and listContainsList(period["dates"], epochListToDateList(epochDateList)) then
      return true
    end
  end
  return false
end

--local function dump(o)
--   if type(o) == 'table' then
--      local s = '{ '
--      for k,v in pairs(o) do
--         if type(k) ~= 'number' then k = '"'..k..'"' end
--         s = s .. '['..k..'] = ' .. dump(v) .. ','
--      end
--      return s .. '} '
--   else
--      return tostring(o)
--   end
--end

local function calculatePeriods(dates, config)
  -- Parse time configurations
  local configs = {}
  for w in tostring(config):gmatch("([^/]+)") do
    configs[#configs + 1] = w
  end
  local force_start = 'DETECT'
  local force_end = 'DETECT'
  local force_period = 'DETECT'
  if configs[3] ~= nil then
    force_end = configs[2]
    force_period = configs[3]
  else
    if configs[2] ~= nil then
      if configs[2]:sub(1, 1) == 'P' then
        force_period = configs[2]
      else
        force_end = configs[2]
      end
    else
      force_end = 'DETECT'
    end
  end
  if configs[1] ~= 'false' then
    force_start = configs[1]
  end
  redis.call('ECHO', 'force_start=' .. tostring(force_start))
  redis.call('ECHO', 'force_end=' .. tostring(force_end))
  redis.call('ECHO', 'force_period=' .. tostring(force_period))
  --redis.call('ECHO', dump(dates))

  -- Don't return any periods if DETECT and no dates available
  if dates[1] == nil then
    if force_start == 'DETECT' or force_end == 'DETECT' then
      redis.call('ECHO', 'No dates available for DETECT')
      return {}
    end
  end

  -- Detect periods
  local periods = {}
  if force_start:sub(1, 6) == 'LATEST' then
    local stripLatestPrefix = force_start:sub(7, #force_start)
    local count = stripLatestPrefix:match("[+-]?%d+")
    local interval = stripLatestPrefix:match("%a+")

    local latestDateEpoch = dateToEpoch(dates[#dates])
    local diffEpoch = calcEpochDiff(latestDateEpoch, count, interval)
    force_start = epochToDate(diffEpoch)
  end
  if force_end == 'LATEST' then
    force_end = dates[#dates]
  end

  if force_start ~= 'DETECT' and force_end ~= 'DETECT' and force_period ~= 'DETECT' then
  -- Skip DETECT if all forced values are provided
    local dateList = {force_start, force_end}
    periods[#periods + 1] = {size=string.match(force_period, "%d+"), dates=dateList, unit=getIntervalUnit(force_period)}
  else
    -- Calculate periods based on dates list
    -- table.sort(dates, dateSort)
    -- Since a date can only be in one period, we keep track of all dates we've matched to periods so we can avoid them during iteration,.
    local datesInPeriods = {}

    -- Check for year matches
    local annual = false
    if dates[3] ~= nil then
      local tail1 = dates[1]:sub(5)
      local baseYear = tonumber(dates[1]:sub(1, 4))
      local tail2 = dates[2]:sub(5)
      local date2Year = tonumber(dates[2]:sub(1, 4))
      local tail3 = dates[3]:sub(5)
      local date3Year = tonumber(dates[3]:sub(1, 4))

      local interval = date2Year - baseYear
      if tail1 == tail2
        and tail2 == tail3
        and interval ~=0
        and date2Year + interval == date3Year
      then
        -- We've found 3 dates at this interval, so it's a valid period. Now find the rest.
        local dateList = {dates[1], dates[2]}
        datesInPeriods[dates[1]] = true
        datesInPeriods[dates[2]] = true

        local prevTail = tail2
        local prevYear =date2Year
        for i = 3, #dates do
          local tailI = dates[i]:sub(5)
          local dateIYear = tonumber(dates[i]:sub(1, 4))

          if prevYear + interval == dateIYear and tailI == prevTail then
            dateList[#dateList+1] = dates[i]
          else
            periods[#periods + 1] = {size=interval, dates=dateList, unit="year"}
            dateList = {dates[i]}
          end

          datesInPeriods[dates[i]] = true
          prevTail = tailI
          prevYear = dateIYear
        end

        periods[#periods + 1] = {size=interval, dates=dateList, unit="year"}
        annual = true
      end
    end

    if dates[3] ~= nil and annual == false then
      -- Figure out the size and interval of the period based on first 3 values
      local diff1 = math.abs(dateToEpoch(dates[1]) - dateToEpoch(dates[2]))
      local diff2 = math.abs(dateToEpoch(dates[2]) - dateToEpoch(dates[3]))
      if (diff1 == diff2) then
        local size, unit = calcIntervalFromSeconds(diff1)
        if isValidPeriod(size, unit) then
          local dateList = {}
          dateList[1] = dates[1] -- set start time to first time
          for i, date1 in ipairs(dates) do
            local dateEpoch1 = dateToEpoch(date1)
            if dates[i+1] == nil then
              dateList[#dateList + 1] = date1
              periods[#periods + 1] = {size=size, dates=dateList, unit=unit}
            else
              local dateEpoch2 = dateToEpoch(dates[i+1])
              local diff = math.abs(dateEpoch2 - dateEpoch1)
              if diff ~= diff1 then
                dateList[#dateList + 1] = date1
                local period = {}
                period[1] = dateList[1]
                period[2] = dateList[2]
                periods[#periods + 1] = {size=size, dates=period, unit=unit}
                dateList[1] = dates[i+1]
                dateList[2] = nil
              end
            end
          end
        end
      else -- More complicated scenarios
        -- TODO: Detect breaks in periods
        -- Check for monthly periods
        if (diff1 % 2678400 == 0) or (diff2 % 2678400 == 0) or (diff1 % 5270400 == 0) or (diff2 % 5270400 == 0) then
          local size = math.floor(diff1/2419200)
          local unit = "month"
          local dateList = {}
          dateList[1] = dates[1] -- set start time to first time
          dateList[#dateList + 1] = dates[#dates]  -- set end time to last time
          periods[#periods + 1] = {size=size, dates=dateList, unit=unit}
        else
          -- Use seconds for subdaily and days otherwise
          local unit = "day"
          if (diff1<86400) then
            unit = "second"
            local dateList = {}
            dateList[1] = dates[1] -- set start time to first time
            dateList[#dateList + 1] = dates[#dates]  -- set end time to last time
            periods[#periods + 1] = {size=1, dates=dateList, unit=unit}
          else
            for _, date in ipairs(dates) do
              if not datesInPeriods[date] then
                periods[#periods + 1] = {size=1, dates={date}, unit=unit}
              end
            end
          end
        end
      end
    else
      -- Leftover times are likely loners
      -- Determine if subdaily or not (assume daily if single)
      local unit = "day"
      if dates[2] ~= nil then
        local diff1 = math.abs(dateToEpoch(dates[1]) - dateToEpoch(dates[2]))
        if (diff1<86400) then
          unit = "second"
         end
      end
      for _, date in ipairs(dates) do
        if not datesInPeriods[date] then
          periods[#periods + 1] = {size=1, dates={date}, unit=unit}
        end
      end
    end
  end

  -- Replace with forced values
  if force_start ~= "DETECT" then
    if force_period:sub(1, 2) == 'PT' and #force_start < 11 then
      force_start = force_start .. "T00:00:00"
    end
    periods[1]["dates"][1] = force_start
  end
  if force_end ~= "DETECT" then
    if force_period:sub(1, 2) == 'PT' and #force_end < 11 then
      force_end = force_end .. "T00:00:00"
    end
    periods[#periods]["dates"][#periods[#periods]["dates"]] = force_end
  end

  -- Create formatted list
  local periodStrings = {}
  for _, period in pairs(periods) do
    local periodStr
    if force_period ~= "DETECT" then
      period["size"] = string.match(force_period, "%d+")
      period["unit"] = getIntervalUnit(force_period)
    end
    if getIntervalLetter(period["unit"]) == "H" or getIntervalLetter(period["unit"]) == "MM" or getIntervalLetter(period["unit"]) == "S" then
      periodStr =  period["dates"][1] .. "Z/" .. period["dates"][#period["dates"]] .. "Z/PT" .. period["size"] .. getIntervalLetter(period["unit"])
      if period["unit"] == "minute" then
       -- Remove the MM hack for minutes
       periodStr = periodStr:sub(1, #periodStr - 1)
      end
    else
      periodStr =  string.sub(period["dates"][1], 0, 10) .. "/" .. string.sub(period["dates"][#period["dates"]], 0, 10) .. "/P" .. period["size"] .. getIntervalLetter(period["unit"])
    end
    periodStrings[#periodStrings + 1] = periodStr
  end
  --Not needed since values are stored in an unordered list in Redis
  --table.sort(periodStrings)
  --redis.call('ECHO', dump(periodStrings))
  return periodStrings
end

-- REDIS SYNTAX == EVAL {script} layer_prefix:layer_name , date_time
-- Routine called by Redis. Read all dates, create periods, and replace old period entries
-- with new list.
redis.replicate_commands()
local dates = {}
local configs = {}
local cursor = "0"

-- GITC mod: Add new date and only update if there was a change
if ARGV[1] ~= nil and ARGV[1] ~= "false" then
  local result = 0
  if ARGV[1]:match("(%d+)-(%d+)-(%d+)") then
    result = redis.call("ZADD", KEYS[1] .. ":dates", 0, ARGV[1])
    if KEYS[2] == "true" then
      result = redis.call("ZADD", KEYS[1] .. ":expiration", 0, ARGV[1])
    end
  end
  if result == 0 then
    return
  end
end
-- End GITC mod

local dates = redis.call("ZRANGE", KEYS[1] .. ":dates", 0, -1)
local expiration = redis.call("ZRANGE", KEYS[1] .. ":expiration", 0, -1)


-- Calculate periods for each time configuration per layer
repeat
  local scan = redis.call("SSCAN", KEYS[1] .. ":config", cursor)
  configs = concat(configs, scan[2])
  cursor = scan[1]
until cursor == "0"

if next(configs) == nil then
  local config = redis.call("GET", KEYS[1] .. ":config")
  local periodStrings = calculatePeriods(dates, config)
  if redis.call("EXISTS", KEYS[1] .. ":periods") then
    redis.call("DEL", KEYS[1] .. ":periods")
  end
  for i, periodString in ipairs(periodStrings) do
    redis.call("SADD", KEYS[1] .. ":periods", periodString)
  end
else
  for i, config in ipairs(configs) do
    local periodStrings = calculatePeriods(dates, config)
    if i == 1 then
      if redis.call("EXISTS", KEYS[1] .. ":periods") then
        redis.call("DEL", KEYS[1] .. ":periods")
      end
    end
    for i, periodString in ipairs(periodStrings) do
      redis.call("SADD", KEYS[1] .. ":periods", periodString)
    end
  end
end

-- table.sort(dates, dateSort)

local defaultDate = dates[#dates]
if defaultDate ~= nil then
  if string.sub(dates[#dates], 12) == "00:00:00" then
    defaultDate = string.sub(dates[#dates], 0, 10)
  end
  redis.call("SET", KEYS[1] .. ":default", defaultDate)
else
  -- use last config time if there are no dates
  local lastConfig = nil
  table.sort(configs)
  -- loop backwards to find last config without DETECT
  for i = #configs, 1, -1 do
    if string.find(configs[i], "DETECT") == nil then
      lastConfig = configs[i]
      break
    end
  end
  if lastConfig ~= nil then
    local configParts = {}
    for w in tostring(lastConfig):gmatch("([^/]+)") do
      configParts[#configParts + 1] = w
    end
    if configParts[3] ~= nil then
      defaultDate = configParts[2]
      if string.sub(configParts[2], 12) == "00:00:00" then
        defaultDate = string.sub(configParts[2], 0, 10)
      end
      redis.call("SET", KEYS[1] .. ":default", defaultDate)
    end
  end
end
