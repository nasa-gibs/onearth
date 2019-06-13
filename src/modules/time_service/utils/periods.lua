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

local function calcIntervalFromSeconds(interval)
	if interval % 86400 == 0 then
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

local function calculatePeriods(dates)
	local periods = {}
	table.sort(dates, dateSort)

	local datesInPeriods = {} -- Since a date can only be in one period, we keep track of all dates we've matched to periods so we can avoid them during iteration,.

	-- Check for year matches
	for _, date1 in ipairs(dates) do
		if not itemInList(date1, datesInPeriods) then
			local tail = date1:sub(5)
			local baseYear = tonumber(date1:sub(1, 4))

			for _, date2 in ipairs(dates) do
				local date2Year = tonumber(date2:sub(1, 4))
				if not itemInList(date2, datesInPeriods) 
					and date1 ~= date2 
					and date2:sub(5) == tail 
					and date2Year > baseYear 
				then
					local interval = date2Year - baseYear				
					local nextDateInInterval = dateAtInterval(date2, interval, dates, "year")

					if nextDateInInterval then
						-- We've found 3 dates at this interval, so it's a valid period. Now find the rest.
						local dateList = {date1, date2}
						while nextDateInInterval do
							dateList[#dateList+1] = nextDateInInterval
							nextDateInInterval = dateAtInterval(nextDateInInterval, interval, dates, "year")
						end

						datesInPeriods = concat(datesInPeriods, dateList)
						periods[#periods + 1] = {size=interval, dates=dateList, unit="year"}
					end
				end
			end
		end
	end


	-- Check for time period matches
	for _, date1 in ipairs(dates) do
		if not itemInList(date1, datesInPeriods) then
			for _, date2 in ipairs(dates) do
				if not itemInList(date2, datesInPeriods) and date1 ~= date2 then
					local dateEpoch1 = dateToEpoch(date1)
					local dateEpoch2 = dateToEpoch(date2)
					if dateEpoch1 < dateEpoch2 then
						local intervalInSec = dateEpoch2 - dateEpoch1
						local nextDateInInterval = dateAtFixedInterval(dateEpoch2, intervalInSec, dates)
						if nextDateInInterval then
							local epochDateList = {dateEpoch1, dateEpoch2}
							local size, unit = calcIntervalFromSeconds(intervalInSec)

							while nextDateInInterval do
								epochDateList[#epochDateList + 1] = nextDateInInterval
								nextDateInInterval = dateAtFixedInterval(nextDateInInterval, intervalInSec, dates)
							end
							
							local dateList = {}
							for i, epoch in ipairs(epochDateList) do
								dateList[#dateList + 1] = epochToDate(epoch)
							end

							if isValidPeriod(size, unit) then
								datesInPeriods = concat(datesInPeriods, dateList)
								periods[#periods + 1] = {size=size, dates=dateList, unit=unit}
							end
						end
					end
				end
			end
		end
	end

	-- Leftover dates are loners
	for _, date in ipairs(dates) do
		if not itemInList(date, datesInPeriods) then
			periods[#periods + 1] = {dates={date}}
		end
	end

	-- Create formatted list
	local periodStrings = {}
	for _, period in pairs(periods) do
		local periodStr
		if #period["dates"] > 1 then
			periodStr =  period["dates"][1] .. "/" .. period["dates"][#period["dates"]] .. "/P" .. period["size"] .. getIntervalLetter(period["unit"])
		else
			periodStr = period["dates"][1]
		end
		periodStrings[#periodStrings + 1] = periodStr
	end

	return periodStrings
end

-- REDIS SYNTAX == EVAL {script} layer_prefix:layer_name
-- Routine called by Redis. Read all dates, create periods, and replace old period entries
-- with new list.
redis.replicate_commands()
local dates = {}
local cursor = "0"
repeat
	local scan = redis.call("SSCAN", KEYS[1] .. ":dates", cursor)
	dates = concat(dates, scan[2])
	cursor = scan[1]
until cursor == "0"

local periodStrings = calculatePeriods(dates)
if redis.call("EXISTS", KEYS[1] .. ":periods") then
	redis.call("DEL", KEYS[1] .. ":periods")
end
for i, periodString in ipairs(periodStrings) do
	redis.call("SADD", KEYS[1] .. ":periods", periodString)
end
local defaultDate = getLatestDate(dates)
redis.call("SET", KEYS[1] .. ":default", defaultDate)
