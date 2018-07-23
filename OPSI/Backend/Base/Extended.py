# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2013-2018 uib GmbH <info@uib.de>

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
Extended backends.

They provide extended functionality.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import collections
import inspect
import os
import random
import types
import warnings

from OPSI.Logger import Logger
from OPSI.Exceptions import *  # this is needed for dynamic loading
from OPSI.Types import *  # this is needed for dynamic loading
from OPSI.Object import *  # this is needed for dynamic loading
from OPSI.Util import timestamp
import OPSI.SharedAlgorithm

from .Backend import Backend

if os.name == 'posix':
	with warnings.catch_warnings():
		warnings.filterwarnings("ignore", category=DeprecationWarning)
		try:
			from ldaptor.protocols import pureldap
			from ldaptor import ldapfilter
		except ImportError:
			from OPSI.ldaptor.protocols import pureldap
			from OPSI.ldaptor import ldapfilter

__all__ = (
	'getArgAndCallString',
	'ExtendedBackend', 'ExtendedConfigDataBackend',
)

logger = Logger()


def getArgAndCallString(method):
	"""
	Inspects `method` to gain information about the method signature.

	:type method: func
	:rtype: (str, str)
	"""
	argString = []
	callString = []
	(args, varargs, varkwargs, argDefaults) = inspect.getargspec(method)

	for element in args:
		if element == 'self':
			continue

		callString.append(u'='.join((element, element)))
		if isinstance(argDefaults, tuple) and (len(argDefaults) + args.index(element) >= len(args)):
			default = argDefaults[len(argDefaults) - len(args) + args.index(element)]
			if isinstance(default, str):
				default = u"'{0}'".format(default)
			elif isinstance(default, bytes):
				default = u"b'{0}'".format(default)

			argString.append(u'='.join((element, str(default))))
		else:
			argString.append(element)

	for (index, element) in enumerate((varargs, varkwargs), start=1):
		if element:
			toAdd = '{0}{1}'.format(index * u'*', element)
			argString.append(toAdd)
			callString.append(toAdd)

	return (u', '.join(argString), u', '.join(callString))


class ExtendedBackend(Backend):
	"""
	Extending an backend with additional functionality.
	"""
	def __init__(self, backend, overwrite=True):
		"""
		Constructor.

		:param backend: Instance of the backend to extend.
		:param overwrite: Overwriting the public methods of the backend.
		"""
		Backend.__init__(self)
		self._backend = backend
		if self._context is self:
			logger.info(u"Setting context to backend %s" % self._context)
			self._context = self._backend
		self._overwrite = forceBool(overwrite)
		self._createInstanceMethods()

	def _createInstanceMethods(self):
		logger.debug(u"%s is creating instance methods" % self.__class__.__name__)
		for methodName, functionRef in inspect.getmembers(self._backend, inspect.isfunction):
			if methodName.startswith('_'):
				# Not a public method
				continue

			logger.debug2(u"Found public {0} method {1!r}", self._backend.__class__.__name__, methodName)
			if hasattr(self, methodName):
				if self._overwrite:
					logger.debug(u"%s: overwriting method %s of backend instance %s" % (self.__class__.__name__, methodName, self._backend))
					continue
				else:
					logger.debug(u"%s: not overwriting method %s of backend instance %s" % (self.__class__.__name__, methodName, self._backend))

			argString, callString = getArgAndCallString(functionRef)

			exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))
			setattr(self, methodName, types.MethodType(eval(methodName), self))

	def _executeMethod(self, methodName, **kwargs):
		logger.debug(u"ExtendedBackend {0!r}: executing {1!r} on backend {2!r}", self, methodName, self._backend)
		meth = getattr(self._backend, methodName)
		return meth(**kwargs)

	def backend_info(self):
		if self._backend:
			return self._backend.backend_info()
		return Backend.backend_info(self)

	def backend_setOptions(self, options):
		"""
		Set options on ``self`` and the extended backend.

		:type options: dict
		"""
		Backend.backend_setOptions(self, options)
		if self._backend:
			self._backend.backend_setOptions(options)

	def backend_getOptions(self):
		"""
		Get options from the current and the extended backend.

		:rtype: dict
		"""
		options = Backend.backend_getOptions(self)
		if self._backend:
			options.update(self._backend.backend_getOptions())
		return options

	def backend_exit(self):
		if self._backend:
			logger.debug(u"Calling backend_exit() on backend %s" % self._backend)
			self._backend.backend_exit()


