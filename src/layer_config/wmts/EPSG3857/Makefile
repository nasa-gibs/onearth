DEPTH=/usr/bin

srcdir=

COMPOSE=$(DEPTH)/compose
TT=$(DEPTH)/twms_tool

TYPES:=

# These are the time variant layers
MRFS:=$(foreach type,$(TYPES),$(type)TTTTTTT_.mrf)

# Static layers go here


TARGETS:=cache_wmts.config

default: cache_wmts.config

all: $(TARGETS)

# Dummy target to build the input .mrf files
# The MRFS list can be a subset of the ones in the source directory
# They all get built, but only the MRFS list get incorporated in the wmts
# cache_wmts.config
#

cache_wmts.config: $(MRFS)
	$(TT) -cb $(MRFS) $@

clean:
	rm -f $(TARGETS) wms_config.xml getCapabilities.xml 
