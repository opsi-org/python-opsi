#!/bin/bash

topdir=/usr/src/packages
builddir=${topdir}/BUILD
rpmdir=${topdir}/RPMS
sourcedir=${topdir}/SOURCES
specdir=${topdir}/SPECS
srcrpmdir=${topdir}/SRPMS

cwd=`pwd`
dir=`dirname $0`
cd $dir

test -e $specdir || mkdir -p $specdir
test -e $sourcedir || mkdir -p $sourcedir

cp python-opsi.spec $specdir/
cp ../build.py $sourcedir/

rpmbuild -ba $specdir/python-opsi.spec

cd $cwd
