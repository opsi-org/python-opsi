# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2017 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Functionality to automatically configure an OPSI MySQL backend.

.. versionadded:: 4.0.4.6

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from contextlib import closing, contextmanager

import MySQLdb

import OPSI.Util.Task.ConfigureBackend as backendUtils
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Logger import Logger

DATABASE_EXISTS_ERROR_CODE = 1007
ACCESS_DENIED_ERROR_CODE = 1044
INVALID_DEFAULT_VALUE = 1067
LOGGER = Logger()


class DatabaseConnectionFailedException(Exception):
	pass


def configureMySQLBackend(
	dbAdminUser, dbAdminPass,
	config=None,
	systemConfiguration=None,
	additionalBackendConfig=None,
	backendConfigFile=u'/etc/opsi/backends/mysql.conf',
	notificationFunction=None,
	errorFunction=None):
	"""
	Does the initial configuration of an MySQL backend.

	It will set up the database for OPSI, grant the specified user the
	rights needed, try if the connection works, save the configuration
	to the backend file and create the backend base.

	:param dbAdminUser: Username of the DBA.
	:param dbAdminPass: Password for the DBA.
	:param backendConfigFile: Path to mysql backend configuration file.
	:param config: The configuration for the database. \
This should include values for the keys `database`, `username`, \
`password` and `address`. `address` is also the address of the database. \
If not given this will be read from ``backendConfigFile``.
	:type config: dict
	:param additionalBackendConfig: If given this will update ``config``
	:param notificationFunction: A function that notifications will be \
passed on to. Defaults to ``Logger.notice``.
	:type notificationFunction: func
	:param errorFunction: A function that error messages will be passed \
on to. Defaults to ``Logger.error``.
	:type errorFunction: func
	"""

	if notificationFunction is None:
		notificationFunction = LOGGER.notice

	if errorFunction is None:
		errorFunction = LOGGER.error

	if config is None:
		config = backendUtils.getBackendConfiguration(backendConfigFile)

	if additionalBackendConfig is not None:
		config.update(additionalBackendConfig)

	try:
		initializeDatabase(
			dbAdminUser, dbAdminPass, config,
			systemConfig=systemConfiguration,
			notificationFunction=notificationFunction
		)
	except DatabaseConnectionFailedException as exc:
		errorFunction(
			u"Failed to connect to host '{hostname}' as user '{username}': "
			u"{error}".format(
				hostname=config['address'],
				username=dbAdminUser,
				error=exc,
			)
		)
		raise exc
	except Exception as exc:
		errorFunction(exc)
		raise exc

	backendUtils.updateConfigFile(backendConfigFile, config, notificationFunction)

	notificationFunction(u"Initializing mysql backend")
	backend = MySQLBackend(**config)
	try:
		backend.backend_createBase()
	except MySQLdb.OperationalError as exc:
		if exc.errno == INVALID_DEFAULT_VALUE:
			errorFunction(
				u"It seems you have the MySQL strict mode enabled. "
				u"Please read the opsi handbook.\n"
				u"{error}".format(error=exc)
			)

		raise exc

	notificationFunction(u"Finished initializing mysql backend.")


def initializeDatabase(
	dbAdminUser, dbAdminPass, config,
	systemConfig=None, notificationFunction=None, errorFunction=None):
	"""
	Create a database and grant the OPSI user the needed rights on it.
	"""
	@contextmanager
	def connectAsDBA():
		conConfig = {
			"host": config['address'],
			"user": dbAdminUser,
			"passwd": dbAdminPass
		}

		try:
			with closing(MySQLdb.connect(**conConfig)) as db:
				yield db
		except Exception as error:
			raise DatabaseConnectionFailedException(error)

	def createUser(host):
		notificationFunction(
			u"Creating user '{username}' and granting"
			u" all rights on '{database}'".format(**config)
		)
		db.query(u'USE {database};'.format(**config))
		db.query(
			(
				u"GRANT ALL ON {1[database]}.* TO '{1[username]}'@'{0}' "
				u"IDENTIFIED BY '{1[password]}'").format(
					host,
					config,
			)
		)
		db.query(u'FLUSH PRIVILEGES;')
		notificationFunction(
			u"User '{username}' created and privileges set".format(**config)
		)

	if notificationFunction is None:
		notificationFunction = LOGGER.notice

	if errorFunction is None:
		errorFunction = LOGGER.error

	if systemConfig is None:
		systemConfig = backendUtils._getSysConfig()

	# Connect to database host
	notificationFunction(
		u"Connecting to host '{0[address]}' as user '{username}'".format(
			config, username=dbAdminUser
		)
	)
	with connectAsDBA() as db:
		notificationFunction(
			u"Successfully connected to host '{0[address]}'"
			u" as user '{username}'".format(config, username=dbAdminUser)
		)

		# Create opsi database and user
		notificationFunction(u"Creating database '{database}'".format(**config))
		try:
			db.query(u'CREATE DATABASE {database} DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_bin;'.format(**config))
		except MySQLdb.OperationalError as error:
			if error.errno == ACCESS_DENIED_ERROR_CODE:
				raise DatabaseConnectionFailedException(error.msg)
			raise error
		except MySQLdb.ProgrammingError as error:
			if error.errno != DATABASE_EXISTS_ERROR_CODE:
				raise error
		notificationFunction(u"Database '{database}' created".format(**config))

		if config['address'] in ("localhost", "127.0.0.1", systemConfig['hostname'], systemConfig['fqdn']):
			createUser("localhost")
			if config['address'] not in ("localhost", "127.0.0.1"):
				createUser(config['address'])
		else:
			createUser(systemConfig['ipAddress'])
			createUser(systemConfig['fqdn'])
			createUser(systemConfig['hostname'])

	# Test connection / credentials
	notificationFunction(
		u"Testing connection to database '{database}' as "
		u"user '{username}'".format(**config)
	)

	userConnectionSettings = {
		"host": config['address'],
		"user": config['username'],
		"passwd": config['password'],
		"db": config['database']
	}
	try:
		with closing(MySQLdb.connect(**userConnectionSettings)):
			pass
	except Exception as error:
		raise DatabaseConnectionFailedException(error)

	notificationFunction(
		u"Successfully connected to host '{address}' as user"
		u" '{username}'".format(**config)
	)
