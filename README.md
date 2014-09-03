# python-opsi

This is the Python library behind the client management-tool opsi.


## License

This library is released under the AGPLv3 and the copyright belongs to
uib GmbH if this is not noted otherwise in the file itself.


## Documentation

You can use Sphinx to build the documentation.
If you are looking for information on how to setup or configure an opsi
system please get the _getting started_ from opsi.org.


## Requirements

Opsi relies on a mix of Python-libraries and system tools that need to
be installed.

The dependencies for your distribution can either be found in
``debian/control`` or ``rpm/python-opsi.spec``.
Please use your distributions recommended tool for the installation of
these.

### Install via pip

It is possible to use ``pip`` to install most of the requirements - some
requirements are for other programs that can not be installed via pip.

  pip install -r requirements.txt


Please note that additional libraries may need to be installed on your
system.
Under Debian / Ubuntu these can be installed with:

  apt-get install build-essential python-dev


If you want to run the tests please install with:

  pip install -r requirements-dev.txt


If you want to contribute you can install used tools for quality assurance with the following command:

  pip install -r requirements-qa.txt


## Building

Packages can be build for distributions that use either Debian or RPM
packages.
Please install the build requirements from either ``debian/control`` or
``rpm/python-opsi.spec`` before you try to build an package.

For building on a Debian-based system you can use the following command:

  dpkg-buildpackage -us -uc


For building on a RPM-based system you can use the following command:

  rpmbuild -ba rpm/python-opsi.spec


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

Please feel free to contribute.

An easy way to contribute is to provide patches. You can either send
them to info@uib.de or post them in the forums under forum.opsi.org.

### Translation

Translations can be edited with any editor that can handle ``.po``-files.
These files can be found in the folder ``gettext``.

### Tests

Please provide tests or a guide on how to test with your contributions.
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


### Documentation

Documentation should be provided for any non-intuitive or complex part.
Please provide the documentation either directly as Python docstrings or
provide it in the form of documents inside the ``doc`` folder.
The documentation should be integrated into the documentation that is
built with Sphinx.
