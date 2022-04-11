package = "OnEarth_Time_Service"
version = "0.1-2"
source = {
   url = "..." -- We don't have one yet
}
description = {
   summary = "Lua utilties for use with the OnEarth Apache modules",
   detailed = [[
      Description here
   ]],
   homepage = "http://...", -- We don't have one yet
   license = "MIT"
}
dependencies = {
   "lua >= 5.1, < 5.4",
   "json-lua == 0.1-4",
   "md5 == 1.3-1",
   "date == 2.1.2-1"
}
build = {
   type = "builtin",
   modules = {
      onearthTimeService = "time_service.lua"
   }
}