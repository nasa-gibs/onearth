Name:		onearth
Version:	1.1.0
Release:	1%{?dist}
Summary:	Installation packages for OnEarth

License:	ASL 2.0+
URL:		http://earthdata.nasa.gov
Source0:	%{name}-%{version}.tar.bz2
Source1:	https://pypi.python.org/packages/source/m/matplotlib/matplotlib-1.5.1.tar.gz
Source2:	http://ftp.gnu.org/gnu/cgicc/cgicc-3.2.16.tar.gz
Source3:	http://download.osgeo.org/mapserver/mapserver-7.0.1.tar.gz

BuildRequires:	httpd-devel
BuildRequires:	chrpath
BuildRequires:	gibs-gdal-devel
BuildRequires:	libpng-devel
BuildRequires:	gcc-c++
BuildRequires:	freetype-devel
BuildRequires:	python-devel
BuildRequires:  sqlite-devel
BuildRequires:	cmake
Requires:	httpd
Requires:	gibs-gdal
Requires:   sqlite

Obsoletes:	mod_twms mod_onearth mod_oems mod_oemstime

%description
Installation packages for OnEarth


%package demo
Summary:	Demonstration of OnEarth
Requires:	%{name} = %{version}-%{release}
BuildArch:	noarch

%description demo
Demonstration of OnEarth


%package metrics
Summary:	OnEarth log tool for metrics
BuildArch:	noarch

%description metrics
OnEarth log tool for metrics


%package mrfgen
Summary:	MRF generator for OnEarth
Requires:	gibs-gdal

%description mrfgen
MRF generator for OnEarth


%package config
Summary:	Layer configuration tools for OnEarth
Requires:	%{name} = %{version}-%{release}
Requires:	libpng-devel
Requires:	chrpath
Requires:	gcc-c++
Requires:	agg
Requires:	agg-devel
Requires:	pyparsing
Requires:	python-devel
Requires:	python-tornado
Requires:	python-pycxx-devel
Requires:	python-dateutil
Requires:	python-pypng
Requires:	python-lxml
Requires:	python-nose
Requires:   python-unittest2
Requires:	freetype-devel
Requires:	gibs-gdal > 0.9.0
BuildArch:	noarch
Provides:	python-matplotlib = 1.5.1
Obsoletes:	python-matplotlib < 1.5.1

%description config
Layer configuration tools for OnEarth including Legend Generator

%package mapserver
Summary:	Mapserver for OnEarth
Requires:   proj-epsg
Provides:	mapserver = %{version}-%{release}
Obsoletes:	mapserver < 7.0.1

%description mapserver
Mapserver package utilized by OnEarth for WMS and WFS services

