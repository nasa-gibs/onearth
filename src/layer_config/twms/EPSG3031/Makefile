DEPTH=../../bin

COMPOSE=$(DEPTH)/compose
TT=$(DEPTH)/twms_tool

TGT_PATH=/sites/twms-antarctic/.lib

TYPES:=

# These are the time variant layers
MRFS:=$(foreach type,$(TYPES),$(type)TTTTTTT_.mrf)

# Static layers go here


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
