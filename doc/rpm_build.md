# RPM Build

## Introduction

OnEarth and MRF RPMs are made available on GitHub: https://github.com/nasa-gibs/onearth/releases and https://github.com/nasa-gibs/mrf/releases

If a new RPM build is desired, these instructions describe how to build the following packages on CentOS 6 x86_64:

* gibs-gdal: The Geospatial Data Abstraction Library (GDAL) with the Meta Raster Format (MRF) plugin.
* onearth: OnEarth Apache module
* onearth-config: OnEarth configuration tools
* onearth-demo: A simple demo layer for the OnEarth Apache module
* onearth-mapserver: Apache modules that leverage MapServer for WMS and WFS services
* onearth-metrics: OnEarth custom log generator for creating metrics
* onearth-mrfgen: A tool used to help automate the generation of MRF files
* onearth-vectorgen: A tool used to help organize vectors files and generate vector tiles
* onearth-tools: Auxiliary tools for OnEarth such as a legend generator

## Quick Build Instructions (using Docker)

These instructions assume that Docker is installed and running.  On a Mac, you
can easily install Docker using [Docker Community Edition for Mac](https://store.docker.com/editions/community/docker-ce-desktop-mac).

The onearth RPMs are built inside of a Docker container which manages all of the
dependencies required in order to build the RPMs.  It is expected that the container
will be started from a Docker image that has the gibs-gdal RPMs installed already.
The name of that image is set in the **docker/el7/gibs-gdal-image.txt** file.

Once Docker is installed and running, the Enterprise Linux 7 RPMs can be built with:

```
./bin/build_el7_rpms_in_docker.sh
```

The generated RPMs will be written to the `dist` directory.

## Verbose Build Instructions

Some build and runtime dependencies require access to the Extra Packages for Enterprise Linux (EPEL) repository. Install the latest repository definition using the RPM found at the following location:

http://download.fedoraproject.org/pub/epel/6/i386/repoview/epel-release.html

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
make download gdal-rpm
```

Install the RPM:

```Shell
sudo yum -y install dist/gibs-gdal-*.el6.x86_64.rpm
```

The development package needs to be installed to build the remaining packages. This RPM should not be installed on production systems:

```Shell
sudo yum -y install dist/gibs-gdal-devel-*.el6.x86_64.rpm
```

Initialize onearth submodules:

```Shell
cd ../onearth
git submodule update --init --recursive
```

Install the build dependencies for onearth:

```Shell
sudo yum-builddep deploy/onearth/onearth.spec
```

Enable newer gcc compiler if using CentOS 6

```Shell
scl enable devtoolset-3 bash
```

Build the RPM:

```Shell
make download onearth-rpm
```

To install the OnEarth RPMs:

```Shell
sudo yum -y install dist/onearth-*.el6.x86_64.rpm dist/onearth-config-*.el6.noarch.rpm dist/onearth-demo-*.el6.noarch.rpm dist/onearth-metrics-*.el6.noarch.rpm dist/onearth-mrfgen-*.el6.x86_64.rpm dist/onearth-mapserver-*.el6.x86_64.rpm dist/onearth-vectorgen-*.el6.x86_64.rpm dist/onearth-tools-*.el6.noarch.rpm
```
