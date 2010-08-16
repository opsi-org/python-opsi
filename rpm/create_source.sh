#!/bin/bash

packagename=$(basename rpm/*.spec .spec)
version=$(head -n1 debian/changelog | cut -d'(' -f2 | cut -d')' -f1 | cut -d'-' -f1)
release=$(head -n1 debian/changelog | cut -d'(' -f2 | cut -d')' -f1 | cut -d'-' -f2)

cp rpm/${packagename}.spec /tmp/
cat /tmp/${packagename}.spec | sed "s/^Version:.*/Version:        ${version}/" | sed "s/^Release:.*/Release:        ${release}/" > rpm/${packagename}.spec
rm rpm/${packagename}.spec

tmpdir=/tmp/${packagename}-${version}
cwd=$(pwd)
dir=${cwd}/$(dirname $0)

cd $dir/..
test -e $tmpdir && rm -rf $tmpdir
mkdir $tmpdir
cp -r OPSI data setup.py ${tmpdir}/
cd ${tmpdir}/..
tar cjvf /tmp/${packagename}-${version}.tar.bz2 ${packagename}-${version}
rm -rf $tmpdir
echo "Source archive: /tmp/${packagename}-${version}.tar.bz2"
cd $cwd

