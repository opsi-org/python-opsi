# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) - http://www.opsi.org

# Copyright (C) 2006-2018 uib GmbH <info@uib.de>

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
General classes used in the library.

As an example this contains classes for hosts, products, configurations.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import inspect

from OPSI.Logger import Logger
from OPSI.Exceptions import BackendBadValueError, BackendConfigurationError
from OPSI.Types import (forceActionProgress, forceActionRequest,
	forceActionResult, forceArchitecture, forceAuditState, forceBool,
	forceBoolList, forceConfigId, forceFilename, forceFloat, forceGroupId,
	forceGroupType, forceHardwareAddress, forceHardwareDeviceId,
	forceHardwareVendorId, forceHostId, forceInstallationStatus, forceInt,
	forceIPAddress, forceLanguageCode, forceLicenseContractId,
	forceLicensePoolId, forceList, forceNetworkAddress, forceObjectId,
	forceOpsiHostKey, forceOpsiTimestamp, forcePackageVersion, forceProductId,
	forceProductIdList, forceProductPriority, forceProductPropertyId,
	forceProductTargetConfiguration, forceProductType, forceProductVersion,
	forceRequirementType, forceSoftwareLicenseId, forceUnicode,
	forceUnicodeList, forceUnicodeLower, forceUnsignedInt, forceUrl)
from OPSI.Util import fromJson, toJson, generateOpsiHostKey, timestamp

__all__ = (
	'AuditHardware', 'AuditHardwareOnHost', 'AuditSoftware',
	'AuditSoftwareOnClient', 'AuditSoftwareToLicensePool', 'BaseObject',
	'BoolConfig', 'BoolProductProperty', 'ConcurrentSoftwareLicense',
	'Config', 'ConfigState', 'Entity', 'Group', 'Host', 'HostGroup',
	'LicenseContract', 'LicenseOnClient', 'LicensePool', 'LocalbootProduct',
	'Logger', 'NetbootProduct', 'OEMSoftwareLicense', 'Object', 'ObjectToGroup',
	'OpsiClient', 'OpsiConfigserver', 'OpsiDepotserver', 'Product',
	'ProductDependency', 'ProductGroup', 'ProductOnClient', 'ProductOnDepot',
	'ProductProperty', 'ProductPropertyState', 'Relationship',
	'RetailSoftwareLicense', 'SoftwareLicense', 'SoftwareLicenseToLicensePool',
	'UnicodeConfig', 'UnicodeProductProperty', 'VolumeSoftwareLicense',
	'decodeIdent', 'getBackendMethodPrefix', 'getForeignIdAttributes',
	'getIdentAttributes', 'getPossibleClassAttributes',
	'mandatoryConstructorArgs', 'objectsDiffer'
)

logger = Logger()
_MANDATORY_CONSTRUCTOR_ARGS_CACHE = {}


def mandatoryConstructorArgs(Class):
	cacheKey = Class.__name__
	try:
		return _MANDATORY_CONSTRUCTOR_ARGS_CACHE[cacheKey]
	except KeyError:
		args, _, _, defaults = inspect.getargspec(Class.__init__)
		try:
			last = len(defaults) * -1
			mandatory = args[1:][:last]
		except TypeError:  # Happens if defaults is None
			mandatory = args[1:]

		logger.debug2(u"mandatoryConstructorArgs for {0!r}: {1}", cacheKey, mandatory)
		_MANDATORY_CONSTRUCTOR_ARGS_CACHE[cacheKey] = mandatory
		return mandatory


def getIdentAttributes(klass):
	return tuple(mandatoryConstructorArgs(klass))


def getForeignIdAttributes(klass):
	return klass.foreignIdAttributes


def getPossibleClassAttributes(klass):
	"""
	Returns the possible attributes of a class.

	:returntype: set of strings
	"""
	attributes = inspect.getargspec(klass.__init__)[0]
	for subClass in klass.subClasses.values():
		attributes.extend(inspect.getargspec(subClass.__init__)[0])

	attributes = set(attributes)
	attributes.add('type')

	try:
		attributes.remove('self')
	except KeyError:
		pass

	return attributes


def getBackendMethodPrefix(klass):
	return klass.backendMethodPrefix


def decodeIdent(klass, hash):
	try:
		identFromHash = hash.pop('ident')
	except KeyError:  # No 'ident' in hash. Can happen.
		return hash

	if identFromHash:
		try:
			hash.update(identFromHash)
		except (TypeError, ValueError):  # identFromHash is no dict
			try:
				identValues = identFromHash.split(klass.identSeparator)
			except AttributeError:  # neither string nor unicode
				if isinstance(identFromHash, (tuple, list)):
					identValues = identFromHash
				else:
					identValues = []

			args = mandatoryConstructorArgs(klass)
			assert len(identValues) == len(args), "ident has unexpected length."
			hash.update({k: v for k, v in zip(args, identValues)})

	return hash


def objectsDiffer(obj1, obj2, excludeAttributes=None):
	if excludeAttributes is None:
		excludeAttributes = []
	else:
		excludeAttributes = forceUnicodeList(excludeAttributes)

	if obj1 != obj2:
		return True

	obj2 = obj2.toHash()
	for (attribute, value1) in obj1.toHash().items():
		if attribute in excludeAttributes:
			continue

		value2 = obj2.get(attribute)

		if type(value1) is not type(value2):
			return True

		if isinstance(value1, dict):
			if len(value1) != len(value2):
				return True

			for (key, value) in value1.items():
				if value2.get(key) != value:
					return True
		elif isinstance(value1, list):
			if len(value1) != len(value2):
				return True

			for value in value1:
				if value not in value2:
					return True

			for value in value2:
				if value not in value1:
					return True
		else:
			if value1 != value2:
				return True
	return False


class BaseObject(object):
	subClasses = {}
	identSeparator = u';'
	foreignIdAttributes = []
	backendMethodPrefix = ''
	_isGeneratedDefault = False

	def getBackendMethodPrefix(self):
		return self.backendMethodPrefix

	def getForeignIdAttributes(self):
		return self.foreignIdAttributes

	def getIdentAttributes(self):
		return getIdentAttributes(self.__class__)

	def getIdent(self, returnType='unicode'):
		returnType = forceUnicodeLower(returnType)
		identAttributes = self.getIdentAttributes()

		def getIdentvalue(attribute):
			try:
				value = getattr(self, attribute)
				if value is None:
					value = u''

				return value
			except AttributeError:
				return u''

		identValues = [forceUnicode(getIdentvalue(attribute)) for attribute in identAttributes]

		if returnType == 'list':
			return identValues
		elif returnType == 'tuple':
			return tuple(identValues)
		elif returnType in ('dict', 'hash'):
			return dict(zip(identAttributes, identValues))
		else:
			return self.identSeparator.join(identValues)

	def setDefaults(self):
		pass

	def emptyValues(self, keepAttributes=[]):
		keepAttributes = set(forceUnicodeList(keepAttributes))
		for attribute in self.getIdentAttributes():
			keepAttributes.add(attribute)
		keepAttributes.add('type')

		for attribute in self.__dict__.keys():
			if attribute not in keepAttributes:
				self.__dict__[attribute] = None

	def update(self, updateObject, updateWithNoneValues=True):
		if not issubclass(updateObject.__class__, self.__class__):
			raise TypeError(u"Cannot update instance of %s with instance of %s" % (self.__class__.__name__, updateObject.__class__.__name__))
		hash = updateObject.toHash()

		try:
			del hash['type']
		except KeyError:
			# No key "type", everything fine.
			pass

		if not updateWithNoneValues:
			for (key, value) in hash.items():
				if value is None:
					del hash[key]

		self.__dict__.update(hash)

	def getType(self):
		return self.__class__.__name__

	def setGeneratedDefault(self, flag=True):
		self._isGeneratedDefault = forceBool(flag)

	def isGeneratedDefault(self):
		return self._isGeneratedDefault

	def toHash(self):
		hash = dict(self.__dict__)
		hash['type'] = self.getType()
		return hash

	def toJson(self):
		return toJson(self)

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		if self.isGeneratedDefault() or other.isGeneratedDefault():
			return False
		return self.getIdent() == other.getIdent()

	def __ne__(self, other):
		return not self.__eq__(other)

	def __str__(self):
		additionalAttributes = []
		for attr in self.getIdentAttributes():
			try:
				value = getattr(self, attr)
				additionalAttributes.append('{0}={1!r}'.format(attr, value))
			except AttributeError:
				pass

		return u"<{0}({1})>".format(self.getType(), ', '.join(additionalAttributes))

	def __repr__(self):
		return self.__str__()


class Entity(BaseObject):
	subClasses = {}

	def setDefaults(self):
		BaseObject.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Entity'

		Class = eval(hash['type'])
		kwargs = {}
		decodeIdent(Class, hash)
		for varname in Class.__init__.__code__.co_varnames[1:]:
			try:
				kwargs[varname] = hash[varname]
			except KeyError:
				pass

		try:
			return Class(**kwargs)
		except TypeError as error:
			if '__init__() takes at least' in forceUnicode(error):
				try:
					args = mandatoryConstructorArgs(Class)
					missingArgs = [arg for arg in args if arg not in kwargs]
					if missingArgs:
						raise TypeError("Missing required argument(s): {0}".format(', '.join(repr(a) for a in missingArgs)))
				except NameError:
					pass

			raise error

	def clone(self, identOnly=False):
		hash = {}

		if identOnly:
			identAttributes = self.getIdentAttributes()
			for (attribute, value) in self.toHash().items():
				if attribute != 'type' and attribute not in identAttributes:
					continue
				hash[attribute] = value
		else:
			hash = self.toHash()

		return self.fromHash(hash)

	def serialize(self):
		hash = self.toHash()
		hash['ident'] = self.getIdent()
		return hash

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Entity')

BaseObject.subClasses['Entity'] = Entity


class Relationship(BaseObject):
	subClasses = {}

	def setDefaults(self):
		BaseObject.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Relationship'

		Class = eval(hash['type'])
		kwargs = {}
		decodeIdent(Class, hash)
		for varname in Class.__init__.__code__.co_varnames[1:]:
			try:
				kwargs[varname] = hash[varname]
			except KeyError:
				pass

		try:
			return Class(**kwargs)
		except TypeError as error:
			if '__init__() takes at least' in forceUnicode(error):
				try:
					args = mandatoryConstructorArgs(Class)
					missingArgs = [arg for arg in args if arg not in kwargs]
					if missingArgs:
						raise TypeError("Missing required argument(s): {0}".format(', '.join(repr(a) for a in missingArgs)))
				except NameError:
					pass

			raise error

	def clone(self, identOnly=False):
		hash = {}
		if identOnly:
			identAttributes = self.getIdentAttributes()
			for (attribute, value) in self.toHash().items():
				if attribute != 'type' and attribute not in identAttributes:
					continue
				hash[attribute] = value
		else:
			hash = self.toHash()
		return self.fromHash(hash)

	def serialize(self):
		hash = self.toHash()
		hash['type'] = self.getType()
		hash['ident'] = self.getIdent()
		return hash

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Relationship')

