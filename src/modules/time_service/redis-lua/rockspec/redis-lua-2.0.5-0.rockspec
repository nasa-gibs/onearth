package = "redis-lua"
version = "2.0.5-0"

source = {
   url = "https://github.com/nasa-gibs/onearth/tree/main/src/modules/time_service/redis-lua",
   md5 = "46e962a4f5361c82473ccd33d4b18003"
}

description = {
   summary = "A Lua client library for the redis key value storage system.",
   detailed = [[
      A Lua client library for the redis key value storage system.
   ]],
   homepage = "http://github.com/nrk/redis-lua",
   license = "MIT/X11"
}

dependencies = {
   "lua >= 5.1",
   "luasocket"
}

build = {
   type = "none",
   install = {
      lua = {
         redis = "src/redis.lua"
      }
   }
}
