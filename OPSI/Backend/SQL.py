#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
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
Basic SQL backend.

This backend is a general SQL implementation undependend from concrete
databases and their implementation.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import json
import re
import time
from contextlib import contextmanager
from datetime import datetime
from hashlib import md5
from twisted.conch.ssh import keys

from OPSI.Logger import Logger
from OPSI.Types import (forceBool, forceUnicodeLower, forceOpsiTimestamp,
	forceList, forceUnicode, forceUnicodeList, forceDict, forceObjectClassList)
from OPSI.Types import (BackendConfigurationError,
	BackendReferentialIntegrityError, BackendModuleDisabledError)
from OPSI.Object import (AuditHardware, AuditHardwareOnHost, AuditSoftware,
	AuditSoftwareOnClient, AuditSoftwareToLicensePool, BootConfiguration,
	Config, ConfigState, Entity, Group, Host, HostGroup, LicenseContract,
	LicenseOnClient, LicensePool, ObjectToGroup, Product, ProductDependency,
	ProductGroup, ProductOnClient, ProductOnDepot, ProductProperty,
	ProductPropertyState, Relationship, SoftwareLicense,
	SoftwareLicenseToLicensePool,
	mandatoryConstructorArgs)
from OPSI.Backend.Backend import BackendModificationListener, ConfigDataBackend
from OPSI.Util import timestamp

__all__ = [
	'timeQuery', 'onlyAllowSelect', 'SQL', 'SQLBackend',
	'SQLBackendObjectModificationTracker'
]

logger = Logger()


@contextmanager
def timeQuery(query):
	startingTime = datetime.now()
	logger.debug(u'start query {0}', query)
	try:
		yield
	finally:
		logger.debug(u'ended query (duration: {1}) {0}', query, datetime.now() - startingTime)


def onlyAllowSelect(query):
	if not forceUnicodeLower(query).strip().startswith('select'):
		raise ValueError('Only queries to SELECT data are allowed.')


class SQL(object):

	AUTOINCREMENT = 'AUTO_INCREMENT'
	ALTER_TABLE_CHANGE_SUPPORTED = True
	ESCAPED_BACKSLASH = "\\\\"
	ESCAPED_APOSTROPHE = "\\\'"
	ESCAPED_UNDERSCORE = "\\_"
	ESCAPED_PERCENT = "\\%"
	ESCAPED_ASTERISK = "\\*"
	doCommit = True

	def __init__(self, **kwargs):
		pass

	def connect(self):
		pass

	def close(self, conn, cursor):
		pass

	def getSet(self, query):
		return []

	def getRow(self, query):
		return {}

	def insert(self, table, valueHash):
		return -1

	def update(self, table, where, valueHash, updateWhereNone=False):
		return 0

	def delete(self, table, where):
		return 0

	def getTables(self):
		return {}

	def execute(self, query, conn=None, cursor=None):
		return None

	def query(self, query, conn=None, cursor=None):
		return self.execute(query)

	def getTableCreationOptions(self, table):
		return u''

	def escapeBackslash(self, string):
		return string.replace('\\', self.ESCAPED_BACKSLASH)

	def escapeApostrophe(self, string):
		return string.replace("'", self.ESCAPED_APOSTROPHE)

	def escapeUnderscore(self, string):
		return string.replace('_', self.ESCAPED_UNDERSCORE)

	def escapePercent(self, string):
		return string.replace('%', self.ESCAPED_PERCENT)

	def escapeAsterisk(self, string):
		return string.replace('*', self.ESCAPED_ASTERISK)


class SQLBackendObjectModificationTracker(BackendModificationListener):
	def __init__(self, **kwargs):
		BackendModificationListener.__init__(self)
		self._sql = None
		self._lastModificationOnly = False
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'lastmodificationonly':
				self._lastModificationOnly = forceBool(value)

	def _createTables(self):
		tables = self._sql.getTables()
		if 'OBJECT_MODIFICATION_TRACKER' not in tables.keys():
			logger.debug(u'Creating table OBJECT_MODIFICATION_TRACKER')
			table = u'''CREATE TABLE `OBJECT_MODIFICATION_TRACKER` (
					`id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`command` varchar(6) NOT NULL,
					`objectClass` varchar(128) NOT NULL,
					`ident` varchar(1024) NOT NULL,
					`date` TIMESTAMP,
					PRIMARY KEY (`id`)
				) %s;
				''' % self._sql.getTableCreationOptions('OBJECT_MODIFICATION_TRACKER')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `objectClass` on `OBJECT_MODIFICATION_TRACKER` (`objectClass`);')
			self._sql.execute('CREATE INDEX `ident` on `OBJECT_MODIFICATION_TRACKER` (`ident`);')
			self._sql.execute('CREATE INDEX `date` on `OBJECT_MODIFICATION_TRACKER` (`date`);')

	def _trackModification(self, command, obj):
		command = forceUnicodeLower(command)
		if command not in ('insert', 'update', 'delete'):
			raise Exception(u"Unhandled command {0!r}".format(command))

		data = {
			'command': command,
			'objectClass': obj.__class__.__name__,
			'ident': obj.getIdent(),
			'date': timestamp()
		}
		if self._lastModificationOnly:
			objectClass = data['objectClass']
			ident = self._sql.escapeApostrophe(self._sql.escapeBackslash(data['ident']))
			self._sql.delete('OBJECT_MODIFICATION_TRACKER', "`objectClass` = '%s' AND `ident` = '%s'" % (objectClass, ident))
		start = time.time()
		self._sql.insert('OBJECT_MODIFICATION_TRACKER', data)
		logger.debug(u"Took %0.2f seconds to track modification of objectClass %s, ident %s" % ((time.time() - start), data['objectClass'], data['ident']))

	def getModifications(self, sinceDate=0):
		return self._sql.getSet("SELECT * FROM `OBJECT_MODIFICATION_TRACKER` WHERE `date` > '%s'" % forceOpsiTimestamp(sinceDate))

	def clearModifications(self, objectClass=None, sinceDate=0):
		where = "`date` > '%s'" % forceOpsiTimestamp(sinceDate)
		if objectClass:
			where = ''.join((where, 'AND `objectClass` = "{0}"'.format(objectClass)))
		self._sql.execute("DELETE FROM `OBJECT_MODIFICATION_TRACKER` WHERE %s" % where)

	def objectInserted(self, backend, obj):
		self._trackModification('insert', obj)

	def objectUpdated(self, backend, obj):
		self._trackModification('update', obj)

	def objectsDeleted(self, backend, objs):
		[self._trackModification('delete', obj) for obj in forceList(objs)]


