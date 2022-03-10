# Build the gdal cgi image subseter
export ME=${ME:-lucianpls}
export THIS_PROJECT=AHTSE
export GITHUB=${GITHUB:-https://github.com}
export PREFIX=${PREFIX:-$HOME}

refresh() {
    project=$(basename $1)
    if [[ ! -d $project ]]
    then
        git clone -q $1
    else
        (cd $project; git pull -q)
    fi
    if [[ ! -z "$2" ]]
    then
        (cd $project; git checkout -q $2)
    fi
}

make_build() {
    pushd $1
    [[ -e ./configure ]] || ./autogen.sh
    [[ -e ./configure ]] && ./configure --prefix=$PREFIX
    make -j $NP 
    $SUDO make install
    make clean
    popd
}

NP=${NP:-$(nproc)}
pushd $HOME/src
export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig

sudo yum install -q -y mod_fcgid lua-devel

# CGICC
VER=3.2.19
wget -qO - http://ftp.gnu.org/gnu/cgicc/cgicc-$VER.tar.gz |tar -zxf -
make_build cgicc-$VER

# fcgi SDK, known release
VER=2.4.2
wget -qO - http://github.com/FastCGI-Archives/fcgi2/archive/refs/tags/$VER.tar.gz |tar -zxf -
make_build fcgi2-$VER

# Ready for gigi itself
refresh $GITHUB/$ME/gigi
# See gigi source for what make install does
make_build gigi

# From $HOME/src
popd
