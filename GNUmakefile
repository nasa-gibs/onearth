# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ONEARTH_VERSION=1.3.1

PREFIX=/usr/local
LIB_PREFIX=/usr
SMP_FLAGS=-j $(shell cat /proc/cpuinfo | grep processor | wc -l)
LIB_DIR=$(shell \
	[ "$(shell arch)" == "x86_64" ] \
		&& echo "lib64" \
		|| echo "lib" \
)
RPMBUILD_FLAGS=-ba

MPL_ARTIFACT=matplotlib-1.5.1.tar.gz
MPL_URL=https://pypi.python.org/packages/source/m/matplotlib/$(MPL_ARTIFACT)
CGICC_ARTIFACT=cgicc-3.2.16.tar.gz
CGICC_URL=http://ftp.gnu.org/gnu/cgicc/$(CGICC_ARTIFACT)
SPATIALINDEX_ARTIFACT=spatialindex-src-1.8.5.tar.gz
SPATIALINDEX_URL=http://download.osgeo.org/libspatialindex/$(SPATIALINDEX_ARTIFACT)

HTTPD_VERSION=$(shell rpm -q --qf "%{VERSION}" $(shell rpm -q --whatprovides redhat-release))
ifeq ($(HTTPD_VERSION), 6)
        HTTPD_ARTIFACT=httpd-2.2.15.tar.gz
        LINE=933
else
		HTTPD_ARTIFACT=httpd-2.4.6.tar.gz
		LINE=735
endif
HTTPD_URL=https://archive.apache.org/dist/httpd/$(HTTPD_ARTIFACT)

MAPSERVER_VERSION=7.0.1
MAPSERVER_ARTIFACT=mapserver-$(MAPSERVER_VERSION).tar.gz
MAPSERVER_HOME=http://download.osgeo.org/mapserver
MAPSERVER_URL=$(MAPSERVER_HOME)/$(MAPSERVER_ARTIFACT)

LXML_VERSION=3.8.0
LXML_ARTIFACT=lxml-$(LXML_VERSION).tar.gz
LXML_URL=https://github.com/lxml/lxml/archive/lxml-3.8.0.tar.gz

PYPARSING_VERSION=2.2.0
PYPARSING_ARTIFACT=pyparsing-$(PYPARSING_VERSION)-py2.py3-none-any.whl

PARSE_APACHE_CONFIGS_VERSION=0.0.2
PARSE_APACHE_CONFIGS_ARTIFACT=parse_apache_configs-$(PARSE_APACHE_CONFIGS_VERSION).tar.gz

all: 
	@echo "Use targets onearth-rpm"

onearth: mpl-unpack cgicc-unpack spatialindex-unpack httpd-unpack mapserver-unpack lxml-unpack pyparsing-unpack parse_apache_configs-unpack onearth-compile

#-----------------------------------------------------------------------------
# Download
#-----------------------------------------------------------------------------

download: mpl-download cgicc-download spatialindex-download httpd-download mapserver-download lxml-download pyparsing-download parse_apache_configs-download
	
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

spatialindex-download: upstream/$(SPATIALINDEX_ARTIFACT).downloaded

upstream/$(SPATIALINDEX_ARTIFACT).downloaded: 
	mkdir -p upstream
	rm -f upstream/$(SPATIALINDEX_ARTIFACT)
	( cd upstream ; wget $(SPATIALINDEX_URL) )
	touch upstream/$(SPATIALINDEX_ARTIFACT).downloaded
	
httpd-download: upstream/$(HTTPD_ARTIFACT).downloaded

upstream/$(HTTPD_ARTIFACT).downloaded:
	mkdir -p upstream
	rm -f upstream/$(HTTPD_ARTIFACT)
	( cd upstream ; wget $(HTTPD_URL) )
	touch upstream/$(HTTPD_ARTIFACT).downloaded

mapserver-download: upstream/$(MAPSERVER_ARTIFACT).downloaded

