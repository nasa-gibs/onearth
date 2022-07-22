local onearth_gc_service = {}

local lfs = require "lfs"
local lyaml = require "lyaml"
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

local function getDateList(endpointConfig)
    local dateServiceUri = endpointConfig["time_service_uri"]
    local dateServiceKeys = endpointConfig["time_service_keys"]
    if dateServiceKeys then
        local formattedKeys = {}
        for idx, value in ipairs(dateServiceKeys) do
            formattedKeys[#formattedKeys + 1] = "key" .. tostring(idx) .. "=" .. value
        end
        local keyString = join(formattedKeys, "&")
        if string.sub(dateServiceUri, -1) ~= "?" then
            dateServiceUri = dateServiceUri .. "?"
        end
        dateServiceUri = dateServiceUri .. keyString
    end
    local headers, stream = assert(request.new_from_uri(dateServiceUri):go(300))
    local body = assert(stream:get_body_as_string())
    if headers:get ":status" ~= "200" then
        print("Error contacting date service: " .. body)
        return nil
    end
    local dateList = JSON:decode(body)
    return dateList or {}
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

-- GetTileService functions

local function makeTiledGroupFromConfig(filename, tmsDefs, epsgCode, targetEpsgCode)
    -- Load and parse the YAML config file
    local configFile = assert(io.open(filename, "r"))
    local config = lyaml.load(configFile:read("*all"))
    configFile:close()

    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerName = assert(config.layer_name, "Can't find 'layer_name' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    local abstract = assert(config.abstract, "Can't find 'abstract' in YAML!")
    local projInfo = assert(PROJECTIONS[targetEpsgCode or epsgCode], "Can't find projection " .. epsgCode)
    local mimeType = assert(config.mime_type, "Can't find MIME type in YAML!")
    local bands
    if mimeType == "application/vnd.mapbox-vector-tile" then
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

    local matrices = tmsDefs[epsgCode][tmsName]
    if targetEpsgCode and targetEpsgCode ~= epsgCode then
        _, matrices = getReprojectedTms(matrices, targetEpsgCode, tmsDefs)
    end
    table.sort(matrices, function (a, b)
        return tonumber(a["scaleDenominator"]) < tonumber(b["scaleDenominator"])
    end)
    targetEpsgCode = targetEpsgCode or epsgCode

    for _, matrix in ipairs(matrices) do
        local widthInPx = math.ceil(2 * math.pi * EARTH_RADIUS / (matrix["scaleDenominator"] * 0.28E-3))
        local heightInPx = targetEpsgCode == "EPSG:4326" and widthInPx / 2 or widthInPx
        local widthRatio = widthInPx / (matrix["tileWidth"] * matrix["matrixWidth"])
        local heightRatio = heightInPx / (matrix["tileHeight"] * matrix["matrixHeight"])
        local resx = math.ceil((bbox["upperCorner"][1] - bbox["lowerCorner"][1]) / (matrix["matrixWidth"] * widthRatio))
        local resy = math.ceil((bbox["upperCorner"][2] - bbox["lowerCorner"][2]) / (matrix["matrixHeight"] * heightRatio))
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
            local time = hasTime and "${time}" or ""
            return string.gsub(template, "${layer}", layerId)
                :gsub("${epsg_code}", targetEpsgCode)
                :gsub("${mime_type}", mimeType)
                :gsub("${time}", time)
                :gsub("${width}", matrix["tileWidth"])
                :gsub("${height}", matrix["tileHeight"])
                :gsub("${bbox}", join(bboxOut, ","))
            end
        local outString = static and make_uri(false) or make_uri(true) .. "\n" .. make_uri(false)
        outString = "<![CDATA[" .. outString .. "]]>"
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
        nodeList[1] = makeTiledGroupFromConfig(layerConfigSource, tmsDefs, epsgCode, targetEpsgCode)
    end

    if fileAttrs["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and
                string.sub(file, 0, 1) ~= "." then
                nodeList[#nodeList + 1] = makeTiledGroupFromConfig(layerConfigSource .. "/" .. file,
                 tmsDefs, epsgCode, targetEpsgCode)
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
    local config = lyaml.load(configFile:read("*all"))
    configFile:close()

    -- Look for the required data in the YAML config file, and throw errors if we can't find it
    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    local layerAbstract = assert(config.abstract, "Can't find 'abstract' in YAML!")
    -- local tmsName = assert(config.tilematrixset, "Can't find TileMatrixSet name in YAML!")

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

    local bbox = PROJECTIONS[targetEpsgCode or epsgCode]["bbox"] or PROJECTIONS[targetEpsgCode or epsgCode]["bbox84"]

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
    local config = lyaml.load(configFile:read("*all"))
    configFile:close()

    -- Look for the required data in the YAML config file, and throw errors if we can't find it
    local layerId = assert(config.layer_id, "Can't find 'layer_id' in YAML!")
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    -- local layerName = assert(config.layer_name, "Can't find 'layer_name' in YAML!")
    local mimeType = assert(config.mime_type, "Can't find MIME type in YAML!")
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
            periods = config.periods or dateInfo["periods"]
        else
            print("Can't find entry for layer " .. layerId .. " in date service list.")
        end
    end

    local layerElem = xml.elem("Layer")

    layerElem:add_child(xml.new("ows:Title", {["xml:lang"]="en"}):text(stripDecodeBytesFormat(layerTitle)))

    -- Get the information we need from the TMS definitions and add bbox node
    local tmsDef = tmsDefs[epsgCode][tmsName]
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
    if not static and dateInfo then
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

    -- Build the ResourceURL element
    local timeString = not static and "/{Time}" or ""
    if string.sub(baseUriGC, -1) ~= "/" then
        baseUriGC = baseUriGC .. "/" 
    end
    local template_static = baseUriGC .. layerId .. "/" .. "default" .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    local template_default = baseUriGC .. layerId .. "/" .. "default" .. "/default" .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    local template_time = baseUriGC .. layerId .. "/" .. "default" .. timeString .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    if not static then
        layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_time}))
    end
    layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_static}))
    layerElem:add_child(xml.new("ResourceURL", {format=mimeType, resourceType="tile", template=template_default}))

    return layerElem
end

local function getAllGCLayerNodes(endpointConfig, tmsXml, tmsLimitsXml, epsgCode, targetEpsgCode, twms)
    local tmsDefs = getTmsDefs(tmsXml)
    local dateList = getDateList(endpointConfig)
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
        nodeList[1] = buildFunc(layerConfigSource, tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode, endpointConfig["base_uri_gc"], endpointConfig["base_uri_meta"])
    end
    if fileAttrs["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and
                string.sub(file, 0, 1) ~= "." then
                nodeList[#nodeList + 1] = buildFunc(layerConfigSource .. "/" .. file,
                 tmsDefs, tmsLimitsDefs, dateList, epsgCode, targetEpsgCode, endpointConfig["base_uri_gc"], endpointConfig["base_uri_meta"])
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

local function generateFromEndpointConfig()
    -- Load endpoint config
    assert(arg[1], "Must specifiy an endpoint config file!")
    local endpointConfigFile = assert(io.open(arg[1], "r"), "Can't open endpoint config file: " .. arg[1])
    local endpointConfig = lyaml.load(endpointConfigFile:read("*all"))
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
        else
            response = "Unrecognized REQUEST parameter: '" .. req .. "'. Request must be one of: WMTSGetCapabilities, TWMSGetCapabilities, GetTileService"
        end
        return sendResponse(200, response)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_gc_service
else
    print(generateFromEndpointConfig())
end