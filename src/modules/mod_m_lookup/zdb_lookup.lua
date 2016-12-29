-- ZDB LUA CONFIGURATION SCRIPT

-- These are configuration variables that indicate the location of the ZDB files and the prefix to use
-- for their filenames. This must be configured for each layer.
local zdbPath = '/var/www/html/onearth/test_zdb/'
local zdbPrefix = 'layer'

-- These lines load external Lua libraries. The libraries must be installed with luarocks.
local sqlite3 = require('lsqlite3')
local path = require('pl.path')
local time = require('posix.time')

-- The getZ function must return a single integer corresponding to the z-level in the MRF.
function getZ(layerName, mValue, tileMatrixSet, matrix, row, col)
	-- Parse incoming time string
	local reqDate = time.strptime(mValue, '%Y-%m-%dT%H:%M:%S')
	if not reqDate then 
		return false, 'Date/time is invalid. Must be in YYYY-MM-DDTHH:MM:SS (ISO 8601) format.'
	end

	-- First figure out the name of the ZDB file we want to look at
	local fileDateString = time.strftime('%Y%j', reqDate)
	local zdbFilename = zdbPrefix .. fileDateString .. '_.zdb'
	local zdbPath = path.join(zdbPath, zdbFilename)

	-- Now get the datetime string used as a key in the ZDB
	local keyString =  time.strftime('%Y%m%d%H%M%S', reqDate)

	-- Open ZDB and get z-index for key
	local db = sqlite3.open(zdbPath, sqlite3.SQLITE_OPEN_READONLY)
	if not db then
		local dateErrStr =  time.strftime('%Y-%m-%d', reqDate)
		return false, "Can't find image data for date: " .. dateErrStr
	end

	local sql = "select * from zindex where key_str=" .. keyString .. " limit 1;"
	for row in db:nrows(sql) do
		return true, row.z
	end

	return false, "Can't find image data for date: " .. mValue
end