# -*- coding: utf-8 -*-
"""
opsi python library - SQLite

This module is part of the desktop management solution opsi
(open pc server integration) http://www.opsi.org

Copyright (C) 2013 uib GmbH

http://www.uib.de/

All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License, version 3
as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Affero General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@copyright:	uib GmbH <info@uib.de>
@author: Jan Schneider <j.schneider@uib.de>
@author: Erol Ueluekmen <e.ueluekmen@uib.de>
@license: GNU Affero GPL version 3
"""

__version__ = '4.0.3.4'

import threading

from apsw import (SQLITE_OPEN_CREATE, SQLITE_CONFIG_MULTITHREAD,
				  SQLITE_OPEN_READWRITE, Connection)

from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceFilename, forceUnicode
from OPSI.Types import BackendBadValueError
from OPSI.Backend.SQL import SQL, SQLBackend, SQLBackendObjectModificationTracker

logger = Logger()


class SQLite(SQL):
	AUTOINCREMENT = ''
	ALTER_TABLE_CHANGE_SUPPORTED = False
	ESCAPED_BACKSLASH  = "\\"
	ESCAPED_APOSTROPHE = "''"
	ESCAPED_ASTERISK   = "**"

	def __init__(self, **kwargs):
		self._database        = ":memory:"
		self._synchronous     = True
		self._databaseCharset = 'utf8'
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('database',):
				self._database = forceFilename(value)
			elif option in ('synchronous',):
				self._synchronous = forceBool(value)
			elif option in ('databasecharset',):
				self._databaseCharset = str(value)

		self._connection = None
		self._cursor = None
		self._transactionLock = threading.Lock()
		logger.debug(u'SQLite created: %s' % self)

	def connect(self):
		# self._transactionLock.acquire()
		try:
			logger.debug2(u"Connecting to sqlite db '%s'" % self._database)
			if not self._connection:
				self._connection = Connection(
					filename           = self._database,
					flags              = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_CONFIG_MULTITHREAD,
					vfs                = None,
					statementcachesize = 100
				)
			if not self._cursor:
				def rowtrace(cursor, row):
					valueSet = {}
					names = cursor.getdescription()
					for i in range(len(row)):
						valueSet[names[i][0]] = row[i]
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
		except:
			# self._transactionLock.release()
			raise

	def close(self, conn, cursor):
		pass
		# try:
		# 	self._transactionLock.release()
		# except:
		# 	pass
		# cursor.close()

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
			except:
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
			colNames = values = u''
			for (key, value) in valueHash.items():
				colNames += u"`%s`, " % key
				if value is None:
					values += u"NULL, "
				elif type(value) is bool:
					if value:
						values += u"1, "
					else:
						values += u"0, "
				elif type(value) in (float, long, int):
					values += u"%s, " % value
				elif type(value) is str:
					values += u"\'%s\', " % (u'%s' % self.escapeApostrophe(self.escapeBackslash(value.decode("utf-8"))))
				else:
					values += u"\'%s\', " % (u'%s' % self.escapeApostrophe(self.escapeBackslash(value)))

			query = u'INSERT INTO `%s` (%s) VALUES (%s);' % (table, colNames[:-2], values[:-2])
			logger.debug2(u"insert: %s" % query)

			self.execute(query, conn, cursor)
			# result = conn.changes()
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
			query = u"UPDATE `%s` SET " % table
			for (key, value) in valueHash.items():
				if value is None and not updateWhereNone:
					continue
				query += u"`%s` = " % key
				if value is None:
					query += u"NULL, "
				elif type(value) is bool:
					if value:
						query += u"1, "
					else:
						query += u"0, "
				elif type(value) in (float, long, int):
					query += u"%s, " % value
				elif type(value) is str:
					query += u"\'%s\', " % (u'%s' % self.escapeApostrophe(self.escapeBackslash(value.decode("utf-8"))))
				else:
					query += u"\'%s\', " % (u'%s' % self.escapeApostrophe(self.escapeBackslash(value)))

			query = u'%s WHERE %s;' % (query[:-2], where)
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
			# query = forceUnicode(query)
			logger.debug2(u"SQL query: %s" % forceUnicode(query))
			res = cursor.execute(query)
			# cursor.execute("commit")
		finally:
			if needClose:
				self.close(conn, cursor)
		return res

	def getTables(self):
		tables = {}
		logger.debug(u"Current tables:")
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


class SQLiteObjectBackendModificationTracker(SQLBackendObjectModificationTracker):
	def __init__(self, **kwargs):
		SQLBackendObjectModificationTracker.__init__(self, **kwargs)
		self._sql = SQLite(**kwargs)
		self._createTables()
