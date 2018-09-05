local onearth_gc_gts = require "onearth_gc_gts"
local config = {
    layer_config_source="/etc/onearth/config/layers/layer_config",
    tms_defs_file="/etc/onearth/config/conf/tilematrixsets.xml",
    gc_header_loc="/etc/onearth/config/conf/header_gts.xml",
    date_service_uri="http://localhost/date_service/date",
    epsg_code="EPSG:4326",
    gts_service=true,
    gc_header_file=nil,
    gts_header_file="/etc/onearth/config/conf/header_gts.xml",
    base_uri_gc=nil,
    base_uri_gts="http://localhost/layer_config_endpoint/",
    target_epsg_code=nil,
    date_service_keys={}
}
handler = onearth_gc_gts.handler(config)
