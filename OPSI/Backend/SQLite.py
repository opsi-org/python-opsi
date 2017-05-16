#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
SQLite backend.

:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero GPL version 3
"""

import threading
from itertools import izip

from apsw import (SQLITE_CONFIG_MULTITHREAD, SQLITE_OPEN_CREATE,
	SQLITE_OPEN_READWRITE, Connection)

from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceFilename, forceUnicode
from OPSI.Types import BackendBadValueError
from OPSI.Backend.SQL import SQL, SQLBackend, SQLBackendObjectModificationTracker

__all__ = ('SQLite', 'SQLiteBackend', 'SQLiteObjectBackendModificationTracker')

logger = Logger()


class SQLite(SQL):
	AUTOINCREMENT = ''
	ALTER_TABLE_CHANGE_SUPPORTED = False
	ESCAPED_BACKSLASH = "\\"
	ESCAPED_APOSTROPHE = "''"
	ESCAPED_ASTERISK = "**"

	def __init__(self, **kwargs):
		self._database = ":memory:"
		self._synchronous = True
		self._databaseCharset = 'utf8'
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'database':
				self._database = forceFilename(value)
			elif option == 'synchronous':
				self._synchronous = forceBool(value)
			elif option == 'databasecharset':
				self._databaseCharset = str(value)

		self._connection = None
		self._cursor = None
		self._transactionLock = threading.Lock()
		logger.debug(u'SQLite created: %s' % self)

	def connect(self):
		try:
			logger.debug2(u"Connecting to sqlite db '%s'" % self._database)
			if not self._connection:
				self._connection = Connection(
					filename=self._database,
					flags=SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_CONFIG_MULTITHREAD,
					vfs=None,
					statementcachesize=100
				)
			if not self._cursor:
				def rowtrace(cursor, row):
					valueSet = {}
					for rowDescription, current in izip(cursor.getdescription(), row):
						valueSet[rowDescription[0]] = current

					return valueSet

				self._cursor = self._connection.cursor()
				if not self._synchronous:
					self._cursor.execute('PRAGMA synchronous=OFF')
					self._cursor.execute('PRAGMA temp_store=MEMORY')
					self._cursor.execute('PRAGMA cache_size=5000')
				if self._databaseCharset.lower() in ('utf8', 'utf-8'):
					self._cursor.execute('PRAGMA encoding="UTF-8"')
				self._cursor.setrowtrace(rowtrace)
			return (self._connection, self._cursor)
		except Exception:
			raise

	def close(self, conn, cursor):
		pass

	def getSet(self, query):
		logger.debug2(u"getSet: %s" % query)
		(conn, cursor) = self.connect()
		valueSet = []
		try:
			self.execute(query, conn, cursor)
			valueSet = cursor.fetchall()
			if not valueSet:
				logger.debug(u"No result for query '%s'" % query)
				valueSet = []
		finally:
			self.close(conn, cursor)
		return valueSet

	def getRow(self, query):
		logger.debug2(u"getRow: %s" % query)
		(conn, cursor) = self.connect()
		row = {}
		try:
			self.execute(query, conn, cursor)
			try:
				row = cursor.next()
			except Exception:
				pass

			if not row:
				logger.debug(u"No result for query '%s'" % query)
				row = {}
			else:
				logger.debug2(u"Result: '%s'" % row)
		finally:
			self.close(conn, cursor)
		return row

	def insert(self, table, valueHash):
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
				elif isinstance(value, (float, long, int)):
					values.append(u"{0}".format(value))
				elif isinstance(value, str):
					values.append(u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value.decode("utf-8")))))
				else:
					values.append(u"\'{0}\'".format(self.escapeApostrophe(self.escapeBackslash(value))))

			query = u'INSERT INTO `{table}` ({columns}) VALUES ({values});'.format(columns=', '.join(colNames), values=', '.join(values), table=table)
			logger.debug2(u"insert: %s" % query)

			self.execute(query, conn, cursor)
			result = conn.last_insert_rowid()
		finally:
			self.close(conn, cursor)

		return result

	def update(self, table, where, valueHash, updateWhereNone=False):
		(conn, cursor) = self.connect()
		result = 0
		try:
			if not valueHash:
				raise BackendBadValueError(u"No values given")

			values = []
			for (key, value) in valueHash.items():
				if value is None and not updateWhereNone:
					continue

				if value is None:
					values.append(u"`{0}` = NULL".format(key))
				elif isinstance(value, bool):
					if value:
						values.append(u"`{0}` = 1".format(key))
					else:
						values.append(u"`{0}` = 0".format(key))
				elif isinstance(value, (float, long, int)):
					values.append(u"`{0}` = {1}".format(key, value))
				elif isinstance(value, str):
					values.append(u"`{0}` = \'{1}\'".format(key, self.escapeApostrophe(self.escapeBackslash(value.decode("utf-8")))))
				else:
					values.append(u"`{0}` = \'{1}\'".format(key, self.escapeApostrophe(self.escapeBackslash(value))))

			query = u"UPDATE `{table}` SET {values} WHERE {condition};".format(table=table, values=', '.join(values), condition=where)
			logger.debug2(u"update: %s" % query)
			self.execute(query, conn, cursor)
			result = conn.changes()
		finally:
			self.close(conn, cursor)
		return result

	def delete(self, table, where):
		(conn, cursor) = self.connect()
		result = 0
		try:
			query = u"DELETE FROM `%s` WHERE %s;" % (table, where)
			logger.debug2(u"delete: %s" % query)
			self.execute(query, conn, cursor)
			result = conn.changes()
		finally:
			self.close(conn, cursor)
		return result

	def execute(self, query, conn=None, cursor=None):
		res = None
		needClose = False
		if not conn or not cursor:
			(conn, cursor) = self.connect()
			needClose = True

		try:
			logger.debug2(u"SQL query: %s" % forceUnicode(query))
			res = cursor.execute(query)
		finally:
			if needClose:
				self.close(conn, cursor)

		return res

	def getTables(self):
		tables = {}
		logger.debug2(u"Current tables:")
		for i in self.getSet('SELECT name FROM sqlite_master WHERE type = "table";'):
			tableName = i.values()[0]
			logger.debug2(u" [ %s ]" % tableName)
			tables[tableName] = []
			for j in self.getSet('PRAGMA table_info(`%s`);' % tableName):
				logger.debug2(u"      %s" % j)
				tables[tableName].append(j['name'])
		return tables

	def getTableCreationOptions(self, table):
		return u''


class SQLiteBackend(SQLBackend):

	def __init__(self, **kwargs):
		self._name = 'sqlite'

		SQLBackend.__init__(self, **kwargs)

		self._sql = SQLite(**kwargs)

		self._licenseManagementEnabled = True
		self._licenseManagementModule = True
		self._sqlBackendModule = True
		logger.debug(u'SQLiteBackend created: %s' % self)

	def _createAuditHardwareTables(self):
		"""
		Creating tables for hardware audit data.

		The speciatly for SQLite is that an ALTER TABLE may not list
		multiple columns to alter but instead has to alter one column
		after another.
		"""
		tables = self._sql.getTables()
		existingTables = set(tables.keys())

		def removeTrailingComma(query):
			if query.endswith(u','):
				return query[:-1]

			return query

		def finishSQLQuery(tableExists, tableName):
			if tableExists:
				return u' ;\n'
			else:
				return u'\n) %s;\n' % self._sql.getTableCreationOptions(tableName)

		def getSQLStatements():
			for (hwClass, values) in self._auditHardwareConfig.items():
				logger.debug(u"Processing hardware class '%s'" % hwClass)
				hardwareDeviceTableName = u'HARDWARE_DEVICE_{0}'.format(hwClass)
				hardwareConfigTableName = u'HARDWARE_CONFIG_{0}'.format(hwClass)

				hardwareDeviceTableExists = hardwareDeviceTableName in existingTables
				hardwareConfigTableExists = hardwareConfigTableName in existingTables

				if hardwareDeviceTableExists:
					hardwareDeviceTable = u'ALTER TABLE `{name}`\n'.format(
						name=hardwareDeviceTableName
					)
				else:
					hardwareDeviceTable = (
						u'CREATE TABLE `{name}` (\n'
						u'`hardware_id` INTEGER NOT NULL {autoincrement},\n'.format(
							name=hardwareDeviceTableName,
							autoincrement=self._sql.AUTOINCREMENT
						)
					)

				avoidProcessingFurtherHardwareDevice = False
				hardwareDeviceValuesProcessed = 0
				for (value, valueInfo) in values.items():
					logger.debug(u"  Processing value '%s'" % value)
					if valueInfo['Scope'] == 'g':
						if hardwareDeviceTableExists:
							if value in tables[hardwareDeviceTableName]:
								# Column exists => change
								if not self._sql.ALTER_TABLE_CHANGE_SUPPORTED:
									continue

								hardwareDeviceTable += u'CHANGE `{column}` `{column}` {type} NULL,\n'.format(
									column=value,
									type=valueInfo['Type']
								)
							else:
								# Column does not exist => add
								yield hardwareDeviceTable + u'ADD COLUMN `{column}` {type} NULL;'.format(
									column=value,
									type=valueInfo["Type"]
								)
								avoidProcessingFurtherHardwareDevice = True
						else:
							hardwareDeviceTable += u'`{column}` {type} NULL,\n'.format(
								column=value,
								type=valueInfo["Type"]
							)
						hardwareDeviceValuesProcessed += 1

				if hardwareConfigTableExists:
					hardwareConfigTable = u'ALTER TABLE `{name}`\n'.format(
						name=hardwareConfigTableName
					)
				else:
					hardwareConfigTable = (
						u'CREATE TABLE `{name}` (\n'
						u'`config_id` INTEGER NOT NULL {autoincrement},\n'
						u'`hostId` varchar(255) NOT NULL,\n'
						u'`hardware_id` INTEGER NOT NULL,\n'
						u'`firstseen` TIMESTAMP NOT NULL DEFAULT \'0000-00-00 00:00:00\',\n'
						u'`lastseen` TIMESTAMP NOT NULL DEFAULT \'0000-00-00 00:00:00\',\n'
						u'`state` TINYINT NOT NULL,\n'.format(
							name=hardwareConfigTableName,
							autoincrement=self._sql.AUTOINCREMENT
						)
					)

				avoidProcessingFurtherHardwareConfig = False
				hardwareConfigValuesProcessed = 0
				for (value, valueInfo) in values.items():
					logger.debug(u"  Processing value '%s'" % value)
					if valueInfo['Scope'] == 'i':
						if hardwareConfigTableExists:
							if value in tables[hardwareConfigTableName]:
								# Column exists => change
								if not self._sql.ALTER_TABLE_CHANGE_SUPPORTED:
									continue

								hardwareConfigTable += u'CHANGE `{column}` `{column}` {type} NULL,\n'.format(
									column=value,
									type=valueInfo['Type']
								)
							else:
								# Column does not exist => add
								yield hardwareConfigTable + u' ADD COLUMN `{column}` {type} NULL;'.format(
									column=value,
									type=valueInfo['Type']
								)
								avoidProcessingFurtherHardwareConfig = True
						else:
							hardwareConfigTable += u'`%s` %s NULL,\n' % (value, valueInfo['Type'])
						hardwareConfigValuesProcessed += 1

				if avoidProcessingFurtherHardwareConfig or avoidProcessingFurtherHardwareDevice:
					continue

				if not hardwareDeviceTableExists:
					hardwareDeviceTable += u'PRIMARY KEY (`hardware_id`)\n'
				if not hardwareConfigTableExists:
					hardwareConfigTable += u'PRIMARY KEY (`config_id`)\n'

				# Remove leading and trailing whitespace
				hardwareDeviceTable = hardwareDeviceTable.strip()
				hardwareConfigTable = hardwareConfigTable.strip()

				hardwareDeviceTable = removeTrailingComma(hardwareDeviceTable)
				hardwareConfigTable = removeTrailingComma(hardwareConfigTable)

				hardwareDeviceTable += finishSQLQuery(hardwareDeviceTableExists, hardwareDeviceTableName)
				hardwareConfigTable += finishSQLQuery(hardwareConfigTableExists, hardwareConfigTableName)

				if hardwareDeviceValuesProcessed or not hardwareDeviceTableExists:
					yield hardwareDeviceTable

				if hardwareConfigValuesProcessed or not hardwareConfigTableExists:
					yield hardwareConfigTable

		for statement in getSQLStatements():
			logger.debug2("Processing statement {0!r}", statement)
			self._sql.execute(statement)
			logger.debug2("Done with statement.")


class SQLiteObjectBackendModificationTracker(SQLBackendObjectModificationTracker):
	def __init__(self, **kwargs):
		SQLBackendObjectModificationTracker.__init__(self, **kwargs)
		self._sql = SQLite(**kwargs)
		self._createTables()
