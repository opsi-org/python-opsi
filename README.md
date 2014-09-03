# python-opsi

This is the Python library behind the client management-tool opsi.


## Documentation

You can use Sphinx to build the documentation.
If you are looking for information on how to setup or configure an opsi
system please get the _getting started_ from opsi.org.


## Requirements


## Testing

Tests can be found in the ``tests`` folder. The tests can be run with
any testrunner. We currently use ``nose`` as a testrunner. If you are
unsure what testrunner to use we recommend using nose.
Tests can be run with:

  nosetests tests/


Currently there are three folders that contain unittests. The current
set of tests is in the ``tests`` folder. The folders ``test`` and
``OPSI/Tests`` contain tests in a currently unknown state. We currently
do not recommend to run these tests.

New tests should be placed under ``tests``.


## Contributing


### Tests

Please provide tests or a guido on how to tests with your contributions.
After applying your code changes all tests must pass.

### Coding Style

Indentation should be done with hard tabs.

Code should be written in ``camelCase``.
For backend methods that can be executed via a call to the webservice
please use stick to the use of camelCase but seperate the object type
and the method name with an underscore like this:

* ``backend_info``
* ``configState_getHashes``


Besides this please follow PEP 008.

To ease following these rules you can simply execute the
``run_qa.sh``-script:

  ./run_qa.sh
