# We get a full absolute path to the tree in this case so that when we
# generate the various paths in the local gdal-config file they will work
# from anywhere in the filesystem. 

include ../GDALmake.opt

CPPFLAGS  := $(GDAL_INCLUDE) -I$(GDAL_ROOT)/frmts -I$(GDAL_ROOT)/frmts/mrf $(CPPFLAGS)
LNK_FLAGS := $(LDFLAGS)
DEP_LIBS  =  $(EXE_DEP_LIBS) $(XTRAOBJ)
BIN_LIST  =  mrf_insert$(EXE) 

default:	gdal-config-inst gdal-config $(BIN_LIST)

all: default $(NON_DEFAULT_LIST)

lib-depend:
	(cd ../gcore ; $(MAKE) )
	(cd ../port ; $(MAKE) )

mrf_insert$(EXE): mrf_insert.$(OBJ_EXT) $(DEP_LIBS)
	$(LD) $(LNK_FLAGS) $< $(XTRAOBJ) $(CONFIG_LIBS) -o $@

clean:
	$(RM) *.o $(BIN_LIST) core gdal-config gdal-config-inst

$(DEP_LIBS):


gdal-config.in:
	cp ../apps/gdal-config.in .

gdal-config:	gdal-config.in ../GDALmake.opt ./GNUmakefile ../VERSION
	rm -f gdal-config
	echo '#!/bin/sh' > gdal-config
	echo 'CONFIG_LIBS="$(CONFIG_LIBS)"' >> gdal-config
	echo 'CONFIG_DEP_LIBS="$(LIBS)"' >> gdal-config
	echo 'CONFIG_PREFIX="$(GDAL_ROOT)"' >> gdal-config
	echo 'CONFIG_CFLAGS="-I$(GDAL_ROOT)/port -I$(GDAL_ROOT)/gcore -I$(GDAL_ROOT)/alg -I$(GDAL_ROOT)/ogr -I$(GDAL_ROOT)/ogr/ogrsf_frmts -I$(GDAL_ROOT)/frmts/vrt"' >> gdal-config
	echo 'CONFIG_DATA="$(GDAL_ROOT)/data"' >> gdal-config
	echo 'CONFIG_VERSION="'`cat ../VERSION`'"' >> gdal-config
	echo 'CONFIG_OGR_ENABLED=$(OGR_ENABLED)' >> gdal-config
	echo 'CONFIG_FORMATS="$(GDAL_FORMATS)"' >> gdal-config
	cat gdal-config.in >> gdal-config
	chmod a+x gdal-config

gdal-config-inst:	gdal-config.in ../GDALmake.opt ./GNUmakefile ../VERSION
	rm -f gdal-config-inst
	echo '#!/bin/sh' > gdal-config-inst
	echo 'CONFIG_LIBS="$(CONFIG_LIBS_INS)"' >> gdal-config-inst
	echo 'CONFIG_DEP_LIBS="$(LIBS)"' >> gdal-config-inst
	echo 'CONFIG_PREFIX="$(INST_PREFIX)"' >> gdal-config-inst
	echo 'CONFIG_CFLAGS="-I$(INST_INCLUDE)"' >> gdal-config-inst
	echo 'CONFIG_DATA="$(INST_DATA)"' >> gdal-config-inst
	echo 'CONFIG_VERSION="'`cat ../VERSION`'"' >> gdal-config-inst
	echo 'CONFIG_OGR_ENABLED=$(OGR_ENABLED)' >> gdal-config-inst
	echo 'CONFIG_FORMATS="$(GDAL_FORMATS)"' >> gdal-config-inst
	cat gdal-config.in >> gdal-config-inst
	chmod a+x gdal-config-inst


install: default
	for f in $(BIN_LIST) ; do $(INSTALL) $$f $(DESTDIR)$(INST_BIN) ; done


