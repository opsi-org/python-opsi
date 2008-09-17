#!/bin/bash

topdir=/usr/src/packages
builddir=${topdir}/BUILD
rpmdir=${topdir}/RPMS
sourcedir=${topdir}/SOURCES
specdir=${topdir}/SPECS
srcrpmdir=${topdir}/SRPMS
version=`grep -i ^Version  rpm/python-opsi.spec | awk '{ print $2 }'`
tmpdir=/tmp/python-opsi-${version}
cwd=`pwd`
dir=${cwd}/`dirname $0`

test -e $specdir || mkdir -p $specdir
test -e $sourcedir || mkdir -p $sourcedir
test -e $buildroot && rm -rf $buildroot

cd $dir/..
test -e $tmpdir && rm -rf $tmpdir
mkdir $tmpdir
cp -r src files gettext setup.py ${tmpdir}/
cd ${tmpdir}/..
tar cjvf ${sourcedir}/python-opsi-${version}.tar.bz2 python-opsi-${version}
rm -rf $tmpdir
cd $dir

cp python-opsi.spec $specdir/
rpmbuild -ba $specdir/python-opsi.spec

cd $cwd
