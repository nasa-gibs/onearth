# Assuming the ahtse components were built in the home folder (ie PREFIX=$HOME)
# build a tar with the files needed to produce a runtime instance
# Some system libraries might still be needed, for example libzstd
#

cd
rm -f bin/{cmake,ctest,cpack}
tar -zcf ec2-home-$(uname -p).tgz modules bin lib lib64 share/gdal share/proj include