BaseObject.subClasses['Relationship'] = Relationship


class Object(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['objectId']

	def __init__(self, id, description=None, notes=None):
		self.description = None
		self.notes = None
		self.setId(id)
		if description is not None:
			self.setDescription(description)
		if notes is not None:
			self.setNotes(notes)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.notes is None:
			self.setNotes(u"")

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceObjectId(id)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def getNotes(self):
		return self.notes

	def setNotes(self, notes):
		self.notes = forceUnicode(notes)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Object'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Object')

Entity.subClasses['Object'] = Object


class Host(Object):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['hostId']
	backendMethodPrefix = 'host'

	def __init__(self, id, description=None, notes=None, hardwareAddress=None,
				ipAddress=None, inventoryNumber=None):
		Object.__init__(self, id, description, notes)
		self.hardwareAddress = None
		self.ipAddress = None
		self.inventoryNumber = None
		self.setId(id)

		if hardwareAddress is not None:
			self.setHardwareAddress(hardwareAddress)
		if ipAddress is not None:
			self.setIpAddress(ipAddress)
		if inventoryNumber is not None:
			self.setInventoryNumber(inventoryNumber)

	def setDefaults(self):
		Object.setDefaults(self)
		if self.inventoryNumber is None:
			self.setInventoryNumber(u"")

	def setId(self, id):
		self.id = forceHostId(id)

	def getHardwareAddress(self):
		return self.hardwareAddress

	def setHardwareAddress(self, hardwareAddress):
		self.hardwareAddress = forceHardwareAddress(forceList(hardwareAddress)[0])

	def getIpAddress(self):
		return self.ipAddress

	def setIpAddress(self, ipAddress):
		self.ipAddress = forceIPAddress(ipAddress)

	def getInventoryNumber(self):
		return self.inventoryNumber

	def setInventoryNumber(self, inventoryNumber):
		self.inventoryNumber = forceUnicode(inventoryNumber)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Host'

		return Object.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Host')

Object.subClasses['Host'] = Host


class OpsiClient(Host):
	subClasses = {}
	foreignIdAttributes = Host.foreignIdAttributes + ['clientId']

	def __init__(self, id, opsiHostKey=None, description=None, notes=None,
				hardwareAddress=None, ipAddress=None, inventoryNumber=None,
				oneTimePassword=None, created=None, lastSeen=None):

		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress,
			inventoryNumber)
		self.opsiHostKey = None
		self.created = None
		self.lastSeen = None
		self.oneTimePassword = None

		if opsiHostKey is not None:
			self.setOpsiHostKey(opsiHostKey)
		if created is not None:
			self.setCreated(created)
		if lastSeen is not None:
			self.setLastSeen(lastSeen)
		if oneTimePassword is not None:
			self.setOneTimePassword(oneTimePassword)

	def setDefaults(self):
		Host.setDefaults(self)
		if self.opsiHostKey is None:
			self.setOpsiHostKey(generateOpsiHostKey())
		if self.created is None:
			self.setCreated(timestamp())
		if self.lastSeen is None:
			self.setLastSeen(timestamp())

	def getLastSeen(self):
		return self.lastSeen

	def setLastSeen(self, lastSeen):
		self.lastSeen = forceOpsiTimestamp(lastSeen)

	def getCreated(self):
		return self.created

	def setCreated(self, created):
		self.created = forceOpsiTimestamp(created)

	def getOpsiHostKey(self):
		return self.opsiHostKey

	def setOpsiHostKey(self, opsiHostKey):
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)

	def getOneTimePassword(self):
		return self.oneTimePassword

	def setOneTimePassword(self, oneTimePassword):
		self.oneTimePassword = forceUnicode(oneTimePassword)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'OpsiClient'

		return Host.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'OpsiClient')

Host.subClasses['OpsiClient'] = OpsiClient


class OpsiDepotserver(Host):
	subClasses = {}
	foreignIdAttributes = Host.foreignIdAttributes + ['depotId']

	def __init__(
		self, id, opsiHostKey=None, depotLocalUrl=None,
		depotRemoteUrl=None, depotWebdavUrl=None,
		repositoryLocalUrl=None, repositoryRemoteUrl=None,
		description=None, notes=None, hardwareAddress=None,
		ipAddress=None, inventoryNumber=None, networkAddress=None,
		maxBandwidth=None, isMasterDepot=None, masterDepotId=None,
		workbenchLocalUrl=None, workbenchRemoteUrl=None):

		Host.__init__(
			self, id, description, notes, hardwareAddress, ipAddress,
			inventoryNumber)

		self.opsiHostKey = None
		self.depotLocalUrl = None
		self.depotRemoteUrl = None
		self.depotWebdavUrl = None
		self.repositoryLocalUrl = None
		self.repositoryRemoteUrl = None
		self.networkAddress = None
		self.maxBandwidth = None
		self.isMasterDepot = None
		self.masterDepotId = None
		self.workbenchLocalUrl = None
		self.workbenchRemoteUrl = None

		if opsiHostKey is not None:
			self.setOpsiHostKey(opsiHostKey)
		if depotLocalUrl is not None:
			self.setDepotLocalUrl(depotLocalUrl)
		if depotRemoteUrl is not None:
			self.setDepotRemoteUrl(depotRemoteUrl)
		if depotWebdavUrl is not None:
			self.setDepotWebdavUrl(depotWebdavUrl)
		if repositoryLocalUrl is not None:
			self.setRepositoryLocalUrl(repositoryLocalUrl)
		if repositoryRemoteUrl is not None:
			self.setRepositoryRemoteUrl(repositoryRemoteUrl)
		if networkAddress is not None:
			self.setNetworkAddress(networkAddress)
		if maxBandwidth is not None:
			self.setMaxBandwidth(maxBandwidth)
		if isMasterDepot is not None:
			self.setIsMasterDepot(isMasterDepot)
		if masterDepotId is not None:
			self.setMasterDepotId(masterDepotId)
		if workbenchLocalUrl is not None:
			self.setWorkbenchLocalUrl(workbenchLocalUrl)
		if workbenchRemoteUrl is not None:
			self.setWorkbenchRemoteUrl(workbenchRemoteUrl)

	def setDefaults(self):
		Host.setDefaults(self)
		if self.opsiHostKey is None:
			self.setOpsiHostKey(generateOpsiHostKey())
		if self.isMasterDepot is None:
			self.setIsMasterDepot(True)

	def getOpsiHostKey(self):
		return self.opsiHostKey

	def setOpsiHostKey(self, opsiHostKey):
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)

	def getDepotLocalUrl(self):
		return self.depotLocalUrl

	def setDepotLocalUrl(self, depotLocalUrl):
		self.depotLocalUrl = forceUrl(depotLocalUrl)

	def getDepotRemoteUrl(self):
		return self.depotRemoteUrl

	def setDepotWebdavUrl(self, depotWebdavUrl):
		self.depotWebdavUrl = forceUrl(depotWebdavUrl)

	def getDepotWebdavUrl(self):
		return self.depotWebdavUrl

	def setDepotRemoteUrl(self, depotRemoteUrl):
		self.depotRemoteUrl = forceUrl(depotRemoteUrl)

	def getRepositoryLocalUrl(self):
		return self.repositoryLocalUrl

	def setRepositoryLocalUrl(self, repositoryLocalUrl):
		self.repositoryLocalUrl = forceUrl(repositoryLocalUrl)

	def getRepositoryRemoteUrl(self):
		return self.repositoryRemoteUrl

	def setRepositoryRemoteUrl(self, repositoryRemoteUrl):
		self.repositoryRemoteUrl = forceUrl(repositoryRemoteUrl)

	def getNetworkAddress(self):
		return self.networkAddress

	def setNetworkAddress(self, networkAddress):
		self.networkAddress = forceNetworkAddress(networkAddress)

	def getMaxBandwidth(self):
		return self.maxBandwidth

	def setMaxBandwidth(self, maxBandwidth):
		self.maxBandwidth = forceInt(maxBandwidth)

	def setIsMasterDepot(self, isMasterDepot):
		self.isMasterDepot = forceBool(isMasterDepot)

	def getIsMasterDepot(self):
		return self.isMasterDepot

	def setMasterDepotId(self, masterDepotId):
		self.masterDepotId = forceHostId(masterDepotId)

	def getMasterDepotId(self):
		return self.masterDepotId

	def setWorkbenchLocalUrl(self, value):
		self.workbenchLocalUrl = forceUrl(value)

	def getWorkbenchLocalUrl(self):
		return self.workbenchLocalUrl

	def setWorkbenchRemoteUrl(self, value):
		self.workbenchRemoteUrl = forceUrl(value)

	def getWorkbenchRemoteUrl(self):
		return self.workbenchRemoteUrl

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'OpsiDepotserver'
		return Host.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'OpsiDepotserver')

	def __unicode__(self):
		additionalInfos = [u"id={0!r}".format(self.id)]
		if self.isMasterDepot:
			additionalInfos.append(u'isMasterDepot={0!r}'.format(self.isMasterDepot))
		if self.masterDepotId:
			additionalInfos.append(u"masterDepotId={0!r}".format(self.masterDepotId))

		return u"<{0}({1})>".format(self.getType(), u', '.join(additionalInfos))

Host.subClasses['OpsiDepotserver'] = OpsiDepotserver


