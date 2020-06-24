#! /bin/bash
if [ -e coverage.xml ]; then
	rm coverage.xml
fi

py.test -o junit_family=xunit2 --junitxml=testreport-OPSI.xml --cov-append --cov OPSI --cov-report term --cov-report xml -v tests/testOPSI
echo "exitcode $?"

py.test -o junit_family=xunit2 --junitxml=testreport-opsicommon.xml --cov-append --cov opsicommon --cov-report term --cov-report xml -v tests/testopsicommon
echo "exitcode $?"

