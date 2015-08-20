ONEARTH_VERSION=0.7.0

PREFIX=/usr/local
SMP_FLAGS=-j $(shell cat /proc/cpuinfo | grep processor | wc -l)
LIB_DIR=$(shell \
	[ "$(shell arch)" == "x86_64" ] \
		&& echo "lib64" \
		|| echo "lib" \
)
RPMBUILD_FLAGS=-ba

NUMPY_ARTIFACT=numpy-1.5.1.tar.gz
NUMPY_URL=https://pypi.python.org/packages/source/n/numpy/$(NUMPY_ARTIFACT)
MPL_ARTIFACT=matplotlib-1.3.1.tar.gz
MPL_URL=https://pypi.python.org/packages/source/m/matplotlib/$(MPL_ARTIFACT)
CGICC_ARTIFACT=cgicc-3.2.16.tar.gz
CGICC_URL=http://ftp.gnu.org/gnu/cgicc/$(CGICC_ARTIFACT)

all: 
	@echo "Use targets onearth-rpm"

onearth: numpy-unpack mpl-unpack cgicc-unpack onearth-compile

#-----------------------------------------------------------------------------
# Download
#-----------------------------------------------------------------------------

download: numpy-download mpl-download cgicc-download

numpy-download: upstream/$(NUMPY_ARTIFACT).downloaded

upstream/$(NUMPY_ARTIFACT).downloaded: 
	mkdir -p upstream
	rm -f upstream/$(NUMPY_ARTIFACT)
	( cd upstream ; wget $(NUMPY_URL) )
	touch upstream/$(NUMPY_ARTIFACT).downloaded
	
mpl-download: upstream/$(MPL_ARTIFACT).downloaded

upstream/$(MPL_ARTIFACT).downloaded: 
	mkdir -p upstream
	rm -f upstream/$(MPL_ARTIFACT)
	( cd upstream ; wget $(MPL_URL) )
	touch upstream/$(MPL_ARTIFACT).downloaded
	
cgicc-download: upstream/$(CGICC_ARTIFACT).downloaded

upstream/$(CGICC_ARTIFACT).downloaded: 
	mkdir -p upstream
	rm -f upstream/$(CGICC_ARTIFACT)
	( cd upstream ; wget $(CGICC_URL) )
	touch upstream/$(CGICC_ARTIFACT).downloaded

#-----------------------------------------------------------------------------
# Compile
#-----------------------------------------------------------------------------

numpy-unpack: build/numpy/VERSION

build/numpy/VERSION:
	mkdir -p build/numpy
	tar xf upstream/$(NUMPY_ARTIFACT) -C build/numpy \
		--strip-components=1 --exclude=.gitignore
		
mpl-unpack: build/mpl/VERSION

build/mpl/VERSION:
	mkdir -p build/mpl
	tar xf upstream/$(MPL_ARTIFACT) -C build/mpl \
		--strip-components=1 --exclude=.gitignore
		
cgicc-unpack: build/cgicc/VERSION

build/cgicc/VERSION:
	mkdir -p build/cgicc
	tar xf upstream/$(CGICC_ARTIFACT) -C build/cgicc \
		--strip-components=1 --exclude=.gitignore

onearth-compile:
	$(MAKE) -C src/mod_onearth \
		LIBS=-L/usr/pgsql-$(POSTGRES_VERSION)/lib \
		LDFLAGS=-lpq

#-----------------------------------------------------------------------------
# Install
#-----------------------------------------------------------------------------
install: onearth-install 