upstream/$(MAPSERVER_ARTIFACT).downloaded:
	mkdir -p upstream
	rm -rf upstream/$(MAPSERVER_ARTIFACT)
	( cd upstream ; wget $(MAPSERVER_URL) )
	touch upstream/$(MAPSERVER_ARTIFACT).downloaded
	
lxml-download: upstream/$(LXML_ARTIFACT).downloaded

upstream/$(LXML_ARTIFACT).downloaded:
	mkdir -p upstream
	rm -rf upstream/$(LXML_ARTIFACT)
	( cd upstream ; wget $(LXML_URL) )
	touch upstream/$(LXML_ARTIFACT).downloaded
	
pyparsing-download: upstream/$(PYPARSING_ARTIFACT).downloaded

upstream/$(PYPARSING_ARTIFACT).downloaded:
	mkdir -p upstream
	rm -rf upstream/$(PYPARSING_ARTIFACT)
	pip install --download upstream pyparsing==$(PYPARSING_VERSION)
	touch upstream/$(PYPARSING_ARTIFACT).downloaded
	
parse_apache_configs-download: upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT).downloaded

upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT).downloaded:
	mkdir -p upstream
	rm -rf upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT)
	pip install --download upstream parse_apache_configs==$(PARSE_APACHE_CONFIGS_VERSION)
	touch upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT).downloaded

#-----------------------------------------------------------------------------
# Compile
#-----------------------------------------------------------------------------
		
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

spatialindex-unpack: build/spatialindex/VERSION

build/spatialindex/VERSION:
	mkdir -p build/spatialindex
	tar xf upstream/$(SPATIALINDEX_ARTIFACT) -C build/spatialindex \
		--strip-components=1 --exclude=.gitignore
	cd build/spatialindex && ./configure --libdir=$(DESTDIR)/$(LIB_PREFIX)/$(LIB_DIR) --prefix=$(DESTDIR)/$(LIB_PREFIX)
	$(MAKE) -C build/spatialindex
	
httpd-unpack: build/httpd/VERSION

build/httpd/VERSION:
	mkdir -p build/httpd
	mkdir -p /tmp/httpd
	tar xf upstream/$(HTTPD_ARTIFACT) -C build/httpd \
		--strip-components=1 --exclude=.gitignore
	sed -i "${LINE}d" build/httpd/modules/proxy/mod_proxy_http.c
	cd build/httpd && ./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared 
	cd build/httpd && make
	cd build/httpd && make install
		
mapserver-unpack: build/mapserver/VERSION

build/mapserver/VERSION:
	mkdir -p build/mapserver
	tar xf upstream/$(MAPSERVER_ARTIFACT) -C build/mapserver \
		--strip-components=1 --exclude=.gitignore
		
lxml-unpack: build/lxml/VERSION

build/lxml/VERSION:
	mkdir -p build/lxml
	tar xf upstream/$(LXML_ARTIFACT) -C build/lxml
	
pyparsing-unpack: build/pyparsing/VERSION

build/pyparsing/VERSION:
	mkdir -p build/pyparsing
	mv upstream/$(PYPARSING_ARTIFACT) build/pyparsing
	
parse_apache_configs-unpack: build/parse_apache_configs/VERSION

build/parse_apache_configs/VERSION:
	mkdir -p build/parse_apache_configs
	tar xf upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT) -C build/parse_apache_configs

onearth-compile:
	# Handle external headers
	cp src/modules/mod_receive/src/receive_context.h src/modules/mod_reproject/src/
	sed -i 's/<receive_context.h>/"receive_context.h"/g' src/modules/mod_reproject/src/mod_reproject.cpp
	cp src/modules/mod_receive/src/receive_context.h src/modules/mod_twms/src/
	sed -i 's/<receive_context.h>/"receive_context.h"/g' src/modules/mod_twms/src/mod_twms.cpp
	cp src/modules/mod_reproject/src/mod_reproject.h src/modules/mod_wmts_wrapper/
	
	$(MAKE) -C src/modules/mod_onearth
	$(MAKE) -C src/modules/mod_oetwms
	$(MAKE) -C src/modules/mod_oems
	$(MAKE) -C src/modules/mod_oemstime
	$(MAKE) -C src/modules/mod_wmts_wrapper
	$(MAKE) -C src/modules/mod_receive/src
	$(MAKE) -C src/modules/mod_reproject/src
	$(MAKE) -C src/modules/mod_twms/src

