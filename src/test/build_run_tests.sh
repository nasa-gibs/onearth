#!/bin/sh

# INSTALL BASE DEPENDENCIES
#Install Apache and EPEL
sudo yum -y install epel-release httpd httpd-devel yum-utils rpmdevtools wget @buildsys-build tar
sudo yum groupinstall -y 'Development Tools' 

# INSTALL AND CONFIGURE SOFTWARE TO BE TESTED
mkdir /home/onearth
cd /home/onearth

# Clone and build MRF 1.0.0 RPMs, then install
git clone https://github.com/nasa-gibs/mrf.git
cd mrf
git checkout 1.0.0
sudo yum-builddep -y deploy/gibs-gdal/gibs-gdal.spec
make download gdal-rpm
sudo yum -y install dist/gibs-gdal-1.11.*.el6.x86_64.rpm
sudo yum -y install dist/gibs-gdal-devel-*.el6.x86_64.rpm 

# Clone OnEarth 'develop' branch, build RPMs, and install
cd /home/onearth
git clone https://github.com/nasa-gibs/onearth.git
cd onearth
git checkout develop
sudo yum-builddep -y deploy/onearth/onearth.spec
make download onearth-rpm
# sudo yum -y remove numpy
sudo yum -y install dist/onearth-*.el6.x86_64.rpm dist/onearth-config-*.el6.noarch.rpm dist/onearth-demo-*.el6.noarch.rpm dist/onearth-mrfgen-*.el6.x86_64.rpm
# yum -y remove gibs-gdal-devel
sudo ldconfig -v

#Set LCDIR
echo "export LCDIR=/etc/onearth/config" >> /home/onearth/.bashrc

#Set Apache to start when machine is restarted
sudo chkconfig --level 234 httpd on

# INSTALL TEST DEPENDENCIES
sudo yum install -y python3-devel
cd /home/onearth/onearth/src/test
sudo pip3 install -r requirements.txt

# RUN TESTS
sudo python3 /home/onearth/onearth/src/test/test_configure_layer.py >> /home/onearth/test_results/test_results.xml 3>&1 1>&2 2>&3
sudo python3 /home/onearth/onearth/src/test/test_mod_onearth.py >> /home/onearth/test_results/test_results.xml 3>&1 1>&2 2>&3
sudo python3 /home/onearth/onearth/src/test/test_mrfgen.py >> /home/onearth/test_results/test_results.xml 3>&1 1>&2 2>&3
