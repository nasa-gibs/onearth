# generic stuff
yum install -q -y python3 dstat zstd

# development tools
yum install -q -y gcc gcc-c++ automake libtool

# various depenencies
yum install -q -y tcl zlib-devel libcurl-devel\
    libpng-devel libjpeg-devel libwebp-devel python3-devel openssl-devel\
    httpd-devel libzstd-devel

pip3 -q install boto3 pytest numpy

refresh() {
    project=$(basename $1)
    if [[ ! -d $project ]]
    then
        git clone -q $1
    # else
    #     (cd $project; git pull -q)
    fi
    if [[ ! -z "$2" ]]
    then
        (cd $project; git checkout -q $2)
    fi
}

export PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig

mkdir $HOME/src/modules
pushd $HOME/src/modules

# Prevent building cmake multiple times. Current version is 3.20
(command -v cmake > /dev/null && cmake --version | grep -q "version 3.2") || (
    refresh $GITHUB/Kitware/CMake v3.20.5
    pushd CMake
    ./bootstrap --prefix=$PREFIX --parallel=$NP
    make -j $NP
    $SUDO make install
    popd
    rm -rf CMake
)

# To previous folder
popd
