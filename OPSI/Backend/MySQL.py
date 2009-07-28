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

__version__ = '0.3.3'

# Imports
import MySQLdb, warnings, time, json
from _mysql_exceptions import *

# OPSI imports
from OPSI.Logger import *
from Object import *
from Backend import *

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                       CLASS MYSQL                                                  =
# ======================================================================================================

class MySQL:
	def __init__(self, username = 'root', password = '', address = 'localhost', database = 'opsi'):
		self.__conn__ = None
		self.__username__ = username
		self.__password__ = password
		self.__address__ = address
		self.__database__ = database
		
	def connect(self):
		try:
			self.__conn__ = MySQLdb.connect(
							host = self.__address__,
							user = self.__username__,
							passwd = self.__password__,
							db = self.__database__,
							use_unicode = True,
							charset = 'utf8' )
		except Exception, e:
			raise BackendIOError("Failed to connect to database '%s' address '%s': %s" % (database, address, e))
		
		self.__cursor__ = self.__conn__.cursor(MySQLdb.cursors.DictCursor)
		
	def db_query(self, query):
		logger.debug2("db_query: %s" % query)
		self.db_execute(query)
		return self.__cursor__.rowcount
	
	def db_getSet(self, query):
		logger.debug2("db_getSet: %s" % query)
		self.db_execute(query)
		valueSet = self.__cursor__.fetchall()
		if not valueSet:
			logger.debug("No result for query '%s'" % query)
			return []
		return valueSet
		
	def db_getRow(self, query):
		logger.debug2("db_getRow: %s" % query)
		self.db_execute(query)
		row = self.__cursor__.fetchone()
		if not row:
			logger.debug("No result for query '%s'" % query)
			return {}
		logger.debug2("Result: '%s'" % row)
		return row
		
	def db_insert(self, table, valueHash):
		colNames = values = ''
		for (key, value) in valueHash.items():
			colNames += "`%s`, " % key
			if type(value) in (float, long, int, bool):
				values += "%s, " % value
			elif type(value) is str:
				values += "\'%s\', " % ('%s' % value.decode("utf-8")).replace("\\", "\\\\").replace("'", "\\\'")
			else:
				values += "\'%s\', " % ('%s' % value).replace("\\", "\\\\").replace("'", "\\\'")
			
		query = "INSERT INTO `%s` (%s) VALUES (%s);" % (table, colNames[:-2], values[:-2])
		logger.debug2("db_insert: %s" % query)
		self.db_execute(query)
		return self.__cursor__.lastrowid
		
	def db_update(self, table, where, valueHash):
		if not valueHash:
			raise ValueError("No values given")
		query = "UPDATE `%s` SET " % table
		for (key, value) in valueHash.items():
			query += "`%s` = " % key
			if type(value) in (float, long, int, bool):
				query += "%s, " % value
			else:
				query += "\'%s\', " % ('%s' % value).replace("\\", "\\\\").replace("'", "\\\'")
		
		query = '%s WHERE %s;' % (query[:-2], where)
		
		logger.debug2("db_update: %s" % query)
		self.db_execute(query)
		self.db_commit()
		return self.__cursor__.lastrowid
	
	def db_delete(self, table, where):
		query = "DELETE FROM `%s` WHERE %s;" % (table, where)
		logger.debug2("db_delete: %s" % query)
		self.db_execute(query)
		return self.__cursor__.lastrowid
		
	def db_commit(self):
		self.__conn__.commit()
		
	def db_execute(self, query):
		if not self.__conn__:
			self.connect()
		if not type(query) is unicode:
			query = unicode(query, 'utf-8')
		res = self.__cursor__.execute(query)
		self.db_commit()
		return res
	
	def db_info(self):
		if not self.__conn__:
			self.connect()
		return self.__conn__.info()
	
	def db_warning_count(self):
		if not self.__conn__:
			self.connect()
		return self.__conn__.warning_count()
		
	def db_close(self):
		if not self.__conn__:
			return
		logger.debug("Closing database connection")
		self.__cursor__.close()
		self.__conn__.commit()
		self.__conn__.close()

