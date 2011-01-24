#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - SQLite    =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

# Imports
import os, threading
try:
	from apsw import *
except:
	pass

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *
from OPSI.Backend.SQL import *

# Get logger instance
logger = Logger()


class SQLite(SQL):
	AUTOINCREMENT = ''
	ALTER_TABLE_CHANGE_SUPPORTED = False
	
	def __init__(self, **kwargs):
		self._database = ":memory:"
		self._synchronous = True
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('database',):
				self._database = forceFilename(value)
			if option in ('synchronous',):
				self._synchronous = forceBool(value)
		
		self._connection = None
		self._transactionLock = threading.Lock()
		logger.debug(u'SQLite created: %s' % self)
	
	def connect(self):
		#self._transactionLock.acquire()
		logger.debug2(u"Connecting to sqlite db '%s'" % self._database)
		if not self._connection:
			self._connection = Connection(
				filename           = self._database,
				flags              = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_CONFIG_MULTITHREAD,
				vfs                = None,
				statementcachesize = 100
			)
			if not self._synchronous:
				self._connection.cursor().execute('PRAGMA synchronous=OFF')
			
		def rowtrace(cursor, row):
			valueSet = {}
			names = cursor.getdescription()
			for i in range(len(row)):
				valueSet[names[i][0]] = row[i]
			return valueSet
		
		cursor = self._connection.cursor()
		cursor.setrowtrace(rowtrace)
		return (self._connection, cursor)
	
	def close(self, conn, cursor):
		#self._transactionLock.release()
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
					values += u"\'%s\', " % (u'%s' % value.decode("utf-8")).replace("'", "''")
				else:
					values += u"\'%s\', " % (u'%s' % value).replace("'", "''")
				
			query = u'INSERT INTO `%s` (%s) VALUES (%s);' % (table, colNames[:-2], values[:-2])
			logger.debug2(u"insert: %s" % query)
			self.execute(query, conn, cursor)
			result = conn.changes()
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
					query += u"\'%s\', " % (u'%s' % value.decode("utf-8")).replace("'", "\\\'")
				else:
					query += u"\'%s\', " % (u'%s' % value).replace("'", "\\\'")
			
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
			query = forceUnicode(query)
			logger.debug2(u"SQL query: %s" % query)
			res = cursor.execute(query)
			#cursor.execute("commit")
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
	
	ESCAPE_BACKSLASH = False
	
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


if (__name__ == "__main__"):
	logger.setConsoleLevel(LOG_DEBUG)
	logger.setConsoleColor(True)
	backend = SQLiteBackend()
	backend.backend_createBase()
	





