class OpsiConfigserver(OpsiDepotserver):
	subClasses = {}
	foreignIdAttributes = OpsiDepotserver.foreignIdAttributes + ['serverId']

	def __init__(
		self, id, opsiHostKey=None, depotLocalUrl=None,
		depotRemoteUrl=None, depotWebdavUrl=None,
		repositoryLocalUrl=None, repositoryRemoteUrl=None,
		description=None, notes=None, hardwareAddress=None,
		ipAddress=None, inventoryNumber=None, networkAddress=None,
		maxBandwidth=None, isMasterDepot=None, masterDepotId=None,
		workbenchLocalUrl=None, workbenchRemoteUrl=None):
		OpsiDepotserver.__init__(
			self, id, opsiHostKey, depotLocalUrl,
			depotRemoteUrl, depotWebdavUrl, repositoryLocalUrl,
			repositoryRemoteUrl, description, notes, hardwareAddress,
			ipAddress, inventoryNumber, networkAddress, maxBandwidth,
			isMasterDepot, masterDepotId,
			workbenchLocalUrl, workbenchRemoteUrl)

	def setDefaults(self):
		if self.isMasterDepot is None:
			self.setIsMasterDepot(True)
		OpsiDepotserver.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'OpsiConfigserver'

		return OpsiDepotserver.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'OpsiConfigserver')

OpsiDepotserver.subClasses['OpsiConfigserver'] = OpsiConfigserver
Host.subClasses['OpsiConfigserver'] = OpsiConfigserver


class Config(Entity):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['configId']
	backendMethodPrefix = 'config'

	def __init__(self, id, description=None, possibleValues=None,
				defaultValues=None, editable=None, multiValue=None):
		self.description = None
		self.possibleValues = None
		self.defaultValues = None
		self.editable = None
		self.multiValue = None

		self.setId(id)
		if description is not None:
			self.setDescription(description)
		if possibleValues is not None:
			self.setPossibleValues(possibleValues)
		if defaultValues is not None:
			self.setDefaultValues(defaultValues)
		if editable is not None:
			self.setEditable(editable)
		if multiValue is not None:
			self.setMultiValue(multiValue)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.editable is None:
			self.editable = True
		if self.multiValue is None:
			self.multiValue = False
		if self.possibleValues is None:
			self.possibleValues = []
		if self.defaultValues is None:
			self.defaultValues = []

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceConfigId(id)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def _updateValues(self):
		if self.possibleValues is None:
			self.possibleValues = []

		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if defaultValue not in self.possibleValues:
					self.defaultValues.remove(defaultValue)
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues

		if self.defaultValues and len(self.defaultValues) > 1:
			self.multiValue = True

		if self.possibleValues is not None:
			self.possibleValues.sort()

		if self.defaultValues is not None:
			self.defaultValues.sort()

	def getPossibleValues(self):
		return self.possibleValues

	def setPossibleValues(self, possibleValues):
		self.possibleValues = [value for value in set(forceList(possibleValues))]
		self._updateValues()

	def getDefaultValues(self):
		return self.defaultValues

	def setDefaultValues(self, defaultValues):
		self.defaultValues = [value for value in set(forceList(defaultValues))]
		self._updateValues()

	def getEditable(self):
		return self.editable

	def setEditable(self, editable):
		self.editable = forceBool(editable)

	def getMultiValue(self):
		return self.multiValue

	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if self.defaultValues is not None and len(self.defaultValues) > 1:
			self.multiValue = True

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Config'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Config')

	def __unicode__(self):
		return (
			u"<{klass}(id={id!r}, description={description!r}, "
			u"possibleValues={possibleValues!r}, defaultValues={defaults!r}, "
			u"editable={editable!r}, multiValue={multiValue!r})>".format(
				klass=self.getType(),
				id=self.id,
				description=self.description,
				possibleValues=self.possibleValues,
				defaults=self.defaultValues,
				editable=self.editable,
				multiValue=self.multiValue
			)
		)

Entity.subClasses['Config'] = Config


class UnicodeConfig(Config):
	subClasses = {}

	def __init__(self, id, description='', possibleValues=None,
				defaultValues=None, editable=None, multiValue=None):

		Config.__init__(self, id, description, possibleValues, defaultValues,
			editable, multiValue)

		if possibleValues is not None:
			self.setPossibleValues(possibleValues)
		if defaultValues is not None:
			self.setDefaultValues(defaultValues)

	def setDefaults(self):
		if self.possibleValues is None:
			self.possibleValues = [u'']
		if self.defaultValues is None:
			self.defaultValues = [u'']
		Config.setDefaults(self)

	def setPossibleValues(self, possibleValues):
		Config.setPossibleValues(self, forceUnicodeList(possibleValues))

	def setDefaultValues(self, defaultValues):
		Config.setDefaultValues(self, forceUnicodeList(defaultValues))

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'UnicodeConfig'

		return Config.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'UnicodeConfig')

Config.subClasses['UnicodeConfig'] = UnicodeConfig


class BoolConfig(Config):
	subClasses = {}

	def __init__(self, id, description=None, defaultValues=None):
		Config.__init__(self, id, description, [True, False], defaultValues,
			False, False)

	def setDefaults(self):
		if self.defaultValues is None:
			self.defaultValues = [False]
		Config.setDefaults(self)

	def setPossibleValues(self, possibleValues):
		Config.setPossibleValues(self, [True, False])

	def setDefaultValues(self, defaultValues):
		defaultValues = [value for value in set(forceBoolList(defaultValues))]
		if len(defaultValues) > 1:
			raise BackendBadValueError(u"Bool config cannot have multiple default values: %s" % defaultValues)
		Config.setDefaultValues(self, defaultValues)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'BoolConfig'

		return Config.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'BoolConfig')

	def __unicode__(self):
		return (
			u"<{klass}(id={id!r}, description={description!r}, "
			u"defaultValues={defaults!r})>".format(
				klass=self.getType(),
				id=self.id,
				description=self.description,
				defaults=self.defaultValues,
			)
		)

Config.subClasses['BoolConfig'] = BoolConfig


class ConfigState(Relationship):
	subClasses = {}
	backendMethodPrefix = 'configState'

	def __init__(self, configId, objectId, values=None):
		self.values = None
		self.setConfigId(configId)
		self.setObjectId(objectId)

		if values is not None:
			self.setValues(values)

	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.values is None:
			self.setValues([])

	def getObjectId(self):
		return self.objectId

	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)

	def getConfigId(self):
		return self.configId

	def setConfigId(self, configId):
		self.configId = forceConfigId(configId)

	def getValues(self):
		return self.values

	def setValues(self, values):
		self.values = forceList(values)
		self.values.sort()

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ConfigState'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ConfigState')

	def __unicode__(self):
		return u"<{0}(configId={1!r}, objectId={2!r}, values={3!r})>".format(self.getType(), self.configId, self.objectId, self.values)

Relationship.subClasses['ConfigState'] = ConfigState


class Product(Entity):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['productId']
	backendMethodPrefix = 'product'

	def __init__(self, id, productVersion, packageVersion, name=None,
				licenseRequired=None, setupScript=None, uninstallScript=None,
				updateScript=None, alwaysScript=None, onceScript=None,
				customScript=None, userLoginScript=None, priority=None,
				description=None, advice=None, changelog=None,
				productClassIds=None, windowsSoftwareIds=None):
		self.name = None
		self.licenseRequired = None
		self.setupScript = None
		self.uninstallScript = None
		self.updateScript = None
		self.alwaysScript = None
		self.onceScript = None
		self.customScript = None
		self.userLoginScript = None
		self.priority = None
		self.description = None
		self.advice = None
		self.changelog = None
		self.productClassIds = None
		self.windowsSoftwareIds = None
		self.setId(id)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)

		if name is not None:
			self.setName(name)
		if licenseRequired is not None:
			self.setLicenseRequired(licenseRequired)
		if setupScript is not None:
			self.setSetupScript(setupScript)
		if uninstallScript is not None:
			self.setUninstallScript(uninstallScript)
		if updateScript is not None:
			self.setUpdateScript(updateScript)
		if alwaysScript is not None:
			self.setAlwaysScript(alwaysScript)
		if onceScript is not None:
			self.setOnceScript(onceScript)
		if customScript is not None:
			self.setCustomScript(customScript)
		if userLoginScript is not None:
			self.setUserLoginScript(userLoginScript)
		if priority is not None:
			self.setPriority(priority)
		if description is not None:
			self.setDescription(description)
		if advice is not None:
			self.setAdvice(advice)
		if changelog is not None:
			self.setChangelog(changelog)
		if productClassIds is not None:
			self.setProductClassIds(productClassIds)
		if windowsSoftwareIds is not None:
			self.setWindowsSoftwareIds(windowsSoftwareIds)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.name is None:
			self.setName(u"")
		if self.licenseRequired is None:
			self.setLicenseRequired(False)
		if self.setupScript is None:
			self.setSetupScript(u"")
		if self.uninstallScript is None:
			self.setUninstallScript(u"")
		if self.updateScript is None:
			self.setUpdateScript(u"")
		if self.alwaysScript is None:
			self.setAlwaysScript(u"")
		if self.onceScript is None:
			self.setOnceScript(u"")
		if self.customScript is None:
			self.setCustomScript(u"")
		if self.userLoginScript is None:
			self.setUserLoginScript(u"")
		if self.priority is None:
			self.setPriority(0)
		if self.description is None:
			self.setDescription(u"")
		if self.advice is None:
			self.setAdvice(u"")
		if self.changelog is None:
			self.setChangelog(u"")
		if self.productClassIds is None:
			self.setProductClassIds([])
		if self.windowsSoftwareIds is None:
			self.setWindowsSoftwareIds([])

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceProductId(id)

	def getProductVersion(self):
		return self.productVersion

	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)

	def getPackageVersion(self):
		return self.packageVersion

	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = forceUnicode(name)

	def getLicenseRequired(self):
		return self.licenseRequired

	def setLicenseRequired(self, licenseRequired):
		self.licenseRequired = forceBool(licenseRequired)

	def getSetupScript(self):
		return self.setupScript

	def setSetupScript(self, setupScript):
		self.setupScript = forceFilename(setupScript)

	def getUninstallScript(self):
		return self.uninstallScript

	def setUninstallScript(self, uninstallScript):
		self.uninstallScript = forceFilename(uninstallScript)

	def getUpdateScript(self):
		return self.updateScript

	def setUpdateScript(self, updateScript):
		self.updateScript = forceFilename(updateScript)

	def getAlwaysScript(self):
		return self.alwaysScript

	def setAlwaysScript(self, alwaysScript):
		self.alwaysScript = forceFilename(alwaysScript)

	def getOnceScript(self):
		return self.onceScript

	def setOnceScript(self, onceScript):
		self.onceScript = forceFilename(onceScript)

	def getCustomScript(self):
		return self.customScript

	def setCustomScript(self, customScript):
		self.customScript = forceFilename(customScript)

	def getUserLoginScript(self):
		return self.userLoginScript

	def setUserLoginScript(self, userLoginScript):
		self.userLoginScript = forceFilename(userLoginScript)

	def getPriority(self):
		return self.priority

	def setPriority(self, priority):
		self.priority = forceProductPriority(priority)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def getAdvice(self):
		return self.advice

	def setAdvice(self, advice):
		self.advice = forceUnicode(advice)

	def getChangelog(self):
		return self.changelog

	def setChangelog(self, changelog):
		self.changelog = forceUnicode(changelog)

	def getProductClassIds(self):
		return self.productClassIds

	def setProductClassIds(self, productClassIds):
		self.productClassIds = forceUnicodeList(productClassIds)
		self.productClassIds.sort()

	def getWindowsSoftwareIds(self):
		return self.windowsSoftwareIds

	def setWindowsSoftwareIds(self, windowsSoftwareIds):
		self.windowsSoftwareIds = forceUnicodeList(windowsSoftwareIds)
		self.windowsSoftwareIds.sort()

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Product'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Product')

	def __unicode__(self):
		return (
			u"<{0}(id={1!r}, name={2!r}, productVersion={3!r}, "
			u"packageVersion={4!r})>".format(
				self.getType(), self.id, self.name, self.productVersion,
				self.packageVersion
			)
		)

