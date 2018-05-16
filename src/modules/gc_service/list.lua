List = {}
function List:new ()
	local l = {first = 0, last = -1 }
	setmetatable(l, self)
	self.__index = self
	return l
end

function List:pushleft (value)
	local first = self.first - 1
	self.first = first
	self[first] = value
	return self:len()
end

function List:push (value)
	return self:pushright(value)
end

function List:pushright (value)
	local last = self.last + 1
	self.last = last
	self[last] = value
	return self:len()
end

function List:pop (value)
	return self:popleft(value)
end

function List:popleft ()
	local first = self.first
	if first > self.last then return nil end
	local value = self[first]
	self[first] = nil        -- to allow garbage collection
	self.first = first + 1
	return value
end

function List:popright ()
	local last = self.last
	if self.first > last then return nil end

	local value = self[last]
	self[last] = nil         -- to allow garbage collection
	self.last = last - 1
	return value
end

function List:all ()
	local res = {}
	local k = 1
	for i = self.first, self.last do
		res[k] = self[i]
		k = k + 1
	end
	return res
end

function List:len ()
	return self.last - self.first + 1
end

return List