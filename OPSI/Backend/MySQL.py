# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2013-2018 uib GmbH <info@uib.de>
# All rights reserved.

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
MySQL-Backend

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero GPL version 3
"""

import base64
import warnings
import time
import threading
from contextlib import contextmanager
from hashlib import md5

import MySQLdb
from MySQLdb.constants import FIELD_TYPE
from MySQLdb.converters import conversions
from sqlalchemy import pool
from twisted.conch.ssh import keys

from OPSI.Backend.Base import ConfigDataBackend
from OPSI.Backend.SQL import (
	onlyAllowSelect, SQL, SQLBackend, SQLBackendObjectModificationTracker)
from OPSI.Exceptions import (BackendBadValueError, BackendUnableToConnectError,
	BackendUnaccomplishableError)
from OPSI.Logger import Logger
from OPSI.Types import forceInt, forceUnicode

__all__ = (
	'ConnectionPool', 'MySQL', 'MySQLBackend',
	'MySQLBackendObjectModificationTracker'
)

logger = Logger()

MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE = 2006
# 2006: 'MySQL server has gone away'
DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE = 1213
# 1213: 'Deadlock found when trying to get lock; try restarting transaction'


@contextmanager
def closingConnectionAndCursor(sqlInstance):
	(connection, cursor) = sqlInstance.connect()
	try:
		yield (connection, cursor)
	finally:
		sqlInstance.close(connection, cursor)


@contextmanager
def disableAutoCommit(sqlInstance):
	"""
	Disable automatic committing.

	:type sqlInstance: MySQL
	"""
	sqlInstance.autoCommit = False
	logger.debug2(u'autoCommit set to False')
	try:
		yield
	finally:
		sqlInstance.autoCommit = True
		logger.debug2(u'autoCommit set to true')


class ConnectionPool(object):
	# Storage for the instance reference
	__instance = None

	def __init__(self, **kwargs):
		""" Create singleton instance """

		# Check whether we already have an instance
		if ConnectionPool.__instance is None:
			logger.debug(u"Creating ConnectionPool instance")
			# Create and remember instance
			poolArgs = {}
			for key in ('pool_size', 'max_overflow', 'timeout'):
				try:
					poolArgs[key] = kwargs[key]
					del kwargs[key]
				except KeyError:
					pass

			def getConnection():
				return MySQLdb.connect(**kwargs)

			ConnectionPool.__instance = pool.QueuePool(getConnection, **poolArgs)
			con = ConnectionPool.__instance.connect()
			con.autocommit(False)
			con.close()

		# Store instance reference as the only member in the handle
		self.__dict__['_ConnectionPool__instance'] = ConnectionPool.__instance

	def destroy(self):
		logger.debug(u"Destroying ConnectionPool instance")
		ConnectionPool.__instance = None

	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)

	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
		return setattr(self.__instance, attr, value)


class MySQL(SQL):

	AUTOINCREMENT = 'AUTO_INCREMENT'
	ALTER_TABLE_CHANGE_SUPPORTED = True
	ESCAPED_BACKSLASH = "\\\\"
	ESCAPED_APOSTROPHE = "\\\'"
	ESCAPED_ASTERISK = "\\*"

	_POOL_LOCK = threading.Lock()

	def __init__(self, **kwargs):
		self._address = u'localhost'
		self._username = u'opsi'
		self._password = u'opsi'
		self._database = u'opsi'
		self._databaseCharset = 'utf8'
		self._connectionPoolSize = 20
		self._connectionPoolMaxOverflow = 10
		self._connectionPoolTimeout = 30
		self.autoCommit = True

		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'address':
				self._address = forceUnicode(value)
			elif option == 'username':
				self._username = forceUnicode(value)
			elif option == 'password':
				self._password = forceUnicode(value)
			elif option == 'database':
				self._database = forceUnicode(value)
			elif option == 'databasecharset':
				self._databaseCharset = str(value)
			elif option == 'connectionpoolsize':
				self._connectionPoolSize = forceInt(value)
			elif option == 'connectionpoolmaxoverflow':
				self._connectionPoolMaxOverflow = forceInt(value)
			elif option == 'connectionpooltimeout':
				self._connectionPoolTimeout = forceInt(value)

		self._transactionLock = threading.Lock()
		self._pool = None
		self._createConnectionPool()
		logger.debug(u'MySQL created: %s' % self)

	def __repr__(self):
		return u'<{0}(address={1!r})>'.format(self.__class__.__name__, self._address)

	def _createConnectionPool(self):
		logger.debug2(u"Creating connection pool")

		if self._pool is not None:
			logger.debug2(u"Connection pool exists - fast exit.")
			return

		logger.debug2(u"Waiting for pool lock...")
		self._POOL_LOCK.acquire(False)  # non-blocking
		try:
			logger.debug2(u"Got pool lock...")

			if self._pool is not None:
				logger.debug2(u"Connection pool has been created while waiting for lock - fast exit.")
				return

			conv = dict(conversions)
			conv[FIELD_TYPE.DATETIME] = str
			conv[FIELD_TYPE.TIMESTAMP] = str

			for tryNumber in (1, 2):
				try:
					self._pool = ConnectionPool(
						host=self._address,
						user=self._username,
						passwd=self._password,
						db=self._database,
						use_unicode=True,
						charset=self._databaseCharset,
						pool_size=self._connectionPoolSize,
						max_overflow=self._connectionPoolMaxOverflow,
						timeout=self._connectionPoolTimeout,
						conv=conv
					)
					logger.debug2("Created connection pool {0}", self._pool)
					break
				except Exception as error:
					logger.logException(error)

					if tryNumber < 2:
						secondsToWait = 5
						logger.debug(
							u"We are waiting {0} seconds before trying "
							u"an reconnect.".format(secondsToWait)
						)
						for _ in range(secondsToWait * 10):
							time.sleep(0.1)
						continue

					raise BackendUnableToConnectError(u"Failed to connect to database '%s' address '%s': %s" % (self._database, self._address, error))
		finally:
			logger.debug2(u"Releasing pool lock...")
			self._POOL_LOCK.release()

	def connect(self, cursorType=None):
		"""
		Connect to the MySQL server.
		If `cursorType` is given this type will be used as the cursor.

		Establishing a connection will be tried multiple times.
		If no connection can be made during this an exception will be
		raised.

		:param cursorType: The class of the cursor to use. \