Entity.subClasses['Product'] = Product


class LocalbootProduct(Product):
	subClasses = {}

	def __init__(self, id, productVersion, packageVersion, name=None,
				licenseRequired=None, setupScript=None, uninstallScript=None,
				updateScript=None, alwaysScript=None, onceScript=None,
				customScript=None, userLoginScript=None, priority=None,
				description=None, advice=None, changelog=None,
				productClassIds=None, windowsSoftwareIds=None):

		Product.__init__(self, id, productVersion, packageVersion, name,
			licenseRequired, setupScript, uninstallScript, updateScript,
			alwaysScript, onceScript, customScript, userLoginScript, priority,
			description, advice, changelog, productClassIds, windowsSoftwareIds)

	def setDefaults(self):
		Product.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'LocalbootProduct'

		return Product.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'LocalbootProduct')

Product.subClasses['LocalbootProduct'] = LocalbootProduct


class NetbootProduct(Product):
	subClasses = {}

	def __init__(self, id, productVersion, packageVersion, name=None,
				licenseRequired=None, setupScript=None, uninstallScript=None,
				updateScript=None, alwaysScript=None, onceScript=None,
				customScript=None, priority=None, description=None,
				advice=None, changelog=None, productClassIds=None,
				windowsSoftwareIds=None, pxeConfigTemplate=u''):

		Product.__init__(self, id, productVersion, packageVersion, name,
			licenseRequired, setupScript, uninstallScript, updateScript,
			alwaysScript, onceScript, customScript, None, priority,
			description, advice, changelog, productClassIds, windowsSoftwareIds)
		self.setPxeConfigTemplate(pxeConfigTemplate)

	def setDefaults(self):
		Product.setDefaults(self)

	def getPxeConfigTemplate(self):
		return self.pxeConfigTemplate

	def setPxeConfigTemplate(self, pxeConfigTemplate):
		if pxeConfigTemplate:
			self.pxeConfigTemplate = forceFilename(pxeConfigTemplate)
		else:
			self.pxeConfigTemplate = None

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'NetbootProduct'

		return Product.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'NetbootProduct')

Product.subClasses['NetbootProduct'] = NetbootProduct


class ProductProperty(Entity):
	subClasses = {}
	backendMethodPrefix = 'productProperty'

	def __init__(self, productId, productVersion, packageVersion, propertyId,
		description=None, possibleValues=None, defaultValues=None,
		editable=None, multiValue=None):
		self.description = None
		self.possibleValues = None
		self.defaultValues = None
		self.editable = None
		self.multiValue = None
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setPropertyId(propertyId)

		if description is not None:
			self.setDescription(description)
		if possibleValues is not None:
			self.setPossibleValues(possibleValues)
		if defaultValues is not None:
			self.setDefaultValues(defaultValues)
		if editable is not None:
			self.setEditable(editable)
		if multiValue is not None:
			self.setMultiValue(multiValue)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.possibleValues is None:
			self.setPossibleValues([])
		if self.defaultValues is None:
			self.setDefaultValues([])
		if self.editable is None:
			self.setEditable(True)
		if self.multiValue is None:
			self.setMultiValue(False)

	def getProductId(self):
		return self.productId

	def setProductId(self, productId):
		self.productId = forceProductId(productId)

	def getProductVersion(self):
		return self.productVersion

	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)

	def getPackageVersion(self):
		return self.packageVersion

	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)

	def getPropertyId(self):
		return self.propertyId

	def setPropertyId(self, propertyId):
		self.propertyId = forceProductPropertyId(propertyId)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def _updateValues(self):
		if self.possibleValues is None:
			self.possibleValues = []

		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if defaultValue not in self.possibleValues:
					self.defaultValues.remove(defaultValue)
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues

		if self.defaultValues and len(self.defaultValues) > 1:
			self.multiValue = True
		if self.possibleValues is not None:
			self.possibleValues.sort()
		if self.defaultValues is not None:
			self.defaultValues.sort()

	def getPossibleValues(self):
		return self.possibleValues

	def setPossibleValues(self, possibleValues):
		self.possibleValues = [value for value in set(forceList(possibleValues))]
		self._updateValues()

	def getDefaultValues(self):
		return self.defaultValues

	def setDefaultValues(self, defaultValues):
		self.defaultValues = [value for value in set(forceList(defaultValues))]
		self._updateValues()

	def getEditable(self):
		return self.editable

	def setEditable(self, editable):
		self.editable = forceBool(editable)

	def getMultiValue(self):
		return self.multiValue

	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if self.defaultValues is not None and len(self.defaultValues) > 1:
			self.multiValue = True

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductProperty'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductProperty')

	def __unicode__(self):
		def getAttributes():
			yield 'productId={0!r}'.format(self.productId)
			yield 'productVersion={0!r}'.format(self.productVersion)
			yield 'packageVersion={0!r}'.format(self.packageVersion)
			yield 'propertyId={0!r}'.format(self.propertyId)

			for attribute in ('description', 'defaultValues', 'possibleValues'):
				try:
					value = getattr(self, attribute)
					if value:
						yield '{0}={1!r}'.format(attribute, value)
				except AttributeError:
					pass

			for attribute in ('editable', 'multiValue'):
				try:
					value = getattr(self, attribute)
					if value is not None:
						yield '{0}={1!r}'.format(attribute, value)
				except AttributeError:
					pass

		return u"<{klass}({0})>".format(', '.join(getAttributes()),
										klass=self.__class__.__name__)

Entity.subClasses['ProductProperty'] = ProductProperty


class UnicodeProductProperty(ProductProperty):
	subClasses = {}

	def __init__(self, productId, productVersion, packageVersion, propertyId,
				description=None, possibleValues=None, defaultValues=None,
				editable=None, multiValue=None):

		ProductProperty.__init__(self, productId, productVersion,
			packageVersion, propertyId, description, possibleValues,
			defaultValues, editable, multiValue)

		self.possibleValues = None
		self.defaultValues = None
		if possibleValues is not None:
			self.setPossibleValues(possibleValues)
		if defaultValues is not None:
			self.setDefaultValues(defaultValues)

	def setDefaults(self):
		if self.possibleValues is None:
			self.possibleValues = [u'']
		if self.defaultValues is None:
			self.defaultValues = [u'']
		ProductProperty.setDefaults(self)

	def setPossibleValues(self, possibleValues):
		ProductProperty.setPossibleValues(self, forceUnicodeList(possibleValues))

	def setDefaultValues(self, defaultValues):
		ProductProperty.setDefaultValues(self, forceUnicodeList(defaultValues))

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'UnicodeProductProperty'

		return ProductProperty.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'UnicodeProductProperty')

ProductProperty.subClasses['UnicodeProductProperty'] = UnicodeProductProperty


class BoolProductProperty(ProductProperty):
	subClasses = {}

	def __init__(self, productId, productVersion, packageVersion, propertyId,
				description=None, defaultValues=None):

		ProductProperty.__init__(self, productId, productVersion,
			packageVersion, propertyId, description, [True, False],
			defaultValues, False, False)

		if self.defaultValues is not None and len(self.defaultValues) > 1:
			raise BackendBadValueError(u"Bool product property cannot have multiple default values: %s" % self.defaultValues)

	def setDefaults(self):
		if self.defaultValues is None:
			self.defaultValues = [False]
		ProductProperty.setDefaults(self)

	def setPossibleValues(self, possibleValues):
		ProductProperty.setPossibleValues(self, [True, False])

	def setDefaultValues(self, defaultValues):
		defaultValues = forceBoolList(defaultValues)
		if len(defaultValues) > 1:
			raise BackendBadValueError(u"Bool config cannot have multiple default values: %s" % defaultValues)
		ProductProperty.setDefaultValues(self, defaultValues)

	def setEditable(self, editable):
		self.editable = False

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'BoolProductProperty'

		return ProductProperty.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'BoolProductProperty')

	def __unicode__(self):
		def getAttributes():
			yield 'productId={0!r}'.format(self.productId)
			yield 'productVersion={0!r}'.format(self.productVersion)
			yield 'packageVersion={0!r}'.format(self.packageVersion)
			yield 'propertyId={0!r}'.format(self.propertyId)

			for attribute in ('description', 'defaultValues'):
				try:
					value = getattr(self, attribute)
					if value:
						yield '{0}={1!r}'.format(attribute, value)
				except AttributeError:
					pass

		return u"<{klass}({0})>".format(', '.join(getAttributes()),
										klass=self.__class__.__name__)

ProductProperty.subClasses['BoolProductProperty'] = BoolProductProperty


