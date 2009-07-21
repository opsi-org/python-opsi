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
import MySQLdb, warnings, time
from _mysql_exceptions import *

# OPSI imports
from OPSI.Logger import *
from Objects import *

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
			else:
				values += "\'%s\', " % ('%s' % value).replace("\\", "\\\\").replace("'", "\\\'")
			
		query = "INSERT INTO `%s` (%s) VALUES (%s);" % (table, colNames[:-2], values[:-2])
		logger.debug2("db_insert: %s" % query)
		self.db_execute(query)
		return self.__cursor__.lastrowid
		#return self.__cursor__.rowcount
		
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
	
	def __init__(self, username = '', password = '', address = 'localhost', backendManager=None, args={}):
		''' MySQLBackend constructor. '''
		
		self.__backendManager = backendManager
		
		# Default values
		self._defaultDomain = 'opsi.org'
		self._username = username
		self._password = password
		self._address = address
		self._database = 'opsi'
		
		# Parse arguments
		for (option, value) in args.items():
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
		if self.__backendManager:
			self._licenseManagementEnabled = False
			try:
				modules = self.__backendManager.getOpsiInformation_hash()['modules']
				if modules.get('valid') and modules.get('license_management'):
					import base64, twisted.conch.ssh.keys
					try:
						from hashlib import md5
					except ImportError:
						from md5 import md5
					publicKey = twisted.conch.ssh.keys.getPublicKeyObject(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP'))
					data = ''
					mks = modules.keys()
					mks.sort()
					for module in mks:
						if module in ('valid', 'signature'):
							continue
						val = modules[module]
						if (val == False): val = 'no'
						if (val == True):  val = 'yes'
						data += module.lower().strip() + ' = ' + val + '\r\n'
					if (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
						raise Exception("Modules file signature expired")
					self._licenseManagementEnabled = bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ]))
			except Exception, e:
				logger.error(e)
		
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
			return u'select %s from %s where %s' % (select, table, where)
		else:
			return u'select %s from %s' % (select, table)
	
	
	def _adjustAttributes(self, objectClass, attributes, filter):
		id = '%sId' % objectClass.__name__.lower()
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
		id = '%sId' % objectClass.__name__.lower()
		if result.has_key(id):
			result['id'] = result[id]
			del result[id]
		return result
		
	def deleteOpsiBase(self):
		# Drop database
		failure = 0
		done = False
		while not done and (failure < 100):
			done = True
			for i in self.__mysql__.db_getSet('SHOW TABLES;'):
				try:
					self.__mysql__.db_execute('DROP TABLE %s;' % i.values()[0])
				except Exception, e:
					logger.error(e)
					done = False
					failure += 1
		
	def createOpsiBase(self):
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
		
		# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
		# = Client Management                                                                           =
		# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
		
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
					`value` TEXT,
					`isDefault` bool
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				'''
			logger.debug(table)
			self._writeToServer_(table)
		
	def host_create(self, hosts=[]):
		# TODO: move to super class
		for host in forceList(hosts):
			logger.notice("Creating host '%s'" % host)
			if self.host_get(attributes=['id'], id = host.id):
				logger.info("Host '%s' already exists, updating" % host)
				return self.host_update(host)
			return self.host_insert(host)
		
	def host_insert(self, host):
		host = host.toHash()
		host['hostId'] = host['id']
		del host['id']
		self.__mysql__.db_insert('HOST', host)
	
	def host_update(self, host):
		#host['hostId'] = host['id']
		#del host['id']
		#self.__mysql__.db_insert('HOST', host)
		pass
	
	def host_get(self, attributes=[], **filter):
		hosts = []
		self._adjustAttributes(Host, attributes, filter)
		for res in  self.__mysql__.db_getSet(self._createQuery('HOST', attributes, filter)):
			self._adjustResult(Host, res)
			hosts.append(Host.fromHash(res))
		return hosts
	
	def host_delete(self, hosts=[]):
		for host in forceList(hosts):
			logger.notice("Deleting host %s" % host)
			self.__mysql__.db_delete('HOST', "`type` = '%s' AND `hostId` = '%s'" % (host.getType(), host.id))
	
	def config_create(self, configs=[]):
		for config in forceList(configs):
			logger.notice("Creating config %s" % config)
			self.__mysql__.db_insert('CONFIG', {
					'name': config.name,
					'description': config.description,
					'type': config.getType(),
					'editable': config.editable,
					'multiValue': config.multiValue
					})
			for value in config.possibleValues:
				self.__mysql__.db_insert('CONFIG_VALUE', {
						'name': config.name,
						'value': value,
						'isDefault': (value in config.defaultValues)
						})
	
	def config_get(self, attributes=[], **filter):
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
	
	def product_create(self, products=[]):
		for product in forceList(products):
			logger.notice("Creating product %s" % product)
			product = product.toHash()
			product['productId'] = product['id']
			del product['id']
			windowsSoftwareIds = product['windowsSoftwareIds']
			del product['windowsSoftwareIds']
			del product['productClassIds']
			self.__mysql__.db_insert('PRODUCT', product)
			for windowsSoftwareId in windowsSoftwareIds:
				self.__mysql__.db_insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT', {'windowsSoftwareId': windowsSoftwareId, 'productId': product['productId']})
	
	def product_get(self, attributes=[], **filter):
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
	
	def productOnDepot_create(self, productOnDepots=[]):
		productOnDepots = forceList(productOnDepots)
		for productOnDepot in productOnDepots:
			logger.notice("Creating productOnDepot '%s'" % productOnDepot)
			if self.productOnDepot_get(productId = productOnDepot.productId, depotId = productOnDepot.depotId):
				logger.info("ProductOnDepot '%s' already exists, updating" % productOnDepot)
				return self.productOnDepot_update(productOnDepot)
			return self.productOnDepot_insert(productOnDepot)
		
	def productOnDepot_insert(self, productOnDepot):
		productOnDepot = productOnDepot.toHash()
		self.__mysql__.db_insert('PRODUCT_ON_DEPOT', productOnDepot)
	
	def productOnDepot_get(self, attributes=[], **filter):
		productOnDepots = []
		for res in self.__mysql__.db_getSet(self._createQuery('PRODUCT_ON_DEPOT', attributes, filter)):
			productOnDepots.append(ProductOnDepot.fromHash(res))
		return productOnDepots
		
	
	def productProperty_create(self, productProperties=[]):
		for productProperty in forceList(productProperties):
			logger.notice("Creating productProperty %s" % productProperty)
			productProperty = productProperty.toHash()
			possibleValues = productProperty['possibleValues']
			defaultValues = productProperty['defaultValues']
			del productProperty['possibleValues']
			del productProperty['defaultValues']
			
			self.__mysql__.db_insert('PRODUCT_PROPERTY', productProperty)
			for value in possibleValues:
				self.__mysql__.db_insert('PRODUCT_PROPERTY_VALUE', {
						'productId': productProperty['productId'],
						'productVersion': productProperty['productVersion'],
						'packageVersion': productProperty['packageVersion'],
						'name': productProperty['name'],
						'value': value,
						'isDefault': (value in defaultValues)
						})
	
	def productProperty_get(self, attributes=[], **filter):
		#configs = []
		#self._adjustAttributes(Config, attributes, filter)
		#for res in self.__mysql__.db_getSet(self._createQuery('CONFIG', attributes, filter)):
		#	res['possibleValues'] = []
		#	res['defaultValues'] = []
		#	if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
		#		for res2 in self.__mysql__.db_getSet(u"select * from CONFIG_VALUE where `name` = '%s'" % res['name']):
		#			res['possibleValues'].append(res2['value'])
		#			if res2['isDefault']:
		#				res['defaultValues'].append(res2['value'])
		#	configs.append(Config.fromHash(res))
		#return configs
		return []
		



























