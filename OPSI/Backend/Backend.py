#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Backend   =
   = = = = = = = = = = = = = = = = = = =
   
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

from OPSI.Logger import *
from OPSI.Backend.Object import *

logger = Logger()

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                                                                                    =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                        CLASS BACKEND                                               =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class Backend:
	def __init__(self, username = '', password = '', address = '', **kwargs):
		
		self._username = forceUnicode(username)
		self._password = forceUnicode(password)
		self._address  = forceUnicode(address)
		
		#for (option, value) in kwargs.items():
		#	if (option.lower() == 'defaultdomain'):
		#		self._defaultDomain = forceDomain(value)
		
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                   CLASS CONFIGDATABACKEND                                          =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ConfigDataBackend(Backend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		Backend.__init__(self, username, password, address, **kwargs)
	
	def _testFilterAndAttributes(self, Class, attributes, **filter):
		possibleAttributes = getPossibleClassAttributes(Class)
		for attribute in attributes:
			if not attribute in possibleAttributes:
				raise BackendBadValueError("Unkown attribute '%s'" % attribute)
		for attribute in filter.keys():
			if not attribute in possibleAttributes:
				raise BackendBadValueError("Unkown attribute '%s'" % attribute)
	
	def base_create(self):
		pass
	
	def base_delete(self):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_createObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			logger.info(u"Creating host '%s'" % host)
			if self.host_getObjects(
					attributes = ['id'],
					id = host.id):
				logger.info(u"%s already exists, updating" % host)
				self.host_updateObject(host)
			else:
				self.host_insertObject(host)
	
	def host_insertObject(self, host):
		host = forceObjectClass(host, Host)
		host.setDefaults()
	
	def host_updateObject(self, host):
		host = forceObjectClass(host, Host)
		
	def host_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Host, attributes, **filter)
		
	def host_deleteObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			# Remove from groups
			self.objectToGroup_delete(
				groupIds = [],
				objectIds = [ host.id ])
			if isinstance(host, OpsiClient):
				# Remove product states
				self.productOnClient_delete(
					productIds = [],
					clientIds = [ host.id ])
			elif isinstance(host, OpsiDepotserver):
				# This is also true for OpsiConfigservers
				# Remove products
				self.productOnDepot_delete(
					productIds = [],
					productVersions = [],
					packageVersions = [],
					depotIds = [ host.id ])
			# Remove product property states
			self.productPropertyState_delete(
				productIds = [],
				names = [],
				objectIds = [ host.id ])
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_createObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Creating config %s" % config)
			if self.config_getObjects(
					attributes = ['name'],
					name = config.name):
				logger.info(u"Config '%s' already exists, updating" % config)
				self.config_updateObject(config)
			else:
				self.config_insertObject(config)
	
	def config_insertObject(self, config):
		config = forceObjectClass(config, Config)
		config.setDefaults()
		
	def config_updateObject(self, config):
		pass
	
	def config_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Config, attributes, **filter)
	
	def config_deleteObjects(self, configs):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_createObjects(self, configStates):
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Creating configState %s" % configState)
			if self.configState_getObjects(
					attributes = ['name'],
					name = configState.name,
					objectId = configState.objectId):
				logger.info(u"ConfigState '%s' already exists, updating" % configState)
				self.configState_updateObject(configState)
			else:
				self.configState_insertObject(configState)
	
	def configState_insertObject(self, configState):
		configState = forceObjectClass(configState, ConfigState)
		configState.setDefaults()
		
	def configState_updateObject(self, configState):
		pass
	
	def configState_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ConfigState, attributes, **filter)
	
	def configState_deleteObjects(self, configStates):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_createObjects(self, products):
		for product in forceObjectClassList(products, Product):
			logger.info(u"Creating product %s" % product)
			if self.product_getObjects(
					attributes = ['productId'],
					id = product.id, productVersion = product.productVersion,
					packageVersion = product.packageVersion):
				logger.info(u"Product '%s' already exists, updating" % product)
				self.product_updateObject(product)
			else:
				self.product_insertObject(product)
	
	def product_insertObject(self, product):
		product = forceObjectClass(product, Product)
		product.setDefaults()
	
	def product_updateObject(self, product):
		pass
	
	def product_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Product, attributes, **filter)
	
	def product_deleteObjects(self, products):
		for product in forceObjectClassList(products, Product):
			self.productProperty_delete(
				productIds = [ product.id ],
				productVersions = [ product.productVersion ],
				packageVersions = [ product.packageVersion ])
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_createObjects(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating product property %s" % productProperty)
			if self.productProperty_getObjects(
					attributes = ['productId'],
					productId = productProperty.productId,
					productVersion = productProperty.productVersion,
					packageVersion = productProperty.packageVersion,
					name = productProperty.name):
				logger.info(u"Product property '%s' already exists, updating" % productProperty)
				self.productProperty_updateObject(productProperty)
			else:
				self.productProperty_insertObject(productProperty)
	
	def productProperty_insertObject(self, productProperty):
		productProperty = forceObjectClass(productProperty, ProductProperty)
		productProperty.setDefaults()
	
	def productProperty_updateObject(self, productProperty):
		pass
	
	def productProperty_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductProperty, attributes, **filter)
	
	def productProperty_deleteObjects(self, productProperties):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_createObjects(self, productOnDepots):
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		for productOnDepot in productOnDepots:
			logger.info(u"Creating productOnDepot '%s'" % productOnDepot)
			if self.productOnDepot_getObjects(
					productId = productOnDepot.productId,
					depotId = productOnDepot.depotId):
				logger.info(u"ProductOnDepot '%s' already exists, updating" % productOnDepot)
				self.productOnDepot_updateObject(productOnDepot)
			else:
				self.productOnDepot_insertObject(productOnDepot)
	
	def productOnDepot_insertObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		productOnDepot.setDefaults()
	
	def productOnDepot_updateObject(self, productOnDepot):
		pass
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnDepot, attributes, **filter)
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_createObjects(self, productOnClients):
		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		for productOnClient in productOnClients:
			logger.info(u"Creating productOnClient '%s'" % productOnClient)
			if self.productOnClient_getObjects(
					productId = productOnClient.productId,
					clientId = productOnClient.clientId):
				logger.info(u"ProductOnClient '%s' already exists, updating" % productOnClient)
				self.productOnClient_updateObject(productOnClient)
			else:
				self.productOnClient_insertObject(productOnClient)
	
	def productOnClient_insertObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		productOnClient.setDefaults()
		
	def productOnClient_updateObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnClient, attributes, **filter)
	
	def productOnClient_deleteObjects(self, productOnClients):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_createObjects(self, productPropertyStates):
		productPropertyStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Creating productPropertyState '%s'" % productPropertyState)
			if self.productPropertyState_getObjects(
						productId = productPropertyState.productId,
						objectId = productPropertyState.objectId,
						name = productPropertyState.name):
				logger.info(u"ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self.productPropertyState_updateObject(productPropertyState)
			else:
				self.productPropertyState_insertObject(productPropertyState)
	
	def productPropertyState_insertObject(self, productPropertyState):
		productPropertyState = forceObjectClass(productPropertyState, ProductPropertyState)
		productPropertyState.setDefaults()
	
	def productPropertyState_updateObject(self, productPropertyState):
		pass
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductPropertyState, attributes, **filter)
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_createObjects(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Creating group '%s'" % group)
			if self.group_getObjects(id = group.id):
				logger.info(u"Group '%s' already exists, updating" % group)
				self.group_updateObject(group)
			else:
				self.group_insertObject(group)
	
	def group_insertObject(self, group):
		group = forceObjectClass(group, Group)
		group.setDefaults()
	
	def group_updateObject(self, group):
		pass
	
	def group_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Group, attributes, **filter)
	
	def group_deleteObjects(self, groups):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_createObjects(self, objectToGroups):
		objectToGroups = forceObjectClassList(objectToGroups, ObjectToGroup)
		for objectToGroup in objectToGroups:
			logger.info(u"Creating %s" % objectToGroup)
			if self.objectToGroup_getObjects(
					groupId = objectToGroup.groupId,
					objectId = objectToGroup.objectId):
				logger.info(u"%s already exists, updating" % objectToGroup)
				self.objectToGroup_updateObject(objectToGroup)
			else:
				self.objectToGroup_insertObject(objectToGroup)
	
	def objectToGroup_insertObject(self, objectToGroup):
		objectToGroup = forceObjectClass(objectToGroup, ObjectToGroup)
		objectToGroup.setDefaults()
	
	def objectToGroup_updateObject(self, objectToGroup):
		pass
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ObjectToGroup, attributes, **filter)
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		pass

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                               CLASS EXTENDEDCONFIGDATABACKEND                                      =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ExtendedConfigDataBackend(ConfigDataBackend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		ConfigDataBackend.__init__(self, username, password, address, **kwargs)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_createOpsiClient(self, id, opsiHostKey=None, description=None, notes=None, hardwareAddress=None, ipAddress=None, created=None, lastSeen=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiClient.fromHash(hash))
	
	def host_createOpsiDepotserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, network=None, maxBandwidth=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiDepotserver.fromHash(hash))
	
	def host_createOpsiConfigserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, network=None, maxBandwidth=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiConfigserver.fromHash(hash))
	
	def host_delete(self, ids):
		return self.host_deleteObjects(
				self.host_getObjects(
					id = forceHostIdList(ids)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_create(self, name, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(Config.fromHash(hash))
	
	def config_createUnicode(self, name, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(UnicodeConfig.fromHash(hash))
	
	def config_createBool(self, name, description=None, defaultValues=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(BoolConfig.fromHash(hash))
	
	def config_delete(self, names):
		return self.config_deleteObjects(
				config_getObjects(
					name = forceUnicodeLowerList(names)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_create(self, name, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.configState_createObjects(ConfigState.fromHash(hash))
	
	def configState_delete(self, names, objectIds):
		return self.configState_deleteObjects(
				configState_getObjects(
					name = forceUnicodeLowerList(names),
					objectId = forceObjectIdsList(objectIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_createLocalboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, productClassNames=None, windowsSoftwareIds=None):
		hash = locals()
		del hash['self']
		return self.product_createObjects(LocalbootProduct.fromHash(hash))
	
	def product_createNetboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, productClassNames=None, windowsSoftwareIds=None,
					pxeConfigTemplate=None):
		hash = locals()
		del hash['self']
		return self.product_createObjects(NetbootProduct.fromHash(hash))
	
	def product_delete(self, productIds):
		return self.product_deleteObjects(
				product_getObjects(
					productId = forceProductIdList(productIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_create(self, productId, productVersion, packageVersion, name, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(ProductProperty.fromHash(hash))
	
	def productProperty_createUnicode(self, productId, productVersion, packageVersion, name, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(UnicodeProductProperty.fromHash(hash))
	
	def productProperty_createBool(self, productId, productVersion, packageVersion, name, description=None, defaultValues=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(BoolProductProperty.fromHash(hash))
	
	def productProperty_delete(self, productIds, productVersions, packageVersions, names):
		return self.productOnDepot_deleteObjects(
				self.productOnDepot_getObjects(
					productId = forceProductIdList(productIds),
					productVersion = forceProductVersionList(productVersions),
					packageVersion = forcePackageVersionList(packageVersions),
					name = forceUnicodeLowerList(names)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_create(self, productId, productVersion, packageVersion, depotId, locked=None):
		hash = locals()
		del hash['self']
		return self.productOnDepot_createObjects(ProductOnDepot.fromHash(hash))
	
	def productOnDepot_delete(self, productIds, productVersions, packageVersions, depotIds):
		return self.productOnDepot_deleteObjects(
				self.productOnDepot_getObjects(
					productId = forceProductIdList(productIds),
					productVersion = forceProductVersionList(productVersions),
					packageVersion = forcePackageVersionList(packageVersions),
					depotId = forceHostIdList(depotIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_create(self, productId, clientId, installationStatus=None, actionRequest=None, actionProgress=None, productVersion=None, packageVersion=None, lastStateChange=None):
		hash = locals()
		del hash['self']
		return self.productOnClient_createObjects(ProductOnClient.fromHash(hash))
	
	def productOnClient_delete(self, productIds, clientIds):
		return self.productOnClient_deleteObjects(
				self.productOnClient_getObjects(
					productId = forceProductIdList(productIds),
					clientId = forceHostIdList(clientIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_create(self, productId, name, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))
	
	def productPropertyState_delete(self, productIds, names, objectIds):
		return self.productPropertyState_deleteObjects(
				self.productPropertyState_getObjects(
					productId = forceProductIdList(productIds),
					name = forceUnicodeLowerList(names),
					objectId = forceObjectIdList(objectIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_createHost(self, id, description=None, notes=None, parentGroupId=None):
		hash = locals()
		del hash['self']
		return self.group_createObjects(HostGroup.fromHash(hash))
	
	def group_delete(self, ids):
		return self.group_deleteObjects(
				self.group_getObjects(
					id = forceGroupIdList(ids)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_create(self, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ObjectToGroup.fromHash(hash))
	
	def objectToGroup_delete(self, groupIds, objectIds):
		return self.objectToGroup_deleteObjects(
				self.objectToGroup_getObjects(
					groupId = forceGroupIdList(groupIds),
					objectId = forceObjectIdList(objectIds)))
		







