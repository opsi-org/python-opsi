#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - MySQL   =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
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

__version__ = '3.5'

# Imports
import MySQLdb, warnings, time, json
from _mysql_exceptions import *
from sqlalchemy import pool

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *

# Get logger instance
logger = Logger()

class ConnectionPool(object):
	# Storage for the instance reference
	__instance = None
	
	def __init__(self, **kwargs):
		""" Create singleton instance """
		
		# Check whether we already have an instance
		if ConnectionPool.__instance is None:
			# Create and remember instance
			poolArgs = {}
			for key in ('pool_size', 'max_overflow', 'timeout'):
				if key in kwargs.keys():
					poolArgs[key] = kwargs[key]
					del kwargs[key]
			def creator():
				return MySQLdb.connect(**kwargs)
			ConnectionPool.__instance = pool.QueuePool(creator, **poolArgs)
		
		# Store instance reference as the only member in the handle
		self.__dict__['_ConnectionPool__instance'] = ConnectionPool.__instance
	
	def __getattr__(self, attr):
		""" Delegate access to implementation """
		return getattr(self.__instance, attr)

	def __setattr__(self, attr, value):
		""" Delegate access to implementation """
	 	return setattr(self.__instance, attr, value)
	
# ======================================================================================================
# =                                       CLASS MYSQL                                                  =
# ======================================================================================================

class MySQL:
	def __init__(self, username = 'root', password = '', address = 'localhost', database = 'opsi'):
		self._username = username
		self._password = password
		self._address  = address
		self._database = database
		self._mysql = ConnectionPool(
				host         = self._address,
				user         = self._username,
				passwd       = self._password,
				db           = self._database,
				use_unicode  = True,
				charset      = 'utf8',
				pool_size    = 20,
				max_overflow = 10,
				timeout      = 30
		)
		#print self._mysql.status()
		#try:
		#	self._conn = mysql.connect()
		#except Exception, e:
		#	raise BackendIOError(u"Failed to connect to database '%s' address '%s': %s" % (self._database, self._address, e))
		#
		#self._cursor = self._conn.cursor(MySQLdb.cursors.DictCursor)
	
	def connect(self):
		conn = self._mysql.connect()
		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		return (conn, cursor)
		
	def close(self, conn, cursor):
		cursor.close()
		conn.close()
		#if not self._conn:
		#	return
		#logger.info(u"Closing database connection")
		#self._cursor.close()
		#self._conn.commit()
		#self._conn.close()
	
	def query(self, query):
		(conn, cursor) = self.connect()
		logger.debug2(u"query: %s" % query)
		self.execute(query, conn, cursor)
		self.close(conn, cursor)
		return cursor.rowcount
		
	def getSet(self, query):
		logger.debug2(u"getSet: %s" % query)
		(conn, cursor) = self.connect()
		self.execute(query, conn, cursor)
		valueSet = cursor.fetchall()
		if not valueSet:
			logger.debug(u"No result for query '%s'" % query)
			return []
		self.close(conn, cursor)
		return valueSet
		
	def getRow(self, query):
		logger.debug2(u"getRow: %s" % query)
		(conn, cursor) = self.connect()
		self.execute(query, conn, cursor)
		row = cursor.fetchone()
		if not row:
			logger.debug(u"No result for query '%s'" % query)
			return {}
		logger.debug2(u"Result: '%s'" % row)
		self.close(conn, cursor)
		return row
		
	def insert(self, table, valueHash):
		(conn, cursor) = self.connect()
		colNames = values = u''
		for (key, value) in valueHash.items():
			colNames += u"`%s`, " % key
			if value is None:
				values += u"NULL, "
			elif type(value) in (float, long, int, bool):
				values += u"%s, " % value
			elif type(value) is str:
				values += u"\'%s\', " % (u'%s' % value.decode("utf-8")).replace("\\", "\\\\").replace("'", "\\\'")
			else:
				values += u"\'%s\', " % (u'%s' % value).replace("\\", "\\\\").replace("'", "\\\'")
			
		query = u'INSERT INTO `%s` (%s) VALUES (%s);' % (table, colNames[:-2], values[:-2])
		logger.debug2(u"insert: %s" % query)
		self.execute(query, conn, cursor)
		result = cursor.lastrowid
		self.close(conn, cursor)
		return result
		
	def update(self, table, where, valueHash):
		(conn, cursor) = self.connect()
		if not valueHash:
			raise BackendBadValueError(u"No values given")
		query = u"UPDATE `%s` SET " % table
		for (key, value) in valueHash.items():
			if value is None:
				continue
			query += u"`%s` = " % key
			if type(value) in (float, long, int, bool):
				query += u"%s, " % value
			elif type(value) is str:
				query += u"\'%s\', " % (u'%s' % value.decode("utf-8")).replace("\\", "\\\\").replace("'", "\\\'")
			else:
				query += u"\'%s\', " % (u'%s' % value).replace("\\", "\\\\").replace("'", "\\\'")
		
		query = u'%s WHERE %s;' % (query[:-2], where)
		logger.debug2(u"update: %s" % query)
		self.execute(query, conn, cursor)
		return cursor.lastrowid
	
	def delete(self, table, where):
		(conn, cursor) = self.connect()
		query = u"DELETE FROM `%s` WHERE %s;" % (table, where)
		logger.debug2(u"delete: %s" % query)
		self.execute(query, conn, cursor)
		result = cursor.lastrowid
		self.close(conn, cursor)
		return result
	
	
	def execute(self, query, conn=None, cursor=None):
		if not conn or not cursor:
			(conn, cursor) = self.connect()
		if not type(query) is unicode:
			query = unicode(query, 'utf-8', 'replace')
		res = cursor.execute(query)
		conn.commit()
		return res
	
	#def info(self, conn):
	#	return conn.info()
	#
	#def warningCount(self):
	#	return conn.warning_count()
	

