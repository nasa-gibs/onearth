# RPM Build

## Introduction

OnEarth and MRF RPMs are made available on GitHub: https://github.com/nasa-gibs/onearth/releases and https://github.com/nasa-gibs/mrf/releases

If a new RPM build is desired, these instructions describe how to build the following packages on CentOS 6 x86_64:

* gibs-gdal: The Geospatial Data Abstraction Library (GDAL) with the Meta Raster Format (MRF) plugin.
* onearth: OnEarth Apache module
* onearth-config: OnEarth configuration tools (oe_configure_layer, oe_generate_legend, oe_generate_empty_tile)
* onearth-demo: A simple demo layer for the OnEarth Apache module
* onearth-metrics: OnEarth custom log generator for creating metrics
* onearth-mrfgen: A tool used to help automate the generation of MRF files

## Quick Build

Some build and runtime dependencies require access to the Extra Packages for Enterprise Linux (EPEL) repository. Install the latest repository definition using the RPM found at the following location:

http://download.fedoraproject.org/pub/epel/6/i386/repoview/epel-release.html

Some packages are built against PostgreSQL 9.2 and PostGIS 2. Install the latest repository definition using the RPM found at the following location:

http://yum.postgresql.org/repopackages.php#pg92

These packages are required or recommended for building:

* ccache: Speeds up rebuilds
* rpmdevtools: Needed to build RPMs
* mock: Used to verify RPM build dependencies
* wget: For downloading upstream sources

This group will install the baseline tools for building:

* buildsys-build

```Shell
sudo yum -y install ccache rpmdevtools mock wget @buildsys-build
```

Clone the onearth and mrf repositories from GitHub:

```Shell
git clone https://github.com/nasa-gibs/onearth.git
git clone https://github.com/nasa-gibs/mrf.git
```

Install the build dependencies for gibs-gdal:

```Shell
cd mrf
sudo yum-builddep deploy/gibs-gdal/gibs-gdal.spec
```

Download the GDAL source and build the RPM:

```Shell
make gdal-download gdal-rpm
```

Install the RPM:

```Shell
sudo yum -y install dist/gibs-gdal-1.11.*.el6.x86_64.rpm
```

The development package needs to be installed to build the remaining packages. This RPM should not be installed on production systems:

```Shell
sudo yum -y install dist/gibs-gdal-devel-*.el6.x86_64.rpm 
```

Install the build dependencies for onearth:

```Shell
cd ../onearth
sudo yum-builddep deploy/onearth/onearth.spec
```

Build the RPM:

```Shell
make download onearth-rpm
```

To install the OnEarth RPMs:

```Shell
sudo yum -y install dist/onearth-0.*.*-1.el6.x86_64.rpm onearth-config-0.*.*-1.el6.noarch.rpm onearth-demo-0.*.*-1.el6.noarch.rpm onearth-metrics-0.*.*-1.el6.noarch.rpm onearth-mrfgen-0.*.*-1.el6.x86_64.rpm
```
