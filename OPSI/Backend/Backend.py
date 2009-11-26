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
import types, new, inspect

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Backend.Object import *

logger = Logger()

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                                                                                    =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

def getArgAndCallString(method):
	argString = u''
	callString = u''
	(args, varargs, varkwargs, argDefaults) = inspect.getargspec(method)
	#logger.debug2(u"args: %s" % unicode(args))
	#logger.debug2(u"varargs: %s" % unicode(varargs))
	#logger.debug2(u"varkwargs: %s" % unicode(varkwargs))
	#logger.debug2(u"argDefaults: %s" % unicode(argDefaults))
	for i in range(len(args)):
		#logger.debug2(u"Processing arg [%s] %s" % (i, args[i]))
		if (args[i] == 'self'):
			continue
		if (argString):
			argString += u', '
			callString += u', '
		argString += args[i]
		callString += u'%s=%s' % (args[i], args[i])
		if type(argDefaults) is tuple and (len(argDefaults) + i >= len(args)):
			default = argDefaults[len(argDefaults)-len(args)+i]
			if type(default) is str:
				default = u"'%s'" % default
			elif type(default) is unicode:
				default = u"u'%s'" % default
			#logger.debug2(u"   Using default [%s] %s" % (len(argDefaults)-len(args)+i, default))
			argString += u'=%s' % unicode(default)
	if varargs:
		for vararg in varargs:
			if argString:
				argString += u', '
				callString += u', '
			argString += u'*%s' % vararg
			callString += u'*%s' % vararg
	if varkwargs:
		if argString:
			argString += u', '
			callString += u', '
		argString += u'**%s' % varkwargs
		callString += u'**%s' % varkwargs
	#logger.debug2(u"Arg string is: %s" % argString)
	#logger.debug2(u"Call string is: %s" % callString)
	return (argString, callString)


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
	
	def getInterface(self):
		''' This function returns a list of available interface methods.
		The methods are defined by hashes containing the keys "name" and
		"params", which is a list of parameter names used for a method.
		Parameters starting with an asterisk (*) are optional '''
		methodList = []
		methods = {}
		for (n, t) in self.__dict__.items():
			# Extract a list of all "public" functions (functionname does not start with '_')
			if ( (type(t) == types.FunctionType or type(t) == types.MethodType ) and not n.startswith('_') ):
				methods[n] = t
		
		for (n, t) in methods.items():
			argCount = t.func_code.co_argcount
			argNames = list(t.func_code.co_varnames[1:argCount])
			argDefaults = t.func_defaults
			if ( argDefaults != None and len(argDefaults) > 0 ):
				offset = argCount - len(argDefaults) - 1
				for i in range( len(argDefaults) ):
					argNames[offset+i] = '*' + argNames[offset+i]		
			methodList.append( { 'name': n, 'params': argNames} )
		
		# Sort the function list by name
		methodList.sort()
		return methodList