Defaults to :py:class:MySQLdb.cursors.DictCursor:.
		:raises BackendUnableToConnectError: In case no connection can be established.
		:return: The connection and the corresponding cursor.
		"""
		retryLimit = 10

		cursorType = cursorType or MySQLdb.cursors.DictCursor

		# We create an connection pool in any case.
		# If a pool exists the function will return very fast.
		self._createConnectionPool()

		for retryCount in range(retryLimit):
			try:
				logger.debug2(u"Connecting to connection pool")
				self._transactionLock.acquire()
				logger.debug2(u"Connection pool status: {0}", self._pool.status())
				conn = self._pool.connect()
				conn.autocommit(False)
				cursor = conn.cursor(cursorType)
				break
			except Exception as connectionError:
				logger.debug(u"MySQL connection error: {0!r}", connectionError)
				errorCode = connectionError.args[0]

				self._transactionLock.release()
				logger.debug2(u"Lock released")

				if errorCode == MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					logger.notice(u'MySQL server has gone away (Code {1}) - restarting connection: retry #{0}', retryCount, errorCode)
					time.sleep(0.1)
				else:
					logger.error(u'Unexpected database error: {0}', connectionError)
					raise
		else:
			logger.debug2("Destroying connection pool.")
			self._pool.destroy()
			self._pool = None

			self._transactionLock.release()
			logger.debug2(u"Lock released")

			raise BackendUnableToConnectError(u"Unable to connnect to mysql server. Giving up after {0} retries!".format(retryLimit))

		return (conn, cursor)

	def close(self, conn, cursor):
		try:
			cursor.close()
			conn.close()
		finally:
			self._transactionLock.release()

	def getSet(self, query):
		logger.debug2(u"getSet: {0}", query)
		(conn, cursor) = self.connect()

		try:
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: %s" % e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				(conn, cursor) = self.connect()
				self.execute(query, conn, cursor)

			valueSet = cursor.fetchall()
		finally:
			self.close(conn, cursor)

		return valueSet or []

	def getRows(self, query):
		logger.debug2(u"getRows: {0}", query)
		onlyAllowSelect(query)

		(conn, cursor) = self.connect(cursorType=MySQLdb.cursors.Cursor)
		valueSet = []
		try:
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: %s" % e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				(conn, cursor) = self.connect(cursorType=MySQLdb.cursors.Cursor)
				self.execute(query, conn, cursor)

			valueSet = cursor.fetchall()
			if not valueSet:
				logger.debug(u"No result for query {0!r}", query)
				valueSet = []
		finally:
			self.close(conn, cursor)

		return valueSet

	def getRow(self, query, conn=None, cursor=None):
		logger.debug2(u"getRow: {0}", query)
		closeConnection = True
		if conn and cursor:
			logger.debug(u"TRANSACTION: conn and cursor given, so we should not close the connection.")
			closeConnection = False
		else:
			(conn, cursor) = self.connect()

		row = {}
		try:
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: {0!r}", e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				(conn, cursor) = self.connect()
				self.execute(query, conn, cursor)

			row = cursor.fetchone()
			if not row:
				logger.debug(u"No result for query {0!r}", query)
				row = {}
			else:
				logger.debug2(u"Result: {0!r}", row)
		finally:
			if closeConnection:
				self.close(conn, cursor)
		return row

	def insert(self, table, valueHash, conn=None, cursor=None):
		closeConnection = True
		if conn and cursor:
			logger.debug(u"TRANSACTION: conn and cursor given, so we should not close the connection.")
			closeConnection = False
		else:
			(conn, cursor) = self.connect()

		result = -1
		try:
			colNames = []
			values = []
			for (key, value) in valueHash.items():
				colNames.append(u"`{0}`".format(key))
				if value is None:
					values.append(u"NULL")
				elif isinstance(value, bool):
					if value:
						values.append(u"1")
					else:
						values.append(u"0")
				elif isinstance(value, (float, int)):
					values.append(u"{0}".format(value))
				elif isinstance(value, str):
					values.append(u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value))))
				else:
					values.append(u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value))))

			query = u'INSERT INTO `{0}` ({1}) VALUES ({2});'.format(table, ', '.join(colNames), ', '.join(values))
			logger.debug2(u"insert: {0}", query)
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: {0!r}", e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				(conn, cursor) = self.connect()
				self.execute(query, conn, cursor)
			result = cursor.lastrowid
		finally:
			if closeConnection:
				self.close(conn, cursor)
		return result

	def update(self, table, where, valueHash, updateWhereNone=False):
		(conn, cursor) = self.connect()
		result = 0
		try:
			if not valueHash:
				raise BackendBadValueError(u"No values given")
			query = []
			for (key, value) in valueHash.items():
				if value is None:
					if not updateWhereNone:
						continue

					value = u"NULL"
				elif isinstance(value, bool):
					if value:
						value = u"1"
					else:
						value = u"0"
				elif isinstance(value, (float, int)):
					value = u"%s" % value
				elif isinstance(value, str):
					value = u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value)))
				else:
					value = u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value)))

				query.append(u"`{0}` = {1}".format(key, value))

			query = u"UPDATE `{0}` SET {1} WHERE {2};".format(table, ', '.join(query), where)
			logger.debug2(u"update: {0}", query)
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: {0!r}", e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				(conn, cursor) = self.connect()
				self.execute(query, conn, cursor)
			result = cursor.rowcount
		finally:
			self.close(conn, cursor)
		return result

	def delete(self, table, where, conn=None, cursor=None):
		if conn and cursor:
			logger.debug(u"TRANSACTION: conn and cursor given, so we should not close the connection.")
			closeConnection = False
		else:
			closeConnection = True
			(conn, cursor) = self.connect()

		result = 0
		try:
			query = u"DELETE FROM `%s` WHERE %s;" % (table, where)
			logger.debug2(u"delete: {0}", query)
			try:
				self.execute(query, conn, cursor)
			except Exception as e:
				logger.debug(u"Execute error: {0}", e)
				if e.args[0] != MYSQL_SERVER_HAS_GONE_AWAY_ERROR_CODE:
					raise

				self.close(conn, cursor)
				conn, cursor = self.connect()
				self.execute(query, conn, cursor)

			result = cursor.rowcount
		finally:
			if closeConnection:
				self.close(conn, cursor)

		return result

	def execute(self, query, conn=None, cursor=None):
		if conn and cursor:
			needClose = False
		else:
			needClose = True
			conn, cursor = self.connect()

		res = None
		try:
			query = forceUnicode(query)
			logger.debug2(u"SQL query: {0}", query)
			res = cursor.execute(query)
			if self.autoCommit:
				conn.commit()
		finally:
			if needClose:
				self.close(conn, cursor)
		return res

	def getTables(self):
		# Hardware audit database
		tables = {}
		logger.debug(u"Current tables:")
		for i in self.getSet(u'SHOW TABLES;'):
			for tableName in i.values():
				logger.debug2(u" [ {0} ]", tableName)
				tables[tableName] = [j['Field'] for j in self.getSet(u'SHOW COLUMNS FROM `%s`' % tableName)]
				logger.debug2("Fields in {0}: {1}", tableName, tables[tableName])

		return tables

	def getTableCreationOptions(self, table):
		if table in ('SOFTWARE', 'SOFTWARE_CONFIG') or table.startswith(('HARDWARE_DEVICE_', 'HARDWARE_CONFIG_')):
			return u'ENGINE=MyISAM DEFAULT CHARSET utf8 COLLATE utf8_general_ci;'
		return u'ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci'


class MySQLBackend(SQLBackend):

	def __init__(self, **kwargs):
		self._name = 'mysql'

		SQLBackend.__init__(self, **kwargs)

		self._sql = MySQL(**kwargs)

		warnings.showwarning = self._showwarning

		self._licenseManagementEnabled = True
		self._licenseManagementModule = False
		self._sqlBackendModule = False

		backendinfo = self._context.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']

		if not all(key in modules for key in ('expires', 'customer')):
			logger.info(
				"Missing important information about modules. "
				"Probably no modules file installed."
			)
		elif not modules.get('customer'):
			logger.error(u"Disabling mysql backend and license management module: no customer in modules file")
		elif not modules.get('valid'):
			logger.error(u"Disabling mysql backend and license management module: modules file invalid")
		elif (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
			logger.error(u"Disabling mysql backend and license management module: modules file expired")
		else:
			logger.info(u"Verifying modules file signature")
			publicKey = keys.Key.fromString(data=base64.decodebytes(b'AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
			data = u''
			mks = list(modules.keys())
			mks.sort()
			for module in mks:
				if module in ('valid', 'signature'):
					continue

				if module in helpermodules:
					val = helpermodules[module]
					if int(val) > 0:
						modules[module] = True
				else:
					val = modules[module]
					if val is False:
						val = 'no'
					if val is True:
						val = 'yes'

				data += u'%s = %s\r\n' % (module.lower().strip(), val)

			if not bool(publicKey.verify(md5(data.encode()).digest(), [int(modules['signature'])])):
				logger.error(u"Disabling mysql backend and license management module: modules file invalid")
			else:
				logger.info(u"Modules file signature verified (customer: %s)" % modules.get('customer'))

				if modules.get('license_management'):
					self._licenseManagementModule = True

				if modules.get('mysql_backend'):
					self._sqlBackendModule = True

		logger.debug(u'MySQLBackend created: %s' % self)

	def _showwarning(self, message, category, filename, lineno, line=None, file=None):
		# logger.warning(u"%s (file: %s, line: %s)" % (message, filename, lineno))
		if str(message).startswith('Data truncated for column'):
			logger.error(message)
		else:
			logger.warning(message)

	def _createTableHost(self):
		logger.debug(u'Creating table HOST')
		# MySQL uses some defaults for a row that specifies TIMESTAMP as
		# type without giving DEFAULT or ON UPDATE constraints that
		# result in hosts always having the current time in created and
		# lastSeen. We do not want this behaviour, so we need to specify
		# our DEFAULT.
		# More information about the defaults can be found in the MySQL
		# handbook:
		#   https://dev.mysql.com/doc/refman/5.1/de/timestamp-4-1.html
		table = u'''CREATE TABLE `HOST` (
				`hostId` varchar(255) NOT NULL,
				`type` varchar(30),
				`description` varchar(100),
				`notes` varchar(500),
				`hardwareAddress` varchar(17),
				`ipAddress` varchar(15),
				`inventoryNumber` varchar(64),
				`created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				`lastSeen` TIMESTAMP,
				`opsiHostKey` varchar(32),
				`oneTimePassword` varchar(32),
				`maxBandwidth` integer,
				`depotLocalUrl` varchar(128),
				`depotRemoteUrl` varchar(255),
				`depotWebdavUrl` varchar(255),
				`repositoryLocalUrl` varchar(128),
				`repositoryRemoteUrl` varchar(255),
				`networkAddress` varchar(31),
				`isMasterDepot` bool,
				`masterDepotId` varchar(255),
				`workbenchLocalUrl` varchar(128),
				`workbenchRemoteUrl` varchar(255),
				PRIMARY KEY (`hostId`)
			) %s;''' % self._sql.getTableCreationOptions('HOST')
		logger.debug(table)
		self._sql.execute(table)
		self._sql.execute('CREATE INDEX `index_host_type` on `HOST` (`type`);')

	# Overwriting productProperty_insertObject and
	# productProperty_updateObject to implement Transaction
	def productProperty_insertObject(self, productProperty):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data.pop('possibleValues') or []
		defaultValues = data.pop('defaultValues') or []

		where = self._uniqueCondition(productProperty)
		if self._sql.getRow('select * from `PRODUCT_PROPERTY` where %s' % where):
			self._sql.update('PRODUCT_PROPERTY', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_PROPERTY', data)

		with closingConnectionAndCursor(self._sql) as (conn, cursor):
			retries = 10
			for retry in range(retries):
				try:
					# transaction
					cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE")
					with disableAutoCommit(self._sql):
						logger.debug2(u'Start Transaction: delete from ppv #{}', retry)
						conn.begin()
						self._sql.delete('PRODUCT_PROPERTY_VALUE', where, conn, cursor)
						conn.commit()
						logger.debug2(u'End Transaction')
						break
				except Exception as deleteError:
					logger.debug(u"Execute error: {}", deleteError)
					if deleteError.args[0] == DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE:
						logger.debug(
							u'Table locked (Code {}) - restarting Transaction',
							DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE
						)
						time.sleep(0.1)
					else:
						logger.error(u'Unknown DB Error: {!r}', deleteError)
						raise
			else:
				errorMessage = u'Table locked (Code {}) - giving up after {} retries'.format(
					DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE,
					retries
				)
				logger.error(errorMessage)
				raise BackendUnaccomplishableError(errorMessage)

		with closingConnectionAndCursor(self._sql) as (conn, cursor):
			for value in possibleValues:
				# transform arguments for sql
				# from uniqueCondition
				if value in defaultValues:
					myPPVdefault = u"`isDefault` = 1"
				else:
					myPPVdefault = u"`isDefault` = 0"

				if isinstance(value, bool):
					if value:
						myPPVvalue = u"`value` = 1"
					else:
						myPPVvalue = u"`value` = 0"
				elif isinstance(value, (float, int)):
					myPPVvalue = u"`value` = %s" % (value)
				else:
					myPPVvalue = u"`value` = '%s'" % (self._sql.escapeApostrophe(self._sql.escapeBackslash(value)))
				myPPVselect = (
					u"select * from PRODUCT_PROPERTY_VALUE where "
					u"`propertyId` = '{0}' AND `productId` = '{1}' AND "
					u"`productVersion` = '{2}' AND "
					u"`packageVersion` = '{3}' AND {4} AND {5}".format(
						data['propertyId'],
						data['productId'],
						str(data['productVersion']),
						str(data['packageVersion']),
						myPPVvalue,
						myPPVdefault
					)
				)

				retries = 10
				for retry in range(retries):
					try:
						# transaction
						cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE")
						with disableAutoCommit(self._sql):
							logger.debug2(u'Start Transaction: insert to ppv #{}', retry)
							conn.begin()
							if not self._sql.getRow(myPPVselect, conn, cursor):
								self._sql.insert('PRODUCT_PROPERTY_VALUE', {
									'productId': data['productId'],
									'productVersion': data['productVersion'],
									'packageVersion': data['packageVersion'],
									'propertyId': data['propertyId'],
									'value': value,
									'isDefault': bool(value in defaultValues)
									}, conn, cursor)
								conn.commit()
							else:
								conn.rollback()
							logger.debug2(u'End Transaction')
							break
					except Exception as insertError:
						logger.debug(u"Execute error: {!r}", insertError)
						if deleteError.args[0] == DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE:
							# 1213: May be table locked because of concurrent access - retrying
							logger.notice(
								u'Table locked (Code {}) - restarting Transaction'.format(
									DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE
								)
							)
							time.sleep(0.1)
						else:
							logger.error(u'Unknown DB Error: {!r}', insertError)
							raise
				else:
					errorMessage = u'Table locked (Code {}) - giving up after {} retries'.format(
						DEADLOCK_FOUND_WHEN_TRYING_TO_GET_LOCK_ERROR_CODE,
						retries
					)
					logger.error(errorMessage)
					raise BackendUnaccomplishableError(errorMessage)

	def productProperty_updateObject(self, productProperty):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		where = self._uniqueCondition(productProperty)
		possibleValues = data.pop('possibleValues') or []
		defaultValues = data.pop('defaultValues') or []

		self._sql.update('PRODUCT_PROPERTY', where, data)

		try:
			self._sql.delete('PRODUCT_PROPERTY_VALUE', where)
		except Exception as delError:
			logger.debug2(u"Failed to delete from PRODUCT_PROPERTY_VALUE: {}", delError)

		for value in possibleValues:
			with disableAutoCommit(self._sql):
				valuesExist = self._sql.getRow(
					u"select * from PRODUCT_PROPERTY_VALUE where "
					u"`propertyId` = '{0}' AND `productId` = '{1}' AND "
					u"`productVersion` = '{2}' AND `packageVersion` = '{3}' "
					u"AND `value` = '{4}' AND `isDefault` = {5}".format(
						data['propertyId'],
						data['productId'],
						str(data['productVersion']),
						str(data['packageVersion']),
						value,
						str(value in defaultValues)
					)
				)

				if not valuesExist:
					self._sql.autoCommit = True
					logger.debug2(u'autoCommit set to True')
					self._sql.insert('PRODUCT_PROPERTY_VALUE', {
						'productId': data['productId'],
						'productVersion': data['productVersion'],
						'packageVersion': data['packageVersion'],
						'propertyId': data['propertyId'],
						'value': value,
						'isDefault': bool(value in defaultValues)
						}
					)


class MySQLBackendObjectModificationTracker(SQLBackendObjectModificationTracker):
	def __init__(self, **kwargs):
		SQLBackendObjectModificationTracker.__init__(self, **kwargs)
		self._sql = MySQL(**kwargs)
		self._createTables()
