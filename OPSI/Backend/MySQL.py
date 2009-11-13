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

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from Object import *
from Backend import *

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                       CLASS MYSQL                                                  =
# ======================================================================================================

class MySQL:
	def __init__(self, username = 'root', password = '', address = 'localhost', database = 'opsi'):
		self._conn     = None
		self._username = username
		self._password = password
		self._address  = address
		self._database = database
		
	def connect(self):
		try:
			self._conn = MySQLdb.connect(
						host        = self._address,
						user        = self._username,
						passwd      = self._password,
						db          = self._database,
						use_unicode = True,
						charset     = 'utf8' )
		except Exception, e:
			raise BackendIOError(u"Failed to connect to database '%s' address '%s': %s" % (self._database, self._address, e))
		
		self._cursor = self._conn.cursor(MySQLdb.cursors.DictCursor)
	
	def close(self):
		if not self._conn:
			return
		logger.info(u"Closing database connection")
		self._cursor.close()
		self._conn.commit()
		self._conn.close()
	
	def query(self, query):
		logger.debug2(u"query: %s" % query)
		self.execute(query)
		return self._cursor.rowcount
	
	def getSet(self, query):
		logger.debug2(u"getSet: %s" % query)
		self.execute(query)
		valueSet = self._cursor.fetchall()
		if not valueSet:
			logger.debug(u"No result for query '%s'" % query)
			return []
		return valueSet
		
	def getRow(self, query):
		logger.debug2(u"getRow: %s" % query)
		self.execute(query)
		row = self._cursor.fetchone()
		if not row:
			logger.debug(u"No result for query '%s'" % query)
			return {}
		logger.debug2(u"Result: '%s'" % row)
		return row
		
	def insert(self, table, valueHash):
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
		self.execute(query)
		return self._cursor.lastrowid
		
	def update(self, table, where, valueHash):
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
		self.execute(query)
		self.commit()
		return self._cursor.lastrowid
	
	def delete(self, table, where):
		query = u"DELETE FROM `%s` WHERE %s;" % (table, where)
		logger.debug2(u"delete: %s" % query)
		self.execute(query)
		return self._cursor.lastrowid
		
	def commit(self):
		self._conn.commit()
		
	def execute(self, query):
		if not self._conn:
			self.connect()
		if not type(query) is unicode:
			query = unicode(query, 'utf-8', 'replace')
		res = self._cursor.execute(query)
		self.commit()
		return res
	
	def info(self):
		if not self._conn:
			self.connect()
		return self._conn.info()
	
	def warningCount(self):
		if not self._conn:
			self.connect()
		return self._conn.warning_count()
	

# ======================================================================================================
# =                                    CLASS MYSQLBACKEND                                              =
# ======================================================================================================
class MySQLBackend(ExtendedConfigDataBackend):
	
	def __init__(self, username = '', password = '', address = 'localhost', **kwargs):
		ConfigDataBackend.__init__(self, username, password, address, **kwargs)
		
		self._database = 'opsi'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			if   (option.lower() == 'database'):
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
			if not type(values) is list:
				values = [ values ]
			if not values:
				continue
			if where:
				where += u' and '
			where += u'('
			for value in values:
				operator = '='
				if type(value) in (float, long, int, bool):
					where += u"`%s` %s %s" % (key, operator, value)
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
	
	def base_delete(self):
		ConfigDataBackend.base_delete(self)
		# Drop database
		failure = 0
		done = False
		while not done and (failure < 100):
			done = True
			for i in self._mysql.getSet(u'SHOW TABLES;'):
				try:
					logger.debug(u'DROP TABLE `%s`;' % i.values()[0])
					self._mysql.execute(u'DROP TABLE `%s`;' % i.values()[0])
				except Exception, e:
					logger.error(e)
					done = False
					failure += 1
		
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
					`network` varchar(31)
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
					`objectId` varchar(255) NOT NULL,
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
					`name` varchar(128) NOT NULL,
					`licenseRequired` varchar(50),
					`setupScript` varchar(50),
					`uninstallScript` varchar(50),
					`updateScript` varchar(50),
					`alwaysScript` varchar(50),
					`onceScript` varchar(50),
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
					`parentGroupId` varchar(255),
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
		self._adjustAttributes(Host, attributes, filter)
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
		self._adjustAttributes(Config, attributes, filter)
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
		self._adjustAttributes(ConfigState, attributes, filter)
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
		for windowsSoftwareId in windowsSoftwareIds:
			self._mysql.insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': data['productId']})
	
	def product_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting products, filter: %s" % filter)
		products = []
		self._adjustAttributes(Product, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('PRODUCT', attributes, filter)):
			res['windowsSoftwareIds'] = []
			res['productClassIds'] = []
			if not attributes or 'windowsSoftwareIds' in attributes or 'productClassIds' in attributes:
				for res2 in self._mysql.getSet(u"select * from WINDOWS_SOFTWARE_ID_TO_PRODUCT where `productId` = '%s'" % res['productId']):
					res['windowsSoftwareIds'].append(res2['windowsSoftwareId'])
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
		self._adjustAttributes(ProductProperty, attributes, filter)
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
		self._adjustAttributes(ProductOnDepot, attributes, filter)
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
		self._adjustAttributes(ProductOnClient, attributes, filter)
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
		self._adjustAttributes(ProductPropertyState, attributes, filter)
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
		self._adjustAttributes(Group, attributes, filter)
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
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting objectToGroups, filter: %s" % filter)
		objectToGroups = []
		self._adjustAttributes(ObjectToGroup, attributes, filter)
		for res in self._mysql.getSet(self._createQuery('OBJECT_TO_GROUP', attributes, filter)):
			objectToGroups.append(ObjectToGroup.fromHash(res))
		return objectToGroups
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			logger.info(u"Deleting objectToGroup %s" % objectToGroup)
			where = self._uniqueCondition(objectToGroup)
			self._mysql.delete('OBJECT_TO_GROUP', where)
























