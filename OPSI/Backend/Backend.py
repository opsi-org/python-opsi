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
		
		self._defaultDomain = 'opsi.org'
		self._username = forceUnicode(username)
		self._password = forceUnicode(password)
		self._address = forceUnicode(address)
		
		for (option, value) in kwargs.items():
			if (option.lower() == 'defaultdomain'):
				self._defaultDomain = forceDomain(value)
		
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                      CLASS DATABACKEND                                             =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class DataBackend(Backend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		Backend.__init__(self, username, password, address, **kwargs)
	
	def base_create(self):
		raise NotImplementedError(u"Not implemented")
	
	def base_delete(self):
		raise NotImplementedError(u"Not implemented")
	
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
	
	def host_createOpsiClient(self, id, opsiHostKey='', description='', notes='', hardwareAddress='', ipAddress='', created='', lastSeen=''):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiClient.fromHash(hash))
	
	def host_createOpsiDepotserver(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
					description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiDepotserver.fromHash(hash))
	
	def host_createOpsiConfigserver(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
					description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiConfigserver.fromHash(hash))
	
	def host_insertObject(self, host):
		raise NotImplementedError(u"Not implemented")
	
	def host_updateObject(self, host):
		raise NotImplementedError(u"Not implemented")
	
	def host_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def host_deleteObjects(self, hosts):
		raise NotImplementedError(u"Not implemented")
	
	def host_delete(ids):
		objects = []
		for id in forceHostIdList(ids):
			objects.append(Host(id = id))
		return self.host_deleteObjects(objects)
	
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
	
	def config_create(self, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		hash = locals()
		del hash['self']
		return self.config_createObjects(Config.fromHash(hash))
	
	def config_createUnicode(self, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		hash = locals()
		del hash['self']
		return self.config_createObjects(UnicodeConfig.fromHash(hash))
	
	def config_createBool(self, name, description='', defaultValues = [ True ]):
		hash = locals()
		del hash['self']
		return self.config_createObjects(BoolConfig.fromHash(hash))
	
	def config_insertObject(self, config):
		raise NotImplementedError(u"Not implemented")
	
	def config_updateObject(self, config):
		raise NotImplementedError(u"Not implemented")
	
	def config_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def config_deleteObjects(self, configs):
		raise NotImplementedError(u"Not implemented")
	
	def config_delete(names):
		objects = []
		for name in forceUnicodeLowerList(names):
			objects.append(Config(name = name))
		return self.config_deleteObjects(objects)
	
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
	
	def configState_create(self, name, objectId, values=[]):
		hash = locals()
		del hash['self']
		return self.configState_createObjects(ConfigState.fromHash(hash))
	
	def configState_insertObject(self, configState):
		raise NotImplementedError(u"Not implemented")
	
	def configState_updateObject(self, configState):
		raise NotImplementedError(u"Not implemented")
	
	def configState_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def configState_deleteObjects(self, configStates):
		raise NotImplementedError(u"Not implemented")
	
	def configState_delete(names, objectIds):
		objects = []
		for name in forceUnicodeLowerList(names):
			for objectId in forceObjectIdsList(objectIds):
				objects.append(ConfigState(name = name, objectId = objectId))
		return self.configState_deleteObjects(objects)
	
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
	
	def product_createLocalboot(self, id, productVersion, packageVersion, name="", licenseRequired=False,
					setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
					priority=0, description="", advice="", productClassNames=[], windowsSoftwareIds=[]):
		hash = locals()
		del hash['self']
		return self.product_createObjects(LocalbootProduct.fromHash(hash))
	
	def product_createNetboot(self, id, productVersion, packageVersion, name="", licenseRequired=False,
					setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
					priority=0, description="", advice="", productClassNames=[], windowsSoftwareIds=[],
					pxeConfigTemplate=''):
		hash = locals()
		del hash['self']
		return self.product_createObjects(NetbootProduct.fromHash(hash))
	
	def product_insertObject(self, product):
		raise NotImplementedError(u"Not implemented")
	
	def product_updateObject(self, product):
		raise NotImplementedError(u"Not implemented")
	
	def product_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def product_deleteObjects(self, products):
		raise NotImplementedError(u"Not implemented")
	
	def product_delete(productIds):
		objects = []
		for productId in forceProductIdList(productIds):
			objects.append(Product(productId = productId))
		return self.product_deleteObjects(objects)
	
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
	
	def productProperty_create(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(ProductProperty.fromHash(hash))
	
	def productProperty_createUnicode(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(UnicodeProductProperty.fromHash(hash))
	
	def productProperty_createBool(self, productId, productVersion, packageVersion, name, description='', defaultValues = [ True ]):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(BoolProductProperty.fromHash(hash))
	
	def productProperty_insertObject(self, productProperty):
		raise NotImplementedError(u"Not implemented")
	
	def productProperty_updateObject(self, productProperty):
		raise NotImplementedError(u"Not implemented")
	
	def productProperty_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def productProperty_deleteObjects(self, productProperties):
		raise NotImplementedError(u"Not implemented")
	
	def productProperty_delete(self, productIds, productVersions, packageVersions, names):
		objects = []
		for productId in forceProductIdList(productIds):
			for productVersion in forceProductVersionList(productVersions):
				for packageVersion in forcePackageVersionList(packageVersions):
					for name in forceUnicodeLowerList(names):
						objects.append(ProductProperty(productId = productId, productVersion = productVersion, packageVersion = packageVersion, name = name))
		return self.productProperty_deleteObjects(objects)
	
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
	
	def productOnDepot_create(self, productId, productVersion, packageVersion, depotId, locked=False):
		hash = locals()
		del hash['self']
		return self.productOnDepot_createObjects(ProductOnDepot.fromHash(hash))
	
	def productOnDepot_insertObject(self, productOnDepot):
		raise NotImplementedError(u"Not implemented")
	
	def productOnDepot_updateObject(self, productOnDepot):
		raise NotImplementedError(u"Not implemented")
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		raise NotImplementedError(u"Not implemented")
	
	def productOnDepot_delete(self, productIds, productVersions, packageVersions, depotId):
		objects = []
		for productId in forceProductIdList(productIds):
			for productVersion in forceProductVersionList(productVersions):
				for packageVersion in forcePackageVersionList(packageVersions):
					for depotId in forceHostIdList(depotIds):
						objects.append(ProductProperty(productId = productId, productVersion = productVersion, packageVersion = packageVersion, depotId = depotId))
		return self.productOnDepot_deleteObjects(objects)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductStates                                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productState_createObjects(self, productStates):
		productStates = forceObjectClassList(productStates, ProductState)
		for productState in productStates:
			logger.info(u"Creating productState '%s'" % productState)
			if self.productState_getObjects(
					productId = productState.productId,
					hostId = productState.hostId):
				logger.info(u"ProductState '%s' already exists, updating" % productState)
				self.productState_updateObject(productState)
			else:
				self.productState_insertObject(productState)
	
	def productState_create(self, productId, hostId, installationStatus='not_installed', actionRequest='none', actionProgress='', productVersion='', packageVersion='', lastStateChange=''):
		hash = locals()
		del hash['self']
		return self.productState_createObjects(ProductState.fromHash(hash))
	
	def productState_insertObject(self, productState):
		raise NotImplementedError(u"Not implemented")
	
	def productState_updateObject(self, productState):
		raise NotImplementedError(u"Not implemented")
	
	def productState_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def productState_deleteObjects(self, productStates):
		raise NotImplementedError(u"Not implemented")
	
	def productState_delete(self, productIds, hostIds):
		objects = []
		for productId in forceProductIdList(productIds):
			for hostId in forceHostIdList(hostIds):
				objects.append(ProductState(productId = productId, hostId = hostId))
		return self.productState_deleteObjects(objects)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_createObjects(self, productPropertyStates):
		productStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Creating productPropertyState '%s'" % productPropertyState)
			if self.productPropertyState_getObjects(
						productId = productPropertyState.productId,
						hostId = productPropertyState.hostId,
						name = productPropertyState.name):
				logger.info(u"ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self.productPropertyState_updateObject(productPropertyState)
			else:
				self.productPropertyState_insertObject(productPropertyState)
	
	def productPropertyState_create(self, productId, name, hostId, values=[]):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))
	
	def productPropertyState_insertObject(self, productPropertyState):
		raise NotImplementedError(u"Not implemented")
	
	def productPropertyState_updateObject(self, productPropertyState):
		raise NotImplementedError(u"Not implemented")
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		raise NotImplementedError(u"Not implemented")
	
	def productPropertyState_delete(self, productIds, names, hostIds):
		objects = []
		for productId in forceProductIdList(productIds):
			for name in forceUnicodeLowerList(names):
				for hostId in forceHostIdList(hostIds):
					objects.append(ProductPropertyState(productId = productId, name = name, hostId = hostId))
		return self.productState_deleteObjects(objects)
	
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
	
	def group_createHost(self, id, description='', notes='', parentGroupId=''):
		hash = locals()
		del hash['self']
		return self.group_createObjects(HostGroup.fromHash(hash))
	
	def group_insertObject(self, group):
		raise NotImplementedError(u"Not implemented")
	
	def group_updateObject(self, group):
		raise NotImplementedError(u"Not implemented")
	
	def group_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def group_deleteObjects(self, groups):
		raise NotImplementedError(u"Not implemented")
	
	def group_delete(self, ids):
		objects = []
		for id in forceGroupIdList(ids):
			objects.append(Group(id = id))
		return self.group_deleteObjects(objects)
	
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
	
	def objectToGroup_create(self, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ObjectToGroup.fromHash(hash))
	
	def objectToGroup_insertObject(self, objectToGroup):
		raise NotImplementedError(u"Not implemented")
	
	def objectToGroup_updateObject(self, objectToGroup):
		raise NotImplementedError(u"Not implemented")
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		raise NotImplementedError(u"Not implemented")
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		raise NotImplementedError(u"Not implemented")
	
	def objectToGroup_delete(self, groupIds, objectIds):
		objects = []
		for groupId in forceGroupIdList(groupIds):
			for objectId in forceObjectIdList(objectIds):
				objects.append(ObjectToGroup(groupId = groupId, objectId = objectId))
		return self.objectToGroup_deleteObjects(objects)