class ProductDependency(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productDependency'

	def __init__(self, productId, productVersion, packageVersion,
				productAction, requiredProductId, requiredProductVersion=None,
				requiredPackageVersion=None, requiredAction=None,
				requiredInstallationStatus=None, requirementType=None):
		self.requiredProductVersion = None
		self.requiredPackageVersion = None
		self.requiredAction = None
		self.requiredInstallationStatus = None
		self.requirementType = None
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setProductAction(productAction)
		self.setRequiredProductId(requiredProductId)

		if requiredProductVersion is not None:
			self.setRequiredProductVersion(requiredProductVersion)
		if requiredPackageVersion is not None:
			self.setRequiredPackageVersion(requiredPackageVersion)
		if requiredAction is not None:
			self.setRequiredAction(requiredAction)
		if requiredInstallationStatus is not None:
			self.setRequiredInstallationStatus(requiredInstallationStatus)
		if requirementType is not None:
			self.setRequirementType(requirementType)

	def setDefaults(self):
		Relationship.setDefaults(self)

	def getProductId(self):
		return self.productId

	def setProductId(self, productId):
		self.productId = forceProductId(productId)

	def getProductVersion(self):
		return self.productVersion

	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)

	def getPackageVersion(self):
		return self.packageVersion

	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)

	def getProductAction(self):
		return self.productAction

	def setProductAction(self, productAction):
		self.productAction = forceActionRequest(productAction)

	def getRequiredProductId(self):
		return self.requiredProductId

	def setRequiredProductId(self, requiredProductId):
		self.requiredProductId = forceProductId(requiredProductId)

	def getRequiredProductVersion(self):
		return self.requiredProductVersion

	def setRequiredProductVersion(self, requiredProductVersion):
		self.requiredProductVersion = forceProductVersion(requiredProductVersion)

	def getRequiredPackageVersion(self):
		return self.requiredPackageVersion

	def setRequiredPackageVersion(self, requiredPackageVersion):
		self.requiredPackageVersion = forcePackageVersion(requiredPackageVersion)

	def getRequiredAction(self):
		return self.requiredAction

	def setRequiredAction(self, requiredAction):
		self.requiredAction = forceActionRequest(requiredAction)

	def getRequiredInstallationStatus(self):
		return self.requiredInstallationStatus

	def setRequiredInstallationStatus(self, requiredInstallationStatus):
		self.requiredInstallationStatus = forceInstallationStatus(requiredInstallationStatus)

	def getRequirementType(self):
		return self.requirementType

	def setRequirementType(self, requirementType):
		self.requirementType = forceRequirementType(requirementType)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductDependency'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductDependency')

	def __unicode__(self):
		return (u"<{klass}(productId={prodId!r}, productVersion={prodVer!r}, "
				u"packageVersion={packVer!r}, productAction={prodAct!r}, "
				u"requiredProductId={reqProdId!r}>".format(
					klass=self.getType(), prodId=self.productId,
					prodVer=self.productVersion, packVer=self.packageVersion,
					prodAct=self.productAction,
					reqProdId=self.requiredProductId))

Relationship.subClasses['ProductDependency'] = ProductDependency


class ProductOnDepot(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productOnDepot'

	def __init__(self, productId, productType, productVersion, packageVersion,
				depotId, locked=None):
		self.locked = None
		self.setProductId(productId)
		self.setProductType(productType)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setDepotId(depotId)
		if locked is not None:
			self.setLocked(locked)

	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.locked is None:
			self.setLocked(False)

	def getProductId(self):
		return self.productId

	def setProductId(self, productId):
		self.productId = forceProductId(productId)

	def getProductType(self):
		return self.productType

	def setProductType(self, productType):
		self.productType = forceProductType(productType)

	def getProductVersion(self):
		return self.productVersion

	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)

	def getPackageVersion(self):
		return self.packageVersion

	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)

	def getDepotId(self):
		return self.depotId

	def setDepotId(self, depotId):
		self.depotId = forceHostId(depotId)

	def getLocked(self):
		return self.locked

	def setLocked(self, locked):
		self.locked = forceBool(locked)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductOnDepot'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductOnDepot')

Relationship.subClasses['ProductOnDepot'] = ProductOnDepot


class ProductOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productOnClient'

	def __init__(self, productId, productType, clientId,
				targetConfiguration=None, installationStatus=None,
				actionRequest=None, lastAction=None, actionProgress=None,
				actionResult=None, productVersion=None, packageVersion=None,
				modificationTime=None, actionSequence=None):
		self.targetConfiguration = None
		self.installationStatus = None
		self.actionRequest = None
		self.lastAction = None
		self.actionProgress = None
		self.actionResult = None
		self.productVersion = None
		self.packageVersion = None
		self.modificationTime = None
		self.actionSequence = -1
		self.setProductId(productId)
		self.setProductType(productType)
		self.setClientId(clientId)

		if targetConfiguration is not None:
			self.setTargetConfiguration(targetConfiguration)
		if installationStatus is not None:
			self.setInstallationStatus(installationStatus)
		if actionRequest is not None:
			self.setActionRequest(actionRequest)
		if lastAction is not None:
			self.setLastAction(lastAction)
		if actionProgress is not None:
			self.setActionProgress(actionProgress)
		if actionResult is not None:
			self.setActionResult(actionResult)
		if productVersion is not None:
			self.setProductVersion(productVersion)
		if packageVersion is not None:
			self.setPackageVersion(packageVersion)
		if modificationTime is not None:
			self.setModificationTime(modificationTime)
		if actionSequence is not None:
			self.setActionSequence(actionSequence)

	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.installationStatus is None:
			self.setInstallationStatus('not_installed')
		if self.actionRequest is None:
			self.setActionRequest('none')
		if self.modificationTime is None:
			self.setModificationTime(timestamp())

	def getProductId(self):
		return self.productId

	def setProductId(self, productId):
		self.productId = forceProductId(productId)

	def getProductType(self):
		return self.productType

	def setProductType(self, productType):
		self.productType = forceProductType(productType)

	def getClientId(self):
		return self.clientId

	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)

	def getTargetConfiguration(self):
		return self.targetConfiguration

	def setTargetConfiguration(self, targetConfiguration):
		self.targetConfiguration = forceProductTargetConfiguration(targetConfiguration)

	def getInstallationStatus(self):
		return self.installationStatus

	def setInstallationStatus(self, installationStatus):
		self.installationStatus = forceInstallationStatus(installationStatus)

	def getActionRequest(self):
		return self.actionRequest

	def setActionRequest(self, actionRequest):
		self.actionRequest = forceActionRequest(actionRequest)

	def getActionProgress(self):
		return self.actionProgress

	def setActionProgress(self, actionProgress):
		self.actionProgress = forceActionProgress(actionProgress)

	def getLastAction(self):
		return self.lastAction

	def setLastAction(self, lastAction):
		self.lastAction = forceActionRequest(lastAction)

	def getActionResult(self):
		return self.actionResult

	def setActionResult(self, actionResult):
		self.actionResult = forceActionResult(actionResult)

	def getProductVersion(self):
		return self.productVersion

	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)

	def getPackageVersion(self):
		return self.packageVersion

	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)

	def getModificationTime(self):
		return self.modificationTime

	def setModificationTime(self, modificationTime):
		self.modificationTime = forceOpsiTimestamp(modificationTime)

	def getActionSequence(self):
		return self.actionSequence

	def setActionSequence(self, actionSequence):
		self.actionSequence = forceInt(actionSequence)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductOnClient'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductOnClient')

	def __unicode__(self):
		return (u"<{klass}(clientId={clientId!r}, productId={prodId!r}, "
				u"installationStatus={status!r}, actionRequest={actReq!r})>".format(
					klass=self.getType(), clientId=self.clientId,
					prodId=self.productId, status=self.installationStatus,
					actReq=self.actionRequest))

Relationship.subClasses['ProductOnClient'] = ProductOnClient


class ProductPropertyState(Relationship):
	subClasses = {}
	backendMethodPrefix = 'productPropertyState'

	def __init__(self, productId, propertyId, objectId, values=None):
		self.values = None
		self.setProductId(productId)
		self.setPropertyId(propertyId)
		self.setObjectId(objectId)

		if values is not None:
			self.setValues(values)

	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.values is None:
			self.setValues([])

	def getProductId(self):
		return self.productId

	def setProductId(self, productId):
		self.productId = forceProductId(productId)

	def getObjectId(self):
		return self.objectId

	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)

	def getPropertyId(self):
		return self.propertyId

	def setPropertyId(self, propertyId):
		self.propertyId = forceProductPropertyId(propertyId)

	def getValues(self):
		return self.values

	def setValues(self, values):
		self.values = forceList(values)
		self.values.sort()

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductPropertyState'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductPropertyState')

	def __unicode__(self):
		def getAttributes():
			yield 'productId={0!r}'.format(self.productId)
			yield 'propertyId={0!r}'.format(self.propertyId)
			yield 'objectId={0!r}'.format(self.objectId)

			if self.values is not None:
				yield 'values={0!r}'.format(self.values)

		return u"<{klass}({0})>".format(', '.join(getAttributes()),
										klass=self.getType())

Relationship.subClasses['ProductPropertyState'] = ProductPropertyState


class Group(Object):
	subClasses = {}
	foreignIdAttributes = Object.foreignIdAttributes + ['groupId']
	backendMethodPrefix = 'group'

	def __init__(self, id, description=None, notes=None, parentGroupId=None):
		Object.__init__(self, id, description, notes)
		self.parentGroupId = None
		self.setId(id)

		if parentGroupId is not None:
			self.setParentGroupId(parentGroupId)

	def setDefaults(self):
		Object.setDefaults(self)

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceGroupId(id)

	def getParentGroupId(self):
		return self.parentGroupId

	def setParentGroupId(self, parentGroupId):
		self.parentGroupId = forceGroupId(parentGroupId)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'Group'

		return Object.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'Group')

	def __unicode__(self):
		return (u"<{klass}(id={id!r}, parentGroupId={parentId!r}>".format(
				klass=self.getType(), id=self.id, parentId=self.parentGroupId))

Object.subClasses['Group'] = Group


class HostGroup(Group):
	subClasses = {}

	def __init__(self, id, description=None, notes=None, parentGroupId=None):
		Group.__init__(self, id, description, notes, parentGroupId)

	def setDefaults(self):
		Group.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'HostGroup'

		return Group.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'HostGroup')

Group.subClasses['HostGroup'] = HostGroup


class ProductGroup(Group):
	subClasses = {}

	def __init__(self, id, description=None, notes=None, parentGroupId=None):
		Group.__init__(self, id, description, notes, parentGroupId)

	def setDefaults(self):
		Group.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ProductGroup'

		return Group.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ProductGroup')

Group.subClasses['ProductGroup'] = ProductGroup


class ObjectToGroup(Relationship):
	subClasses = {}
	backendMethodPrefix = 'objectToGroup'

	def __init__(self, groupType, groupId, objectId):
		self.setGroupType(groupType)
		self.setGroupId(groupId)
		self.setObjectId(objectId)

	def setDefaults(self):
		Relationship.setDefaults(self)

	def getGroupType(self):
		return self.groupType

	def setGroupType(self, groupType):
		self.groupType = forceGroupType(groupType)

	def getGroupId(self):
		return self.groupId

	def setGroupId(self, groupId):
		self.groupId = forceGroupId(groupId)

	def getObjectId(self):
		return self.objectId

	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ObjectToGroup'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ObjectToGroup')