class SQLBackend(ConfigDataBackend):

	_OPERATOR_IN_CONDITION_PATTERN = re.compile('^\s*([>=<]+)\s*(\d\.?\d*)')

	def __init__(self, **kwargs):
		self._name = 'sql'

		ConfigDataBackend.__init__(self, **kwargs)

		self._sql = None
		self._auditHardwareConfig = {}
		self._setAuditHardwareConfig(self.auditHardware_getConfig())

	def _setAuditHardwareConfig(self, config):
		self._auditHardwareConfig = {}
		for conf in config:
			hwClass = conf['Class']['Opsi']
			self._auditHardwareConfig[hwClass] = {}
			for value in conf['Values']:
				self._auditHardwareConfig[hwClass][value['Opsi']] = {
					'Type': value["Type"],
					'Scope': value["Scope"]
				}

	def _requiresEnabledSQLBackendModule(self):
		"""
		This will raise an exception if the SQL backend module is not enabled.

		:raises BackendModuleDisabledError: if SQL backend module disabled
		"""
		if not self._sqlBackendModule:
			raise BackendModuleDisabledError(u"SQL backend module disabled")

	def _filterToSql(self, filter={}):
		"""
		Creates a SQL condition out of the given filter.
		"""
		def buildCondition():
			for key, values in filter.items():
				if values is None:
					continue
				values = forceList(values)
				if not values:
					continue

				yield u' or '.join(processValues(key, values))

		def processValues(key, values):
			for value in values:
				if isinstance(value, bool):
					if value:
						yield u"`{0}` = 1".format(key)
					else:
						yield u"`{0}` = 0".format(key)
				elif isinstance(value, (float, long, int)):
					yield u"`{0}` = {1}".format(key, value)
				elif value is None:
					yield u"`{0}` is NULL".format(key)
				else:
					value = value.replace(self._sql.ESCAPED_ASTERISK, u'\uffff')
					value = self._sql.escapeApostrophe(self._sql.escapeBackslash(value))
					match = self._OPERATOR_IN_CONDITION_PATTERN.search(value)
					if match:
						operator = match.group(1)
						value = match.group(2)
						value = value.replace(u'\uffff', self._sql.ESCAPED_ASTERISK)
						yield u"`%s` %s %s" % (key, operator, forceUnicode(value))
					else:
						if '*' in value:
							operator = 'LIKE'
							value = self._sql.escapeUnderscore(self._sql.escapePercent(value)).replace('*', '%')
						else:
							operator = '='

						value = value.replace(u'\uffff', self._sql.ESCAPED_ASTERISK)
						yield u"`{0}` {1} '{2}'".format(key, operator, forceUnicode(value))

		def addParenthesis(conditions):
			for condition in conditions:
				yield u'({0})'.format(condition)

		return u' and '.join(addParenthesis(buildCondition()))

	def _createQuery(self, table, attributes=[], filter={}):
		select = u','.join(
			u'`{0}`'.format(attribute) for attribute in attributes
		) or u'*'

		condition = self._filterToSql(filter)
		if condition:
			query = u'select %s from `%s` where %s' % (select, table, condition)
		else:
			query = u'select %s from `%s`' % (select, table)
		logger.debug(u"Created query: {0}", query)
		return query

	def _adjustAttributes(self, objectClass, attributes, filter):
		if attributes:
			newAttributes = forceUnicodeList(attributes)
		else:
			newAttributes = []

		newFilter = forceDict(filter)
		objectId = self._objectAttributeToDatabaseAttribute(objectClass, 'id')

		try:
			newFilter[objectId] = newFilter['id']
			del newFilter['id']
		except KeyError:
			# No key 'id' - everything okay
			pass

		try:
			newAttributes.remove('id')
			newAttributes.append(objectId)
		except ValueError:
			# No element 'id' - everything okay
			pass

		try:
			for oc in forceList(filter['type']):
				if objectClass.__name__ == oc:
					newFilter['type'] = forceList(filter['type']).append(objectClass.subClasses.values())
		except KeyError:
			# No key 'type' - everything okay
			pass

		if newAttributes:
			if issubclass(objectClass, Entity) and 'type' not in newAttributes:
				newAttributes.append('type')
			objectClasses = [objectClass]
			objectClasses.extend(objectClass.subClasses.values())
			for oc in objectClasses:
				for arg in mandatoryConstructorArgs(oc):
					if arg == 'id':
						arg = objectId

					if arg not in newAttributes:
						newAttributes.append(arg)

		return (newAttributes, newFilter)

	def _adjustResult(self, objectClass, result):
		idAttribute = self._objectAttributeToDatabaseAttribute(objectClass, 'id')

		try:
			result['id'] = result[idAttribute]
			del result[idAttribute]
		except KeyError:
			pass

		return result

	def _objectToDatabaseHash(self, object):
		hash = object.toHash()
		if object.getType() == 'ProductOnClient':
			try:
				del hash['actionSequence']
			except KeyError:
				pass  # not there - can be

		if issubclass(object.__class__, Product):
			try:
				# Truncating a possibly too long changelog entry
				hash['changelog'] = hash['changelog'][:65534]
			except (KeyError, TypeError):
				pass  # Either not present in hash or set to None

		if issubclass(object.__class__, Relationship):
			try:
				del hash['type']
			except KeyError:
				pass  # not there - can be

		for objectAttribute in hash.keys():
			dbAttribute = self._objectAttributeToDatabaseAttribute(object.__class__, objectAttribute)
			if objectAttribute != dbAttribute:
				hash[dbAttribute] = hash[objectAttribute]
				del hash[objectAttribute]

		return hash

	def _objectAttributeToDatabaseAttribute(self, objectClass, attribute):
		if attribute == 'id':
			# A class is considered a subclass of itself
			if issubclass(objectClass, Product):
				return 'productId'
			elif issubclass(objectClass, Host):
				return 'hostId'
			elif issubclass(objectClass, Group):
				return 'groupId'
			elif issubclass(objectClass, Config):
				return 'configId'
			elif issubclass(objectClass, LicenseContract):
				return 'licenseContractId'
			elif issubclass(objectClass, SoftwareLicense):
				return 'softwareLicenseId'
			elif issubclass(objectClass, LicensePool):
				return 'licensePoolId'
		return attribute

	def _uniqueCondition(self, object):
		"""
		Creates an unique condition that can be used in the WHERE part
		of an SQL query to identify an object.
		To achieve this the constructor of the object is inspected.
		Objects must have an attribute named like the parameter.

		:param object: The object to create an condition for.
		:returntype: str
		"""
		def createCondition():
			for argument in mandatoryConstructorArgs(object.__class__):
				value = getattr(object, argument)
				if value is None:
					continue

				arg = self._objectAttributeToDatabaseAttribute(object.__class__, argument)
				if isinstance(value, bool):
					if value:
						yield u"`{0}` = 1".format(arg)
					else:
						yield u"`{0}` = 0".format(arg)
				elif isinstance(value, (float, long, int)):
					yield u"`{0}` = {1}".format(arg, value)
				else:
					yield u"`{0}` = '{1}'".format(arg, self._sql.escapeApostrophe(self._sql.escapeBackslash(value)))

			if isinstance(object, HostGroup) or isinstance(object, ProductGroup):
				yield u"`type` = '{0}'".format(object.getType())

		return ' and '.join(createCondition())

	def _objectExists(self, table, object):
		query = 'select * from `%s` where %s' % (table, self._uniqueCondition(object))
		return bool(self._sql.getRow(query))

	def backend_exit(self):
		pass

	def backend_deleteBase(self):
		ConfigDataBackend.backend_deleteBase(self)

		# Drop database
		for tableName in self._sql.getTables().keys():
			dropCommand = u'DROP TABLE `{name}`;'.format(name=tableName)
			logger.debug(dropCommand)
			try:
				self._sql.execute(dropCommand)
			except Exception as error:
				logger.error(error)

	def backend_createBase(self):
		ConfigDataBackend.backend_createBase(self)

		tables = self._sql.getTables()

		logger.notice(u'Creating opsi base')

		existingTables = set(tables.keys())
		# Host table
		if 'HOST' not in existingTables:
			self._createTableHost()

		if 'CONFIG' not in existingTables:
			logger.debug(u'Creating table CONFIG')
			table = u'''CREATE TABLE `CONFIG` (
					`configId` varchar(200) NOT NULL,
					`type` varchar(30) NOT NULL,
					`description` varchar(256),
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL,
					PRIMARY KEY (`configId`)
				) %s;
				''' % self._sql.getTableCreationOptions('CONFIG')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_config_type` on `CONFIG` (`type`);')

		if 'CONFIG_VALUE' not in existingTables:
			logger.debug(u'Creating table CONFIG_VALUE')
			table = u'''CREATE TABLE `CONFIG_VALUE` (
					`config_value_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`configId` varchar(200) NOT NULL,
					`value` TEXT,
					`isDefault` bool,
					PRIMARY KEY (`config_value_id`),
					FOREIGN KEY (`configId`) REFERENCES `CONFIG` (`configId`)
				) %s;
				''' % self._sql.getTableCreationOptions('CONFIG_VALUE')
			logger.debug(table)
			self._sql.execute(table)

		if 'CONFIG_STATE' not in existingTables:
			logger.debug(u'Creating table CONFIG_STATE')
			table = u'''CREATE TABLE `CONFIG_STATE` (
					`config_state_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`configId` varchar(200) NOT NULL,
					`objectId` varchar(255) NOT NULL,
					`values` text,
					PRIMARY KEY (`config_state_id`)
				) %s;
				''' % self._sql.getTableCreationOptions('CONFIG_STATE')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_config_state_configId` on `CONFIG_STATE` (`configId`);')
			self._sql.execute('CREATE INDEX `index_config_state_objectId` on `CONFIG_STATE` (`objectId`);')

		if 'PRODUCT' not in existingTables:
			logger.debug(u'Creating table PRODUCT')
			table = u'''CREATE TABLE `PRODUCT` (
					`productId` varchar(255) NOT NULL,
					`productVersion` varchar(32) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`type` varchar(32) NOT NULL,
					`name` varchar(128) NOT NULL,
					`licenseRequired` varchar(50),
					`setupScript` varchar(50),
					`uninstallScript` varchar(50),
					`updateScript` varchar(50),
					`alwaysScript` varchar(50),
					`onceScript` varchar(50),
					`customScript` varchar(50),
					`userLoginScript` varchar(50),
					`priority` integer,
					`description` TEXT,
					`advice` TEXT,
					`pxeConfigTemplate` varchar(50),
					`changelog` TEXT,
					PRIMARY KEY (`productId`, `productVersion`, `packageVersion`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_product_type` on `PRODUCT` (`type`);')

		# FOREIGN KEY ( `productId` ) REFERENCES `PRODUCT` ( `productId` ),
		if 'WINDOWS_SOFTWARE_ID_TO_PRODUCT' not in existingTables:
			logger.debug(u'Creating table WINDOWS_SOFTWARE_ID_TO_PRODUCT')
			table = u'''CREATE TABLE `WINDOWS_SOFTWARE_ID_TO_PRODUCT` (
					`windowsSoftwareId` VARCHAR(100) NOT NULL,
					`productId` varchar(255) NOT NULL,
					PRIMARY KEY (`windowsSoftwareId`, `productId`)
				) %s;
				''' % self._sql.getTableCreationOptions('WINDOWS_SOFTWARE_ID_TO_PRODUCT')
			logger.debug(table)
			self._sql.execute(table)

		if 'PRODUCT_ON_DEPOT' not in existingTables:
			logger.debug(u'Creating table PRODUCT_ON_DEPOT')
			table = u'''CREATE TABLE `PRODUCT_ON_DEPOT` (
					`productId` varchar(255) NOT NULL,
					`productVersion` varchar(32) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`depotId` varchar(255) NOT NULL,
					`productType` varchar(16) NOT NULL,
					`locked` bool,
					PRIMARY KEY (`productId`, `depotId`),
					FOREIGN KEY (`productId`, `productVersion`, `packageVersion` ) REFERENCES `PRODUCT` (`productId`, `productVersion`, `packageVersion`),
					FOREIGN KEY (`depotId`) REFERENCES `HOST` (`hostId`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_ON_DEPOT')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_product_on_depot_productType` on `PRODUCT_ON_DEPOT` (`productType`);')

		if 'PRODUCT_PROPERTY' not in existingTables:
			logger.debug(u'Creating table PRODUCT_PROPERTY')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY` (
					`productId` varchar(255) NOT NULL,
					`productVersion` varchar(32) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`propertyId` varchar(200) NOT NULL,
					`type` varchar(30) NOT NULL,
					`description` TEXT,
					`multiValue` bool NOT NULL,
					`editable` bool NOT NULL,
					PRIMARY KEY (`productId`, `productVersion`, `packageVersion`, `propertyId`),
					FOREIGN KEY (`productId`, `productVersion`, `packageVersion`) REFERENCES `PRODUCT` (`productId`, `productVersion`, `packageVersion`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_PROPERTY')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_product_property_type` on `PRODUCT_PROPERTY` (`type`);')

		if 'PRODUCT_PROPERTY_VALUE' not in existingTables:
			logger.debug(u'Creating table PRODUCT_PROPERTY_VALUE')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY_VALUE` (
					`product_property_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`productId` varchar(255) NOT NULL,
					`productVersion` varchar(32) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`propertyId` varchar(200) NOT NULL,
					`value` text,
					`isDefault` bool,
					PRIMARY KEY (`product_property_id`),
					FOREIGN KEY (`productId`, `productVersion`, `packageVersion`, `propertyId`) REFERENCES `PRODUCT_PROPERTY` (`productId`, `productVersion`, `packageVersion`, `propertyId`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_PROPERTY_VALUE')
			logger.debug(table)
			self._sql.execute(table)

		if 'PRODUCT_DEPENDENCY' not in existingTables:
			logger.debug(u'Creating table PRODUCT_DEPENDENCY')
			table = u'''CREATE TABLE `PRODUCT_DEPENDENCY` (
					`productId` varchar(255) NOT NULL,
					`productVersion` varchar(32) NOT NULL,
					`packageVersion` varchar(16) NOT NULL,
					`productAction` varchar(16) NOT NULL,
					`requiredProductId` varchar(255) NOT NULL,
					`requiredProductVersion` varchar(32),
					`requiredPackageVersion` varchar(16),
					`requiredAction` varchar(16),
					`requiredInstallationStatus` varchar(16),
					`requirementType` varchar(16),
					PRIMARY KEY (`productId`, `productVersion`, `packageVersion`, `productAction`, `requiredProductId`),
					FOREIGN KEY (`productId`, `productVersion`, `packageVersion`) REFERENCES `PRODUCT` (`productId`, `productVersion`, `packageVersion`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_DEPENDENCY')
			logger.debug(table)
			self._sql.execute(table)

		# FOREIGN KEY ( `productId` ) REFERENCES PRODUCT( `productId` ),
		if 'PRODUCT_ON_CLIENT' not in existingTables:
			logger.debug(u'Creating table PRODUCT_ON_CLIENT')
			table = u'''CREATE TABLE `PRODUCT_ON_CLIENT` (
					`productId` varchar(255) NOT NULL,
					`clientId` varchar(255) NOT NULL,
					`productType` varchar(16) NOT NULL,
					`targetConfiguration` varchar(16),
					`installationStatus` varchar(16),
					`actionRequest` varchar(16),
					`actionProgress` varchar(255),
					`actionResult` varchar(16),
					`lastAction` varchar(16),
					`productVersion` varchar(32),
					`packageVersion` varchar(16),
					`modificationTime` TIMESTAMP,
					PRIMARY KEY (`productId`, `clientId`),
					FOREIGN KEY (`clientId`) REFERENCES `HOST` (`hostId`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_ON_CLIENT')
			logger.debug(table)
			self._sql.execute(table)

		# FOREIGN KEY ( `productId` ) REFERENCES `PRODUCT` ( `productId` ),
		if 'PRODUCT_PROPERTY_STATE' not in existingTables:
			logger.debug(u'Creating table PRODUCT_PROPERTY_STATE')
			table = u'''CREATE TABLE `PRODUCT_PROPERTY_STATE` (
					`product_property_state_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`productId` varchar(255) NOT NULL,
					`propertyId` varchar(200) NOT NULL,
					`objectId` varchar(255) NOT NULL,
					`values` text,
					PRIMARY KEY (`product_property_state_id`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_PROPERTY_STATE')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_product_property_state_objectId` on `PRODUCT_PROPERTY_STATE` (`objectId`);')

		if 'GROUP' not in existingTables:
			logger.debug(u'Creating table GROUP')
			table = u'''CREATE TABLE `GROUP` (
					`type` varchar(30) NOT NULL,
					`groupId` varchar(255) NOT NULL,
					`parentGroupId` varchar(255),
					`description` varchar(100),
					`notes` varchar(500),
					PRIMARY KEY (`type`, `groupId`)
				) %s;
				''' % self._sql.getTableCreationOptions('GROUP')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_group_parentGroupId` on `GROUP` (`parentGroupId`);')

		if 'OBJECT_TO_GROUP' not in existingTables:
			logger.debug(u'Creating table OBJECT_TO_GROUP')
			table = u'''CREATE TABLE `OBJECT_TO_GROUP` (
					`object_to_group_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`groupType` varchar(30) NOT NULL,
					`groupId` varchar(100) NOT NULL,
					`objectId` varchar(255) NOT NULL,
					PRIMARY KEY (`object_to_group_id`),
					FOREIGN KEY (`groupType`, `groupId`) REFERENCES `GROUP` (`type`, `groupId`)
				) %s;
				''' % self._sql.getTableCreationOptions('OBJECT_TO_GROUP')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_object_to_group_objectId` on `OBJECT_TO_GROUP` (`objectId`);')

		if 'LICENSE_CONTRACT' not in existingTables:
			logger.debug(u'Creating table LICENSE_CONTRACT')
			table = u'''CREATE TABLE `LICENSE_CONTRACT` (
					`licenseContractId` VARCHAR(100) NOT NULL,
					`type` varchar(30) NOT NULL,
					`description` varchar(100),
					`notes` varchar(1000),
					`partner` varchar(100),
					`conclusionDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`notificationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					PRIMARY KEY (`licenseContractId`)
				) %s;
				''' % self._sql.getTableCreationOptions('LICENSE_CONTRACT')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_license_contract_type` on `LICENSE_CONTRACT` (`type`);')

		if 'SOFTWARE_LICENSE' not in existingTables:
			logger.debug(u'Creating table SOFTWARE_LICENSE')
			table = u'''CREATE TABLE `SOFTWARE_LICENSE` (
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					`licenseContractId` VARCHAR(100) NOT NULL,
					`type` varchar(30) NOT NULL,
					`boundToHost` varchar(255),
					`maxInstallations` integer,
					`expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					PRIMARY KEY (`softwareLicenseId`),
					FOREIGN KEY (`licenseContractId`) REFERENCES `LICENSE_CONTRACT` (`licenseContractId`)
				) %s;
				''' % self._sql.getTableCreationOptions('SOFTWARE_LICENSE')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_software_license_type` on `SOFTWARE_LICENSE` (`type`);')
			self._sql.execute('CREATE INDEX `index_software_license_boundToHost` on `SOFTWARE_LICENSE` (`boundToHost`);')

		if 'LICENSE_POOL' not in existingTables:
			logger.debug(u'Creating table LICENSE_POOL')
			table = u'''CREATE TABLE `LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					`type` varchar(30) NOT NULL,
					`description` varchar(200),
					PRIMARY KEY (`licensePoolId`)
				) %s;
				''' % self._sql.getTableCreationOptions('LICENSE_POOL')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_license_pool_type` on `LICENSE_POOL` (`type`);')

		if 'AUDIT_SOFTWARE_TO_LICENSE_POOL' not in existingTables:
			logger.debug(u'Creating table AUDIT_SOFTWARE_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `AUDIT_SOFTWARE_TO_LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					`name` varchar(100) NOT NULL,
					`version` varchar(100) NOT NULL,
					`subVersion` varchar(100) NOT NULL,
					`language` varchar(10) NOT NULL,
					`architecture` varchar(3) NOT NULL,
					PRIMARY KEY (`name`, `version`, `subVersion`, `language`, `architecture`),
					FOREIGN KEY (`licensePoolId`) REFERENCES `LICENSE_POOL` (`licensePoolId`)
				) %s;
				''' % self._sql.getTableCreationOptions('AUDIT_SOFTWARE_TO_LICENSE_POOL')
			logger.debug(table)
			self._sql.execute(table)

		if 'PRODUCT_ID_TO_LICENSE_POOL' not in existingTables:
			logger.debug(u'Creating table PRODUCT_ID_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `PRODUCT_ID_TO_LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					`productId` VARCHAR(255) NOT NULL,
					PRIMARY KEY (`licensePoolId`, `productId`),
					FOREIGN KEY (`licensePoolId`) REFERENCES `LICENSE_POOL` (`licensePoolId`)
				) %s;
				''' % self._sql.getTableCreationOptions('PRODUCT_ID_TO_LICENSE_POOL')
			logger.debug(table)
			self._sql.execute(table)

		if 'SOFTWARE_LICENSE_TO_LICENSE_POOL' not in existingTables:
			logger.debug(u'Creating table SOFTWARE_LICENSE_TO_LICENSE_POOL')
			table = u'''CREATE TABLE `SOFTWARE_LICENSE_TO_LICENSE_POOL` (
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					`licensePoolId` VARCHAR(100) NOT NULL,
					`licenseKey` VARCHAR(1024),
					PRIMARY KEY (`softwareLicenseId`, `licensePoolId`),
					FOREIGN KEY (`softwareLicenseId`) REFERENCES `SOFTWARE_LICENSE` (`softwareLicenseId`),
					FOREIGN KEY (`licensePoolId`) REFERENCES `LICENSE_POOL` (`licensePoolId`)
				) %s;
				''' % self._sql.getTableCreationOptions('SOFTWARE_LICENSE_TO_LICENSE_POOL')
			logger.debug(table)
			self._sql.execute(table)

		if 'LICENSE_ON_CLIENT' not in existingTables:
			logger.debug(u'Creating table LICENSE_ON_CLIENT')
			table = u'''CREATE TABLE `LICENSE_ON_CLIENT` (
					`license_on_client_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					`licensePoolId` VARCHAR(100) NOT NULL,
					`clientId` varchar(255),
					`licenseKey` VARCHAR(1024),
					`notes` VARCHAR(1024),
					PRIMARY KEY (`license_on_client_id`),
					FOREIGN KEY (`softwareLicenseId`, `licensePoolId`) REFERENCES `SOFTWARE_LICENSE_TO_LICENSE_POOL` (`softwareLicenseId`, `licensePoolId`)
				) %s;
				''' % self._sql.getTableCreationOptions('LICENSE_ON_CLIENT')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_license_on_client_clientId` on `LICENSE_ON_CLIENT` (`clientId`);')

		if 'BOOT_CONFIGURATION' not in existingTables:
			logger.debug(u'Creating table BOOT_CONFIGURATION')
			table = u'''CREATE TABLE `BOOT_CONFIGURATION` (
					`name` varchar(64) NOT NULL,
					`clientId` varchar(255) NOT NULL,
					`priority` integer DEFAULT 0,
					`description` TEXT,
					`netbootProductId` varchar(255),
					`pxeTemplate` varchar(255),
					`options` varchar(255),
					`disk` integer,
					`partition` integer,
					`active` bool,
					`deleteAfter` integer,
					`deactivateAfter` integer,
					`accessCount` integer,
					`osName` varchar(128),
					PRIMARY KEY (`name`, `clientId`),
					FOREIGN KEY (`clientId`) REFERENCES `HOST` (`hostId`)
				) %s;
				''' % self._sql.getTableCreationOptions('BOOT_CONFIGURATION')
			logger.debug(table)
			self._sql.execute(table)

		# Software audit tables
		if 'SOFTWARE' not in existingTables:
			logger.debug(u'Creating table SOFTWARE')
			table = u'''CREATE TABLE `SOFTWARE` (
					`name` varchar(100) NOT NULL,
					`version` varchar(100) NOT NULL,
					`subVersion` varchar(100) NOT NULL,
					`language` varchar(10) NOT NULL,
					`architecture` varchar(3) NOT NULL,
					`windowsSoftwareId` varchar(100),
					`windowsDisplayName` varchar(100),
					`windowsDisplayVersion` varchar(100),
					`type` varchar(30) NOT NULL,
					`installSize` BIGINT,
					PRIMARY KEY (`name`, `version`, `subVersion`, `language`, `architecture`)
				) %s;
				''' % self._sql.getTableCreationOptions('SOFTWARE')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_software_windowsSoftwareId` on `SOFTWARE` (`windowsSoftwareId`);')
			self._sql.execute('CREATE INDEX `index_software_type` on `SOFTWARE` (`type`);')

		if 'SOFTWARE_CONFIG' not in existingTables:
			logger.debug(u'Creating table SOFTWARE_CONFIG')
			table = u'''CREATE TABLE `SOFTWARE_CONFIG` (
					`config_id` integer NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
					`clientId` varchar(255) NOT NULL,
					`name` varchar(100) NOT NULL,
					`version` varchar(100) NOT NULL,
					`subVersion` varchar(100) NOT NULL,
					`language` varchar(10) NOT NULL,
					`architecture` varchar(3) NOT NULL,
					`uninstallString` varchar(200),
					`binaryName` varchar(100),
					`firstseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`lastseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`state` TINYINT NOT NULL,
					`usageFrequency` integer NOT NULL DEFAULT -1,
					`lastUsed` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00',
					`licenseKey` VARCHAR(1024),
					PRIMARY KEY (`config_id`)
				) %s;
				''' % self._sql.getTableCreationOptions('SOFTWARE_CONFIG')
			logger.debug(table)
			self._sql.execute(table)
			self._sql.execute('CREATE INDEX `index_software_config_clientId` on `SOFTWARE_CONFIG` (`clientId`);')
			self._sql.execute('CREATE INDEX `index_software_config_nvsla` on `SOFTWARE_CONFIG` (`name`, `version`, `subVersion`, `language`, `architecture`);')

		self._createAuditHardwareTables()

	def _createTableHost(self):
		logger.debug(u'Creating table HOST')
		table = u'''CREATE TABLE `HOST` (
				`hostId` varchar(255) NOT NULL,
				`type` varchar(30),
				`description` varchar(100),
				`notes` varchar(500),
				`hardwareAddress` varchar(17),
				`ipAddress` varchar(15),
				`inventoryNumber` varchar(30),
				`created` TIMESTAMP,
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
				PRIMARY KEY (`hostId`)
			) {0};'''.format(self._sql.getTableCreationOptions('HOST'))
		logger.debug(table)
		self._sql.execute(table)
		self._sql.execute('CREATE INDEX `index_host_type` on `HOST` (`type`);')

	def _createAuditHardwareTables(self):
		tables = self._sql.getTables()
		existingTables = set(tables.keys())

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

			hardwareDeviceValuesProcessed = 0
			hardwareConfigValuesProcessed = 0
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
							hardwareDeviceTable += u'ADD `{column}` {type} NULL,\n'.format(
								column=value,
								type=valueInfo["Type"]
							)
					else:
						hardwareDeviceTable += u'`{column}` {type} NULL,\n'.format(
							column=value,
							type=valueInfo["Type"]
						)
					hardwareDeviceValuesProcessed += 1
				elif valueInfo['Scope'] == 'i':
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
							hardwareConfigTable += u'ADD `{column}` {type} NULL,\n'.format(
								column=value,
								type=valueInfo['Type']
							)
					else:
						hardwareConfigTable += u'`%s` %s NULL,\n' % (value, valueInfo['Type'])
					hardwareConfigValuesProcessed += 1

			if not hardwareDeviceTableExists:
				hardwareDeviceTable += u'PRIMARY KEY (`hardware_id`)\n'
			if not hardwareConfigTableExists:
				hardwareConfigTable += u'PRIMARY KEY (`config_id`)\n'

			# Remove leading and trailing whitespace
			hardwareDeviceTable = hardwareDeviceTable.strip()
			hardwareConfigTable = hardwareConfigTable.strip()

			# Remove trailing comma
			if hardwareDeviceTable.endswith(u','):
				hardwareDeviceTable = hardwareDeviceTable[:-1]
			if hardwareConfigTable.endswith(u','):
				hardwareConfigTable = hardwareConfigTable[:-1]

			# Finish sql query
			if hardwareDeviceTableExists:
				hardwareDeviceTable += u' ;\n'
			else:
				hardwareDeviceTable += u'\n) %s;\n' % self._sql.getTableCreationOptions(hardwareDeviceTableName)

			if hardwareConfigTableExists:
				hardwareConfigTable += u' ;\n'
			else:
				hardwareConfigTable += u'\n) %s;\n' % self._sql.getTableCreationOptions(hardwareConfigTableName)

			# Execute sql query
			if hardwareDeviceValuesProcessed or not hardwareDeviceTableExists:
				logger.debug(hardwareDeviceTable)
				self._sql.execute(hardwareDeviceTable)
			if hardwareConfigValuesProcessed or not hardwareConfigTableExists:
				logger.debug(hardwareConfigTable)
				self._sql.execute(hardwareConfigTable)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		data = self._objectToDatabaseHash(host)
		where = self._uniqueCondition(host)
		if self._sql.getRow('select * from `HOST` where {0}'.format(where)):
			self._sql.update('HOST', where, data, updateWhereNone=True)
		else:
			self._sql.insert('HOST', data)

	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		data = self._objectToDatabaseHash(host)
		where = self._uniqueCondition(host)
		self._sql.update('HOST', where, data)

	def host_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.host_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting hosts, filter: %s" % filter)

		hostType = forceList(filter.get('type', []))
		if 'OpsiDepotserver' in hostType and 'OpsiConfigserver' not in hostType:
			hostType.append('OpsiConfigserver')
			filter['type'] = hostType

		hosts = []
		(attributes, filter) = self._adjustAttributes(Host, attributes, filter)
		for res in self._sql.getSet(self._createQuery('HOST', attributes, filter)):
			self._adjustResult(Host, res)
			hosts.append(Host.fromHash(res))

		return hosts

	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)

		for host in forceObjectClassList(hosts, Host):
			logger.info(u"Deleting host {0}".format(host))
			where = self._uniqueCondition(host)
			self._sql.delete('HOST', where)

			auditHardwareOnDeletedHost = self.auditHardwareOnHost_getObjects(objectId=host.id)
			if auditHardwareOnDeletedHost:
				self.auditHardwareOnHost_deleteObjects(auditHardwareOnDeletedHost)

			# TODO: Delete audit data!
			# Siehe: https://redmine.uib.local/issues/869

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.config_insertObject(self, config)
		data = self._objectToDatabaseHash(config)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		if possibleValues is None:
			possibleValues = []
		if defaultValues is None:
			defaultValues = []
		del data['possibleValues']
		del data['defaultValues']

		where = self._uniqueCondition(config)
		if self._sql.getRow('select * from `CONFIG` where %s' % where):
			self._sql.update('CONFIG', where, data, updateWhereNone=True)
		else:
			self._sql.insert('CONFIG', data)

		self._sql.delete('CONFIG_VALUE', where)
		for value in possibleValues:
			self._sql.insert('CONFIG_VALUE', {
				'configId': data['configId'],
				'value': value,
				'isDefault': (value in defaultValues)
				})

	def config_updateObject(self, config):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.config_updateObject(self, config)
		data = self._objectToDatabaseHash(config)
		where = self._uniqueCondition(config)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		if possibleValues is None:
			possibleValues = []
		if defaultValues is None:
			defaultValues = []
		del data['possibleValues']
		del data['defaultValues']

		self._sql.update('CONFIG', where, data)
		self._sql.delete('CONFIG_VALUE', where)
		[self._sql.insert('CONFIG_VALUE', {
			'configId': data['configId'],
			'value': value,
			'isDefault': (value in defaultValues)
			}
		) for value in possibleValues]

	def config_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.config_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting configs, filter: %s" % filter)
		configs = []
		(attributes, filter) = self._adjustAttributes(Config, attributes, filter)

		if 'defaultValues' in filter:
			if filter['defaultValues']:
				configIds = filter.get('configId')
				filter['configId'] = [res['configId'] for res in
					self._sql.getSet(
						self._createQuery(
							'CONFIG_VALUE',
							('configId', ),
							{'configId': configIds, 'value': filter['defaultValues'], 'isDefault': True}
						)
					)
				]

				if not filter['configId']:
					return []

			del filter['defaultValues']

		if 'possibleValues' in filter:
			if filter['possibleValues']:
				configIds = filter.get('configId')
				filter['configId'] = [res['configId'] for res in
					self._sql.getSet(
						self._createQuery(
							'CONFIG_VALUE',
							('configId', ),
							{'configId': configIds, 'value': filter['possibleValues']}
						)
					)
				]

				if not filter['configId']:
					return []

			del filter['possibleValues']
		attrs = [attr for attr in attributes if attr not in ('defaultValues', 'possibleValues')]
		for res in self._sql.getSet(self._createQuery('CONFIG', attrs, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self._sql.getSet(u"select * from CONFIG_VALUE where `configId` = '%s'" % res['configId']):
					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])
			self._adjustResult(Config, res)
			configs.append(Config.fromHash(res))
		return configs

	def config_deleteObjects(self, configs):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.config_deleteObjects(self, configs)
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Deleting config %s" % config)
			where = self._uniqueCondition(config)
			self._sql.delete('CONFIG_VALUE', where)
			self._sql.delete('CONFIG', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.configState_insertObject(self, configState)
		data = self._objectToDatabaseHash(configState)
		data['values'] = json.dumps(data['values'])

		where = self._uniqueCondition(configState)
		if self._sql.getRow('select * from `CONFIG_STATE` where %s' % where):
			self._sql.update('CONFIG_STATE', where, data, updateWhereNone=True)
		else:
			self._sql.insert('CONFIG_STATE', data)

	def configState_updateObject(self, configState):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.configState_updateObject(self, configState)
		data = self._objectToDatabaseHash(configState)
		where = self._uniqueCondition(configState)
		data['values'] = json.dumps(data['values'])
		self._sql.update('CONFIG_STATE', where, data)

	def configState_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.configState_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting configStates, filter: %s" % filter)
		configStates = []
		(attributes, filter) = self._adjustAttributes(ConfigState, attributes, filter)
		for res in self._sql.getSet(self._createQuery('CONFIG_STATE', attributes, filter)):
			if 'values' in res:
				res['values'] = json.loads(res['values'])
			configStates.append(ConfigState.fromHash(res))
		return configStates

	def configState_deleteObjects(self, configStates):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.configState_deleteObjects(self, configStates)
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info("Deleting configState %s" % configState)
			where = self._uniqueCondition(configState)
			self._sql.delete('CONFIG_STATE', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		self._requiresEnabledSQLBackendModule()
		backendinfo = self._context.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']

		publicKey = keys.Key.fromString(data=base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''; mks = modules.keys(); mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue
			if helpermodules.has_key(module):
				val = helpermodules[module]
				if int(val) > 0:
					modules[module] = True
			else:
				val = modules[module]
				if val == False:
					val = 'no'
				elif val == True:
					val = 'yes'
			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [long(modules['signature'])])):
			logger.error(u"Failed to verify modules signature")
			return

		ConfigDataBackend.product_insertObject(self, product)
		data = self._objectToDatabaseHash(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']

		where = self._uniqueCondition(product)
		if self._sql.getRow('select * from `PRODUCT` where %s' % where):
			self._sql.update('PRODUCT', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT', data)

		self._sql.delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])

		[self._sql.insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT',
			{
				'windowsSoftwareId': windowsSoftwareId,
				'productId': data['productId']
			}
		) for windowsSoftwareId in windowsSoftwareIds]

	def product_updateObject(self, product):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.product_updateObject(self, product)
		data = self._objectToDatabaseHash(product)
		where = self._uniqueCondition(product)
		windowsSoftwareIds = data['windowsSoftwareIds']
		del data['windowsSoftwareIds']
		del data['productClassIds']
		self._sql.update('PRODUCT', where, data)
		self._sql.delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % data['productId'])
		if windowsSoftwareIds:
			[self._sql.insert('WINDOWS_SOFTWARE_ID_TO_PRODUCT',
				{
					'windowsSoftwareId': windowsSoftwareId,
					'productId': data['productId']
				}
			) for windowsSoftwareId in windowsSoftwareIds]

	def product_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting products, filter: %s" % filter)
		products = []
		(attributes, filter) = self._adjustAttributes(Product, attributes, filter)
		for res in self._sql.getSet(self._createQuery('PRODUCT', attributes, filter)):
			res['windowsSoftwareIds'] = []
			res['productClassIds'] = []
			if not attributes or 'windowsSoftwareIds' in attributes:
				for res2 in self._sql.getSet(u"select * from WINDOWS_SOFTWARE_ID_TO_PRODUCT where `productId` = '%s'" % res['productId']):
					res['windowsSoftwareIds'].append(res2['windowsSoftwareId'])
			if not attributes or 'productClassIds' in attributes:
				pass
			self._adjustResult(Product, res)
			products.append(Product.fromHash(res))
		return products

	def product_deleteObjects(self, products):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.product_deleteObjects(self, products)
		for product in forceObjectClassList(products, Product):
			logger.info("Deleting product %s" % product)
			where = self._uniqueCondition(product)
			self._sql.delete('WINDOWS_SOFTWARE_ID_TO_PRODUCT', "`productId` = '%s'" % product.getId())
			self._sql.delete('PRODUCT', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		if possibleValues is None:
			possibleValues = []
		if defaultValues is None:
			defaultValues = []
		del data['possibleValues']
		del data['defaultValues']

		where = self._uniqueCondition(productProperty)
		if self._sql.getRow('select * from `PRODUCT_PROPERTY` where %s' % where):
			self._sql.update('PRODUCT_PROPERTY', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_PROPERTY', data)

		if possibleValues is not None:
			self._sql.delete('PRODUCT_PROPERTY_VALUE', where)

		[self._sql.insert('PRODUCT_PROPERTY_VALUE',
			{
				'productId': data['productId'],
				'productVersion': data['productVersion'],
				'packageVersion': data['packageVersion'],
				'propertyId': data['propertyId'],
				'value': value,
				'isDefault': (value in defaultValues)
			}
		) for value in possibleValues]

	def productProperty_updateObject(self, productProperty):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		data = self._objectToDatabaseHash(productProperty)
		where = self._uniqueCondition(productProperty)
		possibleValues = data['possibleValues']
		defaultValues = data['defaultValues']
		if possibleValues is None:
			possibleValues = []
		if defaultValues is None:
			defaultValues = []
		del data['possibleValues']
		del data['defaultValues']
		self._sql.update('PRODUCT_PROPERTY', where, data)

		if possibleValues is not None:
			self._sql.delete('PRODUCT_PROPERTY_VALUE', where)

		[self._sql.insert('PRODUCT_PROPERTY_VALUE',
			{
				'productId': data['productId'],
				'productVersion': data['productVersion'],
				'packageVersion': data['packageVersion'],
				'propertyId': data['propertyId'],
				'value': value,
				'isDefault': (value in defaultValues)
			}
		) for value in possibleValues]

	def productProperty_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting product properties, filter: %s" % filter)
		productProperties = []
		(attributes, filter) = self._adjustAttributes(ProductProperty, attributes, filter)
		for res in self._sql.getSet(self._createQuery('PRODUCT_PROPERTY', attributes, filter)):
			res['possibleValues'] = []
			res['defaultValues'] = []
			if not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes:
				for res2 in self._sql.getSet(
					u"select * from PRODUCT_PROPERTY_VALUE where "
					u"`propertyId` = '{0}' AND `productId` = '{1}' AND "
					u"`productVersion` = '{2}' AND "
					u"`packageVersion` = '{3}'".format(
						res['propertyId'],
						res['productId'],
						res['productVersion'],
						res['packageVersion']
					)):

					res['possibleValues'].append(res2['value'])
					if res2['isDefault']:
						res['defaultValues'].append(res2['value'])

			productProperties.append(ProductProperty.fromHash(res))

		return productProperties

	def productProperty_deleteObjects(self, productProperties):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info("Deleting product property %s" % productProperty)
			where = self._uniqueCondition(productProperty)
			self._sql.delete('PRODUCT_PROPERTY_VALUE', where)
			self._sql.delete('PRODUCT_PROPERTY', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		data = self._objectToDatabaseHash(productDependency)

		where = self._uniqueCondition(productDependency)
		if self._sql.getRow('select * from `PRODUCT_DEPENDENCY` where %s' % where):
			self._sql.update('PRODUCT_DEPENDENCY', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_DEPENDENCY', data)

	def productDependency_updateObject(self, productDependency):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		data = self._objectToDatabaseHash(productDependency)
		where = self._uniqueCondition(productDependency)

		self._sql.update('PRODUCT_DEPENDENCY', where, data)

	def productDependency_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting product dependencies, filter: %s" % filter)
		(attributes, filter) = self._adjustAttributes(ProductDependency, attributes, filter)
		return [ProductDependency.fromHash(res) for res in self._sql.getSet(self._createQuery('PRODUCT_DEPENDENCY', attributes, filter))]

	def productDependency_deleteObjects(self, productDependencies):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			logger.info("Deleting product dependency %s" % productDependency)
			where = self._uniqueCondition(productDependency)
			self._sql.delete('PRODUCT_DEPENDENCY', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		data = self._objectToDatabaseHash(productOnDepot)

		productOnDepotClone = productOnDepot.clone(identOnly=True)
		productOnDepotClone.productVersion = None
		productOnDepotClone.packageVersion = None
		productOnDepotClone.productType = None
		where = self._uniqueCondition(productOnDepotClone)
		if self._sql.getRow('select * from `PRODUCT_ON_DEPOT` where %s' % where):
			self._sql.update('PRODUCT_ON_DEPOT', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_ON_DEPOT', data)

	def productOnDepot_updateObject(self, productOnDepot):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
		data = self._objectToDatabaseHash(productOnDepot)
		where = self._uniqueCondition(productOnDepot)
		self._sql.update('PRODUCT_ON_DEPOT', where, data)

	def productOnDepot_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		(attributes, filter) = self._adjustAttributes(ProductOnDepot, attributes, filter)
		return [ProductOnDepot.fromHash(res) for res in
				self._sql.getSet(self._createQuery('PRODUCT_ON_DEPOT', attributes, filter))]

	def productOnDepot_deleteObjects(self, productOnDepots):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			logger.info(u"Deleting productOnDepot %s" % productOnDepot)
			where = self._uniqueCondition(productOnDepot)
			self._sql.delete('PRODUCT_ON_DEPOT', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		data = self._objectToDatabaseHash(productOnClient)

		productOnClientClone = productOnClient.clone(identOnly=True)
		productOnClientClone.productVersion = None
		productOnClientClone.packageVersion = None
		productOnClientClone.productType = None
		where = self._uniqueCondition(productOnClientClone)

		if self._sql.getRow('select * from `PRODUCT_ON_CLIENT` where %s' % where):
			self._sql.update('PRODUCT_ON_CLIENT', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_ON_CLIENT', data)

	def productOnClient_updateObject(self, productOnClient):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		data = self._objectToDatabaseHash(productOnClient)
		where = self._uniqueCondition(productOnClient)
		self._sql.update('PRODUCT_ON_CLIENT', where, data)

	def productOnClient_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting productOnClients, filter: %s" % filter)
		(attributes, filter) = self._adjustAttributes(ProductOnClient, attributes, filter)
		return [ProductOnClient.fromHash(res) for res in
				self._sql.getSet(self._createQuery('PRODUCT_ON_CLIENT', attributes, filter))]

	def productOnClient_deleteObjects(self, productOnClients):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		for productOnClient in forceObjectClassList(productOnClients, ProductOnClient):
			logger.info(u"Deleting productOnClient %s" % productOnClient)
			where = self._uniqueCondition(productOnClient)
			self._sql.delete('PRODUCT_ON_CLIENT', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
		if not self._sql.getSet(self._createQuery('HOST', ['hostId'], {"hostId": productPropertyState.objectId})):
			raise BackendReferentialIntegrityError(u"Object '%s' does not exist" % productPropertyState.objectId)
		data = self._objectToDatabaseHash(productPropertyState)
		data['values'] = json.dumps(data['values'])

		where = self._uniqueCondition(productPropertyState)
		if self._sql.getRow('select * from `PRODUCT_PROPERTY_STATE` where %s' % where):
			self._sql.update('PRODUCT_PROPERTY_STATE', where, data, updateWhereNone=True)
		else:
			self._sql.insert('PRODUCT_PROPERTY_STATE', data)

	def productPropertyState_updateObject(self, productPropertyState):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
		data = self._objectToDatabaseHash(productPropertyState)
		where = self._uniqueCondition(productPropertyState)
		data['values'] = json.dumps(data['values'])
		self._sql.update('PRODUCT_PROPERTY_STATE', where, data)

	def productPropertyState_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting productPropertyStates, filter: %s" % filter)
		productPropertyStates = []
		(attributes, filter) = self._adjustAttributes(ProductPropertyState, attributes, filter)
		for res in self._sql.getSet(self._createQuery('PRODUCT_PROPERTY_STATE', attributes, filter)):
			try:
				res['values'] = json.loads(res['values'])
			except KeyError:
				pass  # Could be non-existing and it would be okay.
			productPropertyStates.append(ProductPropertyState.fromHash(res))
		return productPropertyStates

	def productPropertyState_deleteObjects(self, productPropertyStates):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			logger.info(u"Deleting productPropertyState %s" % productPropertyState)
			where = self._uniqueCondition(productPropertyState)
			self._sql.delete('PRODUCT_PROPERTY_STATE', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.group_insertObject(self, group)
		data = self._objectToDatabaseHash(group)

		where = self._uniqueCondition(group)
		if self._sql.getRow('select * from `GROUP` where %s' % where):
			self._sql.update('GROUP', where, data, updateWhereNone=True)
		else:
			self._sql.insert('GROUP', data)

	def group_updateObject(self, group):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.group_updateObject(self, group)
		data = self._objectToDatabaseHash(group)
		where = self._uniqueCondition(group)
		self._sql.update('GROUP', where, data)

	def group_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting groups, filter: %s" % filter)
		groups = []
		(attributes, filter) = self._adjustAttributes(Group, attributes, filter)
		for res in self._sql.getSet(self._createQuery('GROUP', attributes, filter)):
			self._adjustResult(Group, res)
			groups.append(Group.fromHash(res))
		return groups

	def group_deleteObjects(self, groups):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.group_deleteObjects(self, groups)
		for group in forceObjectClassList(groups, Group):
			logger.info(u"Deleting group %s" % group)
			where = self._uniqueCondition(group)
			self._sql.delete('GROUP', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
		data = self._objectToDatabaseHash(objectToGroup)

		where = self._uniqueCondition(objectToGroup)
		if self._sql.getRow('select * from `OBJECT_TO_GROUP` where %s' % where):
			self._sql.update('OBJECT_TO_GROUP', where, data, updateWhereNone=True)
		else:
			self._sql.insert('OBJECT_TO_GROUP', data)

	def objectToGroup_updateObject(self, objectToGroup):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
		data = self._objectToDatabaseHash(objectToGroup)
		where = self._uniqueCondition(objectToGroup)
		self._sql.update('OBJECT_TO_GROUP', where, data)

	def objectToGroup_getObjects(self, attributes=[], **filter):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting objectToGroups, filter: %s" % filter)
		(attributes, filter) = self._adjustAttributes(ObjectToGroup, attributes, filter)
		return [ObjectToGroup.fromHash(res) for res in
				self._sql.getSet(self._createQuery('OBJECT_TO_GROUP', attributes, filter))]

	def objectToGroup_deleteObjects(self, objectToGroups):
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			logger.info(u"Deleting objectToGroup %s" % objectToGroup)
			where = self._uniqueCondition(objectToGroup)
			self._sql.delete('OBJECT_TO_GROUP', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_insertObject(self, licenseContract):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseContract_insertObject(self, licenseContract)
		data = self._objectToDatabaseHash(licenseContract)

		where = self._uniqueCondition(licenseContract)
		if self._sql.getRow('select * from `LICENSE_CONTRACT` where %s' % where):
			self._sql.update('LICENSE_CONTRACT', where, data, updateWhereNone=True)
		else:
			self._sql.insert('LICENSE_CONTRACT', data)

	def licenseContract_updateObject(self, licenseContract):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseContract_updateObject(self, licenseContract)
		data = self._objectToDatabaseHash(licenseContract)
		where = self._uniqueCondition(licenseContract)
		self._sql.update('LICENSE_CONTRACT', where, data)

	def licenseContract_getObjects(self, attributes=[], **filter):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return []

		ConfigDataBackend.licenseContract_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licenseContracts, filter: %s" % filter)
		licenseContracts = []
		(attributes, filter) = self._adjustAttributes(LicenseContract, attributes, filter)
		for res in self._sql.getSet(self._createQuery('LICENSE_CONTRACT', attributes, filter)):
			self._adjustResult(LicenseContract, res)
			licenseContracts.append(LicenseContract.fromHash(res))
		return licenseContracts

	def licenseContract_deleteObjects(self, licenseContracts):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseContract_deleteObjects(self, licenseContracts)
		for licenseContract in forceObjectClassList(licenseContracts, LicenseContract):
			logger.info(u"Deleting licenseContract %s" % licenseContract)
			where = self._uniqueCondition(licenseContract)
			self._sql.delete('LICENSE_CONTRACT', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_insertObject(self, softwareLicense):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicense_insertObject(self, softwareLicense)
		data = self._objectToDatabaseHash(softwareLicense)

		where = self._uniqueCondition(softwareLicense)
		if self._sql.getRow('select * from `SOFTWARE_LICENSE` where %s' % where):
			self._sql.update('SOFTWARE_LICENSE', where, data, updateWhereNone=True)
		else:
			self._sql.insert('SOFTWARE_LICENSE', data)

	def softwareLicense_updateObject(self, softwareLicense):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicense_updateObject(self, softwareLicense)
		data = self._objectToDatabaseHash(softwareLicense)
		where = self._uniqueCondition(softwareLicense)
		self._sql.update('SOFTWARE_LICENSE', where, data)

	def softwareLicense_getObjects(self, attributes=[], **filter):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return []

		ConfigDataBackend.softwareLicense_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting softwareLicenses, filter: %s" % filter)
		softwareLicenses = []
		(attributes, filter) = self._adjustAttributes(SoftwareLicense, attributes, filter)
		for res in self._sql.getSet(self._createQuery('SOFTWARE_LICENSE', attributes, filter)):
			self._adjustResult(SoftwareLicense, res)
			softwareLicenses.append(SoftwareLicense.fromHash(res))
		return softwareLicenses

	def softwareLicense_deleteObjects(self, softwareLicenses):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicense_deleteObjects(self, softwareLicenses)
		for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense):
			logger.info(u"Deleting softwareLicense %s" % softwareLicense)
			where = self._uniqueCondition(softwareLicense)
			self._sql.delete('SOFTWARE_LICENSE', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePools
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_insertObject(self, licensePool):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		backendinfo = self._context.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']

		publicKey = keys.Key.fromString(data=base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''; mks = modules.keys(); mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue

			if helpermodules.has_key(module):
				val = helpermodules[module]
				if int(val) > 0:
					modules[module] = True
			else:
				val = modules[module]
				if val == False:
					val = 'no'
				if val == True:
					val = 'yes'

			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [long(modules['signature'])])):
			logger.error(u"Failed to verify modules signature")
			return

		ConfigDataBackend.licensePool_insertObject(self, licensePool)
		data = self._objectToDatabaseHash(licensePool)
		productIds = data['productIds']
		del data['productIds']

		where = self._uniqueCondition(licensePool)
		if self._sql.getRow('select * from `LICENSE_POOL` where %s' % where):
			self._sql.update('LICENSE_POOL', where, data, updateWhereNone=True)
		else:
			self._sql.insert('LICENSE_POOL', data)

		self._sql.delete('PRODUCT_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])

		[self._sql.insert('PRODUCT_ID_TO_LICENSE_POOL',
			{
				'productId': productId,
				'licensePoolId': data['licensePoolId']
			}
		) for productId in productIds]

	def licensePool_updateObject(self, licensePool):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licensePool_updateObject(self, licensePool)
		data = self._objectToDatabaseHash(licensePool)
		where = self._uniqueCondition(licensePool)
		productIds = data['productIds']
		del data['productIds']
		self._sql.update('LICENSE_POOL', where, data)
		self._sql.delete('PRODUCT_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % data['licensePoolId'])

		[self._sql.insert('PRODUCT_ID_TO_LICENSE_POOL',
			{
				'productId': productId,
				'licensePoolId': data['licensePoolId']
			}
		) for productId in productIds]

	def licensePool_getObjects(self, attributes=[], **filter):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return []

		ConfigDataBackend.licensePool_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licensePools, filter: %s" % filter)
		licensePools = []
		(attributes, filter) = self._adjustAttributes(LicensePool, attributes, filter)

		if filter.has_key('productIds'):
			if filter['productIds']:
				licensePoolIds = filter.get('licensePoolId')
				filter['licensePoolId'] = []
				for res in self._sql.getSet(self._createQuery('PRODUCT_ID_TO_LICENSE_POOL', ['licensePoolId'], {'licensePoolId': licensePoolIds, 'productId': filter['productIds']})):
					filter['licensePoolId'].append(res['licensePoolId'])
				if not filter['licensePoolId']:
					return []
			del filter['productIds']

		attrs = [attr for attr in attributes if attr != 'productIds']
		for res in self._sql.getSet(self._createQuery('LICENSE_POOL', attrs, filter)):
			res['productIds'] = []
			if not attributes or 'productIds' in attributes:
				for res2 in self._sql.getSet(u"select * from PRODUCT_ID_TO_LICENSE_POOL where `licensePoolId` = '%s'" % res['licensePoolId']):
					res['productIds'].append(res2['productId'])
			self._adjustResult(LicensePool, res)
			licensePools.append(LicensePool.fromHash(res))
		return licensePools

	def licensePool_deleteObjects(self, licensePools):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licensePool_deleteObjects(self, licensePools)
		for licensePool in forceObjectClassList(licensePools, LicensePool):
			logger.info(u"Deleting licensePool %s" % licensePool)
			where = self._uniqueCondition(licensePool)
			self._sql.delete('PRODUCT_ID_TO_LICENSE_POOL', "`licensePoolId` = '%s'" % licensePool.id)
			self._sql.delete('LICENSE_POOL', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool)
		data = self._objectToDatabaseHash(softwareLicenseToLicensePool)

		where = self._uniqueCondition(softwareLicenseToLicensePool)
		if self._sql.getRow('select * from `SOFTWARE_LICENSE_TO_LICENSE_POOL` where %s' % where):
			self._sql.update('SOFTWARE_LICENSE_TO_LICENSE_POOL', where, data, updateWhereNone=True)
		else:
			self._sql.insert('SOFTWARE_LICENSE_TO_LICENSE_POOL', data)

	def softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool)
		data = self._objectToDatabaseHash(softwareLicenseToLicensePool)
		where = self._uniqueCondition(softwareLicenseToLicensePool)
		self._sql.update('SOFTWARE_LICENSE_TO_LICENSE_POOL', where, data)

	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return []

		ConfigDataBackend.softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting softwareLicenseToLicensePool, filter: %s" % filter)
		(attributes, filter) = self._adjustAttributes(SoftwareLicenseToLicensePool, attributes, filter)
		return [SoftwareLicenseToLicensePool.fromHash(res) for res in
				self._sql.getSet(
					self._createQuery(
						'SOFTWARE_LICENSE_TO_LICENSE_POOL', attributes, filter
					)
				)
		]

	def softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools)
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			logger.info(u"Deleting softwareLicenseToLicensePool %s" % softwareLicenseToLicensePool)
			where = self._uniqueCondition(softwareLicenseToLicensePool)
			self._sql.delete('SOFTWARE_LICENSE_TO_LICENSE_POOL', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_insertObject(self, licenseOnClient):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseOnClient_insertObject(self, licenseOnClient)
		data = self._objectToDatabaseHash(licenseOnClient)

		where = self._uniqueCondition(licenseOnClient)
		if self._sql.getRow('select * from `LICENSE_ON_CLIENT` where %s' % where):
			self._sql.update('LICENSE_ON_CLIENT', where, data, updateWhereNone=True)
		else:
			self._sql.insert('LICENSE_ON_CLIENT', data)

	def licenseOnClient_updateObject(self, licenseOnClient):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseOnClient_updateObject(self, licenseOnClient)
		data = self._objectToDatabaseHash(licenseOnClient)
		where = self._uniqueCondition(licenseOnClient)
		self._sql.update('LICENSE_ON_CLIENT', where, data)

	def licenseOnClient_getObjects(self, attributes=[], **filter):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return []

		ConfigDataBackend.licenseOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting licenseOnClient, filter: %s" % filter)
		(attributes, filter) = self._adjustAttributes(LicenseOnClient, attributes, filter)
		return [LicenseOnClient.fromHash(res) for res in
				self._sql.getSet(
					self._createQuery('LICENSE_ON_CLIENT', attributes, filter)
				)
		]

	def licenseOnClient_deleteObjects(self, licenseOnClients):
		if not self._licenseManagementModule:
			logger.warning(u"License management module disabled")
			return

		ConfigDataBackend.licenseOnClient_deleteObjects(self, licenseOnClients)
		for licenseOnClient in forceObjectClassList(licenseOnClients, LicenseOnClient):
			logger.info(u"Deleting licenseOnClient %s" % licenseOnClient)
			where = self._uniqueCondition(licenseOnClient)
			self._sql.delete('LICENSE_ON_CLIENT', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_insertObject(self, auditSoftware)
		data = self._objectToDatabaseHash(auditSoftware)

		where = self._uniqueCondition(auditSoftware)
		if self._sql.getRow('select * from `SOFTWARE` where %s' % where):
			self._sql.update('SOFTWARE', where, data, updateWhereNone=True)
		else:
			self._sql.insert('SOFTWARE', data)

	def auditSoftware_updateObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_updateObject(self, auditSoftware)
		data = self._objectToDatabaseHash(auditSoftware)
		where = self._uniqueCondition(auditSoftware)
		self._sql.update('SOFTWARE', where, data)

	def auditSoftware_getHashes(self, attributes=[], **filter):
		(attributes, filter) = self._adjustAttributes(AuditSoftware, attributes, filter)
		return self._sql.getSet(self._createQuery('SOFTWARE', attributes, filter))

	def auditSoftware_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftware_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting auditSoftware, filter: %s" % filter)
		return [AuditSoftware.fromHash(h) for h in
			self.auditSoftware_getHashes(attributes, **filter)
		]

	def auditSoftware_deleteObjects(self, auditSoftwares):
		ConfigDataBackend.auditSoftware_deleteObjects(self, auditSoftwares)
		for auditSoftware in forceObjectClassList(auditSoftwares, AuditSoftware):
			logger.info(u"Deleting auditSoftware %s" % auditSoftware)
			where = self._uniqueCondition(auditSoftware)
			self._sql.delete('SOFTWARE', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareToLicensePools
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareToLicensePool_insertObject(self, auditSoftwareToLicensePool):
		ConfigDataBackend.auditSoftwareToLicensePool_insertObject(self, auditSoftwareToLicensePool)
		data = self._objectToDatabaseHash(auditSoftwareToLicensePool)

		where = self._uniqueCondition(auditSoftwareToLicensePool)
		if self._sql.getRow('select * from `AUDIT_SOFTWARE_TO_LICENSE_POOL` where %s' % where):
			self._sql.update('AUDIT_SOFTWARE_TO_LICENSE_POOL', where, data, updateWhereNone=True)
		else:
			self._sql.insert('AUDIT_SOFTWARE_TO_LICENSE_POOL', data)

	def auditSoftwareToLicensePool_updateObject(self, auditSoftwareToLicensePool):
		ConfigDataBackend.auditSoftwareToLicensePool_updateObject(self, auditSoftwareToLicensePool)
		data = self._objectToDatabaseHash(auditSoftwareToLicensePool)
		where = self._uniqueCondition(auditSoftwareToLicensePool)
		self._sql.update('AUDIT_SOFTWARE_TO_LICENSE_POOL', where, data)

	def auditSoftwareToLicensePool_getHashes(self, attributes=[], **filter):
		(attributes, filter) = self._adjustAttributes(AuditSoftwareToLicensePool, attributes, filter)
		return self._sql.getSet(self._createQuery('AUDIT_SOFTWARE_TO_LICENSE_POOL', attributes, filter))

	def auditSoftwareToLicensePool_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftwareToLicensePool_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting auditSoftwareToLicensePool, filter: %s" % filter)
		return [AuditSoftwareToLicensePool.fromHash(h) for h in
				self.auditSoftwareToLicensePool_getHashes(attributes, **filter)]

	def auditSoftwareToLicensePool_deleteObjects(self, auditSoftwareToLicensePools):
		ConfigDataBackend.auditSoftwareToLicensePool_deleteObjects(self, auditSoftwareToLicensePools)
		for auditSoftwareToLicensePool in forceObjectClassList(auditSoftwareToLicensePools, AuditSoftwareToLicensePool):
			logger.info(u"Deleting auditSoftware %s" % auditSoftwareToLicensePool)
			where = self._uniqueCondition(auditSoftwareToLicensePool)
			self._sql.delete('AUDIT_SOFTWARE_TO_LICENSE_POOL', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient)
		data = self._objectToDatabaseHash(auditSoftwareOnClient)

		where = self._uniqueCondition(auditSoftwareOnClient)
		if self._sql.getRow('select * from `SOFTWARE_CONFIG` where %s' % where):
			self._sql.update('SOFTWARE_CONFIG', where, data, updateWhereNone=True)
		else:
			self._sql.insert('SOFTWARE_CONFIG', data)

	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient)
		data = self._objectToDatabaseHash(auditSoftwareOnClient)
		where = self._uniqueCondition(auditSoftwareOnClient)
		self._sql.update('SOFTWARE_CONFIG', where, data)

	def auditSoftwareOnClient_getHashes(self, attributes=[], **filter):
		(attributes, filter) = self._adjustAttributes(AuditSoftwareOnClient, attributes, filter)
		return self._sql.getSet(self._createQuery('SOFTWARE_CONFIG', attributes, filter))

	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftwareOnClient_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting auditSoftwareOnClient, filter: %s" % filter)
		return [AuditSoftwareOnClient.fromHash(h) for h in
				self.auditSoftwareOnClient_getHashes(attributes, **filter)]

	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		ConfigDataBackend.auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients)
		for auditSoftwareOnClient in forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient):
			logger.info(u"Deleting auditSoftwareOnClient %s" % auditSoftwareOnClient)
			where = self._uniqueCondition(auditSoftwareOnClient)
			self._sql.delete('SOFTWARE_CONFIG', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def _uniqueAuditHardwareCondition(self, auditHardware):
		if hasattr(auditHardware, 'toHash'):
			auditHardware = auditHardware.toHash()

		def createCondition():
			for attribute, value in auditHardware.items():
				if attribute in ('hardwareClass', 'type'):
					continue

				if value is None or value == [None]:
					yield u"`{0}` is NULL".format(attribute)
				elif isinstance(value, (float, long, int, bool)):
					yield u"`{0}` = {1}".format(attribute, value)
				else:
					yield u"`{0}` = '{1}'".format(attribute, self._sql.escapeApostrophe(self._sql.escapeBackslash(value)))

		return u' and '.join(createCondition())

	def _getHardwareIds(self, auditHardware):
		try:
			auditHardware = auditHardware.toHash()
		except AttributeError:  # Method not present
			pass

		for (attribute, value) in auditHardware.items():
			if value is None:
				auditHardware[attribute] = [None]
			elif isinstance(value, unicode):
				auditHardware[attribute] = self._sql.escapeAsterisk(value)

		logger.debug(u"Getting hardware ids, filter {0}", auditHardware)
		hardwareIds = self._auditHardware_search(returnHardwareIds=True, attributes=[], **auditHardware)
		logger.debug(u"Found hardware ids: {0}", hardwareIds)
		return hardwareIds

	def auditHardware_insertObject(self, auditHardware):
		ConfigDataBackend.auditHardware_insertObject(self, auditHardware)

		logger.info(u"Inserting auditHardware: %s" % auditHardware)
		hardwareHash = auditHardware.toHash()
		filter = {}
		for attribute, value in hardwareHash.items():
			if value is None:
				filter[attribute] = [None]
			elif isinstance(value, unicode):
				filter[attribute] = self._sql.escapeAsterisk(value)
			else:
				filter[attribute] = value
		res = self.auditHardware_getObjects(**filter)
		if res:
			return

		table = u'HARDWARE_DEVICE_' + hardwareHash['hardwareClass']
		del hardwareHash['hardwareClass']
		del hardwareHash['type']

		self._sql.insert(table, hardwareHash)

	def auditHardware_updateObject(self, auditHardware):
		ConfigDataBackend.auditHardware_updateObject(self, auditHardware)

		logger.info(u"Updating auditHardware: %s" % auditHardware)
		filter = {}
		for (attribute, value) in auditHardware.toHash().items():
			if value is None:
				filter[attribute] = [None]

		if not self.auditHardware_getObjects(**filter):
			raise Exception(u"AuditHardware '%s' not found" % auditHardware.getIdent())

	def auditHardware_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditHardware_getObjects(self, attributes=[], **filter)

		logger.info(u"Getting auditHardwares, filter: %s" % filter)
		return [AuditHardware.fromHash(h) for h in
				self.auditHardware_getHashes(attributes, **filter)]

	def auditHardware_getHashes(self, attributes=[], **filter):
		return self._auditHardware_search(returnHardwareIds=False, attributes=attributes, **filter)

	def _auditHardware_search(self, returnHardwareIds=False, attributes=[], **filter):
		hardwareClasses = set()
		hardwareClass = filter.get('hardwareClass')
		if hardwareClass not in ([], None):
			for hwc in forceUnicodeList(hardwareClass):
				regex = re.compile(u'^{0}$'.format(hwc.replace('*', '.*')))
				for key in self._auditHardwareConfig:
					if regex.search(key):
						hardwareClasses.add(key)

			if not hardwareClasses:
				return []

		if not hardwareClasses:
			hardwareClasses = set(self._auditHardwareConfig)

		for unwanted_key in ('hardwareClass', 'type'):
			try:
				del filter[unwanted_key]
			except KeyError:
				pass  # not there - everything okay.

		if 'hardwareClass' in attributes:
			attributes.remove('hardwareClass')

		for attribute in attributes:
			if attribute not in filter:
				filter[attribute] = None

		if returnHardwareIds and attributes and 'hardware_id' not in attributes:
			attributes.append('hardware_id')

		results = []
		for hardwareClass in hardwareClasses:
			classFilter = {}
			for (attribute, value) in filter.iteritems():
				valueInfo = self._auditHardwareConfig[hardwareClass].get(attribute)
				if not valueInfo:
					logger.debug(u"Skipping hardwareClass '%s', because of missing info for attribute '%s'" % (hardwareClass, attribute))
					break

				try:
					if valueInfo['Scope'] != 'g':
						continue
				except KeyError:
					pass

				if value is not None:
					value = forceList(value)
				classFilter[attribute] = value
			else:
				if not classFilter and filter:
					continue

				logger.debug(u"Getting auditHardwares, hardwareClass '%s', filter: %s" % (hardwareClass, classFilter))
				query = self._createQuery(u'HARDWARE_DEVICE_' + hardwareClass, attributes, classFilter)
				for res in self._sql.getSet(query):
					if returnHardwareIds:
						results.append(res['hardware_id'])
						continue

					try:
						del res['hardware_id']
					except KeyError:
						pass

					res['hardwareClass'] = hardwareClass
					for (attribute, valueInfo) in self._auditHardwareConfig[hardwareClass].iteritems():
						try:
							if valueInfo['Scope'] == 'i':
								continue
						except KeyError:
							pass

						if attribute not in res:
							res[attribute] = None

					results.append(res)

		return results

	def auditHardware_deleteObjects(self, auditHardwares):
		ConfigDataBackend.auditHardware_deleteObjects(self, auditHardwares)
		for auditHardware in forceObjectClassList(auditHardwares, AuditHardware):
			logger.info(u"Deleting auditHardware: %s" % auditHardware)

			where = self._uniqueAuditHardwareCondition(auditHardware)
			[self._sql.delete(
				u'HARDWARE_CONFIG_{0}'.format(auditHardware.getHardwareClass()),
				u'`hardware_id` = {0}'.format(hardware_id)
			) for hardware_id in self._getHardwareIds(auditHardware)]

			self._sql.delete(u'HARDWARE_DEVICE_{0}'.format(auditHardware.getHardwareClass()), where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def _extractAuditHardwareHash(self, auditHardwareOnHost):
		if hasattr(auditHardwareOnHost, 'toHash'):
			auditHardwareOnHost = auditHardwareOnHost.toHash()

		hardwareClass = auditHardwareOnHost['hardwareClass']

		auditHardware = {'type': 'AuditHardware'}
		auditHardwareOnHostNew = {}
		for (attribute, value) in auditHardwareOnHost.items():
			if attribute == 'type':
				continue
			elif attribute in ('hostId', 'state', 'firstseen', 'lastseen'):
				auditHardwareOnHostNew[attribute] = value
				continue
			elif attribute == 'hardwareClass':
				auditHardware[attribute] = value
				auditHardwareOnHostNew[attribute] = value
				continue

			valueInfo = self._auditHardwareConfig[hardwareClass].get(attribute)
			if valueInfo is None:
				raise BackendConfigurationError(u"Attribute '%s' not found in config of hardware class '%s'" % (attribute, hardwareClass))

			if valueInfo.get('Scope', '') == 'g':
				auditHardware[attribute] = value
				continue
			auditHardwareOnHostNew[attribute] = value

		return (auditHardware, auditHardwareOnHostNew)

	def _uniqueAuditHardwareOnHostCondition(self, auditHardwareOnHost):
		(auditHardware, auditHardwareOnHost) = self._extractAuditHardwareHash(auditHardwareOnHost)

		del auditHardwareOnHost['hardwareClass']

		filter = {}
		for (attribute, value) in auditHardwareOnHost.iteritems():
			if value is None:
				filter[attribute] = [None]
			elif isinstance(value, unicode):
				filter[attribute] = self._sql.escapeAsterisk(value)
			else:
				filter[attribute] = value

		where = self._filterToSql(filter)

		hwIdswhere = u' or '.join(
			[
				u'`hardware_id` = {0}'.format(hardwareId) for hardwareId in \
				self._getHardwareIds(auditHardware)
			]
		)

		if not hwIdswhere:
			raise BackendReferentialIntegrityError(u"Hardware device %s not found" % auditHardware)

		return ' and '.join(
			(
				where,
				hwIdswhere.join((u'(', u')'))
			)
		)

	def _auditHardwareOnHostObjectToDatabaseHash(self, auditHardwareOnHost):
		(auditHardware, auditHardwareOnHost) = self._extractAuditHardwareHash(auditHardwareOnHost)

		hardwareClass = auditHardwareOnHost['hardwareClass']

		data = {}
		for (attribute, value) in auditHardwareOnHost.items():
			if attribute in ('hardwareClass', 'type'):
				continue
			data[attribute] = value

		for (key, value) in auditHardware.items():
			if value is None:
				auditHardware[key] = [None]
		hardwareIds = self._getHardwareIds(auditHardware)
		if not hardwareIds:
			raise BackendReferentialIntegrityError(u"Hardware device %s not found" % auditHardware)
		data['hardware_id'] = hardwareIds[0]
		return data

	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		ConfigDataBackend.auditHardwareOnHost_insertObject(self, auditHardwareOnHost)

		table = u'HARDWARE_CONFIG_{0}'.format(auditHardwareOnHost.getHardwareClass())

		where = self._uniqueAuditHardwareOnHostCondition(auditHardwareOnHost)
		if not self._sql.getRow('select * from `%s` where %s' % (table, where)):
			data = self._auditHardwareOnHostObjectToDatabaseHash(auditHardwareOnHost)
			self._sql.insert(table, data)

	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		ConfigDataBackend.auditHardwareOnHost_updateObject(self, auditHardwareOnHost)

		logger.info(u"Updating auditHardwareOnHost: %s" % auditHardwareOnHost)
		data = auditHardwareOnHost.toHash()
		update = {}
		for (attribute, value) in data.items():
			if attribute in ('state', 'lastseen', 'firstseen'):
				if value is not None:
					update[attribute] = value
				del data[attribute]

		if update:
			where = self._uniqueAuditHardwareOnHostCondition(data)
			self._sql.update('HARDWARE_CONFIG_%s' % auditHardwareOnHost.hardwareClass, where, update)

	def auditHardwareOnHost_getHashes(self, attributes=[], **filter):
		hardwareClasses = set()
		hardwareClass = filter.get('hardwareClass')
		if hardwareClass not in ([], None):
			for hwc in forceUnicodeList(hardwareClass):
				regex = re.compile(u'^{0}$'.format(hwc.replace('*', '.*')))
				[hardwareClasses.add(key) for key in self._auditHardwareConfig if regex.search(key)]

			if not hardwareClasses:
				return []

		if not hardwareClasses:
			hardwareClasses = set(self._auditHardwareConfig)

		for unwanted_key in ('hardwareClass', 'type'):
			try:
				del filter[unwanted_key]
			except KeyError:
				pass  # not there - everything okay.

		for attribute in attributes:
			if attribute not in filter:
				filter[attribute] = None

		hashes = []
		for hardwareClass in hardwareClasses:
			auditHardwareFilter = {}
			classFilter = {}
			skipHardwareClass = False
			for attribute, value in filter.iteritems():
				valueInfo = None
				if attribute not in ('hostId', 'state', 'firstseen', 'lastseen'):
					valueInfo = self._auditHardwareConfig[hardwareClass].get(attribute)
					if not valueInfo:
						logger.debug(u"Skipping hardwareClass '%s', because of missing info for attribute '%s'" % (hardwareClass, attribute))
						skipHardwareClass = True
						break

					scope = valueInfo.get('Scope', '')
					if scope == 'g':
						auditHardwareFilter[attribute] = value
						continue
					if scope != 'i':
						continue

				if value is not None:
					value = forceList(value)

				classFilter[attribute] = value

			if skipHardwareClass:
				continue

			hardwareIds = []
			if auditHardwareFilter:
				auditHardwareFilter['hardwareClass'] = hardwareClass
				hardwareIds = self._getHardwareIds(auditHardwareFilter)
				logger.debug2(u"Filtered matching hardware ids: {0}", hardwareIds)
				if not hardwareIds:
					continue
			classFilter['hardware_id'] = hardwareIds

			if attributes and 'hardware_id' not in attributes:
				attributes.append('hardware_id')

			logger.debug(u"Getting auditHardwareOnHosts, hardwareClass '%s', hardwareIds: %s, filter: %s" % (hardwareClass, hardwareIds, classFilter))
			for res in self._sql.getSet(self._createQuery(u'HARDWARE_CONFIG_{0}'.format(hardwareClass), attributes, classFilter)):
				data = self._sql.getSet(u'SELECT * from `HARDWARE_DEVICE_%s` where `hardware_id` = %s' \
								% (hardwareClass, res['hardware_id']))

				if not data:
					logger.error(u"Hardware device of class '%s' with hardware_id '%s' not found" % (hardwareClass, res['hardware_id']))
					continue

				data = data[0]
				data.update(res)
				data['hardwareClass'] = hardwareClass
				del data['hardware_id']
				try:
					del data['config_id']
				except KeyError:
					pass  # not there - everything okay

				for attribute in self._auditHardwareConfig[hardwareClass]:
					if attribute not in data:
						data[attribute] = None
				hashes.append(data)

		return hashes

	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditHardwareOnHost_getObjects(self, attributes=[], **filter)

		logger.info(u"Getting auditHardwareOnHosts, filter: %s" % filter)
		return [AuditHardwareOnHost.fromHash(h) for h in self.auditHardwareOnHost_getHashes(attributes, **filter)]

	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):
		ConfigDataBackend.auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts)
		for auditHardwareOnHost in forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost):
			logger.info(u"Deleting auditHardwareOnHost: %s" % auditHardwareOnHost)
			where = self._uniqueAuditHardwareOnHostCondition(auditHardwareOnHost)
			self._sql.delete(u'HARDWARE_CONFIG_{0}'.format(auditHardwareOnHost.getHardwareClass()), where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   BootConfigurations
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def bootConfiguration_insertObject(self, bootConfiguration):
		ConfigDataBackend.bootConfiguration_insertObject(self, bootConfiguration)
		data = self._objectToDatabaseHash(bootConfiguration)

		where = self._uniqueCondition(bootConfiguration)
		if self._sql.getRow('select * from `BOOT_CONFIGURATION` where %s' % where):
			self._sql.update('BOOT_CONFIGURATION', where, data, updateWhereNone=True)
		else:
			self._sql.insert('BOOT_CONFIGURATION', data)

	def bootConfiguration_updateObject(self, bootConfiguration):
		ConfigDataBackend.bootConfiguration_updateObject(self, bootConfiguration)
		data = self._objectToDatabaseHash(bootConfiguration)
		where = self._uniqueCondition(bootConfiguration)
		self._sql.update('BOOT_CONFIGURATION', where, data)

	def bootConfiguration_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.bootConfiguration_getObjects(self, attributes=[], **filter)
		logger.info(u"Getting bootConfigurations, filter: %s" % filter)
		bootConfigurations = []
		(attributes, filter) = self._adjustAttributes(BootConfiguration, attributes, filter)
		for res in self._sql.getSet(self._createQuery('BOOT_CONFIGURATION', attributes, filter)):
			self._adjustResult(BootConfiguration, res)
			bootConfigurations.append(BootConfiguration.fromHash(res))
		return bootConfigurations

	def bootConfiguration_deleteObjects(self, bootConfigurations):
		ConfigDataBackend.bootConfiguration_deleteObjects(self, bootConfigurations)
		for bootConfiguration in forceObjectClassList(bootConfigurations, BootConfiguration):
			logger.info(u"Deleting bootConfiguration %s" % bootConfiguration)
			where = self._uniqueCondition(bootConfiguration)
			self._sql.delete('BOOT_CONFIGURATION', where)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Extension for direct connect to db
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def getData(self, query):
		self._requiresEnabledSQLBackendModule()
		onlyAllowSelect(query)

		with timeQuery(query):
			return self._sql.getSet(query)

	def getRawData(self, query):
		self._requiresEnabledSQLBackendModule()
		onlyAllowSelect(query)

		with timeQuery(query):
			return self._sql.getRows(query)