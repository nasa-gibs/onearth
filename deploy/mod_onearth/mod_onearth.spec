Name:		mod_onearth
Version:	0.3.0
Release:	2%{?dist}
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


%install
rm -rf %{buildroot}
make mod_onearth-install PREFIX=%{_prefix} DESTDIR=%{buildroot}
install -m 755 -d %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/cgi/wmts.cgi \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/empty_tiles/black.jpg \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/empty_tiles/RGBA_512.png \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/empty_tiles/TransparentIDX.png \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
install -m 755 -d %{buildroot}/%{_sysconfdir}/httpd/conf.d
mv %{buildroot}/%{_datadir}/mod_onearth/demo/on_earth-demo.conf \
   %{buildroot}/%{_sysconfdir}/httpd/conf.d
touch %{buildroot}/%{_sysconfdir}/httpd/conf.d/on_earth-dit.conf


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%{_bindir}/*
%{_libdir}/httpd/modules/*
%dir %{_datadir}/mod_onearth
%{_datadir}/mod_onearth/cgi
%{_datadir}/mod_onearth/empty_tiles
%{_datadir}/mod_onearth/layer_config

%files demo
%defattr(-,root,root,-)
%{_datadir}/mod_onearth/demo
%config %{_sysconfdir}/httpd/conf.d/on_earth-demo.conf

%files dit
%defattr(-,gibsdev,gibsdev,-)
%config(noreplace) %{_sysconfdir}/httpd/conf.d/on_earth-dit.conf


%changelog
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
