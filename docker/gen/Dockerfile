FROM lambci/lambda:build-provided

# Install deps

RUN \
  touch /var/lib/rpm/* \
  && yum install -y epel-release
RUN \
    yum install -y gcc-c++-4.8.3 libtool-2.4.2 pkgconfig-0.27.1 libpng-devel-1.2.49 giflib-devel-4.1.6 libtiff-devel-4.0.3 \
    jpackage-utils-1.7.5 jasper-devel-1.900.1 sqlite-devel-3.7.17 sqlite-3.7.17 turbojpeg-1.2.90 turbojpeg-devel-1.2.90 agg-2.5 agg-devel-2.5 \
    libxslt-devel-1.1.28 chrpath-0.13 zlib-devel-1.2.8 curl-devel-7.51.0 swig-2.0.10 doxygen-1.8.2 expat-devel-2.1.0 geos-3.4.2 geos-devel-3.4.2

# Install mrfgen and OnEarth utils dependencies
RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
RUN python get-pip.py
RUN pip install apacheconfig==0.2.8
RUN pip install numpy==1.10.4
RUN rm get-pip.py
	
# Fetch PROJ.4

RUN \
  curl -L http://download.osgeo.org/proj/proj-4.9.3.tar.gz | tar zxf - -C /tmp

# Build and install PROJ.4

WORKDIR /tmp/proj-4.9.3

RUN \
  ./configure \
    --prefix=/var/task && \
  make -j $(nproc) && \
  make install

# Fetch GDAL

RUN \
  mkdir -p /tmp/gdal-dev && \
  curl -L http://download.osgeo.org/gdal/2.1.4/gdal-2.1.4.tar.gz | tar zxf - -C /tmp/gdal-dev --strip-components=1

# Build + install GDAL

WORKDIR /tmp/gdal-dev

RUN \
  ./configure \
    --prefix=/var/task \
    --datarootdir=/var/task/share/gdal \
	--with-threads \
	--without-bsb \
	--with-libtiff=internal \
	--without-ogdi \
	--with-libz \
	--with-geos \
	--with-jasper \
	--with-png \
	--with-gif \
	--with-jpeg \
	--with-sqlite3 \
	--with-curl \
	--with-python=yes \
	--with-pcraster \
	--with-jpeg12=no \
	--disable-rpath \
	--with-expat && \
  make -j $(nproc) && \
  make install

WORKDIR /tmp/gdal-dev/swig/python

RUN \
  python setup.py install && \
  cp /usr/lib64/libpython2.7.so.1.0 /var/task/lib64/python2.7/site-packages

RUN \
  cp -r /usr/local/lib64/python2.7/site-packages/GDAL-2.1.4-py2.7-linux-x86_64.egg/osgeo /var/task/lib64/python2.7/site-packages

WORKDIR /tmp/mrf-dev

# Build mrf_insert from GIBS
RUN \
  git clone --branch v1.1.2 --depth 1 https://github.com/nasa-gibs/mrf.git && \
  mv mrf/src/gdal_mrf/mrf_apps /tmp/gdal-dev/ && \
  cd /tmp/gdal-dev/mrf_apps && \
  make && \
  mv .libs/mrf_insert /var/task/bin/mrf_insert

# Install vectorgen dependencies
WORKDIR /tmp
RUN curl -L http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz | tar xzf - -C /tmp
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig
RUN pip install Fiona==1.8.4 Shapely==1.5.16 Rtree==0.8.3 mapbox-vector-tile==0.4.0 lxml==3.8.0

# Build mrfgen/vectorgen from nasa-gibs
WORKDIR /tmp/gen-dev
RUN \
  git clone --branch 2.2.1  --depth 1 https://github.com/nasa-gibs/onearth.git && \
  mv onearth/src/mrfgen/*.py /var/task/bin/ && \
  mv onearth/src/mrfgen/RGBApng2Palpng.c /var/task/bin/ && \
  mv onearth/src/vectorgen/*.py /var/task/bin/ && \
  mv onearth/src/scripts/*.py /var/task/bin/ && \
  mv onearth/src/generate_legend/*.py /var/task/bin/ && \
  mv onearth/src/colormaps/bin/*.py /var/task/bin/

# Build RGBApng2Palpng
WORKDIR /var/task/bin
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng
RUN rm RGBApng2Palpng.c

# Clean up
WORKDIR /var/task
RUN \
  strip lib/libgdal.so.20.* && \
  strip lib/libproj.so.12.*
RUN rm -rf /tmp/*