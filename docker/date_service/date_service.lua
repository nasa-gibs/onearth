local onearth = require "onearth"
handler = onearth.date_snapper({handler_type="redis", host="127.0.0.1", port="22121"}, {filename_format="hash"})