Name:		mod_onearth
Version:	1.0.0
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

%description demo
Demonstration of OnEarth


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
ln -s %{_datadir}/mod_onearth/blank_images/black.jpg \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/blank_images/RGBA_512.png \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
ln -s %{_datadir}/mod_onearth/blank_images/TransparentIDX.png \
   %{buildroot}/%{_datadir}/mod_onearth/demo/wmts
install -m 755 -d %{buildroot}/%{_sysconfdir}/httpd/conf.d
ln -s %{_datadir}/mod_onearth/demo/on_earth-demo.conf \
   %{buildroot}/%{_sysconfdir}/httpd/conf.d


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%{_bindir}/*
%{_libdir}/httpd/modules/*
%dir %{_datadir}/mod_onearth
%{_datadir}/mod_onearth/cgi
%{_datadir}/mod_onearth/blank_images

%files demo
%defattr(-,root,root,-)
%{_datadir}/mod_onearth/demo
%config %{_sysconfdir}/httpd/conf.d/on_earth-demo.conf


%changelog
* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.0.0-1
- Initial package