Relationship.subClasses['ObjectToGroup'] = ObjectToGroup


class LicenseContract(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['licenseContractId']
	backendMethodPrefix = 'licenseContract'

	def __init__(self, id, description=None, notes=None, partner=None,
				conclusionDate=None, notificationDate=None,
				expirationDate=None):
		self.description = None
		self.notes = None
		self.partner = None
		self.conclusionDate = None
		self.notificationDate = None
		self.expirationDate = None
		self.setId(id)

		if description is not None:
			self.setDescription(description)
		if notes is not None:
			self.setNotes(notes)
		if partner is not None:
			self.setPartner(partner)
		if conclusionDate is not None:
			self.setConclusionDate(conclusionDate)
		if notificationDate is not None:
			self.setNotificationDate(notificationDate)
		if conclusionDate is not None:
			self.setExpirationDate(expirationDate)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.notes is None:
			self.setNotes(u"")
		if self.partner is None:
			self.setPartner(u"")
		if self.conclusionDate is None:
			self.setConclusionDate(timestamp())
		if self.notificationDate is None:
			self.setNotificationDate('0000-00-00 00:00:00')
		if self.expirationDate is None:
			self.setExpirationDate('0000-00-00 00:00:00')

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceLicenseContractId(id)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def getNotes(self):
		return self.notes

	def setNotes(self, notes):
		self.notes = forceUnicode(notes)

	def getPartner(self):
		return self.partner

	def setPartner(self, partner):
		self.partner = forceUnicode(partner)

	def getConclusionDate(self):
		return self.conclusionDate

	def setConclusionDate(self, conclusionDate):
		self.conclusionDate = forceOpsiTimestamp(conclusionDate)

	def getNotificationDate(self):
		return self.notificationDate

	def setNotificationDate(self, notificationDate):
		self.notificationDate = forceOpsiTimestamp(notificationDate)

	def getExpirationDate(self):
		return self.expirationDate

	def setExpirationDate(self, expirationDate):
		self.expirationDate = forceOpsiTimestamp(expirationDate)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'LicenseContract'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'LicenseContract')

	def __unicode__(self):
		infos = [u"id={0!r}".format(self.id)]

		if self.description:
			infos.append(u"description={0!r}".format(self.description))
		if self.partner:
			infos.append(u"partner={0!r}".format(self.partner))
		if self.conclusionDate:
			infos.append(u"conclusionDate={0!r}".format(self.conclusionDate))
		if self.notificationDate:
			infos.append(u"notificationDate={0!r}".format(self.notificationDate))
		if self.expirationDate:
			infos.append(u"expirationDate={0!r}".format(self.expirationDate))

		return u"<{0}({1})>".format(self.getType(), u', '.join(infos))

Entity.subClasses['LicenseContract'] = LicenseContract


class SoftwareLicense(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['softwareLicenseId']
	backendMethodPrefix = 'softwareLicense'

	def __init__(self, id, licenseContractId, maxInstallations=None,
				boundToHost=None, expirationDate=None):
		self.maxInstallations = None
		self.boundToHost = None
		self.expirationDate = None
		self.setId(id)
		self.setLicenseContractId(licenseContractId)

		if maxInstallations is not None:
			self.setMaxInstallations(maxInstallations)
		if boundToHost is not None:
			self.setBoundToHost(boundToHost)
		if expirationDate is not None:
			self.setExpirationDate(expirationDate)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.maxInstallations is None:
			self.setMaxInstallations(1)
		if self.expirationDate is None:
			self.setExpirationDate('0000-00-00 00:00:00')

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceSoftwareLicenseId(id)

	def getLicenseContractId(self):
		return self.licenseContractId

	def setLicenseContractId(self, licenseContractId):
		self.licenseContractId = forceLicenseContractId(licenseContractId)

	def getMaxInstallations(self):
		return self.maxInstallations

	def setMaxInstallations(self, maxInstallations):
		self.maxInstallations = forceUnsignedInt(maxInstallations)

	def getBoundToHost(self):
		return self.boundToHost

	def setBoundToHost(self, boundToHost):
		self.boundToHost = forceHostId(boundToHost)

	def getExpirationDate(self):
		return self.expirationDate

	def setExpirationDate(self, expirationDate):
		self.expirationDate = forceOpsiTimestamp(expirationDate)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'SoftwareLicense'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'SoftwareLicense')

	def __unicode__(self):
		infos = [
			u"id='{0}'".format(self.id),
			u"licenseContractId='{0}'".format(self.licenseContractId)
		]
		if self.maxInstallations:
			infos.append(u'maxInstallations={0}'.format(self.maxInstallations))
		if self.boundToHost:
			infos.append(u"boundToHost={0!r}".format(self.boundToHost))
		if self.expirationDate:
			infos.append(u"expirationDate={0!r}".format(self.expirationDate))

		return u"<{0}({1})>".format(self.getType(), u', '.join(infos))

Entity.subClasses['LicenseContract'] = LicenseContract


class RetailSoftwareLicense(SoftwareLicense):
	subClasses = {}

	def __init__(self, id, licenseContractId, maxInstallations=None,
				boundToHost=None, expirationDate=None):

		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations,
			boundToHost, expirationDate)

	def setDefaults(self):
		SoftwareLicense.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'RetailSoftwareLicense'

		return SoftwareLicense.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'RetailSoftwareLicense')

SoftwareLicense.subClasses['RetailSoftwareLicense'] = RetailSoftwareLicense


class OEMSoftwareLicense(SoftwareLicense):
	subClasses = {}

	def __init__(self, id, licenseContractId, maxInstallations=None,
				boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, 1, boundToHost,
			expirationDate)

	def setDefaults(self):
		SoftwareLicense.setDefaults(self)

	def setMaxInstallations(self, maxInstallations):
		maxInstallations = forceUnsignedInt(maxInstallations)
		if maxInstallations > 1:
			raise BackendBadValueError(u"OEM software license max installations can only be set to 1")
		self.maxInstallations = maxInstallations

	def setBoundToHost(self, boundToHost):
		self.boundToHost = forceHostId(boundToHost)
		if not self.boundToHost:
			raise BackendBadValueError(u"OEM software license requires boundToHost value")

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'OEMSoftwareLicense'

		return SoftwareLicense.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'OEMSoftwareLicense')

SoftwareLicense.subClasses['OEMSoftwareLicense'] = OEMSoftwareLicense


class VolumeSoftwareLicense(SoftwareLicense):
	subClasses = {}

	def __init__(self, id, licenseContractId, maxInstallations=None,
				boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations,
			boundToHost, expirationDate)

	def setDefaults(self):
		SoftwareLicense.setDefaults(self)
		if self.maxInstallations is None:
			self.setMaxInstallations(1)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'VolumeSoftwareLicense'

		return SoftwareLicense.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'VolumeSoftwareLicense')

SoftwareLicense.subClasses['VolumeSoftwareLicense'] = VolumeSoftwareLicense


class ConcurrentSoftwareLicense(SoftwareLicense):
	subClasses = {}

	def __init__(self, id, licenseContractId, maxInstallations=None,
				boundToHost=None, expirationDate=None):
		SoftwareLicense.__init__(self, id, licenseContractId, maxInstallations,
			boundToHost, expirationDate)

	def setDefaults(self):
		SoftwareLicense.setDefaults(self)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'ConcurrentSoftwareLicense'

		return SoftwareLicense.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'ConcurrentSoftwareLicense')

SoftwareLicense.subClasses['ConcurrentSoftwareLicense'] = ConcurrentSoftwareLicense


class LicensePool(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes + ['licensePoolId']
	backendMethodPrefix = 'licensePool'

	def __init__(self, id, description=None, productIds=None):
		self.description = None
		self.productIds = None
		self.setId(id)

		if description is not None:
			self.setDescription(description)
		if productIds is not None:
			self.setProductIds(productIds)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.description is None:
			self.setDescription(u"")
		if self.productIds is None:
			self.setProductIds([])

	def getId(self):
		return self.id

	def setId(self, id):
		self.id = forceLicensePoolId(id)

	def getDescription(self):
		return self.description

	def setDescription(self, description):
		self.description = forceUnicode(description)

	def getProductIds(self):
		return self.productIds

	def setProductIds(self, productIds):
		self.productIds = forceProductIdList(productIds)
		self.productIds.sort()

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'LicensePool'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'LicensePool')

	def __unicode__(self):
		infos = [u"id={0!r}".format(self.id)]

		if self.description:
			infos.append(u"description={0!r}".format(self.description))
		if self.productIds:
			infos.append(u"productIds={0!r}".format(self.productIds))

		return u"<{0}({1})>".format(self.getType(), u', '.join(infos))

Entity.subClasses['LicensePool'] = LicensePool


class AuditSoftwareToLicensePool(Relationship):
	subClasses = {}
	backendMethodPrefix = 'auditSoftwareToLicensePool'

	def __init__(self, name, version, subVersion, language, architecture,
				licensePoolId):
		self.setName(name)
		self.setVersion(version)
		self.setSubVersion(subVersion)
		self.setLanguage(language)
		self.setArchitecture(architecture)
		self.setLicensePoolId(licensePoolId)

	def getLicensePoolId(self):
		return self.licensePoolId

	def setLicensePoolId(self, licensePoolId):
		self.licensePoolId = forceLicensePoolId(licensePoolId)

	def setName(self, name):
		self.name = forceUnicode(name)

	def getName(self):
		return self.name

	def setVersion(self, version):
		if not version:
			self.version = u''
		else:
			self.version = forceUnicodeLower(version)

	def getVersion(self):
		return self.version

	def setSubVersion(self, subVersion):
		if not subVersion:
			self.subVersion = u''
		else:
			self.subVersion = forceUnicodeLower(subVersion)

	def getSubVersion(self):
		return self.subVersion

	def setLanguage(self, language):
		if not language:
			self.language = u''
		else:
			self.language = forceLanguageCode(language)

	def getLanguage(self):
		return self.language

	def setArchitecture(self, architecture):
		if not architecture:
			self.architecture = u''
		else:
			self.architecture = forceArchitecture(architecture)

	def getArchitecture(self):
		return self.architecture

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'AuditSoftwareToLicensePool'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'AuditSoftwareToLicensePool')

	def __unicode__(self):
		infos = [u"name={0}".format(self.name)]

		if self.version:
			infos.append(u"version={0!r}".format(self.version))
		if self.subVersion:
			infos.append(u"subVersion={0!r}".format(self.subVersion))
		if self.language:
			infos.append(u"language={0!r}".format(self.language))
		if self.architecture:
			infos.append(u"architecture={0!r}".format(self.architecture))
		if self.licensePoolId:
			infos.append(u"licensePoolId={0!r}".format(self.licensePoolId))

		return u"<{0}({1})>".format(self.getType(), u', '.join(infos))


