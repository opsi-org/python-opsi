# python-opsi

This is the Python library behind the client management-tool opsi.


## License

This library is released under the AGPLv3 and the copyright belongs to
uib GmbH if this is not noted otherwise in the file itself.


## Documentation

You can use [Sphinx](http://sphinx-doc.org/) to build the documentation.
If you are looking for information on how to setup or configure an opsi
system please get the _getting started_ from opsi.org.

### Building the documentation

First we create the API documentation from the Python files:

  sphinx-apidoc --separate --output-dir=doc/src OPSI/

After that we can build the documentation:

  sphinx-build -b html -d doc/_build/doctrees doc/src/ doc/html/


After that you will find the documentation in the folder ``doc/html``.

## Requirements

Opsi relies on a mix of Python-libraries and system tools that need to
be installed.

The dependencies for your distribution can either be found in
``debian/control`` or ``rpm/python-opsi.spec``.
Please use your distributions recommended tool for the installation of
these.

Installing the depedencies on Ubuntu 12.04:

  apt-get install lsb-release python-twisted-web python-twisted-conch \
  python-magic python-crypto python-ldap python-newt \
  python-pam python-openssl python-mysqldb python-sqlalchemy iproute \
  duplicity python-m2crypto lshw python-dev python-ldaptor


For installing further depedencies on your system we also recommend to
install the header files for Python, librsync and to test the
SQLite-backend we also need apsw.

This can be done on Ubuntu 12.04 with:

  apt-get install build-essential python-dev librsync-dev python-apsw


### Install via pip

It is possible to use ``pip`` to install most of the requirements - some
requirements are for other programs that can not be installed via pip.

  pip install -r requirements.txt


## Building

Packages can be build for distributions that use either Debian or RPM
packages.
Please install the build requirements from either ``debian/control`` or
``rpm/python-opsi.spec`` before you try to build an package.


Installing the build-requirements on a Ubuntu 12.04:

  apt-get install gettext debhelper python-support python \
  python-setuptools lsb-release


For building on a Debian-based system you can use the following command:

  dpkg-buildpackage -us -uc


For building on a RPM-based system you can use the following command:

  rpmbuild -ba rpm/python-opsi.spec


## Testing

Tests can be found in the ``tests`` folder. The tests can be run with
any testrunner. We currently use
[nose](http://nose.readthedocs.org/en/latest/) as a testrunner.
If you are unsure what testrunner to use we recommend using _nose_.

### Installing Requirements

Requirements for the tests can be found in ``requirements-dev.txt``.
They can be installed with the following command:

  pip install -r requirements-dev.txt


If you want to install _nose_ you can do so with the following command:

  pip install nose


### Running

Tests can then be run with:

  ./run_tests.sh


## Contributing

Please feel free to contribute.

An easy way to contribute is to provide patches. You can either send
them to _info@uib.de_ or post them in the [forums](https://forum.opsi.org).

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


Besides this please follow
[PEP 008](http://legacy.python.org/dev/peps/pep-0008/).


#### Automated Quality Checks

There is a script that runs ``pylint``, ``flake8`` and all the tests.
If you want to use it please install the requirements for it first:

  pip install -r requirements-qa.txt


After that you can execute the script:

  ./run_qa.sh

The script will not display any problems reported by ``pylint`` or
``pep8`` but instead creates the files ``pylint.txt`` and ``pep8.txt``.

It will also run all tests and create a coverage from those tests as
``coverage.xml``.

### Documentation

Documentation should be provided for any non-intuitive or complex part.
Please provide the documentation either directly as Python docstrings or
provide it in the form of documents inside the ``doc`` folder.
The documentation should be integrated into the documentation that is
built with Sphinx.
