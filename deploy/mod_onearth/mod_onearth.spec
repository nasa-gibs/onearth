Name:		mod_onearth
Version:	0.3.3
Release:	1%{?dist}
Summary:	Apache module for OnEarth

License:	ASL 2.0+
URL:		http://earthdata.nasa.gov
Source0:	%{name}-%{version}.tar.bz2

BuildRequires:	httpd-devel
BuildRequires:	chrpath
BuildRequires:	gibs-gdal-devel
BuildRequires:	postgresql92-devel
Requires:	httpd
Requires:	gibs-gdal

Obsoletes:	mod_twms mod_wms

%description
Apache module for OnEarth


%package demo
Summary:	Demonstration of OnEarth
Requires:	%{name} = %{version}-%{release}
BuildArch:	noarch

%description demo
Demonstration of OnEarth


%package dit
Summary:	DIT environment
Requires:	%{name} = %{version}-%{release}
BuildArch:	noarch

%description dit
DIT environment


%prep
%setup -q


%build
make mod_onearth PREFIX=%{_prefix}


%install demo
rm -rf %{buildroot}
make mod_onearth-install PREFIX=%{_prefix} DESTDIR=%{buildroot}
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/cgi/wmts.cgi \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/empty_tiles/black.jpg \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/empty_tiles/RGBA_512.png \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
ln -s %{_datadir}/onearth/empty_tiles/TransparentIDX.png \
   %{buildroot}/%{_datadir}/onearth/demo/wmts-geo
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/wmts-geo/1.0.0
install -m 755 -d %{buildroot}/%{_sysconfdir}/httpd/conf.d
mv %{buildroot}/%{_datadir}/onearth/demo/on_earth-demo.conf \
   %{buildroot}/%{_sysconfdir}/httpd/conf.d
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo
install -m 755 -d %{buildroot}/%{_datadir}/onearth/demo/twms-geo/.lib


%clean
rm -rf %{buildroot}


%files
%defattr(755,root,root,-)
%{_bindir}/*
%{_libdir}/httpd/modules/*
%defattr(-,gibs,gibs,775)
%dir %{_datadir}/onearth
%defattr(664,gibs,gibs,775)
%{_datadir}/onearth/cgi
%{_datadir}/onearth/empty_tiles
%{_datadir}/onearth/onearth_logs
%{_datadir}/onearth/layer_config

%files demo
%defattr(-,gibs,gibs,-)
%{_datadir}/onearth/demo
%config %{_sysconfdir}/httpd/conf.d/on_earth-demo.conf


%changelog
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

* Thu Feb 13 2014 Joe T. Roberts <joe.t.roberts@jpl.nasa.gov> - 1.0.0-2
- Changed to release 0.2

* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.0.0-1
- Initial package