Relationship.subClasses['AuditSoftwareToLicensePool'] = AuditSoftwareToLicensePool


class SoftwareLicenseToLicensePool(Relationship):
	subClasses = {}
	backendMethodPrefix = 'softwareLicenseToLicensePool'

	def __init__(self, softwareLicenseId, licensePoolId, licenseKey=None):
		self.licenseKey = None
		self.setSoftwareLicenseId(softwareLicenseId)
		self.setLicensePoolId(licensePoolId)

		if licenseKey is not None:
			self.setLicenseKey(licenseKey)

	def setDefaults(self):
		Relationship.setDefaults(self)

		if self.licenseKey is None:
			self.setLicenseKey(u'')

	def getSoftwareLicenseId(self):
		return self.softwareLicenseId

	def setSoftwareLicenseId(self, softwareLicenseId):
		self.softwareLicenseId = forceSoftwareLicenseId(softwareLicenseId)

	def getLicensePoolId(self):
		return self.licensePoolId

	def setLicensePoolId(self, licensePoolId):
		self.licensePoolId = forceLicensePoolId(licensePoolId)

	def getLicenseKey(self):
		return self.licenseKey

	def setLicenseKey(self, licenseKey):
		self.licenseKey = forceUnicode(licenseKey)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'SoftwareLicenseToLicensePool'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'SoftwareLicenseToLicensePool')

Relationship.subClasses['SoftwareLicenseToLicensePool'] = SoftwareLicenseToLicensePool


class LicenseOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'licenseOnClient'

	def __init__(self, softwareLicenseId, licensePoolId, clientId,
				licenseKey=None, notes=None):
		self.licenseKey = None
		self.notes = None
		self.setSoftwareLicenseId(softwareLicenseId)
		self.setLicensePoolId(licensePoolId)
		self.setClientId(clientId)

		if licenseKey is not None:
			self.setLicenseKey(licenseKey)
		if notes is not None:
			self.setNotes(notes)

	def setDefaults(self):
		Relationship.setDefaults(self)

		if self.licenseKey is None:
			self.setLicenseKey(u'')
		if self.notes is None:
			self.setNotes(u'')

	def getSoftwareLicenseId(self):
		return self.softwareLicenseId

	def setSoftwareLicenseId(self, softwareLicenseId):
		self.softwareLicenseId = forceSoftwareLicenseId(softwareLicenseId)

	def getLicensePoolId(self):
		return self.licensePoolId

	def setLicensePoolId(self, licensePoolId):
		self.licensePoolId = forceLicensePoolId(licensePoolId)

	def getClientId(self):
		return self.clientId

	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)

	def getLicenseKey(self):
		return self.licenseKey

	def setLicenseKey(self, licenseKey):
		self.licenseKey = forceUnicode(licenseKey)

	def getNotes(self):
		return self.notes

	def setNotes(self, notes):
		self.notes = forceUnicode(notes)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'LicenseOnClient'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'LicenseOnClient')

Relationship.subClasses['LicenseOnClient'] = LicenseOnClient


class AuditSoftware(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes
	backendMethodPrefix = 'auditSoftware'

	def __init__(self, name, version, subVersion, language, architecture,
				windowsSoftwareId=None, windowsDisplayName=None,
				windowsDisplayVersion=None, installSize=None):
		self.windowsSoftwareId = None
		self.windowsDisplayName = None
		self.windowsDisplayVersion = None
		self.installSize = None
		self.setName(name)
		self.setVersion(version)
		self.setSubVersion(subVersion)
		self.setLanguage(language)
		self.setArchitecture(architecture)

		if windowsSoftwareId is not None:
			self.setWindowsSoftwareId(windowsSoftwareId)
		if windowsDisplayName is not None:
			self.setWindowsDisplayName(windowsDisplayName)
		if windowsDisplayVersion is not None:
			self.setWindowsDisplayVersion(windowsDisplayVersion)
		if installSize is not None:
			self.setInstallSize(installSize)

	def setDefaults(self):
		Entity.setDefaults(self)
		if self.installSize is None:
			self.setInstallSize(0)

	def setName(self, name):
		self.name = forceUnicode(name)

	def getName(self):
		return self.name

	def setVersion(self, version):
		self.version = forceUnicodeLower(version)

	def getVersion(self):
		return self.version

	def setSubVersion(self, subVersion):
		self.subVersion = forceUnicodeLower(subVersion)

	def getSubVersion(self):
		return self.subVersion

	def setLanguage(self, language):
		if not language:
			self.language = u''
		else:
			self.language = forceLanguageCode(language)

	def getLanguage(self):
		return self.language

	def setArchitecture(self, architecture):
		if not architecture:
			self.architecture = u''
		else:
			self.architecture = forceArchitecture(architecture)

	def getArchitecture(self):
		return self.architecture

	def getWindowsSoftwareId(self):
		return self.windowsSoftwareId

	def setWindowsSoftwareId(self, windowsSoftwareId):
		self.windowsSoftwareId = forceUnicodeLower(windowsSoftwareId)

	def getWindowsDisplayName(self):
		return self.windowsDisplayName

	def setWindowsDisplayName(self, windowsDisplayName):
		self.windowsDisplayName = forceUnicode(windowsDisplayName)

	def getWindowsDisplayVersion(self):
		return self.windowsDisplayVersion

	def setWindowsDisplayVersion(self, windowsDisplayVersion):
		self.windowsDisplayVersion = forceUnicode(windowsDisplayVersion)

	def getInstallSize(self):
		return self.installSize

	def setInstallSize(self, installSize):
		self.installSize = forceInt(installSize)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'AuditSoftware'

		return Entity.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'AuditSoftware')

Entity.subClasses['AuditSoftware'] = AuditSoftware


class AuditSoftwareOnClient(Relationship):
	subClasses = {}
	backendMethodPrefix = 'auditSoftwareOnClient'

	def __init__(self, name, version, subVersion, language, architecture,
				clientId, uninstallString=None, binaryName=None,
				firstseen=None, lastseen=None, state=None,
				usageFrequency=None, lastUsed=None, licenseKey=None):
		self.uninstallString = None
		self.binaryName = None
		self.firstseen = None
		self.lastseen = None
		self.state = None
		self.usageFrequency = None
		self.lastUsed = None
		self.licenseKey = None
		self.setName(name)
		self.setVersion(version)
		self.setSubVersion(subVersion)
		self.setLanguage(language)
		self.setArchitecture(architecture)
		self.setClientId(clientId)

		if uninstallString is not None:
			self.setUninstallString(uninstallString)
		if binaryName is not None:
			self.setBinaryName(binaryName)
		if firstseen is not None:
			self.setFirstseen(firstseen)
		if lastseen is not None:
			self.setLastseen(lastseen)
		if state is not None:
			self.setState(state)
		if usageFrequency is not None:
			self.setUsageFrequency(usageFrequency)
		if lastUsed is not None:
			self.setLastUsed(lastUsed)
		if licenseKey is not None:
			self.setLicenseKey(licenseKey)

	def setDefaults(self):
		Relationship.setDefaults(self)

		if self.uninstallString is None:
			self.setUninstallString(u"")
		if self.binaryName is None:
			self.setBinaryName(u"")
		if self.firstseen is None:
			self.setFirstseen(timestamp())
		if self.lastseen is None:
			self.setLastseen(timestamp())
		if self.state is None:
			self.setState(1)
		if self.usageFrequency is None:
			self.setUsageFrequency(-1)
		if self.lastUsed is None:
			self.setLastUsed('0000-00-00 00:00:00')

	def setName(self, name):
		self.name = forceUnicode(name)

	def getName(self):
		return self.name

	def setVersion(self, version):
		self.version = forceUnicodeLower(version)

	def getVersion(self):
		return self.version

	def setSubVersion(self, subVersion):
		self.subVersion = forceUnicodeLower(subVersion)

	def getSubVersion(self):
		return self.subVersion

	def setLanguage(self, language):
		if not language:
			self.language = u''
		else:
			self.language = forceLanguageCode(language)

	def getLanguage(self):
		return self.language

	def setArchitecture(self, architecture):
		if not architecture:
			self.architecture = u''
		else:
			self.architecture = forceArchitecture(architecture)

	def getArchitecture(self):
		return self.architecture

	def getClientId(self):
		return self.clientId

	def setClientId(self, clientId):
		self.clientId = forceHostId(clientId)

	def getUninstallString(self):
		return self.uninstallString

	def setUninstallString(self, uninstallString):
		self.uninstallString = forceUnicode(uninstallString)

	def getBinaryName(self):
		return self.binaryName

	def setBinaryName(self, binaryName):
		self.binaryName = forceUnicode(binaryName)

	def getFirstseen(self):
		return self.firstseen

	def setFirstseen(self, firstseen):
		self.firstseen = forceOpsiTimestamp(firstseen)

	def getLastseen(self):
		return self.firstseen

	def setLastseen(self, lastseen):
		self.lastseen = forceOpsiTimestamp(lastseen)

	def getState(self):
		return self.state

	def setState(self, state):
		self.state = forceAuditState(state)

	def getUsageFrequency(self):
		return self.usageFrequency

	def setUsageFrequency(self, usageFrequency):
		self.usageFrequency = forceInt(usageFrequency)

	def getLastUsed(self):
		return self.lastUsed

	def setLastUsed(self, lastUsed):
		self.lastUsed = forceOpsiTimestamp(lastUsed)

	def getLicenseKey(self):
		return self.licenseKey

	def setLicenseKey(self, licenseKey):
		self.licenseKey = forceUnicode(licenseKey)

	@staticmethod
	def fromHash(hash):
		try:
			hash['type']
		except KeyError:
			hash['type'] = 'AuditSoftwareOnClient'

		return Relationship.fromHash(hash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'AuditSoftwareOnClient')

Relationship.subClasses['AuditSoftwareOnClient'] = AuditSoftwareOnClient


