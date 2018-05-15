local onearth_gc_service = {}

local xmlser = require "xml-ser"
local xmlserde = require "xml-serde"
local lfs = require "lfs"
local lyaml = require "lyaml"
local request = require "http.request"
local JSON = require "JSON"

-- Utility functions
local function split (sep, str)
    local results = {}
    for value in string.gmatch(str, "([^" .. sep .. "]+)") do
        results[#results + 1] = value
    end
    return results
end

local function sendResponse (code, msg_string)
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

local function getExtensionFromMimeType(mimeType) 
    if mimeType == "image/jpeg" then
        return ".jpeg"
    end
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
handler = gc.handler(${config_loc}, ${tms_loc}, ${gc_header_loc}, ${date_service_uri} )
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

-- Service functions

local function getDateList(dateServiceUri)
    local headers, stream = assert(request.new_from_uri(dateServiceUri):go(5))
    local body = assert(stream:get_body_as_string())
    if headers:get ":status" ~= "200" then
        error(body)
    end
    return JSON:decode(body)
end

-- Turn the XML tms defs file into a table containing just what we need.
local function getTmsDefs(tmsXml) 
    local tileMatrixSets = {}
    for _, tms in pairs(tmsXml["kids"]) do
        local tmsName = getXmlChildrenByName(tms, "Identifier")
        local matrices = {}
        for _, matrix in pairs(tms["kids"]) do
            if matrix["name"] == "TileMatrix" then
                local identifier = getXmlChildrenByName(matrix, "Identifier")
                local topLeft = split(" ", getXmlChildrenByName(matrix, "TopLeftCorner"))
                matrices[tonumber(identifier) + 1] = {
                    topLeft={tonumber(topLeft[1]), tonumber(topLeft[2])}
                }
            end
        end
        tileMatrixSets[tmsName] = matrices
    end
    return tileMatrixSets
end

local function makeGts(endpointConfig)
    -- Load and parse header
    local headerFilename = assert(endpointConfig["gts_header_file"], "No gts_header_file specified in endpoint config")
    local headerFile = assert(io.open(headerFilename, "r"), "Can't open GTS header file at:" .. headerFilename)

    -- Build <TiledPatterns>
end


local function parseFile(filename, tmsDefs, dateList, baseUriGC)
    -- Load and parse the YAML config file
    local configFile = assert(io.open(filename, "r"))
    local config = lyaml.load(configFile:read("*all"))
    configFile:close()

    -- Look for the required data in the YAML config file, and throw errors if we can't find it
    local layerTitle = assert(config.layer_title, "Can't find 'layer_title' in YAML!")
    local layerName = assert(config.layer_name, "Can't find 'layer_name' in YAML!")
    -- local projection = assert(config.projection, "Can't find projection in YAML!")
    local mimeType = assert(config.mime_type, "Can't find MIME type in YAML!")
    local tmsName = assert(config.tms, "Can't find TileMatrixSet name in YAML!")
    local static = true
    static = config.static or static

    local defaultDate
    local periods
    if not static then
        defaultDate = config.default_date or dateList[layerName]["default"]
        periods = config.periods or dateList[layerName]["periods"]
    end
    
    local layerContents = {}
    layerContents[#layerContents + 1] = {name= "ows:Title", attr={["xml:lang"]="en"}, text=layerTitle}

    -- Get the information we need from the TMS definitions and add bbox node
    local tmsDef = tmsDefs[tmsName]
    local upperCorner = tostring(tmsDef[1]["topLeft"][1] * -1) .. " " .. tostring(tmsDef[2]["topLeft"][2])
    local lowerCorner = tostring(tmsDef[1]["topLeft"][1]) .. " " .. tostring(tmsDef[2]["topLeft"][2] * -1)
    
    layerContents[#layerContents + 1] = {name="ows:WGS84BoundingBox", attr={crs="urn:ogc:def:crs:OGC:2:84"}, kids={
        {name="ows:LowerCorner", text=lowerCorner}, {name="ows:UpperCorner", text=upperCorner}
    }}

    layerContents[#layerContents + 1] = {name="ows:BoundingBox", attr={crs="urn:ogc:def:crs:EPSG::3413"}, kids={
     {name="ows:LowerCorner", text=lowerCorner}, {name="ows:UpperCorner", text=upperCorner}
    }}

    -- Add identifier node
    layerContents[#layerContents + 1] = {name="ows:Identifier", text=layerName}

    -- Build Metadata and add nodes
    for _, metadata in pairs(config.metadata) do
        local metadataNode = {name="ows:Metadata", attr={}}
        for attr, value in pairs(metadata) do
            metadataNode["attr"][attr] = value
        end
        layerContents[#layerContents + 1] = metadataNode
    end

    -- Build the ResourceURL element
    local timeString = not static and "/{Time}" or ""
    local template = baseUriGC .. layerName .. "/" .. "default" .. timeString .. "/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}" .. getExtensionFromMimeType(mimeType)
    layerContents[#layerContents + 1] = {name="ResourceURL", attr={format=mimeType, resourceType="tile", template=template}}

    -- Build the Style element
    local styleNode = {name="Style", attr={isDefault="true"}, kids={
        {name="ows:Title", attr={["xml:lang"]="en"}, text="default"},
        {name="ows:Identifier", text="default"}
    }}
    layerContents[#layerContents + 1] = styleNode

    -- Build the <Dimension> element for time (if necessary)
    local dimensionNode
    if not static then
        dimensionNode = {name="Dimension", kids={
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
    return { name="Layer", kids=layerContents}
end

local function getAllLayerNodes(layerConfigSource, tmsXml, dateServiceUri, baseUriGC)
    local tmsDefs = getTmsDefs(tmsXml)
    local dateList = getDateList(dateServiceUri)

    local nodeList = {}
    if lfs.attributes(layerConfigSource)["mode"] == "file" then
        nodeList[1] = parseFile(layerConfigSource, tmsDefs, dateList, baseUriGC)
    end

    if lfs.attributes(layerConfigSource)["mode"] == "directory" then
        -- Only going down a single directory level
        for file in lfs.dir(layerConfigSource) do
            if lfs.attributes(layerConfigSource .. "/" .. file)["mode"] == "file" and 
                string.sub(file, 0, 1) ~= "." then
                nodeList[#nodeList + 1] = parseFile(layerConfigSource .. "/" .. file, tmsDefs, dateList, baseUriGC)
            end
        end
    end
    return nodeList
end

local function main(layerConfigSource, tmsDefsFilename, headerFilename, dateServiceUri, baseUriGC)
    -- Load TMS defs
    local tmsFile = assert(io.open(tmsDefsFilename, "r")
        , "Can't open tile matrixsets definition file at: " .. tmsDefsFilename)
    local tmsXml = xmlserde.deserialize(tmsFile:read("*all")) 
    tmsFile:close()

    -- Parse header
    local headerFile = assert(io.open(headerFilename, "r"), "Can't open GC header file at:" .. headerFilename)
    local mainXml = xmlserde.deserialize(headerFile:read("*all"))
    headerFile:close()

    -- Build contents section
    local contentsNodeContent = {}
    for _, layer in pairs(getAllLayerNodes(layerConfigSource, tmsXml, dateServiceUri, baseUriGC)) do
        contentsNodeContent[#contentsNodeContent + 1] = layer
    end
    for _, tms in pairs(tmsXml["kids"]) do
        contentsNodeContent[#contentsNodeContent + 1] = tms
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

    local tmsDefsFilename = endpointConfig["tms_defs_file"]
    local headerFilename = endpointConfig["gc_header_file"]
    local layerConfigSource = endpointConfig["layer_config_source"]
    local dateServiceUri = endpointConfig["date_service_uri"]
    local baseUriGC = endpointConfig["base_uri_gc"]
    return main(layerConfigSource, tmsDefsFilename, headerFilename, dateServiceUri, baseUriGC)
end

function onearth_gc_service.handler(layerConfigSource, tmsDefsFilename, headerFilename, dateServiceUri, baseUriGC)
    return function()
        local responseXml = main(layerConfigSource, tmsDefsFilename, headerFilename, dateServiceUri, baseUriGC)
        return sendResponse(200, responseXml)
    end
end

if pcall(debug.getlocal, 4, 1) then
    return onearth_gc_service
else
    print(generateFromEndpointConfig())
end