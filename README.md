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

```bash
sphinx-apidoc --separate --output-dir=doc/src OPSI/
```

After that we can build the documentation:

```bash
sphinx-build -b html -d doc/_build/doctrees doc/src/ doc/python-opsi/
```

After that you will find the documentation in the folder `doc/python-opsi`.


## Requirements
Opsi relies on a mix of Python libraries and system tools that need to
be installed.

The dependencies can be found in `pyproject.toml`.
Please use pip or your distributions recommended tool for the installation of
these.


### Installing on Ubuntu
Installing the depedencies via apt-get:

```bash
apt-get install python3-dev python3-twisted python3-magic python3-pycryptodome python3-newt python3-pampy python3-openssl python3-mysqldb python3-sqlalchemy iproute lshw librsync2
```


## Packaging
You need `python poetry` to build sdist / wheel / Debian and RPM packages.

Build sdist and wheel package:

```bash
poetry install
poetry build
```

Build debian package:

```bash
apt install dpkg-dev
poetry install
poetry run opsi-dev-tool --deb-create-pkg .
```

## Testing
Tests can be found in the `tests` folder. We use [pytest](http://pytest.org/) for our tests.


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

```bash
cp tests/Backends/config.py.example tests/Backends/config.py
```

In this file fill the dict `MySQLconfiguration` with the settings for your test database.
If your are reusing the values from `/etc/opsi/backends/mysql.conf` you can copy the content of `config` to it.


### Run tests
Tests can then be run with:

```bash
poetry install
poetry run pytests
```

### Running Tests on local machine with docker
You need docker, git, python3 and python3-pip installed.

First install poetry:

```bash
pip3 install poetry
```

To run all tests you need a modules file under /etc/opsi of the machine (set the rights for your user, that will run the tests).

You will find a file under `tests/Backends/config.py.gitlabci` copy this file as `config.py` in the same directory.

Start a docker container with mysql for tests:

```bash
docker run --detach --name=mysql --env="MYSQL_ROOT_PASSWORD=opsi" --env="MYSQL_DATABASE=opsi" mysql:latest
```

Grab the ip of your new container with:

```bash
docker inspect mysql
```

and patch your `tests/Backends/config.py` with the new host information for mysql.

Disable strict mode from mysql:

```bash
mysql --host=172.17.0.2 --user=root --password=opsi -e "SET GLOBAL sql_mode = 'NO_ENGINE_SUBSTITUTION';"
```

Change host ip from that what you have seen in docker inspect of your machine.

If you want to run your tests under Ubuntu 18.04 you need also a pip update from ppa:

```bash
apt -y install software-properties-common
add-apt-repository ppa:ci-train-ppa-service/3690
apt -y install python-pip=9.0.1-2.3~ubuntu1.18.04.2~ubuntu18.04.1~ppa202002141134
```

Last step for running:

You need the files from opsi-server for the tests. If you have also cloned opsi-server in the same directory like python-opsi you can set a symbolic link to the data-files:

```bash
ln -s ../opsi-server/opsi-server_data/etc data
```

Now you can install your venv over poetry:

```bash
poetry install
```

Now run the tests:

```bash
poetry run pytests
```

## Contributing
Contributions are welcome.

If you find any security problem please inform us (info@uib.de) before disclosing the security vulnerability in public.


### Translation
Translations are made via [Transifex](https://www.transifex.com/opsi-org/opsiorg/) and the corresponding resource is located [here](https://www.transifex.com/opsi-org/opsiorg/python-opsi/).


### Tests
Please provide tests or a guide on how to test with your contributions.
After applying your code changes all tests must pass.


### Coding Style
Please use conventions described in [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
Deviating from this, indentation has to be done with hard tabs.

For general information about webservice methods please refer to the [manual](http://download.uib.de/opsi4.0/doc/html/en/opsi-manual/opsi-manual.html#opsi-manual-api-datastructure-opsi).


#### Semi-Automated Quality Checks
There is a script that runs `pylint`, `flake8` and all the tests.

```bash
poetry install
poetry run ./run_qa.sh
```

The script will not display any problems reported by `pylint` or
`pep8` but instead creates the files `pylint.txt` and `pep8.txt`.
You then can check the corresponding output.

It will also run all tests and create a coverage from those tests as
`coverage.xml`.


### Documentation
Documentation should be provided for any non-intuitive or complex part.
Please provide the documentation either directly as Python docstrings or
provide it in the form of documents inside the `doc` folder.
The documentation should be integrated into the documentation that is
built with Sphinx.