class AuditHardware(Entity):
	subClasses = {}
	foreignIdAttributes = Entity.foreignIdAttributes
	backendMethodPrefix = 'auditHardware'
	hardwareAttributes = {}

	def __init__(self, hardwareClass, **kwargs):
		self.setHardwareClass(hardwareClass)
		for attribute in self.hardwareAttributes.get(hardwareClass, {}):
			if attribute not in kwargs:
				lowAttr = attribute.lower()
				try:
					kwargs[attribute] = kwargs[lowAttr]
					del kwargs[lowAttr]
				except KeyError:
					kwargs[attribute] = None

		if self.hardwareAttributes.get(hardwareClass):
			for (attribute, value) in kwargs.items():
				attrType = self.hardwareAttributes[hardwareClass].get(attribute)
				if not attrType:
					del kwargs[attribute]
					continue
				if value is None:
					continue

				if attrType.startswith('varchar'):
					kwargs[attribute] = forceUnicode(value).strip()
					try:
						size = int(attrType.split('(')[1].split(')')[0].strip())

						if len(kwargs[attribute]) > size:
							logger.warning(u'Truncating value of attribute %s of hardware class %s to length %d' % (attribute, hardwareClass, size))
							kwargs[attribute] = kwargs[attribute][:size].strip()
					except (ValueError, IndexError):
						pass
				elif 'int' in attrType:
					try:
						kwargs[attribute] = forceInt(value)
					except Exception as e:
						logger.debug2(e)
						kwargs[attribute] = None
				elif attrType == 'double':
					try:
						kwargs[attribute] = forceFloat(value)
					except Exception as e:
						logger.debug2(e)
						kwargs[attribute] = None
				else:
					raise BackendConfigurationError(u"Attribute '%s' of hardware class '%s' has unknown type '%s'" % (attribute, hardwareClass, type))
		else:
			for (attribute, value) in kwargs.items():
				if isinstance(value, str):
					kwargs[attribute] = forceUnicode(value).strip()

		self.__dict__.update(kwargs)

		try:
			if self.vendorId:
				self.vendorId = forceHardwareVendorId(self.vendorId)
		except AttributeError:
			pass

		try:
			if self.subsystemVendorId:
				self.subsystemVendorId = forceHardwareVendorId(self.subsystemVendorId)
		except AttributeError:
			pass

		try:
			if self.deviceId:
				self.deviceId = forceHardwareDeviceId(self.deviceId)
		except AttributeError:
			pass

		try:
			if self.subsystemDeviceId:
				self.subsystemDeviceId = forceHardwareDeviceId(self.subsystemDeviceId)
		except AttributeError:
			pass

	@staticmethod
	def setHardwareConfig(hardwareConfig):
		hardwareAttributes = {}
		for config in hardwareConfig:
			hwClass = config['Class']['Opsi']
			hardwareAttributes[hwClass] = {}
			for value in config['Values']:
				if value["Scope"] == 'g':
					hardwareAttributes[hwClass][value['Opsi']] = value["Type"]
		AuditHardware.hardwareAttributes = hardwareAttributes

	def setDefaults(self):
		Entity.setDefaults(self)

	def setHardwareClass(self, hardwareClass):
		self.hardwareClass = forceUnicode(hardwareClass)

	def getHardwareClass(self):
		return self.hardwareClass

	def getIdentAttributes(self):
		attributes = self.hardwareAttributes.get(self.hardwareClass, {}).keys()
		attributes.sort()
		attributes.insert(0, 'hardwareClass')
		return attributes

	def serialize(self):
		return self.toHash()

	@staticmethod
	def fromHash(hash):
		initHash = {
			key: value
			for key, value in hash.items()
			if key != 'type'
		}

		return AuditHardware(**initHash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'AuditHardware')

	def __unicode__(self):
		infos = []
		hardwareClass = self.getHardwareClass()
		if hardwareClass:
			infos.append(u"hardwareClass={0!r}".format(hardwareClass))

		try:
			infos.append(u"name={0!r}".format(self.name))
		except AttributeError:
			pass

		try:
			if self.vendorId:
				infos.append(u"vendorId={0!r}".format(self.vendorId))
		except AttributeError:
			pass

		try:
			if self.subsystemVendorId:
				infos.append(u"subsystemVendorId={0!r}".format(self.subsystemVendorId))
		except AttributeError:
			pass

		try:
			if self.deviceId:
				infos.append(u"deviceId={0!r}".format(self.deviceId))
		except AttributeError:
			pass

		try:
			if self.subsystemDeviceId:
				infos.append(u"subsystemDeviceId={0!r}".format(self.subsystemDeviceId))
		except AttributeError:
			pass

		return u"<{0}({1})>".format(self.__class__.__name__, u', '.join(infos))

Entity.subClasses['AuditHardware'] = AuditHardware


class AuditHardwareOnHost(Relationship):
	subClasses = {}
	backendMethodPrefix = 'auditHardwareOnHost'
	hardwareAttributes = {}

	def __init__(self, hardwareClass, hostId, firstseen=None, lastseen=None,
				state=None, **kwargs):
		self.firstseen = None
		self.lastseen = None
		self.state = None
		self.setHostId(hostId)
		self.setHardwareClass(hardwareClass)

		for attribute in self.hardwareAttributes.get(hardwareClass, {}):
			if attribute not in kwargs:
				lowerAttribute = attribute.lower()
				try:
					kwargs[attribute] = kwargs[lowerAttribute]
					del kwargs[lowerAttribute]
				except KeyError:
					kwargs[attribute] = None

		if self.hardwareAttributes.get(hardwareClass):
			for (attribute, value) in kwargs.items():
				attrType = self.hardwareAttributes[hardwareClass].get(attribute)
				if not attrType:
					del kwargs[attribute]
					continue
				if value is None:
					continue

				if attrType.startswith('varchar'):
					kwargs[attribute] = forceUnicode(value).strip()
					try:
						size = int(attrType.split('(')[1].split(')')[0].strip())

						if len(kwargs[attribute]) > size:
							logger.warning(u'Truncating value of attribute %s of hardware class %s to length %d' % (attribute, hardwareClass, size))
							kwargs[attribute] = kwargs[attribute][:size].strip()
					except (ValueError, IndexError):
						pass
				elif 'int' in attrType:
					try:
						kwargs[attribute] = forceInt(value)
					except Exception as e:
						logger.debug2(e)
						kwargs[attribute] = None
				elif attrType == 'double':
					try:
						kwargs[attribute] = forceFloat(value)
					except Exception as e:
						logger.debug2(e)
						kwargs[attribute] = None
				else:
					raise BackendConfigurationError(u"Attribute '%s' of hardware class '%s' has unknown type '%s'" % (attribute, hardwareClass, type))
		else:
			for (attribute, value) in kwargs.items():
				if isinstance(value, str):
					kwargs[attribute] = forceUnicode(value).strip()

		self.__dict__.update(kwargs)
		if firstseen is not None:
			self.setFirstseen(firstseen)
		if lastseen is not None:
			self.setLastseen(lastseen)
		if state is not None:
			self.setState(state)

		try:
			if self.vendorId:
				self.vendorId = forceHardwareVendorId(self.vendorId)
		except AttributeError:
			pass

		try:
			if self.subsystemVendorId:
				self.subsystemVendorId = forceHardwareVendorId(self.subsystemVendorId)
		except AttributeError:
			pass

		try:
			if self.deviceId:
				self.deviceId = forceHardwareDeviceId(self.deviceId)
		except AttributeError:
			pass

		try:
			if self.subsystemDeviceId:
				self.subsystemDeviceId = forceHardwareDeviceId(self.subsystemDeviceId)
		except AttributeError:
			pass

	@staticmethod
	def setHardwareConfig(hardwareConfig):
		hardwareAttributes = {}
		for config in hardwareConfig:
			hwClass = config['Class']['Opsi']
			hardwareAttributes[hwClass] = {}
			for value in config['Values']:
				hardwareAttributes[hwClass][value['Opsi']] = value["Type"]
		AuditHardwareOnHost.hardwareAttributes = hardwareAttributes

	def setDefaults(self):
		Relationship.setDefaults(self)
		if self.firstseen is None:
			self.setFirstseen(timestamp())
		if self.lastseen is None:
			self.setLastseen(timestamp())
		if self.state is None:
			self.setState(1)

	def getHostId(self):
		return self.hostId

	def setHostId(self, hostId):
		self.hostId = forceHostId(hostId)

	def setHardwareClass(self, hardwareClass):
		self.hardwareClass = forceUnicode(hardwareClass)

	def getHardwareClass(self):
		return self.hardwareClass

	def getFirstseen(self):
		return self.firstseen

	def setFirstseen(self, firstseen):
		self.firstseen = forceOpsiTimestamp(firstseen)

	def getLastseen(self):
		return self.firstseen

	def setLastseen(self, lastseen):
		self.lastseen = forceOpsiTimestamp(lastseen)

	def getState(self):
		return self.state

	def setState(self, state):
		self.state = forceAuditState(state)

	def toAuditHardware(self):
		auditHardwareHash = {'type': 'AuditHardware'}
		attributes = set(AuditHardware.hardwareAttributes.get(self.getHardwareClass(), {}).keys())

		for (attribute, value) in self.toHash():
			if attribute == 'type':
				continue

			if attribute == 'hardwareClass':
				auditHardwareHash[attribute] = value
				continue

			if attribute in attributes:
				auditHardwareHash[attribute] = value

		return AuditHardware.fromHash(auditHardwareHash)

	def getIdentAttributes(self):
		attributes = self.hardwareAttributes.get(self.hardwareClass, {}).keys()
		attributes.sort()
		attributes.insert(0, 'hostId')
		attributes.insert(0, 'hardwareClass')
		return attributes

	def serialize(self):
		return self.toHash()

	@staticmethod
	def fromHash(hash):
		initHash = {
			key: value
			for key, value in hash.items()
			if key != 'type'
		}

		return AuditHardwareOnHost(**initHash)

	@staticmethod
	def fromJson(jsonString):
		return fromJson(jsonString, 'AuditHardwareOnHost')

	def __unicode__(self):
		additional = [u"hostId={0!r}".format(self.hostId)]
		hardwareClass = self.getHardwareClass()
		if hardwareClass:
			additional.append(u"hardwareClass={0!r}".format(hardwareClass))

		try:
			additional.append(u"name={0!r}".format(forceUnicode(self.name)))
		except AttributeError:
			pass

		return u"<{type}({additional})>".format(
			type=self.getType(),
			additional=u', '.join(additional)
		)

Relationship.subClasses['AuditHardwareOnHost'] = AuditHardwareOnHost
