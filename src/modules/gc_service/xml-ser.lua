-- xmlser, a simple xml serializer
-- @author bibby <bibby@bbby.org>
-- @license MIT
-- @version 0.1.0 (29 Mar 2014)

--[[
Use:
	xmlser.serialize( xmlSpec [,options])

Serialize a table that complies with the spec
to a xml string. The spec is as follows:

	"name" : string, required.
	The tag name of the element

	"attr" : table (associative, map, kv pairs), optional
	Tag attributes, ie {"type"="xmlser:xml"}

	"kids" : table (list, array), optional
	Child elements, following this same spec

	"text" : string, optional
	tag data, escaped for you unless opt.noEscapeText is true

	"cdata" : string, optional
	use in place of text for tag data to have serialized as CDATA


Serializer options:

	"shortClosure" : Allow self closing tags
	Default = true

	"escapeText" : Safe-xml escaping on tag data.
	Not sure why you'd disable this.
	Default = true

	"escapeAttr" : Safe-xml escaping on tag attributes.
	Not sure why you'd disable this.
	Default = true

--]]


xmlser = {}

-- serialize a table
function xmlser.serialize(spec, opts)
	if type(spec) ~= "table" then 
		error("xmlser.serialize expected table, got "..type(spec))
	end

	-- default ser options
	local options = {
		shortClosure = true,
		escapeText = true,
		escapeAttr = true
	}

	-- apply user options
	if type(opts) == "table" then
		for k,v in pairs(opts) do
			if options[k] ~= nil then
				options[k] = v
			end
		end
	end
	
	-- start a tag
	local tag = spec.name
	local xml = {"<"..tag} -- open tag

	-- add attributes
	local attrs = xmlser.serAttr(spec.attr, options.escapeAttr)
	if attrs then
		push(xml, " "..attrs)
	end
	
	-- decide on short closure
	local close = options.shortClosure

	if close
	and not spec.text 
	and not spec.kids then
		push(xml, "/>")
		close = false
	else
		push(xml, ">")
	end
	
	-- add text data
	if spec.text then
		local text = spec.text
		if options.escapeText then
			text = xmlser.escape(spec.text)
		end
		push(xml, text)
	end
	
	-- add cdata
	if spec.cdata then
		push(xml, xmlser.cdata(spec.cdata)) 
	end

	-- add nested tags
	if spec.kids then
		for _,kid in ipairs(spec.kids) do
			push(xml, xmlser.serialize(kid, opts))
		end
	end
	
	if close then 
		push(xml, "</", spec.name, ">")
	end
	
	return table.concat(xml)
	
end

function xmlser.serAttr(attr, escape)
	if type(attr) ~= "table" then
		return nil
	end
	local attrStr ={}
	for prop, val in pairs(attr) do
		if escape then
			 val = xmlser.escape(val)
		end
		push(attrStr, table.concat({prop, '="', val, '"'}))
	end
	
	return table.concat(attrStr, " ")
end

function xmlser.cdata(str)
	return table.concat({"<![CDATA[", str, "]]"})
end

function xmlser.escape(str)
	local ents = {
		['"']="&quot;",
		["'"]="&apos;",
		["&"]="&amp;",
		["<"]="&lt;",
		[">"]="&gt;"
	}
	return string.gsub(str,"([\"'<>&])",ents)
end

function push(list, ...)
	if type(...) ~= "table" then
		push(list,{...})
	else
		for _,v in ipairs(...) do
		list[ #list + 1 ] = v
		end
	end
end

return xmlser