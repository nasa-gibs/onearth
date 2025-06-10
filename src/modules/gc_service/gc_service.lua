local onearth_gc_service = {}

local lfs = require "lfs"
local yaml = require "yaml"
local request = require "http.request"
local JSON = require "JSON"
local xml = require "pl.xml"

-- Reference Constants
local EARTH_RADIUS = 6378137.0
local PROJECTIONS = {
    ["EPSG:3031"] = {
        wkt='PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, -90}, upperCorner={180, -38.941373}},
        bbox={crs="urn:ogc:def:crs:EPSG::3031", lowerCorner={-4194304, -4194304}, upperCorner={194304, 4194304}}
    },
    ["EPSG:3031-Extended"] = {
        wkt='PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-135, 19.735368}, upperCorner={45, 19.735368}},
        bbox={crs="urn:ogc:def:crs:EPSG::3031", lowerCorner={-12400000, -12400000}, upperCorner={12400000, 12400000}}
    },
    ["EPSG:3413"] = {
        wkt='PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, 38.807151}, upperCorner={180, 90}},
        bbox={crs="urn:ogc:def:crs:EPSG::3413", lowerCorner={-4194304, -4194304}, upperCorner={4194304, 4194304}}
    },
    ["EPSG:3413-Extended"] = {
        wkt='PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-90, -19.897867}, upperCorner={90, -19.897867}},
        bbox={crs="urn:ogc:def:crs:EPSG::3031", lowerCorner={-12400000, -12400000}, upperCorner={12400000, 12400000}}
    },
    ["EPSG:3857"] = {
        wkt='PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, -85.051129}, upperCorner={180, 85.051129}},
        bbox={crs="urn:ogc:def:crs:EPSG::3857", lowerCorner={-20037508.34278925, -20037508.34278925}, upperCorner={20037508.34278925, 20037508.34278925}}
    },
    ["EPSG:4326"] = {
        wkt='GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, -90}, upperCorner={180, 90}},
    }
}

local date_template = "%d%d%d%d%-%d%d?%-%d%d?$"
local datetime_template = "%d%d%d%d%-%d%d?%-%d%d?T%d%d?:%d%d?:%d%d?Z$"

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

local function getExtensionFromMimeType(mimeType)
    if mimeType == "image/jpeg" then
        return ".jpeg"
    end
    if mimeType == "image/png" then
        return ".png"
    end
    if mimeType == "image/tiff" then
        return ".tiff"
    end
    if mimeType == "image/lerc" then
        return ".lerc"
    end
    if mimeType == "application/x-protobuf;type=mapbox-vector" then
        return ".pbf"
    end
    if mimeType == "application/vnd.mapbox-vector-tile" then
        return ".mvt"
    end
end

