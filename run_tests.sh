#! /bin/bash
if [ -e coverage.xml ]; then
	rm coverage.xml
fi

py.test -o junit_family=xunit2 --junitxml=testreport-OPSI.xml --cov-config .coveragerc --cov OPSI --cov-report term --cov-report xml -v tests/testOPSI
py.test -o junit_family=xunit2 --junitxml=testreport-opsicommon.xml --cov-config .coveragerc --cov opsicommon --cov-report term --cov-report xml -v tests/testopsicommon
