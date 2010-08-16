#!/bin/bash

topdir=/usr/src/packages
builddir=${topdir}/BUILD
rpmdir=${topdir}/RPMS
sourcedir=${topdir}/SOURCES
specdir=${topdir}/SPECS
srcrpmdir=${topdir}/SRPMS
packagename=$(basename rpm/*.spec .spec)
version=$(grep -i ^Version  rpm/${packagename}.spec | awk '{ print $2 }')
tmpdir=/tmp/${packagename}-${version}
cwd=$(pwd)
dir=${cwd}/$(dirname $0)

test -e $specdir || mkdir -p $specdir
test -e $sourcedir || mkdir -p $sourcedir
test -e $buildroot && rm -rf $buildroot

rpm/create_source.sh
cd $dir

mv /tmp/${packagename}-${version}.tar.bz2 ${sourcedir}/

cp ${packagename}.spec $specdir/
rpmbuild -ba $specdir/${packagename}.spec

cd $cwd
