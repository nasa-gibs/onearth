DEPTH=../bin

srcdir=../Tiled-WMS

COMPOSE=$(DEPTH)/compose
TT=$(DEPTH)/twms_tool
TWMS_MRFS=$(DEPTH)/get_mrfs

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

TARGETS:=mrfs cache_wmts.config

default: mrfs cache_wmts.config

all: $(TARGETS)

# Dummy target to build the input .mrf files
# The MRFS list can be a subset of the ones in the source directory
# They all get built, but only the MRFS list get incorporated in the wmts
# cache_wmts.config
#

mrfs	:
	$(TWMS_MRFS) $(srcdir)

cache_wmts.config: $(MRFS)
	$(TT) -cb $(MRFS) $@

clean:
	rm -f $(TARGETS) $(MRFS) wms_config.xml getCapabilities.xml 
