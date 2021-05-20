#! /bin/bash
[ -e coverage.xml ] && rm coverage.xml
set -e

py.test --log-level=WARNING -o junit_family=xunit2 --junitxml=testreport-OPSI.xml --cov-append --cov OPSI --cov-report term --cov-report xml -v tests/testOPSI
py.test --log-level=WARNING -o junit_family=xunit2 --junitxml=testreport-opsicommon.xml --cov-append --cov opsicommon --cov-report term --cov-report xml -v tests/testopsicommon