#-----------------------------------------------------------------------------
# Install
#-----------------------------------------------------------------------------
install: onearth-install 

onearth-install:
	install -m 755 -d $(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules
	install -m 755 src/modules/mod_oetwms/.libs/mod_oetwms.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_oetwms.so
	install -m 755 src/modules/mod_onearth/.libs/mod_onearth.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_onearth.so
	install -m 755 src/modules/mod_oems/.libs/mod_oems.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_oems.so
	install -m 755 src/modules/mod_oemstime/.libs/mod_oemstime.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_oemstime.so
	install -m 755 src/modules/mod_receive/src/.libs/mod_receive.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_receive.so
	install -m 755 src/modules/mod_reproject/src/.libs/mod_reproject.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_reproject.so
	install -m 755 src/modules/mod_twms/src/.libs/mod_twms.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_twms.so
	install -m 755 src/modules/mod_wmts_wrapper/.libs/mod_wmts_wrapper.so \
		$(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_wmts_wrapper.so
		
	install -m 755 -d $(DESTDIR)/$(PREFIX)/bin
	install -m 755 src/modules/mod_onearth/oe_create_cache_config \
		$(DESTDIR)/$(PREFIX)/bin/oe_create_cache_config
	install -m 755 src/layer_config/bin/oe_configure_layer.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_configure_layer
	install -m 755 src/empty_tile/oe_generate_empty_tile.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_generate_empty_tile.py
	install -m 755 src/onearth_logs/onearth_logs.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/onearth_metrics
	install -m 755 src/generate_legend/oe_generate_legend.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_generate_legend.py
	install -m 755 src/mrfgen/mrfgen.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/mrfgen
	install -m 755 src/mrfgen/colormap2vrt.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/colormap2vrt.py
	install -m 755 src/mrfgen/overtiffpacker.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/overtiffpacker.py
	install -m 755 src/mrfgen/RGBApng2Palpng  \
		-D $(DESTDIR)/$(PREFIX)/bin/RGBApng2Palpng
	install -m 755 src/mrfgen/oe_validate_palette.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_validate_palette.py
	install -m 755 src/scripts/oe_utils.py \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_utils.py
	install -m 755 src/scripts/oe_configure_reproject_layer.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_configure_reproject_layer.py
	install -m 755 src/scripts/oe_validate_configs.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/oe_validate_configs.py
	install -m 755 src/scripts/read_idx.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/read_idx.py
	install -m 755 src/scripts/read_mrf.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/read_mrf.py
	install -m 755 src/scripts/read_mrfdata.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/read_mrfdata.py
	install -m 755 src/scripts/twmsbox2wmts.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/twmsbox2wmts.py
	install -m 755 src/scripts/wmts2twmsbox.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/wmts2twmsbox.py
	install -m 755 src/colormaps/bin/colorMaptoHTML.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/colorMaptoHTML.py
	install -m 755 src/colormaps/bin/colorMaptoSLD.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/colorMaptoSLD.py
	install -m 755 src/colormaps/bin/SLDtoColorMap.py  \
		-D $(DESTDIR)/$(PREFIX)/bin/SLDtoColorMap.py

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/empty_tiles
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/apache/kml
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/vectorgen
	install -m 755 src/cgi/twms.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 src/cgi/wmts.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 src/cgi/wms.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	install -m 755 src/cgi/wfs.cgi \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	cp src/cgi/kml/* \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache/kml
	cp src/cgi/index.html \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/apache
	cp src/mrfgen/empty_tiles/* \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/empty_tiles

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/mrfgen
	cp src/mrfgen/empty_tiles/* \
		$(DESTDIR)/$(PREFIX)/share/onearth/mrfgen

	install -m 755 -d $(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/conf \
		$(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/layers \
		$(DESTDIR)/etc/onearth/config
	cp -r src/layer_config/reproject \
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
	
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/onearth/test
	cp -rL ../../../../src/test/* $(DESTDIR)/$(PREFIX)/share/onearth/test

	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/mpl
	cp -r build/mpl/* $(DESTDIR)/$(PREFIX)/share/mpl
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/cgicc
	cp -r build/cgicc/* $(DESTDIR)/$(PREFIX)/share/cgicc
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/lxml
	cp -r build/lxml/* $(DESTDIR)/$(PREFIX)/share/lxml
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/pyparsing
	cp -r build/pyparsing/* $(DESTDIR)/$(PREFIX)/share/pyparsing
	install -m 755 -d $(DESTDIR)/$(PREFIX)/share/parse_apache_configs
	cp -r build/parse_apache_configs/* $(DESTDIR)/$(PREFIX)/share/parse_apache_configs

	install -m 755 src/scripts/oe_utils.py \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/vectorgen
	install -m 755 src/vectorgen/*.py \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/vectorgen
	install -m 755 src/layer_config/conf/tilematrixsets.xml \
		-t $(DESTDIR)/$(PREFIX)/share/onearth/vectorgen
	ln -s ../share/onearth/vectorgen/oe_vectorgen.py $(DESTDIR)/$(PREFIX)/bin/oe_vectorgen

	install -m 755 -d $(DESTDIR)/$(LIB_PREFIX)/$(LIB_DIR)
	$(MAKE) install -C build/spatialindex

	# Install patched mod_proxy
	install -m 755 -d $(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_proxy
	cp -r /tmp/httpd/modules/mod_proxy* $(DESTDIR)/$(PREFIX)/$(LIB_DIR)/httpd/modules/mod_proxy
	rm -rf /tmp/httpd/

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
		src/modules/mod_onearth src/modules/mod_oetwms src/modules/mod_oems src/modules/mod_oemstime \
		src/modules/mod_receive/src src/modules/mod_reproject/src src/modules/mod_twms/src src/modules/mod_wmts_wrapper \
		src/scripts src/colormaps src/vectorgen src/layer_config src/mrfgen src/cgi src/demo src/test src/onearth_logs \
		src/generate_legend src/empty_tile GNUmakefile

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
		upstream/$(MPL_ARTIFACT) \
		upstream/$(CGICC_ARTIFACT) \
		upstream/$(SPATIALINDEX_ARTIFACT) \
		upstream/$(HTTPD_ARTIFACT) \
		upstream/$(MAPSERVER_ARTIFACT) \
		upstream/$(LXML_ARTIFACT) \
		upstream/$(PYPARSING_ARTIFACT) \
		upstream/$(PARSE_APACHE_CONFIGS_ARTIFACT) \
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
		dist/onearth*$(ONEARTH_VERSION)-*.src.rpm

#-----------------------------------------------------------------------------
# Clean
#-----------------------------------------------------------------------------
clean: onearth-clean
	rm -rf build

onearth-clean:
	# Reuse Makefile.lcl for external modules
	cp src/modules/mod_wmts_wrapper/Makefile.lcl src/modules/mod_receive/src/
	cp src/modules/mod_wmts_wrapper/Makefile.lcl src/modules/mod_reproject/src/
	cp src/modules/mod_wmts_wrapper/Makefile.lcl src/modules/mod_twms/src/
	
	$(MAKE) -C src/modules/mod_onearth clean
	$(MAKE) -C src/modules/mod_oetwms clean
	$(MAKE) -C src/modules/mod_oems clean
	$(MAKE) -C src/modules/mod_oemstime clean
	$(MAKE) -C src/modules/mod_receive/src clean
	$(MAKE) -C src/modules/mod_reproject/src clean
	$(MAKE) -C src/modules/mod_twms/src clean
	$(MAKE) -C src/modules/mod_wmts_wrapper clean

distclean: clean
	rm -rf dist
	rm -rf upstream


