local onearthTimeService = require "onearthTimeService"
handler = onearthTimeService.timeService({handler_type="redis", host="{REDIS_HOST_READER}"}, {filename_format="basic"})
