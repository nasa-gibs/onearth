local onearth_gc_service = {}

local xmlser = require "xml-ser"
local xmlserde = require "xml-serde"
local lfs = require "lfs"
local lyaml = require "lyaml"
local request = require "http.request"
local JSON = require "JSON"
local inspect = require "inspect"

-- Reference Constants
local EARTH_RADIUS = 6378137.0
local PROJECTIONS = {
    ["EPSG:3031"] = {
        wkt='PROJCS["WGS 84 / Antarctic Polar Stereographic",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",-71],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3031"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, -90}, upperCorner={180, -38.941373}},
        bbox={crs="urn:ogc:def:crs:EPSG::3031", lowerCorner={-4194304, -4194304}, upperCorner={194304, 4194304}}
    },
    ["EPSG:3413"] = {
        wkt='PROJCS["WGS 84 / NSIDC Sea Ice Polar Stereographic North",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Polar_Stereographic"],PARAMETER["latitude_of_origin",70],PARAMETER["central_meridian",-45],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],AUTHORITY["EPSG","3413"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, 8.807151}, upperCorner={180, 90}},
        bbox={crs="urn:ogc:def:crs:EPSG::3413", lowerCorner={-4194304, -4194304}, upperCorner={4194304, 4194304}}
    },
    ["EPSG:3857"] = {
        wkt='PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"],AUTHORITY["EPSG","3857"]]',
        bbox84={crs="urn:ogc:def:crs:OGC:2:84", lowerCorner={-180, -85}, upperCorner={180, 85}},
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

local function sendResponse(code, msg_string)
    return msg_string,
    {
        ["Content-Type"] = "text/xml"
    },
    code
end

local function getXmlChildrenByName(rootElement, elementName)
    for _, value in pairs(rootElement["kids"]) do
        if value["name"] == elementName then
            return value["text"]
        end
    end
end

local function getXmlNodesByName(rootElement, elementName)
    local nodes = {}
    for _, node in pairs(rootElement["kids"]) do
        if node["name"] == elementName then
            nodes[#nodes + 1] = node
        end
    end
    return nodes
end

local function getExtensionFromMimeType(mimeType) 
    if mimeType == "image/jpeg" then
        return ".jpeg"
    end
end

local function getDateList(dateServiceUri)
    local headers, stream = assert(request.new_from_uri(dateServiceUri):go(5))
    local body = assert(stream:get_body_as_string())
    if headers:get ":status" ~= "200" then
        error(body)
    end
    return JSON:decode(body)
end

local function getTmsDefs(tmsXml)
    local tmsDefs = {}
    for _, proj in ipairs(getXmlNodesByName(tmsXml, "Projection")) do
        local tileMatrixSets = {}
        for _, tms in ipairs(getXmlNodesByName(proj, "TileMatrixSet")) do
            local tmsName = getXmlChildrenByName(tms, "Identifier")
            local matrices = {}
            for _, matrix in pairs(tms["kids"]) do
                if matrix["name"] == "TileMatrix" then
                    local identifier = getXmlChildrenByName(matrix, "Identifier")
                    local topLeft = split(" ", getXmlChildrenByName(matrix, "TopLeftCorner"))
                    matrices[tonumber(identifier) + 1] = {
                        topLeft={tonumber(topLeft[1]), tonumber(topLeft[2])},
                        scaleDenominator = getXmlChildrenByName(matrix, "ScaleDenominator"),
                        matrixWidth = getXmlChildrenByName(matrix, "MatrixWidth"),
                        matrixHeight = getXmlChildrenByName(matrix, "MatrixHeight"),
                        tileWidth = getXmlChildrenByName(matrix, "TileWidth"),
                        tileHeight = getXmlChildrenByName(matrix, "TileHeight"),
                    }
                end
            end
        tileMatrixSets[tmsName] = matrices
        end
    tmsDefs[proj["attr"]["id"]] = tileMatrixSets
    end
    return tmsDefs
end

local function getReprojectedTms(sourceTms, targetEpsgCode, tmsDefs)
    local function sortTms(a,b)
        return tonumber(a["scaleDenominator"]) > tonumber(b["scaleDenominator"])
    end
    table.sort(sourceTms, sortTms)
    local sourceScaleDenom = sourceTms[1]["scaleDenominator"]
    local targetTms
    local targetTmsName
    for name, tms in pairs(tmsDefs[targetEpsgCode]) do
        table.sort(tms, sortTms)
        if not targetTms or tms[1]["scaleDenominator"] > sourceScaleDenom and sourceScaleDenom < targetTms[1]["scaleDenominator"] then
            targetTmsName = name
            targetTms = tms
        end
    end
    return targetTmsName, targetTms
end


-- Functions for building configuration files (used by config tools, not service)

local apacheConfigHeaderTemplate = [[
<IfModule !ahtse_lua>
    LoadModule ahtse_lua_module modules/mod_ahtse_lua.so
</IfModule>

<Directory ${dir}>
        AHTSE_lua_RegExp ${regexp}
        AHTSE_lua_Script ${script_loc}
        AHTSE_lua_Redirect On
        AHTSE_lua_KeepAlive On
</Directory>
]]

local luaConfigTemplate = [[
local gc = require "gc"
handler = gc.handler(${config_loc}, ${tms_loc}, ${gc_header_loc}, ${date_service_uri}, ${gettileservicemode} )
]]

function onearth_gc_service.createConfiguration(endpointConfigFilename)
    local endpointConfigFile = assert(io.open(endpointConfigFilename, "r"), "Can't open endpoint config file: " .. endpointConfigFilename)
    local endpointConfig = lyaml.load(endpointConfigFile:read("*all"))
    endpointConfigFile:close()

    local tmsDefsFilename = endpointConfig["tms_defs_file"]
    local headerFilename = endpointConfig["gc_header_file"]
    local layerConfigSource = endpointConfig["layer_config_source"]
    local dateServiceUri = endpointConfig["date_service_uri"]

    local apacheConfigLocation = endpointConfig["apache_config_location"]
    if not apacheConfigLocation then
        print("No Apache config location specified. Using '/etc/httpd/conf.d/get_capabilities.conf'")
        apacheConfigLocation = "/etc/httpd/conf.d/get_capabilities.conf"
    end
    local endpoint = endpointConfig["endpoint"]
    if not endpoint then
        print("No endpoint specified. Using /gc")
        endpoint = "/gc"
    end
    local regexp = split("/", endpoint)[#split("/", endpoint)]
    local luaConfigBaseLocation = endpointConfig["endpoint_config_base_location"]
    if not luaConfigBaseLocation then
        print("No Lua config location specified. Using '/var/www/html" .. endpoint .. ";")
        luaConfigBaseLocation = "/var/www/html"
    end
    local luaConfigLocation = luaConfigBaseLocation .. endpoint .. "/" .. "get_capabilities.lua"

    -- Make and write Apache config
    local apacheConfig = apacheConfigHeaderTemplate:gsub("${dir}", endpoint)
        :gsub("${regexp}", regexp)
        :gsub("${script_loc}", luaConfigLocation)

    local apacheConfigFile = assert(io.open(apacheConfigLocation, "w+"), "Can't open Apache config file " 
        .. apacheConfigLocation .. " for writing.")
    apacheConfigFile:write(apacheConfig)
    apacheConfigFile:close()

    -- Make and write Lua config
    local luaConfig = luaConfigTemplate:gsub("${config_loc}", layerConfigSource)
        :gsub("${tms_loc}", tmsDefsFilename)
        :gsub("${gc_header_loc}", headerFilename)
        :gsub("${date_service_uri}", dateServiceUri)
    lfs.mkdir(luaConfigBaseLocation .. endpoint)
    local luaConfigFile = assert(io.open(luaConfigLocation, "w+", "Can't open Lua config file " 
        .. luaConfigLocation .. " for writing."))
    luaConfigFile:write(luaConfig)
    luaConfigFile:close()

    print("Configuration complete!")
    print("Apache config has been saved to " .. apacheConfigLocation)
    print("GC service config has been saved to " .. luaConfigLocation)
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
    local bands = mimeType == "image/png" and "4" or "3"
    local static = true
    if config.static ~= nil then
        static = config.static
    end
    local bbox = projInfo["bbox"] or projInfo["bbox84"]
    local tmsName = assert(config.tilematrixset, "Can't find TileMatrixSet name in YAML!")

    local tiledGroupNode = {name="TiledGroup", kids={
        {name="Name", text=layerName},
        {name="Title", attr={["xml:lang"]="en"}, text=layerTitle},
        {name="Abstract", attr={["xml:lang"]="en"}, text=abstract},
        {name="Projection", text=projInfo["wkt"]},
        {name="Pad", text="0"},
        {name="Bands", text=bands},
        {name="LatLonBoundingBox",attr={
            minx=bbox["lowerCorner"][1],
            miny=bbox["lowerCorner"][2],
            maxx=bbox["upperCorner"][1],
            maxy=bbox["upperCorner"][2]
        }},
        {name="Key", text="${time}"}}
    }

    local matrices = tmsDefs[epsgCode][tmsName]
    if targetEpsgCode then
        tmsName, matrices = getReprojectedTms(matrices, targetEpsgCode, tmsDefs)
    end
    table.sort(matrices, function (a, b)
        return tonumber(a["scaleDenominator"]) < tonumber(b["scaleDenominator"])
    end)
    for _, matrix in ipairs(matrices) do
        local widthInPx = math.ceil(2 * math.pi * EARTH_RADIUS / (matrix["scaleDenominator"] * 0.28E-3))
        local heightInPx = epsgCode == "EPSG:4326" and widthInPx / 2 or widthInPx
        local widthRatio = widthInPx / (matrix["tileWidth"] * matrix["matrixWidth"])
        local heightRatio = heightInPx / (matrix["tileHeight"] * matrix["matrixHeight"])
        local resx = math.ceil((bbox["upperCorner"][1] - bbox["lowerCorner"][1]) / (matrix["matrixWidth"] * widthRatio))
        local resy = math.ceil((bbox["upperCorner"][2] - bbox["lowerCorner"][2]) / (matrix["matrixHeight"] * heightRatio))
        local xmax = matrix["topLeft"][1] + resx
        local ymax = matrix["topLeft"][2] - resy
        local template = "request=GetMap&layers=${layer}&srs=${epsg_code}&format=${mime_type}&styles=${time}&width=${width}&height=${height}&bbox=${bbox}"
        local make_uri = function(hasTime)
            local time = hasTime and "${time}" or ""
            return string.gsub(template, "${layer}", layerId)
                :gsub("${epsg_code}", epsgCode)
                :gsub("${mime_type}", mimeType)
                :gsub("${time}", time)
                :gsub("${width}", matrix["tileWidth"])
                :gsub("${height}", matrix["tileHeight"])
                :gsub("${bbox}", join({matrix["topLeft"][1], ymax, xmax, matrix["topLeft"][2]}, ","))
            end
        local outString = static and make_uri(false) or make_uri(true) .. "\n" .. make_uri(false)
        outString = "<![CDATA[" .. outString .. "]]>"
        tiledGroupNode["kids"][#tiledGroupNode["kids"] + 1] = {name="TilePattern", text=outString}
    end
    return tiledGroupNode
end

local function getAllGTSTiledGroups(endpointConfig, epsgCode, targetEpsgCode)
    -- Load TMS defs
    local tmsFile = assert(io.open(endpointConfig["tms_defs_file"], "r")
        , "Can't open tile matrixsets definition file at: " .. endpointConfig["tms_defs_file"])
    local tmsXml = xmlserde.deserialize(tmsFile:read("*all"))
    local tmsDefs = getTmsDefs(tmsXml)
    tmsFile:close()

    local layerConfigSource = endpointConfig["layer_config_source"]

    local nodeList = {}
    local fileAttrs = assert(lfs.attributes(layerConfigSource), "Can't open layer config location: " .. layerConfigSource)
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
    local headerFile = assert(io.open(endpointConfig["gts_header_file"], "r"),
        "Can't open GTS header file at:" .. endpointConfig["gts_header_file"])
    local mainXml = xmlserde.deserialize(headerFile:read("*all"))
    headerFile:close()

    -- Load projection (add "EPSG:" part if omitted)
    local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
    if string.match(epsgCode:lower(), "^%d") then
        epsgCode = "EPSG:" .. epsgCode
    end

    local targetEpsgCode = endpointConfig["target_epsg_code"]
    if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
        targetEpsgCode = "EPSG:" .. targetEpsgCode
    end

    local projection = PROJECTIONS[targetEpsgCode or epsgCode]
    local bbox = projection["bbox"] or projection["bbox84"]

    local serviceNode = getXmlNodesByName(mainXml, "Service")[1]
    local onlineResourceNode = getXmlNodesByName(serviceNode, "OnlineResource")[1]

    -- Build <TiledPatterns> section
    local tiledPatternsNode = {name="TiledPatterns", kids={}}
    tiledPatternsNode["kids"][#tiledPatternsNode["kids"] + 1] = {name="OnlineResource", text=onlineResourceNode["attr"]["href"] .. "twms?"}
    tiledPatternsNode["kids"][#tiledPatternsNode["kids"] + 1] = {name="LatLonBoundingBox",attr={
            minx=bbox["lowerCorner"][1],
            miny=bbox["lowerCorner"][2],
            maxx=bbox["upperCorner"][1],
            maxy=bbox["upperCorner"][2]
        }
    }

    for _, tiledGroup in pairs(getAllGTSTiledGroups(endpointConfig, epsgCode, targetEpsgCode)) do
        tiledPatternsNode["kids"][#tiledPatternsNode["kids"] + 1] = tiledGroup
    end

    -- Add contents to the rest of the XML
    mainXml["kids"][#mainXml["kids"] + 1] = tiledPatternsNode
    return xmlser.serialize(mainXml)
end


-- GetCapabilities functions

local function makeGCLayer(filename, tmsDefs, dateList, baseUriGC, epsgCode, targetEpsgCode)
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
    local static = true
    static = config.static or static

    local defaultDate
    local periods
    if not static then
        defaultDate = config.default_date or dateList[layerId]["default"]
        periods = config.periods or dateList[layerId]["periods"]
    end

    local layerContents = {}
    layerContents[#layerContents + 1] = {name= "ows:Title", attr={["xml:lang"]="en"}, text=layerTitle}

    -- Get the information we need from the TMS definitions and add bbox node
    local tmsDef = tmsDefs[epsgCode][tmsName]
    if targetEpsgCode then
        tmsName, tmsDef = getReprojectedTms(tmsDef, targetEpsgCode, tmsDefs)
    end

    local upperCorner = tostring(tmsDef[1]["topLeft"][1] * -1) .. " " .. tostring(tmsDef[2]["topLeft"][2])
    local lowerCorner = tostring(tmsDef[1]["topLeft"][1]) .. " " .. tostring(tmsDef[2]["topLeft"][2] * -1)

    layerContents[#layerContents + 1] = {name="ows:WGS84BoundingBox", attr={crs="urn:ogc:def:crs:OGC:2:84"}, kids={
        {name="ows:LowerCorner", text=lowerCorner}, {name="ows:UpperCorner", text=upperCorner}
    }}

    layerContents[#layerContents + 1] = {name="ows:BoundingBox", attr={crs="urn:ogc:def:crs:EPSG::3413"}, kids={
     {name="ows:LowerCorner", text=lowerCorner}, {name="ows:UpperCorner", text=upperCorner}
    }}

    -- Add identifier node
    layerContents[#layerContents + 1] = {name="ows:Identifier", text=layerId}

    -- Build Metadata and add nodes
    for _, metadata in pairs(config.metadata) do
        local metadataNode = {name="ows:Metadata", attr={}}
        for attr, value in pairs(metadata) do
            metadataNode["attr"][attr] = value
        end
        layerContents[#layerContents + 1] = metadataNode
    end

    -- Build the Style element
    local styleNode = {name="Style", attr={isDefault="true"}, kids={
        {name="ows:Title", attr={["xml:lang"]="en"}, text="default"},
        {name="ows:Identifier", text="default"}
    }}
    layerContents[#layerContents + 1] = styleNode

    layerContents[#layerContents + 1] = {name="Format", text=mimeType}

    -- Build the <Dimension> element for time (if necessary)
    if not static then
        local dimensionNode = {name="Dimension", kids={
            {name="ows:Identifier", text="time"},
            {name="ows:UOM", text="ISO8601"},
            {name="Default", text=defaultDate},
            {name="Current", text="false"},
        }}
        for _, period in pairs(periods) do
            dimensionNode["kids"][#dimensionNode["kids"] + 1] = {name="Value", text=period}
        end
        layerContents[#layerContents + 1] = dimensionNode
    end

    -- Build <TileMatrixSetLink>
    layerContents[#layerContents + 1] = {name="TileMatrixSetLink", kids={{name="TileMatrixSet", text=tmsName}}}

    -- Build the ResourceURL element
    local timeString = not static and "/{Time}" or ""
    local template = baseUriGC .. layerId .. "/" .. "default" .. timeString .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    layerContents[#layerContents + 1] = {name="ResourceURL", attr={format=mimeType, resourceType="tile", template=template}}

    return { name="Layer", kids=layerContents}
end

local function getAllGCLayerNodes(endpointConfig, tmsXml, epsgCode, targetEpsgCode)
    local tmsDefs = getTmsDefs(tmsXml)
    local dateList = getDateList(endpointConfig["date_service_uri"])
    local layerConfigSource = endpointConfig["layer_config_source"]

    local nodeList = {}
    local fileAttrs = assert(lfs.attributes(layerConfigSource), "Can't open layer config location: " .. layerConfigSource)
    if fileAttrs["mode"] == "file" then
        nodeList[1] = makeGCLayer(layerConfigSource, tmsDefs, dateList, endpointConfig["base_uri_gc"], epsgCode, targetEpsgCode)
    end

    if fileAttrs["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and
                string.sub(file, 0, 1) ~= "." then
                nodeList[#nodeList + 1] = makeGCLayer(layerConfigSource .. "/" .. file,
                 tmsDefs, dateList, endpointConfig["base_uri_gc"], targetEpsgCode)
            end
        end
    end
    return nodeList
end

local function makeGC(endpointConfig)
    -- Load TMS defs
    local tmsFile = assert(io.open(endpointConfig["tms_defs_file"], "r")
        , "Can't open tile matrixsets definition file at: " .. endpointConfig["tms_defs_file"])
    local tmsXml = xmlserde.deserialize(tmsFile:read("*all"))
    tmsFile:close()

    local epsgCode = assert(endpointConfig["epsg_code"], "Can't find epsg_code in endpoint config!")
    if string.match(epsgCode:lower(), "^%d") then
        epsgCode = "EPSG:" .. epsgCode
    end

    local targetEpsgCode = endpointConfig["target_epsg_code"]
    if targetEpsgCode and string.match(targetEpsgCode:lower(), "^%d") then
        targetEpsgCode = "EPSG:" .. targetEpsgCode
    end

    -- Parse header
    local headerFile = assert(io.open(endpointConfig["gc_header_file"], "r"),
        "Can't open GC header file at:" .. endpointConfig["gc_header_file"])
    local mainXml = xmlserde.deserialize(headerFile:read("*all"))
    headerFile:close()

    -- Build contents section
    local contentsNodeContent = {}
    for _, layer in pairs(getAllGCLayerNodes(endpointConfig, tmsXml, epsgCode, targetEpsgCode)) do
        contentsNodeContent[#contentsNodeContent + 1] = layer
    end
    for _, proj in ipairs(getXmlNodesByName(tmsXml, "Projection")) do
        if proj["attr"]["id"] == targetEpsgCode or not targetEpsgCode and epsgCode then
            for _, tms in ipairs(getXmlNodesByName(proj, "TileMatrixSet")) do
                contentsNodeContent[#contentsNodeContent + 1] = tms
            end
        end
    end
    local contentsNode = {name="Contents", kids=contentsNodeContent}

    -- Add contents to the rest of the XML
    mainXml["kids"][#mainXml["kids"] + 1] = contentsNode
    return xmlser.serialize(mainXml)
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
    return function()
        local responseXml = endpointConfig["gts_service"] == true and makeGTS(endpointConfig)
            or makeGC(endpointConfig)
        return sendResponse(200, responseXml)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_gc_service
else
    print(generateFromEndpointConfig())
end