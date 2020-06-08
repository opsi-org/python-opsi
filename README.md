# python-opsi

This is the Python library behind the client management-tool [opsi](http://www.opsi.org/).


## License

This library is released under the AGPLv3 and the copyright belongs to
uib GmbH if this is not noted otherwise in the file itself.


## Documentation

You can use [Sphinx](http://sphinx-doc.org/) to build the documentation.
If you are looking for information on how to setup or configure an opsi
system please get the _getting started_ from opsi.org.

### Building the documentation

First we create the API documentation from the Python files:
``sphinx-apidoc --separate --output-dir=doc/src OPSI/``

After that we can build the documentation:
``sphinx-build -b html -d doc/_build/doctrees doc/src/ doc/python-opsi/``


After that you will find the documentation in the folder ``doc/python-opsi``.

## Requirements

Opsi relies on a mix of Python-libraries and system tools that need to
be installed.

The dependencies for your distribution can either be found in
`debian/control` or `rpm/python-opsi.spec`.
Please use your distributions recommended tool for the installation of
these.

### Installing on Ubuntu

Installing the depedencies via apt-get:
``apt-get install lsb-release python3-twisted python3-magic python3-crypto python3-newt python3-pampy python3-openssl python3-mysqldb python3-sqlalchemy iproute duplicity lshw python3-dev``

For installing further depedencies on your system we also recommend to
install the header files for Python and librsync.

This can be done with:
``apt-get install build-essential python3-dev librsync-dev``


## Building

Packages can be build for distributions that use either Debian or RPM
packages.
Please install the necessary build requirements from either `debian/control` or
`rpm/python-opsi.spec` before you build a package.

### On Debian-based systems

For building on a Debian-based system you can use the following command:
``dpkg-buildpackage -us -uc``

### On RPM-based systems

For building on a RPM-based system you can use the following command:
``rpmbuild -ba rpm/python-opsi.spec``


## Testing

Tests can be found in the `tests` folder. We use [pytest](http://pytest.org/) for our tests.

### Installing Requirements

Requirements for tests and QA are listed as package extras.

They can be installed with the following command:
``pip install ".[test,qa]"``

### Configuring database for test

Testing the MySQL backend requires a license file for most of the tests.

To run tests with MySQL as a backend you need to install and configure
your MySQL server first.
You then need to create a user and database for the tests.
Please follow the corresponding guides of your distribution and/or MySQL
to do so.

**Warning:** The tests will drop every table on the configured database
so make sure you are not running things against your production database!

It is possible to let opsi create a database for you by running `opsi-setup --configure-mysql` and then re-use the configuration from `/etc/opsi/backends/mysql.conf`.

To configure the tests copy the example configuration to `tests/Backends/config.py`:

``cp tests/Backends/config.py.example tests/Backends/config.py``

In this file fill the dict `MySQLconfiguration` with the settings for your test database.
If your are reusing the values from `/etc/opsi/backends/mysql.conf` you can copy the content of `config` to it.

### Running

Tests can then be run with:
``./run_tests.sh``

### Running Tests on local machine with docker

You need docker, git, python3 and python3-pip installed.

First install poetry:
``pip3 install poetry``

To run all tests you need a modules file under /etc/opsi of the machine (set the rights for your user, that will run the tests).

You will find a file under ``tests/Backends/config.py.gitlabci`` copy this file as config.py in the same directory.

Start a docker container with mysql for tests:

```
docker run --detach --name=mysql --env="MYSQL_ROOT_PASSWORD=opsi" --env="MYSQL_DATABASE=opsi" mysql:5.7
```

Grab the ip of your new container with:

```
docker inspect mysql
```

and patch your ``tests/Backends/config.py``` with the new host information for mysql.

Disable strict mode from mysql:

```
mysql --host=172.17.0.2 --user=root --password=opsi -e "SET GLOBAL sql_mode = 'NO_ENGINE_SUBSTITUTION';"
```

Change host ip from that what you have seen in docker inspect of your machine.

If you want to run your tests under Ubuntu 18.04 you need also a pip update from ppa:

```
apt -y install software-properties-common
add-apt-repository ppa:ci-train-ppa-service/3690
apt -y install python-pip=9.0.1-2.3~ubuntu1.18.04.2~ubuntu18.04.1~ppa202002141134
```

Last step for running:

You need the files from opsi-server for the tests. If you have also cloned opsi-server in the same directory like python-opsi you can set a symbolic link to the data-files:

```
ln -s ../opsi-server/opsi-server_data/etc data
```

Now you can install your venv over poetry:

```
poetry install
```

Now run the tests:

```poetry run pytests```

## Contributing

Contributions are welcome.

If you find any security problem please inform us (info@uib.de) before disclosing the security vulnerability in public.

### Translation

Translations are made via [Transifex](https://www.transifex.com/opsi-org/opsiorg/) and the corresponding resource is located [here](https://www.transifex.com/opsi-org/opsiorg/python-opsi/).

### Tests

Please provide tests or a guide on how to test with your contributions.
After applying your code changes all tests must pass.

### Coding Style

Indentation should be done with hard tabs.

Code should be written in `camelCase`.
For backend methods that can be executed via a call to the webservice
please use stick to the use of camelCase but seperate the object type
and the method name with an underscore like this:

* `backend_info`
* `configState_getHashes`

For more general information about webservice methods please refer to the [manual](http://download.uib.de/opsi4.0/doc/html/en/opsi-manual/opsi-manual.html#opsi-manual-api-datastructure-opsi).


Besides this please follow
[PEP 008](http://legacy.python.org/dev/peps/pep-0008/).


#### Semi-Automated Quality Checks

There is a script that runs ``pylint``, ``flake8`` and all the tests.
If you want to use it please install the requirements for it first:
``pip install -r requirements-qa.txt``


After that you can execute the script:
``./run_qa.sh``

The script will not display any problems reported by `pylint` or
`pep8` but instead creates the files `pylint.txt` and `pep8.txt`.
You then can check the corresponding output.

It will also run all tests and create a coverage from those tests as
`coverage.xml`.

### Documentation

Documentation should be provided for any non-intuitive or complex part.
Please provide the documentation either directly as Python docstrings or
provide it in the form of documents inside the ``doc`` folder.
The documentation should be integrated into the documentation that is
built with Sphinx.