class BackendIdentExtension(Backend):
	def host_getIdents(self, returnType='unicode', **filter):
		result = []
		for host in self.host_getObjects(attributes = ['id'], **filter):
			result.append(host.getIdent(returnType))
		return result
	
	def config_getIdents(self, returnType='unicode', **filter):
		result = []
		for config in self.config_getObjects(attributes = ['id'], **filter):
			result.append(config.getIdent(returnType))
		return result
	
	def configState_getIdents(self, returnType='unicode', **filter):
		result = []
		for configState in self.configState_getObjects(attributes = ['configId', 'objectId'], **filter):
			result.append(configState.getIdent(returnType))
		return result
	
	def product_getIdents(self, returnType='unicode', **filter):
		result = []
		for product in self.product_getObjects(attributes = ['id'], **filter):
			result.append(product.getIdent(returnType))
		return result
	
	def productProperty_getIdents(self, returnType='unicode', **filter):
		result = []
		for productProperty in self.productProperty_getObjects(attributes = ['productId', 'productVersion', 'packageVersion', 'propertyId'], **filter):
			result.append(productProperty.getIdent(returnType))
		return result
	
	def productDependency_getIdents(self, returnType='unicode', **filter):
		result = []
		for productDependency in self.productDependency_getObjects(attributes = ['productId', 'productVersion', 'packageVersion', 'productAction', 'requiredProductId'], **filter):
			result.append(productDependency.getIdent(returnType))
		return result
	
	def productOnDepot_getIdents(self, returnType='unicode', **filter):
		result = []
		for productOnDepot in self.productOnDepot_getObjects(attributes = ['productId', 'productType', 'depotId'], **filter):
			result.append(productOnDepot.getIdent(returnType))
		return result
	
	def productOnClient_getIdents(self, returnType='unicode', **filter):
		result = []
		for productOnClient in self.productOnClient_getObjects(attributes = ['productId', 'productType', 'clientId'], **filter):
			result.append(productOnClient.getIdent(returnType))
		return result
	
	def productPropertyState_getIdents(self, returnType='unicode', **filter):
		result = []
		for productPropertyState in self.productPropertyState_getObjects(attributes = ['productId', 'propertyId', 'objectId'], **filter):
			result.append(productPropertyState.getIdent(returnType))
		return result
	
	def group_getIdents(self, returnType='unicode', **filter):
		result = []
		for group in self.group_getObjects(attributes = ['id'], **filter):
			result.append(group.getIdent(returnType))
		return result
	
	def objectToGroup_getIdents(self, returnType='unicode', **filter):
		result = []
		for objectToGroup in self.objectToGroup_getObjects(attributes = ['groupId', 'objectId'], **filter):
			result.append(objectToGroup.getIdent(returnType))
		return result
	
	def licenseContract_getIdents(self, returnType='unicode', **filter):
		result = []
		for licenseContract in self.licenseContract_getObjects(attributes = ['id'], **filter):
			result.append(licenseContract.getIdent(returnType))
		return result
	
	def softwareLicense_getIdents(self, returnType='unicode', **filter):
		result = []
		for softwareLicense in self.softwareLicense_getObjects(attributes = ['id', 'licenseContractId'], **filter):
			result.append(softwareLicense.getIdent(returnType))
		return result
	
	def licensePool_getIdents(self, returnType='unicode', **filter):
		result = []
		for licensePool in self.licensePool_getObjects(attributes = ['id'], **filter):
			result.append(licensePool.getIdent(returnType))
		return result
	
	def licenseOnClient_getIdents(self, returnType='unicode', **filter):
		result = []
		for licenseOnClient in self.licenseOnClient_getObjects(attributes = ['softwareLicenseId', 'licensePoolId', 'clientId'], **filter):
			result.append(licenseOnClient.getIdent(returnType))
		return result
	
	
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                   CLASS CONFIGDATABACKEND                                          =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ConfigDataBackend(BackendIdentExtension):
	
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
		productIds = []
		for product in forceObjectClassList(products, Product):
			if not product.id in productIds:
				productIds.append(product.id)
			self.productProperty_deleteObjects(
				self.productProperty_getObjects(
					productId = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion ))
			self.productDependency_deleteObjects(
				self.productDependency_getObjects(
					productId = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion ))
			self.productOnDepot_deleteObjects(
				self.productOnDepot_getObjects(
					productId = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion ))
			self.productOnClient_deleteObjects(
				self.productOnClient_getObjects(
					productId = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion ))
		
		for productId in productIds:
			if not self.product_getIdents(id = productId):
				# No more products with this id found => delete productPropertyStates
				self.productPropertyState_deleteObjects(
					self.productPropertyState_getObjects(productId = productId))
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		productProperty = forceObjectClass(productProperty, ProductProperty)
		productProperty.setDefaults()
		
		if not self.product_getIdents(
				id             = productProperty.productId,
				productVersion = productProperty.productVersion,
				packageVersion = productProperty.packageVersion):
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productProperty.productId, productProperty.productVersion, productProperty.packageVersion))
		
	def productProperty_updateObject(self, productProperty):
		pass
	
	def productProperty_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductProperty, attributes, **filter)
	
	def productProperty_deleteObjects(self, productProperties):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		productDependency = forceObjectClass(productDependency, ProductDependency)
		productDependency.setDefaults()
		if not productDependency.getRequiredAction() and not productDependency.getRequiredInstallationStatus():
			raise BackendBadValueError(u"Either a required action or a required installation status must be given")
		if not self.product_getIdents(
				id                = productDependency.productId,
				productVersion    = productDependency.productVersion,
				packageVersion    = productDependency.packageVersion):
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productProperty.productId, productProperty.productVersion, productProperty.packageVersion))
		
	def productDependency_updateObject(self, productDependency):
		pass
	
	def productDependency_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductDependency, attributes, **filter)
	
	def productDependency_deleteObjects(self, productDependencies):
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
		elif (productOnClient.actionRequest == 'uninstall') and not products[0].uninstallScript:
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
		if not self.productProperty_getIdents(
					productId  = productPropertyState.productId,
					propertyId = productPropertyState.propertyId):
			raise BackendReferentialIntegrityError(u"ProductProperty with id '%s' for product '%s' not found"
				% (productPropertyState.productId, productPropertyState.propertyId))
	
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
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_insertObject(self, licenseContract):
		licenseContract = forceObjectClass(licenseContract, LicenseContract)
		licenseContract.setDefaults()
	
	def licenseContract_updateObject(self, licenseContract):
		pass
	
	def licenseContract_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicenseContract, attributes, **filter)
	
	def licenseContract_deleteObjects(self, licenseContracts):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_insertObject(self, softwareLicense):
		softwareLicense = forceObjectClass(softwareLicense, SoftwareLicense)
		softwareLicense.setDefaults()
		if not softwareLicense.licenseContractId:
			raise BackendBadValueError(u"License contract missing")
		if not self.licenseContract_getIdents(id = softwareLicense.licenseContractId):
			raise BackendReferentialIntegrityError(u"License contract with id '%s' not found" % softwareLicense.licenseContractId)
		
	def softwareLicense_updateObject(self, softwareLicense):
		pass
	
	def softwareLicense_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(SoftwareLicense, attributes, **filter)
	
	def softwareLicense_deleteObjects(self, softwareLicenses):
		softwareLicenseIds = []
		for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense):
			softwareLicenseIds.append(softwareLicense.id)
		self.softwareLicenseToLicensePool_deleteObjects(
			self.softwareLicenseToLicensePool_getObjects(
				softwareLicenseId = softwareLicenseIds ))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePools                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_insertObject(self, licensePool):
		licensePool = forceObjectClass(licensePool, LicensePool)
		licensePool.setDefaults()
	
	def licensePool_updateObject(self, licensePool):
		pass
	
	def licensePool_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicensePool, attributes, **filter)
	
	def licensePool_deleteObjects(self, licensePools):
		licensePoolIds = []
		for licensePool in forceObjectClassList(licensePools, LicensePool):
			licensePoolIds.append(licensePool.id)
		softwareLicenseToLicensePoolIdents = self.softwareLicenseToLicensePool_getIdents(licensePoolId = licensePoolIds, returnType = 'unicode')
		if softwareLicenseToLicensePoolIdents:
			raise BackendReferentialIntegrityError(u"Refusing to delete license pool(s) %s, one ore more licenses/keys refer to pool: %s" % \
				(licensePoolIds, softwareLicenseToLicensePoolIdents))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool):
		softwareLicenseToLicensePool = forceObjectClass(softwareLicenseToLicensePool, SoftwareLicenseToLicensePool)
		softwareLicenseToLicensePool.setDefaults()
		if not self.softwareLicense_getIdents(id = softwareLicenseToLicensePool.softwareLicenseId):
			raise BackendReferentialIntegrityError(u"Software license with id '%s' not found" % softwareLicenseToLicensePool.softwareLicenseId)
		if not self.licensePool_getIdents(id = softwareLicenseToLicensePool.licensePoolId):
			raise BackendReferentialIntegrityError(u"License with id '%s' not found" % softwareLicenseToLicensePool.licensePoolId)
		
	def softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool):
		pass
	
	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(SoftwareLicenseToLicensePool, attributes, **filter)
	
	def softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools):
		softwareLicenseIds = []
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			softwareLicenseIds.append(softwareLicenseToLicensePool.softwareLicenseId)
		licenseOnClientIdents = self.licenseOnClient_getIdents(softwareLicenseId = softwareLicenseIds)
		if licenseOnClientIdents:
			raise BackendReferentialIntegrityError(u"Refusing to delete softwareLicenseToLicensePool(s), one ore more licenses in use: %s"\
				% licenseOnClientIdents)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_insertObject(self, licenseOnClient):
		licenseOnClient = forceObjectClass(licenseOnClient, LicenseOnClient)
		licenseOnClient.setDefaults()
	
	def licenseOnClient_updateObject(self, licenseOnClient):
		pass
	
	def licenseOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicenseOnClient, attributes, **filter)
	
	def licenseOnClient_deleteObjects(self, licenseOnClients):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   HardwareInventory                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def hardwareInventory_insertObject(self, hardwareInventory):
		hardwareInventory = forceObjectClass(hardwareInventory, HardwareInventory)
		hardwareInventory.setDefaults()
	
	def hardwareInventory_updateObject(self, hardwareInventory):
		pass
	
	def hardwareInventory_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(HardwareInventory, attributes, **filter)
	
	def hardwareInventory_deleteObjects(self, hardwareInventory):
		pass


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                               CLASS EXTENDEDCONFIGDATABACKEND                                      =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ExtendedConfigDataBackend(BackendIdentExtension):
	
	def __init__(self, backend):
		self._backend = backend
		self._createInstanceMethods()
	
	def _createInstanceMethods(self):
		for member in inspect.getmembers(self._backend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public method '%s'" % methodName)
			if hasattr(self.__class__, methodName):
				logger.debug(u"Not overwriting method %s" % methodName)
				continue
			(argString, callString) = getArgAndCallString(member[1])
			
			exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))
			setattr(self.__class__, methodName, new.instancemethod(eval(methodName), self, self.__class__))
		
	def _executeMethod(self, methodName, **kwargs):
		return eval(u'self._backend.%s(**kwargs)' % methodName)
	
	def searchObjects(self, filter):
		logger.info(u"=== Starting search, filter: %s" % filter)
		try:
			parsedFilter = ldapfilter.parseFilter(filter)
		except Exception, e:
			raise BackendBadValueError(u"Failed to parse filter '%s'" % filter)
		logger.debug(u"Parsed search filter: %s" % repr(parsedFilter))
		
		
		def combineResults(result1, result2, operator):
			if not result1:
				return result2
			if not result2:
				return result1
			
			result1IdentIndex = -1
			result2IdentIndex = -1
			
			for i in range(len(result1['identAttributes'])):
				for j in range(len(result2['identAttributes'])):
					if (result1['identAttributes'][i] == result2['identAttributes'][j]):
						if (result1['identAttributes'][i] != 'id') or (result1['objectClass'] == result2['objectClass']):
							result1IdentIndex = i
							result2IdentIndex = j
							break
			if (result1IdentIndex == -1):
				logger.debug(u"No matching identAttributes found (%s, %s)" % (result1['identAttributes'], result2['identAttributes']))
			
			if (result1IdentIndex == -1):
				#if (len(result1['identAttributes']) == 1) and result1['foreignIdAttributes']:
				if 'id' in result1['identAttributes'] and result1['foreignIdAttributes']:
					logger.debug(u"Trying foreignIdAttributes of result1: %s" % result1['foreignIdAttributes'])
					for attr in result1['foreignIdAttributes']:
						for i in range(len(result2['identAttributes'])):
							logger.debug2("%s == %s" % (attr, result2['identAttributes'][i]))
							if (attr == result2['identAttributes'][i]):
								result2IdentIndex = i
								for a in range(len(result1['identAttributes'])):
									if (result1['identAttributes'][a] == 'id'):
										result1IdentIndex = a
								break
				else:
					logger.debug(u"Cannot use foreignIdAttributes of result1")
				
			if (result1IdentIndex == -1):
				#if (len(result2['identAttributes']) == 1) and result2['foreignIdAttributes']:
				if 'id' in result2['identAttributes'] and result2['foreignIdAttributes']:
					logger.debug(u"Trying foreignIdAttributes of result2: %s" % result2['foreignIdAttributes'])
					for attr in result2['foreignIdAttributes']:
						for i in range(len(result1['identAttributes'])):
							logger.debug2("%s == %s" % (attr, result1['identAttributes'][i]))
							if (attr == result1['identAttributes'][i]):
								result1IdentIndex = i
								for a in range(len(result2['identAttributes'])):
									if (result2['identAttributes'][a] == 'id'):
										result2IdentIndex = a
								break
				else:
					logger.debug(u"Cannot use foreignIdAttributes of result2")
			
			if (result1IdentIndex == -1):
				raise BackendBadValueError(u"Failed to combine partial results %s(%s | %s) %s(%s | %s)" \
					% (result1['objectClass'], result1['identAttributes'], result1['foreignIdAttributes'],
					   result2['objectClass'], result2['identAttributes'], result2['foreignIdAttributes']))
			
			logger.info(u"Using attributes %s.%s and %s.%s to combine results (%s)" \
				% (result1['objectClass'], result1['identAttributes'][result1IdentIndex],
				   result2['objectClass'], result2['identAttributes'][result2IdentIndex],
				   operator))
			
			values1 = []
			for v in result1['identValues']:
				values1.append(v[result1IdentIndex])
			values2 = []
			for v in result2['identValues']:
				values2.append(v[result2IdentIndex])
			
			foreignIdAttributes = result1["foreignIdAttributes"]
			for attr in result2["foreignIdAttributes"]:
				if attr in result1["foreignIdAttributes"]:
					continue
				foreignIdAttributes.append(attr)
			
			result = {
				"objectClass":         result2["objectClass"],
				"foreignIdAttributes": foreignIdAttributes,
				"identAttributes":     [ result2['identAttributes'][result2IdentIndex] ],
				"identValues":         []
			}
			
			if (operator == 'OR'):
				vals = []
				values1.extend(values2)
				for v in values1:
					if v in vals:
						continue
					vals.append(v)
					result['identValues'].append([v])
			elif (operator == 'AND'):
				vals = []
				for v in values2:
					if not v in values1 or v in vals:
						continue
					vals.append(v)
					result['identValues'].append([v])
			
			return result
			
		def handleFilter(f, level=0):
			objectClass = None
			objectFilter = {}
			result = None
			
			logger.debug(u"Level %s, processing: %s" % (level, repr(f)))
			
			if isinstance(f, pureldap.LDAPFilter_equalityMatch):
				logger.debug(u"Handle equality attribute '%s', value '%s'" % (f.attributeDesc.value, f.assertionValue.value))
				if (f.attributeDesc.value.lower() == 'objectclass'):
					objectClass = f.assertionValue.value
				else:
					objectFilter = { f.attributeDesc.value: f.assertionValue.value }
					
			elif isinstance(f, pureldap.LDAPFilter_substrings):
				logger.debug(u"Handle substrings type %s: %s" % (f.type, repr(f.substrings)))
				if (f.type.lower() == 'objectclass'):
					raise BackendBadValueError(u"Substring search not allowed for objectClass")
				if   isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_initial):
					# string*
					objectFilter = { f.type: '%s*' % f.substrings[0].value }
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_final):
					# *string
					objectFilter = { f.type: '*%s' % f.substrings[0].value }
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_any):
					# *string*
					objectFilter = { f.type: '*%s*' % f.substrings[0].value }
				else:
					raise BackendBadValueError(u"Unsupported substring class: %s" % repr(f))
			elif isinstance(f, pureldap.LDAPFilter_present):
				objectFilter = { f.value: '*' }
				
			elif isinstance(f, pureldap.LDAPFilter_and) or isinstance(f, pureldap.LDAPFilter_or):
				operator = None
				if isinstance(f, pureldap.LDAPFilter_and):
					operator = 'AND'
				elif isinstance(f, pureldap.LDAPFilter_or):
					operator = 'OR'
				
				for fChild in f.data:
					(res, oc, of) = handleFilter(fChild, level+1)
					logger.debug(u"Got return values: %s, %s, %s" % (res, oc, of))
					if oc:
						objectClass = oc
					if of:
						objectFilter.update(of)
					if res:
						#if (objectClass or objectFilter):
						#	raise BackendBadValueError(u"Unsupported search filter: %s" % repr(f))
						result = combineResults(result, res, operator)
				
				if objectFilter or objectClass:
					if objectFilter and not objectClass:
						raise BackendBadValueError(u"Bad search filter '%s': objectClass not defined" % repr(f))
					
					try:
						oc = eval(objectClass)
						if not ('type' in objectFilter):
							types = [ objectClass ]
							for c in oc.subClasses:
								types.append(c)
							if (len(types) > 1):
								objectFilter['type'] = types
							
						this = self
						objectFilterNew = {}
						for (key, value) in objectFilter.items():
							if (key != 'type'):
								try:
									value = eval(value)
								except:
									pass
							objectFilterNew[str(key)] = value
						objectFilter = objectFilterNew
						
						logger.debug(u"Executing: this.%s_getIdents(returnType = 'list', %s)" % (getBackendMethodPrefix(oc), objectFilter))
						res = {
							"objectClass":         objectClass,
							"foreignIdAttributes": getForeignIdAttributes(oc),
							"identAttributes":     getIdentAttributes(oc),
							"identValues":         eval("this.%s_getIdents(returnType = 'list', **objectFilter)" % getBackendMethodPrefix(oc))
						}
						if (level == 0):
							result = combineResults(result, res, operator)
						else:
							result = res
						logger.debug("Result: %s" % result)
					except Exception, e:
						logger.logException(e)
						raise BackendBadValueError(u"Failed to process search filter '%s': %s" % (repr(f), e))
					
					objectClass = None
					objectFilter = {}
					
			elif isinstance(f, pureldap.LDAPFilter_not):
				raise BackendBadValueError(u"Operator '!' not allowed")
			else:
				raise BackendBadValueError(u"Unsupported search filter: %s" % repr(f))
			
			return (result, objectClass, objectFilter)
		
		result = []
		for v in handleFilter(parsedFilter)[0].get('identValues', []):
			result.append(v[0])
		logger.info(u"=== Search done, result: %s" % result)
		return result
		
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
	
	def host_updateObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			self._backend.host_updateObject(host)
	
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
	
	def host_delete(self, id):
		if not id: id = []
		return self._backend.host_deleteObjects(
				self._backend.host_getObjects(
					id = forceHostIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_createObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Creating config %s" % config)
			if self._backend.config_getObjects(
					attributes = ['id'],
					id         = config.id):
				logger.info(u"Config '%s' already exists, updating" % config)
				self._backend.config_updateObject(config)
			else:
				self._backend.config_insertObject(config)
	
	def config_updateObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			self._backend.config_updateObject(config)
	
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
	
	def config_delete(self, id):
		if not id: id = []
		return self._backend.config_deleteObjects(
				config_getObjects(
					id = forceUnicodeLowerList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_getObjects(self, attributes=[], **filter):
		# Get product states from backend
		configStates = self._backend.configState_getObjects(attributes, **filter)
		# Get objectIds
		objectIds = self._backend.host_getIdents(id = filter.get('objectId'), returnType = 'unicode')
		# Create data structure for config states to find missing ones
		css = {}
		for objectId in objectIds:
			css[objectId] = []
		for cs in self._backend.configState_getObjects(attributes = ['objectId', 'configId'], objectId = objectIds):
			css[cs.objectId].append(cs.configId)
		# Create missing config states
		for config in self._backend.config_getObjects(id = filter.get('configId')):
			logger.debug("Default values for '%s': %s" % (config.id, config.defaultValues))
			if filter.get('configId') and not config.id in filter['configId']:
				continue
			for objectId in objectIds:
				if not config.id in css[objectId]:
					# Create default
					configStates.append(
						ConfigState(
							configId = config.id,
							objectId = objectId,
							values   = config.defaultValues
						)
					)
		return configStates
		
	def configState_createObjects(self, configStates):
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Creating configState %s" % configState)
			if self._backend.configState_getObjects(
					attributes = ['configId'],
					configId   = configState.configId,
					objectId   = configState.objectId):
				logger.info(u"ConfigState '%s' already exists, updating" % configState)
				self._backend.configState_updateObject(configState)
			else:
				self._backend.configState_insertObject(configState)
	
	def configState_updateObjects(self, configStates):
		for configState in forceObjectClassList(configStates, ConfigState):
			self._backend.configState_updateObject(configState)
	
	def configState_create(self, configId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self._backend.configState_createObjects(ConfigState.fromHash(hash))
	
	def configState_delete(self, configId, objectId):
		if not configId: configId = []
		if not objectId: objectId = []
		return self._backend.configState_deleteObjects(
				self._backend.configState_getObjects(
					configId = forceUnicodeLowerList(configId),
					objectId = forceObjectIdList(objectId)))
	
	def configState_getClientToDepotserver(self, depotIds=[], clientIds=[]):
		result = []
		if not depotIds:
			depotIds = self.host_getIdents(type = 'OpsiDepotserver')
		
		knownClientIds = self.host_getIdents(type = 'OpsiClient', id = clientIds)
		configId = 'network.depot_server.depot_id'
		for configState in self.configState_getObjects(configId = configId, objectId = clientIds):
			if not configState.objectId in knownClientIds:
				logger.debug(u"Skipping objectId '%s': not a opsi client" % configState.objectId)
				continue
			depotId = configState.values[0]
			if not depotId:
				logger.error(u"No depot server configured for client '%s'" % configState.objectId)
				continue
			if not depotId in depotIds:
				continue
			result.append({ 'depotId': depotId, 'clientId': configState.objectId })
		return result
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_createObjects(self, products):
		for product in forceObjectClassList(products, Product):
			logger.info(u"Creating product %s" % product)
			if self._backend.product_getObjects(
					attributes = ['productId'],
					id = product.id, productVersion = product.productVersion,
					packageVersion = product.packageVersion):
				logger.info(u"Product '%s' already exists, updating" % product)
				self._backend.product_updateObject(product)
			else:
				self._backend.product_insertObject(product)
	
	def product_updateObjects(self, products):
		for product in forceObjectClassList(products, Product):
			self._backend.product_updateObject(product)
	
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
	
	def product_delete(self, productId):
		if not productId: productId = []
		return self._backend.product_deleteObjects(
				product_getObjects(
					productId = forceProductIdList(productId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_createObjects(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating product property %s" % productProperty)
			if self._backend.productProperty_getObjects(
					attributes     = ['productId'],
					productId      = productProperty.productId,
					productVersion = productProperty.productVersion,
					packageVersion = productProperty.packageVersion,
					propertyId     = productProperty.propertyId):
				logger.info(u"Product property '%s' already exists, updating" % productProperty)
				self._backend.productProperty_updateObject(productProperty)
			else:
				self._backend.productProperty_insertObject(productProperty)
	
	def productProperty_updateObjects(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			self._backend.productProperty_updateObject(productProperty)
	
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
	
	def productProperty_delete(self, productId, productVersion, packageVersion, propertyId):
		if not productId:      productId      = []
		if not productVersion: productVersion = []
		if not packageVersion: packageVersion = []
		if not propertyId:     propertyId     = []
		return self._backend.productOnDepot_deleteObjects(
				self._backend.productOnDepot_getObjects(
					productId      = forceProductIdList(productId),
					productVersion = forceProductVersionList(productVersion),
					packageVersion = forcePackageVersionList(packageVersion),
					propertyIds    = forceUnicodeLowerList(propertyId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_createObjects(self, productDependencies):
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			logger.info(u"Creating product dependency %s" % productDependency)
			if self._backend.productDependency_getIdents(
					productId         = productDependency.productId,
					productVersion    = productDependency.productVersion,
					packageVersion    = productDependency.packageVersion,
					productAction     = productDependency.productAction,
					requiredProductId = productDependency.requiredProductId):
				logger.info(u"Product dependency '%s' already exists, updating" % productDependency)
				self._backend.productDependency_updateObject(productDependency)
			else:
				self._backend.productDependency_insertObject(productDependency)
	
	def productDependency_updateObjects(self, productDependencies):
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			self._backend.productDependency_updateObject(productDependency)
	
	def productDependency_create(self, productId, productVersion, packageVersion, productAction, requiredProductId, requiredProductVersion=None, requiredPackageVersion=None, requiredAction=None, requiredInstallationStatus=None, requirementType=None):
		hash = locals()
		del hash['self']
		return self.productDependency_createObjects(ProductDependency.fromHash(hash))
	
	def productDependency_delete(self, productId, productVersion, packageVersion, productAction, requiredProductId):
		if not productId:         productId         = []
		if not productVersion:    productVersion    = []
		if not packageVersion:    packageVersion    = []
		if not productAction:     productAction     = []
		if not requiredProductId: requiredProductId = []
		return self._backend.productDependency_deleteObjects(
				self._backend.productDependency_getObjects(
					productId         = forceProductIdList(productId),
					productVersion    = forceProductVersionList(productVersion),
					packageVersion    = forcePackageVersionList(packageVersion),
					productAction     = forceActionRequestList(productAction),
					requiredProductId = forceProductIdList(requiredProductId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_createObjects(self, productOnDepots):
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		for productOnDepot in productOnDepots:
			logger.info(u"Creating productOnDepot '%s'" % productOnDepot)
			if self._backend.productOnDepot_getObjects(
					productId = productOnDepot.productId,
					depotId = productOnDepot.depotId):
				logger.info(u"ProductOnDepot '%s' already exists, updating" % productOnDepot)
				self._backend.productOnDepot_updateObject(productOnDepot)
			else:
				self._backend.productOnDepot_insertObject(productOnDepot)
	
	def productOnDepot_updateObjects(self, productOnDepots):
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			self._backend.productOnDepot_updateObject(productOnDepot)
	
	def productOnDepot_create(self, productId, productType, productVersion, packageVersion, depotId, locked=None):
		hash = locals()
		del hash['self']
		return self.productOnDepot_createObjects(ProductOnDepot.fromHash(hash))
	
	def productOnDepot_delete(self, productId, productVersion, packageVersion, depotId):
		if not productId:      productId      = []
		if not productVersion: productVersion = []
		if not packageVersion: packageVersion = []
		if not depotId:        depotId        = []
		return self._backend.productOnDepot_deleteObjects(
				self._backend.productOnDepot_getObjects(
					productId = forceProductIdList(productId),
					productVersion = forceProductVersionList(productVersion),
					packageVersion = forcePackageVersionList(packageVersion),
					depotId = forceHostIdList(depotId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_getObjects(self, attributes=[], **filter):
		# Get product states from backend
		productOnClients = self._backend.productOnClient_getObjects(attributes, **filter)
		if filter.get('installationStatus') in (None, 'not_installed') and filter.get('actionRequest') in (None, 'none'):
			# Get all client ids by filter
			clientIds = self._backend.host_getIdents(id = filter.get('clientId'), returnType = 'unicode')
			# Get depot to client assignment
			depotToClients = {}
			for clientToDepot in self.configState_getClientToDepotserver(clientIds = clientIds):
				if not depotToClients.has_key(clientToDepot['depotId']):
					depotToClients[clientToDepot['depotId']] = []
				depotToClients[clientToDepot['depotId']].append(clientToDepot['clientId'])
			# Create data structure for product states to find missing ones
			pocs = {}
			for clientId in clientIds:
				pocs[clientId] = []
			# Get available on clients without filter!
			for poc in self._backend.productOnClient_getObjects(attributes = ['clientId', 'productId'], clientId = clientIds):
				pocs[poc.clientId].append(poc.productId)
			# Create missing product states
			for (depotId, depotClientIds) in depotToClients.items():
				productOnDepots = self._backend.productOnDepot_getObjects(
					depotId        = depotId,
					productId      = filter.get('productId'),
					productVersion = filter.get('productVersion'),
					packageVersion = filter.get('packageVersion'))
				for clientId in depotClientIds:
					if not clientId in clientIds:
						# Filtered
						continue
					for pod in productOnDepots:
						if not pod.productId in pocs[clientId]:
							# Create default
							productOnClients.append(
								ProductOnClient(
									productId          = pod.productId,
									productType        = pod.productType,
									clientId           = clientId,
									installationStatus = u'not_installed',
									actionRequest      = u'none',
								)
							)
		return productOnClients
	
	def productOnClient_createObjects(self, productOnClients):
		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		for productOnClient in productOnClients:
			logger.info(u"Creating productOnClient '%s'" % productOnClient)
			if self._backend.productOnClient_getObjects(
					productId = productOnClient.productId,
					clientId = productOnClient.clientId):
				logger.info(u"ProductOnClient '%s' already exists, updating" % productOnClient)
				self._backend.productOnClient_updateObject(productOnClient)
			else:
				self._backend.productOnClient_insertObject(productOnClient)
	
	def productOnClient_updateObjects(self, productOnClients):
		for productOnClient in forceObjectClassList(productOnClients, ProductOnClient):
			self._backend.productOnClient_updateObject(productOnClient)
	
	def productOnClient_create(self, productId, productType, clientId, installationStatus=None, actionRequest=None, actionProgress=None, productVersion=None, packageVersion=None, lastStateChange=None):
		hash = locals()
		del hash['self']
		return self.productOnClient_createObjects(ProductOnClient.fromHash(hash))
	
	def productOnClient_delete(self, productId, clientId):
		if not productId:  productId  = []
		if not clientId:   clientId   = []
		return self._backend.productOnClient_deleteObjects(
				self._backend.productOnClient_getObjects(
					productId = forceProductIdList(productId),
					clientId = forceHostIdList(clientId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_getObjects(self, attributes=[], **filter):
		# Get product properties from backend
		productPropertyStates = self._backend.productPropertyState_getObjects(attributes, **filter)
		# Get objectIds
		objectIds = self._backend.host_getIdents(type = 'OpsiClient', id = filter.get('objectId'), returnType = 'unicode')
		# Get depotIds
		depotIdToClientIds = {}
		for configState in self.configState_getClientToDepotserver(clientIds = filter.get('objectIds')):
			if not configState['depotId'] in depotIdToClientIds.keys():
				depotIdToClientIds[configState['depotId']] = []
			depotIdToClientIds[configState['depotId']].append(configState['clientId'])
		# Create data structure for product property states to find missing ones
		ppss = {}
		for objectId in objectIds:
			ppss[objectId] = []
		for pps in self._backend.productPropertyState_getObjects(attributes = ['objectId', 'propertyId'], objectId = objectIds):
			ppss[pps.objectId].append(pps.propertyId)
		# Create missing product property states
		for (depotId, clientIds) in depotIdToClientIds.items():
			for productOnDepot in self.productOnDepot_getObjects(depotId = depotId, productId = filter.get('productId')):
				# TODO: Use productPropertyState of depot as default!
				for productProperty in self._backend.productProperty_getObjects(
								productId      = productOnDepot.productId,
								productVersion = productOnDepot.productVersion,
								packageVersion = productOnDepot.packageVersion,
								propertyId     = filter.get('propertyId')):
					for clientId in clientIds:
						if not clientId in objectIds:
							# Filtered
							continue
						if productProperty.propertyId in ppss[clientId]:
							continue
						productPropertyStates.append(
							ProductPropertyState(
								productId  = productProperty.productId,
								propertyId = productProperty.propertyId,
								objectId   = clientId,
								values     = productProperty.defaultValues
							)
						)
		return productPropertyStates
	
	def productPropertyState_createObjects(self, productPropertyStates):
		productPropertyStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Creating productPropertyState '%s'" % productPropertyState)
			if self._backend.productPropertyState_getObjects(
						productId  = productPropertyState.productId,
						objectId   = productPropertyState.objectId,
						propertyId = productPropertyState.propertyId):
				logger.info(u"ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self._backend.productPropertyState_updateObject(productPropertyState)
			else:
				self._backend.productPropertyState_insertObject(productPropertyState)
	
	def productPropertyState_updateObjects(self, productPropertyStates):
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			self._backend.productPropertyState_updateObject(productPropertyState)
	
	def productPropertyState_create(self, productId, propertyId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))
	
	def productPropertyState_delete(self, productId, propertyId, objectId):
		if not productId:  productId  = []
		if not propertyId: propertyId = []
		if not objectId:   objectId   = []
		return self._backend.productPropertyState_deleteObjects(
				self._backend.productPropertyState_getObjects(
					productId  = forceProductIdList(productId),
					propertyId = forceUnicodeLowerList(propertyId),
					objectId   = forceObjectIdList(objectId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_createObjects(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Creating group '%s'" % group)
			if self._backend.group_getObjects(id = group.id):
				logger.info(u"Group '%s' already exists, updating" % group)
				self._backend.group_updateObject(group)
			else:
				self._backend.group_insertObject(group)
	
	def group_updateObjects(self, groups):
		for group in forceObjectClassList(groups, Group):
			self._backend.group_updateObject(group)
	
	def group_createHostGroup(self, id, description=None, notes=None, parentGroupId=None):
		hash = locals()
		del hash['self']
		return self.group_createObjects(HostGroup.fromHash(hash))
	
	def group_delete(self, id):
		if not id: id = []
		return self._backend.group_deleteObjects(
				self._backend.group_getObjects(
					id = forceGroupIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_createObjects(self, objectToGroups):
		objectToGroups = forceObjectClassList(objectToGroups, ObjectToGroup)
		for objectToGroup in objectToGroups:
			logger.info(u"Creating %s" % objectToGroup)
			if self._backend.objectToGroup_getObjects(
					groupId = objectToGroup.groupId,
					objectId = objectToGroup.objectId):
				logger.info(u"%s already exists, updating" % objectToGroup)
				self._backend.objectToGroup_updateObject(objectToGroup)
			else:
				self._backend.objectToGroup_insertObject(objectToGroup)
	
	def objectToGroup_updateObjects(self, objectToGroups):
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			self._backend.objectToGroup_updateObject(objectToGroup)
	
	def objectToGroup_create(self, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ObjectToGroup.fromHash(hash))
	
	def objectToGroup_delete(self, groupId, objectId):
		if not groupId:  groupId  = []
		if not objectId: objectId = []
		return self._backend.objectToGroup_deleteObjects(
				self._backend.objectToGroup_getObjects(
					groupId = forceGroupIdList(groupId),
					objectId = forceObjectIdList(objectId)))
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_createObjects(self, licenseContracts):
		licenseContracts = forceObjectClassList(licenseContracts, LicenseContract)
		for licenseContract in licenseContracts:
			logger.info(u"Creating licenseContract '%s'" % licenseContract)
			if self._backend.licenseContract_getObjects(id = licenseContract.id):
				logger.info(u"LicenseContract '%s' already exists, updating" % licenseContract)
				self._backend.licenseContract_updateObject(licenseContract)
			else:
				self._backend.licenseContract_insertObject(licenseContract)
	
	def licenseContract_updateObjects(self, licenseContracts):
		for licenseContract in forceObjectClassList(licenseContracts, LicenseContract):
			self._backend.licenseContract_updateObject(licenseContract)
	
	def licenseContract_create(self, id, description=None, notes=None, partner=None, conclusionDate=None, notificationDate=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.licenseContract_createObjects(LicenseContract.fromHash(hash))
	
	def licenseContract_delete(self, id):
		if not id: id = []
		return self._backend.licenseContract_deleteObjects(
				self._backend.licenseContract_getObjects(
					id = forceLicenseContractIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_createObjects(self, softwareLicenses):
		softwareLicenses = forceObjectClassList(softwareLicenses, SoftwareLicense)
		for softwareLicense in softwareLicenses:
			logger.info(u"Creating softwareLicense '%s'" % softwareLicense)
			if self._backend.softwareLicense_getObjects(id = softwareLicense.id):
				logger.info(u"SoftwareLicense '%s' already exists, updating" % softwareLicense)
				self._backend.softwareLicense_updateObject(softwareLicense)
			else:
				self._backend.softwareLicense_insertObject(softwareLicense)
	
	def softwareLicense_updateObjects(self, softwareLicenses):
		for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense):
			self._backend.softwareLicense_updateObject(softwareLicense)
	
	def softwareLicense_createRetail(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.softwareLicense_createObjects(RetailSoftwareLicense.fromHash(hash))
	
	def softwareLicense_createOEM(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.softwareLicense_createObjects(OEMSoftwareLicense.fromHash(hash))
	
	def softwareLicense_createVolume(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.softwareLicense_createObjects(VolumeSoftwareLicense.fromHash(hash))
	
	def softwareLicense_createConcurrent(self, id, licenseContractId, maxInstallations=None, boundToHost=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.softwareLicense_createObjects(ConcurrentSoftwareLicense.fromHash(hash))
	
	def softwareLicense_delete(self, id):
		if not id: id = []
		return self._backend.softwareLicense_deleteObjects(
				self._backend.softwareLicense_getObjects(
					id = forceSoftwareLicenseIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePool                                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_createObjects(self, licensePools):
		licensePools = forceObjectClassList(licensePools, LicensePool)
		for licensePool in licensePools:
			logger.info(u"Creating licensePool '%s'" % licensePool)
			if self._backend.licensePool_getObjects(id = licensePool.id):
				logger.info(u"LicensePool '%s' already exists, updating" % licensePool)
				self._backend.licensePool_updateObject(licensePool)
			else:
				self._backend.licensePool_insertObject(licensePool)
	
	def licensePool_updateObjects(self, licensePools):
		for licensePool in forceObjectClassList(licensePools, LicensePool):
			self._backend.softwareLicense_updateObject(licensePool)
	
	def licensePool_create(self, id, description=None, productIds=None, windowsSoftwareIds=None):
		hash = locals()
		del hash['self']
		return self.licensePool_createObjects(LicensePool.fromHash(hash))
	
	def licensePool_delete(self, id):
		if not id: id = []
		return self._backend.licensePool_deleteObjects(
				self._backend.licensePool_getObjects(
					id = forceLicensePoolIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_createObjects(self, softwareLicenseToLicensePools):
		softwareLicenseToLicensePools = forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool)
		for softwareLicenseToLicensePool in softwareLicenseToLicensePools:
			logger.info(u"Creating %s" % softwareLicenseToLicensePool)
			if self._backend.softwareLicenseToLicensePool_getObjects(
					softwareLicenseId = softwareLicenseToLicensePool.softwareLicenseId,
					licensePoolId     = softwareLicenseToLicensePool.licensePoolId):
				logger.info(u"%s already exists, updating" % softwareLicenseToLicensePool)
				self._backend.softwareLicenseToLicensePool_updateObject(softwareLicenseToLicensePool)
			else:
				self._backend.softwareLicenseToLicensePool_insertObject(softwareLicenseToLicensePool)
	
	def softwareLicenseToLicensePool_updateObjects(self, softwareLicenseToLicensePools):
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			self._backend.softwareLicenseToLicensePool_updateObject(softwareLicenseToLicensePool)
	
	def softwareLicenseToLicensePool_create(self, softwareLicenseId, licensePoolId, licenseKey=None):
		hash = locals()
		del hash['self']
		return self.softwareLicenseToLicensePool_createObjects(SoftwareLicenseToLicensePool.fromHash(hash))
	
	def softwareLicenseToLicensePool_delete(self, softwareLicenseId, licensePoolId):
		if not softwareLicenseId: softwareLicenseId  = []
		if not licensePoolId:     licensePoolId = []
		return self._backend.softwareLicenseToLicensePool_deleteObjects(
				self._backend.softwareLicenseToLicensePool_getObjects(
					softwareLicenseId = forceSoftwareLicenseIdList(softwareLicenseId),
					licensePoolId     = forceLicensePoolIdList(licensePoolId)))
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_createObjects(self, licenseOnClients):
		licenseOnClients = forceObjectClassList(licenseOnClients, LicenseOnClient)
		for licenseOnClient in licenseOnClients:
			logger.info(u"Creating %s" % licenseOnClient)
			if self._backend.licenseOnClient_getObjects(
					softwareLicenseId = licenseOnClient.softwareLicenseId,
					licensePoolId     = licenseOnClient.licensePoolId,
					clientId          = licenseOnClient.clientId):
				logger.info(u"%s already exists, updating" % licenseOnClient)
				self._backend.licenseOnClient_updateObject(licenseOnClient)
			else:
				self._backend.licenseOnClient_insertObject(licenseOnClient)
	
	def licenseOnClient_updateObjects(self, licenseOnClients):
		for licenseOnClient in forceObjectClassList(licenseOnClients, LicenseOnClient):
			self._backend.licenseOnClient_updateObject(licenseOnClient)
	
	def licenseOnClient_create(self, softwareLicenseId, licensePoolId, clientId, licenseKey=None, notes=None):
		hash = locals()
		del hash['self']
		return self.licenseOnClient_createObjects(LicenseOnClient.fromHash(hash))
	
	def licenseOnClient_delete(self, softwareLicenseId, licensePoolId, clientId):
		if not softwareLicenseId: softwareLicenseId  = []
		if not licensePoolId:     licensePoolId = []
		if not clientId:          clientId = []
		return self._backend.licenseOnClient_deleteObjects(
				self._backend.licenseOnClient_getObjects(
					softwareLicenseId = forceSoftwareLicenseIdList(softwareLicenseId),
					licensePoolId     = forceLicensePoolIdList(licensePoolId),
					clientId          = forceHostIdList(clientId)))
	


















