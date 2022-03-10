ARCH=$(uname -p)
sudo yum install -y yum-utils rpmdevtools
yumdownloader --source httpd.$ARCH
file=$(echo httpd-*.amzn2.src.rpm)
rpm -i $file
sudo yum-builddep -y $file

cp mod_proxy_http_subreq_connection_reuse.patch rpmbuild/SOURCES
cp proxypass_nomain_flag.patch rpmbuild/SOURCES
patch -p1 -d rpmbuild <httpd_spec.patch

rpmbuild -bb rpmbuild/SPECS/httpd.spec

# This part fails because there is a circular dependency between
# httpd and mod_http2
# 
# rpm -i rpmbuild/RPMS/$ARCH/httpd-* rpmbuild/RPMS/$ARCH/mod_proxy_* 
#

# So we just overwrite the existing modules with the patched ones

sudo yum -qy install httpd httpd-devel
find rpmbuild -name mod_proxy.so -exec sudo cp \{} /etc/httpd/modules
find rpmbuild -name mod_proxy_http.so -exec sudo cp \{} /etc/httpd/modules
