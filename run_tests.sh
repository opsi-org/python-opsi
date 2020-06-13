#! /bin/bash
if [ -e coverage.xml ]; then
	rm coverage.xml
fi

py.test --junit_family=xunit2 --junitxml=testreport.xml --cov-config .coveragerc --cov OPSI --cov-report term --cov-report xml -v tests/ --ignore=tests/manual_tests
