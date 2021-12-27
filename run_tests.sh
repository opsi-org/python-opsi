#! /bin/bash
[ -e coverage.xml ] && rm coverage.xml
set -e

py.test -v --log-level=warning \
	-o junit_family=xunit2 --junitxml=testreport-OPSI.xml \
	--cov-append --cov OPSI --cov-report term --cov-report xml \
	tests
