DEPTH=../bin

COMPOSE=$(DEPTH)/compose
TT=$(DEPTH)/twms_tool

TGT_PATH=/home/jeff/apache2/htdocs/Tiled_WMS/.lib

TYPES:=aquarius_l3_sss_smi_daily___sss___1440_x_720___daynight \
 ascat_l2_coastal___wind_speed___2880_x_1440___day \
 ascat_l2_coastal___wind_speed___2880_x_1440___night \
 jpl_l2p_modis_a___chlorophyll_a___46080_x_23040___day \
 jpl_l2p_modis_a___jpl_l2p_modis_t___sst___46080_x_23040___night \
 jpl_ourocean_l4___sst___36000_x_18000___daynight \
 oscar_l4_oc_third_deg___oceancurrent_speed___1088_x_544___daynight \
 remss_windsat_l2p_gridded___sst___1440_x_720___night

# These are the time variant layers
MRFS:=$(foreach type,$(TYPES),$(type)TTTTTTT_.mrf)

TARGETS:=getTileService.xml cache.config getCapabilities.xml wms_config.xml

default: getTileService.xml

all: $(TARGETS)

getTileService.xml:	getTileService.base	TiledGroup.master $(MRFS)
	TT=$(TT) $(COMPOSE) <$< >$@

installGTS:	getTileService.xml
	cp -p $< $(TGT_PATH)

getCapabilities.xml:	getCapabilities.base	Layer_template
	$(COMPOSE) <$< >$@

installGC:	getCapabilities.xml
	cp -p $< $(TGT_PATH)

cache.config: $(MRFS)
	$(TT) -cb $(MRFS) $@

wms_config.xml:	wms_config.base wmsc.master
	$(COMPOSE) <$< >$@

installWMSC:	wms_config.xml
	cp -p $< $(TGT_PATH)

clean:
	rm -f $(TARGETS) wms_config.xml getCapabilities.xml