# ======================================================================================================
# =                                    CLASS MYSQLBACKEND                                              =
# ======================================================================================================
class MySQLBackend(DataBackend):
	
	def __init__(self, username = '', password = '', address = 'localhost', **kwargs):
		''' MySQLBackend constructor. '''
		
		#self.__backendManager = backendManager
		
		# Default values
		self._defaultDomain = 'opsi.org'
		self._username = username
		self._password = password
		self._address = address
		self._database = 'opsi'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			if   (option.lower() == 'database'):		self._database = value
			elif (option.lower() == 'defaultdomain'): 	self._defaultDomain = value
			elif (option.lower() == 'host'):		self._address = value
			elif (option.lower() == 'username'):		self._username = value
			elif (option.lower() == 'password'):		self._password = value
			else:
				logger.warning("Unknown argument '%s' passed to MySQLBackend constructor" % option)
		
		warnings.showwarning = self._showwarning
		self.__mysql__ = MySQL(username = self._username, password = self._password, address = self._address, database = self._database)
		
		self._licenseManagementEnabled = True
		
	def _showwarning(self, message, category, filename, lineno, line=None, file=None):
		#logger.warning("%s (file: %s, line: %s)" % (message, filename, lineno))
		if str(message).startswith('Data truncated for column'):
			logger.error(message)
		else:
			logger.warning(message)
	
	def _writeToServer_(self, queries):
		for query in queries.split(';'):
			if query.strip():
				self.__mysql__.db_query(query + ' ;')
	
	def _createQuery(self, table, attributes=[], filter={}):
		where = u''
		select = u''
		for attribute in attributes:
			if select:
				select += u','
			select += u'`%s`' % attribute
		
		for (key, value) in filter.items():
			if where:
				where += u' and '
			if type(value) in (float, long, int, bool):
				where += u"`%s` = %s" % (key, value)
			else:
				where += u"`%s` = '%s'" % (key, value)
		result = []
		if not select:
			select = u'*'
		if where:
			return u'select %s from `%s` where %s' % (select, table, where)
		else:
			return u'select %s from `%s`' % (select, table)
	
	
	def _adjustAttributes(self, objectClass, attributes, filter):
		id = self._objectAttributeToDatabaseAttribute(objectClass, 'id')
		if filter.has_key('id'):
			filter[id] = filter['id']
			del filter['id']
		if 'id' in attributes:
			attributes.remove('id')
			attributes.append(id)
		if attributes:
			if not 'type' in attributes:
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
		return attribute
	
	def _uniqueCondition(self, object):
		condition = u''
		args = mandatoryConstructorArgs(object.__class__)
		if isinstance(object, Group):
			args.append('type')
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
		# Drop database
		failure = 0
		done = False
		while not done and (failure < 100):
			done = True
			for i in self.__mysql__.db_getSet('SHOW TABLES;'):
				try:
					logger.debug('DROP TABLE `%s`;' % i.values()[0])
					self.__mysql__.db_execute('DROP TABLE `%s`;' % i.values()[0])
				except Exception, e:
					logger.error(e)
					done = False
					failure += 1
		
	def base_create(self):
		# Hardware audit database
		tables = {}
		logger.debug("Current tables:")
		for i in self.__mysql__.db_getSet('SHOW TABLES;'):
			tableName = i.values()[0]
			logger.debug(" [ %s ]" % tableName)
			tables[tableName] = []
			for j in self.__mysql__.dtb_getSet('SHOW COLUMNS FROM `%s`' % tableName):
				logger.debug("      %s" % j)
				tables[tableName].append(j['Field'])
		
		logger.notice('Creating opsi base')
		
		# Host table
		if not 'HOST' in tables.keys():
			logger.debug('Creating table HOST')
			table = '''CREATE TABLE `HOST` (
					`hostId` varchar(255) NOT NULL,
					PRIMARY KEY( `hostId` ),
					`type` varchar(30),
					`description` varchar(100),
					`notes` varchar(500),
					`hardwareAddress` varchar(17),
					`ipAddress` varchar(15),
					`created` TIMESTAMP,
					`lastSeen` TIMESTAMP,
					`opsiHostKey` varchar(32),
					`depotLocalUrl` varchar(128),
					`depotRemoteUrl` varchar(255),
					`repositoryLocalUrl` varchar(128),
					`repositoryRemoteUrl` varchar(255),
					`network` varchar(31)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'CONFIG' in tables.keys():
			logger.debug('Creating table CONFIG')
			table = '''CREATE TABLE `CONFIG` (
					`name` varchar(200) NOT NULL,
					PRIMARY KEY( `name` ),
					`type` varchar(30) NOT NULL,
					`description` varchar(256),
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'CONFIG_VALUE' in tables.keys():
			logger.debug('Creating table CONFIG_VALUE')
			table = '''CREATE TABLE `CONFIG_VALUE` (
					`config_value_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `config_value_id` ),
					`name` varchar(200) NOT NULL,
					FOREIGN KEY ( `name` ) REFERENCES CONFIG( `name` ),
					`value` TEXT,
					`isDefault` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT' in tables.keys():
			logger.debug('Creating table PRODUCT')
			table = '''CREATE TABLE `PRODUCT` (
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
					`priority` int,
					`description` TEXT,
					`advice` TEXT,
					`pxeConfigTemplate` varchar(50)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'WINDOWS_SOFTWARE_ID_TO_PRODUCT' in tables.keys():
			logger.debug('Creating table WINDOWS_SOFTWARE_ID_TO_PRODUCT')
			table = '''CREATE TABLE `WINDOWS_SOFTWARE_ID_TO_PRODUCT` (
					`windowsSoftwareId` VARCHAR(100) NOT NULL,
					PRIMARY KEY( `windowsSoftwareId`),
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES PRODUCT( `productId` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT_ON_DEPOT' in tables.keys():
			logger.debug('Creating table PRODUCT_ON_DEPOT')
			table = '''CREATE TABLE `PRODUCT_ON_DEPOT` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion` ) REFERENCES PRODUCT( `productId`, `productVersion`, `packageVersion` ),
					`depotId` varchar(50) NOT NULL,
					FOREIGN KEY ( `depotId` ) REFERENCES HOST( `hostId` ),
					PRIMARY KEY(  `productId`, `depotId` ),
					`locked` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT_PROPERTY' in tables.keys():
			logger.debug('Creating table PRODUCT_PROPERTY')
			table = '''CREATE TABLE `PRODUCT_PROPERTY` (
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`name` varchar(200) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion` ) REFERENCES PRODUCT( `productId`, `productVersion`, `packageVersion` ),
					PRIMARY KEY( `productId`, `productVersion`, `packageVersion`, `name` ),
					`type` varchar(30) NOT NULL,
					`description` varchar(256),
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT_PROPERTY_VALUE' in tables.keys():
			logger.debug('Creating table PRODUCT_PROPERTY_VALUE')
			table = '''CREATE TABLE `PRODUCT_PROPERTY_VALUE` (
					`product_property_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `product_property_id` ),
					`productId` varchar(50) NOT NULL,
					`productVersion` varchar(16) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`name` varchar(200) NOT NULL,
					FOREIGN KEY ( `productId`, `productVersion`, `packageVersion`, `name` ) REFERENCES PRODUCT_PROPERTY( `productId`, `productVersion`, `packageVersion`, `name` ),
					`value` text,
					`isDefault` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT_STATE' in tables.keys():
			logger.debug('Creating table PRODUCT_STATE')
			table = '''CREATE TABLE `PRODUCT_STATE` (
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES PRODUCT( `productId` ),
					`hostId` varchar(255) NOT NULL,
					FOREIGN KEY ( `hostId` ) REFERENCES HOST( `hostId` ),
					PRIMARY KEY( `productId`, `hostId` ),
					`installationStatus` varchar(16),
					`actionRequest` varchar(16),
					`actionProgress` varchar(255),
					`productVersion` varchar(16),
					`packageVersion` varchar(16),
					`lastStateChange` TIMESTAMP
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'PRODUCT_PROPERTY_STATE' in tables.keys():
			logger.debug('Creating table PRODUCT_PROPERTY_STATE')
			table = '''CREATE TABLE `PRODUCT_PROPERTY_STATE` (
					`product_property_state_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `product_property_state_id` ),
					`productId` varchar(50) NOT NULL,
					FOREIGN KEY ( `productId` ) REFERENCES PRODUCT( `productId` ),
					`name` varchar(200) NOT NULL,
					`hostId` varchar(255) NOT NULL,
					FOREIGN KEY ( `hostId` ) REFERENCES HOST( `hostId` ),
					`values` text
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
		if not 'GROUP' in tables.keys():
			logger.debug('Creating table GROUP')
			table = '''CREATE TABLE `GROUP` (
					`groupId` varchar(255) NOT NULL,
					`type` varchar(30) NOT NULL,
					PRIMARY KEY( `groupId`, `type` ),
					`parentGroupId` varchar(255),
					`description` varchar(100),
					`notes` varchar(500)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insert(self, host):
		data = self._objectToDatabaseHash(host)
		self.__mysql__.db_insert('HOST', data)
	
	def host_update(self, host):
		data = self._objectToDatabaseHash(host)
		where = self._uniqueCondition(host)
		self.__mysql__.db_update('HOST', where, data)
	
	def host_get(self, attributes=[], **filter):
		logger.info(u"Getting hosts, filter: %s" % filter)
		hosts = []
		self._adjustAttributes(Host, attributes, filter)
		for res in  self.__mysql__.db_getSet(self._createQuery('HOST', attributes, filter)):
			self._adjustResult(Host, res)
			hosts.append(Host.fromHash(res))
		return hosts
	
	def host_delete(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			logger.info("Deleting host %s" % host)
			where = self._uniqueCondition(host)
			self.__mysql__.db_delete('HOST', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insert(self, config):
		config = self._objectToDatabaseHash(config)
		possibleValues = config['possibleValues']
		defaultValues = config['defaultValues']
		del config['possibleValues']
		del config['defaultValues']
		
		self.__mysql__.db_insert('CONFIG', config)
		for value in possibleValues:
			self.__mysql__.db_insert('CONFIG_VALUE', {
				'name': config['name'],
				'value': value,
				'isDefault': (value in defaultValues)
				})
	
	def config_update(self, config):
		data = self._objectToDatabaseHash(config)
		where = self._uniqueCondition(config)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self.__mysql__.db_update('CONFIG', where, data)
		self.__mysql__.db_delete('CONFIG_VALUE', where)
		for value in possibleValues:
			self.__mysql__.db_insert('CONFIG_VALUE', {
				'name': data['name'],
				'value': value,
				'isDefault': (value in defaultValues)
				})
		
	def config_get(self, attributes=[], **filter):
		logger.info(u"Getting configs, filter: %s" % filter)
		configs = []
		self._adjustAttributes(Config, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('CONFIG', attributes, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self.__mysql__.db_getSet(u"select * from CONFIG_VALUE where `name` = '%s'" % res['name']):
					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])
			configs.append(Config.fromHash(res))
		return configs
	
	def config_delete(self, configs):
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Deleting config %s" % config)
			where = self._uniqueCondition(config)
			self.__mysql__.db_delete('CONFIG_VALUE', where)
			self.__mysql__.db_delete('CONFIG', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insert(self, product):
		data = self._objectToDatabaseHash(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']
		self.__mysql__.db_insert('PRODUCT', data)
		for windowsSoftwareId in windowsSoftwareIds:
			self.__mysql__.db_insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': data['productId']})
	
	def product_update(self, product):
		data = self._objectToDatabaseHash(product)
		where = self._uniqueCondition(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']
		self.__mysql__.db_update('PRODUCT', where, data)
		self.__mysql__.db_delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])
		for windowsSoftwareId in windowsSoftwareIds:
			self.__mysql__.db_insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': data['productId']})
	
	def product_get(self, attributes=[], **filter):
		logger.info("Getting products, filter: %s" % filter)
		products = []
		self._adjustAttributes(Product, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT', attributes, filter)):
			res['windowsSoftwareIds'] = []
			res['productClassIds'] = []
			if not attributes or 'windowsSoftwareIds' in attributes or 'productClassIds' in attributes:
				for res2 in self.__mysql__.db_getSet(u"select * from WINDOWS_SOFTWARE_ID_TO_PRODUCT where `productId` = '%s'" % res['productId']):
					res['windowsSoftwareIds'].append(res2['windowsSoftwareId'])
			self._adjustResult(Product, res)
			products.append(Product.fromHash(res))
		return products
	
	def product_delete(self, products):
		for product in forceObjectClassList(products, Product):
			logger.info("Deleting config %s" % config)
			where = self._uniqueCondition(product)
			self.__mysql__.db_delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])
			self.__mysql__.db_delete('PRODUCT', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insert(self, productProperty):
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self.__mysql__.db_insert('PRODUCT_PROPERTY', data)
		for value in possibleValues:
			self.__mysql__.db_insert('PRODUCT_PROPERTY_VALUE', {
					'productId': data['productId'],
					'productVersion': data['productVersion'],
					'packageVersion': data['packageVersion'],
					'name': data['name'],
					'value': value,
					'isDefault': (value in defaultValues)
					})
	
	def productProperty_update(self, productProperty):
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		del data['possibleValues']
		del data['defaultValues']
		
		self.__mysql__.db_update('PRODUCT_PROPERTY', data)
		for value in possibleValues:
			self.__mysql__.db_insert('PRODUCT_PROPERTY_VALUE', {
					'productId': data['productId'],
					'productVersion': data['productVersion'],
					'packageVersion': data['packageVersion'],
					'name': data['name'],
					'value': value,
					'isDefault': (value in defaultValues)
					})
	
	def productProperty_get(self, attributes=[], **filter):
		logger.info("Getting product properties, filter: %s" % filter)
		productProperties = []
		self._adjustAttributes(ProductProperty, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT_PROPERTY', attributes, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self.__mysql__.db_getSet(u"select * from PRODUCT_PROPERTY_VALUE where " \
					+ u"`name` = '%s' AND `productId` = '%s' AND `productVersion` = '%s' AND `packageVersion` = '%s'" \
					% (res['name'], res['productId'], res['productVersion'], res['packageVersion'])):
					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])
			productProperties.append(ProductProperty.fromHash(res))
		return productProperties
	
	def productProperty_delete(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info("Deleting product property %s" % productProperty)
			where = self._uniqueCondition(productProperty)
			self.__mysql__.db_delete('PRODUCT_PROPERTY_VALUE', where)
			self.__mysql__.db_delete('PRODUCT_PROPERTY', where)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insert(self, productOnDepot):
		data = self._objectToDatabaseHash(productOnDepot)
		self.__mysql__.db_insert('PRODUCT_ON_DEPOT', data)
	
	def productOnDepot_update(self, productOnDepot):
		data = self._objectToDatabaseHash(productOnDepot)
		where = self._uniqueCondition(productOnDepot)
		self.__mysql__.db_update('PRODUCT_ON_DEPOT', where, data)
	
	def productOnDepot_get(self, attributes=[], **filter):
		productOnDepots = []
		self._adjustAttributes(ProductOnDepot, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT_ON_DEPOT', attributes, filter)):
			productOnDepots.append(ProductOnDepot.fromHash(res))
		return productOnDepots
	
	def productOnDepot_delete(self, productOnDepots):
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			logger.info("Deleting productOnDepot %s" % productOnDepot)
			where = self._uniqueCondition(ProductOnDepot)
			self.__mysql__.db_delete('PRODUCT_ON_DEPOT', where)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductStates                                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productState_insert(self, productState):
		data = self._objectToDatabaseHash(productState)
		self.__mysql__.db_insert('PRODUCT_STATE', data)
		
	def productState_update(self, productState):
		data = self._objectToDatabaseHash(productState)
		where = self._uniqueCondition(productState)
		self.__mysql__.db_update('PRODUCT_STATE', where, data)
	
	def productState_get(self, attributes=[], **filter):
		logger.info("Getting productStates, filter: %s" % filter)
		productStates = []
		self._adjustAttributes(ProductState, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT_STATE', attributes, filter)):
			productStates.append(ProductState.fromHash(res))
		return productStates
	
	def productState_delete(self, productStates):
		for productState in forceObjectClassList(productStates, ProductState):
			logger.info("Deleting productState %s" % productState)
			where = self._uniqueCondition(productState)
			self.__mysql__.db_delete('PRODUCT_STATE', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insert(self, productPropertyState):
		data = self._objectToDatabaseHash(productPropertyState)
		data['values'] = json.dumps(data['values'])
		self.__mysql__.db_insert('PRODUCT_PROPERTY_STATE', data)
	
	def productPropertyState_update(self, productPropertyState):
		data = self._objectToDatabaseHash(productPropertyState)
		where = self._uniqueCondition(productPropertyState)
		data['values'] = json.dumps(data['values'])
		self.__mysql__.db_update('PRODUCT_PROPERTY_STATE', where, data)
	
	def productPropertyState_get(self, attributes=[], **filter):
		logger.info("Getting productPropertyStates, filter: %s" % filter)
		productPropertyStates = []
		self._adjustAttributes(ProductPropertyState, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT_PROPERTY_STATE', attributes, filter)):
			res['values'] = json.loads(res['values'])
			productPropertyStates.append(ProductPropertyState.fromHash(res))
		return productPropertyStates
	
	def productPropertyState_delete(self, productPropertyStates):
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			logger.info("Deleting productPropertyState %s" % productPropertyState)
			where = self._uniqueCondition(productPropertyState)
			self.__mysql__.db_delete('PRODUCT_PROPERTY_STATE', where)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insert(self, group):
		data = self._objectToDatabaseHash(group)
		memberIds = data['memberIds']
		del data['memberIds']
		self.__mysql__.db_insert('GROUP', data)
	
	def group_update(self, group):
		data = self._objectToDatabaseHash(group)
		where = self._uniqueCondition(group)
		self.__mysql__.db_update('GROUP', where, data)
	
	def group_get(self, attributes=[], **filter):
		logger.info("Getting groups, filter: %s" % filter)
		groups = []
		self._adjustAttributes(Group, attributes, filter)
		for res in self.__mysql__.db_getSet(self._createQuery('GROUP', attributes, filter)):
			groups.append(Group.fromHash(res))
		return groups
	
	def group_delete(self, groups):
		for group in forceObjectClassList(groups, Group):
			logger.info("Deleting group %s" % group)
			where = self._uniqueCondition(group)
			self.__mysql__.db_delete('GROUP', where)


























