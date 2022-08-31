# This Dockerfile must be run from source root

FROM centos:7

# Copy mrfgen/vectorgen
RUN mkdir -p /var/task/bin
COPY ./src/mrfgen/*.py /var/task/bin/
COPY ./src/mrfgen/RGBApng2Palpng.c /var/task/bin/
COPY ./src/vectorgen/*.py /var/task/bin/
COPY ./src/scripts/*.py /var/task/bin/
COPY ./src/empty_tile/*.py /var/task/bin/
COPY ./src/generate_legend/*.py /var/task/bin/
COPY ./src/colormaps/bin/*.py /var/task/bin/

WORKDIR /tmp
RUN touch /var/lib/rpm/* && \
	yum install -y epel-release python3-devel make libpng-devel

# Install GDAL
RUN yum install -y turbojpeg-1.2.90 turbojpeg-devel-1.2.90
RUN yum groupinstall -y "Development Tools"
RUN yum install -y "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-3/gibs-gdal-2.4.4-3.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-3/gibs-gdal-devel-2.4.4-3.el7.x86_64.rpm" "https://github.com/nasa-gibs/mrf/releases/download/v2.4.4-3/gibs-gdal-apps-2.4.4-3.el7.x86_64.rpm" && \
	yum clean all
RUN pip3 install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

# Copy binaries and libs
RUN cp /usr/bin/*mrf* /var/task/bin
RUN cp /usr/bin/epsg_tr.py /var/task/bin
RUN cp /usr/bin/esri2wkt.py /var/task/bin
RUN cp /usr/bin/gcps2vec.py /var/task/bin
RUN cp /usr/bin/gcps2wld.py /var/task/bin
RUN cp /usr/bin/gdal* /var/task/bin
RUN cp /usr/bin/gnmanalyse /var/task/bin
RUN cp /usr/bin/gnmmanage /var/task/bin
RUN cp /usr/bin/mkgraticule.py /var/task/bin
RUN cp /usr/bin/nearblack /var/task/bin
RUN cp /usr/bin/ogr* /var/task/bin
RUN cp /usr/bin/pct2rgb.py /var/task/bin
RUN cp /usr/bin/rgb2pct.py /var/task/bin
RUN cp /usr/bin/testepsg /var/task/bin
RUN mkdir /var/task/lib64/
RUN cp /usr/lib64/libgdal.so.20 /var/task/lib64/
RUN cp /usr/lib64/libgeos-3.4.2.so /var/task/lib64/
RUN cp /usr/lib64/libgeos_c.so.1 /var/task/lib64/
RUN mkdir /var/task/lib64/pkgconfig
RUN cp /usr/lib64/pkgconfig/gdal.pc /var/task/lib64/pkgconfig
RUN mkdir -p /var/task/share/gdal/
RUN cp -R /usr/share/gdal/* /var/task/share/gdal/

ENV GDAL_DATA=/var/task/gdal
#ENV PYTHONPATH=${PYTHONPATH}:/var/task/lib64/python2.7/site-packages:/var/task/lib/python2.7/site-packages
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/var/task/lib64:/var/task/lib
ENV PATH=$PATH:/var/task/bin

# Install mrfgen and OnEarth utils dependencies
RUN pip3 install --prefix=/var/task --ignore-installed apacheconfig==0.2.8
RUN pip3 install --ignore-installed apacheconfig==0.2.8
RUN pip3 install --prefix=/var/task --ignore-installed numpy==1.16.6
RUN pip3 install --ignore-installed numpy==1.16.6

# Fetch PROJ.4
RUN curl -L http://download.osgeo.org/proj/proj-4.9.3.tar.gz | tar zxf - -C /tmp

# Build and install PROJ.4
WORKDIR /tmp/proj-4.9.3
RUN \
  ./configure \
    --prefix=/var/task && \
  make -j $(nproc) && \
  make install

# Install vectorgen dependencies
WORKDIR /tmp
RUN curl -L http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz | tar xzf - -C /tmp
WORKDIR /tmp/spatialindex-src-1.8.5
RUN ./configure --libdir=/usr/lib64
RUN make && make install
RUN ldconfig
RUN pip3 install wheel==0.37.1
RUN pip3 install --prefix=/var/task --ignore-installed Fiona==1.8.19 Shapely==1.5.16 Rtree==0.9.7 mapbox_vector_tile==1.2.1 lxml==4.9.1 protobuf==3.19.4
RUN pip3 install --ignore-installed Fiona==1.8.19 Shapely==1.5.16 Rtree==0.9.7 mapbox_vector_tile==1.2.1 lxml==4.9.1 protobuf==3.19.4
# TODO: Sort out weirdness with some dependencies expecting specific lib locations
RUN cp /usr/lib64/libspatialindex*so* /var/task/lib64/
RUN pip3 uninstall -y protobuf && pip3 install protobuf==3.19.4

RUN pip3 install matplotlib==2.2.5
RUN pip3 install pypng==0.0.20

RUN mkdir -p /var/task/lib64/python2.7/site-packages
RUN cp -R /usr/lib64/python2.7/site-packages/* /var/task/lib64/python2.7/site-packages

# Build RGBApng2Palpng
WORKDIR /var/task/bin
RUN gcc -O3 RGBApng2Palpng.c -o RGBApng2Palpng -lpng
RUN rm RGBApng2Palpng.c

# Clean up
WORKDIR /var/task
RUN \
  strip lib64/libgdal.so.20* && \
  strip lib64/libgeos* && \
  strip lib64/libspatialindex*so* && \
  strip lib/libproj.so.12.*
RUN yum remove -y gibs-gdal
RUN rm -rf /tmp/*

# Set the locale
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Add non-root user
RUN groupadd dockeruser && useradd -g dockeruser dockeruser
RUN chown -hR dockeruser:dockeruser /var/task && chown -hR dockeruser:dockeruser /var/log && chmod 1777 /tmp

# Change user
USER dockeruser

ARG ONEARTH_VERSION
ENV ONEARTH_VERSION=$ONEARTH_VERSION
