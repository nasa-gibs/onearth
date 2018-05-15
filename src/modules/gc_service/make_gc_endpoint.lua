local onearth_gc_service = require "gc"

assert(arg[1], "Must specify endpoint config YAML file")
onearth_gc_service.createConfiguration(arg[1])