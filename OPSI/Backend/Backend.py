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
import types, new, inspect, socket
import copy as pycopy

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.System import getDiskSpaceUsage
from OPSI.Util import md5sum, librsyncSignature, librsyncPatchFile, timestamp, compareVersions
from OPSI.Util.File import ConfigFile
from OPSI.Util.Product import ProductPackageFile

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
	logger.debug2(u"Arg string is: %s" % argString)
	logger.debug2(u"Call string is: %s" % callString)
	return (argString, callString)


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                        CLASS BACKEND                                               =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class Backend:
	def __init__(self, **kwargs):
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('username'):
				self._username = value
			elif option in ('password'):
				self._password = value
		
	def backend_getInterface(self):
		methods = {}
		for member in inspect.getmembers(self, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# protected / private
				continue
			(args, varargs, keywords, defaults) = inspect.getargspec(member[1])
			#logger.debug2(u"args: %s" % unicode(args))
			#logger.debug2(u"varargs: %s" % unicode(varargs))
			#logger.debug2(u"keywords: %s" % unicode(keywords))
			#logger.debug2(u"defaults: %s" % unicode(defaults))
			params = []
			if args:
				for arg in forceList(args):
					if (arg != 'self'):
						params.append(arg)
			if ( defaults != None and len(defaults) > 0 ):
				offset = len(params) - len(defaults)
				for i in range(len(defaults)):
					params[offset+i] = '*' + params[offset+i]
			
			if varargs:
				for arg in forceList(varargs):
					params.append('*' + arg)
			
			if keywords:
				for arg in forceList(keywords):
					params.append('**' + arg)
			
			logger.debug2(u"Interface method name '%s' params %s" % (methodName, params))
			methods[methodName] = { 'name': methodName, 'params': params, 'args': args, 'varargs': varargs, 'keywords': keywords, 'defaults': defaults}
		
		methodList = []
		methodNames = methods.keys()
		methodNames.sort()
		for methodName in methodNames:
			methodList.append(methods[methodName])
		return methodList
	
	def backend_setOptions(self):
		pass
	
	def backend_getOptions(self, options):
		return {}
	
	def backend_exit(self):
		pass


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                    CLASS EXTENDEDBACKEND                                           =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ExtendedBackend(Backend):
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
			setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
		
	def _executeMethod(self, methodName, **kwargs):
		return eval(u'self._backend.%s(**kwargs)' % methodName)
	
	def backend_exit(self):
		logger.debug(u"Calling backend_exit() on backend %s" % self._backend)
		self._backend.backend_exit()
	
	def backend_setOptions(self, options):
		self._backend.backend_setOptions(options)
	
	def backend_getOptions(self):
		return self._backend.backend_getOptions()
	

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                  CLASS BACKENDIDENTEXTENSION                                        =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
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
	
	def softwareLicenseToLicensePool_getIdents(self, returnType='unicode', **filter):
		result = []
		for softwareLicenseToLicensePool in self.softwareLicenseToLicensePool_getObjects(attributes = ['softwareLicenseId', 'licensePoolId'], **filter):
			result.append(softwareLicenseToLicensePool.getIdent(returnType))
		return result
	
	def licenseOnClient_getIdents(self, returnType='unicode', **filter):
		result = []
		for licenseOnClient in self.licenseOnClient_getObjects(attributes = ['softwareLicenseId', 'licensePoolId', 'clientId'], **filter):
			result.append(licenseOnClient.getIdent(returnType))
		return result
	
	def auditSoftware_getIdents(self, returnType='unicode', **filter):
		result = []
		for auditSoftware in self.auditSoftware_getObjects(attributes = ['name', 'version', 'subVersion', 'language', 'architecture'], **filter):
			result.append(auditSoftware.getIdent(returnType))
		return result
	
	def auditSoftwareOnClient_getIdents(self, returnType='unicode', **filter):
		result = []
		for auditSoftwareOnClient in self.auditSoftwareOnClient_getObjects(attributes = ['name', 'version', 'subVersion', 'language', 'architecture', 'clientId'], **filter):
			result.append(auditSoftwareOnClient.getIdent(returnType))
		return result
	
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                   CLASS CONFIGDATABACKEND                                          =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ConfigDataBackend(BackendIdentExtension):
	
	def __init__(self, **kwargs):
		Backend.__init__(self, **kwargs)
		self._auditHardwareConfigFile       = u'/etc/opsi/hwaudit/opsihwaudit.conf'
		self._auditHardwareConfigLocalesDir = u'/etc/opsi/hwaudit/locales'
		
	def _testFilterAndAttributes(self, Class, attributes, **filter):
		if not attributes:
			attributes = []
		attributes = forceUnicodeList(attributes)
		possibleAttributes = getPossibleClassAttributes(Class)
		for attribute in attributes:
			if not attribute in possibleAttributes:
				raise BackendBadValueError("Class '%s' has not attribute '%s'" % (Class, attribute))
		for attribute in filter.keys():
			if not attribute in possibleAttributes:
				raise BackendBadValueError("Class '%s' has not attribute '%s'" % (Class, attribute))
	
	def backend_createBase(self):
		pass
	
	def backend_deleteBase(self):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		host = forceObjectClass(host, Host)
		host.setDefaults()
	
	def host_updateObject(self, host):
		host = forceObjectClass(host, Host)
		
	def host_getObjects(self, attributes = [], **filter):
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
	
	def config_getObjects(self, attributes = [], **filter):
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
	
	def configState_getObjects(self, attributes = [], **filter):
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
	
	def product_getObjects(self, attributes = [], **filter):
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
		if not self.product_getIdents(
			id = productOnDepot.productId,
			productVersion = productOnDepot.productVersion,
			packageVersion = productOnDepot.packageVersion):
			
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion))
		
	def productOnDepot_updateObject(self, productOnDepot):
		if not self.product_getIdents(
			id = productOnDepot.productId,
			productVersion = productOnDepot.productVersion,
			packageVersion = productOnDepot.packageVersion):
			
			raise BackendReferentialIntegrityError(u"Product with id '%s', productVersion '%s', packageVersion '%s' not found" \
				% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion))
	
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
		if productOnClient.actionRequest not in ('none', None) or productOnClient.installationStatus not in ('not_installed', None):
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
				% (productPropertyState.propertyId, productPropertyState.productId))
	
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
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		auditSoftware = forceObjectClass(auditSoftware, AuditSoftware)
		auditSoftware.setDefaults()
	
	def auditSoftware_updateObject(self, auditSoftware):
		pass
	
	def auditSoftware_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(AuditSoftware, attributes, **filter)
	
	def auditSoftware_deleteObjects(self, auditSoftwares):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		auditSoftwareOnClient = forceObjectClass(auditSoftwareOnClient, AuditSoftwareOnClient)
		auditSoftwareOnClient.setDefaults()
	
	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		pass
	
	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(AuditSoftwareOnClient, attributes, **filter)
	
	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardware_insertObject(self, auditHardware):
		auditHardware = forceObjectClass(auditHardware, AuditHardware)
		auditHardware.setDefaults()
	
	def auditHardware_updateObject(self, auditHardware):
		pass
	
	def auditHardware_getObjects(self, attributes=[], **filter):
		pass
	
	def auditHardware_deleteObjects(self, auditHardwares):
		pass
	
	def auditHardware_getConfig(self, language=None):
		if not language:
			language = 'en_US'
		language = forceLanguageCode(language)
		
		localeFile = os.path.join(self._auditHardwareConfigLocalesDir, language)
		if not os.path.exists(localeFile):
			logger.error(u"No translation file found for language %s, falling back to en_US" % language)
			language = 'en_US'
			localeFile = os.path.join(self._auditHardwareConfigLocalesDir, language)
		
		locale = {}
		try:
			lf = ConfigFile(localeFile)
			for line in lf.parse():
				if (line.count('=') == 0):
					continue
				(k, v) = line.split('=', 1)
				locale[k.strip()] = v.strip()
		except Exception, e:
			logger.error(u"Failed to read translation file for language %s: %s" % (language, e))
		
		def __inheritFromSuperClasses(classes, c, scname=None):
			if not scname:
				for scname in c['Class'].get('Super', []):
					__inheritFromSuperClasses(classes, c, scname)
			else:
				sc = None
				found = False
				for cl in classes:
					if (cl['Class'].get('Opsi') == scname):
						clcopy = pycopy.deepcopy(cl)
						__inheritFromSuperClasses(classes, clcopy)
						newValues = []
						for newValue in clcopy['Values']:
							foundAt = -1
							for i in range(len(c['Values'])):
								if (c['Values'][i]['Opsi'] == newValue['Opsi']):
									if not c['Values'][i].get('UI'):
										c['Values'][i]['UI'] = newValue.get('UI', '')
									foundAt = i
									break
							if (foundAt > -1):
								newValue = c['Values'][foundAt]
								del c['Values'][foundAt]
							newValues.append(newValue)
						found = True
						newValues.extend(c['Values'])
						c['Values'] = newValues
						break
				if not found:
					logger.error(u"Super class '%s' of class '%s' not found!" % (scname, c['Class'].get('Opsi')))
		
		classes = []
		try:
			execfile(self._auditHardwareConfigFile)
			for i in range(len(OPSI_HARDWARE_CLASSES)):
				opsiClass = OPSI_HARDWARE_CLASSES[i]['Class']['Opsi']
				if (OPSI_HARDWARE_CLASSES[i]['Class']['Type'] == 'STRUCTURAL'):
					if locale.get(opsiClass):
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = locale[opsiClass]
					else:
						logger.error(u"No translation for class '%s' found" % opsiClass)
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = opsiClass
				for j in range(len(OPSI_HARDWARE_CLASSES[i]['Values'])):
					opsiProperty = OPSI_HARDWARE_CLASSES[i]['Values'][j]['Opsi']
					if locale.get(opsiClass + '.' + opsiProperty):
						OPSI_HARDWARE_CLASSES[i]['Values'][j]['UI'] = locale[opsiClass + '.' + opsiProperty]
					
			for c in OPSI_HARDWARE_CLASSES:
				try:
					if (c['Class'].get('Type') == 'STRUCTURAL'):
						logger.info(u"Found STRUCTURAL hardware class '%s'" % c['Class'].get('Opsi'))
						ccopy = pycopy.deepcopy(c)
						if ccopy['Class'].has_key('Super'):
							__inheritFromSuperClasses(OPSI_HARDWARE_CLASSES, ccopy)
							del ccopy['Class']['Super']
						del ccopy['Class']['Type']
						
						# Fill up empty display names
						for j in range(len(ccopy.get('Values', []))):
							if not ccopy['Values'][j].get('UI'):
								logger.warning("No translation for property '%s.%s' found" % (ccopy['Class']['Opsi'], ccopy['Values'][j]['Opsi']))
								ccopy['Values'][j]['UI'] = ccopy['Values'][j]['Opsi']
						
						classes.append(ccopy)
				except Exception, e:
					logger.error(u"Error in config file '%s': %s" % (self._auditHardwareConfigFile, e))
		except Exception, e:
			raise Exception(u"Failed to read audit hardware configuration from file '%s': %s" % (self._auditHardwareConfigFile, e))
		
		return classes
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		auditHardwareOnHost = forceObjectClass(auditHardwareOnHost, AuditHardwareOnHost)
		auditHardwareOnHost.setDefaults()
		
	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		pass
	
	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):
		pass
	
	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):
		pass
	
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                               CLASS EXTENDEDCONFIGDATABACKEND                                      =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class ExtendedConfigDataBackend(ExtendedBackend, BackendIdentExtension):
	
	def __init__(self, backend):
		ExtendedBackend.__init__(self, backend)
		self._processProductPriorities = False
		self._processProductDependencies = False
		self._addProductOnClientDefaults = False
		self._deleteConfigStateIfDefault = True
		self._deleteProductPropertyStateIfDefault = True
		self._returnObjectsOnUpdateAndCreate = True
		self._auditHardwareConfig = {}
		
		if hasattr(self._backend, 'auditHardware_getConfig'):
			for config in self._backend.auditHardware_getConfig():
				hwClass = config['Class']['Opsi']
				self._auditHardwareConfig[hwClass] = {}
				for value in config['Values']:
					self._auditHardwareConfig[hwClass][value['Opsi']] = {
						'Type':  value["Type"],
						'Scope': value["Scope"]
					}
		
	def backend_exit(self):
		if self._backend:
			self._backend.backend_exit()
	
	def backend_searchObjects(self, filter):
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
		result = []
		for host in forceObjectClassList(hosts, Host):
			logger.info(u"Creating host '%s'" % host)
			if self.host_getIdents(id = host.id):
				logger.info(u"%s already exists, updating" % host)
				self._backend.host_updateObject(host)
			else:
				self._backend.host_insertObject(host)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.host_getObjects(id = host.id)
				)
		return result
	
	def host_updateObjects(self, hosts):
		result = []
		for host in forceObjectClassList(hosts, Host):
			self._backend.host_updateObject(host)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.host_getObjects(id = host.id)
				)
		return result
	
	def host_createOpsiClient(self, id, opsiHostKey=None, description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, created=None, lastSeen=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiClient.fromHash(hash))
	
	def host_createOpsiDepotserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, networkAddress=None, maxBandwidth=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiDepotserver.fromHash(hash))
	
	def host_createOpsiConfigserver(self, id, opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None, repositoryLocalUrl=None, repositoryRemoteUrl=None,
					description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, networkAddress=None, maxBandwidth=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiConfigserver.fromHash(hash))
	
	def host_delete(self, id):
		if id is None: id = []
		return self._backend.host_deleteObjects(
				self._backend.host_getObjects(
					id = forceHostIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_createObjects(self, configs):
		result = []
		for config in forceObjectClassList(configs, Config):
			logger.info(u"Creating config %s" % config)
			if self._backend.config_getIdents(id = config.id):
				logger.info(u"Config '%s' already exists, updating" % config)
				self._backend.config_updateObject(config)
			else:
				self._backend.config_insertObject(config)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.config_getObjects(id = config.id)
				)
		return result
	
	def config_updateObjects(self, configs):
		result = []
		for config in forceObjectClassList(configs, Config):
			self._backend.config_updateObject(config)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.config_getObjects(id = config.id)
				)
		return result
	
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
		if id is None: id = []
		return self._backend.config_deleteObjects(
				self.config_getObjects(
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
	
	def configState_insertObject(self, configState):
		if self._deleteConfigStateIfDefault:
			configs = self._backend.config_getObjects(attributes = ['defaultValues'], id = configState.configId)
			if configs and not configs[0].defaultValues and (len(configs[0].defaultValues) == len(configState.values)):
				isDefault = True
				for v in configState.values:
					if not v in configs[0].defaultValues:
						isDefault = False
						break
				if isDefault:
					logger.debug(u"Not inserting configState '%s', because it does not differ from defaults" % configState)
					return
		self._backend.configState_insertObject(configState)
	
	def configState_updateObject(self, configState):
		if self._deleteConfigStateIfDefault:
			configs = self._backend.config_getObjects(attributes = ['defaultValues'], id = configState.configId)
			if configs and not configs[0].defaultValues is None and (len(configs[0].defaultValues) == len(configState.values)):
				isDefault = True
				for v in configState.values:
					if not v in configs[0].defaultValues:
						isDefault = False
						break
				if isDefault:
					logger.debug(u"Deleting configState '%s', because it does not differ from defaults" % configState)
					return self._backend.configState_deleteObjects(configState)
		self._backend.configState_updateObject(configState)
	
	def configState_createObjects(self, configStates):
		result = []
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Creating configState %s" % configState)
			if self._backend.configState_getIdents(
					configId   = configState.configId,
					objectId   = configState.objectId):
				logger.info(u"ConfigState '%s' already exists, updating" % configState)
				self.configState_updateObject(configState)
			else:
				self.configState_insertObject(configState)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.configState_getObjects(
						configId   = configState.configId,
						objectId   = configState.objectId
					)
				)
		return result
	
	def configState_updateObjects(self, configStates):
		result = []
		for configState in forceObjectClassList(configStates, ConfigState):
			self._backend.configState_updateObject(configState)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.configState_getObjects(
						configId   = configState.configId,
						objectId   = configState.objectId
					)
				)
		return result
	
	def configState_create(self, configId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.configState_createObjects(ConfigState.fromHash(hash))
	
	def configState_delete(self, configId, objectId):
		if configId is None: configId = []
		if objectId is None: objectId = []
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
		result = []
		for product in forceObjectClassList(products, Product):
			logger.info(u"Creating product %s" % product)
			if self._backend.product_getIdents(
					id             = product.id,
					productVersion = product.productVersion,
					packageVersion = product.packageVersion):
				logger.info(u"Product '%s' already exists, updating" % product)
				self._backend.product_updateObject(product)
			else:
				self._backend.product_insertObject(product)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.product_getObjects(
						id             = product.id,
						productVersion = product.productVersion,
						packageVersion = product.packageVersion
					)
				)
		return result
	
	def product_updateObjects(self, products):
		result = []
		for product in forceObjectClassList(products, Product):
			self._backend.product_updateObject(product)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.product_getObjects(
						id             = product.id,
						productVersion = product.productVersion,
						packageVersion = product.packageVersion
					)
				)
		return result
		
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
		if productId is None: productId = []
		return self._backend.product_deleteObjects(
				product_getObjects(
					productId = forceProductIdList(productId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_createObjects(self, productProperties):
		result = []
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating product property %s" % productProperty)
			if self._backend.productProperty_getIdents(
					productId      = productProperty.productId,
					productVersion = productProperty.productVersion,
					packageVersion = productProperty.packageVersion,
					propertyId     = productProperty.propertyId):
				logger.info(u"Product property '%s' already exists, updating" % productProperty)
				self._backend.productProperty_updateObject(productProperty)
			else:
				self._backend.productProperty_insertObject(productProperty)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productProperty_getObjects(
						productId      = productProperty.productId,
						productVersion = productProperty.productVersion,
						packageVersion = productProperty.packageVersion,
						propertyId     = productProperty.propertyId
					)
				)
		return result
		
	def productProperty_updateObjects(self, productProperties):
		result = []
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			self._backend.productProperty_updateObject(productProperty)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productProperty_getObjects(
						productId      = productProperty.productId,
						productVersion = productProperty.productVersion,
						packageVersion = productProperty.packageVersion,
						propertyId     = productProperty.propertyId
					)
				)
		return result
		
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
		if productId is None:      productId      = []
		if productVersion is None: productVersion = []
		if packageVersion is None: packageVersion = []
		if propertyId is None:     propertyId     = []
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
		result = []
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
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productDependency_getObjects(
						productId         = productDependency.productId,
						productVersion    = productDependency.productVersion,
						packageVersion    = productDependency.packageVersion,
						productAction     = productDependency.productAction,
						requiredProductId = productDependency.requiredProductId
					)
				)
		return result
		
	def productDependency_updateObjects(self, productDependencies):
		result = []
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			self._backend.productDependency_updateObject(productDependency)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productDependency_getObjects(
						productId         = productDependency.productId,
						productVersion    = productDependency.productVersion,
						packageVersion    = productDependency.packageVersion,
						productAction     = productDependency.productAction,
						requiredProductId = productDependency.requiredProductId
					)
				)
		return result
	
	def productDependency_create(self, productId, productVersion, packageVersion, productAction, requiredProductId, requiredProductVersion=None, requiredPackageVersion=None, requiredAction=None, requiredInstallationStatus=None, requirementType=None):
		hash = locals()
		del hash['self']
		return self.productDependency_createObjects(ProductDependency.fromHash(hash))
	
	def productDependency_delete(self, productId, productVersion, packageVersion, productAction, requiredProductId):
		if productId is None:         productId         = []
		if productVersion is None:    productVersion    = []
		if packageVersion is None:    packageVersion    = []
		if productAction is None:     productAction     = []
		if requiredProductId is None: requiredProductId = []
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
		result = []
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		for productOnDepot in productOnDepots:
			logger.info(u"Creating productOnDepot '%s'" % productOnDepot)
			if self._backend.productOnDepot_getIdents(
					productId = productOnDepot.productId,
					depotId   = productOnDepot.depotId):
				logger.info(u"ProductOnDepot '%s' already exists, updating" % productOnDepot)
				self._backend.productOnDepot_updateObject(productOnDepot)
			else:
				self._backend.productOnDepot_insertObject(productOnDepot)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productOnDepot_getObjects(
						productId = productOnDepot.productId,
						depotId   = productOnDepot.depotId
					)
				)
		return result
	
	def productOnDepot_updateObjects(self, productOnDepots):
		result = []
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			self._backend.productOnDepot_updateObject(productOnDepot)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productOnDepot_getObjects(
						productId = productOnDepot.productId,
						depotId   = productOnDepot.depotId
					)
				)
		return result
	
	def productOnDepot_create(self, productId, productType, productVersion, packageVersion, depotId, locked=None):
		hash = locals()
		del hash['self']
		return self.productOnDepot_createObjects(ProductOnDepot.fromHash(hash))
	
	def productOnDepot_delete(self, productId, productVersion, packageVersion, depotId):
		if productId is None:      productId      = []
		if productVersion is None: productVersion = []
		if packageVersion is None: packageVersion = []
		if depotId is None:        depotId        = []
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
		'''
		##### TODO: remove state if product not available on clients depot (dynamic depot selection)
		##### TODO: filters with placeholders
		
		possible attributes/filter-keys of ProductOnClient are:
			productId
			productType
			clientId
			installationStatus
			actionRequest
			actionProgress
			productVersion
			packageVersion
			lastStateChange
		
		missing ProductOnClients will be created with the following defaults:
			installationStatus = u'not_installed'
			actionRequest      = u'none'
			productVersion     = None
			packageVersion     = None
			lastStateChange    = None
		'''
		pocAttributes = attributes
		pocFilter = dict(filter)
		
		defaultMatchesFilter = \
				    (not filter.get('installationStatus') or 'not_installed' in forceList(filter['installationStatus'])) \
				and (not filter.get('actionRequest')      or 'none'          in forceList(filter['actionRequest'])) \
				and (not filter.get('productVersion')     or [ None ] == filter['productVersion']) \
				and (not filter.get('packageVersion')     or [ None ] == filter['packageVersion']) \
				and (not filter.get('lastStateChange')    or [ None ] == filter['lastStateChange'])
		
		if (self._addProductOnClientDefaults and defaultMatchesFilter) or self._processProductDependencies:
			# Do not filter out ProductOnClients on the basis of these attributes in this case
			# If filter is kept unchanged we cannot distinguish between "missing" and "filtered" ProductOnClients
			# We also need to know installationStatus and actionRequest of every product to test if dependencies are fulfilled
			pocFilter = {}
			for (key, value) in filter.items():
				if key in ('installationStatus', 'actionRequest', 'productVersion', 'packageVersion', 'lastStateChange'):
					continue
				pocFilter[key] = value
		
		if self._processProductDependencies and attributes:
			# In this case we definetly need to add the following attributes
			if not 'installationStatus' in pocAttributes: pocAttributes.append('installationStatus')
			if not 'actionRequest'      in pocAttributes: pocAttributes.append('actionRequest')
			if not 'productVersion'     in pocAttributes: pocAttributes.append('productVersion')
			if not 'packageVersion'     in pocAttributes: pocAttributes.append('packageVersion')
		
		# Get product states from backend
		productOnClients = self._backend.productOnClient_getObjects(pocAttributes, **pocFilter)
		logger.debug(u"Got productOnClients")
		
		
		# We need to adjust ProductOnClients if:
		#    * missing ProductOnClients should be generated (addProductOnClientDefaults) and the default matches the filter
		#    * we should sort by priority (processProductPriorities)
		#    * ProductOnClients should be created to achieve product dependencies (processProductDependencies)
			
		if not (self._addProductOnClientDefaults and defaultMatchesFilter) and not self._processProductPriorities and not self._processProductDependencies:
			# No adjustment needed => done!
			return productOnClients
		
		logger.debug(u"Need to adjust productOnClients")
		
		# Get all client ids which match the filter
		clientIds = self._backend.host_getIdents(id = pocFilter.get('clientId'), returnType = 'unicode')
		logger.debug(u"   * got clientIds")
		
		# Get depot to client assignment
		depotToClients = {}
		for clientToDepot in self.configState_getClientToDepotserver(clientIds = clientIds):
			if not depotToClients.has_key(clientToDepot['depotId']):
				depotToClients[clientToDepot['depotId']] = []
			depotToClients[clientToDepot['depotId']].append(clientToDepot['clientId'])
		logger.debug(u"   * got depotToClients")
		
		# Get product on depots which match the filter
		productOnDepots = {}
		for depotId in depotToClients.keys():
			productOnDepots[depotId] = self._backend.productOnDepot_getObjects(
							depotId        = depotId,
							productId      = pocFilter.get('productId'),
							productVersion = pocFilter.get('productVersion'),
							packageVersion = pocFilter.get('packageVersion'))
		logger.debug(u"   * got productOnDepots")
		
		# Create data structure for product states to find missing ones
		pocByClientIdAndProductId = {}
		for clientId in clientIds:
			pocByClientIdAndProductId[clientId] = {}
		for poc in productOnClients:
			pocByClientIdAndProductId[poc.clientId][poc.productId] = poc
		
		logger.debug(u"   * created pocByClientIdAndProductId")
		#for (clientId, pocs) in pocByClientIdAndProductId.items():
		#	for (productId, poc) in pocs.items():
		#		logger.debug2(u"      [%s] %s: %s" % (clientId, productId, poc.toHash()))
		
		# Create missing product states if addProductOnClientDefaults is set
		if self._addProductOnClientDefaults:
			for (depotId, depotClientIds) in depotToClients.items():
				for clientId in depotClientIds:
					for pod in productOnDepots[depotId]:
						if not pocByClientIdAndProductId[clientId].has_key(pod.productId):
							logger.debug(u"      - creating default productOnClient for clientId '%s', productId '%s'" % (clientId, pod.productId))
							poc = ProductOnClient(
									productId          = pod.productId,
									productType        = pod.productType,
									clientId           = clientId,
									installationStatus = u'not_installed',
									actionRequest      = u'none',
							)
							productOnClients.append(poc)
							if self._processProductPriorities or self._processProductDependencies:
								pocByClientIdAndProductId[clientId][pod.productId] = poc
			
			logger.debug(u"   * created productOnClient defaults")
			#for (clientId, pocs) in pocByClientIdAndProductId.items():
			#	for (productId, poc) in pocs.items():
			#		logger.debug2(u"      [%s] %s: %s" % (clientId, productId, poc.toHash()))
		
		
		if not self._processProductPriorities and not self._processProductDependencies:
			# No more adjustments needed => done!
			return productOnClients
		
		logger.debug(u"   * processing product priorities/dependencies")
		adjustedProductOnClients = []
		
		# Process priorities/dependencies depot by depot
		for (depotId, depotClientIds) in depotToClients.items():
			# Get needed product informations (priority, dependencies)
			logger.debug(u"   * depot %s" % depotId)
			depotProducts = {}
			depotDependencies = {}
			depotProductSequence = []
			priorityToProductIds = {}
			for pod in productOnDepots[depotId]:
				for product in self.product_getObjects(
						id             = pod.productId,
						productVersion = pod.productVersion,
						packageVersion = pod.packageVersion):
					depotProducts[pod.productId] = product
				for productDependency in self.productDependency_getObjects(
						productId      = pod.productId,
						productVersion = pod.productVersion,
						packageVersion = pod.packageVersion):
					if not depotDependencies.has_key(pod.productId):
						depotDependencies[pod.productId] = []
					depotDependencies[pod.productId].append(productDependency)
			
			logger.debug(u"      * got product informations for depot %s" % depotId)
			if self._processProductPriorities:
				logger.debug(u"      * Sorting products by priority for depot %s" % depotId)
				for (productId, product) in depotProducts.items():
					if not priorityToProductIds.has_key(product.getPriority()):
						priorityToProductIds[product.getPriority()] = []
					priorityToProductIds[product.getPriority()].append(productId)
				priorities = priorityToProductIds.keys()
				priorities.sort()
				priorities.reverse()
				for priority in priorities:
					depotProductSequence.extend(priorityToProductIds[priority])
				
				logger.debug(u"      * sequence after priority sorting (depot: %s):" % depotId)
				for i in range(len(depotProductSequence)):
					logger.debug(u"        [%2.0f] %s" % (i, depotProductSequence[i]))
			
			for clientId in depotClientIds:
				logger.debug(u"         * client %s" % clientId)
				sequence = list(depotProductSequence)
				
				if self._processProductDependencies:
					logger.debug(u"            - processing dependencies")
					# Add dependent product actions
					def addActionRequest(pocByClientIdAndProductId, clientId, poc, addedInfo):
						logger.debug(u"              checking dependencies for product '%s', action '%s'" % (poc.productId, poc.actionRequest))
						for dependency in depotDependencies.get(poc.productId, []):
							if (dependency.productAction != poc.actionRequest):
								continue
							if not depotProducts.has_key(dependency.requiredProductId):
								logger.warning(u"              dependency to product '%s' defined, which does not exist on depot '%s' ignoring!" \
									% (dependency.requiredProductId, depotId))
								continue
							logger.debug(u"              need to check dependency to product '%s'" % (dependency.requiredProductId))
							requiredAction     = dependency.requiredAction
							installationStatus = 'not_installed'
							actionRequest      = 'none'
							if pocByClientIdAndProductId[clientId].has_key(dependency.requiredProductId):
								installationStatus = pocByClientIdAndProductId[clientId][dependency.requiredProductId].installationStatus
								actionRequest      = pocByClientIdAndProductId[clientId][dependency.requiredProductId].actionRequest
							if not requiredAction:
								if   (dependency.requiredInstallationStatus == installationStatus):
									logger.debug(u"              required installation status '%s' is fulfilled" % dependency.requiredInstallationStatus)
									continue
								elif (dependency.requiredInstallationStatus == 'installed'):
									requiredAction = 'setup'
								elif (dependency.requiredInstallationStatus == 'not_installed'):
									requiredAction = 'uninstall'
							if   (actionRequest == requiredAction):
								logger.debug(u"              required action '%s' is already set" % requiredAction)
								continue
							elif (actionRequest != 'none'):
								logger.error(u"              cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
											% (poc.productId, dependency.requiredProductId, requiredAction, actionRequest))
								continue
								#raise BackendUnaccomplishableError(u"Cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
								#		% (poc.productId, dependency.requiredProductId, requiredAction, productOnClientsByProductId[dependency.requiredProductId].actionRequest))
							logger.debug(u"              need to add action '%s' for product '%s'" % (requiredAction, dependency.requiredProductId))
							if addedInfo.has_key(dependency.requiredProductId):
								logger.warning(u"Product dependency loop detected, skipping")
								continue
							
							if not pocByClientIdAndProductId[clientId].has_key(dependency.requiredProductId):
								pocByClientIdAndProductId[clientId][dependency.requiredProductId] = ProductOnClient(
									productId          = dependency.requiredProductId,
									productType        = depotProducts[requiredProductId].productType,
									clientId           = clientId,
									installationStatus = u'not_installed',
									actionRequest      = u'none',
								)
							addedInfo[dependency.requiredProductId] = {
								'addedForProduct': requiredAction,
								'requiredAction':  requiredAction,
								'requirementType': dependency.requirementType
							}
							pocByClientIdAndProductId[clientId][dependency.requiredProductId].setActionRequest(requiredAction)
							addActionRequest(pocByClientIdAndProductId, clientId, pocByClientIdAndProductId[clientId][dependency.requiredProductId], addedInfo)
					
					addedInfo = {}
					for (productId, poc) in pocByClientIdAndProductId[clientId].items():
						if (poc.actionRequest == 'none') or not depotDependencies.get(poc.productId):
							continue
						addActionRequest(pocByClientIdAndProductId, clientId, poc, addedInfo)
					
					if addedInfo:
						for run in (1, 2):
							for (requiredProductId, info) in addedInfo.items():
								logger.debug(u"              correcting sequence for action '%s', product '%s'" % (info['requiredAction'], requiredProductId))
								(ppos, dpos) = (0, 0)
								for i in range(len(sequence)):
									if   (sequence[i] == info['addedForProduct']):
										ppos = i
									elif (sequence[i] == requiredProductId):
										dpos = i
								if   (info['requirementType'] == 'before') and (ppos < dpos):
									if (run == 2):
										raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
														% (info['addedForProduct'], requiredProductId))
									sequence.remove(requiredProductId)
									sequence.insert(ppos, requiredProductId)
								elif (info['requirementType'] == 'after') and (dpos < ppos):
									if (run == 2):
										raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
														% (info['addedForProduct'], requiredProductId))
									sequence.remove(requiredProductId)
									sequence.insert(ppos+1, requiredProductId)
							
							logger.debug(u"              sequence after dependency sorting run %d (client: %s):" % (run, clientId))
							for i in range(len(sequence)):
								logger.debug(u"                 [%2.0f] %s" % (i, sequence[i]))
				
				for productId in sequence:
					if not pocByClientIdAndProductId[clientId].has_key(productId):
						continue
					actionRequest      = pocByClientIdAndProductId[clientId][productId].actionRequest
					installationStatus = pocByClientIdAndProductId[clientId][productId].installationStatus
					if (not filter.get('installationStatus') or installationStatus in forceList(filter['installationStatus'])) and \
					   (not filter.get('actionRequest')      or actionRequest      in forceList(filter['actionRequest'])):
						logger.debug(u"            - adding results (clientId: '%s', productId: '%s', installationStatus: '%s', actionRequest: '%s')" \
										% (clientId, productId, installationStatus, actionRequest))
						adjustedProductOnClients.append(pocByClientIdAndProductId[clientId][productId])
				
				logger.debug(u"         * client %s processed" % clientId)
			
			logger.debug(u"   * depot %s processed" % depotId)
		
		return adjustedProductOnClients
	
	def _productOnClient_correctData(self, productOnClients):
		newProductOnClients = []
		insertVersions = []
		clientIds = []
		productIds = []
		for productOnClient in productOnClients:
			if not productOnClient.lastStateChange:
				productOnClient.setLastStateChange(timestamp())
			if not productOnClient.clientId in clientIds:
				clientIds.append(productOnClient.clientId)
			if not productOnClient.productId in productIds:
				productIds.append(productOnClient.productId)
			if productOnClient.actionRequest not in ('none', None) or productOnClient.installationStatus not in ('not_installed', None):
				# Should have version info
				if not productOnClient.productVersion or not productOnClient.packageVersion:
					insertVersions.append(productOnClient)
					continue
			else:
				productOnClient.productVersion = None
				productOnClient.packageVersion = None
			newProductOnClients.append(productOnClient)
			
		if insertVersions:
			productOnDepots = {}
			depotIds = []
			clientIdToDepotId = {}
			
			for clientToDepot in self.configState_getClientToDepotserver(clientIds = clientIds):
				if not clientToDepot['depotId'] in depotIds:
					depotIds.append(clientToDepot['depotId'])
				clientIdToDepotId[clientToDepot['clientId']] = clientToDepot['depotId']
			
			for depotId in depotIds:
				productOnDepots[depotId] = {}
				for productOnDepot in self._backend.productOnDepot_getObjects(
								depotId        = depotId,
								productId      = productIds):
					productOnDepots[depotId][productOnDepot.productId] = productOnDepot
			
			for productOnClient in insertVersions:
				productOnClient.setProductVersion( productOnDepots[clientIdToDepotId[productOnClient.clientId]][productOnClient.productId].productVersion )
				productOnClient.setPackageVersion( productOnDepots[clientIdToDepotId[productOnClient.clientId]][productOnClient.productId].packageVersion )
				newProductOnClients.append(productOnClient)
				
		return newProductOnClients
		
	def productOnClient_createObjects(self, productOnClients):
		result = []
		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		productOnClients = self._productOnClient_correctData(productOnClients)
		for productOnClient in productOnClients:
			logger.info(u"Creating productOnClient '%s'" % productOnClient)
			if self._backend.productOnClient_getIdents(
					productId = productOnClient.productId,
					clientId  = productOnClient.clientId):
				logger.info(u"ProductOnClient '%s' already exists, updating" % productOnClient)
				self._backend.productOnClient_updateObject(productOnClient)
			else:
				self._backend.productOnClient_insertObject(productOnClient)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productOnClient_getObjects(
						productId = productOnClient.productId,
						clientId  = productOnClient.clientId
					)
				)
		return result
	
	def productOnClient_updateObjects(self, productOnClients):
		return self.productOnClient_createObjects(productOnClients)
	
	def productOnClient_create(self, productId, productType, clientId, installationStatus=None, actionRequest=None, actionProgress=None, productVersion=None, packageVersion=None, lastStateChange=None):
		hash = locals()
		del hash['self']
		return self.productOnClient_createObjects(ProductOnClient.fromHash(hash))
	
	def productOnClient_delete(self, productId, clientId):
		if productId is None:  productId  = []
		if clientId is None:   clientId   = []
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
		result = []
		productPropertyStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Creating productPropertyState '%s'" % productPropertyState)
			if self._backend.productPropertyState_getIdents(
						productId  = productPropertyState.productId,
						objectId   = productPropertyState.objectId,
						propertyId = productPropertyState.propertyId):
				logger.info(u"ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self._backend.productPropertyState_updateObject(productPropertyState)
			else:
				self._backend.productPropertyState_insertObject(productPropertyState)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productPropertyState_getObjects(
						productId  = productPropertyState.productId,
						objectId   = productPropertyState.objectId,
						propertyId = productPropertyState.propertyId
					)
				)
		return result
	
	def productPropertyState_updateObjects(self, productPropertyStates):
		result = []
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			self._backend.productPropertyState_updateObject(productPropertyState)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.productPropertyState_getObjects(
						productId  = productPropertyState.productId,
						objectId   = productPropertyState.objectId,
						propertyId = productPropertyState.propertyId
					)
				)
		return result
		
	def productPropertyState_create(self, productId, propertyId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))
	
	def productPropertyState_delete(self, productId, propertyId, objectId):
		if productId is None:  productId  = []
		if propertyId is None: propertyId = []
		if objectId is None:   objectId   = []
		return self._backend.productPropertyState_deleteObjects(
				self._backend.productPropertyState_getObjects(
					productId  = forceProductIdList(productId),
					propertyId = forceUnicodeLowerList(propertyId),
					objectId   = forceObjectIdList(objectId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_createObjects(self, groups):
		result = []
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Creating group '%s'" % group)
			if self._backend.group_getIdents(id = group.id):
				logger.info(u"Group '%s' already exists, updating" % group)
				self._backend.group_updateObject(group)
			else:
				self._backend.group_insertObject(group)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.group_getObjects(id = group.id)
				)
		return result
	
	def group_updateObjects(self, groups):
		result = []
		for group in forceObjectClassList(groups, Group):
			self._backend.group_updateObject(group)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.group_getObjects(id = group.id)
				)
		return result
	
	def group_createHostGroup(self, id, description=None, notes=None, parentGroupId=None):
		hash = locals()
		del hash['self']
		return self.group_createObjects(HostGroup.fromHash(hash))
	
	def group_delete(self, id):
		if id is None: id = []
		return self._backend.group_deleteObjects(
				self._backend.group_getObjects(
					id = forceGroupIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_createObjects(self, objectToGroups):
		result = []
		objectToGroups = forceObjectClassList(objectToGroups, ObjectToGroup)
		for objectToGroup in objectToGroups:
			logger.info(u"Creating %s" % objectToGroup)
			if self._backend.objectToGroup_getIdents(
					groupId = objectToGroup.groupId,
					objectId = objectToGroup.objectId):
				logger.info(u"%s already exists, updating" % objectToGroup)
				self._backend.objectToGroup_updateObject(objectToGroup)
			else:
				self._backend.objectToGroup_insertObject(objectToGroup)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.objectToGroup_getObjects(
						groupId  = objectToGroup.groupId,
						objectId = objectToGroup.objectId
					)
				)
		return result
	
	def objectToGroup_updateObjects(self, objectToGroups):
		result = []
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			self._backend.objectToGroup_updateObject(objectToGroup)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.objectToGroup_getObjects(
						groupId  = objectToGroup.groupId,
						objectId = objectToGroup.objectId
					)
				)
		return result
	
	def objectToGroup_create(self, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ObjectToGroup.fromHash(hash))
	
	def objectToGroup_delete(self, groupId, objectId):
		if not groupId:  groupId  = []
		if not objectId: objectId = []
		return self._backend.objectToGroup_deleteObjects(
				self._backend.objectToGroup_getObjects(
					groupId  = forceGroupIdList(groupId),
					objectId = forceObjectIdList(objectId)))
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_createObjects(self, licenseContracts):
		result = []
		licenseContracts = forceObjectClassList(licenseContracts, LicenseContract)
		for licenseContract in licenseContracts:
			logger.info(u"Creating licenseContract '%s'" % licenseContract)
			if self._backend.licenseContract_getIdents(id = licenseContract.id):
				logger.info(u"LicenseContract '%s' already exists, updating" % licenseContract)
				self._backend.licenseContract_updateObject(licenseContract)
			else:
				self._backend.licenseContract_insertObject(licenseContract)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licenseContract_getObjects(id = licenseContract.id)
				)
		return result
		
	def licenseContract_updateObjects(self, licenseContracts):
		result = []
		for licenseContract in forceObjectClassList(licenseContracts, LicenseContract):
			self._backend.licenseContract_updateObject(licenseContract)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licenseContract_getObjects(id = licenseContract.id)
				)
		return result
	
	def licenseContract_create(self, id, description=None, notes=None, partner=None, conclusionDate=None, notificationDate=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.licenseContract_createObjects(LicenseContract.fromHash(hash))
	
	def licenseContract_delete(self, id):
		if id is None: id = []
		return self._backend.licenseContract_deleteObjects(
				self._backend.licenseContract_getObjects(
					id = forceLicenseContractIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_createObjects(self, softwareLicenses):
		result = []
		softwareLicenses = forceObjectClassList(softwareLicenses, SoftwareLicense)
		for softwareLicense in softwareLicenses:
			logger.info(u"Creating softwareLicense '%s'" % softwareLicense)
			if self._backend.softwareLicense_getIdents(id = softwareLicense.id):
				logger.info(u"SoftwareLicense '%s' already exists, updating" % softwareLicense)
				self._backend.softwareLicense_updateObject(softwareLicense)
			else:
				self._backend.softwareLicense_insertObject(softwareLicense)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.softwareLicense_getObjects(id = softwareLicense.id)
				)
		return result
	
	def softwareLicense_updateObjects(self, softwareLicenses):
		result = []
		for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense):
			self._backend.softwareLicense_updateObject(softwareLicense)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.softwareLicense_getObjects(id = softwareLicense.id)
				)
		return result
	
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
		if id is None: id = []
		return self._backend.softwareLicense_deleteObjects(
				self._backend.softwareLicense_getObjects(
					id = forceSoftwareLicenseIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePool                                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_createObjects(self, licensePools):
		result = []
		licensePools = forceObjectClassList(licensePools, LicensePool)
		for licensePool in licensePools:
			logger.info(u"Creating licensePool '%s'" % licensePool)
			if self._backend.licensePool_getIdents(id = licensePool.id):
				logger.info(u"LicensePool '%s' already exists, updating" % licensePool)
				self._backend.licensePool_updateObject(licensePool)
			else:
				self._backend.licensePool_insertObject(licensePool)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licensePool_getObjects(id = licensePool.id)
				)
		return result
	
	def licensePool_updateObjects(self, licensePools):
		result = []
		for licensePool in forceObjectClassList(licensePools, LicensePool):
			self._backend.softwareLicense_updateObject(licensePool)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licensePool_getObjects(id = licensePool.id)
				)
		return result
	
	def licensePool_create(self, id, description=None, productIds=None, windowsSoftwareIds=None):
		hash = locals()
		del hash['self']
		return self.licensePool_createObjects(LicensePool.fromHash(hash))
	
	def licensePool_delete(self, id):
		if id is None: id = []
		return self._backend.licensePool_deleteObjects(
				self._backend.licensePool_getObjects(
					id = forceLicensePoolIdList(id)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_createObjects(self, softwareLicenseToLicensePools):
		result = []
		softwareLicenseToLicensePools = forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool)
		for softwareLicenseToLicensePool in softwareLicenseToLicensePools:
			logger.info(u"Creating %s" % softwareLicenseToLicensePool)
			if self._backend.softwareLicenseToLicensePool_getIdents(
					softwareLicenseId = softwareLicenseToLicensePool.softwareLicenseId,
					licensePoolId     = softwareLicenseToLicensePool.licensePoolId):
				logger.info(u"%s already exists, updating" % softwareLicenseToLicensePool)
				self._backend.softwareLicenseToLicensePool_updateObject(softwareLicenseToLicensePool)
			else:
				self._backend.softwareLicenseToLicensePool_insertObject(softwareLicenseToLicensePool)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.softwareLicenseToLicensePool_getObjects(
						softwareLicenseId = softwareLicenseToLicensePool.softwareLicenseId,
						licensePoolId     = softwareLicenseToLicensePool.licensePoolId
					)
				)
		return result
	
	def softwareLicenseToLicensePool_updateObjects(self, softwareLicenseToLicensePools):
		result = []
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			self._backend.softwareLicenseToLicensePool_updateObject(softwareLicenseToLicensePool)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.softwareLicenseToLicensePool_getObjects(
						softwareLicenseId = softwareLicenseToLicensePool.softwareLicenseId,
						licensePoolId     = softwareLicenseToLicensePool.licensePoolId
					)
				)
		return result
	
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
		result = []
		licenseOnClients = forceObjectClassList(licenseOnClients, LicenseOnClient)
		for licenseOnClient in licenseOnClients:
			logger.info(u"Creating %s" % licenseOnClient)
			if self._backend.licenseOnClient_getIdents(
					softwareLicenseId = licenseOnClient.softwareLicenseId,
					licensePoolId     = licenseOnClient.licensePoolId,
					clientId          = licenseOnClient.clientId):
				logger.info(u"%s already exists, updating" % licenseOnClient)
				self._backend.licenseOnClient_updateObject(licenseOnClient)
			else:
				self._backend.licenseOnClient_insertObject(licenseOnClient)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licenseOnClient_getObjects(
						softwareLicenseId = licenseOnClient.softwareLicenseId,
						licensePoolId     = licenseOnClient.licensePoolId,
						clientId          = licenseOnClient.clientId
					)
				)
		return result
	
	def licenseOnClient_updateObjects(self, licenseOnClients):
		result = []
		for licenseOnClient in forceObjectClassList(licenseOnClients, LicenseOnClient):
			self._backend.licenseOnClient_updateObject(licenseOnClient)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.licenseOnClient_getObjects(
						softwareLicenseId = licenseOnClient.softwareLicenseId,
						licensePoolId     = licenseOnClient.licensePoolId,
						clientId          = licenseOnClient.clientId
					)
				)
		return result
	
	def licenseOnClient_create(self, softwareLicenseId, licensePoolId, clientId, licenseKey=None, notes=None):
		hash = locals()
		del hash['self']
		return self.licenseOnClient_createObjects(LicenseOnClient.fromHash(hash))
	
	def licenseOnClient_delete(self, softwareLicenseId, licensePoolId, clientId):
		if softwareLicenseId is None: softwareLicenseId  = []
		if licensePoolId is None:     licensePoolId = []
		if clientId is None:          clientId = []
		return self._backend.licenseOnClient_deleteObjects(
				self._backend.licenseOnClient_getObjects(
					softwareLicenseId = forceSoftwareLicenseIdList(softwareLicenseId),
					licensePoolId     = forceLicensePoolIdList(licensePoolId),
					clientId          = forceHostIdList(clientId)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_createObjects(self, auditSoftwares):
		result = []
		auditSoftwares = forceObjectClassList(auditSoftwares, AuditSoftware)
		for auditSoftware in auditSoftwares:
			logger.info(u"Creating %s" % auditSoftware)
			if self._backend.auditSoftware_getIdents(
					name           = auditSoftware.name,
					version        = auditSoftware.version,
					subVersion     = auditSoftware.subVersion,
					language       = auditSoftware.language,
					architecture   = auditSoftware.architecture):
				logger.info(u"%s already exists, updating" % auditSoftware)
				self._backend.auditSoftware_updateObject(auditSoftware)
			else:
				self._backend.auditSoftware_insertObject(auditSoftware)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.auditSoftware_getObjects(
						name           = auditSoftware.name,
						version        = auditSoftware.version,
						subVersion     = auditSoftware.subVersion,
						language       = auditSoftware.language,
						architecture   = auditSoftware.architecture
					)
				)
		return result
	
	def auditSoftware_updateObjects(self, auditSoftwares):
		result = []
		for auditSoftware in forceObjectClassList(auditSoftwares, AuditSoftware):
			self._backend.auditSoftware_updateObject(auditSoftware)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.auditSoftware_getObjects(
						name           = auditSoftware.name,
						version        = auditSoftware.version,
						subVersion     = auditSoftware.subVersion,
						language       = auditSoftware.language,
						architecture   = auditSoftware.architecture
					)
				)
		return result
	
	def auditSoftware_create(self, name, version, subVersion, language, architecture, windowsSoftwareId=None, windowsDisplayName=None, windowsDisplayVersion=None, installSize=None):
		hash = locals()
		del hash['self']
		return self.auditSoftware_createObjects(AuditSoftware.fromHash(hash))
	
	def auditSoftware_delete(self, name, version, subVersion, language, architecture):
		if name is None:         name  = []
		if version is None:      version = []
		if subVersion is None:   subVersion = []
		if language is None:     language = []
		if architecture is None: architecture = []
		return self._backend.auditSoftware_deleteObjects(
				self._backend.auditSoftware_getObjects(
					name           = forceUnicodeList(name),
					version        = forceUnicodeLowerList(version),
					subVersion     = forceUnicodeLowerList(subVersion),
					language       = forceLanguageCodeList(language),
					architecture   = forceArchitectureList(architecture)))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_createObjects(self, auditSoftwareOnClients):
		result = []
		auditSoftwareOnClients = forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient)
		for auditSoftwareOnClient in auditSoftwareOnClients:
			logger.info(u"Creating %s" % auditSoftwareOnClient)
			if self._backend.auditSoftwareOnClient_getIdents(
					name           = auditSoftwareOnClient.name,
					version        = auditSoftwareOnClient.version,
					subVersion     = auditSoftwareOnClient.subVersion,
					language       = auditSoftwareOnClient.language,
					architecture   = auditSoftwareOnClient.architecture,
					clientId       = auditSoftwareOnClient.clientId):
				logger.info(u"%s already exists, updating" % auditSoftwareOnClient)
				self._backend.auditSoftwareOnClient_updateObject(auditSoftwareOnClient)
			else:
				self._backend.auditSoftwareOnClient_insertObject(auditSoftwareOnClient)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.auditSoftwareOnClient_getObjects(
						name           = auditSoftwareOnClient.name,
						version        = auditSoftwareOnClient.version,
						subVersion     = auditSoftwareOnClient.subVersion,
						language       = auditSoftwareOnClient.language,
						architecture   = auditSoftwareOnClient.architecture,
						clientId       = auditSoftwareOnClient.clientId
					)
				)
		return result
	
	def auditSoftwareOnClient_updateObjects(self, auditSoftwareOnClients):
		result = []
		for auditSoftwareOnClient in forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient):
			self._backend.auditSoftwareOnClient_updateObject(auditSoftwareOnClient)
			if self._returnObjectsOnUpdateAndCreate:
				result.extend(
					self._backend.auditSoftwareOnClient_getObjects(
						name           = auditSoftwareOnClient.name,
						version        = auditSoftwareOnClient.version,
						subVersion     = auditSoftwareOnClient.subVersion,
						language       = auditSoftwareOnClient.language,
						architecture   = auditSoftwareOnClient.architecture,
						clientId       = auditSoftwareOnClient.clientId
					)
				)
		return result
	
	def auditSoftwareOnClient_create(self, name, version, subVersion, language, architecture, clientId, uninstallString=None, binaryName=None, firstseen=None, lastseen=None, state=None, usageFrequency=None, lastUsed=None):
		hash = locals()
		del hash['self']
		return self.auditSoftwareOnClient_createObjects(AuditSoftwareOnClient.fromHash(hash))
	
	def auditSoftwareOnClient_delete(self, name, version, subVersion, language, architecture, clientId):
		if name is None:         name  = []
		if version is None:      version = []
		if subVersion is None:   subVersion = []
		if language is None:     language = []
		if architecture is None: architecture = []
		if clientId is None:     clientId = []
		return self._backend.auditSoftwareOnClient_deleteObjects(
				self._backend.auditSoftwareOnClient_getObjects(
					name           = forceUnicodeList(name),
					version        = forceUnicodeLowerList(version),
					subVersion     = forceUnicodeLowerList(subVersion),
					language       = forceLanguageCodeList(language),
					architecture   = forceArchitectureList(architecture),
					clientId       = forceHostIdList(clientId)))
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardware_createObjects(self, auditHardwares):
		result = []
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardware)
		for auditHardware in auditHardwares:
			data = auditHardware.toHash()
			if self.auditHardware_getObjects(attributes = [], **data):
				logger.info(u"%s already exists, nothing to do" % auditHardware)
			else:
				self._backend.auditHardware_insertObject(auditHardware)
		return result
	
	def auditHardware_updateObjects(self, auditHardwares):
		result = []
		for auditHardware in forceObjectClassList(auditHardwares, AuditHardware):
			self._backend.auditHardware_updateObject(auditHardware)
		return result
	
	def auditHardware_create(self, hardwareClass, **kwargs):
		hash = locals()
		del hash['self']
		return self.auditHardware_createObjects(AuditHardware.fromHash(hash))
	
	def auditHardware_delete(self, hardwareClass, **kwargs):
		if hardwareClass is None: hardwareClass  = []
		for key in kwargs.keys():
			if kwargs[key] is None: kwargs[key] = []
		
		return self._backend.auditHardware_deleteObjects(
				self._backend.auditHardware_getObjects(
					hardwareClass  = hardwareClass,
					**kwargs ))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardwareOnHost_createObjects(self, auditHardwareOnHosts):
		result = []
		auditHardwareOnHosts = forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost)
		for auditHardwareOnHost in auditHardwareOnHosts:
			filter = { 'hardwareClass': auditHardwareOnHost.getHardwareClass() }
			for attribute in self._auditHardwareConfig[auditHardwareOnHost.getHardwareClass()].keys():
				if not hasattr(auditHardwareOnHost, attribute):
					filter[attribute] = [ None ]
					setattr(auditHardwareOnHost, attribute, None)
				else:
					filter[attribute] = getattr(auditHardwareOnHost, attribute)
			
			if self.auditHardwareOnHost_getObjects(attributes = ['hostId'], **filter):
				logger.info(u"%s already exists, updating" % auditHardwareOnHost)
				auditHardwareOnHost.setLastseen(timestamp())
				auditHardwareOnHost.setState(1)
				self._backend.auditHardwareOnHost_updateObject(auditHardwareOnHost)
			else:
				self._backend.auditHardwareOnHost_insertObject(auditHardwareOnHost)
		return result
		
	def auditHardwareOnHost_updateObjects(self, auditHardwareOnHosts):
		result = []
		for auditHardwareOnHost in forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost):
			self._backend.auditHardwareOnHost_updateObject(auditHardwareOnHost)
		return result
	
	def auditHardwareOnHost_create(self, hostId, hardwareClass, firstseen=None, lastseen=None, state=None, **kwargs):
		hash = locals()
		del hash['self']
		return self.auditHardwareOnHost_createObjects(AuditHardwareOnHost.fromHash(hash))
	
	def auditHardwareOnHost_delete(self, hostId, hardwareClass, firstseen=None, lastseen=None, state=None, **kwargs):
		if hostId is None:        hostId  = []
		if hardwareClass is None: hardwareClass  = []
		if firstseen is None:     firstseen  = []
		if lastseen is None:      lastseen  = []
		if state is None:         state  = []
		for key in kwargs.keys():
			if kwargs[key] is None: kwargs[key] = []
		
		return self._backend.auditHardwareOnHost_deleteObjects(
				self._backend.auditHardwareOnHost_getObjects(
					hostId         = hostId,
					hardwareClass  = hardwareClass,
					firstseen      = firstseen,
					lastseen       = lastseen,
					state          = state,
					**kwargs ))
	
	def auditHardwareOnHost_setObsolete(self, hostId):
		if hostId is None: hostId  = []
		hostId = forceHostIdList(hostId)
		auditHardwareOnHosts = self.auditHardwareOnHost_getObjects(hostId = hostId, state = 1)
		for i in range(len(auditHardwareOnHosts)):
			auditHardwareOnHosts[i].setState(0)
		self.auditHardwareOnHost_updateObjects(auditHardwareOnHosts)
	
	
