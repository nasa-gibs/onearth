WORKING_DIR=$PWD

setup_dependencies() {
    yum groupinstall -y "Development Tools"
    yum install -y epel-release lua-devel jansson-devel httpd-devel libpng-devel libjpeg-devel pcre-devel mod_proxy mod_ssl wget 
    yum install -y luarocks redis
}

setup_mod_receive() {
    cp Makefile.lcl ../modules/mod_receive/src/
    cd ../modules/mod_receive/src/
    make && make install
    if [[ ! -f /lib64/httpd/modules/mod_receive.so || ! -f /usr/include/httpd/receive_context.h ]]
    then
        echo "ERROR: mod_receive install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_mod_mrf() {
    pwd
    cp Makefile.lcl ../modules/mod_mrf/src/
    cd ../modules/mod_mrf/src/
    make && make install
    if [ ! -f /lib64/httpd/modules/mod_receive.so ] 
    then
        echo "ERROR: mod_mrf install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_mod_reproject() {
    cp Makefile.lcl ../modules/mod_reproject/src/
    cd ../modules/mod_reproject/src/
    make && make install
    if [ ! -f /lib64/httpd/modules/mod_reproject.so ] 
    then
        echo "ERROR: mod_reproject install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_mod_twms() {
    cp Makefile.lcl ../modules/mod_twms/src/
    cd ../modules/mod_twms/src/
    make && make install
    if [ ! -f /lib64/httpd/modules/mod_twms.so ] 
    then
        echo "ERROR: mod_twms install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_mod_wmts_wrapper() {
    cp Makefile.lcl ../modules/mod_wmts_wrapper/
    cd ../modules/mod_wmts_wrapper/
    cp ../mod_reproject/src/mod_reproject.h .
    make && make install
    if [ ! -f /lib64/httpd/modules/mod_reproject.so ] 
    then
        echo "ERROR: mod_mrf install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_mod_ahtse_lua() {
    cp Makefile.lcl ../modules/mod_ahtse_lua/src/
    cd ../modules/mod_ahtse_lua/src
    make && make install
    if [ ! -f /lib64/httpd/modules/mod_ahtse_lua.so ] 
    then
        echo "ERROR: mod_ahtse_lua install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

setup_time_snap() {
    cd ../modules/time_snap/redis-lua
    luarocks make rockspec/redis-lua-2.0.5-0.rockspec
    if [ ! -d /usr/lib64/luarocks/rocks/redis-lua ] 
    then
        echo "ERROR: redis-lua install failed" >&2
    fi    
    cd ..
    luarocks make onearth-0.1-1.rockspec
    if [ ! -d /usr/lib64/luarocks/rocks/onearth ] 
    then
        echo "ERROR: onearth-lua install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

patch_mod_proxy() {
    cd /tmp
    wget https://archive.apache.org/dist/httpd/httpd-2.4.6.tar.gz
    tar xf httpd-2.4.6.tar.gz
    cd httpd-2.4.6/modules/proxy
    patch < $WORKING_DIR/mod_proxy_http.patch
    cd ../../
    ./configure --prefix=/tmp/httpd --enable-proxy=shared --enable-proxy-balancer=shared 
    make && make install
    cp /tmp/httpd/modules/mod_proxy* /lib64/httpd/modules
    MD5=($(md5sum /lib64/httpd/modules/mod_proxy_http.so))
    if [ "$MD5" != "9392e8d6e70a3e06f0eb574814dda597" ] 
    then
        echo "ERROR: patched mod_proxy install failed" >&2
        ERR=1
    fi
    cd $WORKING_DIR
}

patch_apr() {
    cd /tmp
    wget http://apache.osuosl.org//apr/apr-1.6.3.tar.gz
    tar xf apr-1.6.3.tar.gz
    cd apr-1.6.3
    patch  -p2 < $WORKING_DIR/../modules/mod_mrf/apr_FOPEN_RANDOM.patch
    ./configure --prefix=/lib64
    make && make install
    # TODO: how can we test for patched APR install?
    cd $WORKING_DIR
}

# Run install
setup_dependencies
setup_mod_receive
setup_mod_mrf
setup_mod_reproject
setup_mod_twms
setup_mod_ahtse_lua
setup_mod_wmts_wrapper
setup_time_snap
patch_mod_proxy
patch_apr

if [ -z "$ERR" ]
then
    echo "No errors found, tests passed!"
else
    echo "Install errors found -- check stderr for error messages"
fi