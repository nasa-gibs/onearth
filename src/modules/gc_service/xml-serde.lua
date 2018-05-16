local xmlser = require("xml-ser")
local SLAXML = require("slaxml")
local List = require("list")

local serde = {}
function serde.serialize(spec, opts)
	return xmlser.serialize(spec, opts)
end

function serde.deserialize(xml)

	local root = {}
	local cur = root
	local tmp
	local stack = List:new()

	-- Specify as many/few of these as you like
	parser = SLAXML:parser{
		startElement = function(name,nsURI)
			tmp = {name=name }
			if not cur.kids
			then cur.kids = {} end
			cur.kids[(#cur.kids)+1] = tmp
			cur=tmp
			stack:pushright(cur)
		end, -- When "<foo" or <x:foo is seen
		attribute    = function(name,value,nsURI)
			if not cur.attr
			then cur.attr = {} end
			cur.attr[name] = value
		end, -- attribute found on current element
		closeElement = function(name,nsURI)
			stack:popright()
			cur=stack[stack.last]
		end, -- When "</foo>" or </x:foo> or "/>" is seen
		text         = function(text)
			cur.text = text
		end, -- text and CDATA nodes
		comment      = function(content)          end, -- comments
		pi           = function(target,content)   end, -- processing instructions e.g. "<?yes mon?>"
	}

	-- Ignore whitespace-only text nodes and strip leading/trailing whitespace from text
	-- (does not strip leading/trailing whitespace from CDATA)
	parser:parse(xml,{stripWhitespace=true})
	return root.kids[1]
end


return serde