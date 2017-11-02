local onearth = require "onearth"
handler = onearth.date_snapper({type="redis", ip="127.0.0.1"}, {type="strftime", date_format="%Y%j", date_time_format="%Y%j"})