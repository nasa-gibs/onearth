DEPTH=../../bin

srcdir=../../twms/EPSG3413

COMPOSE=$(DEPTH)/compose
TT=$(DEPTH)/twms_tool
TWMS_MRFS=$(DEPTH)/get_mrfs

TYPES:=

# These are the time variant layers
MRFS:=$(foreach type,$(TYPES),$(type)TTTTTTT_.mrf)

# Static layers go here


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
