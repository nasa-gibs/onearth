%global gdal_version 1.10.1
%global gdal_release 2%{?dist}
%global mrf_version 1.1.1
%global mrf_release 2%{?dist}

Name:		gibs-gdal
Version:	%{gdal_version}
Release:	%{gdal_release}
Summary:	GIS file format library

Group:		System Environment/Libraries
License:	MIT
URL:		http://www.gdal.org/
Source0:	gibs-gdal-%{gdal_version}.tar.bz2
Source1:	http://download.osgeo.org/gdal/%{gdal_version}/gdal-%{gdal_version}.tar.gz

BuildRequires:	libtool pkgconfig
BuildRequires:	python-devel numpy xerces-c-devel
BuildRequires:	libpng-devel libungif-devel
BuildRequires:	libjpeg-devel
BuildRequires:	libtiff-devel
BuildRequires:	jpackage-utils
BuildRequires:	jasper-devel cfitsio-devel libdap-devel librx-devel 
BuildRequires:	hdf-static hdf-devel
BuildRequires:	unixODBC-devel mysql-devel sqlite-devel 
BuildRequires:	postgresql92-devel postgis2_92-devel
BuildRequires:	zlib-devel
BuildRequires:	proj-devel geos-devel netcdf-devel hdf5-devel ogdi-devel 
BuildRequires:	libgeotiff-devel
BuildRequires:	curl-devel
BuildRequires:	perl(ExtUtils::MakeMaker)
BuildRequires:	chrpath
BuildRequires:	swig 
BuildRequires:	doxygen
BuildRequires:	expat-devel
Requires:	proj-devel

Provides:	gdal = %{gdal_version}-%{gdal_release}
Obsoletes:	gdal < 1.10
Provides:	gdal-python = %{gdal_version}-%{gdal_release}
Obsoletes:	gdal-python < 1.10
	
%description
The GDAL library provides support to handle multiple GIS file formats.

This build includes the MRF plug-in for GIBS.


%package devel
Summary:	Development libraries for the GDAL library
Group:		Development/Libraries               
Requires:	%{name} = %{gdal_version}-%{gdal_release}

%description devel
Development libraries for the GDAL library


%package plugin-mrf
Summary:	Plugin for the MRF raster file format
Group:		Development/Libraries
Requires:	%{name} = %{gdal_version}-%{gdal_release}
Version:	%{mrf_version}
Release:	%{mrf_release}

%description plugin-mrf
Plugin for the MRF raster file format


%prep
%setup -q
mkdir upstream
cp %{SOURCE1} upstream


%build
make gdal PREFIX=/usr


%install
rm -rf %{buildroot}
make gdal-install DESTDIR=%{buildroot} PREFIX=/usr

# Man files are not being placed in the correct location
install -m 755 -d %{buildroot}/%{_mandir}
mv %{buildroot}/usr/man/* %{buildroot}/%{_mandir}

# Remove documentation that somehow made it into the bin directory
rm -f %{buildroot}/%{_bindir}/*.dox

# gdal doesn't respect the lib64 directory
install -m 755 -d %{buildroot}/usr/lib/gdalplugins
install -m 755 build/gdal/frmts/mrf/gdal_mrf.so.1 \
        %{buildroot}/usr/lib/gdalplugins
ln -s gdal_mrf.so.1 %{buildroot}/usr/lib/gdalplugins/gdal_mrf.so

# Remove SWIG samples
rm -rf swig/python/samples


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc build/gdal/COMMITERS 
%doc build/gdal/LICENSE.TXT 
%doc build/gdal/NEWS 
%doc build/gdal/PROVENANCE.TXT
%doc build/gdal/VERSION
%{_bindir}/*
%exclude %{_bindir}/mrf_insert
%exclude %{_bindir}/gdal-config
%{_libdir}/*.so.*
%{_datadir}/gdal
%{_mandir}/man1/*.1*
%{python_sitearch}/*.egg-info
%{python_sitearch}/gdal*
%{python_sitearch}/ogr*
%{python_sitearch}/osr*
%{python_sitearch}/osgeo
%dir /usr/lib/gdalplugins

%files devel
%defattr(-,root,root,-)
%{_bindir}/gdal-config
%{_includedir}/*
%{_libdir}/*.a
%{_libdir}/*.la
%{_libdir}/*.so

%files plugin-mrf
%defattr(-,root,root,-)
%{_bindir}/mrf_insert
/usr/lib/gdalplugins/*


%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig


%changelog
* Thu Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.1-2
- Rebuild with PostgreSQL 9.2 and Expat support
- Added correct Obsoletes/Provides for devel package

* Wed Sep 4 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.1-1
- New upstream version
- Rebuild with official MRF code

* Fri Aug 23 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-7
- Obsoletes/Provides now correct and includes gdal-python

* Wed Jul 24 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-6
- Corrections for mrf_insert from Lucian.

* Wed Jul 11 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-5
- Link failure discovered in chroot build. Back to dynamic linking of
  proj with a dependency on the devel package.

* Mon Jul 8 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-4
- Statically linking libproj for now since it is looking for the non-versioned
  shared object that is in the devel package.
- Added Lucian artifact which adds insert support for MRFs.

* Thu Jun 6 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-3
- Split out MRF plugin into a separate package.

* Sat May 11 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-2
- Combined python package into main since it is required to run many of
  the gdal utilities.

* Wed Apr 24 2013 Mike McGann <mike.mcgann@nasa.gov> - 1.10.0-1
- Initial package
