#!/bin/bash

package_name="python-opsi"

cwd=$(pwd)
dir=${cwd}/$(dirname $0)

cd $dir
pygettext --extract-all --default-domain=${package_name} ../OPSI/UI.py
for lang in de da fr; do
    if [ -e ${package_name}_${lang}.po ]; then
	msgmerge -U ${package_name}_${lang}.po ${package_name}.pot
    else
	msginit --no-translator --locale $lang --output-file ${package_name}_${lang}.po --input ${package_name}.pot
        sed -i 's#"Content-Type: text/plain.*#"Content-Type: text/plain; charset=UTF-8\\n"#' ${package_name}_${lang}.po
    fi
done
