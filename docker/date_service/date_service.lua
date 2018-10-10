local onearth = require "onearth"
handler = onearth.date_snapper({handler_type="redis", host="{REDIS_HOST}"}, {filename_format="hash"})