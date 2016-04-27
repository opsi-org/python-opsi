#! /bin/bash -e
# Running QA tools against the current repo.
# This will create various files with QA information.
# Please make sure the tools from requirements-qa.txt are installed
echo "Running tests"
./run_tests.sh

echo "Running pylint"
pylint --rcfile=.pylintrc OPSI > pylint.txt || echo 'pylint did not finish with return code 0'

echo "Running flake8"
flake8 --exit-zero OPSI/ > pep8.txt
