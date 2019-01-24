local onearthTimeService = require "onearthTimeService"
handler = onearthTimeService.timeService({handler_type="redis", host="{REDIS_HOST}"}, {filename_format="basic"})
