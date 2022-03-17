# 
# For Amazon Linux 2, x64 or ARM
#

# GIT ID
export ME=lucianpls
export THIS_PROJECT=AHTSE
export GITHUB=https://github.com
export HOME=/home/oe2/onearth

yum install -q -y git

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

# Set PREFIX to /usr/local for system install
export PREFIX=/usr/local
mkdir $HOME/src/modules

# $SUDO to be used for install commands
if [[ $PREFIX =~ ^/usr ]]
then
SUDO=
else
SUDO=
fi

$SUDO mkdir $PREFIX/{bin,lib,include,modules}

# How many processors to use for compilation
export NP=$(nproc)
export PATH=$HOME/bin:$PATH
export LD_LIBRARY_PATH=$HOME/lib

pushd $HOME/src/modules

#refresh $GITHUB/$ME/$THIS_PROJECT
# Execute the updated scripts
. $HOME/src/modules/$THIS_PROJECT/devtools.bash
#. $HOME/src/$THIS_PROJECT/gdal.bash
. $HOME/src/modules/$THIS_PROJECT/ahtse.bash

# To previous folder
popd
