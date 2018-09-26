local onearth_gc_gts = require "onearth_gc_gts"
local config = {
    layer_config_source="/etc/onearth/config/layers/layer_config/",
    tms_defs_file="/etc/onearth/config/conf/tilematrixsets.xml",
    gc_header_loc="/etc/onearth/config/conf/header_gc.xml",
    date_service_uri="http://localhost/date_service/date",
    epsg_code="EPSG:4326",
    gts_service=false,
    gc_header_file="/etc/onearth/config/conf/header_gc.xml",
    gts_header_file=nil,
    base_uri_gc="http://localhost/layer_config_reproject_endpoint/",
    base_uri_gts=nil,
    target_epsg_code="EPSG:3857",
    date_service_keys={}
}
handler = onearth_gc_gts.handler(config)
