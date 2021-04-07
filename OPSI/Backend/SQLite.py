# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
SQLite backend.
"""

import os
import sqlite3
import threading

from OPSI.Backend.SQL import SQL, SQLBackend, SQLBackendObjectModificationTracker
from OPSI.Exceptions import BackendBadValueError
from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceFilename

__all__ = ('SQLite', 'SQLiteBackend', 'SQLiteObjectBackendModificationTracker')

logger = Logger()


class SQLite(SQL):
	AUTOINCREMENT = ''
	ALTER_TABLE_CHANGE_SUPPORTED = False
	ESCAPED_BACKSLASH = "\\"
	ESCAPED_APOSTROPHE = "''"
	ESCAPED_ASTERISK = "**"
	_WRITE_LOCK = threading.Lock()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

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
		logger.debug('SQLite created: %s', self)

	def delete_db(self):
		if self._connection:
			try:
				self._connection.close()
			except Exception as err:  # pylint: disable=broad-except
				logger.warning(err)
		self._connection = None
		self._cursor = None
		if os.path.exists(self._database):
			os.remove(self._database)

	def connect(self, cursorType=None):
		with self._WRITE_LOCK:
			for trynum in (1, 2):
				try:
					if not self._connection:
						logger.debug("Connecting to sqlite database '%s'", self._database)
						# When using multiple threads with the same connection writing operations
						# should be serialized by the user to avoid data corruption
						self._connection = sqlite3.connect(self._database, check_same_thread=False)
					if not self._cursor:
						def dict_factory(cursor, row):
							_dict = {}
							for idx, col in enumerate(cursor.description):
								_dict[col[0]] = row[idx]
							return _dict
						self._connection.row_factory = dict_factory
						self._cursor = self._connection.cursor()
						if not self._synchronous:
							self._cursor.execute('PRAGMA synchronous=OFF')
							self._cursor.execute('PRAGMA temp_store=MEMORY')
							self._cursor.execute('PRAGMA cache_size=5000')
						if self._databaseCharset.lower() in ('utf8', 'utf-8'):
							self._cursor.execute('PRAGMA encoding="UTF-8"')
					return (self._connection, self._cursor)
				except sqlite3.DatabaseError as dbError:
					logger.error("SQLite database '%s' is defective: %s", self._database, dbError)
					if trynum > 1:
						raise
					logger.warning("Recreating defective sqlite database '%s'", self._database)
					self.delete_db()
				except Exception as err:  # pylint: disable=broad-except
					logger.warning("Problem connecting to SQLite database: %s", err)
					if trynum > 1:
						raise

	def close(self, conn, cursor):
		pass

	def getSet(self, query):
		logger.trace("getSet: %s", query)
		(conn, cursor) = self.connect()
		valueSet = []
		try:
			self.execute(query, conn, cursor)
			valueSet = cursor.fetchall()
			if not valueSet:
				logger.debug("No result for query '%s'", query)
				valueSet = []
		finally:
			self.close(conn, cursor)
		return valueSet

	def getRow(self, query, conn=None, cursor=None):  # pylint: disable=unused-argument
		logger.trace("getRow: %s", query)
		(conn, cursor) = self.connect()
		row = {}
		try:
			self.execute(query, conn, cursor)
			try:
				row = cursor.fetchone()
			except Exception as err:  # pylint: disable=broad-except
				logger.trace("Failed to fetch data: %s", err)

			if not row:
				logger.debug("No result for query '%s'", query)
				row = {}
			else:
				logger.trace("Result: '%s'", row)
		finally:
			self.close(conn, cursor)
		return row

	def insert(self, table, valueHash, conn=None, cursor=None):  # pylint: disable=unused-argument
		(conn, cursor) = self.connect()
		result = -1
		try:
			colNames = []
			values = []
			for (key, value) in valueHash.items():
				colNames.append(f"`{key}`")
				if value is None:
					values.append("NULL")
				elif isinstance(value, bool):
					if value:
						values.append("1")
					else:
						values.append("0")
				elif isinstance(value, (float, int)):
					values.append(f"{value}")
				else:
					values.append(f"'{self.escapeApostrophe(self.escapeBackslash(value))}'")

			query = f"INSERT INTO `{table}` ({', '.join(colNames)}) VALUES ({', '.join(values)});"
			logger.trace("insert: %s", query)

			with self._WRITE_LOCK:
				self.execute(query, conn, cursor)
				result = cursor.lastrowid
				conn.commit()
		finally:
			self.close(conn, cursor)

		return result

	def update(self, table, where, valueHash, updateWhereNone=False):
		(conn, cursor) = self.connect()
		result = 0
		try:
			if not valueHash:
				raise BackendBadValueError("No values given")

			values = []
			for (key, value) in valueHash.items():
				if value is None and not updateWhereNone:
					continue

				if value is None:
					values.append(f"`{key}` = NULL")
				elif isinstance(value, bool):
					if value:
						values.append(f"`{key}` = 1")
					else:
						values.append(f"`{key}` = 0")
				elif isinstance(value, (float, int)):
					values.append(f"`{key}` = {value}")
				else:
					values.append(f"`{key}` = '{self.escapeApostrophe(self.escapeBackslash(value))}'")

			query = f"UPDATE `{table}` SET {', '.join(values)} WHERE {where};"
			logger.trace("update: %s", query)
			with self._WRITE_LOCK:
				result = self.execute(query, conn, cursor).rowcount
				conn.commit()
		finally:
			self.close(conn, cursor)
		return result

	def delete(self, table, where, conn=None, cursor=None):  # pylint: disable=unused-argument
		(conn, cursor) = self.connect()
		result = 0
		try:
			query = "DELETE FROM `%s` WHERE %s;" % (table, where)
			logger.trace("delete: %s", query)
			with self._WRITE_LOCK:
				result = self.execute(query, conn, cursor).rowcount
				conn.commit()
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
			logger.trace("SQL query: %s", query)
			res = cursor.execute(query)
		finally:
			if needClose:
				self.close(conn, cursor)

		return res

	def getTables(self):
		"""
		Get what tables are present in the database.

		Table names will always be uppercased.

		:returns: A dict with the tablename as key and the field names as value.
		:rtype: dict
		"""
		tables = {}
		logger.trace("Current tables:")
		for i in self.getSet('SELECT name FROM sqlite_master WHERE type = "table";'):
			tableName = tuple(i.values())[0].upper()
			logger.trace(" [ %s ]", tableName)
			fields = [j['name'] for j in self.getSet('PRAGMA table_info(`%s`);' % tableName)]
			tables[tableName] = fields
			logger.trace("Fields in %s: %s", tableName, fields)

		return tables

	def getTableCreationOptions(self, table):
		return ''


class SQLiteBackend(SQLBackend):

	def __init__(self, **kwargs):
		self._name = 'sqlite'

		SQLBackend.__init__(self, **kwargs)

		self._sql = SQLite(**kwargs)

		self._licenseManagementEnabled = True
		self._licenseManagementModule = True
		self._sqlBackendModule = True
		logger.debug('SQLiteBackend created: %s', self)

	def backend_createBase(self):
		try:
			return SQLBackend.backend_createBase(self)
		except sqlite3.DatabaseError as dbError:
			logger.error("SQLite database %s is defective: %s, recreating", self._sql, dbError)
			self._sql.delete_db()
			self._sql.connect()
			return SQLBackend.backend_createBase(self)

	def _createAuditHardwareTables(self):  # pylint: disable=too-many-statements
		"""
		Creating tables for hardware audit data.

		The speciatly for SQLite is that an ALTER TABLE may not list
		multiple columns to alter but instead has to alter one column
		after another.
		"""
		tables = self._sql.getTables()
		existingTables = set(tables.keys())

		def removeTrailingComma(query):
			if query.endswith(','):
				return query[:-1]

			return query

		def finishSQLQuery(tableExists, tableName):
			if tableExists:
				return ' ;\n'
			return '\n) %s;\n' % self._sql.getTableCreationOptions(tableName)

		def getSQLStatements():  # pylint: disable=too-many-branches,too-many-statements
			for (hwClass, values) in self._auditHardwareConfig.items():  # pylint: disable=too-many-nested-blocks
				logger.debug("Processing hardware class '%s'", hwClass)
				hardwareDeviceTableName = f"HARDWARE_DEVICE_{hwClass}"
				hardwareConfigTableName = f"HARDWARE_CONFIG_{hwClass}"

				hardwareDeviceTableExists = hardwareDeviceTableName in existingTables
				hardwareConfigTableExists = hardwareConfigTableName in existingTables

				if hardwareDeviceTableExists:
					hardwareDeviceTable = f"ALTER TABLE `{hardwareDeviceTableName}`\n"
				else:
					hardwareDeviceTable = (
						f"CREATE TABLE `{hardwareDeviceTableName}` (\n"
						f"`hardware_id` INTEGER NOT NULL {self._sql.AUTOINCREMENT},\n"
					)

				avoid_process_further_hw_dev = False
				hardwareDeviceValuesProcessed = 0
				for (value, valueInfo) in values.items():
					logger.debug("  Processing value '%s'", value)
					if valueInfo['Scope'] == 'g':
						if hardwareDeviceTableExists:
							if value in tables[hardwareDeviceTableName]:
								# Column exists => change
								if not self._sql.ALTER_TABLE_CHANGE_SUPPORTED:
									continue
								hardwareDeviceTable += f"CHANGE `{value}` `{value}` {valueInfo['Type']} NULL,\n"
							else:
								# Column does not exist => add
								yield f"{hardwareDeviceTable} ADD COLUMN `{value}` {valueInfo['Type']} NULL;"
								avoid_process_further_hw_dev = True
						else:
							hardwareDeviceTable += f"`{value}` {valueInfo['Type']} NULL,\n"
						hardwareDeviceValuesProcessed += 1

				if hardwareConfigTableExists:
					hardwareConfigTable = f"ALTER TABLE `{hardwareConfigTableName}`\n"
				else:
					hardwareConfigTable = (
						f"CREATE TABLE `{hardwareConfigTableName}` (\n"
						f"`config_id` INTEGER NOT NULL {self._sql.AUTOINCREMENT},\n"
						"`hostId` varchar(255) NOT NULL,\n"
						"`hardware_id` INTEGER NOT NULL,\n"
						"`firstseen` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',\n"
						"`lastseen` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',\n"
						"`state` TINYINT NOT NULL,\n"
					)

				avoid_process_further_hw_cnf = False
				hardwareConfigValuesProcessed = 0
				for (value, valueInfo) in values.items():
					logger.debug("  Processing value '%s'", value)
					if valueInfo['Scope'] == 'i':
						if hardwareConfigTableExists:
							if value in tables[hardwareConfigTableName]:
								# Column exists => change
								if not self._sql.ALTER_TABLE_CHANGE_SUPPORTED:
									continue

								hardwareConfigTable += f"CHANGE `{value}` `{value}` {valueInfo['Type']} NULL,\n"
							else:
								# Column does not exist => add
								yield f"{hardwareConfigTable} ADD COLUMN `{value}` {valueInfo['Type']} NULL;"
								avoid_process_further_hw_cnf = True
						else:
							hardwareConfigTable += f"`{value}` {valueInfo['Type']} NULL,\n"
						hardwareConfigValuesProcessed += 1

				if avoid_process_further_hw_cnf or avoid_process_further_hw_dev:
					continue

				if not hardwareDeviceTableExists:
					hardwareDeviceTable += 'PRIMARY KEY (`hardware_id`)\n'
				if not hardwareConfigTableExists:
					hardwareConfigTable += 'PRIMARY KEY (`config_id`)\n'

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
			logger.trace("Processing statement %s", statement)
			self._sql.execute(statement)
			logger.trace("Done with statement.")


class SQLiteObjectBackendModificationTracker(SQLBackendObjectModificationTracker):
	def __init__(self, **kwargs):
		SQLBackendObjectModificationTracker.__init__(self, **kwargs)
		self._sql = SQLite(**kwargs)
		self._createTables()