'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                   CLASS DEPOTSERVERBACKEND                                         =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class DepotserverBackend(ExtendedBackend):
	def __init__(self, backend):
		if not isinstance(backend, ExtendedConfigDataBackend):
			raise Exception("DepotserverBackend needs instance of ExtendedConfigDataBackend as backend, got %s" % backend.__class__.__name__)
		ExtendedBackend.__init__(self, backend)
		
		self._logDir = u'/var/log/opsi'
		self._packageLog = os.path.join(self._logDir, 'package.log')
		self._depotId = forceHostId(socket.getfqdn())
		if not self.host_getIdents(id = self._depotId):
			raise BackendMissingDataError(u"Depot '%s' not found in backend" % self._depotBackend._depotId)
		self._packageManager = DepotserverPackageManager(self)
		
	def backend_exit(self):
		if self._backend:
			self._backend.backend_exit()
	
	def log_write(self, logType, data, objectId=None, append=True):
		logType = forceUnicode(logType)
		data = forceUnicode(data)
		if not objectId:
			objectId = None
		else:
			objectId = forceObjectId(objectId)
		append = forceBool(append)
		
		if logType not in ('bootimage', 'clientconnect', 'instlog', 'opsiconfd'):
			raise BackendBadValueError(u"Unknown log type '%s'" % logType)
		
		if not objectId and logType in ('bootimage', 'clientconnect', 'instlog', 'opsiconfd'):
			raise BackendBadValueError(u"Log type '%s' requires objectId" % logType)
		
		if not os.path.exists( os.path.join(self._logDir, logType) ):
			mkdir(os.path.join(self._logDir, logType), mode=0770)
		
		logFile = os.path.join(self._logDir, logType, objectId + '.log')
		
		f = None
		if append:
			f = codecs.open(logFile, 'a+', 'utf-8', 'replace')
		else:
			f = codecs.open(logFile, 'w', 'utf-8', 'replace')
		f.write(data)
		f.close()
		os.chmod(logFile, 0640)
		
	def log_read(self, logType, objectId=None, maxSize=0):
		logType = forceUnicode(logType)
		if not objectId:
			objectId = None
		else:
			objectId = forceObjectId(objectId)
		maxSize = forceInt(maxSize)
		if logType not in ('bootimage', 'clientconnect', 'instlog', 'opsiconfd'):
			raise BackendBadValueError(u'Unknown log type %s' % type)
		
		if not objectId and logType in ('bootimage', 'clientconnect', 'instlog', 'opsiconfd'):
			raise BackendBadValueError(u"Log type '%s' requires objectId" % type)
		
		logFile = os.path.join(self._logDir, logType, objectId + '.log')
		data = u''
		if not os.path.exists(logFile):
			return data
		logFile = codecs.open(logFile, 'r', 'utf-8', 'replace')
		data = logFile.read()
		logFile.close()
		if maxSize and (len(data) > maxSize):
			start = data.find('\n', len(data)-maxSize)
			if (start == -1):
				start = len(data)-maxSize
			return data[start+1:]
		return data
	
	def depot_getMD5Sum(self, filename):
		try:
			res = md5sum(filename)
			logger.info(u"MD5sum of file '%s' is '%s'" % (filename, res))
			return res
		except Exception, e:
			raise BackendIOError(u"Failed to get md5sum: %s" % e)
	
	def depot_librsyncSignature(self, filename):
		try:
			return librsyncSignature(filename)
		except Exception, e:
			raise BackendIOError(u"Failed to get librsync signature: %s" % e)
	
	def depot_librsyncPatchFile(self, oldfile, deltafile, newfile):
		try:
			return librsyncPatchFile(oldfile, deltafile, newfile)
		except Exception, e:
			raise BackendIOError(u"Failed to patch file: %s" % e)
	
	def depot_getDiskSpaceUsage(self, path):
		if (os.name != 'posix'):
			raise NotImplementedError(u"Not implemented for non-posix os")
		
		try:
			return getDiskSpaceUsage(path)
		except Exception, e:
			raise BackendIOError(u"Failed to get disk space usage: %s" % e)
	
	
	def depot_installPackage(self, filename, force=False, defaultProperties={}, tempDir=None):
		self._packageManager.installPackage(filename, force, defaultProperties, tempDir)
	

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                   CLASS DEPOTSERVERBACKEND                                         =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class DepotserverPackageManager(object):
	def __init__(self, depotBackend):
		self._depotBackend = depotBackend
		logger.setLogFile(self._depotBackend._packageLog, object = self)
		
	def installPackage(self, filename, force=False, defaultProperties={}, tempDir=None):
		depotId = self._depotBackend._depotId
		logger.notice(u"Installing package file '%s' on depot '%s'" % (filename, depotId))
		try:
			filename = forceFilename(filename)
			force = forceBool(force)
			defaultProperties = forceDict(defaultProperties)
			if tempDir:
				tempDir = forceFilename(tempDir)
			else:
				tempDir = None
			
			if not os.path.isfile(filename):
				raise BackendIOError(u"Package file '%s' not found" % filename)
			
			depots = self._depotBackend.host_getObjects(id = depotId)
			if not depots:
				raise BackendMissingDataError(u"Depot '%s' not found in backend" % depotId)
			depot = depots[0]
			
			depotLocalUrl = depot.getDepotLocalUrl()
			if not depotLocalUrl.startswith(u'file:///'):
				raise BackendBadValueError(u"Value '%s' not allowed for depot local url (has to start with 'file:///')" % depotLocalUrl)
			clientDataDir = depotLocalUrl[7:]
			
			ppf = ProductPackageFile(filename, tempDir=tempDir)
			ppf.setClientDataDir(clientDataDir)
			ppf.getMetaData()
			
			productCreated = False
			currentProduct = None
			productOnDepot = None
			product = None
			try:
				product = ppf.packageControlFile.getProduct()
				
				products = self._depotBackend.product_getObjects(
							id             = product.getId(),
							productVersion = product.getProductVersion(),
							packageVersion = product.getPackageVersion() )
				if products:
					currentProduct = products[0]
				
				if not currentProduct:
					logger.notice(u"Creating product in backend")
					self._depotBackend.product_createObjects(product)
					productCreated = True
				
				logger.notice(u"Locking product '%s' on depot '%s'" % (product.getId(), depotId))
				productOnDepots = self._depotBackend.productOnDepot_getObjects(depotId = depotId, productId = product.getId())
				if productOnDepots:
					productOnDepot = productOnDepots[0]
					if productOnDepot.getLocked():
						logger.notice(u"Product currently locked on depot '%s'" % depotId)
						if not force:
							raise BackendTemporaryError(u"Product currently locked on depot '%s'" % depotId)
						logger.warning(u"Installation of locked product forced")
					productOnDepot.setLocked(True)
					self._depotBackend.productOnDepot_updateObject(productOnDepot)
				else:
					productOnDepot = ProductOnDepot(
						productId      = product.getId(),
						productType    = product.getType(),
						productVersion = product.getProductVersion(),
						packageVersion = product.getPackageVersion(),
						depotId        = depotId,
						locked         = True
					)
					self._depotBackend.productOnDepot_createObjects(productOnDepot)
				
				logger.notice(u"Checking package dependencies")
				self.checkDependencies(ppf)
				
				for line in ppf.runPreinst():
					logger.info(u"[preinst] -> %s" % line)
				
				logger.info(u"Deleting product dependencies of product %s" % product)
				self._depotBackend.productDependency_deleteObjects(
					self._depotBackend.productDependency_getObjects(
							productId      = product.getId(),
							productVersion = product.getProductVersion(),
							packageVersion = product.getPackageVersion() ) )
				
				logger.info(u"Deleting product properties of product %s" % product)
				self._depotBackend.productProperty_deleteObjects(
					self._depotBackend.productProperty_getObjects(
							productId      = product.getId(),
							productVersion = product.getProductVersion(),
							packageVersion = product.getPackageVersion() ) )
				
				if ppf.packageControlFile.getIncrementalPackage():
					logger.info(u"Incremental package, not deleting old client-data files")
				else:
					logger.info(u"Deleting old client-data dir")
					ppf.deleteProductClientDataDir()
				
				ppf.extractData()
				ppf.createPackageContentFile()
				ppf.setAccessRights()
				
				if not productCreated:
					logger.notice(u"Creating product in backend")
					self._depotBackend.product_createObjects(product)
					productCreated = True
				logger.notice(u"Creating product dependencies in backend")
				self._depotBackend.productDependency_createObjects(ppf.packageControlFile.getProductDependencies())
				logger.notice(u"Creating product properties in backend")
				self._depotBackend.productProperty_createObjects(ppf.packageControlFile.getProductProperties())
				
				ppf.runPostinst()
				
				ppf.cleanup()
				
				logger.notice(u"Unlocking product '%s' on depot '%s'" % (productOnDepot.getProductId(), depotId))
				productOnDepot.setLocked(False)
				self._depotBackend.productOnDepot_updateObject(productOnDepot)
				
			except Exception:
				if productCreated:
					try:
						if currentProduct:
							self._depotBackend.product_createObjects(currentProduct)
						else:
							self._depotBackend.product_deleteObject(product)
					except Exception, e:
						logger.error(e)
				try:
					ppf.cleanup()
				except Exception, e:
					logger.error(e)
				
				if productOnDepot:
					try:
						productOnDepot.setLocked(False)
						self._depotBackend.productOnDepot_updateObject(productOnDepot)
					except Exception, e:
						logger.error(e)
				raise
			
		except Exception, e:
			logger.logException(e)
			raise BackendError(u"Failed to install package '%s' on depot '%s': %s" % (filename, depotId, e))
		
		
	def checkDependencies(self, productPackageFile):
		for dependency in productPackageFile.packageControlFile.getPackageDependencies():
			productOnDepots = self._depotBackend.productOnDepot_getObjects(depotId = self._depotBackend._depotId, productId = dependency['package'])
			if not productOnDepots:
				raise Exception(u"Dependent package '%s' not installed" % dependency['package'])
			
			if not dependency['version']:
				logger.info(u"Fulfilled product dependency '%s'" % dependency)
				continue
			
			productOnDepot = productOnDepots[0]
			availableVersion = productOnDepot.getProductVersion() + u'-' + productOnDepot.getPackageVersion()
			
			if compareVersions(availableVersion, dependency['condition'], dependency['version']):
				logger.info(u"Fulfilled package dependency %s (available version: %s)" % (dependency, availableVersion))
			else:
				raise Exception(u"Unfulfilled package dependency %s (available version: %s)" % (dependency, availableVersion))
		






