onearth-install:
	install -m 755 -d $(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules
	install -m 755 src/mod_onearth/.libs/mod_twms.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_twms.so
	install -m 755 src/mod_onearth/.libs/mod_onearth.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_onearth.so

	install -m 755 -d $(DESTDIR)/$(PREFIX)/bin
	install -m 755 src/mod_onearth/oe_create_cache_config \
		$(DESTDIR)/$(PREFIX)/bin/oe_create_cache_config
	install -m 755 src/layer_config/bin/oe_configure_layer.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_configure_layer
	install -m 755 src/layer_config/bin/oe_generate_empty_tile.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_generate_empty_tile.py
	install -m 755 src/onearth_logs/onearth_logs.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/onearth_metrics
	install -m 755 src/generate_legend/oe_generate_legend.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_generate_legend.py
	install -m 755 src/mrfgen/mrfgen.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/mrfgen
	install -m 755 src/mrfgen/colormap2vrt.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/colormap2vrt.py
	install -m 755 src/mrfgen/RGBApng2Palpng  \
		-D $(DESTDIR)/$(PREFIX)/bin/RGBApng2Palpng

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/apache/kml
	install -m 755 src/cgi/twms.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 src/cgi/wmts.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	cp src/cgi/kml/* \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache/kml
	cp src/cgi/index.html \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	cp src/mrfgen/empty_tiles/black.jpg \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	cp src/mrfgen/empty_tiles/transparent.png \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/mrfgen
	cp src/mrfgen/empty_tiles/* \
		$(DESTDIR)/$(PREFIX)/share/onearth/mrfgen

	install -m 755 -d $(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/conf \
		$(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/layers \
		$(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/schema \
		$(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/mapserver \
		$(DESTDIR)/etc/onearth/config
	install -m 755 -d $(DESTDIR)/etc/onearth/config/headers

	install -m 755 -d $(DESTDIR)/etc/onearth/metrics
	cp -r src/onearth_logs/logs.* \
		$(DESTDIR)/etc/onearth/metrics
	cp -r src/onearth_logs/tilematrixsetmap.* \
		$(DESTDIR)/etc/onearth/metrics

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/demo
	cp -r src/demo/* $(DESTDIR)/$(PREFIX)/share/onearth/demo

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/numpy
	cp -r build/numpy/* $(DESTDIR)/$(PREFIX)/share/numpy
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/mpl
	cp -r build/mpl/* $(DESTDIR)/$(PREFIX)/share/mpl
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/cgicc
	cp -r build/cgicc/* $(DESTDIR)/$(PREFIX)/share/cgicc


#-----------------------------------------------------------------------------
# Local install
#-----------------------------------------------------------------------------
local-install: onearth-local-install

onearth-local-install: 
	mkdir -p build/install
	$(MAKE) onearth-install DESTDIR=$(PWD)/build/install

#-----------------------------------------------------------------------------
# Artifacts
#-----------------------------------------------------------------------------
artifacts: onearth-artifact

onearth-artifact: onearth-clean
	mkdir -p dist
	rm -rf dist/onearth-$(ONEARTH_VERSION).tar.bz2
	tar cjvf dist/onearth-$(ONEARTH_VERSION).tar.bz2 \
		--transform="s,^,onearth-$(ONEARTH_VERSION)/," \
		src/mod_onearth src/layer_config src/mrfgen src/cgi \
		src/demo src/onearth_logs src/generate_legend GNUmakefile

#-----------------------------------------------------------------------------
# RPM
#-----------------------------------------------------------------------------
rpm: onearth-rpm

onearth-rpm: onearth-artifact 
	mkdir -p build/rpmbuild/SOURCES
	mkdir -p build/rpmbuild/BUILD	
	mkdir -p build/rpmbuild/BUILDROOT
	rm -f dist/onearth*.rpm
	cp \
		upstream/$(NUMPY_ARTIFACT) \
		upstream/$(MPL_ARTIFACT) \
		upstream/$(CGICC_ARTIFACT) \
		dist/onearth-$(ONEARTH_VERSION).tar.bz2 \
		build/rpmbuild/SOURCES
	rpmbuild \
		--define _topdir\ "$(PWD)/build/rpmbuild" \
		-ba deploy/onearth/onearth.spec 
	mv build/rpmbuild/RPMS/*/onearth*.rpm dist

#-----------------------------------------------------------------------------
# Mock
#-----------------------------------------------------------------------------
mock: onearth-mock

onearth-mock:
	mock --clean
	mock --init
	mock --copyin dist/gibs-gdal-*$(GDAL_VERSION)-*.$(shell arch).rpm /
	mock --install yum
	mock --shell \
	       "yum install -y /gibs-gdal-*$(GDAL_VERSION)-*.$(shell arch).rpm"
	mock --rebuild --no-clean \
		dist/mod_twms-$(ONEARTH_VERSION)-*.src.rpm

#-----------------------------------------------------------------------------
# Clean
#-----------------------------------------------------------------------------
clean: onearth-clean
	rm -rf build

onearth-clean:
	$(MAKE) -C src/mod_onearth clean

distclean: clean
	rm -rf dist
	rm -rf upstream