# ======================================================================================================
# =                                    CLASS MYSQLBACKEND                                              =
# ======================================================================================================
class MySQLBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._address  = 'localhost'
		self._database = 'opsi'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('address'):
				self._address = value
			elif option in ('database'):
				self._database = value
			
		warnings.showwarning = self._showwarning
		self._mysql = MySQL(username = self._username, password = self._password, address = self._address, database = self._database)
		
		self._licenseManagementEnabled = True
		
	def _showwarning(self, message, category, filename, lineno, line=None, file=None):
		#logger.warning(u"%s (file: %s, line: %s)" % (message, filename, lineno))
		if str(message).startswith('Data truncated for column'):
			logger.error(message)
		else:
			logger.warning(message)
	
	def _createQuery(self, table, attributes=[], filter={}):
		where = u''
		select = u''
		query = u''
		for attribute in attributes:
			if select:
				select += u','
			select += u'`%s`' % attribute
		
		for (key, values) in filter.items():
			if values is None:
				continue
			values = forceList(values)
			if not values:
				continue
			if where:
				where += u' and '
			where += u'('
			for value in values:
				operator = '='
				if type(value) in (float, long, int, bool):
					where += u"`%s` %s %s" % (key, operator, value)
				elif value is None:
					where += u"`%s` is NULL" % key
				else:
					match = re.search('^\s*([>=<]+)\s*(\S+)', value)
					if match:
						operator = match.group(1)
						value = match.group(2)
					
					if (value.find('*') != -1):
						operator = 'LIKE'
						value = value.replace('%', '\%').replace('_', '\_').replace('*', '%')
					
					where += u"`%s` %s '%s'" % (key, operator, value)
				where += u' or '
			where = where[:-4] + u')'
		result = []
		if not select:
			select = u'*'
		if where:
			query = u'select %s from `%s` where %s' % (select, table, where)
		else:
			query = u'select %s from `%s`' % (select, table)
		logger.debug(u"Created query: '%s'" % query)
		return query
	
	def _adjustAttributes(self, objectClass, attributes, filter):
		if not attributes:
			attributes = []
		attributes = forceUnicodeList(attributes)
		id = self._objectAttributeToDatabaseAttribute(objectClass, 'id')
		if filter.has_key('id'):
			filter[id] = filter['id']
			del filter['id']
		if 'id' in attributes:
			attributes.remove('id')
			attributes.append(id)
		if attributes:
			if issubclass(objectClass, Entity) and not 'type' in attributes:
				attributes.append('type')
			objectClasses = [ objectClass ]
			objectClasses.extend(objectClass.subClasses.values())
			for oc in objectClasses:
				for arg in mandatoryConstructorArgs(oc):
					if (arg == 'id'):
						arg = id
					if not arg in attributes:
						attributes.append(arg)
		return (attributes, filter)
		
	def _adjustResult(self, objectClass, result):
		id = self._objectAttributeToDatabaseAttribute(objectClass, 'id')
		if result.has_key(id):
			result['id'] = result[id]
			del result[id]
		return result
	
	def _objectToDatabaseHash(self, object):
		hash = object.toHash()
		for (key, value) in hash.items():
			arg = self._objectAttributeToDatabaseAttribute(object.__class__, key)
			if (key != arg):
				hash[arg] = hash[key]
				del hash[key]
		return hash
		
	def _objectAttributeToDatabaseAttribute(self, objectClass, attribute):
		if (attribute == 'id'):
			# A class is considered a subclass of itself
			if issubclass(objectClass, Product):
				return 'productId'
			if issubclass(objectClass, Host):
				return 'hostId'
			if issubclass(objectClass, Group):
				return 'groupId'
			if issubclass(objectClass, Config):
				return 'configId'
			if issubclass(objectClass, LicenseContract):
				return 'licenseContractId'
			if issubclass(objectClass, SoftwareLicense):
				return 'softwareLicenseId'
			if issubclass(objectClass, LicensePool):
				return 'licensePoolId'
		return attribute
	
	def _uniqueCondition(self, object):
		condition = u''
		args = mandatoryConstructorArgs(object.__class__)
		for arg in args:
			value = eval('object.%s' % arg)
			arg = self._objectAttributeToDatabaseAttribute(object.__class__, arg)
			if condition:
				condition += u' and '
			if type(value) in (float, long, int, bool):
				condition += u"`%s` = %s" % (arg, value)
			else:
				condition += u"`%s` = '%s'" % (arg, value)
		return condition
	
	def exit(self):
		if self._mysql:
			self._mysql.close()
	
	def base_delete(self):
		ConfigDataBackend.base_delete(self)
		# Drop database
		errors = 0
		done = False
		while not done and (errors < 100):
			done = True
			for i in self._mysql.getSet(u'SHOW TABLES;'):
				try:
					logger.debug(u'DROP TABLE `%s`;' % i.values()[0])
					self._mysql.execute(u'DROP TABLE `%s`;' % i.values()[0])
				except Exception, e:
					logger.error(e)
					done = False
					errors += 1
		
	def base_create(self):
		ConfigDataBackend.base_create(self)
		# Hardware audit database
		tables = {}
		logger.debug(u"Current tables:")
		for i in self._mysql.getSet(u'SHOW TABLES;'):
			tableName = i.values()[0]
			logger.debug(u" [ %s ]" % tableName)
			tables[tableName] = []
			for j in self._mysql.getSet(u'SHOW COLUMNS FROM `%s`' % tableName):
				logger.debug(u"      %s" % j)
				tables[tableName].append(j['Field'])
		
		logger.notice(u'Creating opsi base')
		
		# Host table
		if not 'HOST' in tables.keys():
			logger.debug(u'Creating table HOST')
			table = u'''CREATE TABLE `HOST` (
					`hostId` varchar(255) NOT NULL,
					PRIMARY KEY( `hostId` ),
					`type` varchar(30),
					INDEX(`type`),
					`description` varchar(100),
					`notes` varchar(500),
					`hardwareAddress` varchar(17),
					`ipAddress` varchar(15),
					`inventoryNumber` varchar(30),
					`created` TIMESTAMP,
					`lastSeen` TIMESTAMP,
					`opsiHostKey` varchar(32),
					`maxBandwidth` int,
					`depotLocalUrl` varchar(128),
					`depotRemoteUrl` varchar(255),
					`repositoryLocalUrl` varchar(128),
					`repositoryRemoteUrl` varchar(255),
					`networkAddress` varchar(31)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'CONFIG' in tables.keys():
			logger.debug(u'Creating table CONFIG')
			table = u'''CREATE TABLE `CONFIG` (
					`configId` varchar(200) NOT NULL,
					PRIMARY KEY( `configId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`description` varchar(256),
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'CONFIG_VALUE' in tables.keys():
			logger.debug(u'Creating table CONFIG_VALUE')
			table = u'''CREATE TABLE `CONFIG_VALUE` (
					`config_value_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `config_value_id` ),
					`configId` varchar(200) NOT NULL,
					FOREIGN KEY ( `configId` ) REFERENCES `CONFIG` ( `configId` ),
					`value` TEXT,
					`isDefault` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'CONFIG_STATE' in tables.keys():
			logger.debug(u'Creating table CONFIG_STATE')
			table = u'''CREATE TABLE `CONFIG_STATE` (
					`config_state_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `config_state_id` ),
					`configId` varchar(200) NOT NULL,
					INDEX(`configId`),
					`objectId` varchar(255) NOT NULL,
					INDEX(`objectId`),
					`values` text
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT' in tables.keys():
			logger.debug(u'Creating table PRODUCT')
			table = u'''CREATE TABLE `PRODUCT` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					PRIMARY KEY( `productId`, `productVersion`, `packageVersion` ),
					`type` varchar(32) NOT NULL,
					INDEX(`type`),
					`name` varchar(128) NOT NULL,
					`licenseRequired` varchar(50),
					`setupScript` varchar(50),
					`uninstallScript` varchar(50),
					`updateScript` varchar(50),
					`alwaysScript` varchar(50),
					`onceScript` varchar(50),
					`customScript` varchar(50),
					`userLoginScript` varchar(50),
					`priority` int,
					`description` TEXT,
					`advice` TEXT,
					`pxeConfigTemplate` varchar(50),
					`changelog` TEXT
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'WINDOWS_SOFTWARE_ID_TO_PRODUCT' in tables.keys():
			logger.debug(u'Creating table WINDOWS_SOFTWARE_ID_TO_PRODUCT')
			table = u'''CREATE TABLE `WINDOWS_SOFTWARE_ID_TO_PRODUCT` (
					`windowsSoftwareId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `windowsSoftwareId`),
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES `PRODUCT` ( `productId` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_ON_DEPOT' in tables.keys():
			logger.debug(u'Creating table PRODUCT_ON_DEPOT')
			table = u'''CREATE TABLE `PRODUCT_ON_DEPOT` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion` ) REFERENCES `PRODUCT` ( `productId`, `productVersion`, `packageVersion` ),
					`depotId` varchar(50) NOT NULL,
					FOREIGN KEY ( `depotId` ) REFERENCES HOST( `hostId` ),
					PRIMARY KEY(  `productId`, `depotId` ),
					`productType` varchar(16) NOT NULL,
					INDEX(`productType`),
					`locked` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_PROPERTY' in tables.keys():
			logger.debug(u'Creating table PRODUCT_PROPERTY')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`propertyId` varchar(200) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion` ) REFERENCES `PRODUCT` ( `productId`, `productVersion`, `packageVersion` ),
					PRIMARY KEY( `productId`, `productVersion`, `packageVersion`, `propertyId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`description` varchar(256),
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_PROPERTY_VALUE' in tables.keys():
			logger.debug(u'Creating table PRODUCT_PROPERTY_VALUE')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY_VALUE` (
					`product_property_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `product_property_id` ),
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`propertyId` varchar(200) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion`, `propertyId` ) REFERENCES `PRODUCT_PROPERTY` ( `productId`, `productVersion`, `packageVersion`, `propertyId` ),
					`value` text,
					`isDefault` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_DEPENDENCY' in tables.keys():
			logger.debug(u'Creating table PRODUCT_DEPENDENCY')
			table = u'''CREATE TABLE `PRODUCT_DEPENDENCY` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion` ) REFERENCES `PRODUCT` ( `productId`, `productVersion`, `packageVersion` ),
					`productAction` varchar(16) NOT NULL,
					`requiredProductId` varchar(50) NOT NULL,
					PRIMARY KEY( `productId`, `productVersion`, `packageVersion`, `productAction`, `requiredProductId` ),
					`requiredProductVersion` varchar(16),
					`requiredPackageVersion` varchar(16),
					`requiredAction` varchar(16),
					`requiredInstallationStatus` varchar(16),
					`requirementType` varchar(16)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
			
		if not 'PRODUCT_ON_CLIENT' in tables.keys():
			logger.debug(u'Creating table PRODUCT_ON_CLIENT')
			table = u'''CREATE TABLE `PRODUCT_ON_CLIENT` (
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES PRODUCT( `productId` ),
					`clientId` varchar(255) NOT NULL,
					FOREIGN KEY ( `clientId` ) REFERENCES `HOST` ( `hostId` ),
					PRIMARY KEY( `productId`, `clientId` ),
					`productType` varchar(16) NOT NULL,
					`installationStatus` varchar(16),
					`actionRequest` varchar(16),
					`actionProgress` varchar(255),
					`productVersion` varchar(16),
					`packageVersion` varchar(16),
					`lastStateChange` TIMESTAMP
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_PROPERTY_STATE' in tables.keys():
			logger.debug(u'Creating table PRODUCT_PROPERTY_STATE')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY_STATE` (
					`product_property_state_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `product_property_state_id` ),
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES `PRODUCT` ( `productId` ),
					`propertyId` varchar(200) NOT NULL,
					`objectId` varchar(255) NOT NULL,
					INDEX(`objectId`),
					`values` text
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'GROUP' in tables.keys():
			logger.debug(u'Creating table GROUP')
			table = u'''CREATE TABLE `GROUP` (
					`groupId` varchar(255) NOT NULL,
					PRIMARY KEY( `groupId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`parentGroupId` varchar(255),
					INDEX(`parentGroupId`),
					`description` varchar(100),
					`notes` varchar(500)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'OBJECT_TO_GROUP' in tables.keys():
			logger.debug(u'Creating table OBJECT_TO_GROUP')
			table = u'''CREATE TABLE `OBJECT_TO_GROUP` (
					`groupId` varchar(255) NOT NULL,
					FOREIGN KEY ( `groupId` ) REFERENCES `GROUP` ( `groupId` ),
					`objectId` varchar(255) NOT NULL,
					PRIMARY KEY( `groupId`, `objectId` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'LICENSE_CONTRACT' in tables.keys():
			logger.debug(u'Creating table LICENSE_CONTRACT')
			table = u'''CREATE TABLE `LICENSE_CONTRACT` (
					`licenseContractId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `licenseContractId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`description` varchar(100),
					`notes` varchar(1000),
					`partner` varchar(100),
					`conclusionDate` TIMESTAMP,
					`notificationDate` TIMESTAMP,
					`expirationDate` TIMESTAMP
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'SOFTWARE_LICENSE' in tables.keys():
			logger.debug(u'Creating table SOFTWARE_LICENSE')
			table = u'''CREATE TABLE `SOFTWARE_LICENSE` (
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `softwareLicenseId` ),
					`licenseContractId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `licenseContractId` ) REFERENCES LICENSE_CONTRACT( `licenseContractId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`boundToHost` varchar(50),
					INDEX(`boundToHost`),
					`maxInstallations` int,
					`expirationDate` TIMESTAMP
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'LICENSE_POOL' in tables.keys():
			logger.debug(u'Creating table LICENSE_POOL')
			table = u'''CREATE TABLE `LICENSE_POOL` (
					`licensePoolId` VARCHAR(200) NOT NULL,
					PRIMARY KEY( `licensePoolId` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`description` varchar(100)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL' in tables.keys():
			logger.debug(u'Creating table WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `licensePoolId` ) REFERENCES LICENSE_POOL( `licensePoolId` ),
					`windowsSoftwareId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `licensePoolId`, `windowsSoftwareId` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'PRODUCT_ID_TO_LICENSE_POOL' in tables.keys():
			logger.debug(u'Creating table PRODUCT_ID_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `PRODUCT_ID_TO_LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `licensePoolId` ) REFERENCES LICENSE_POOL( `licensePoolId` ),
					`productId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `licensePoolId`, `productId` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'SOFTWARE_LICENSE_TO_LICENSE_POOL' in tables.keys():
			logger.debug(u'Creating table SOFTWARE_LICENSE_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `SOFTWARE_LICENSE_TO_LICENSE_POOL` (
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `softwareLicenseId` ) REFERENCES SOFTWARE_LICENSE( `softwareLicenseId` ),
					`licensePoolId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `licensePoolId` ) REFERENCES LICENSE_POOL( `licensePoolId` ),
					PRIMARY KEY( `softwareLicenseId`, `licensePoolId` ),
					`licenseKey` VARCHAR(100)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		# LICENSE_USED_BY_HOST
		if not 'LICENSE_ON_CLIENT' in tables.keys():
			logger.debug(u'Creating table LICENSE_ON_CLIENT')
			table = u'''CREATE TABLE `LICENSE_ON_CLIENT` (
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					`licensePoolId` VARCHAR(100) NOT NULL,
					`clientId` varchar(255),
					PRIMARY KEY( `softwareLicenseId`, `licensePoolId`, `clientId` ),
					FOREIGN KEY( `softwareLicenseId`, `licensePoolId` ) REFERENCES SOFTWARE_LICENSE_TO_LICENSE_POOL( `softwareLicenseId`, `licensePoolId` ),
					`licenseKey` VARCHAR(100),
					`notes` VARCHAR(1024)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		
		# Software audit database
		if not 'SOFTWARE' in tables.keys():
			logger.debug(u'Creating table SOFTWARE')
			table = u'''CREATE TABLE `SOFTWARE` (
					`softwareId` varchar(100) NOT NULL,
					`displayName` varchar(100),
					`displayVersion` varchar(100),
					PRIMARY KEY( `softwareId`, `displayName`, `displayVersion` ),
					`type` varchar(30) NOT NULL,
					INDEX(`type`),
					`uninstallString` varchar(200),
					`binaryName` varchar(100),
					`installSize` BIGINT
				) ENGINE=MyISAM DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		if not 'SOFTWARE_CONFIG' in tables.keys():
			logger.debug(u'Creating table SOFTWARE_CONFIG')
			table = u'''CREATE TABLE `SOFTWARE_CONFIG` (
					`config_id` INT NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `config_id` ),
					`clientId` varchar(255) NOT NULL,
					INDEX(`clientId`),
					`softwareId` varchar(100) NOT NULL,
					`displayName` varchar(100),
					`displayVersion` varchar(100),
					INDEX(`softwareId`, `displayName`, `displayVersion`),
					`firstseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`lastseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`state` TINYINT NOT NULL,
					`usageFrequency` int NOT NULL DEFAULT -1,
					`lastUsed` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00'
				) ENGINE=MyISAM DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._mysql.execute(table)
		
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		data = self._objectToDatabaseHash(host)
		self._mysql.insert('HOST', data)
	
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		data = self._objectToDatabaseHash(host)
		where = self._uniqueCondition(host)
		self._mysql.update('HOST', where, data)
	
	def host_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.host_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting hosts, filter: %s" % filter)
		hosts = []
		type = forceList(filter.get('type', []))
		if 'OpsiDepotserver' in type and not 'OpsiConfigserver' in type:
			type.append('OpsiConfigserver')
			filter['type'] = type
		(attributes, filter) = self._adjustAttributes(Host, attributes, filter)
		for res in  self._mysql.getSet(self._createQuery('HOST', attributes, filter)):
			self._adjustResult(Host, res)
			hosts.append(Host.fromHash(res))
		return hosts
	
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		for host in forceObjectClassList(hosts, Host):
			logger.info(u"Deleting host %s" % host)
			where = self._uniqueCondition(host)
			self._mysql.delete('HOST', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		config = self._objectToDatabaseHash(config)
		possibleValues = config['possibleValues']
		defaultValues = config['defaultValues']
		del config['possibleValues']
		del config['defaultValues']
		
		self._mysql.insert('CONFIG', config)
		for value in possibleValues:
			self._mysql.insert('CONFIG_VALUE', {
				'configId': config['configId'],
				'value': value,
				'isDefault': (value in defaultValues)
				})
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		data = self._objectToDatabaseHash(config)
		where = self._uniqueCondition(config)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self._mysql.update('CONFIG', where, data)
		self._mysql.delete('CONFIG_VALUE', where)
		for value in possibleValues:
			self._mysql.insert('CONFIG_VALUE', {
				'configId': data['configId'],
				'value': value,
				'isDefault': (value in defaultValues)
				})
	
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting configs, filter: %s" % filter)
		configs = []
		(attributes, filter) = self._adjustAttributes(Config, attributes, filter)
		
		if filter.has_key('defaultValues'):
			if filter['defaultValues']:
				configIds = filter.get('configId')
				filter['configId'] = []
				for res in self._mysql.getSet(self._createQuery('CONFIG_VALUE', ['configId'], {'configId': configIds, 'value': filter['defaultValues'], 'isDefault': True})):
					filter['configId'].append(res['configId'])
				if not filter['configId']:
					return []
			del filter['defaultValues']
		if filter.has_key('possibleValues'):
			if filter['possibleValues']:
				configIds = filter.get('configId')
				filter['configId'] = []
				for res in self._mysql.getSet(self._createQuery('CONFIG_VALUE', ['configId'], {'configId': configIds, 'value': filter['possibleValues']})):
					filter['configId'].append(res['configId'])
				if not filter['configId']:
					return []
			del filter['possibleValues']
		attrs = []
		for attr in attributes:
			if not attr in ('defaultValues', 'possibleValues'):
				attrs.append(attr)
		for res in self._mysql.getSet(self._createQuery('CONFIG', attrs, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self._mysql.getSet(u"select * from CONFIG_VALUE where `configId` = '%s'" % res['configId']):
					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])
			self._adjustResult(Config, res)
			configs.append(Config.fromHash(res))
		return configs
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Deleting config %s" % config)
			where = self._uniqueCondition(config)
			self._mysql.delete('CONFIG_VALUE', where)
			self._mysql.delete('CONFIG', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
		data = self._objectToDatabaseHash(configState)
		data['values'] = json.dumps(data['values'])
		self._mysql.insert('CONFIG_STATE', data)
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
		data = self._objectToDatabaseHash(configState)
		where = self._uniqueCondition(configState)
		data['values'] = json.dumps(data['values'])
		self._mysql.update('CONFIG_STATE', where, data)
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting configStates, filter: %s" % filter)
		configStates = []
		(attributes, filter) = self._adjustAttributes(ConfigState, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('CONFIG_STATE', attributes, filter)):
			if res.has_key('values'):
				res['values'] = json.loads(res['values'])
			configStates.append(ConfigState.fromHash(res))
		return configStates
	
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info("Deleting configState %s" % configState)
			where = self._uniqueCondition(configState)
			self._mysql.delete('CONFIG_STATE', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		data = self._objectToDatabaseHash(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']
		self._mysql.insert('PRODUCT', data)
		for windowsSoftwareId in windowsSoftwareIds:
			self._mysql.insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': data['productId']})
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		data = self._objectToDatabaseHash(product)
		where = self._uniqueCondition(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']
		self._mysql.update('PRODUCT', where, data)
		self._mysql.delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])
		if windowsSoftwareIds:
			for windowsSoftwareId in windowsSoftwareIds:
				self._mysql.insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': data['productId']})
	
	def product_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting products, filter: %s" % filter)
		products = []
		(attributes, filter) = self._adjustAttributes(Product, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT', attributes, filter)):
			res['windowsSoftwareIds'] = []
			res['productClassIds'] = []
			if not attributes or 'windowsSoftwareIds' in attributes:
				for res2 in self._mysql.getSet(u"select * from WINDOWS_SOFTWARE_ID_TO_PRODUCT where `productId` = '%s'" % res['productId']):
					res['windowsSoftwareIds'].append(res2['windowsSoftwareId'])
			if not attributes or 'productClassIds' in attributes:
				pass
			self._adjustResult(Product, res)
			products.append(Product.fromHash(res))
		return products
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
		for product in forceObjectClassList(products, Product):
			logger.info("Deleting product %s" % config)
			where = self._uniqueCondition(product)
			self._mysql.delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])
			self._mysql.delete('PRODUCT', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self._mysql.insert('PRODUCT_PROPERTY', data)
		for value in possibleValues:
			self._mysql.insert('PRODUCT_PROPERTY_VALUE', {
					'productId': data['productId'],
					'productVersion': data['productVersion'],
					'packageVersion': data['packageVersion'],
					'propertyId': data['propertyId'],
					'value': value,
					'isDefault': (value in defaultValues)
					})
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self._mysql.update('PRODUCT_PROPERTY', data)
		for value in possibleValues:
			self._mysql.insert('PRODUCT_PROPERTY_VALUE', {
					'productId': data['productId'],
					'productVersion': data['productVersion'],
					'packageVersion': data['packageVersion'],
					'propertyId': data['propertyId'],
					'value': value,
					'isDefault': (value in defaultValues)
					})
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting product properties, filter: %s" % filter)
		productProperties = []
		(attributes, filter) = self._adjustAttributes(ProductProperty, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT_PROPERTY', attributes, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self._mysql.getSet(u"select * from PRODUCT_PROPERTY_VALUE where " \
					+ u"`propertyId` = '%s' AND `productId` = '%s' AND `productVersion` = '%s' AND `packageVersion` = '%s'" \
					% (res['propertyId'], res['productId'], res['productVersion'], res['packageVersion'])):
					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])
			productProperties.append(ProductProperty.fromHash(res))
		return productProperties
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info("Deleting product property %s" % productProperty)
			where = self._uniqueCondition(productProperty)
			self._mysql.delete('PRODUCT_PROPERTY_VALUE', where)
			self._mysql.delete('PRODUCT_PROPERTY', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		data = self._objectToDatabaseHash(productDependency)
		
		self._mysql.insert('PRODUCT_DEPENDENCY', data)
	
	def productDependency_updateObject(self, productDependency):
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		data = self._objectToDatabaseHash(productDependency)
		
		self._mysql.update('PRODUCT_DEPENDENCY', data)
	
	def productDependency_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting product dependencies, filter: %s" % filter)
		productDependencies = []
		(attributes, filter) = self._adjustAttributes(ProductDependency, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT_DEPENDENCY', attributes, filter)):
			productDependencies.append(ProductDependency.fromHash(res))
		return productDependencies
	
	def productDependency_deleteObjects(self, productDependencies):
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			logger.info("Deleting product dependency %s" % productDependency)
			where = self._uniqueCondition(productDependency)
			self._mysql.delete('PRODUCT_DEPENDENCY', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		data = self._objectToDatabaseHash(productOnDepot)
		self._mysql.insert('PRODUCT_ON_DEPOT', data)
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
		data = self._objectToDatabaseHash(productOnDepot)
		where = self._uniqueCondition(productOnDepot)
		self._mysql.update('PRODUCT_ON_DEPOT', where, data)
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		productOnDepots = []
		(attributes, filter) = self._adjustAttributes(ProductOnDepot, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT_ON_DEPOT', attributes, filter)):
			productOnDepots.append(ProductOnDepot.fromHash(res))
		return productOnDepots
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			logger.info(u"Deleting productOnDepot %s" % productOnDepot)
			where = self._uniqueCondition(productOnDepot)
			self._mysql.delete('PRODUCT_ON_DEPOT', where)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		data = self._objectToDatabaseHash(productOnClient)
		self._mysql.insert('PRODUCT_ON_CLIENT', data)
		
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		data = self._objectToDatabaseHash(productOnClient)
		where = self._uniqueCondition(productOnClient)
		self._mysql.update('PRODUCT_ON_CLIENT', where, data)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting productOnClients, filter: %s" % filter)
		productOnClients = []
		(attributes, filter) = self._adjustAttributes(ProductOnClient, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT_ON_CLIENT', attributes, filter)):
			productOnClients.append(ProductOnClient.fromHash(res))
		return productOnClients
	
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		for productOnClient in forceObjectClassList(productOnClients, ProductOnClient):
			logger.info(u"Deleting productOnClient %s" % productOnClient)
			where = self._uniqueCondition(productOnClient)
			self._mysql.delete('PRODUCT_ON_CLIENT', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
		data = self._objectToDatabaseHash(productPropertyState)
		data['values'] = json.dumps(data['values'])
		self._mysql.insert('PRODUCT_PROPERTY_STATE', data)
	
	def productPropertyState_updateObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
		data = self._objectToDatabaseHash(productPropertyState)
		where = self._uniqueCondition(productPropertyState)
		data['values'] = json.dumps(data['values'])
		self._mysql.update('PRODUCT_PROPERTY_STATE', where, data)
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting productPropertyStates, filter: %s" % filter)
		productPropertyStates = []
		(attributes, filter) = self._adjustAttributes(ProductPropertyState, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT_PROPERTY_STATE', attributes, filter)):
			if res.has_key('values'):
				res['values'] = json.loads(res['values'])
			productPropertyStates.append(ProductPropertyState.fromHash(res))
		return productPropertyStates
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			logger.info(u"Deleting productPropertyState %s" % productPropertyState)
			where = self._uniqueCondition(productPropertyState)
			self._mysql.delete('PRODUCT_PROPERTY_STATE', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		ConfigDataBackend.group_insertObject(self, group)
		data = self._objectToDatabaseHash(group)
		self._mysql.insert('GROUP', data)
	
	def group_updateObject(self, group):
		ConfigDataBackend.group_updateObject(self, group)
		data = self._objectToDatabaseHash(group)
		where = self._uniqueCondition(group)
		self._mysql.update('GROUP', where, data)
	
	def group_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting groups, filter: %s" % filter)
		groups = []
		(attributes, filter) = self._adjustAttributes(Group, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('GROUP', attributes, filter)):
			self._adjustResult(Group, res)
			groups.append(Group.fromHash(res))
		return groups
	
	def group_deleteObjects(self, groups):
		ConfigDataBackend.group_deleteObjects(self, groups)
		for group in forceObjectClassList(groups, Group):
			logger.info(u"Deleting group %s" % group)
			where = self._uniqueCondition(group)
			self._mysql.delete('GROUP', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
		data = self._objectToDatabaseHash(objectToGroup)
		self._mysql.insert('OBJECT_TO_GROUP', data)
	
	def objectToGroup_updateObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
		data = self._objectToDatabaseHash(objectToGroup)
		where = self._uniqueCondition(objectToGroup)
		self._mysql.update('OBJECT_TO_GROUP', where, data)
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting objectToGroups, filter: %s" % filter)
		objectToGroups = []
		(attributes, filter) = self._adjustAttributes(ObjectToGroup, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('OBJECT_TO_GROUP', attributes, filter)):
			objectToGroups.append(ObjectToGroup.fromHash(res))
		return objectToGroups
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			logger.info(u"Deleting objectToGroup %s" % objectToGroup)
			where = self._uniqueCondition(objectToGroup)
			self._mysql.delete('OBJECT_TO_GROUP', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_insertObject(self, licenseContract):
		ConfigDataBackend.licenseContract_insertObject(self, licenseContract)
		data = self._objectToDatabaseHash(licenseContract)
		self._mysql.insert('LICENSE_CONTRACT', data)
		
	def licenseContract_updateObject(self, licenseContract):
		ConfigDataBackend.licenseContract_updateObject(self, licenseContract)
		data = self._objectToDatabaseHash(licenseContract)
		where = self._uniqueCondition(licenseContract)
		self._mysql.update('LICENSE_CONTRACT', where, data)
	
	def licenseContract_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.licenseContract_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licenseContracts, filter: %s" % filter)
		licenseContracts = []
		(attributes, filter) = self._adjustAttributes(LicenseContract, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('LICENSE_CONTRACT', attributes, filter)):
			self._adjustResult(LicenseContract, res)
			licenseContracts.append(LicenseContract.fromHash(res))
		return licenseContracts
	
	def licenseContract_deleteObjects(self, licenseContracts):
		ConfigDataBackend.licenseContract_deleteObjects(self, licenseContracts)
		for licenseContract in forceObjectClassList(licenseContracts, LicenseContract):
			logger.info(u"Deleting licenseContract %s" % licenseContract)
			where = self._uniqueCondition(licenseContract)
			self._mysql.delete('LICENSE_CONTRACT', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_insertObject(self, softwareLicense):
		ConfigDataBackend.softwareLicense_insertObject(self, softwareLicense)
		data = self._objectToDatabaseHash(softwareLicense)
		self._mysql.insert('SOFTWARE_LICENSE', data)
		
	def softwareLicense_updateObject(self, softwareLicense):
		ConfigDataBackend.softwareLicense_updateObject(self, softwareLicense)
		data = self._objectToDatabaseHash(softwareLicense)
		where = self._uniqueCondition(softwareLicense)
		self._mysql.update('SOFTWARE_LICENSE', where, data)
	
	def softwareLicense_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.softwareLicense_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting softwareLicenses, filter: %s" % filter)
		softwareLicenses = []
		(attributes, filter) = self._adjustAttributes(SoftwareLicense, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('SOFTWARE_LICENSE', attributes, filter)):
			self._adjustResult(SoftwareLicense, res)
			softwareLicenses.append(SoftwareLicense.fromHash(res))
		return softwareLicenses
	
	def softwareLicense_deleteObjects(self, softwareLicenses):
		ConfigDataBackend.softwareLicense_deleteObjects(self, softwareLicenses)
		for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense):
			logger.info(u"Deleting softwareLicense %s" % softwareLicense)
			where = self._uniqueCondition(softwareLicense)
			self._mysql.delete('SOFTWARE_LICENSE', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePools                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_insertObject(self, licensePool):
		ConfigDataBackend.licensePool_insertObject(self, licensePool)
		data = self._objectToDatabaseHash(licensePool)
		windowsSoftwareIds = data['windowsSoftwareIds']
		productIds = data['productIds']
		del data['windowsSoftwareIds']
		del data['productIds']
		self._mysql.insert('LICENSE_POOL', data)
		for windowsSoftwareId in windowsSoftwareIds:
			self._mysql.insert('WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL', {'windowsSoftwareId': windowsSoftwareId, 'licensePoolId': data['licensePoolId']})
		for productId in productIds:
			self._mysql.insert('PRODUCT_ID_TO_LICENSE_POOL', {'productId': productId, 'licensePoolId': data['licensePoolId']})
		
	def licensePool_updateObject(self, licensePool):
		ConfigDataBackend.licensePool_updateObject(self, licensePool)
		data = self._objectToDatabaseHash(licensePool)
		where = self._uniqueCondition(licensePool)
		windowsSoftwareIds = data['windowsSoftwareIds']
		productIds = data['productIds']
		del data['windowsSoftwareIds']
		del data['productIds']
		self._mysql.update('LICENSE_POOL', where, data)
		self._mysql.delete('WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])
		self._mysql.delete('PRODUCT_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])
		if windowsSoftwareIds:
			for windowsSoftwareId in windowsSoftwareIds:
				self._mysql.insert('WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL', {'windowsSoftwareId': windowsSoftwareId, 'licensePoolId': data['licensePoolId']})
		if productIds:
			for productId in productIds:
				self._mysql.insert('PRODUCT_ID_TO_LICENSE_POOL', {'productId': productId, 'licensePoolId': data['licensePoolId']})
		
	def licensePool_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.licensePool_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licensePools, filter: %s" % filter)
		licensePools = []
		(attributes, filter) = self._adjustAttributes(LicensePool, attributes, filter)
		
		if filter.has_key('windowsSoftwareIds'):
			if filter['windowsSoftwareIds']:
				licensePoolIds = filter.get('licensePoolId')
				filter['licensePoolId'] = []
				for res in self._mysql.getSet(self._createQuery('WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL', ['licensePoolId'], {'licensePoolId': licensePoolIds, 'windowsSoftwareId': filter['windowsSoftwareIds']})):
					filter['licensePoolId'].append(res['licensePoolId'])
				if not filter['licensePoolId']:
					return []
			del filter['windowsSoftwareIds']
		if filter.has_key('productIds'):
			if filter['productIds']:
				licensePoolIds = filter.get('licensePoolId')
				filter['licensePoolId'] = []
				for res in self._mysql.getSet(self._createQuery('PRODUCT_ID_TO_LICENSE_POOL', ['licensePoolId'], {'licensePoolId': licensePoolIds, 'productId': filter['productIds']})):
					filter['licensePoolId'].append(res['licensePoolId'])
				if not filter['licensePoolId']:
					return []
			del filter['productIds']
		attrs = []
		for attr in attributes:
			if not attr in ('windowsSoftwareIds', 'productIds'):
				attrs.append(attr)
		for res in self._mysql.getSet(self._createQuery('LICENSE_POOL', attrs, filter)):
			res['windowsSoftwareIds'] = []
			res['productIds'] = []
			if not attributes or 'windowsSoftwareIds' in attributes:
				for res2 in self._mysql.getSet(u"select * from WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL where `licensePoolId` = '%s'" % res['licensePoolId']):
					res['windowsSoftwareIds'].append(res2['windowsSoftwareId'])
			if not attributes or 'productIds' in attributes:
				for res2 in self._mysql.getSet(u"select * from PRODUCT_ID_TO_LICENSE_POOL where `licensePoolId` = '%s'" % res['licensePoolId']):
					res['productIds'].append(res2['productId'])
			self._adjustResult(LicensePool, res)
			licensePools.append(LicensePool.fromHash(res))
		return licensePools
	
	def licensePool_deleteObjects(self, licensePools):
		ConfigDataBackend.licensePools_deleteObjects(self, licensePools)
		for licensePools in forceObjectClassList(licensePools, LicensePool):
			logger.info(u"Deleting licensePools %s" % licensePools)
			where = self._uniqueCondition(licensePools)
			self._mysql.delete('WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])
			self._mysql.delete('PRODUCT_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])
			self._mysql.delete('LICENSE_POOL', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool):
		ConfigDataBackend.softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool)
		data = self._objectToDatabaseHash(softwareLicenseToLicensePool)
		self._mysql.insert('SOFTWARE_LICENSE_TO_LICENSE_POOL', data)
	
	def softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool):
		ConfigDataBackend.softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool)
		data = self._objectToDatabaseHash(softwareLicenseToLicensePool)
		where = self._uniqueCondition(softwareLicenseToLicensePool)
		self._mysql.update('SOFTWARE_LICENSE_TO_LICENSE_POOL', where, data)
	
	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting softwareLicenseToLicensePool, filter: %s" % filter)
		softwareLicenseToLicensePools = []
		(attributes, filter) = self._adjustAttributes(SoftwareLicenseToLicensePool, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('SOFTWARE_LICENSE_TO_LICENSE_POOL', attributes, filter)):
			softwareLicenseToLicensePools.append(SoftwareLicenseToLicensePool.fromHash(res))
		return softwareLicenseToLicensePools
	
	def softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools):
		ConfigDataBackend.softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools)
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			logger.info(u"Deleting softwareLicenseToLicensePool %s" % softwareLicenseToLicensePool)
			where = self._uniqueCondition(softwareLicenseToLicensePool)
			self._mysql.delete('SOFTWARE_LICENSE_TO_LICENSE_POOL', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_insertObject(self, licenseOnClient):
		ConfigDataBackend.licenseOnClient_insertObject(self, licenseOnClient)
		data = self._objectToDatabaseHash(licenseOnClient)
		self._mysql.insert('LICENSE_ON_CLIENT', data)
	
	def licenseOnClient_updateObject(self, licenseOnClient):
		ConfigDataBackend.licenseOnClient_updateObject(self, licenseOnClient)
		data = self._objectToDatabaseHash(licenseOnClient)
		where = self._uniqueCondition(licenseOnClient)
		self._mysql.update('LICENSE_ON_CLIENT', where, data)
	
	def licenseOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.licenseOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licenseOnClient, filter: %s" % filter)
		licenseOnClients = []
		(attributes, filter) = self._adjustAttributes(LicenseOnClient, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('LICENSE_ON_CLIENT', attributes, filter)):
			licenseOnClients.append(LicenseOnClient.fromHash(res))
		return licenseOnClients
	
	def licenseOnClient_deleteObjects(self, licenseOnClients):
		ConfigDataBackend.licenseOnClient_deleteObjects(self, licenseOnClients)
		for licenseOnClient in forceObjectClassList(licenseOnClients, LicenseOnClient):
			logger.info(u"Deleting licenseOnClient %s" % licenseOnClient)
			where = self._uniqueCondition(licenseOnClient)
			self._mysql.delete('LICENSE_ON_CLIENT', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_insertObject(self, auditSoftware)
		data = self._objectToDatabaseHash(auditSoftware)
		self._mysql.insert('SOFTWARE', data)
	
	def auditSoftware_updateObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_updateObject(self, auditSoftware)
		data = self._objectToDatabaseHash(auditSoftware)
		where = self._uniqueCondition(auditSoftware)
		self._mysql.update('SOFTWARE', where, data)
	
	def auditSoftware_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftware_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting auditSoftware, filter: %s" % filter)
		auditSoftwares = []
		(attributes, filter) = self._adjustAttributes(AuditSoftware, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('SOFTWARE', attributes, filter)):
			auditSoftwares.append(AuditSoftware.fromHash(res))
		return auditSoftwares
	
	def auditSoftware_deleteObjects(self, auditSoftwares):
		ConfigDataBackend.auditSoftware_deleteObjects(self, auditSoftwares)
		for auditSoftware in forceObjectClassList(auditSoftwares, AuditSoftware):
			logger.info(u"Deleting auditSoftware %s" % auditSoftware)
			where = self._uniqueCondition(auditSoftware)
			self._mysql.delete('SOFTWARE', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient)
		data = self._objectToDatabaseHash(auditSoftwareOnClient)
		self._mysql.insert('SOFTWARE_CONFIG', data)
	
	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient)
		data = self._objectToDatabaseHash(auditSoftwareOnClient)
		where = self._uniqueCondition(auditSoftwareOnClient)
		self._mysql.update('SOFTWARE_CONFIG', where, data)
	
	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftwareOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting auditSoftwareOnClient, filter: %s" % filter)
		auditSoftwareOnClients = []
		(attributes, filter) = self._adjustAttributes(AuditSoftwareOnClient, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('SOFTWARE_CONFIG', attributes, filter)):
			auditSoftwareOnClients.append(AuditSoftwareOnClient.fromHash(res))
		return auditSoftwareOnClients
	
	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		ConfigDataBackend.auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients)
		for auditSoftwareOnClient in forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient):
			logger.info(u"Deleting auditSoftwareOnClient %s" % auditSoftwareOnClient)
			where = self._uniqueCondition(auditSoftwareOnClient)
			self._mysql.delete('SOFTWARE_CONFIG', where)
	






