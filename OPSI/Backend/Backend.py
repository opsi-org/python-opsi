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

# Imports
from ldaptor.protocols import pureldap
from ldaptor import ldapfilter

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
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
			self.objectToGroup_deleteObjects(
				self.objectToGroup_getObjects(
					groupId = [],
					objectId = host.id ))
			if isinstance(host, OpsiClient):
				# Remove product states
				self.productOnClient_deleteObjects(
					self.productOnClient_getObjects(
						productId = [],
						clientId = host.id ))
			elif isinstance(host, OpsiDepotserver):
				# This is also true for OpsiConfigservers
				# Remove products
				self.productOnDepot_deleteObjects(
					self.productOnDepot_getObjects(
						productId = [],
						productVersion = [],
						packageVersion = [],
						depotId = host.id ))
			# Remove product property states
			self.productPropertyState_deleteObjects(
				self.productPropertyState_getObjects(
					productId  = [],
					propertyId = [],
					objectId   = host.id ))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		config = forceObjectClass(config, Config)
		config.setDefaults()
		
	def config_updateObject(self, config):
		pass
	
	def config_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Config, attributes, **filter)
	
	def config_deleteObjects(self, configs):
		ids = []
		for config in forceObjectClassList(configs, Config):
			ids.append(config.id)
		if ids:
			self.configState_deleteObjects(
				self.configState_getObjects(
					configId = ids,
					objectId = []))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		configState = forceObjectClass(configState, ConfigState)
		configState.setDefaults()
		
		configIds = []
		for config in self.config_getObjects(attributes = ['id']):
			configIds.append(config.id)
		if configState.configId not in configIds:
			raise BackendReferentialIntegrityError(u"Config with id '%s' not found" % configState.configId)
		
	def configState_updateObject(self, configState):
		pass
	
	def configState_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ConfigState, attributes, **filter)
		
	def configState_deleteObjects(self, configStates):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		product = forceObjectClass(product, Product)
		product.setDefaults()
	
	def product_updateObject(self, product):
		pass
	
	def product_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Product, attributes, **filter)
	
	def product_deleteObjects(self, products):
		for product in forceObjectClassList(products, Product):
			self.productProperty_deleteObjects(
				self.productProperty_getObjects(
					productId = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion ))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
	def productOnDepot_insertObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		productOnDepot.setDefaults()
		products = self.product_getObjects(
			id = productOnDepot.productId,
			productVersion = productOnDepot.productVersion,
			packageVersion = productOnDepot.packageVersion)
		if not products:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion))
		
	def productOnDepot_updateObject(self, productOnDepot):
		pass
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnDepot, attributes, **filter)
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		productOnClient.setDefaults()
		products = self.product_getObjects(
			id = productOnClient.productId,
			productVersion = productOnClient.productVersion,
			packageVersion = productOnClient.packageVersion)
		if not products:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion))
		if   (productOnClient.actionRequest == 'setup') and not products[0].setupScript:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' does not define a script for action '%s'" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion, productOnClient.actionRequest))
		elif (productOnClient.actionRequest == 'uninstall') and not products[0].setupScript:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' does not define a script for action '%s'" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion, productOnClient.actionRequest))
		elif (productOnClient.actionRequest == 'update') and not products[0].updateScript:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' does not define a script for action '%s'" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion, productOnClient.actionRequest))
		elif (productOnClient.actionRequest == 'once') and not products[0].onceScript:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' does not define a script for action '%s'" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion, productOnClient.actionRequest))
		elif (productOnClient.actionRequest == 'always') and not products[0].alwaysScript:
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' does not define a script for action '%s'" \
				% (productOnClient.productId, productOnClient.productVersion, productOnClient.packageVersion, productOnClient.actionRequest))
		
	def productOnClient_updateObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnClient, attributes, **filter)
	
	def productOnClient_deleteObjects(self, productOnClients):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
	def group_insertObject(self, group):
		group = forceObjectClass(group, Group)
		group.setDefaults()
	
	def group_updateObject(self, group):
		pass
	
	def group_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Group, attributes, **filter)
	
	def group_deleteObjects(self, groups):
		for group in forceObjectClassList(groups, Group):
			self.objectToGroup_deleteObjects(
				self.objectToGroup_getObjects(
					groupId = group.id ))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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
	
	def searchIds(self, filter):
		try:
			parsedFilter = ldapfilter.parseFilter(filter)
		except Exception, e:
			raise BackendBadValueError(u"Failed to parse filter '%s'" % filter)
		logger.debug(u"Parsed search filter: %s" % repr(parsedFilter))
		
		
		def handleFilter(f):
			operator = None
			objectClass = None
			objectFilter = {}
			if   isinstance(f, pureldap.LDAPFilter_equalityMatch):
				logger.debug(u"Handle equality attribute '%s', value '%s'" % (f.attributeDesc.value, f.assertionValue.value))
				if (f.attributeDesc.value.lower() == 'objectclass'):
					objectClass = f.assertionValue.value
					return (None, objectClass, {})
				else:
					return (None, None, { f.attributeDesc.value: f.assertionValue.value })
				
			elif isinstance(f, pureldap.LDAPFilter_substrings):
				logger.debug(u"Handle substrings type %s: %s" % (f.type, repr(f.substrings)))
				if (f.type.lower() == 'objectclass'):
					raise BackendBadValueError(u"Substring search not allowed for objectClass")
				if   isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_initial):
					# string*
					return (None, None, { f.type: '%s*' % f.substrings[0].value })
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_final):
					# *string
					return (None, None, { f.type: '*%s' % f.substrings[0].value })
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_any):
					# *string*
					return (None, None, { f.type: '*%s*' % f.substrings[0].value })
				else:
					raise BackendBadValueError(u"Unsupported substring class: %s" % repr(f))
			elif isinstance(f, pureldap.LDAPFilter_present):
				return (None, None, { f.value: '*' })
			
			elif isinstance(f, pureldap.LDAPFilter_and):
				operator = 'AND'
			elif isinstance(f, pureldap.LDAPFilter_or):
				operator = 'OR'
			elif isinstance(f, pureldap.LDAPFilter_not):
				raise BackendBadValueError(u"Operator '!' not allowed")
			else:
				raise BackendBadValueError(u"Unsupported search filter: %s" % repr(f))
			
			for fChild in f.data:
				(result, oc, of) = handleFilter(fChild)
				if oc:
					objectClass = oc
				if of:
					objectFilter.update(of)
			
			logger.error("operator: %s, objectClass: %s, objectFilter: %s" % (operator, objectClass, objectFilter))
			if objectFilter or objectClass:
				result = []
				if objectFilter and not objectClass:
					raise BackendBadValueError(u"Bad search filter '%s': objectClass not defined" % repr(f))
				type = None
				if objectClass in ('Host', 'OpsiClient', 'OpsiDepotserver', 'OpsiConfigserver'):
					#if not objectFilter.has_key('type'):
					#	objectFilter['type'] = objectClass
					result = self.host_getIds(**objectFilter)
					logger.error(result)
				else:
					raise BackendBadValueError(u"ObjectClass '%s' not supported" % objectClass)
				objectClass = None
				objectFilter = {}
				return (result, None, None)
			
		handleFilter(parsedFilter)
		
		raise Exception("STOP")
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_getIdents(self, returnType='unicode', **filter):
		result = []
		for host in self.host_getObjects(attributes = ['id'], **filter):
			result.append(host.getIdent(returnType))
		return result
	
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
	
	def host_updateObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			self.host_updateObject(host)
	
	def host_createOpsiClient(self, id, opsiHostKey=None, description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, created=None, lastSeen=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiClient.fromHash(hash))
	
	def host_createOpsiDepotserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, network=None, maxBandwidth=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiDepotserver.fromHash(hash))
	
	def host_createOpsiConfigserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, network=None, maxBandwidth=None):
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
	def config_getIdents(self, returnType='unicode', **filter):
		result = []
		for config in self.config_getObjects(attributes = ['id'], **filter):
			result.append(config.getIdent(returnType))
		return result
	
	def config_createObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Creating config %s" % config)
			if self.config_getObjects(
					attributes = ['id'],
					id         = config.id):
				logger.info(u"Config '%s' already exists, updating" % config)
				self.config_updateObject(config)
			else:
				self.config_insertObject(config)
	
	def config_updateObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			self.config_updateObject(config)
	
	def config_create(self, id, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(Config.fromHash(hash))
	
	def config_createUnicode(self, id, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(UnicodeConfig.fromHash(hash))
	
	def config_createBool(self, id, description=None, defaultValues=None):
		hash = locals()
		del hash['self']
		return self.config_createObjects(BoolConfig.fromHash(hash))
	
	def config_delete(self, ids):
		return self.config_deleteObjects(
				config_getObjects(
					id = forceUnicodeLowerList(ids)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_getIdents(self, returnType='unicode', **filter):
		result = []
		for configState in self.configState_getObjects(attributes = ['configId', 'objectId'], **filter):
			result.append(configState.getIdent(returnType))
		return result
	
	def configState_createObjects(self, configStates):
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Creating configState %s" % configState)
			if self.configState_getObjects(
					attributes = ['configId'],
					configId   = configState.configId,
					objectId   = configState.objectId):
				logger.info(u"ConfigState '%s' already exists, updating" % configState)
				self.configState_updateObject(configState)
			else:
				self.configState_insertObject(configState)
	
	def configState_updateObjects(self, configStates):
		for configState in forceObjectClassList(configStates, ConfigState):
			self.configState_updateObject(configState)
	
	def configState_create(self, configId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.configState_createObjects(ConfigState.fromHash(hash))
	
	def configState_delete(self, configIds, objectIds):
		return self.configState_deleteObjects(
				self.configState_getObjects(
					configId = forceUnicodeLowerList(configIds),
					objectId = forceObjectIdList(objectIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_getIdents(self, returnType='unicode', **filter):
		result = []
		for product in self.product_getObjects(attributes = ['id'], **filter):
			result.append(product.getIdent(returnType))
		return result
	
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
	
	def product_updateObjects(self, products):
		for product in forceObjectClassList(products, Product):
			self.product_updateObject(product)
	
	def product_createLocalboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, changelog=None, productClassNames=None, windowsSoftwareIds=None):
		hash = locals()
		del hash['self']
		return self.product_createObjects(LocalbootProduct.fromHash(hash))
	
	def product_createNetboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, changelog=None, productClassNames=None, windowsSoftwareIds=None,
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
	def productProperty_getIdents(self, returnType='unicode', **filter):
		result = []
		for productProperty in self.productProperty_getObjects(attributes = ['productId', 'productVersion', 'packageVersion', 'propertyId'], **filter):
			result.append(productProperty.getIdent(returnType))
		return result
	
	def productProperty_createObjects(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating product property %s" % productProperty)
			if self.productProperty_getObjects(
					attributes     = ['productId'],
					productId      = productProperty.productId,
					productVersion = productProperty.productVersion,
					packageVersion = productProperty.packageVersion,
					propertyId     = productProperty.propertyId):
				logger.info(u"Product property '%s' already exists, updating" % productProperty)
				self.productProperty_updateObject(productProperty)
			else:
				self.productProperty_insertObject(productProperty)
	
	def productProperty_updateObjects(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			self.productProperty_updateObject(productProperty)
	
	def productProperty_create(self, productId, productVersion, packageVersion, propertyId, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(ProductProperty.fromHash(hash))
	
	def productProperty_createUnicode(self, productId, productVersion, packageVersion, propertyId, description=None, possibleValues=None, defaultValues=None, editable=None, multiValue=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(UnicodeProductProperty.fromHash(hash))
	
	def productProperty_createBool(self, productId, productVersion, packageVersion, propertyId, description=None, defaultValues=None):
		hash = locals()
		del hash['self']
		return self.productProperty_createObjects(BoolProductProperty.fromHash(hash))
	
	def productProperty_delete(self, productIds, productVersions, packageVersions, propertyIds):
		return self.productOnDepot_deleteObjects(
				self.productOnDepot_getObjects(
					productId      = forceProductIdList(productIds),
					productVersion = forceProductVersionList(productVersions),
					packageVersion = forcePackageVersionList(packageVersions),
					propertyIds    = forceUnicodeLowerList(propertyIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_getIdents(self, returnType='unicode', **filter):
		result = []
		for productOnDepot in self.productOnDepot_getObjects(attributes = ['productId', 'productType', 'depotId'], **filter):
			result.append(productOnDepot.getIdent(returnType))
		return result
	
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
	
	def productOnDepot_updateObjects(self, productOnDepots):
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			self.productOnDepot_updateObject(productOnDepot)
	
	def productOnDepot_create(self, productId, productType, productVersion, packageVersion, depotId, locked=None):
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
	def productOnClient_getIdents(self, returnType='unicode', **filter):
		result = []
		for productOnClient in self.productOnClient_getObjects(attributes = ['productId', 'productType', 'clientId'], **filter):
			result.append(productOnClient.getIdent(returnType))
		return result
	
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
	
	def productOnClient_updateObjects(self, productOnClients):
		for productOnClient in forceObjectClassList(productOnClients, ProductOnClient):
			self.productOnClient_updateObject(productOnClient)
	
	def productOnClient_create(self, productId, productType, clientId, installationStatus=None, actionRequest=None, actionProgress=None, productVersion=None, packageVersion=None, lastStateChange=None):
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
	def productPropertyState_getIdents(self, returnType='unicode', **filter):
		result = []
		for productPropertyState in self.productPropertyState_getObjects(attributes = ['productId', 'propertyId', 'objectId'], **filter):
			result.append(productPropertyState.getIdent(returnType))
		return result
	
	def productPropertyState_createObjects(self, productPropertyStates):
		productPropertyStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Creating productPropertyState '%s'" % productPropertyState)
			if self.productPropertyState_getObjects(
						productId  = productPropertyState.productId,
						objectId   = productPropertyState.objectId,
						propertyId = productPropertyState.propertyId):
				logger.info(u"ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self.productPropertyState_updateObject(productPropertyState)
			else:
				self.productPropertyState_insertObject(productPropertyState)
	
	def productPropertyState_updateObjects(self, productPropertyStates):
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			self.productPropertyState_updateObject(productPropertyState)
	
	def productPropertyState_create(self, productId, propertyId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))
	
	def productPropertyState_delete(self, productIds, propertyIds, objectIds):
		return self.productPropertyState_deleteObjects(
				self.productPropertyState_getObjects(
					productId  = forceProductIdList(productIds),
					propertyId = forceUnicodeLowerList(propertyIds),
					objectId   = forceObjectIdList(objectIds)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_getIdents(self, returnType='unicode', **filter):
		result = []
		for group in self.group_getObjects(attributes = ['id'], **filter):
			result.append(group.getIdent(returnType))
		return result
	
	def group_createObjects(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Creating group '%s'" % group)
			if self.group_getObjects(id = group.id):
				logger.info(u"Group '%s' already exists, updating" % group)
				self.group_updateObject(group)
			else:
				self.group_insertObject(group)
	
	def group_updateObjects(self, groups):
		for group in forceObjectClassList(groups, Group):
			self.group_updateObject(group)
	
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
	def objectToGroup_getIdents(self, returnType='unicode', **filter):
		result = []
		for objectToGroup in self.objectToGroup_getObjects(attributes = ['groupId', 'objectId'], **filter):
			result.append(objectToGroup.getIdent(returnType))
		return result
	
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
	
	def objectToGroup_updateObjects(self, objectToGroups):
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			self.objectToGroup_updateObject(objectToGroup)
	
	def objectToGroup_create(self, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ObjectToGroup.fromHash(hash))
	
	def objectToGroup_delete(self, groupIds, objectIds):
		return self.objectToGroup_deleteObjects(
				self.objectToGroup_getObjects(
					groupId = forceGroupIdList(groupIds),
					objectId = forceObjectIdList(objectIds)))
	







