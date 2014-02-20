#! /bin/bash
# Running QA tools against the current repo.
# This will create various files with QA information.
# Please make sure the tools from requirements-qa.txt are installed
echo "Running pylint"
pylint --rcfile=pylintrc OPSI > pylint.txt || echo 'pylint did not finish with return code 0'

echo "Running flake8"
flake8 --ignore=W191 --exclude=OPSI/web2/*,OPSI/tests/* OPSI/ > pep8.txt || echo 'pep8 did not finish with return code 0'

echo "Running nosetests"
nosetests --with-xunit --with-xcoverage --cover-package=OPSI tests/ || echo 'nosetests did not finish with return code 0'