local function merge_time_service_results(t1, t2)
    for k1,v1 in pairs(t2) do
        for k2,v2 in pairs(v1) do
            if type(v2) == "table" then -- append periods
                for i = 1, #v2 do
                    t1[k1][k2][#t1[k1][k2] + 1] = v2[i]
                end
            else
                t1[k1][k2] = v2
            end
        end
    end
    return t1
end

local function getDateList(endpointConfig, layer, periods_start, periods_end, limit)
    local dateServiceUri = endpointConfig["time_service_uri"]
    local dateServiceKeys = endpointConfig["time_service_keys"]

    if string.sub(dateServiceUri, -1) ~= "?" then
        dateServiceUri = dateServiceUri .. "?"
    end
    
    -- assemble the base request URI
    local base_query_options = {}
    if dateServiceKeys then
        for idx, value in ipairs(dateServiceKeys) do
            base_query_options[#base_query_options + 1] = "key" .. tostring(idx) .. "=" .. value
        end
    end
    if layer then
        base_query_options[#base_query_options + 1] = "layer=" .. layer
    end
    if periods_start then
        base_query_options[#base_query_options + 1] = 'periods_start=' .. periods_start
    end
    if periods_end then
        base_query_options[#base_query_options + 1] = 'periods_end=' .. periods_end
    end

    -- Requests for more than 100 periods will be broken up into multiple requests to the time service.
    -- If limit wasn't specified, then we will continue performing requests until all periods have been obtained
    local left_to_req = limit and math.abs(limit) or nil
    local sign
    if limit and limit > 0 or not limit then
        sign = 1
    else
        sign = -1
    end
    local max_req_amt = 100
    local dateList = nil
    local skip = 0
    while not left_to_req or left_to_req > 0 do
        local requestUri = dateServiceUri
        local current_query_options = {}
        for k, v in pairs(base_query_options) do
            current_query_options[k] = v
        end
        
        -- assemble the URI for this particular request
        if left_to_req then
            local req_amt = math.min(left_to_req, max_req_amt)
            current_query_options[#current_query_options + 1] = 'limit=' .. tostring(sign * req_amt)
            current_query_options[#current_query_options + 1] = 'skip=' .. tostring(skip)
        else
            current_query_options[#current_query_options + 1] = 'limit=' .. tostring(max_req_amt)
        end

        local queryString = join(current_query_options, "&")
        requestUri = requestUri .. queryString
        
        -- perform the request
        local success, headers, stream = pcall(function ()
            return assert(request.new_from_uri(requestUri):go(300))
        end)
        if not success then
            print("Error: " .. headers .. " -- Skipping periods for this layer")
            return {}
        end
        
        local body = assert(stream:get_body_as_string())
        if headers:get ":status" ~= "200" then
            print("Error contacting date service: " .. body)
            return nil
        end

        -- decode the request and merge with the results of any previous requests
        local reqDateList = JSON:decode(body)
        if reqDateList["err_msg"] == "Invalid Layer" then
            return {}
        end
        if not dateList then
            dateList = reqDateList
        else
            if sign > 0 then
                dateList = merge_time_service_results(dateList, reqDateList)
            else
                dateList = merge_time_service_results(reqDateList, dateList)
            end
        end

        -- after the first request, determine how many more requests we need to perform
        if not left_to_req or skip == 0 then
            local max_to_req = 0
            for _, v in pairs(dateList) do
                max_to_req = math.max(max_to_req, tonumber(v["periods_in_range"]))
            end
            -- when a limit isn't specified, we'll request the maximum amount of periods
            if not left_to_req then
                left_to_req = max_to_req
            -- when a limit is specified, we'll ensure that the limit is no greater than the maximum amount of periods
            elseif skip == 0 then
                left_to_req = math.min(max_to_req, left_to_req)
            end
        end
        left_to_req = left_to_req - max_req_amt
        skip = skip + max_req_amt
    end
    return dateList
end

local function getTmsDefs(tmsXml)
    local tmsDefs = {}
    for _, proj in ipairs(tmsXml:get_elements_with_name("Projection")) do
        local tileMatrixSets = {}
        for _, tms in ipairs(proj:get_elements_with_name("TileMatrixSet")) do
            local tmsName = tms:get_elements_with_name("ows:Identifier")[1]:get_text()
            local matrices = {}
            for matrix in tms:childtags() do
                if matrix.tag == "TileMatrix" then
                    local identifier = matrix:get_elements_with_name("ows:Identifier")[1]:get_text()
                    local topLeft = split(" ", matrix:get_elements_with_name("TopLeftCorner")[1]:get_text())
                    matrices[tonumber(identifier) + 1] = {
                        topLeft={topLeft[1], topLeft[2]},
                        scaleDenominator = matrix:get_elements_with_name("ScaleDenominator")[1]:get_text(),
                        matrixWidth = matrix:get_elements_with_name("MatrixWidth")[1]:get_text(),
                        matrixHeight = matrix:get_elements_with_name("MatrixHeight")[1]:get_text(),
                        tileWidth = matrix:get_elements_with_name("TileWidth")[1]:get_text(),
                        tileHeight = matrix:get_elements_with_name("TileHeight")[1]:get_text()
                    }
                end
            end
        tileMatrixSets[tmsName] = matrices
        end
        tmsDefs[proj:get_attribs()["id"]] = tileMatrixSets
    end
    return tmsDefs
end

local function getTmsLimitsDefs(tmsLimitsXml)
    local tmsLimitsDefs = {}
    for _, tmLimits in ipairs(tmsLimitsXml:get_elements_with_name("TileMatrixSetLimits")) do
        tmsLimitsDefs[tmLimits:get_attribs().id] = tmLimits
    end
    return tmsLimitsDefs
end

local function getReprojectedTms(sourceTms, targetEpsgCode, tmsDefs)
    -- Start by getting the maximum ScaleDenominator for the source TMS
    local function sortTms(a,b)
        return tonumber(a["scaleDenominator"]) < tonumber(b["scaleDenominator"])
    end
    table.sort(sourceTms, sortTms)
    local sourceScaleDenom = sourceTms[1]["scaleDenominator"]

    -- Now find the TMS in the destination projection that has the closest max scale denominator
    -- to the source TMS

    -- Sort the possible reprojected TileMatrixSets by the value of the biggest scale denominator in their TileMatrix(s).
    local sortedTmsDefs = {}
    for name, tms in pairs(tmsDefs[targetEpsgCode]) do
        table.sort(tms, sortTms)
        table.insert(sortedTmsDefs, {name = name, scaleDenominator = tms[1]["scaleDenominator"]})
    end
    table.sort(sortedTmsDefs, sortTms)

    local targetTms
    local targetTmsName
    local idx = #sortedTmsDefs
    while idx > 0 do
        local tmsInfo = sortedTmsDefs[idx]
        if tonumber(tmsInfo["scaleDenominator"]) < tonumber(sourceScaleDenom) then
            return targetTmsName, targetTms
        end
        targetTmsName = tmsInfo["name"]
        targetTms = tmsDefs[targetEpsgCode][targetTmsName]
        idx = idx - 1
    end
    return targetTmsName, targetTms
end

local function stripDecodeBytesFormat(inputString)
    -- Interpret any bytes in the string
    inputString = inputString:gsub("\\x(%x%x)",function (x) return string.char(tonumber(x,16)) end)
    b_removed = inputString:match("^b'(.*)'$")
    if b_removed then
        return b_removed
    end
    return inputString
end

local function makeExceptionReport(exceptionCode, exceptionText, locator, dom)
    if not dom then
        dom = xml.new("ExceptionReport", { ["xmlns:ows"] = "http://www.opengis.net/ows/1.1",
                                     ["xmlns:xsi"] =  "http://www.w3.org/2001/XMLSchema-instance",
                                     ["xsi:schemaLocation"] = "http://schemas.opengis.net/ows/1.1.0/owsExceptionReport.xsd",
                                     ["version"] = "1.1.0",
                                     ["xml:lang"] = "en" } )
    end
    local exceptionNode = xml.elem("Exception", {
        ["exceptionCode"] = exceptionCode,
        ["locator"] = locator,
        xml.elem("ExceptionText", exceptionText)
    })
    dom:add_direct_child(exceptionNode)
    return dom
end

-- GetTileService functions

local function makeTiledGroupFromConfig(filename, tmsDefs, epsgCode, targetEpsgCode)
    -- Load and parse the YAML config file
    local configFile = assert(io.open(filename, "r"))
    local status, config = pcall(yaml.eval, configFile:read("*all"))
    if not status then
        print("ERROR: Failed to parse config " .. filename .. ": " .. config)
        return nil
    end
    configFile:close()

    -- Skip hidden layers
    local hidden = false
    if config.hidden ~= nil then
        hidden = config.hidden
    end
    if config.hidden then
        return nil
    end

    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerName = assert(config.layer_name, "Can't find 'layer_name' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    local proj = assert(config.projection, "Can't find projection name in YAML!")
    local projInfo = assert(PROJECTIONS[targetEpsgCode or proj], "Can't find projection " .. proj)
    local mimeType = assert(config.mime_type, "Can't find MIME type in YAML!")
    local abstract = config.abstract
    if abstract == nil then
        abstract = layerId .. " abstract"
    end
    if mimeType == 'image/x-j' then
        mimeType = 'image/jpeg'
    end
    local bands
    if mimeType == "application/vnd.mapbox-vector-tile" then
        bands = "1"
    elseif mimeType == "image/lerc" then 
        bands = "1"
    else
        bands = mimeType == "image/png" and "4" or "3"
    end
    local static = true
    if config.static ~= nil then
        static = config.static
    end
    local bbox = projInfo["bbox"] or projInfo["bbox84"]
    local tmsName = assert(config.tilematrixset, "Can't find TileMatrixSet name in YAML!")

    -- Maintain backward compatibility with layer titles that include unicode xB5
    if string.find(layerTitle, "\\xB5") then
        layerTitle = layerTitle:gsub("\\xB5", "µ")
    end

    local tiledGroupNode = xml.elem("TiledGroup", {
        xml.new("Name"):text(layerName),
        xml.new("Title", {["xml:lang"]="en"}):text(stripDecodeBytesFormat(layerTitle)),
        xml.new("Abstract", {["xml:lang"]="en"}):text(stripDecodeBytesFormat(abstract)),
        xml.new("Projection"):text(projInfo["wkt"]),
        xml.new("Pad"):text("0"),
        xml.new("Bands"):text(bands),
        xml.new("LatLonBoundingBox", {
            minx=bbox["lowerCorner"][1],
            miny=bbox["lowerCorner"][2],
            maxx=bbox["upperCorner"][1],
            maxy=bbox["upperCorner"][2]
        }),
        xml.new("Key"):text("${time}")}
    )
    local matrices = tmsDefs[proj][tmsName]
    if targetEpsgCode and targetEpsgCode ~= epsgCode then
        _, matrices = getReprojectedTms(matrices, targetEpsgCode, tmsDefs)
    end
    table.sort(matrices, function (a, b)
        return tonumber(a["scaleDenominator"]) < tonumber(b["scaleDenominator"])
    end)
    targetEpsgCode = targetEpsgCode or epsgCode

    for _, matrix in ipairs(matrices) do
        local widthInPx = 2 * math.pi * EARTH_RADIUS / (matrix["scaleDenominator"] * 0.28E-3)
        local heightInPx = targetEpsgCode == "EPSG:4326" and widthInPx / 2 or widthInPx
        local widthRatio = widthInPx / (matrix["tileWidth"] * matrix["matrixWidth"])
        local heightRatio = heightInPx / (matrix["tileHeight"] * matrix["matrixHeight"])
        local resx = (bbox["upperCorner"][1] - bbox["lowerCorner"][1]) / (matrix["matrixWidth"] * widthRatio)
        local resy = (bbox["upperCorner"][2] - bbox["lowerCorner"][2]) / (matrix["matrixHeight"] * heightRatio)
        local xmax = tonumber(matrix["topLeft"][1]) + resx
        local ymax = tonumber(matrix["topLeft"][2]) - resy
        local template = "request=GetMap&layers=${layer}&srs=${epsg_code}&format=${mime_type}&styles=${time}&width=${width}&height=${height}&bbox=${bbox}"
        local bboxOut = {}
        for _, param in ipairs({tonumber(matrix["topLeft"][1]), ymax, xmax, tonumber(matrix["topLeft"][2])}) do
            -- Old version of OE rounded zeroes
            if param < 1 and param > -1 then
                table.insert(bboxOut, 0)
            else
                table.insert(bboxOut, string.format("%.6f", param))
            end
        end
        local make_uri = function(hasTime)
            local time = hasTime and "&time=${time}" or ""
            return string.gsub(template, "${layer}", layerId)
                :gsub("${epsg_code}", targetEpsgCode)
                :gsub("${mime_type}", mimeType)
                :gsub("${time}", time)
                :gsub("${width}", matrix["tileWidth"])
                :gsub("${height}", matrix["tileHeight"])
                :gsub("${bbox}", join(bboxOut, ","))
            end
        local outString = static and make_uri(false) or make_uri(true) .. "\n" .. make_uri(false)
        -- *****Removing the CDATA from the formatting:
        -- outString = "<![CDATA[" .. outString .. "]]>"
        tiledGroupNode:add_child(xml.new("TilePattern"):text(outString))
    end
    return tiledGroupNode
end

local function getAllGTSTiledGroups(endpointConfig, epsgCode, targetEpsgCode)
    -- Load TMS defs
    local tmsFile = assert(io.open(endpointConfig["tms_defs_file"], "r")
        , "Can't open tile matrixsets definition file at: " .. endpointConfig["tms_defs_file"])
    local tmsXml = xml.parse(tmsFile:read("*all"))
    local tmsDefs = getTmsDefs(tmsXml)
    tmsFile:close()

    local layerConfigSource = endpointConfig["layer_config_source"]

    local nodeList = {}
    local fileAttrs = lfs.attributes(layerConfigSource)
    
    if not fileAttrs then
        print("Can't open layer config location: " .. layerConfigSource)
        return
    end
    
    if fileAttrs["mode"] == "file" then
        node = makeTiledGroupFromConfig(layerConfigSource, tmsDefs, epsgCode, targetEpsgCode)
        if node ~= nil then
            nodeList[1] = node
        end
    end

    if fileAttrs["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and
                string.sub(file, 0, 1) ~= "." then
                node = makeTiledGroupFromConfig(layerConfigSource .. "/" .. file,
                 tmsDefs, epsgCode, targetEpsgCode)
                if node ~= nil then
                    nodeList[#nodeList + 1] = node
                end
            end
        end
    end
    return nodeList
end

local function makeGTS(endpointConfig)
    -- Parse header
    if not endpointConfig["gts_header_file"] then
        print("Error: no 'gts_header_file' configured!")
    end
    local headerFile = assert(io.open(endpointConfig["gts_header_file"], "r"),
        "Can't open GTS header file at:" .. endpointConfig["gts_header_file"])
    local mainXml = xml.parse(headerFile:read("*all"))
    headerFile:close()

    -- Load projection (add "EPSG:" part if omitted)
    local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
    if string.match(epsgCode:lower(), "^%d") then
        epsgCode = "EPSG:" .. epsgCode
    end

    local targetEpsgCode = endpointConfig["reproject"] and endpointConfig["reproject"]["target_epsg_code"] or endpointConfig["target_epsg_code"]
    if targetEpsgCode then
        if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
            targetEpsgCode = "EPSG:" .. targetEpsgCode
        end
    else
        targetEpsgCode = epsgCode
    end

    local projection = PROJECTIONS[targetEpsgCode or epsgCode]
    local bbox = projection["bbox"] or projection["bbox84"]

    local serviceNode = mainXml:get_elements_with_name("Service")[1]
    local onlineResourceNode = serviceNode:get_elements_with_name("OnlineResource")[1]

    -- Build <TiledPatterns> section
    local href_url = onlineResourceNode:get_attribs()["xlink:href"]
    local tiledPatternsNode = xml.elem("TiledPatterns", {
        xml.new("OnlineResource", {["xlink:href"]=href_url,
            ["xmlns:xlink"]="http://www.w3.org/1999/xlink",
            ["xlink:type"]="simple"}),
        xml.new("LatLonBoundingBox",
            { miny=bbox["lowerCorner"][2],
            minx=bbox["lowerCorner"][1],
            maxx=bbox["upperCorner"][1],
            maxy=bbox["upperCorner"][2]})
    })

    local layers = getAllGTSTiledGroups(endpointConfig, epsgCode, targetEpsgCode)
    if not layers then
        return sendResponse(400, "No layers found!")
    end

    for _, tiledGroup in ipairs(layers) do
        tiledPatternsNode:add_child(tiledGroup)
    end

    -- Add contents to the rest of the XML
    mainXml:add_direct_child(tiledPatternsNode)
    return xml.tostring(mainXml)
end


-- GetCapabilities functions
local function makeTWMSGCLayer(filename, tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode)
    -- Load and parse the YAML config file
    local configFile = assert(io.open(filename, "r"))
    local status, config = pcall(yaml.eval, configFile:read("*all"))
    if not status then
        print("ERROR: Failed to parse config " .. filename .. ": " .. config)
        return nil
    end
    configFile:close()

    -- Skip hidden layers
    local hidden = false
    if config.hidden ~= nil then
        hidden = config.hidden
    end
    if config.hidden then
        return nil
    end

    -- Look for the required data in the YAML config file, and throw errors if we can't find it
    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    local proj = assert(config.projection, "Can't find projection name in YAML!")
    -- local tmsName = assert(config.tilematrixset, "Can't find TileMatrixSet name in YAML!")

    local layerAbstract = config.abstract
    if layerAbstract == nil then
        layerAbstract = layerId .. " abstract"
    end

    -- Maintain backward compatibility with layer titles that include unicode xB5
    if string.find(layerTitle, "\\xB5") then
        layerTitle = layerTitle:gsub("\\xB5", "µ")
    end

    local layerElem = xml.new("Layer", {queryable="0"})
    layerElem:add_child(xml.new("Name"):text(layerId))
    layerElem:add_child(xml.new("Title",  {["xml:lang"]="en"}):text(stripDecodeBytesFormat(layerTitle)))
    layerElem:add_child(xml.new("Abstract",  {["xml:lang"]="en"}):text(stripDecodeBytesFormat(layerAbstract)))

    -- Get the information we need from the TMS definitions and add bbox node
    -- local tmsDef = tmsDefs[epsgCode][tmsName]
    -- if not tmsDef then
    --     print("Can't find TileMatrixSet (" .. tmsName .. ") for this layer in the TileMatrixSet definitions file." )
    -- end
    -- if targetEpsgCode ~= epsgCode then
    --     _, tmsDef = getReprojectedTms(tmsDef, targetEpsgCode, tmsDefs)
    -- end

    local bbox = PROJECTIONS[targetEpsgCode or proj]["bbox"] or PROJECTIONS[targetEpsgCode or proj]["bbox84"]

    layerElem:add_child(xml.new("LatLonBoundingBox", {
        minx=tostring(bbox["lowerCorner"][1]),
        miny=tostring(bbox["lowerCorner"][2]),
        maxx=tostring(bbox["upperCorner"][1]),
        maxy=tostring(bbox["upperCorner"][2])
    }))

    layerElem:add_child(xml.elem("Style", {
        xml.new("Name"):text("default"),
        xml.new("Title", {["xml:lang"]="en"}):text("(default) Default style")}
    ))

    layerElem:add_child(xml.new("ScaleHint", {min="10", max="100"}))
    layerElem:add_child(xml.new("MinScaleDenominator"):text("100"))

    return layerElem
end

local function makeGCLayer(filename, tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode, baseUriGC, baseUriMeta)
    -- Load and parse the YAML config file
    local configFile = assert(io.open(filename, "r"))
    local status, config = pcall(yaml.eval, configFile:read("*all"))
    configFile:close()
    if not status then
        print("ERROR: Failed to parse config " .. filename .. ": " .. config)
        return nil
    end

    -- Skip hidden layers
    local hidden = false
    if config.hidden ~= nil then
        hidden = config.hidden
    end
    if config.hidden then
        return nil
    end

    -- Look for the required data in the YAML config file, and throw errors if we can't find it
    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    -- local layerName = assert(config.layer_name, "Can't find 'layer_name' in YAML!")
    local mimeType = assert(config.mime_type, "Can't find MIME type in YAML!")
    if mimeType == 'image/x-j' then
        mimeType = 'image/jpeg'
    end
    local tmsName = assert(config.tilematrixset, "Can't find TileMatrixSet name in YAML!")
    local proj = assert(config.projection, "Can't find projection name in YAML!") 
    local static = true
    if config.static ~= nil then
        static = config.static
    end

    local defaultDate
    local periods
    local dateInfo
    if not static then
        dateInfo = dateList[layerId] or dateList[config.alias]
        if dateInfo then
            defaultDate = config.default_date or dateInfo["default"]
            -- Make sure Z is included for subdaily times
            if defaultDate then
                if string.find(defaultDate, "T") then
                    if not string.find(defaultDate, "Z") then
                        defaultDate = defaultDate .. "Z"
                    end
                end
            end
            periods = config.periods or dateInfo["periods"]
        else
            print("Can't find entry for layer " .. layerId .. " in date service list.")
        end
    end

    local layerElem = xml.elem("Layer")

    -- Maintain backward compatibility with layer titles that include unicode xB5
    if string.find(layerTitle, "\\xB5") then
        layerTitle = layerTitle:gsub("\\xB5", "µ")
    end
    layerElem:add_child(xml.new("ows:Title", {["xml:lang"]="en"}):text(stripDecodeBytesFormat(layerTitle)))

    -- Get the information we need from the TMS definitions and add bbox node
    local tmsDef = tmsDefs[proj][tmsName]
    if not tmsDef then
        print("Can't find TileMatrixSet (" .. tmsName .. ") for this layer in the TileMatrixSet definitions file." )
    end
    if targetEpsgCode ~= epsgCode then
        tmsName, tmsDef = getReprojectedTms(tmsDef, targetEpsgCode, tmsDefs)
        proj = targetEpsgCode
    end

    local bbox_84 = PROJECTIONS[proj]["bbox84"]
    local lowerCorner_84 = tostring(bbox_84["lowerCorner"][1]) .. " " .. tostring(bbox_84["lowerCorner"][2])
    local upperCorner_84 = tostring(bbox_84["upperCorner"][1]) .. " " .. tostring(bbox_84["upperCorner"][2])
    local bbox_elem_84 = xml.elem("ows:WGS84BoundingBox",
        {xml.elem("ows:LowerCorner"):text(lowerCorner_84), xml.elem("ows:UpperCorner"):text(upperCorner_84)})
    bbox_elem_84:set_attrib("crs","urn:ogc:def:crs:OGC:2:84")
    layerElem:add_child(bbox_elem_84)
    
    -- String manipulation to turn pos to neg and vice versa
    local negTopLeft11 = tmsDef[1]["topLeft"][1]:sub(1,1) == "-" and tmsDef[1]["topLeft"][1]:sub(2) or "-" .. tmsDef[1]["topLeft"][1] 
    local negTopLeft22 = tmsDef[2]["topLeft"][2]:sub(1,1) == "-" and tmsDef[2]["topLeft"][2]:sub(2) or "-" .. tmsDef[2]["topLeft"][2] 
    local upperCorner = negTopLeft11 .. " " .. tmsDef[2]["topLeft"][2]
    local lowerCorner = tmsDef[1]["topLeft"][1] .. " " .. negTopLeft22
    if(upperCorner ~= upperCorner_84 and lowerCorner ~= lowerCorner_84) then 
        local bbox_elem = xml.elem("ows:BoundingBox",
            {xml.elem("ows:LowerCorner"):text(lowerCorner), xml.elem("ows:UpperCorner"):text(upperCorner)})
        bbox_elem:set_attrib("crs", "urn:ogc:def:crs:EPSG::" .. split(":", targetEpsgCode)[2])
        layerElem:add_child(bbox_elem)
    end

    -- Add identifier node
    local id_elem = xml.new("ows:Identifier")
    id_elem:text(layerId)
    layerElem:add_child(id_elem)

    -- Build Metadata and add nodes
    if config.metadata then
        for _, metadata in pairs(config.metadata) do
            local metadataNode = xml.new("ows:Metadata")
            assert(type(metadata) == "table", "ERROR: metadata is not a table! It is probably a string. Layer config: " .. filename)
            for key, value in pairs(metadata) do
                metadataNode:set_attrib(key, string.gsub(value, "{base_uri_meta}", baseUriMeta or ""))
            end
            layerElem:add_child(metadataNode)
        end
    end

    -- Build the Style element
    local styleNode = xml.new("Style", {isDefault="true"})
    if config.style then
        styleNode:add_child(xml.new("ows:Title",{["xml:lang"]="en"}):text(config.style.title))
        styleNode:add_child(xml.new("ows:Identifier"):text(config.style.identifier))
        for _, urls in pairs(config.style.urls) do
            local legendNode = xml.new("LegendURL")
            for key, value in pairs(urls) do
                legendNode:set_attrib(key, string.gsub(value, "{base_uri_meta}", baseUriMeta or ""))
            end
            styleNode:add_child(legendNode)
        end
        layerElem:add_child(styleNode)
    else
        styleNode:add_child(xml.new("ows:Title",{["xml:lang"]="en"}):text("default"))
        styleNode:add_child(xml.new("ows:Identifier"):text("default"))
        layerElem:add_child(styleNode)
    end


    -- Build the <Dimension> element for time (if necessary)
    -- Note that we omit this if for some reason we don't have dates from the date service.
    if not static and dateInfo and periods and defaultDate and #periods > 0 then
        local dimensionNode = xml.elem("Dimension", {
            xml.new("ows:Identifier"):text("Time"),
            xml.new("ows:UOM"):text("ISO8601"),
            xml.new("Default"):text(defaultDate),
            xml.new("Current"):text("false")
        })
        for _, period in pairs(periods) do
            dimensionNode:add_child(xml.new("Value"):text(period))
        end
        layerElem:add_child(dimensionNode)
    end

    -- Build <TileMatrixSetLink>
    local tmsSetLinkNode = xml.elem("TileMatrixSetLink", xml.new("TileMatrixSet"):text(tmsName))
    if config.tilematrixset_limits_id and tmsLimitsDefs then
        -- Find Matrix set limits for id
        local id = config.tilematrixset_limits_id
        -- Build <TileMatrixSetLimits>
        local tmsLimitsNode = xml.elem("TileMatrixSetLimits")
        id = tmsLimitsDefs[id] and id or nil
        -- tmsLimitsNode:set_attrib("id", id)
        if id then
            for _, tmLimits in ipairs(tmsLimitsDefs[id]:get_elements_with_name("TileMatrixLimits")) do
                tmsLimitsNode:add_child(tmLimits)
            end
            tmsSetLinkNode:add_child(tmsLimitsNode)
        end
    end
    layerElem:add_child(tmsSetLinkNode)
    -- Build <Format>
    layerElem:add_child(xml.new("Format"):text(mimeType))

    -- Build the ResourceURL elements
    local timeString = not static and "/{Time}" or ""
    if string.sub(baseUriGC, -1) ~= "/" then
        baseUriGC = baseUriGC .. "/" 
    end
    
    -- tiles
    local template_static = baseUriGC .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    local template_default = baseUriGC .. layerId .. "/" .. "default" .. "/default" .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    if not static then
        local template_time = baseUriGC .. layerId .. "/" .. "default" .. timeString .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
        layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_time}))
    end
    layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_static}))
    layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_default}))
    
    -- describedomains
    if not static then
        local template_domains = baseUriGC .. "1.0.0" .. "/" .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/{BBOX}/{TimeStart}.xml"
        local template_domains_bbox_all = baseUriGC .. "1.0.0" .. "/" .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/all/{TimeStart}.xml"
        local template_domains_time_end = baseUriGC .. "1.0.0" .. "/" .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/all/--{TimeEnd}.xml"
        local template_domains_time_start_end = baseUriGC .. "1.0.0" .. "/" .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/all/{TimeStart}--{TimeEnd}.xml"
        local template_domains_time_all = baseUriGC .. "1.0.0" .. "/" .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/{BBOX}/all.xml"
        layerElem:add_child(xml.new("ResourceURL", {format="text/xml", resourceType="Domains", template=template_domains}))
        layerElem:add_child(xml.new("ResourceURL", {format="text/xml", resourceType="Domains", template=template_domains_bbox_all}))
        layerElem:add_child(xml.new("ResourceURL", {format="text/xml", resourceType="Domains", template=template_domains_time_end}))
        layerElem:add_child(xml.new("ResourceURL", {format="text/xml", resourceType="Domains", template=template_domains_time_start_end}))
        layerElem:add_child(xml.new("ResourceURL", {format="text/xml", resourceType="Domains", template=template_domains_time_all}))
    end
    return layerElem
end

local function getAllGCLayerNodes(endpointConfig, tmsXml, tmsLimitsXml, epsgCode, targetEpsgCode, twms)
    local tmsDefs = getTmsDefs(tmsXml)
    local periods_limit = -100 -- most recent 100 periods
    local dateList = getDateList(endpointConfig, nil, nil, nil, periods_limit)
    local tmsLimitsDefs
    if tmsLimitsXml then 
        tmsLimitsDefs = getTmsLimitsDefs(tmsLimitsXml)
    end
    local layerConfigSource = endpointConfig["layer_config_source"]

    local buildFunc = twms and makeTWMSGCLayer or makeGCLayer
        if not twms and not endpointConfig["base_uri_gc"] then
        print("Error: no 'base_uri_gc' configured")
    end

    local nodeList = {}

    local fileAttrs = lfs.attributes(layerConfigSource)
    if not fileAttrs then
        print("Can't open layer config location: " .. layerConfigSource)
        return
    end

    if fileAttrs["mode"] == "file" then
        node = buildFunc(layerConfigSource, tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode, endpointConfig["base_uri_gc"], endpointConfig["base_uri_meta"])
        if node ~= nil then
            nodeList[1] = node
        end
    end
    if fileAttrs["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and
                string.sub(file, 0, 1) ~= "." then
                node = buildFunc(layerConfigSource .. "/" .. file,
                 tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode, endpointConfig["base_uri_gc"], endpointConfig["base_uri_meta"])
                if node ~= nil then
                    nodeList[#nodeList + 1] = node
                end
            end
        end
    end
    local function sortLayers(a,b)
        return a[1][1] < b[1][1]
    end
    table.sort(nodeList, sortLayers)
    return nodeList
end


local function makeGC(endpointConfig)
    -- Load TMS defs
    local tmsFile = assert(io.open(endpointConfig["tms_defs_file"], "r")
        , "Can't open tile matrixsets definition file at: " .. endpointConfig["tms_defs_file"])
    local tmsXml = xml.parse(tmsFile:read("*all"))
    tmsFile:close()
    
    local tms_limits_defs_file = endpointConfig["tms_limits_defs_file"]
    local tmsLimitsXml
    if tms_limits_defs_file and tms_limits_defs_file ~= "nil" then
        local tmsLimitsFile = assert(io.open(endpointConfig["tms_limits_defs_file"], "r")
            , "Can't open tile matrixsetslimits definition file at: " .. endpointConfig["tms_limits_defs_file"])
        tmsLimitsXml = xml.parse(tmsLimitsFile:read("*all"))
        tmsLimitsFile:close()
    end

    local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
    if string.match(epsgCode:lower(), "^%d") then
        epsgCode = "EPSG:" .. epsgCode
    end

    local targetEpsgCode = endpointConfig["reproject"] and endpointConfig["reproject"]["target_epsg_code"] or endpointConfig["target_epsg_code"]
    if targetEpsgCode then
        if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
            targetEpsgCode = "EPSG:" .. targetEpsgCode
        end
    else
        targetEpsgCode = epsgCode
    end

    -- Parse header
    local headerFile = assert(io.open(endpointConfig["gc_header_file"], "r"),
        "Can't open GC header file at:" .. endpointConfig["gc_header_file"])
    local dom = xml.parse(headerFile:read("*all"))
    headerFile:close()

    -- Build contents section
    local contentsElem = xml.elem("Contents")
    local layers = getAllGCLayerNodes(endpointConfig, tmsXml, tmsLimitsXml, epsgCode, targetEpsgCode)

    if not layers then
        return sendResponse(400, "No layers found!")
    end
   
    for _, layer in ipairs(layers) do
        contentsElem:add_child(layer)
    end

    for _, proj in ipairs(tmsXml:get_elements_with_name("Projection")) do
        if proj:get_attribs()["id"] == targetEpsgCode or not targetEpsgCode and epsgCode then
            for _, tms in ipairs(proj:get_elements_with_name("TileMatrixSet")) do
                contentsElem:add_child(tms)
            end
        end
    end

    -- Add contents section
    dom:add_direct_child(contentsElem)

    -- Move ServiceMetadataURL below contents
    local serviceMetadataURL = dom:get_elements_with_name("ServiceMetadataURL")[1]
    local function removeServiceMetadataURL(x)
      if (x == serviceMetadataURL) then
        return nil
      end
      return x
    end
    dom:maptags(removeServiceMetadataURL)
    dom:add_direct_child(serviceMetadataURL)
    return xml.tostring(dom)
    
end


local function makeTWMSGC(endpointConfig)
    -- Load TMS defs
    local tmsFile = assert(io.open(endpointConfig["tms_defs_file"], "r")
        , "Can't open tile matrixsets definition file at: " .. endpointConfig["tms_defs_file"])
    local tmsXml = xml.parse(tmsFile:read("*all"))
    tmsFile:close()

    local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
    if string.match(epsgCode:lower(), "^%d") then
        epsgCode = "EPSG:" .. epsgCode
    end

    local targetEpsgCode = endpointConfig["reproject"] and endpointConfig["reproject"]["target_epsg_code"] or endpointConfig["target_epsg_code"]
    if targetEpsgCode then
        if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
            targetEpsgCode = "EPSG:" .. targetEpsgCode
        end
    else
        targetEpsgCode = epsgCode
    end

    -- Parse header
    local headerFile = assert(io.open(endpointConfig["twms_gc_header_file"], "r"),
        "Can't open TWMS GC header file at:" .. endpointConfig["twms_gc_header_file"])
    local content = {}
    local doctype = ""
    if headerFile then
      for line in headerFile:lines() do
          if string.match(line, "DOCTYPE") then
            doctype = line -- parser doesn't like DOCTYPE, so we take it out and prepend again later
          else
            content[#content+1] = line
          end
      end
    end
    headerFile:close()
    local dom = xml.parse(table.concat(content,"\n"))

    -- Add layers to <Capability> section
    local capabilityElems = dom:get_elements_with_name("Capability")
    if not capabilityElems then
        return "{\"error\": \"Can't find <Capability> element in header TWMS GetCapabilities header file.\"}"
    end
    local capabilityElem = capabilityElems[1]

    local baseLayerElem = capabilityElem:get_elements_with_name("Layer")[1]
    local layers = getAllGCLayerNodes(endpointConfig, tmsXml, tmsLimitsXml, epsgCode, targetEpsgCode, true)
    
    if not layers then
        return sendResponse(400, "No layers found!")
    end
    
    for _, layer in ipairs(layers) do
        baseLayerElem:add_direct_child(layer)
    end

    return doctype .. xml.tostring(dom)
end

local function makeDD(endpointConfig, query_string)
    local xml_header = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'
    local layer = get_query_param("layer", query_string)
    local errorDom
    if not layer then 
        errorDom = makeExceptionReport("MissingParameterValue", "Missing LAYER parameter", "LAYER", errorDom)
    end
    
    local domains = get_query_param("domains", query_string)
    if not domains then
        domains = "bbox,time"
    end

    local dom = xml.new("Domains", { ["xmlns:ows"] = "http://www.opengis.net/ows/1.1" } )

    -- get bbox
    if domains:find("bbox") then
        local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
        if string.match(epsgCode:lower(), "^%d") then
            epsgCode = "EPSG:" .. epsgCode
        end

        local targetEpsgCode = endpointConfig["reproject"] and endpointConfig["reproject"]["target_epsg_code"] or endpointConfig["target_epsg_code"]
        if targetEpsgCode then
            if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
                targetEpsgCode = "EPSG:" .. targetEpsgCode
            end
        else
            targetEpsgCode = epsgCode
        end
        
        local projection = PROJECTIONS[targetEpsgCode or epsgCode]
        local bbox = projection["bbox"] or projection["bbox84"]

        local spaceDomainNode = xml.elem("SpaceDomain", {
            xml.new("BoundingBox",
                { crs=bbox["crs"],
                miny=bbox["lowerCorner"][2],
                minx=bbox["lowerCorner"][1],
                maxx=bbox["upperCorner"][1],
                maxy=bbox["upperCorner"][2]})
        })
        dom:add_direct_child(spaceDomainNode)
    end

    -- get periods
    if domains:find("time") then
        local time_query = get_query_param("time", query_string)
        local dateList = nil
        local periods_start
        local periods_end
        if time_query and time_query:lower() ~= "all" then
            local times = split('/', time_query)
            if #times == 1 then
                -- When there's just one time specified, use it as a periods end bound if the time query starts with a '/'.
                -- Otherwise, assume it to be a periods start bound.
                if time_query:sub(1, 1) == '/' then
                    periods_end = times[1]
                else
                    periods_start = times[1]
                end
            elseif #times > 1 then
                periods_start = times[1]
                periods_end = times[2]
            end
            if (periods_start and not string.match(periods_start, date_template) and not string.match(periods_start, datetime_template)) or
                (periods_end and not string.match(periods_end, date_template) and not string.match(periods_end, datetime_template)) then
                errorDom = makeExceptionReport("InvalidParameterValue",
                        "Invalid TIME parameter: time range must follow format of START_DATE/END_DATE, or be 'ALL'. START_DATE and END_DATE must have format of YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ",
                        "TIME", errorDom)
            end
        end
        if errorDom then
            return xml_header .. xml.tostring(errorDom)
        end
        dateList = getDateList(endpointConfig, layer, periods_start, periods_end, nil)
        local periodsList = dateList and dateList[layer] and dateList[layer]["periods"] or {}
        local size = dateList and dateList[layer] and dateList[layer]["periods_in_range"] or "0"
        local timeDomainNode = xml.elem("DimensionDomain", {
            xml.elem("ows:Identifier", "time"),
            xml.elem("Domain", join(periodsList, ",")),
            xml.elem("Size", "" .. size)
        })
        dom:add_direct_child(timeDomainNode)
    elseif errorDom then
        return xml_header .. xml.tostring(errorDom)
    end
    return xml_header .. xml.tostring(dom)
end

local function generateFromEndpointConfig()
    -- Load endpoint config
    assert(arg[1], "Must specifiy an endpoint config file!")
    local endpointConfigFile = assert(io.open(arg[1], "r"), "Can't open endpoint config file: " .. arg[1])
    local status, endpointConfig = pcall(yaml.eval, endpointConfigFile:read("*all"))
    if not status then
        error("Failed to parse endpoint config " .. arg[1] .. ": " .. endpointConfig)
    end
    endpointConfigFile:close()
    if arg[2] == "--make_gts" then
        return makeGTS(endpointConfig)
    end
    return makeGC(endpointConfig)
end

function onearth_gc_service.handler(endpointConfig)
    return function(query_string, _, _)
        local req = get_query_param("request", query_string)
        if not req then
            return sendResponse(200, 'No REQUEST parameter specified')
        end
        req = req:lower()
        local response
        if req == "wmtsgetcapabilities" then
            response = makeGC(endpointConfig)
        elseif req == "twmsgetcapabilities" then
            response = makeTWMSGC(endpointConfig)
        elseif req == "gettileservice" then
            response = makeGTS(endpointConfig)
        elseif req == "describedomains" then
            response = makeDD(endpointConfig, query_string)
        else
            response = "Unrecognized REQUEST parameter: '" .. req .. "'. Request must be one of: WMTSGetCapabilities, TWMSGetCapabilities, GetTileService, DescribeDomains"
        end
        return sendResponse(200, response)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_gc_service
else
    print(generateFromEndpointConfig())
end