%global python_sitearch %(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")

%prep
%setup -q
mkdir upstream
cp %{SOURCE1} upstream
cp %{SOURCE2} upstream
cp %{SOURCE3} upstream

%build
make onearth PREFIX=%{_prefix}
cd build/mapserver
mkdir build
cd build
cmake \
      -DCMAKE_INSTALL_PREFIX="%{_prefix}" \
      -DWITH_GD=1 \
      -DWITH_GIF=1 \
      -DWITH_GDAL=1 \
      -DWITH_OGR=1 \
      -DWITH_GEOS=1 \
      -DWITH_CAIRO=0 \
      -DWITH_PROJ=1 \
      -DWITH_KML=1 \
      -DWITH_WMS=1 \
      -DWITH_WFS=1 \
      -DWITH_WCS=1 \
      -DWITH_SOS=1 \
      -DWITH_CLIENT_WMS=1 \
      -DWITH_CLIENT_WFS=1 \
      -DWITH_POSTGIS=0 \
      -DWITH_CURL=1 \
      -DWITH_LIBXML2=1 \
      -DWITH_PHP=0 \
      -DWITH_FRIBIDI=0 \
      -DWITH_FCGI=0 \
      -DWITH_THREAD_SAFETY=1 \
      -DWITH_PYTHON=1 \
      -DWITH_ICONV=1 \
      -DWITH_HARFBUZZ=0 \
      ..
make %{?smp_flags}

%install
rm -rf %{buildroot}
make onearth-install PREFIX=%{_prefix} DESTDIR=%{buildroot}
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/apache/wmts.cgi \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/empty_tiles/Blank_RGB_512.jpg \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo/black.jpg
ln -s %{_datadir}/onearth/empty_tiles/Blank_RGBA_512.png \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo/transparent.png
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo/1.0.0
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo/.lib
ln -s %{_datadir}/onearth/apache/twms.cgi \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo
ln -s %{_datadir}/onearth/empty_tiles/Blank_RGB_512.jpg \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo/black.jpg
ln -s %{_datadir}/onearth/empty_tiles/Blank_RGBA_512.png \
   %{buildroot}/%{_datadir}/onearth/demo/twms-geo/transparent.png
install -m 755 -d %{buildroot}/%{_sysconfdir}/httpd/conf.d
mv %{buildroot}/%{_datadir}/onearth/demo/on_earth-demo.conf \
   %{buildroot}/%{_sysconfdir}/httpd/conf.d

( cd build/mapserver/build; DESTDIR=%{buildroot} make install )
mv %{buildroot}/%{_libdir}/../lib/* %{buildroot}/%{_libdir}/
chrpath --delete %{buildroot}/%{_bindir}/legend
chrpath --delete %{buildroot}/%{_bindir}/mapserv
chrpath --delete %{buildroot}/%{_bindir}/msencrypt
chrpath --delete %{buildroot}/%{_bindir}/scalebar
chrpath --delete %{buildroot}/%{_bindir}/shp2img
chrpath --delete %{buildroot}/%{_bindir}/shptree
chrpath --delete %{buildroot}/%{_bindir}/shptreetst
chrpath --delete %{buildroot}/%{_bindir}/shptreevis
chrpath --delete %{buildroot}/%{_bindir}/sortshp
chrpath --delete %{buildroot}/%{_bindir}/tile4ms
chrpath --delete %{buildroot}/%{_libdir}/*.so
rm -rf %{buildroot}/%{_datarootdir}/mapserver/cmake/

%clean
rm -rf %{buildroot}

%files
%{_libdir}/httpd/modules/*
%defattr(-,gibs,gibs,775)
%dir %{_datadir}/onearth
%defattr(775,gibs,gibs,775)
%{_datadir}/onearth/apache
%{_datadir}/onearth/empty_tiles
%defattr(755,root,root,-)
%{_bindir}/oe_create_cache_config
%{_datadir}/cgicc

%post
cd %{_datadir}/cgicc/
%{_datadir}/cgicc/configure --prefix=/usr
make install

%files config
%defattr(664,gibs,gibs,775)
%{_sysconfdir}/onearth/config/
%config(noreplace) %{_sysconfdir}/onearth/config/conf
%config(noreplace) %{_sysconfdir}/onearth/config/layers
%config(noreplace) %{_sysconfdir}/onearth/config/headers
%config(noreplace) %{_sysconfdir}/onearth/config/mapserver
%{_sysconfdir}/onearth/config/schema
%defattr(755,root,root,-)
%{_bindir}/oe_configure_layer
%{_bindir}/oe_generate_legend.py
%{_bindir}/oe_generate_empty_tile.py
%{_datadir}/mpl

%post config		
cd %{_datadir}/mpl/		
python setup.py build		
python setup.py install

%files mrfgen
%defattr(664,gibs,gibs,775)
%{_datadir}/onearth/mrfgen
%defattr(755,root,root,-)
%{_bindir}/RGBApng2Palpng
%{_bindir}/mrfgen
%{_bindir}/colormap2vrt.py

%files metrics
%defattr(664,gibs,gibs,775)
%{_sysconfdir}/onearth/metrics
%defattr(755,root,root,-)
%{_bindir}/onearth_metrics

%files demo
%defattr(-,gibs,gibs,-)
%{_datadir}/onearth/demo
%config(noreplace) %{_sysconfdir}/httpd/conf.d/on_earth-demo.conf

%post demo
cd %{_datadir}/onearth/apache/kml
make WEB_HOST=localhost/onearth/demo-twms
mv %{_datadir}/onearth/apache/kml/kmlgen.cgi \
   %{_datadir}/onearth/demo/twms-geo
mkdir %{_datadir}/onearth/demo/wms
ln -s %{_bindir}/mapserv %{_datadir}/onearth/demo/wms/mapserv

%files mapserver
%defattr(755,root,root,-)
%{_libdir}/libmapserver.so*
%{_includedir}/mapserver/*
%{python_sitearch}/_mapscript*
%{python_sitearch}/mapscript*
%{_bindir}/legend
%{_bindir}/mapserv
%{_bindir}/msencrypt
%{_bindir}/scalebar
%{_bindir}/shp2img
%{_bindir}/shptree
%{_bindir}/shptreetst
%{_bindir}/shptreevis
%{_bindir}/sortshp
%{_bindir}/tile4ms

%changelog
* Wed Aug 17 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.1.0-1
- Added onearth-mapserver package, mod_oems, and mod_oemstime

* Fri Jul 15 2016 Joshua D. Rodriguez <joshua.d.rodriguez@jpl.nasa.gov> - 1.0.2-1
- Updated Matplotlib dependency install to 1.5.1

* Wed May 25 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.0.1-1
- Modified empty tiles

* Tue Mar 8 2016 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.9.1-1
- Removed numpy as it is included in gibs-gdal

* Wed Nov 11 2015 Joshua Rodriguez <joshua.d.rodriguez@jpl.nasa.gov> - 0.8.0-1
- Added creation of kml/twms endpoint

* Wed Nov 4 2015 Joshua Rodriguez <joshua.d.rodriguez@jpl.nasa.gov> - 0.8.0-1
- Remove Postgres dependencies

* Mon Aug 10 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.7.0-1
- Added requires for sqlite

* Tue Mar 24 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.3-2
- Added installation of cgicc for kmlgen

* Thu Feb 12 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.3-1
- Updated BuildRequires and config package Requires

* Thu Jan 29 2015 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.2-1
- Updated dependencies including downloads for numpy and matplotlib

* Mon Nov 24 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.6.1-1
- Added oe_generate_empty_tile and missing python dependencies

* Fri Oct 03 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.5.0-1
- Removed deprecated OnEarth layer configuration files and folders

* Mon Aug 18 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.4.2-1
- Reorganized into separate packages for different components

* Fri Aug 8 2014 Mike McGann <mike.mcgann@nasa.gov> - 0.4.1-2
- Updates for building on EL7

* Mon Jul 28 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.4.1-1
- Added noreplace options to configuration directories

* Wed May 14 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.2-1
- Renamed mod_onearth directory to onearth and added TWMS directories

* Wed Apr 30 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.1-1
- Changed the version to 0.3.1

* Fri Apr 4 2014 Mike McGann <mike.mcgann@nasa.gov> - 0.3.0-2
- Included layer_config in package

* Tue Apr 1 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.3.0-1
- Changed the version to 0.3.0

* Wed Feb 26 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.2.5-1
- Changed the version to 0.2.5

* Tue Feb 18 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.2.4-1
- Changed the version to 0.2.4 to be consistent with project release

* Thu Feb 13 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 0.0.0-2
- Changed to release 0.2

* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 0.0.0-1
- Initial package