class ExtendedConfigDataBackend(ExtendedBackend):

	def __init__(self, configDataBackend, overwrite=True):
		ExtendedBackend.__init__(self, configDataBackend, overwrite=overwrite)
		self._options = {
			'addProductOnClientDefaults': False,
			'addProductPropertyStateDefaults': False,
			'addConfigStateDefaults': False,
			'deleteConfigStateIfDefault': False,
			'returnObjectsOnUpdateAndCreate': False,
			'addDependentProductOnClients': False,
			'processProductOnClientSequence': False
		}
		self._auditHardwareConfig = {}

		if hasattr(self._backend, 'auditHardware_getConfig'):
			ahwconf = self._backend.auditHardware_getConfig()
			AuditHardware.setHardwareConfig(ahwconf)
			AuditHardwareOnHost.setHardwareConfig(ahwconf)
			for config in ahwconf:
				hwClass = config['Class']['Opsi']
				self._auditHardwareConfig[hwClass] = {}
				for value in config['Values']:
					self._auditHardwareConfig[hwClass][value['Opsi']] = {
						'Type': value["Type"],
						'Scope': value["Scope"]
					}

	def __repr__(self):
		return u"<{0}(configDataBackend={1!r})>".format(self.__class__.__name__, self._backend)

	def backend_searchIdents(self, filter):
		logger.info(u"=== Starting search, filter: %s" % filter)
		try:
			parsedFilter = ldapfilter.parseFilter(filter)
		except Exception as e:
			logger.debug(u"Failed to parse filter {0!r}: {1}", filter, e)
			raise BackendBadValueError(u"Failed to parse filter '%s'" % filter)
		logger.debug(u"Parsed search filter: {0!r}", parsedFilter)


		def combineResults(result1, result2, operator):
			if not result1:
				return result2
			if not result2:
				return result1

			result1IdentIndex = -1
			result2IdentIndex = -1

			for i, identAttr in enumerate(result1['identAttributes']):
				for j, identAttr2 in enumerate(result2['identAttributes']):
					if identAttr == identAttr2:
						if (identAttr != 'id') or (result1['objectClass'] == result2['objectClass']):
							result1IdentIndex = i
							result2IdentIndex = j
							break

			if result1IdentIndex == -1:
				logger.debug(u"No matching identAttributes found ({0}, {1})", result1['identAttributes'], result2['identAttributes'])

			if result1IdentIndex == -1:
				if 'id' in result1['identAttributes'] and result1['foreignIdAttributes']:
					logger.debug(u"Trying foreignIdAttributes of result1: {0}", result1['foreignIdAttributes'])
					for attr in result1['foreignIdAttributes']:
						for i, identAttr in enumerate(result2['identAttributes']):
							logger.debug2("%s == %s" % (attr, identAttr))
							if attr == identAttr:
								result2IdentIndex = i
								for a, identAttr2 in enumerate(result1['identAttributes']):
									if identAttr2 == 'id':
										result1IdentIndex = a
								break
				else:
					logger.debug(u"Cannot use foreignIdAttributes of result1")

			if result1IdentIndex == -1:
				if 'id' in result2['identAttributes'] and result2['foreignIdAttributes']:
					logger.debug(u"Trying foreignIdAttributes of result2: {0}", result2['foreignIdAttributes'])
					for attr in result2['foreignIdAttributes']:
						for i, identAttr in enumerate(result1['identAttributes']):
							logger.debug2("%s == %s" % (attr, identAttr))
							if attr == identAttr:
								result1IdentIndex = i
								for a, identAttr2 in enumerate(result2['identAttributes']):
									if identAttr2 == 'id':
										result2IdentIndex = a
								break
				else:
					logger.debug(u"Cannot use foreignIdAttributes of result2")

			if result1IdentIndex == -1:
				raise BackendBadValueError(u"Failed to combine partial results %s(%s | %s) %s(%s | %s)" \
					% (result1['objectClass'], result1['identAttributes'],
						result1['foreignIdAttributes'], result2['objectClass'],
						result2['identAttributes'],
						result2['foreignIdAttributes']))

			logger.info(u"Using attributes %s.%s and %s.%s to combine results (%s)" \
				% (result1['objectClass'],
					result1['identAttributes'][result1IdentIndex],
					result2['objectClass'],
					result2['identAttributes'][result2IdentIndex],
					operator))

			values1 = [value[result1IdentIndex] for value in result1['identValues']]
			values2 = [value[result2IdentIndex] for value in result2['identValues']]

			foreignIdAttributes = result1["foreignIdAttributes"]
			for attr in result2["foreignIdAttributes"]:
				if attr in result1["foreignIdAttributes"]:
					continue
				foreignIdAttributes.append(attr)

			result = {
				"objectClass": result2["objectClass"],
				"foreignIdAttributes": foreignIdAttributes,
				"identAttributes": [result2['identAttributes'][result2IdentIndex]],
				"identValues": []
			}

			if operator == 'OR':
				alreadyAddedValues = set()
				values1.extend(values2)
				for value in values1:
					if value in alreadyAddedValues:
						continue
					alreadyAddedValues.add(value)
					result['identValues'].append([value])
			elif operator == 'AND':
				alreadyAddedValues = set()
				for value in values2:
					if value not in values1 or value in alreadyAddedValues:
						continue
					alreadyAddedValues.add(value)
					result['identValues'].append([value])

			return result

		def handleFilter(f, level=0):
			objectClass = None
			objectFilter = {}
			result = None

			logger.debug(u"Level {0}, processing: {1!r}", level, f)

			if isinstance(f, pureldap.LDAPFilter_equalityMatch):
				logger.debug(u"Handle equality attribute '%s', value '%s'" % (f.attributeDesc.value, f.assertionValue.value))
				if f.attributeDesc.value.lower() == 'objectclass':
					objectClass = f.assertionValue.value
				else:
					objectFilter = {f.attributeDesc.value: f.assertionValue.value}

			elif isinstance(f, pureldap.LDAPFilter_greaterOrEqual):
				logger.debug(u"Handle greaterOrEqual attribute '%s', value '%s'" % (f.attributeDesc.value, f.assertionValue.value))
				objectFilter = {f.attributeDesc.value: u'>=%s' % f.assertionValue.value}

			elif isinstance(f, pureldap.LDAPFilter_lessOrEqual):
				logger.debug(u"Handle lessOrEqual attribute '%s', value '%s'" % (f.attributeDesc.value, f.assertionValue.value))
				objectFilter = {f.attributeDesc.value: u'<=%s' % f.assertionValue.value}

			elif isinstance(f, pureldap.LDAPFilter_substrings):
				logger.debug(u"Handle substrings type %s: %s" % (f.type, repr(f.substrings)))
				if f.type.lower() == 'objectclass':
					raise BackendBadValueError(u"Substring search not allowed for objectClass")
				if isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_initial):
					# string*
					objectFilter = {f.type: '%s*' % f.substrings[0].value}
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_final):
					# *string
					objectFilter = {f.type: '*%s' % f.substrings[0].value}
				elif isinstance(f.substrings[0], pureldap.LDAPFilter_substrings_any):
					# *string*
					objectFilter = {f.type: '*%s*' % f.substrings[0].value}
				else:
					raise BackendBadValueError(u"Unsupported substring class: %s" % repr(f))
			elif isinstance(f, pureldap.LDAPFilter_present):
				objectFilter = {f.value: '*'}

			elif isinstance(f, (pureldap.LDAPFilter_and, pureldap.LDAPFilter_or)):
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
						result = combineResults(result, res, operator)

				if objectFilter or objectClass:
					if objectFilter and not objectClass:
						raise BackendBadValueError(u"Bad search filter '%s': objectClass not defined" % repr(f))

					try:
						oc = eval(objectClass)
						if 'type' not in objectFilter:
							types = [c for c in oc.subClasses]
							types.insert(0, objectClass)

							if len(types) > 1:
								objectFilter['type'] = types

						this = self
						objectFilterNew = {}
						for (key, value) in objectFilter.items():
							if key != 'type':
								try:
									value = eval(value)
								except Exception:
									pass
							objectFilterNew[str(key)] = value
						objectFilter = objectFilterNew

						addProductOnClientDefaults = self._options.get('addProductOnClientDefaults', False)
						addConfigStateDefaults = self._options.get('addConfigStateDefaults', False)
						addProductPropertyStateDefaults = self._options.get('addProductPropertyStateDefaults', False)
						if objectClass == 'ProductOnClient':
							self._options['addProductOnClientDefaults'] = True
						elif objectClass == 'ConfigState':
							self._options['addConfigStateDefaults'] = True
						elif objectClass == 'ProductPropertyState':
							self._options['addProductPropertyStateDefaults'] = True

						logger.debug(u"Executing: this.%s_getIdents(returnType = 'list', %s)" % (getBackendMethodPrefix(oc), objectFilter))
						try:
							res = {
								"objectClass": objectClass,
								"foreignIdAttributes": getForeignIdAttributes(oc),
								"identAttributes": getIdentAttributes(oc),
								"identValues": eval("this.%s_getIdents(returnType='list', **objectFilter)" % getBackendMethodPrefix(oc))
							}
						finally:
							self._options['addProductOnClientDefaults'] = addProductOnClientDefaults
							self._options['addConfigStateDefaults'] = addConfigStateDefaults
							self._options['addProductPropertyStateDefaults'] = addProductPropertyStateDefaults

						if level == 0:
							result = combineResults(result, res, operator)
						else:
							result = res
						logger.debug("Result: {0}", result)
					except Exception as e:
						logger.logException(e)
						raise BackendBadValueError(u"Failed to process search filter '%s': %s" % (repr(f), e))

					objectClass = None
					objectFilter = {}

			elif isinstance(f, pureldap.LDAPFilter_not):
				raise BackendBadValueError(u"Operator '!' not allowed")
			else:
				raise BackendBadValueError(u"Unsupported search filter: %s" % repr(f))

			return (result, objectClass, objectFilter)

		result = [v[0] for v in handleFilter(parsedFilter)[0].get('identValues', [])]
		result.sort()
		logger.info(u"=== Search done, result: %s" % result)
		return result

	def host_getIdents(self, returnType='unicode', **filter):
		return [host.getIdent(returnType) for host in self.host_getObjects(attributes=['id'], **filter)]

	def config_getIdents(self, returnType='unicode', **filter):
		return [config.getIdent(returnType) for config in self.config_getObjects(attributes=['id'], **filter)]

	def configState_getIdents(self, returnType='unicode', **filter):
		return [configState.getIdent(returnType) for configState in self.configState_getObjects(attributes=['configId', 'objectId'], **filter)]

	def product_getIdents(self, returnType='unicode', **filter):
		return [product.getIdent(returnType) for product in self.product_getObjects(attributes=['id'], **filter)]

	def productProperty_getIdents(self, returnType='unicode', **filter):
		return [productProperty.getIdent(returnType) for productProperty
				in self.productProperty_getObjects(
					attributes=['productId', 'productVersion', 'packageVersion', 'propertyId'],
					**filter
				)
		]

	def productDependency_getIdents(self, returnType='unicode', **filter):
		return [productDependency.getIdent(returnType) for productDependency
				in self.productDependency_getObjects(
					attributes=['productId', 'productVersion', 'packageVersion', 'productAction', 'requiredProductId'],
					**filter
				)
		]

	def productOnDepot_getIdents(self, returnType='unicode', **filter):
		return [productOnDepot.getIdent(returnType) for productOnDepot
				in self.productOnDepot_getObjects(
					attributes=['productId', 'productType', 'depotId'],
					**filter
				)
		]

	def productOnClient_getIdents(self, returnType='unicode', **filter):
		return [productOnClient.getIdent(returnType) for productOnClient
				in self.productOnClient_getObjects(
					attributes=['productId', 'productType', 'clientId'],
					**filter
				)
		]

	def productPropertyState_getIdents(self, returnType='unicode', **filter):
		return [productPropertyState.getIdent(returnType) for
				productPropertyState in self.productPropertyState_getObjects(
					attributes=['productId', 'propertyId', 'objectId'],
					**filter
				)
		]

	def group_getIdents(self, returnType='unicode', **filter):
		return [group.getIdent(returnType) for group in
				self.group_getObjects(attributes=['id'], **filter)]

	def objectToGroup_getIdents(self, returnType='unicode', **filter):
		return [objectToGroup.getIdent(returnType) for objectToGroup
				in self.objectToGroup_getObjects(
					attributes=['groupType', 'groupId', 'objectId'],
					**filter
				)
		]

	def licenseContract_getIdents(self, returnType='unicode', **filter):
		return [licenseContract.getIdent(returnType) for licenseContract
				in self.licenseContract_getObjects(attributes=['id'], **filter)]

	def softwareLicense_getIdents(self, returnType='unicode', **filter):
		return [softwareLicense.getIdent(returnType) for softwareLicense
				in self.softwareLicense_getObjects(
					attributes=['id', 'licenseContractId'],
					**filter
				)
		]

	def licensePool_getIdents(self, returnType='unicode', **filter):
		return [licensePool.getIdent(returnType) for licensePool in
				self.licensePool_getObjects(attributes=['id'], **filter)]

	def softwareLicenseToLicensePool_getIdents(self, returnType='unicode', **filter):
		return [softwareLicenseToLicensePool.getIdent(returnType) for
				softwareLicenseToLicensePool in
				self.softwareLicenseToLicensePool_getObjects(
					attributes=['softwareLicenseId', 'licensePoolId'],
					**filter
				)
		]

	def licenseOnClient_getIdents(self, returnType='unicode', **filter):
		return [licenseOnClient.getIdent(returnType) for licenseOnClient
				in self.licenseOnClient_getObjects(
					attributes=['softwareLicenseId', 'licensePoolId', 'clientId'],
					**filter
				)
		]

	def auditSoftware_getIdents(self, returnType='unicode', **filter):
		return [auditSoftware.getIdent(returnType) for auditSoftware in
				self.auditSoftware_getObjects(
					attributes=['name', 'version', 'subVersion', 'language', 'architecture'],
					**filter
				)
		]

	def auditSoftwareToLicensePool_getIdents(self, returnType='unicode', **filter):
		return [auditSoftwareToLicensePool.getIdent(returnType) for
				auditSoftwareToLicensePool in
				self.auditSoftwareToLicensePool_getObjects(
					attributes=['name', 'version', 'subVersion', 'language', 'architecture', 'licensePoolId'],
					**filter
				)
		]

	def auditSoftwareOnClient_getIdents(self, returnType='unicode', **filter):
		return [auditSoftwareOnClient.getIdent(returnType) for
				auditSoftwareOnClient in
				self.auditSoftwareOnClient_getObjects(
					attributes=['name', 'version', 'subVersion', 'language', 'architecture', 'clientId'],
					**filter
				)
		]

	def auditHardware_getIdents(self, returnType='unicode', **filter):
		return [auditHardware.getIdent(returnType) for auditHardware
				in self.auditHardware_getObjects(**filter)]

	def auditHardwareOnHost_getIdents(self, returnType='unicode', **filter):
		return [auditHardwareOnHost.getIdent(returnType) for auditHardwareOnHost
				in self.auditHardwareOnHost_getObjects(**filter)]

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_createObjects(self, hosts):
		forcedHosts = forceObjectClassList(hosts, Host)
		for host in forcedHosts:
			logger.info(u"Creating host '%s'" % host)
			self._backend.host_insertObject(host)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.host_getObjects(id=[host.id for host in forcedHosts])
		else:
			return []

	def host_updateObjects(self, hosts):
		def updateOrInsert(host):
			logger.info(u"Updating host '%s'" % host)
			if self.host_getIdents(id=host.id):
				self._backend.host_updateObject(host)
			else:
				logger.info(u"Host %s does not exist, creating" % host)
				self._backend.host_insertObject(host)

		hostList = forceObjectClassList(hosts, Host)
		for host in hostList:
			updateOrInsert(host)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.host_getObjects(id=[host.id for host in hostList])
		else:
			return []

	def host_renameOpsiClient(self, id, newId):
		id = forceHostId(id)
		newId = forceHostId(newId)

		logger.info(u"Renaming client {0} to {1}...", id, newId)

		clients = self._backend.host_getObjects(type='OpsiClient', id=id)
		try:
			client = clients[0]
		except IndexError:
			raise BackendMissingDataError(u"Cannot rename: client '%s' not found" % id)

		if self._backend.host_getObjects(id=newId):
			raise BackendError(u"Cannot rename: host '%s' already exists" % newId)

		logger.info("Processing group mappings...")
		objectToGroups = []
		for objectToGroup in self._backend.objectToGroup_getObjects(groupType='HostGroup', objectId=client.id):
			objectToGroup.setObjectId(newId)
			objectToGroups.append(objectToGroup)

		logger.info("Processing products on client...")
		productOnClients = []
		for productOnClient in self._backend.productOnClient_getObjects(clientId=client.id):
			productOnClient.setClientId(newId)
			productOnClients.append(productOnClient)

		logger.info("Processing product property states...")
		productPropertyStates = []
		for productPropertyState in self._backend.productPropertyState_getObjects(objectId=client.id):
			productPropertyState.setObjectId(newId)
			productPropertyStates.append(productPropertyState)

		logger.info("Processing config states...")
		configStates = []
		for configState in self._backend.configState_getObjects(objectId=client.id):
			configState.setObjectId(newId)
			configStates.append(configState)

		logger.info("Processing software audit data...")
		auditSoftwareOnClients = []
		for auditSoftwareOnClient in self._backend.auditSoftwareOnClient_getObjects(clientId=client.id):
			auditSoftwareOnClient.setClientId(newId)
			auditSoftwareOnClients.append(auditSoftwareOnClient)

		logger.info("Processing hardware audit data...")
		auditHardwareOnHosts = []
		for auditHardwareOnHost in self._backend.auditHardwareOnHost_getObjects(hostId=client.id):
			auditHardwareOnHost.setHostId(newId)
			auditHardwareOnHosts.append(auditHardwareOnHost)

		logger.info("Processing license data...")
		licenseOnClients = []
		for licenseOnClient in self._backend.licenseOnClient_getObjects(clientId=client.id):
			licenseOnClient.setClientId(newId)
			licenseOnClients.append(licenseOnClient)

		logger.info("Processing software licenses...")
		softwareLicenses = []
		for softwareLicense in self._backend.softwareLicense_getObjects(boundToHost=client.id):
			softwareLicense.setBoundToHost(newId)
			softwareLicenses.append(softwareLicense)

		logger.debug(u"Deleting client {0!r}", client)
		self._backend.host_deleteObjects([client])

		logger.info(u"Updating client {0}...", client.id)
		client.setId(newId)
		self.host_createObjects([client])

		if objectToGroups:
			logger.info(u"Updating group mappings...")
			self.objectToGroup_createObjects(objectToGroups)
		if productOnClients:
			logger.info("Updating products on client...")
			self.productOnClient_createObjects(productOnClients)
		if productPropertyStates:
			logger.info("Updating product property states...")
			self.productPropertyState_createObjects(productPropertyStates)
		if configStates:
			logger.info("Updating config states...")
			self.configState_createObjects(configStates)
		if auditSoftwareOnClients:
			logger.info("Updating software audit data...")
			self.auditSoftwareOnClient_createObjects(auditSoftwareOnClients)
		if auditHardwareOnHosts:
			logger.info("Updating hardware audit data...")
			self.auditHardwareOnHost_createObjects(auditHardwareOnHosts)
		if licenseOnClients:
			logger.info("Updating license data...")
			self.licenseOnClient_createObjects(licenseOnClients)
		if softwareLicenses:
			logger.info("Updating software licenses...")
			self.softwareLicense_createObjects(softwareLicenses)

	def host_renameOpsiDepotserver(self, oldId, newId):
		"""
		Rename OpsiDepotserver with id `oldId` to `newId`.

		References to the old id will be changed aswell.

		:raises BackendMissingDataError: If no depot `oldId` is found.
		:raises BackendError: If depot `newId` already exists.
		:param oldId: ID of the server to change.
		:type oldId: str
		:param oldId: New ID.
		:type newId: str
		"""
		oldId = forceHostId(oldId)
		newId = forceHostId(newId)
		oldHostname = oldId.split('.')[0]
		newHostname = newId.split('.')[0]

		depots = self._backend.host_getObjects(type='OpsiDepotserver', id=oldId)
		try:
			depot = depots[0]
		except IndexError:
			raise BackendMissingDataError(u"Cannot rename: depot '%s' not found" % oldId)

		if self._backend.host_getObjects(id=newId):
			raise BackendError(u"Cannot rename: host '%s' already exists" % newId)

		logger.info("Renaming depot {0} to {1}", oldId, newId)

		logger.info("Processing ProductOnDepots...")
		productOnDepots = []
		for productOnDepot in self._backend.productOnDepot_getObjects(depotId=oldId):
			productOnDepot.setDepotId(newId)
			productOnDepots.append(productOnDepot)

		def replaceServerId(someList):
			"""
			Replaces occurrences of `oldId` with `newId` in `someList`.

			If someList is the wrong type or no change was made `False`
			will be returned.

			:type someList: list
			:returns: `True` if a change was made.
			:rtype: bool
			"""
			try:
				someList.remove(oldId)
				someList.append(newId)
				return True
			except (ValueError, AttributeError):
				return False

		logger.info("Processing ProductProperties...")
		modifiedProductProperties = []
		for productProperty in self._backend.productProperty_getObjects():
			changed = replaceServerId(productProperty.possibleValues)
			changed = replaceServerId(productProperty.defaultValues) or changed

			if changed:
				modifiedProductProperties.append(productProperty)

		if modifiedProductProperties:
			logger.info("Updating ProductProperties...")
			self.productProperty_updateObjects(modifiedProductProperties)

		logger.info("Processing ProductPropertyStates...")
		productPropertyStates = []
		for productPropertyState in self._backend.productPropertyState_getObjects(objectId=oldId):
			productPropertyState.setObjectId(newId)
			replaceServerId(productPropertyState.values)
			productPropertyStates.append(productPropertyState)

		logger.info("Processing Configs...")
		modifiedConfigs = []
		for config in self._backend.config_getObjects():
			changed = replaceServerId(config.possibleValues)
			changed = replaceServerId(config.defaultValues) or changed

			if changed:
				modifiedConfigs.append(config)

		if modifiedConfigs:
			logger.info("Updating Configs...")
			self.config_updateObjects(modifiedConfigs)

		logger.info("Processing ConfigStates...")
		configStates = []
		for configState in self._backend.configState_getObjects(objectId=oldId):
			configState.setObjectId(newId)
			replaceServerId(configState.values)
			configStates.append(configState)

		logger.info(u"Deleting depot {0}", depot)
		self._backend.host_deleteObjects([depot])

		def changeAddress(value):
			newValue = value.replace(oldId, newId)
			newValue = newValue.replace(oldHostname, newHostname)
			logger.debug("Changed {0!r} to {1!r}", value, newValue)
			return newValue

		logger.info("Updating depot and it's urls...")
		depot.setId(newId)
		if depot.repositoryRemoteUrl:
			depot.setRepositoryRemoteUrl(changeAddress(depot.repositoryRemoteUrl))
		if depot.depotRemoteUrl:
			depot.setDepotRemoteUrl(changeAddress(depot.depotRemoteUrl))
		if depot.depotWebdavUrl:
			depot.setDepotWebdavUrl(changeAddress(depot.depotWebdavUrl))
		if depot.workbenchRemoteUrl:
			depot.setWorkbenchRemoteUrl(changeAddress(depot.workbenchRemoteUrl))
		self.host_createObjects([depot])

		if productOnDepots:
			logger.info("Updating ProductOnDepots...")
			self.productOnDepot_createObjects(productOnDepots)
		if productPropertyStates:
			logger.info("Updating ProductPropertyStates...")
			self.productPropertyState_createObjects(productPropertyStates)
		if configStates:
			logger.info("Updating ConfigStates...")
			self.configState_createObjects(configStates)

		def replaceOldAddress(values):
			"""
			Searches for old address in elements of `values` and
			replaces it with the new address.

			:type values: list
			:returns: `True` if an item was changed, `False` otherwise.
			:rtype: bool
			"""
			changed = False
			try:
				for i, value in enumerate(values):
					if oldId in value:
						values[i] = value.replace(oldId, newId)
						changed = True
			except TypeError:  # values probably None
				pass

			return changed

		logger.info("Processing depot assignment configs...")
		updateConfigs = []
		for config in self._backend.config_getObjects(id=['clientconfig.configserver.url', 'clientconfig.depot.id']):
			changed = replaceOldAddress(config.defaultValues)
			changed = replaceOldAddress(config.possibleValues) or changed

			if changed:
				updateConfigs.append(config)

		if updateConfigs:
			logger.info("Processing depot assignment configs...")
			self.config_updateObjects(updateConfigs)

		logger.info("Processing depot assignment config states...")
		updateConfigStates = []
		for configState in self._backend.configState_getObjects(configId=['clientconfig.configserver.url', 'clientconfig.depot.id']):
			if replaceOldAddress(configState.values):
				updateConfigStates.append(configState)

		if updateConfigStates:
			logger.info("Updating depot assignment config states...")
			self.configState_updateObjects(updateConfigStates)

		logger.info("Processing depots...")
		modifiedDepots = []
		for depot in self._backend.host_getObjects(type='OpsiDepotserver'):
			if depot.masterDepotId and (depot.masterDepotId == oldId):
				depot.masterDepotId = newId
				modifiedDepots.append(depot)

		if modifiedDepots:
			logger.info("Updating depots...")
			self.host_updateObjects(modifiedDepots)

	def host_createOpsiClient(self, id, opsiHostKey=None, description=None, notes=None, hardwareAddress=None, ipAddress=None, inventoryNumber=None, oneTimePassword=None, created=None, lastSeen=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiClient.fromHash(hash))

	def host_createOpsiDepotserver(
			self, id,
			opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None,
			depotWebdavUrl=None, repositoryLocalUrl=None,
			repositoryRemoteUrl=None, description=None, notes=None,
			hardwareAddress=None, ipAddress=None, inventoryNumber=None,
			networkAddress=None, maxBandwidth=None, isMasterDepot=None,
			masterDepotId=None, workbenchLocalUrl=None, workbenchRemoteUrl=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiDepotserver.fromHash(hash))

	def host_createOpsiConfigserver(
			self, id,
			opsiHostKey=None, depotLocalUrl=None, depotRemoteUrl=None,
			depotWebdavUrl=None, repositoryLocalUrl=None,
			repositoryRemoteUrl=None, description=None, notes=None,
			hardwareAddress=None, ipAddress=None, inventoryNumber=None,
			networkAddress=None, maxBandwidth=None, isMasterDepot=None,
			masterDepotId=None, workbenchLocalUrl=None, workbenchRemoteUrl=None):
		hash = locals()
		del hash['self']
		return self.host_createObjects(OpsiConfigserver.fromHash(hash))

	def host_delete(self, id):
		if id is None:
			id = []
		return self._backend.host_deleteObjects(self._backend.host_getObjects(id=id))

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_createObjects(self, configs):
		forcedConfigs = forceObjectClassList(configs, Config)
		for config in forcedConfigs:
			logger.info(u"Creating config '{}'", config)
			self._backend.config_insertObject(config)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.config_getObjects(id=[config.id for config in forcedConfigs])
		else:
			return []

	def config_updateObjects(self, configs):
		forcedConfigs = forceObjectClassList(configs, Config)
		for config in forcedConfigs:
			logger.info(u"Updating config %s" % config)
			if self.config_getIdents(id=config.id):
				self._backend.config_updateObject(config)
			else:
				logger.info(u"Config %s does not exist, creating" % config)
				self._backend.config_insertObject(config)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.config_getObjects(id=[config.id for config in forcedConfigs])
		else:
			return []

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
		if id is None:
			id = []
		return self._backend.config_deleteObjects(self.config_getObjects(id=id))

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_getObjects(self, attributes=[], **filter):
		'''
		Add default objects to result for objects which do not exist in backend
		'''
		# objectIds can only be client ids

		# Get config states from backend
		configStates = self._backend.configState_getObjects(attributes, **filter)

		if not self._options['addConfigStateDefaults']:
			return configStates

		# Create data structure for config states to find missing ones
		css = {}
		for cs in self._backend.configState_getObjects(
						attributes=['objectId', 'configId'],
						objectId=filter.get('objectId', []),
						configId=filter.get('configId', [])):

			try:
				css[cs.objectId].append(cs.configId)
			except KeyError:
				css[cs.objectId] = [cs.configId]

		clientIds = self.host_getIdents(id=filter.get('objectId'), returnType='unicode')
		# Create missing config states
		for config in self._backend.config_getObjects(id=filter.get('configId')):
			logger.debug(u"Default values for {0!r}: {1}", config.id, config.defaultValues)
			for clientId in clientIds:
				if config.id not in css.get(clientId, []):
					# Config state does not exist for client => create default
					cf = ConfigState(
						configId=config.id,
						objectId=clientId,
						values=config.defaultValues
					)
					cf.setGeneratedDefault(True)
					configStates.append(cf)

		return configStates

	def _configStateMatchesDefault(self, configState):
		isDefault = False
		configs = self._backend.config_getObjects(attributes=['defaultValues'], id=configState.configId)
		if configs and not configs[0].defaultValues and (len(configs[0].defaultValues) == len(configState.values)):
			isDefault = True
			for v in configState.values:
				if v not in configs[0].defaultValues:
					isDefault = False
					break
		return isDefault

	def _configState_checkValid(self, configState):
		if configState.configId == 'clientconfig.depot.id':
			if not configState.values or not configState.values[0]:
				raise ValueError(u"No valid depot id given")
			depotId = forceHostId(configState.values[0])
			if not self.host_getIdents(type='OpsiDepotserver', id=depotId, isMasterDepot=True):
				raise ValueError(u"Depot '%s' does not exist or is not a master depot" % depotId)

	def configState_insertObject(self, configState):
		if self._options['deleteConfigStateIfDefault'] and self._configStateMatchesDefault(configState):
			# Do not insert configStates which match the default
			logger.debug(u"Not inserting configState {0!r}, because it does not differ from defaults", configState)
			return

		configState = forceObjectClass(configState, ConfigState)
		self._configState_checkValid(configState)
		self._backend.configState_insertObject(configState)

	def configState_updateObject(self, configState):
		if self._options['deleteConfigStateIfDefault'] and self._configStateMatchesDefault(configState):
			# Do not update configStates which match the default
			logger.debug(u"Deleting configState {0!r}, because it does not differ from defaults", configState)
			return self._backend.configState_deleteObjects(configState)

		configState = forceObjectClass(configState, ConfigState)
		self._configState_checkValid(configState)
		self._backend.configState_updateObject(configState)

	def configState_createObjects(self, configStates):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Creating configState '%s'" % configState)
			self.configState_insertObject(configState)
			if returnObjects:
				result.extend(
					self._backend.configState_getObjects(
						configId=configState.configId,
						objectId=configState.objectId
					)
				)

		return result

	def configState_updateObjects(self, configStates):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for configState in forceObjectClassList(configStates, ConfigState):
			logger.info(u"Updating configState %s" % configState)
			if self.configState_getIdents(
					configId=configState.configId,
					objectId=configState.objectId):
				self.configState_updateObject(configState)
			else:
				logger.info(u"ConfigState %s does not exist, creating" % configState)
				self.configState_insertObject(configState)

			if returnObjects:
				result.extend(
					self._backend.configState_getObjects(
						configId=configState.configId,
						objectId=configState.objectId
					)
				)

		return result

	def configState_create(self, configId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.configState_createObjects(ConfigState.fromHash(hash))

	def configState_delete(self, configId, objectId):
		if configId is None:
			configId = []
		if objectId is None:
			objectId = []

		return self._backend.configState_deleteObjects(
			self._backend.configState_getObjects(
				configId=configId,
				objectId=objectId
			)
		)

	def configState_getClientToDepotserver(self, depotIds=[], clientIds=[], masterOnly=True, productIds=[]):
		"""
		Get a mapping of client and depots.

		:param depotIds: Limit the search to the specified depot ids. \
If nothing is given all depots are taken into account.
		:type depotIds: [str, ]
		:param clientIds: Limit the search to the specified client ids. \
If nothing is given all depots are taken into account.
		:type clientIds: [str, ]
		:param masterOnly: If this is set to `True` only master depots \
are taken into account.
		:type masterOnly: bool
		:param productIds: Limit the data to the specified products if \
alternative depots are to be taken into account.
		:type productIds: [str,]
		:return: A list of dicts containing the keys `depotId` and \
`clientId` that belong to each other. If alternative depots are taken \
into the IDs of these depots are to be found in the list behind \
`alternativeDepotIds`. The key does always exist but may be empty.
		:returntype: [{"depotId": str, "alternativeDepotIds": [str, ], "clientId": str},]
		"""
		depotIds = forceHostIdList(depotIds)
		productIds = forceProductIdList(productIds)

		depotIds = self.host_getIdents(type='OpsiDepotserver', id=depotIds)
		if not depotIds:
			return []
		depotIds = set(depotIds)

		clientIds = forceHostIdList(clientIds)
		clientIds = self.host_getIdents(type='OpsiClient', id=clientIds)
		if not clientIds:
			return []

		usedDepotIds = set()
		result = []
		addConfigStateDefaults = self.backend_getOptions().get('addConfigStateDefaults', False)
		try:
			logger.debug(u"Calling backend_setOptions on {0}", self)
			self.backend_setOptions({'addConfigStateDefaults': True})
			for configState in self.configState_getObjects(configId=u'clientconfig.depot.id', objectId=clientIds):
				try:
					depotId = configState.values[0]
					if not depotId:
						raise IndexError("Missing value")
				except IndexError:
					logger.error(u"No depot server configured for client {0!r}", configState.objectId)
					continue

				if depotId not in depotIds:
					continue
				usedDepotIds.add(depotId)

				result.append(
					{
						'depotId': depotId,
						'clientId': configState.objectId,
						'alternativeDepotIds': []
					}
				)
		finally:
			self.backend_setOptions({'addConfigStateDefaults': addConfigStateDefaults})

		if forceBool(masterOnly):
			return result

		productOnDepotsByDepotIdAndProductId = {}
		for pod in self.productOnDepot_getObjects(productId=productIds):
			try:
				productOnDepotsByDepotIdAndProductId[pod.depotId][pod.productId] = pod
			except KeyError:
				productOnDepotsByDepotIdAndProductId[pod.depotId] = {pod.productId: pod}

		pHash = {}
		for (depotId, productOnDepotsByProductId) in productOnDepotsByDepotIdAndProductId.items():
			productString = [u'|{0};{1};{2}'.format(
				productId,
				productOnDepotsByProductId[productId].productVersion,
				productOnDepotsByProductId[productId].packageVersion)
				for productId in sorted(productOnDepotsByProductId.keys())]

			pHash[depotId] = u''.join(productString)

		for usedDepotId in usedDepotIds:
			pString = pHash.get(usedDepotId, u'')
			alternativeDepotIds = [depotId for (depotId, ps) in pHash.items() if depotId != usedDepotId and pString == ps]

			for i, element in enumerate(result):
				if element['depotId'] == usedDepotId:
					result[i]['alternativeDepotIds'] = alternativeDepotIds

		return result

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_createObjects(self, products):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for product in forceObjectClassList(products, Product):
			logger.info(u"Creating product %s" % product)
			self._backend.product_insertObject(product)
			if returnObjects:
				result.extend(
					self._backend.product_getObjects(
						id=product.id,
						productVersion=product.productVersion,
						packageVersion=product.packageVersion
					)
				)

		return result

	def product_updateObjects(self, products):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for product in forceObjectClassList(products, Product):
			logger.info(u"Updating product %s" % product)
			if self.product_getIdents(
					id=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion):
				self._backend.product_updateObject(product)
			else:
				logger.info(u"Product %s does not exist, creating" % product)
				self._backend.product_insertObject(product)

			if returnObjects:
				result.extend(
					self._backend.product_getObjects(
						id=product.id,
						productVersion=product.productVersion,
						packageVersion=product.packageVersion
					)
				)

		return result

	def product_createLocalboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, changelog=None, productClassIds=None, windowsSoftwareIds=None):
		hash = locals()
		del hash['self']
		return self.product_createObjects(LocalbootProduct.fromHash(hash))

	def product_createNetboot(self, id, productVersion, packageVersion, name=None, licenseRequired=None,
					setupScript=None, uninstallScript=None, updateScript=None, alwaysScript=None, onceScript=None,
					priority=None, description=None, advice=None, changelog=None, productClassIds=None, windowsSoftwareIds=None,
					pxeConfigTemplate=None):
		hash = locals()
		del hash['self']
		return self.product_createObjects(NetbootProduct.fromHash(hash))

	def product_delete(self, productId, productVersion, packageVersion):
		if productId is None:
			productId = []
		if productVersion is None:
			productVersion = []
		if packageVersion is None:
			packageVersion = []

		return self._backend.product_deleteObjects(
			self._backend.product_getObjects(
				id=productId,
				productVersion=productVersion,
				packageVersion=packageVersion
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def _adjustProductPropertyStates(self, productProperty):
		'''
		A productProperty was created or updated
		check if the current productPropertyStates are valid
		'''
		if productProperty.editable or not productProperty.possibleValues:
			return

		# Check if productPropertyStates are possible
		depotIds = set(
			[
				productOnDepot.depotId
				for productOnDepot in self.productOnDepot_getObjects(
					productId=productProperty.productId,
					productVersion=productProperty.productVersion,
					packageVersion=productProperty.packageVersion
				)
			]
		)

		if not depotIds:
			return

		# Get depot to client assignment
		objectIds = depotIds.union(
			set(
				[
					clientToDepot['clientId'] for clientToDepot
					in self.configState_getClientToDepotserver(
						depotIds=depotIds
					)
				]
			)
		)

		deleteProductPropertyStates = []
		updateProductPropertyStates = []
		for productPropertyState in self.productPropertyState_getObjects(
					objectId=objectIds,
					productId=productProperty.productId,
					propertyId=productProperty.propertyId):

			changed = False
			newValues = []
			for v in productPropertyState.values:
				if v in productProperty.possibleValues:
					newValues.append(v)
					continue

				if productProperty.getType() == 'BoolProductProperty' and forceBool(v) in productProperty.possibleValues:
					newValues.append(forceBool(v))
					changed = True
					continue

				if productProperty.getType() == 'UnicodeProductProperty':
					newValue = None
					for pv in productProperty.possibleValues:
						if forceUnicodeLower(pv) == forceUnicodeLower(v):
							newValue = pv
							break

					if newValue:
						newValues.append(newValue)
						changed = True
						continue

				changed = True

			if changed:
				if not newValues:
					logger.debug(u"Properties changed: marking productPropertyState %s for deletion" % productPropertyState)
					deleteProductPropertyStates.append(productPropertyState)
				else:
					productPropertyState.setValues(newValues)
					logger.debug(u"Properties changed: marking productPropertyState %s for update" % productPropertyState)
					updateProductPropertyStates.append(productPropertyState)

		if deleteProductPropertyStates:
			self.productPropertyState_deleteObjects(deleteProductPropertyStates)
		if updateProductPropertyStates:
			self.productPropertyState_updateObjects(updateProductPropertyStates)

	def productProperty_createObjects(self, productProperties):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating productProperty %s" % productProperty)
			self._backend.productProperty_insertObject(productProperty)

			if returnObjects:
				result.extend(
					self._backend.productProperty_getObjects(
						productId=productProperty.productId,
						productVersion=productProperty.productVersion,
						packageVersion=productProperty.packageVersion,
						propertyId=productProperty.propertyId
					)
				)

		return result

	def productProperty_updateObjects(self, productProperties):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info(u"Creating productProperty %s" % productProperty)
			if self.productProperty_getIdents(
					productId=productProperty.productId,
					productVersion=productProperty.productVersion,
					packageVersion=productProperty.packageVersion,
					propertyId=productProperty.propertyId):
				self._backend.productProperty_updateObject(productProperty)
			else:
				logger.info(u"ProductProperty %s does not exist, creating" % productProperty)
				self._backend.productProperty_insertObject(productProperty)

			if returnObjects:
				result.extend(
					self._backend.productProperty_getObjects(
						productId=productProperty.productId,
						productVersion=productProperty.productVersion,
						packageVersion=productProperty.packageVersion,
						propertyId=productProperty.propertyId
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
		if productId is None:
			productId = []
		if productVersion is None:
			productVersion = []
		if packageVersion is None:
			packageVersion = []
		if propertyId is None:
			propertyId = []

		return self._backend.productProperty_deleteObjects(
			self._backend.productProperty_getObjects(
				productId=productId,
				productVersion=productVersion,
				packageVersion=packageVersion,
				propertyId=propertyId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_createObjects(self, productDependencies):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			logger.info(u"Creating productDependency %s" % productDependency)
			self._backend.productDependency_insertObject(productDependency)

			if returnObjects:
				result.extend(
					self._backend.productDependency_getObjects(
						productId=productDependency.productId,
						productVersion=productDependency.productVersion,
						packageVersion=productDependency.packageVersion,
						productAction=productDependency.productAction,
						requiredProductId=productDependency.requiredProductId
					)
				)

		return result

	def productDependency_updateObjects(self, productDependencies):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			logger.info(u"Updating productDependency %s" % productDependency)
			if self.productDependency_getIdents(
					productId=productDependency.productId,
					productVersion=productDependency.productVersion,
					packageVersion=productDependency.packageVersion,
					productAction=productDependency.productAction,
					requiredProductId=productDependency.requiredProductId):

				self._backend.productDependency_updateObject(productDependency)
			else:
				logger.info(u"ProductDependency %s does not exist, creating" % productDependency)
				self._backend.productDependency_insertObject(productDependency)

			if returnObjects:
				result.extend(
					self._backend.productDependency_getObjects(
						productId=productDependency.productId,
						productVersion=productDependency.productVersion,
						packageVersion=productDependency.packageVersion,
						productAction=productDependency.productAction,
						requiredProductId=productDependency.requiredProductId
					)
				)

		return result

	def productDependency_create(self, productId, productVersion, packageVersion, productAction, requiredProductId, requiredProductVersion=None, requiredPackageVersion=None, requiredAction=None, requiredInstallationStatus=None, requirementType=None):
		hash = locals()
		del hash['self']
		return self.productDependency_createObjects(ProductDependency.fromHash(hash))

	def productDependency_delete(self, productId, productVersion, packageVersion, productAction, requiredProductId):
		if productId is None:
			productId = []
		if productVersion is None:
			productVersion = []
		if packageVersion is None:
			packageVersion = []
		if productAction is None:
			productAction = []
		if requiredProductId is None:
			requiredProductId = []

		return self._backend.productDependency_deleteObjects(
			self._backend.productDependency_getObjects(
				productId=productId,
				productVersion=productVersion,
				packageVersion=packageVersion,
				productAction=productAction,
				requiredProductId=requiredProductId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		'''
		If productOnDepot exits (same productId, same depotId, different version)
		then update existing productOnDepot instead of creating a new one
		'''
		currentProductOnDepots = self._backend.productOnDepot_getObjects(
			productId=productOnDepot.productId,
			depotId=productOnDepot.depotId
		)

		if currentProductOnDepots:
			currentProductOnDepot = currentProductOnDepots[0]
			logger.info(u"Updating productOnDepot %s instead of creating a new one" % currentProductOnDepot)
			currentProductOnDepot.update(productOnDepot)
			self._backend.productOnDepot_insertObject(currentProductOnDepot)
		else:
			self._backend.productOnDepot_insertObject(productOnDepot)

	def productOnDepot_createObjects(self, productOnDepots):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			logger.info(u"Creating productOnDepot %s" % productOnDepot.toHash())
			self.productOnDepot_insertObject(productOnDepot)

			if returnObjects:
				result.extend(
					self._backend.productOnDepot_getObjects(
						productId=productOnDepot.productId,
						depotId=productOnDepot.depotId
					)
				)

		return result

	def productOnDepot_updateObjects(self, productOnDepots):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		for productOnDepot in productOnDepots:
			logger.info(u"Updating productOnDepot '%s'" % productOnDepot)
			if self.productOnDepot_getIdents(
					productId=productOnDepot.productId,
					productType=productOnDepot.productType,
					productVersion=productOnDepot.productVersion,
					packageVersion=productOnDepot.packageVersion,
					depotId=productOnDepot.depotId):
				self._backend.productOnDepot_updateObject(productOnDepot)
			else:
				logger.info(u"ProductOnDepot %s does not exist, creating" % productOnDepot)
				self.productOnDepot_insertObject(productOnDepot)

			if returnObjects:
				result.extend(
					self._backend.productOnDepot_getObjects(
						productId=productOnDepot.productId,
						depotId=productOnDepot.depotId
					)
				)

		return result

	def productOnDepot_create(self, productId, productType, productVersion, packageVersion, depotId, locked=None):
		hash = locals()
		del hash['self']
		return self.productOnDepot_createObjects(ProductOnDepot.fromHash(hash))

	def productOnDepot_deleteObjects(self, productOnDepots):
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		products = {}
		for productOnDepot in productOnDepots:
			if productOnDepot.productId not in products:
				products[productOnDepot.productId] = {}
			if productOnDepot.productVersion not in products[productOnDepot.productId]:
				products[productOnDepot.productId][productOnDepot.productVersion] = []
			if productOnDepot.packageVersion not in products[productOnDepot.productId][productOnDepot.productVersion]:
				products[productOnDepot.productId][productOnDepot.productVersion].append(productOnDepot.packageVersion)

		ret = self._backend.productOnDepot_deleteObjects(productOnDepots)

		if products:
			for (productId, versions) in products.items():
				for (productVersion, packageVersions) in versions.items():
					for packageVersion in packageVersions:
						if not self.productOnDepot_getIdents(
								productId=productId,
								productVersion=productVersion,
								packageVersion=packageVersion):

							# Product not found on any depot
							self._backend.product_deleteObjects(
								self._backend.product_getObjects(
									id=[productId],
									productVersion=[productVersion],
									packageVersion=[packageVersion]
								)
							)

		return ret

	def productOnDepot_delete(self, productId, depotId, productVersion=None, packageVersion=None):
		if productId is None:
			productId = []
		if productVersion is None:
			productVersion = []
		if packageVersion is None:
			packageVersion = []
		if depotId is None:
			depotId = []
		return self._backend.productOnDepot_deleteObjects(
			self._backend.productOnDepot_getObjects(
				productId=productId,
				productVersion=productVersion,
				packageVersion=packageVersion,
				depotId=depotId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def _productOnClient_processWithFunction(self, productOnClients, function):
		productOnClientsByClient = {}
		productIds = set()
		for poc in productOnClients:
			try:
				productOnClientsByClient[poc.getClientId()].append(poc)
			except KeyError:
				productOnClientsByClient[poc.getClientId()] = [poc]

			productIds.add(poc.productId)

		depotToClients = {}
		for clientToDepot in self.configState_getClientToDepotserver(clientIds=(clientId for clientId in productOnClientsByClient)):
			try:
				depotToClients[clientToDepot['depotId']].append(clientToDepot['clientId'])
			except KeyError:
				depotToClients[clientToDepot['depotId']] = [clientToDepot['clientId']]

		productByProductIdAndVersion = collections.defaultdict(lambda: collections.defaultdict(dict))
		for product in self._backend.product_getObjects(id=productIds):
			productByProductIdAndVersion[product.id][product.productVersion][product.packageVersion] = product

		additionalProductIds = []
		productDependenciesByProductIdAndVersion = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))

		def addDependencies(additionalProductIds, productDependency, productDependenciesByProductIdAndVersion):
			productDependenciesByProductIdAndVersion[productDependency.productId][productDependency.productVersion][productDependency.packageVersion].append(productDependency)

			if productDependency.requiredProductId not in productIds and productDependency.requiredProductId not in additionalProductIds:
				additionalProductIds.append(productDependency.requiredProductId)
				for productDependency in self._backend.productDependency_getObjects(productId=productDependency.requiredProductId):
					addDependencies(additionalProductIds, productDependency, productDependenciesByProductIdAndVersion)

		for productDependency in self._backend.productDependency_getObjects(productId=productIds):
			addDependencies(additionalProductIds, productDependency, productDependenciesByProductIdAndVersion)

		if additionalProductIds:
			for product in self._backend.product_getObjects(id=additionalProductIds):
				productByProductIdAndVersion[product.id][product.productVersion][product.packageVersion] = product

			productIds = productIds.union(additionalProductIds)

		productOnClients = []
		for (depotId, clientIds) in depotToClients.items():
			products = set()
			productDependencies = set()

			for productOnDepot in self._backend.productOnDepot_getObjects(depotId=depotId, productId=productIds):
				product = productByProductIdAndVersion[productOnDepot.productId][productOnDepot.productVersion][productOnDepot.packageVersion]
				if product is None:
					raise BackendMissingDataError(u"Product '%s', productVersion '%s', packageVersion '%s' not found"
						% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion))
				products.add(product)

				def addDependencies(product, products, productDependencies, productByProductIdAndVersion, productDependenciesByProductIdAndVersion):
					dependencies = productDependenciesByProductIdAndVersion[product.id][product.productVersion][product.packageVersion]
					for dep in dependencies:
						product = productByProductIdAndVersion[dep.productId][dep.productVersion][dep.packageVersion]
						if product:
							products.add(product)

							if dep not in productDependencies:
								productDependencies.add(dep)
								addDependencies(product, products, productDependencies, productByProductIdAndVersion, productDependenciesByProductIdAndVersion)

				addDependencies(product, products, productDependencies, productByProductIdAndVersion, productDependenciesByProductIdAndVersion)

			for clientId in clientIds:
				try:
					productOnClientsByClient[clientId]
				except KeyError:
					continue

				productOnClients.extend(
					function(
						productOnClients=productOnClientsByClient[clientId],
						availableProducts=products,
						productDependencies=productDependencies
					)
				)

		return productOnClients

	def productOnClient_generateSequence(self, productOnClients):
		configs = self._context.config_getObjects(id="product_sort_algorithm")  # pylint: disable=maybe-no-member
		try:
			defaults = configs[0].getDefaultValues()
		except IndexError:
			defaults = []

		if "algorithm2" in defaults:
			logger.info("Generating productOnClient sequence with algorithm 2")
			generateProductOnClientSequence = OPSI.SharedAlgorithm.generateProductOnClientSequence_algorithm2
		else:
			logger.info("Generating productOnClient sequence with algorithm 1")
			generateProductOnClientSequence = OPSI.SharedAlgorithm.generateProductOnClientSequence_algorithm1

		return self._productOnClient_processWithFunction(productOnClients, generateProductOnClientSequence)

	def productOnClient_addDependencies(self, productOnClients):
		return self._productOnClient_processWithFunction(productOnClients, OPSI.SharedAlgorithm.addDependentProductOnClients)

	def productOnClient_getObjects(self, attributes=[], **filter):
		'''
		possible attributes/filter-keys of ProductOnClient are:
			productId
			productType
			clientId
			targetState
			installationStatus
			actionRequest
			lastAction
			actionProgress
			actionResult
			productVersion
			packageVersion
			modificationTime

		missing ProductOnClients will be created with the following defaults:
			installationStatus = u'not_installed'
			actionRequest      = u'none'
			productVersion     = None
			packageVersion     = None
			modificationTime   = None
			targetState        = None
			lastAction         = None
			actionProgress     = None
			actionResult       = None
		'''

		pocAttributes = attributes
		pocFilter = dict(filter)

		defaultMatchesFilter = \
					(not filter.get('installationStatus') or 'not_installed' in forceList(filter['installationStatus'])) \
				and (not filter.get('actionRequest')      or 'none'          in forceList(filter['actionRequest'])) \
				and (not filter.get('productVersion')     or None            in forceList(filter['productVersion'])) \
				and (not filter.get('packageVersion')     or None            in forceList(filter['packageVersion'])) \
				and (not filter.get('modificationTime')   or None            in forceList(filter['modificationTime'])) \
				and (not filter.get('targetState')        or None            in forceList(filter['targetState'])) \
				and (not filter.get('lastAction')         or None            in forceList(filter['lastAction'])) \
				and (not filter.get('actionProgress')     or None            in forceList(filter['actionProgress'])) \
				and (not filter.get('actionResult')       or None            in forceList(filter['actionResult']))

		if (self._options['addProductOnClientDefaults'] and defaultMatchesFilter) or self._options['processProductOnClientSequence']:
			# Do not filter out ProductOnClients on the basis of these attributes in this case
			# If filter is kept unchanged we cannot distinguish between "missing" and "filtered" ProductOnClients
			# We also need to know installationStatus and actionRequest of every product to create sequence
			unwantedKeys = set((
				'installationStatus', 'actionRequest', 'productVersion',
				'packageVersion', 'modificationTime', 'targetState',
				'lastAction', 'actionProgress', 'actionResult'
			))
			pocFilter = {
				key: value for (key, value) in filter.items()
				if key not in unwantedKeys
			}

		if (self._options['addProductOnClientDefaults'] or self._options['processProductOnClientSequence']) and attributes:
			# In this case we definetly need to add the following attributes
			if 'installationStatus' not in pocAttributes:
				pocAttributes.append('installationStatus')
			if 'actionRequest' not in pocAttributes:
				pocAttributes.append('actionRequest')
			if 'productVersion' not in pocAttributes:
				pocAttributes.append('productVersion')
			if 'packageVersion' not in pocAttributes:
				pocAttributes.append('packageVersion')

		# Get product states from backend
		productOnClients = self._backend.productOnClient_getObjects(pocAttributes, **pocFilter)
		logger.debug(u"Got productOnClients")

		if not (self._options['addProductOnClientDefaults'] and defaultMatchesFilter) and not self._options['processProductOnClientSequence']:
			# No adjustment needed => done!
			return productOnClients

		logger.debug(u"Need to adjust productOnClients")

		# Create missing product states if addProductOnClientDefaults is set
		if self._options['addProductOnClientDefaults']:
			# Get all client ids which match the filter
			clientIds = self.host_getIdents(id=pocFilter.get('clientId'), returnType='unicode')
			logger.debug(u"   * got clientIds")

			# Get depot to client assignment
			depotToClients = {}
			for clientToDepot in self.configState_getClientToDepotserver(clientIds=clientIds):
				if clientToDepot['depotId'] not in depotToClients:
					depotToClients[clientToDepot['depotId']] = []
				depotToClients[clientToDepot['depotId']].append(clientToDepot['clientId'])
			logger.debug(u"   * got depotToClients")

			productOnDepots = {}
			# Get product on depots which match the filter
			for depotId in depotToClients:
				productOnDepots[depotId] = self._backend.productOnDepot_getObjects(
					depotId=depotId,
					productId=pocFilter.get('productId'),
					productType=pocFilter.get('productType'),
					productVersion=pocFilter.get('productVersion'),
					packageVersion=pocFilter.get('packageVersion')
				)

			logger.debug(u"   * got productOnDepots")

			# Create data structure for product states to find missing ones
			pocByClientIdAndProductId = {}
			for clientId in clientIds:
				pocByClientIdAndProductId[clientId] = {}
			for poc in productOnClients:
				pocByClientIdAndProductId[poc.clientId][poc.productId] = poc

			logger.debug(u"   * created pocByClientIdAndProductId")
			# for (clientId, pocs) in pocByClientIdAndProductId.items():
			#   for (productId, poc) in pocs.items():
			#       logger.debug2(u"      [%s] %s: %s" % (clientId, productId, poc.toHash()))

			for (depotId, depotClientIds) in depotToClients.items():
				for clientId in depotClientIds:
					for pod in productOnDepots[depotId]:
						if pod.productId not in pocByClientIdAndProductId[clientId]:
							logger.debug(u"      - creating default productOnClient for clientId '%s', productId '%s'" % (clientId, pod.productId))
							poc = ProductOnClient(
									productId=pod.productId,
									productType=pod.productType,
									clientId=clientId,
									installationStatus=u'not_installed',
									actionRequest=u'none',
							)
							poc.setGeneratedDefault(True)
							productOnClients.append(poc)

			logger.debug(u"   * created productOnClient defaults")
			# for (clientId, pocs) in pocByClientIdAndProductId.items():
			#   for (productId, poc) in pocs.items():
			#       logger.debug2(u"      [%s] %s: %s" % (clientId, productId, poc.toHash()))

		if not self._options['addProductOnClientDefaults'] and not self._options['processProductOnClientSequence']:
			return productOnClients

		if self._options['processProductOnClientSequence']:
			logger.debug(u"   * generating productOnClient sequence")
			productOnClients = self.productOnClient_generateSequence(productOnClients)

		return [productOnClient for productOnClient in productOnClients if
				self._objectHashMatches(productOnClient.toHash(), **filter)]

	def _productOnClientUpdateOrCreate(self, productOnClient, update=False):
		nextProductOnClient = None
		currentProductOnClients = self._backend.productOnClient_getObjects(
			productId=productOnClient.productId,
			clientId=productOnClient.clientId
		)
		if currentProductOnClients:
			# If productOnClient exists
			# (same productId, same clientId, different version)
			# then update the existing instead of creating a new one
			nextProductOnClient = currentProductOnClients[0].clone()
			if update:
				nextProductOnClient.update(productOnClient, updateWithNoneValues=False)
			else:
				logger.info(u"Updating productOnClient %s instead of creating a new one" % nextProductOnClient)
				nextProductOnClient.update(productOnClient, updateWithNoneValues=True)
		else:
			nextProductOnClient = productOnClient.clone()

		if nextProductOnClient.installationStatus:
			if nextProductOnClient.installationStatus == 'installed':
				# TODO: Check if product exists?
				if not nextProductOnClient.productVersion or not nextProductOnClient.packageVersion:
					clientToDepots = self.configState_getClientToDepotserver(clientIds=[nextProductOnClient.clientId])
					if not clientToDepots:
						raise BackendError(u"Cannot set productInstallationStatus 'installed' for product '%s' on client '%s': product/package version not set and depot for client not found" \
									% (nextProductOnClient.productId, nextProductOnClient.clientId))

					productOnDepots = self._backend.productOnDepot_getObjects(
						depotId=clientToDepots[0]['depotId'],
						productId=nextProductOnClient.productId
					)
					if not productOnDepots:
						raise BackendError(u"Cannot set productInstallationStatus 'installed' for product '%s' on client '%s': product/package version not set and product not found on depot '%s'" \
									% (nextProductOnClient.productId, nextProductOnClient.clientId, clientToDepots[0]['depotId']))
					nextProductOnClient.setProductVersion(productOnDepots[0].productVersion)
					nextProductOnClient.setPackageVersion(productOnDepots[0].packageVersion)
			else:
				nextProductOnClient.productVersion = None
				nextProductOnClient.packageVersion = None

		nextProductOnClient.setModificationTime(timestamp())

		return self._backend.productOnClient_insertObject(nextProductOnClient)

	def productOnClient_insertObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		return self._productOnClientUpdateOrCreate(productOnClient, update=False)

	def productOnClient_updateObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		return self._productOnClientUpdateOrCreate(productOnClient, update=True)

	def productOnClient_createObjects(self, productOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']
		result = []

		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		if self._options['addDependentProductOnClients']:
			productOnClients = self.productOnClient_addDependencies(productOnClients)

		for productOnClient in productOnClients:
			logger.info(u"Creating productOnClient %s" % productOnClient)
			self.productOnClient_insertObject(productOnClient)

			if returnObjects:
				result.extend(
					self._backend.productOnClient_getObjects(
						productId=productOnClient.productId,
						clientId=productOnClient.clientId
					)
				)

		return result

	def productOnClient_updateObjects(self, productOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']
		result = []

		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		if self._options['addDependentProductOnClients']:
			productOnClients = self.productOnClient_addDependencies(productOnClients)

		for productOnClient in productOnClients:
			logger.info(u"Updating productOnClient {0!r}".format(productOnClient))
			if self.productOnClient_getIdents(
					productId=productOnClient.productId,
					productType=productOnClient.productType,
					clientId=productOnClient.clientId):
				logger.info(u"ProductOnClient %s exists, updating" % productOnClient)
				self.productOnClient_updateObject(productOnClient)
			else:
				logger.info(u"ProductOnClient %s does not exist, creating" % productOnClient)
				self.productOnClient_insertObject(productOnClient)

			if returnObjects:
				result.extend(
					self._backend.productOnClient_getObjects(
						productId=productOnClient.productId,
						clientId=productOnClient.clientId
					)
				)

		return result

	def productOnClient_create(self, productId, productType, clientId, installationStatus=None, actionRequest=None, lastAction=None, actionProgress=None, actionResult=None, productVersion=None, packageVersion=None, modificationTime=None):
		hash = locals()
		del hash['self']
		return self.productOnClient_createObjects(ProductOnClient.fromHash(hash))

	def productOnClient_delete(self, productId, clientId):
		if productId is None:
			productId = []
		if clientId is None:
			clientId = []

		return self._backend.productOnClient_deleteObjects(
			self._backend.productOnClient_getObjects(
				productId=productId,
				clientId=clientId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_getObjects(self, attributes=[], **filter):
		'''
		Add default objects to result for objects which do not exist in backend
		'''
		# objectIds can be depot ids or client ids

		# Get product property states
		productPropertyStates = self._backend.productPropertyState_getObjects(attributes, **filter)

		if not self._options['addProductPropertyStateDefaults']:
			return productPropertyStates

		# Get depot to client assignment
		depotToClients = collections.defaultdict(list)
		for clientToDepot in self.configState_getClientToDepotserver(clientIds=filter.get('objectId', [])):
			depotToClients[clientToDepot['depotId']].append(clientToDepot['clientId'])

		# Create data structure for product property states to find missing ones
		ppss = collections.defaultdict(lambda: collections.defaultdict(list))
		for pps in self._backend.productPropertyState_getObjects(
						attributes=['objectId', 'productId', 'propertyId'],
						objectId=filter.get('objectId', []),
						productId=filter.get('productId', []),
						propertyId=filter.get('propertyId', [])):
			ppss[pps.objectId][pps.productId].append(pps.propertyId)

		# Create missing product property states
		for (depotId, clientIds) in depotToClients.items():
			depotFilter = dict(filter)
			depotFilter['objectId'] = depotId
			for pps in self._backend.productPropertyState_getObjects(attributes, **depotFilter):
				for clientId in clientIds:
					if pps.propertyId not in ppss.get(clientId, {}).get(pps.productId, []):
						# Product property for client does not exist => add default (values of depot)
						productPropertyStates.append(
							ProductPropertyState(
								productId=pps.productId,
								propertyId=pps.propertyId,
								objectId=clientId,
								values=pps.values
							)
						)
		return productPropertyStates

	def productPropertyState_createObjects(self, productPropertyStates):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']
		result = []
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			logger.info(u"Updating productPropertyState %s" % productPropertyState)
			self._backend.productPropertyState_insertObject(productPropertyState)

			if returnObjects:
				result.extend(
					self._backend.productPropertyState_getObjects(
						productId=productPropertyState.productId,
						objectId=productPropertyState.objectId,
						propertyId=productPropertyState.propertyId
					)
				)

		return result

	def productPropertyState_updateObjects(self, productPropertyStates):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']
		result = []
		productPropertyStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info(u"Updating productPropertyState '%s'" % productPropertyState)
			if self.productPropertyState_getIdents(
						productId=productPropertyState.productId,
						objectId=productPropertyState.objectId,
						propertyId=productPropertyState.propertyId):

				self._backend.productPropertyState_updateObject(productPropertyState)
			else:
				logger.info(u"ProductPropertyState %s does not exist, creating" % productPropertyState)
				self._backend.productPropertyState_insertObject(productPropertyState)

			if returnObjects:
				result.extend(
					self._backend.productPropertyState_getObjects(
						productId=productPropertyState.productId,
						objectId=productPropertyState.objectId,
						propertyId=productPropertyState.propertyId
					)
				)

		return result

	def productPropertyState_create(self, productId, propertyId, objectId, values=None):
		hash = locals()
		del hash['self']
		return self.productPropertyState_createObjects(ProductPropertyState.fromHash(hash))

	def productPropertyState_delete(self, productId, propertyId, objectId):
		if productId is None:
			productId = []
		if propertyId is None:
			propertyId = []
		if objectId is None:
			objectId = []

		return self._backend.productPropertyState_deleteObjects(
			self._backend.productPropertyState_getObjects(
				productId=productId,
				propertyId=propertyId,
				objectId=objectId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_createObjects(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Creating group '%s'" % group)
			self._backend.group_insertObject(group)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.group_getObjects(id=[group.id for group in groups])
		else:
			return []

	def group_updateObjects(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info(u"Updating group '%s'" % group)
			if self.group_getIdents(id=group.id):
				self._backend.group_updateObject(group)
			else:
				logger.info(u"Group %s does not exist, creating" % group)
				self._backend.group_insertObject(group)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.group_getObjects(id=[group.id for group in groups])
		else:
			return []

	def group_createHostGroup(self, id, description=None, notes=None, parentGroupId=None):
		hash = locals()
		del hash['self']
		return self.group_createObjects(HostGroup.fromHash(hash))

	def group_createProductGroup(self, id, description=None, notes=None, parentGroupId=None):
		hash = locals()
		del hash['self']
		return self.group_createObjects(ProductGroup.fromHash(hash))

	def group_delete(self, id):
		if id is None:
			id = []

		return self._backend.group_deleteObjects(
			self._backend.group_getObjects(id=id)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_createObjects(self, objectToGroups):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			logger.info(u"Creating objectToGroup %s" % objectToGroup)
			self._backend.objectToGroup_insertObject(objectToGroup)

			if returnObjects:
				result.extend(
					self._backend.objectToGroup_getObjects(
						groupType=objectToGroup.groupType,
						groupId=objectToGroup.groupId,
						objectId=objectToGroup.objectId
					)
				)
		return result

	def objectToGroup_updateObjects(self, objectToGroups):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']
		result = []
		objectToGroups = forceObjectClassList(objectToGroups, ObjectToGroup)
		for objectToGroup in objectToGroups:
			logger.info(u"Updating objectToGroup %s" % objectToGroup)
			if self.objectToGroup_getIdents(
					groupType=objectToGroup.groupType,
					groupId=objectToGroup.groupId,
					objectId=objectToGroup.objectId):
				self._backend.objectToGroup_updateObject(objectToGroup)
			else:
				logger.info(u"ObjectToGroup %s does not exist, creating" % objectToGroup)
				self._backend.objectToGroup_insertObject(objectToGroup)

			if returnObjects:
				result.extend(
					self._backend.objectToGroup_getObjects(
						groupType=objectToGroup.groupType,
						groupId=objectToGroup.groupId,
						objectId=objectToGroup.objectId
					)
				)

		return result

	def objectToGroup_create(self, groupType, groupId, objectId):
		hash = locals()
		del hash['self']
		return self.objectToGroup_createObjects(ObjectToGroup.fromHash(hash))

	def objectToGroup_delete(self, groupType, groupId, objectId):
		if not groupType:
			groupType = []
		if not groupId:
			groupId = []
		if not objectId:
			objectId = []

		return self._backend.objectToGroup_deleteObjects(
			self._backend.objectToGroup_getObjects(
				groupType=groupType,
				groupId=groupId,
				objectId=objectId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_createObjects(self, licenseContracts):
		licenseContracts = forceObjectClassList(licenseContracts, LicenseContract)
		for licenseContract in licenseContracts:
			logger.info(u"Creating licenseContract %s" % licenseContract)
			self._backend.licenseContract_insertObject(licenseContract)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.licenseContract_getObjects(id=[licenseContract.id for licenseContract in licenseContracts])
		else:
			return []

	def licenseContract_updateObjects(self, licenseContracts):
		licenseContracts = forceObjectClassList(licenseContracts, LicenseContract)
		for licenseContract in licenseContracts:
			logger.info(u"Updating licenseContract '%s'" % licenseContract)
			if self.licenseContract_getIdents(id=licenseContract.id):
				self._backend.licenseContract_updateObject(licenseContract)
			else:
				logger.info(u"LicenseContract %s does not exist, creating" % licenseContract)
				self._backend.licenseContract_insertObject(licenseContract)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.licenseContract_getObjects(id=[licenseContract.id for licenseContract in licenseContracts])
		else:
			return []

	def licenseContract_create(self, id, description=None, notes=None, partner=None, conclusionDate=None, notificationDate=None, expirationDate=None):
		hash = locals()
		del hash['self']
		return self.licenseContract_createObjects(LicenseContract.fromHash(hash))

	def licenseContract_delete(self, id):
		if id is None:
			id = []

		return self._backend.licenseContract_deleteObjects(
			self._backend.licenseContract_getObjects(id=id)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_createObjects(self, softwareLicenses):
		softwareLicenses = forceObjectClassList(softwareLicenses, SoftwareLicense)
		for softwareLicense in softwareLicenses:
			logger.info(u"Creating softwareLicense '%s'" % softwareLicense)
			self._backend.softwareLicense_insertObject(softwareLicense)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.softwareLicense_getObjects(id=[softwareLicense.id for softwareLicense in softwareLicenses])
		else:
			return []

	def softwareLicense_updateObjects(self, softwareLicenses):
		softwareLicenses = forceObjectClassList(softwareLicenses, SoftwareLicense)
		for softwareLicense in softwareLicenses:
			logger.info(u"Updating softwareLicense '%s'" % softwareLicense)
			if self.softwareLicense_getIdents(id=softwareLicense.id):
				self._backend.softwareLicense_updateObject(softwareLicense)
			else:
				logger.info(u"ProducSoftwareLicenset %s does not exist, creating" % softwareLicense)
				self._backend.softwareLicense_insertObject(softwareLicense)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.softwareLicense_getObjects(id=[softwareLicense.id for softwareLicense in softwareLicenses])
		else:
			return []

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
		if id is None:
			id = []

		return self._backend.softwareLicense_deleteObjects(
			self._backend.softwareLicense_getObjects(id=id)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePool                                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_createObjects(self, licensePools):
		licensePools = forceObjectClassList(licensePools, LicensePool)
		for licensePool in licensePools:
			logger.info(u"Creating licensePool '%s'" % licensePool)
			self._backend.licensePool_insertObject(licensePool)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.licensePool_getObjects(id=[licensePool.id for licensePool in licensePools])
		else:
			return []

	def licensePool_updateObjects(self, licensePools):
		licensePools = forceObjectClassList(licensePools, LicensePool)
		for licensePool in licensePools:
			logger.info(u"Updating licensePool '%s'" % licensePool)
			if self.licensePool_getIdents(id=licensePool.id):
				self._backend.licensePool_updateObject(licensePool)
			else:
				logger.info(u"LicensePool %s does not exist, creating" % licensePool)
				self._backend.licensePool_insertObject(licensePool)

		if self._options['returnObjectsOnUpdateAndCreate']:
			return self._backend.licensePool_getObjects(id=[licensePool.id for licensePool in licensePools])
		else:
			return []

	def licensePool_create(self, id, description=None, productIds=None):
		hash = locals()
		del hash['self']
		return self.licensePool_createObjects(LicensePool.fromHash(hash))

	def licensePool_delete(self, id):
		if id is None:
			id = []

		return self._backend.licensePool_deleteObjects(
			self._backend.licensePool_getObjects(id=id)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_createObjects(self, softwareLicenseToLicensePools):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool):
			logger.info(u"Creating softwareLicenseToLicensePool %s" % softwareLicenseToLicensePool)
			self._backend.softwareLicenseToLicensePool_insertObject(softwareLicenseToLicensePool)

			if returnObjects:
				result.extend(
					self._backend.softwareLicenseToLicensePool_getObjects(
						softwareLicenseId=softwareLicenseToLicensePool.softwareLicenseId,
						licensePoolId=softwareLicenseToLicensePool.licensePoolId
					)
				)

		return result

	def softwareLicenseToLicensePool_updateObjects(self, softwareLicenseToLicensePools):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		softwareLicenseToLicensePools = forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool)
		for softwareLicenseToLicensePool in softwareLicenseToLicensePools:
			logger.info(u"Updating %s" % softwareLicenseToLicensePool)
			if self.softwareLicenseToLicensePool_getIdents(
					softwareLicenseId=softwareLicenseToLicensePool.softwareLicenseId,
					licensePoolId=softwareLicenseToLicensePool.licensePoolId):
				self._backend.softwareLicenseToLicensePool_updateObject(softwareLicenseToLicensePool)
			else:
				logger.info(u"SoftwareLicenseToLicensePool %s does not exist, creating" % softwareLicenseToLicensePool)
				self._backend.softwareLicenseToLicensePool_insertObject(softwareLicenseToLicensePool)

			if returnObjects:
				result.extend(
					self._backend.softwareLicenseToLicensePool_getObjects(
						softwareLicenseId=softwareLicenseToLicensePool.softwareLicenseId,
						licensePoolId=softwareLicenseToLicensePool.licensePoolId
					)
				)

		return result

	def softwareLicenseToLicensePool_create(self, softwareLicenseId, licensePoolId, licenseKey=None):
		hash = locals()
		del hash['self']
		return self.softwareLicenseToLicensePool_createObjects(SoftwareLicenseToLicensePool.fromHash(hash))

	def softwareLicenseToLicensePool_delete(self, softwareLicenseId, licensePoolId):
		if not softwareLicenseId:
			softwareLicenseId = []
		if not licensePoolId:
			licensePoolId = []

		return self._backend.softwareLicenseToLicensePool_deleteObjects(
			self._backend.softwareLicenseToLicensePool_getObjects(
				softwareLicenseId=softwareLicenseId,
				licensePoolId=licensePoolId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_createObjects(self, licenseOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for licenseOnClient in forceObjectClassList(licenseOnClients, LicenseOnClient):
			logger.info(u"Creating licenseOnClient %s" % licenseOnClient)
			self._backend.licenseOnClient_insertObject(licenseOnClient)

			if returnObjects:
				result.extend(
					self._backend.licenseOnClient_getObjects(
						softwareLicenseId=licenseOnClient.softwareLicenseId,
						licensePoolId=licenseOnClient.licensePoolId,
						clientId=licenseOnClient.clientId
					)
				)

		return result

	def licenseOnClient_updateObjects(self, licenseOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		licenseOnClients = forceObjectClassList(licenseOnClients, LicenseOnClient)
		for licenseOnClient in licenseOnClients:
			logger.info(u"Updating licenseOnClient %s" % licenseOnClient)
			if self.licenseOnClient_getIdents(
					softwareLicenseId=licenseOnClient.softwareLicenseId,
					licensePoolId=licenseOnClient.licensePoolId,
					clientId=licenseOnClient.clientId):
				self._backend.licenseOnClient_updateObject(licenseOnClient)
			else:
				logger.info(u"LicenseOnClient %s does not exist, creating" % licenseOnClient)
				self._backend.licenseOnClient_insertObject(licenseOnClient)

			if returnObjects:
				result.extend(
					self._backend.licenseOnClient_getObjects(
						softwareLicenseId=licenseOnClient.softwareLicenseId,
						licensePoolId=licenseOnClient.licensePoolId,
						clientId=licenseOnClient.clientId
					)
				)

		return result

	def licenseOnClient_create(self, softwareLicenseId, licensePoolId, clientId, licenseKey=None, notes=None):
		hash = locals()
		del hash['self']
		return self.licenseOnClient_createObjects(LicenseOnClient.fromHash(hash))

	def licenseOnClient_delete(self, softwareLicenseId, licensePoolId, clientId):
		if softwareLicenseId is None:
			softwareLicenseId = []
		if licensePoolId is None:
			licensePoolId = []
		if clientId is None:
			clientId = []

		return self._backend.licenseOnClient_deleteObjects(
			self._backend.licenseOnClient_getObjects(
				softwareLicenseId=softwareLicenseId,
				licensePoolId=licensePoolId,
				clientId=clientId
			)
		)

	def licenseOnClient_getOrCreateObject(self, clientId, licensePoolId=None, productId=None, windowsSoftwareId=None):
		clientId = forceHostId(clientId)
		if licensePoolId:
			licensePoolId = forceLicensePoolId(licensePoolId)
		elif productId or windowsSoftwareId:
			if productId:
				productId = forceProductId(productId)
				licensePoolIds = self.licensePool_getIdents(productIds=productId, returnType='unicode')
			elif windowsSoftwareId:
				licensePoolIds = []
				windowsSoftwareId = forceUnicode(windowsSoftwareId)

				auditSoftwares = self.auditSoftware_getObjects(windowsSoftwareId=windowsSoftwareId)
				for auditSoftware in auditSoftwares:
					auditSoftwareToLicensePools = self.auditSoftwareToLicensePool_getObjects(
						name=auditSoftware.name,
						version=auditSoftware.version,
						subVersion=auditSoftware.subVersion,
						language=auditSoftware.language,
						architecture=auditSoftware.architecture
					)
					if auditSoftwareToLicensePools:
						licensePoolIds.append(auditSoftwareToLicensePools[0].licensePoolId)

			if len(licensePoolIds) < 1:
				raise LicenseConfigurationError(u"No license pool for product id '%s', windowsSoftwareId '%s' found" % (productId, windowsSoftwareId))
			elif len(licensePoolIds) > 1:
				raise LicenseConfigurationError(u"Multiple license pools for product id '%s', windowsSoftwareId '%s' found: %s" \
						% (productId, windowsSoftwareId, licensePoolIds))
			licensePoolId = licensePoolIds[0]
		else:
			raise ValueError(u"You have to specify one of: licensePoolId, productId, windowsSoftwareId")

		if not self.licensePool_getIdents(id=licensePoolId):
			raise LicenseConfigurationError(u"License pool '%s' not found" % licensePoolId)

		# Test if a license is already used by the host
		licenseOnClient = None
		licenseOnClients = self._backend.licenseOnClient_getObjects(licensePoolId=licensePoolId, clientId=clientId)
		if licenseOnClients:
			logger.info(u"Using already assigned license '%s' for client '%s', license pool '%s'" \
					% (licenseOnClients[0].getSoftwareLicenseId(), clientId, licensePoolId))
			licenseOnClient = licenseOnClients[0]
		else:
			(softwareLicenseId, licenseKey) = self._getUsableSoftwareLicense(clientId, licensePoolId)
			if not licenseKey:
				logger.info(u"License available but no license key found")

			logger.info(u"Using software license id '%s', license key '%s' for host '%s' and license pool '%s'" \
						% (softwareLicenseId, licenseKey, clientId, licensePoolId))

			licenseOnClient = LicenseOnClient(
				softwareLicenseId=softwareLicenseId,
				licensePoolId=licensePoolId,
				clientId=clientId,
				licenseKey=licenseKey,
				notes=None
			)
			self.licenseOnClient_createObjects(licenseOnClient)
		return licenseOnClient

	def _getUsableSoftwareLicense(self, clientId, licensePoolId):
		softwareLicenseId = u''
		licenseKey = u''

		licenseOnClients = self._backend.licenseOnClient_getObjects(licensePoolId=licensePoolId, clientId=clientId)
		if licenseOnClients:
			# Already registered
			return (licenseOnClients[0].getSoftwareLicenseId(), licenseOnClients[0].getLicenseKey())

		softwareLicenseToLicensePools = self._backend.softwareLicenseToLicensePool_getObjects(licensePoolId=licensePoolId)
		if not softwareLicenseToLicensePools:
			raise LicenseMissingError(u"No licenses in pool '%s'" % licensePoolId)

		softwareLicenseIds = [softwareLicenseToLicensePool.softwareLicenseId
								for softwareLicenseToLicensePool
								in softwareLicenseToLicensePools]

		softwareLicensesBoundToHost = self._backend.softwareLicense_getObjects(id=softwareLicenseIds, boundToHost=clientId)
		if softwareLicensesBoundToHost:
			logger.info(u"Using license bound to host: %s" % softwareLicensesBoundToHost[0])
			softwareLicenseId = softwareLicensesBoundToHost[0].getId()
		else:
			# Search an available license
			for softwareLicense in self._backend.softwareLicense_getObjects(id=softwareLicenseIds, boundToHost=[None, '']):
				logger.debug(u"Checking license '%s', maxInstallations %d" \
					% (softwareLicense.getId(), softwareLicense.getMaxInstallations()))
				if softwareLicense.getMaxInstallations() == 0:
					# 0 = infinite
					softwareLicenseId = softwareLicense.getId()
					break
				installations = len(self.licenseOnClient_getIdents(softwareLicenseId=softwareLicense.getId()))
				logger.debug(u"Installations registered: %d" % installations)
				if installations < softwareLicense.getMaxInstallations():
					softwareLicenseId = softwareLicense.getId()
					break

			if softwareLicenseId:
				logger.info(u"Found available license for pool '%s' and client '%s': %s" % (licensePoolId, clientId, softwareLicenseId))

		if not softwareLicenseId:
			raise LicenseMissingError(u"No license available for pool '%s' and client '%s'" % (licensePoolId, clientId))

		licenseKeys = []
		for softwareLicenseToLicensePool in softwareLicenseToLicensePools:
			if softwareLicenseToLicensePool.getLicenseKey():
				if softwareLicenseToLicensePool.getSoftwareLicenseId() == softwareLicenseId:
					licenseKey = softwareLicenseToLicensePool.getLicenseKey()
					break
				logger.debug(u"Found license key: %s" % licenseKey)
				licenseKeys.append(softwareLicenseToLicensePool.getLicenseKey())

		if not licenseKey and licenseKeys:
			licenseKey = random.choice(licenseKeys)
			logger.info(u"Randomly choosing license key")

		logger.debug(u"Using license '%s', license key: %s" % (softwareLicenseId, licenseKey))
		return (softwareLicenseId, licenseKey)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_createObjects(self, auditSoftwares):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for auditSoftware in forceObjectClassList(auditSoftwares, AuditSoftware):
			logger.info(u"Creating auditSoftware %s" % auditSoftware)
			self._backend.auditSoftware_insertObject(auditSoftware)

			if returnObjects:
				result.extend(
					self._backend.auditSoftware_getObjects(
						name=auditSoftware.name,
						version=auditSoftware.version,
						subVersion=auditSoftware.subVersion,
						language=auditSoftware.language,
						architecture=auditSoftware.architecture
					)
				)

		return result

	def auditSoftware_updateObjects(self, auditSoftwares):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		auditSoftwares = forceObjectClassList(auditSoftwares, AuditSoftware)
		for auditSoftware in auditSoftwares:
			logger.info(u"Updating %s" % auditSoftware)
			if self.auditSoftware_getIdents(
					name=auditSoftware.name,
					version=auditSoftware.version,
					subVersion=auditSoftware.subVersion,
					language=auditSoftware.language,
					architecture=auditSoftware.architecture):

				self._backend.auditSoftware_updateObject(auditSoftware)
			else:
				logger.info(u"AuditSoftware %s does not exist, creating" % auditSoftware)
				self._backend.auditSoftware_insertObject(auditSoftware)

			if returnObjects:
				result.extend(
					self._backend.auditSoftware_getObjects(
						name=auditSoftware.name,
						version=auditSoftware.version,
						subVersion=auditSoftware.subVersion,
						language=auditSoftware.language,
						architecture=auditSoftware.architecture
					)
				)

		return result

	def auditSoftware_create(self, name, version, subVersion, language, architecture, windowsSoftwareId=None, windowsDisplayName=None, windowsDisplayVersion=None, installSize=None):
		hash = locals()
		del hash['self']
		return self.auditSoftware_createObjects(AuditSoftware.fromHash(hash))

	def auditSoftware_delete(self, name, version, subVersion, language, architecture):
		if name is None:
			name = []
		if version is None:
			version = []
		if subVersion is None:
			subVersion = []
		if language is None:
			language = []
		if architecture is None:
			architecture = []

		return self._backend.auditSoftware_deleteObjects(
			self._backend.auditSoftware_getObjects(
				name=name,
				version=version,
				subVersion=subVersion,
				language=language,
				architecture=architecture
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareToLicensePools                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareToLicensePool_createObjects(self, auditSoftwareToLicensePools):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for auditSoftwareToLicensePool in forceObjectClassList(auditSoftwareToLicensePools, AuditSoftwareToLicensePool):
			logger.info(u"Creating %s" % auditSoftwareToLicensePool)
			self._backend.auditSoftwareToLicensePool_insertObject(auditSoftwareToLicensePool)

			if returnObjects:
				result.extend(
					self._backend.auditSoftwareToLicensePool_getObjects(
						name=auditSoftwareToLicensePool.name,
						version=auditSoftwareToLicensePool.version,
						subVersion=auditSoftwareToLicensePool.subVersion,
						language=auditSoftwareToLicensePool.language,
						architecture=auditSoftwareToLicensePool.architecture
					)
				)

		return result

	def auditSoftwareToLicensePool_updateObjects(self, auditSoftwareToLicensePools):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		auditSoftwareToLicensePools = forceObjectClassList(auditSoftwareToLicensePools, AuditSoftwareToLicensePool)
		for auditSoftwareToLicensePool in auditSoftwareToLicensePools:
			logger.info(u"Creating %s" % auditSoftwareToLicensePool)
			if self.auditSoftwareToLicensePool_getIdents(
					name=auditSoftwareToLicensePool.name,
					version=auditSoftwareToLicensePool.version,
					subVersion=auditSoftwareToLicensePool.subVersion,
					language=auditSoftwareToLicensePool.language,
					architecture=auditSoftwareToLicensePool.architecture):

				self._backend.auditSoftwareToLicensePool_updateObject(auditSoftwareToLicensePool)
			else:
				logger.info(u"AuditSoftwareToLicensePool %s does not exist, creating" % auditSoftwareToLicensePool)
				self._backend.auditSoftwareToLicensePool_insertObject(auditSoftwareToLicensePool)

			if returnObjects:
				result.extend(
					self._backend.auditSoftwareToLicensePool_getObjects(
						name=auditSoftwareToLicensePool.name,
						version=auditSoftwareToLicensePool.version,
						subVersion=auditSoftwareToLicensePool.subVersion,
						language=auditSoftwareToLicensePool.language,
						architecture=auditSoftwareToLicensePool.architecture
					)
				)

		return result

	def auditSoftwareToLicensePool_create(self, name, version, subVersion, language, architecture, licensePoolId):
		hash = locals()
		del hash['self']
		return self.auditSoftwareToLicensePool_createObjects(AuditSoftwareToLicensePool.fromHash(hash))

	def auditSoftwareToLicensePool_delete(self, name, version, subVersion, language, architecture, licensePoolId):
		if name is None:
			name = []
		if version is None:
			version = []
		if subVersion is None:
			subVersion = []
		if language is None:
			language = []
		if architecture is None:
			architecture = []
		if licensePoolId is None:
			licensePoolId = []

		return self._backend.auditSoftwareToLicensePool_deleteObjects(
			self._backend.auditSoftwareToLicensePool_getObjects(
				name=name,
				version=version,
				subVersion=subVersion,
				language=language,
				architecture=architecture,
				licensePoolId=licensePoolId
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_createObjects(self, auditSoftwareOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		for auditSoftwareOnClient in forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient):
			logger.info(u"Creating auditSoftwareOnClient %s" % auditSoftwareOnClient)
			self._backend.auditSoftwareOnClient_insertObject(auditSoftwareOnClient)

			if returnObjects:
				result.extend(
					self._backend.auditSoftwareOnClient_getObjects(
						name=auditSoftwareOnClient.name,
						version=auditSoftwareOnClient.version,
						subVersion=auditSoftwareOnClient.subVersion,
						language=auditSoftwareOnClient.language,
						architecture=auditSoftwareOnClient.architecture,
						clientId=auditSoftwareOnClient.clientId
					)
				)

		return result

	def auditSoftwareOnClient_updateObjects(self, auditSoftwareOnClients):
		returnObjects = self._options['returnObjectsOnUpdateAndCreate']

		result = []
		auditSoftwareOnClients = forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient)
		for auditSoftwareOnClient in auditSoftwareOnClients:
			logger.info(u"Updating auditSoftwareOnClient %s" % auditSoftwareOnClient)
			if self.auditSoftwareOnClient_getIdents(
					name=auditSoftwareOnClient.name,
					version=auditSoftwareOnClient.version,
					subVersion=auditSoftwareOnClient.subVersion,
					language=auditSoftwareOnClient.language,
					architecture=auditSoftwareOnClient.architecture,
					clientId=auditSoftwareOnClient.clientId):
				self._backend.auditSoftwareOnClient_updateObject(auditSoftwareOnClient)
			else:
				logger.info(u"AuditSoftwareOnClient %s does not exist, creating" % auditSoftwareOnClient)
				self._backend.auditSoftwareOnClient_insertObject(auditSoftwareOnClient)

			if returnObjects:
				result.extend(
					self._backend.auditSoftwareOnClient_getObjects(
						name=auditSoftwareOnClient.name,
						version=auditSoftwareOnClient.version,
						subVersion=auditSoftwareOnClient.subVersion,
						language=auditSoftwareOnClient.language,
						architecture=auditSoftwareOnClient.architecture,
						clientId=auditSoftwareOnClient.clientId
					)
				)

		return result

	def auditSoftwareOnClient_create(self, name, version, subVersion, language, architecture, clientId, uninstallString=None, binaryName=None, firstseen=None, lastseen=None, state=None, usageFrequency=None, lastUsed=None, licenseKey=None):
		hash = locals()
		del hash['self']
		return self.auditSoftwareOnClient_createObjects(AuditSoftwareOnClient.fromHash(hash))

	def auditSoftwareOnClient_delete(self, name, version, subVersion, language, architecture, clientId):
		if name is None:
			name = []
		if version is None:
			version = []
		if subVersion is None:
			subVersion = []
		if language is None:
			language = []
		if architecture is None:
			architecture = []
		if clientId is None:
			clientId = []

		return self._backend.auditSoftwareOnClient_deleteObjects(
			self._backend.auditSoftwareOnClient_getObjects(
				name=name,
				version=version,
				subVersion=subVersion,
				language=language,
				architecture=architecture,
				clientId=clientId
			)
		)

	def auditSoftwareOnClient_setObsolete(self, clientId):
		if clientId is None:
			clientId = []
		clientId = forceHostIdList(clientId)
		self._backend.auditSoftwareOnClient_deleteObjects(
			self._backend.auditSoftwareOnClient_getObjects(clientId=clientId)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardware_createObjects(self, auditHardwares):
		for auditHardware in forceObjectClassList(auditHardwares, AuditHardware):
			logger.info(u"Creating auditHardware %s" % auditHardware)
			self.auditHardware_insertObject(auditHardware)
		return []

	def auditHardware_updateObjects(self, auditHardwares):
		for auditHardware in forceObjectClassList(auditHardwares, AuditHardware):
			logger.info(u"Updating auditHardware %s" % auditHardware)
			# You can't update auditHardwares, because the ident contains all attributes
			self.auditHardware_insertObject(auditHardware)
		return []

	def auditHardware_create(self, hardwareClass, **kwargs):
		hash = locals()
		del hash['self']
		return self.auditHardware_createObjects(AuditHardware.fromHash(hash))

	def auditHardware_delete(self, hardwareClass, **kwargs):
		if hardwareClass is None:
			hardwareClass = []
		for key in kwargs.keys():
			if kwargs[key] is None:
				kwargs[key] = []

		return self._backend.auditHardware_deleteObjects(
			self._backend.auditHardware_getObjects(
				hardwareClass=hardwareClass,
				**kwargs
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		"""
		Update an auditHardwareOnHost object.

		This will update the attributes `state` and `lastseen` on the object.
		"""
		auditHardwareOnHost.setLastseen(timestamp())
		auditHardwareOnHost.setState(1)
		self._backend.auditHardwareOnHost_updateObject(auditHardwareOnHost)

	def auditHardwareOnHost_createObjects(self, auditHardwareOnHosts):
		for auditHardwareOnHost in forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost):
			logger.info(u"Creating auditHardwareOnHost %s" % auditHardwareOnHost)
			self._backend.auditHardwareOnHost_insertObject(auditHardwareOnHost)

		return []

	def auditHardwareOnHost_updateObjects(self, auditHardwareOnHosts):
		def getNoneAsListOrValue(value):
			if value is None:
				return [None]
			else:
				return value

		for auditHardwareOnHost in forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost):
			filter = {
				attribute: getNoneAsListOrValue(value)
				for (attribute, value) in auditHardwareOnHost.toHash().items()
				if attribute not in ('firstseen', 'lastseen', 'state')
			}

			if self.auditHardwareOnHost_getObjects(attributes=['hostId'], **filter):
				logger.debug2(u"Updating existing AuditHardwareOnHost {0!r}", auditHardwareOnHost)
				self.auditHardwareOnHost_updateObject(auditHardwareOnHost)
			else:
				logger.info(u"AuditHardwareOnHost %s does not exist, creating" % auditHardwareOnHost)
				self._backend.auditHardwareOnHost_insertObject(auditHardwareOnHost)

		return []

	def auditHardwareOnHost_create(self, hostId, hardwareClass, firstseen=None, lastseen=None, state=None, **kwargs):
		hash = locals()
		del hash['self']
		return self.auditHardwareOnHost_createObjects(AuditHardwareOnHost.fromHash(hash))

	def auditHardwareOnHost_delete(self, hostId, hardwareClass, firstseen=None, lastseen=None, state=None, **kwargs):
		if hostId is None:
			hostId = []
		if hardwareClass is None:
			hardwareClass = []
		if firstseen is None:
			firstseen = []
		if lastseen is None:
			lastseen = []
		if state is None:
			state = []

		for key in kwargs:
			if kwargs[key] is None:
				kwargs[key] = []

		return self._backend.auditHardwareOnHost_deleteObjects(
			self._backend.auditHardwareOnHost_getObjects(
				hostId=hostId,
				hardwareClass=hardwareClass,
				firstseen=firstseen,
				lastseen=lastseen,
				state=state,
				**kwargs
			)
		)

	def auditHardwareOnHost_setObsolete(self, hostId):
		if hostId is None:
			hostId = []

		hostId = forceHostIdList(hostId)
		for ahoh in self.auditHardwareOnHost_getObjects(hostId=hostId, state=1):
			ahoh.setState(0)
			self._backend.auditHardwareOnHost_updateObject(ahoh)
