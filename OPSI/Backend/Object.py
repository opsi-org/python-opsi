#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Object    =
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

import json, re, copy, time, inspect


def forceList(var):
	if not type(var) is list:
		var = [ var ]
	return var

def forceUnicode(var):
	if type(var) is unicode:
		return var
	if not type(var) is str:
		var = str(var)
	return unicode(var, 'utf-8', 'replace')

def forceUnicodeLower(var):
	return forceUnicode(var).lower()

def forceUnicodeList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceUnicode(var[i])
	return var

def forceUnicodeLowerList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceUnicodeLower(var[i])
	return var

def forceBool(var):
	if type(var) is bool:
		return var
	if type(var) in (unicode, str):
		if var.lower() in ('true', 'yes', 'on', '1'):
			return True
		elif var.lower() in ('false', 'no', 'off', '0'):
			return False
	return bool(var)

def forceBoolList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceBool(var[i])
	return var

def forceInt(var):
	if type(var) is int:
		return var
	try:
		return int(var)
	except Exception, e:
		raise BackendBadValueError(u"Bad int value '%s': %s" % (var, e))

def forceDict(var):
	if type(var) is dict:
		return var
	raise BackendBadValueError(u"Not a dict '%s'")

opsiTimestampRegex = re.compile('^(\d{4})-?(\d{2})-?(\d{2})\s?(\d{2}):?(\d{2}):?(\d{2})$')
def forceOpsiTimestamp(var):
	if not var:
		var = u'0000-00-00 00:00:00'
	var = forceUnicode(var)
	match = re.search(opsiTimestampRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad opsi timestamp: '%s'" % var)
	return u'%s-%s-%s %s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )

hostIdRegex = re.compile('^[a-z0-9][a-z0-9\-]{,63}\.[a-z0-9][a-z0-9\-]*\.[a-z]{2,}$')
def forceHostId(var):
	var = forceObjectId(var)
	match = re.search(hostIdRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad host id: '%s'" % var)
	return var

def forceHostIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceHostId(var[i])
	return var

hardwareAddressRegex = re.compile('^([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})$')
def forceHardwareAddress(var):
	var = forceUnicodeLower(var)
	if not var:
		return var
	match = re.search(hardwareAddressRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad hardware address: %s" % var)
	return u'%s:%s:%s:%s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )

ipAddressRegex = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
def forceIPAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(ipAddressRegex, var):
		raise BackendBadValueError(u"Bad ip address: '%s'" % var)
	return var

networkAddressRegex = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/([0-3][0-9]*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$')
def forceNetworkAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(networkAddressRegex, var):
		raise BackendBadValueError(u"Bad network address: '%s'" % var)
	return var

urlRegex = re.compile('^[a-z0-9]+://[/a-z0-9]')
def forceUrl(var):
	var = forceUnicodeLower(var)
	if not re.search(urlRegex, var):
		raise BackendBadValueError(u"Bad url: '%s'" % var)
	return var

opsiHostKeyRegex = re.compile('^[0-9a-f]{32}$')
def forceOpsiHostKey(var):
	var = forceUnicodeLower(var)
	if not re.search(opsiHostKeyRegex, var):
		raise BackendBadValueError(u"Bad opsi host key: '%s'" % var)
	return var

productVersionRegex = re.compile('^[\w\.]+$')
def forceProductVersion(var):
	var = forceUnicode(var)
	match = re.search(productVersionRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: '%s'" % var)
	return var

packageVersionRegex = re.compile('^[\w\.]+$')
def forcePackageVersion(var):
	var = forceUnicode(var)
	match = re.search(packageVersionRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: '%s'" % var)
	return var
	
productIdRegex = re.compile('^[a-zA-Z0-9\_\.-]+$')
def forceProductId(var):
	var = forceObjectId(var)
	match = re.search(productIdRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: '%s'" % var)
	return var

def forceFilename(var):
	return forceUnicode(var)

def forceInstallationStatus(var):
	var = forceUnicodeLower(var)
	if var and var not in ('installed', 'not_installed'):
		raise BackendBadValueError(u"Bad installation status: '%s'" % var)
	return var

def forceActionRequest(var):
	var = forceUnicodeLower(var)
	if var and var not in ('setup', 'uninstall', 'update', 'always', 'once', 'none'):
		raise BackendBadValueError(u"Bad action request: '%s'" % var)
	return var

def forceActionProgress(var):
	return forceUnicode(var)

def forceObjectClass(var, objectClass):
	if type(var) in (unicode, str):
		try:
			var = json.loads(var)
		except Exception, e:
			logger.debug(e)
	
	if type(var) is dict and var.has_key('type'):
		try:
			c = eval(var['type'])
			if issubclass(c, objectClass):
				var = c.fromHash(var)
		except Exception, e:
			logger.debug(e)
	
	if not isinstance(var, objectClass):
		raise BackendBadValueError(u"Not a %s: '%s'" % (objectClass, var))
	return var
	
def forceObjectClassList(var, objectClass):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceObjectClass(var[i], objectClass)
	return var

groupIdRegex = re.compile('^[a-z0-9][a-z0-9-_. ]*$')
def forceGroupId(var):
	var = forceObjectId(var)
	match = re.search(groupIdRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad group id: '%s'" % var)
	return var

def forceObjectId(var):
	return forceUnicodeLower(var)

def forceObjectIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceObjectId(var[i])
	return var

domainRegex = re.compile('^[a-z0-9][a-z0-9\-]*\.[a-z]{2,}$')
def forceDomain(var):
	var = forceUnicodeLower(var)
	match = re.search(domainRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad domain: '%s'" % var)
	return var

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                      EXCEPTION CLASSES                                             =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class OpsiError(Exception):
	""" Base class for OPSI Backend exceptions. """
	
	ExceptionShortDescription = "OPSI-Backend generic exception"
	_message = None
	
	def __init__(self, message = ''):
		self._message = forceUnicode(message)
	
	def __unicode__(self):
		if self._message:
			return u"%s: %s" % (self.ExceptionShortDescription, self._message)
		else:
			return u"%s" % self.ExceptionShortDescription
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
	complete_message = __unicode__
	
	def message():
		def get(self):
			return self._message
		def set(self, message):
			self._message = forceUnicode(message)
		return property(get, set)
	
	
class BackendError(OpsiError):
	""" Exception raised if there is an error in the backend. """
	ExceptionShortDescription = u"Backend error"

class BackendIOError(OpsiError):
	""" Exception raised if there is a read or write error in the backend. """
	ExceptionShortDescription = u"Backend I/O error"

class BackendReferentialIntegrityError(OpsiError):
	""" Exception raised if there is a referential integration error occurs in the backend. """
	ExceptionShortDescription = u"Backend referential integrity error"

class BackendBadValueError(OpsiError):
	""" Exception raised if a malformed value is found. """
	ExceptionShortDescription = u"Backend bad value error"

class BackendMissingDataError(OpsiError):
	""" Exception raised if expected data not found. """
	ExceptionShortDescription = u"Backend missing data error"

class BackendAuthenticationError(OpsiError):
	""" Exception raised if authentication failes. """
	ExceptionShortDescription = u"Backend authentication error"

class BackendPermissionDeniedError(OpsiError):
	""" Exception raised if a permission is denied. """
	ExceptionShortDescription = u"Backend permission denied error"

class BackendTemporaryError(OpsiError):
	""" Exception raised if a temporary error occurs. """
	ExceptionShortDescription = u"Backend temporary error"

class BackendUnaccomplishableError(OpsiError):
	""" Exception raised if a temporary error occurs. """
	ExceptionShortDescription = u"Backend unaccomplishable error"

class BackendModuleDisabledError(OpsiError):
	""" Exception raised if a needed module is disabled. """
	ExceptionShortDescription = u"Backend module disabled error"

class LicenseConfigurationError(OpsiError):
	""" Exception raised if a configuration error occurs in the license data base. """
	ExceptionShortDescription = u"License configuration error"

class LicenseMissingError(OpsiError):
	""" Exception raised if a license is requested but cannot be found. """
	ExceptionShortDescription = u"License missing error"










def mandatoryConstructorArgs(Class):
	(args, varargs, varkwargs, defaults) = inspect.getargspec(Class.__init__)
	return args[1:][:-1*len(defaults)]
	
class Entity(object):
	subClasses = {}
	
	def getType(self):
		return self.__class__.__name__
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Entity'
		Class = eval(hash['type'])
		kwargs = {}
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		return Class(**kwargs)
	
	def toHash(self):
		hash = copy.deepcopy(self.__dict__)
		hash['type'] = self.getType()
		return hash
	
	@staticmethod
	def fromJson(jsonString):
		return Entity.fromHash(json.loads(jsonString))
	
	def toJson(self):
		return json.dumps(self.toHash())
	
	def __unicode__(self):
		return u"<%s'>" % self.getType()
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__

class Relationship(object):
	subClasses = {}
	
	def getType(self):
		return self.__class__.__name__
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Relationship'
		Class = eval(hash['type'])
		kwargs = {}
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		return Class(**kwargs)
	
	def toHash(self):
		return copy.deepcopy(self.__dict__)
	
	@staticmethod
	def fromJson(jsonString):
		return Relationship.fromHash(json.loads(jsonString))
	
	def toJson(self):
		return json.dumps(self.toHash())
	
	def __unicode__(self):
		return u"<%s'>" % self.getType()
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__

class Object(Entity):
	subClasses = {}
	
	def __init__(self, id, description='', notes=''):
		self.setId(id)
		self.setDescription(description)
		self.setNotes(notes)
	
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
		if not hash.has_key('type'): hash['type'] = 'Object'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Object.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s'>" \
			% (self.getType(), self.id, self.description, self.notes)

Entity.subClasses['Object'] = Object

class Host(Object):
	subClasses = {}
	
	def __init__(self, id, description='', notes='', hardwareAddress='', ipAddress=''):
		Object.__init__(self, id, description, notes)
		self.setId(id)
		self.setHardwareAddress(hardwareAddress)
		self.setIpAddress(ipAddress)
	
	def setId(self, id):
		self.id = forceHostId(id)
	
	def getHardwareAddress(self):
		return self.hardwareAddress
	
	def setHardwareAddress(self, hardwareAddress):
		if not hardwareAddress:
			self.hardwareAddress = u''
		else:
			self.hardwareAddress = forceHardwareAddress(hardwareAddress)
	
	def getIpAddress(self):
		return self.ipAddress
	
	def setIpAddress(self, ipAddress):
		if not ipAddress:
			self.ipAddress = u''
		else:
			self.ipAddress = forceIPAddress(ipAddress)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Host'
		return Object.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Host.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
	
Object.subClasses['Host'] = Host

class OpsiClient(Host):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', description='', notes='', hardwareAddress='', ipAddress='', created='', lastSeen=''):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress)
		self.setLastSeen(lastSeen)
		self.setCreated(created)
		self.setOpsiHostKey(opsiHostKey)
	
	def getLastSeen(self):
		return self.lastSeen
	
	def setLastSeen(self, lastSeen):
		self.lastSeen = forceOpsiTimestamp(lastSeen)
	
	def getCreated(self):
		return self.created
	
	def setCreated(self, created):
		if not created:
			self.created = time.strftime( "%Y%m%d%H%M%S", time.localtime() )
		self.created = forceOpsiTimestamp(created)
	
	def getOpsiHostKey(self):
		return self.opsiHostKey
	
	def setOpsiHostKey(self, opsiHostKey):
		if not opsiHostKey:
			self.opsiHostKey = u''
		else:
			self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiClient'
		return Host.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiClient.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.hardwareAddress, self.ipAddress)
	
Host.subClasses['OpsiClient'] = OpsiClient

class OpsiDepotserver(Host):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
		     description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress)
		self.setOpsiHostKey(opsiHostKey)
		self.setDepotLocalUrl(depotLocalUrl)
		self.setDepotRemoteUrl(depotRemoteUrl)
		self.setRepositoryLocalUrl(repositoryLocalUrl)
		self.setRepositoryRemoteUrl(repositoryRemoteUrl)
		self.setNetwork(network)
	
	def getOpsiHostKey(self):
		return self.opsiHostKey
	
	def setOpsiHostKey(self, opsiHostKey):
		if not opsiHostKey:
			self.opsiHostKey = u''
		else:
			self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
	
	def getDepotLocalUrl(self):
		return self.depotLocalUrl
	
	def setDepotLocalUrl(self, depotLocalUrl):
		if not depotLocalUrl:
			self.depotLocalUrl = u''
		else:
			self.depotLocalUrl = forceUrl(depotLocalUrl)
	
	def getDepotRemoteUrl(self):
		return self.depotRemoteUrl
	
	def setDepotRemoteUrl(self, depotRemoteUrl):
		if not depotRemoteUrl:
			self.depotRemoteUrl = u''
		else:
			self.depotRemoteUrl = forceUrl(depotRemoteUrl)
	
	def getRepositoryLocalUrl(self):
		return self.repositoryLocalUrl
	
	def setRepositoryLocalUrl(self, repositoryLocalUrl):
		if not repositoryLocalUrl:
			self.repositoryLocalUrl = u''
		else:
			self.repositoryLocalUrl = forceUrl(repositoryLocalUrl)
	
	def getRepositoryRemoteUrl(self):
		return self.repositoryRemoteUrl
	
	def setRepositoryRemoteUrl(self, repositoryRemoteUrl):
		if not repositoryRemoteUrl:
			self.repositoryRemoteUrl = u''
		else:
			self.repositoryRemoteUrl = forceUrl(repositoryRemoteUrl)
	
	def getNetwork(self):
		return self.network
	
	def setNetwork(self, network):
		if not network:
			self.network = u''
		else:
			self.network = forceNetworkAddress(network)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiDepotserver'
		return Host.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiDepotserver.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
	
Host.subClasses['OpsiDepotserver'] = OpsiDepotserver

class OpsiConfigserver(OpsiDepotserver):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
		     description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		OpsiDepotserver.__init__(self, id, opsiHostKey, depotLocalUrl, depotRemoteUrl, repositoryLocalUrl, repositoryRemoteUrl,
		     description, notes, hardwareAddress, ipAddress, network, maxBandwidth)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'OpsiConfigserver'
		return OpsiDepotserver.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return OpsiConfigserver.fromHash(json.loads(jsonString))
	
OpsiDepotserver.subClasses['OpsiConfigserver'] = OpsiConfigserver

class Config(Entity):
	subClasses = {}
	
	def __init__(self, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		self.setName(name)
		self.setDescription(description)
		self.setPossibleValues(possibleValues)
		self.setDefaultValues(defaultValues)
		self.setEditable(editable)
		self.setMultiValue(multiValue)
		
	def getName(self):
		return self.name
	
	def setName(self, name):
		self.name = forceUnicodeLower(name)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getPossibleValues(self):
		return self.possibleValues
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = forceList(possibleValues)
	
	def getDefaultValues(self):
		return self.defaultValues
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceList(defaultValues)
	
	def getEditable(self):
		return self.editable
	
	def setEditable(self, editable):
		self.editable = forceBool(editable)
	
	def getMultiValue(self):
		return self.multiValue
	
	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Config'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Config.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s name '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.name, self.description, self.possibleValues, self.defaultValues, self.multiValue)
	
Entity.subClasses['Config'] = Config

class UnicodeConfig(Config):
	subClasses = {}
	
	def __init__(self, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		Config.__init__(self, name, description, possibleValues, defaultValues, editable, multiValue)
		self.setPossibleValues(possibleValues)
		self.setDefaultValues(defaultValues)
		
		def setPossibleValues(self, possibleValues):
			self.possibleValues = forceUnicodeList(possibleValues)
			if self.possibleValues and self.defaultValues:
				for defaultValue in self.defaultValues:
					if not defaultValue in self.possibleValues:
						raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
							% (defaultValue, possibleValues))
			elif not self.possibleValues and self.defaultValues:
				self.possibleValues = self.defaultValues
		
		def setDefaultValues(self, defaultValues):
			self.defaultValues = forceUnicodeList(defaultValues)
			if self.possibleValues and self.defaultValues:
				for defaultValue in self.defaultValues:
					if not defaultValue in self.possibleValues:
						raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
							% (defaultValue, possibleValues))
			elif not self.possibleValues and self.defaultValues:
				self.possibleValues = self.defaultValues
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'UnicodeConfig'
		return Config.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return UnicodeConfig.fromHash(json.loads(jsonString))
	
Config.subClasses['UnicodeConfig'] = UnicodeConfig

class BoolConfig(Config):
	subClasses = {}
	
	def __init__(self, name, description='', defaultValues = [ True ]):
		Config.__init__(self, name, description, [ True, False ], forceBoolList(defaultValues), False, False)
		if (len(self.defaultValues) > 1):
			raise BackendBadValueError(u"Bool config cannot have multiple default values: %s" % self.defaultValues)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'BoolConfig'
		return Config.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return BoolConfig.fromHash(json.loads(jsonString))
	
Config.subClasses['BoolConfig'] = BoolConfig

class ConfigState(Relationship):
	subClasses = {}
	
	def __init__(self, name, objectId, values=[]):
		self.setName(name)
		self.setObjectId(objectId)
		self.setValues(values)
	
	def getObjectId(self):
		return self.objectId
	
	def setObjectId(self, objectId):
		self.objectId = forceObjectId(objectId)
	
	def getName(self):
		return self.name
	
	def setName(self, name):
		self.name = forceUnicodeLower(name)
	
	def getValues(self):
		return self.values
	
	def setValues(self, values):
		self.values = forceList(values)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ConfigState'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ConfigState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s objectId '%s', name '%s'>" \
			% (self.getType(), self.objectId, self.name)
	
Relationship.subClasses['ConfigState'] = ConfigState

class Product(Entity):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name="", licenseRequired=False,
		     setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		     priority=0, description="", advice="", productClassIds=[], windowsSoftwareIds=[]):
		self.setId(id)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setName(name)
		self.setLicenseRequired(licenseRequired)
		self.setSetupScript(setupScript)
		self.setUninstallScript(uninstallScript)
		self.setUpdateScript(updateScript)
		self.setAlwaysScript(alwaysScript)
		self.setOnceScript(onceScript)
		self.setPriority(priority)
		self.setDescription(description)
		self.setAdvice(advice)
		self.setProductClassIds(productClassIds)
		self.setWindowsSoftwareIds(windowsSoftwareIds)
	
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
	
	def getPriority(self):
		return self.priority
	
	def setPriority(self, priority):
		self.priority = forceInt(priority)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getAdvice(self):
		return self.advice
	
	def setAdvice(self, advice):
		self.advice = forceUnicode(advice)
	
	def getProductClassIds(self):
		return self.productClassIds
	
	def setProductClassIds(self, productClassIds):
		self.productClassIds = forceUnicodeList(productClassIds)
	
	def getWindowsSoftwareIds(self):
		return self.windowsSoftwareIds
	
	def setWindowsSoftwareIds(self, windowsSoftwareIds):
		self.windowsSoftwareIds = forceUnicodeList(windowsSoftwareIds)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Product'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Product.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', name '%s'>" \
			% (self.getType(), self.id, self.name)
	
Entity.subClasses['Product'] = Product

class LocalbootProduct(Product):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name="", licenseRequired=False,
		     setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		     priority=0, description="", advice="", productClassNames=[], windowsSoftwareIds=[]):
		Product.__init__(self, id, productVersion, packageVersion, name, licenseRequired,
		     setupScript, uninstallScript, updateScript, alwaysScript, onceScript,
		     priority, description, advice, productClassNames, windowsSoftwareIds)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'LocalbootProduct'
		return Product.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return LocalbootProduct.fromHash(json.loads(jsonString))
	
Product.subClasses['LocalbootProduct'] = LocalbootProduct

class NetbootProduct(Product):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name="", licenseRequired=False,
		     setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		     priority=0, description="", advice="", productClassNames=[], windowsSoftwareIds=[],
		     pxeConfigTemplate=''):
		Product.__init__(self, id, productVersion, packageVersion, name, licenseRequired,
		     setupScript, uninstallScript, updateScript, alwaysScript, onceScript,
		     priority, description, advice, productClassNames, windowsSoftwareIds)
		self.pxeConfigTemplate = forceFilename(pxeConfigTemplate)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'NetbootProduct'
		return Product.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return NetbootProduct.fromHash(json.loads(jsonString))
	
Product.subClasses['NetbootProduct'] = NetbootProduct

class ProductProperty(Entity):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setName(name)
		self.setDescription(description)
		self.setPossibleValues(possibleValues)
		self.setDefaultValues(defaultValues)
		self.setEditable(editable)
		self.setMultiValue(multiValue)
	
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
	
	def getName(self):
		return self.name
	
	def setName(self, name):
		self.name = forceUnicodeLower(name)
	
	def getDescription(self):
		return self.description
	
	def setDescription(self, description):
		self.description = forceUnicode(description)
	
	def getPossibleValues(self):
		return self.possibleValues
	
	def setPossibleValues(self, possibleValues):
		self.possibleValues = forceList(possibleValues)
	
	def getDefaultValues(self):
		return self.defaultValues
	
	def setDefaultValues(self, defaultValues):
		self.defaultValues = forceList(defaultValues)
	
	def getEditable(self):
		return self.editable
	
	def setEditable(self, editable):
		self.editable = forceBool(editable)
	
	def getMultiValue(self):
		return self.multiValue
	
	def setMultiValue(self, multiValue):
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductProperty'
		return Entity.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductProperty.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s name '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.name, self.description, self.possibleValues, self.defaultValues, self.multiValue)
	
Entity.subClasses['ProductProperty'] = ProductProperty

class UnicodeProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, name, description, possibleValues, defaultValues, editable, multiValue)
		self.setPossibleValues(possibleValues)
		self.setDefaultValues(defaultValues)
		
		def setPossibleValues(self, possibleValues):
			self.possibleValues = forceUnicodeList(possibleValues)
			if self.possibleValues and self.defaultValues:
				for defaultValue in self.defaultValues:
					if not defaultValue in self.possibleValues:
						raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
							% (defaultValue, possibleValues))
			elif not self.possibleValues and self.defaultValues:
				self.possibleValues = self.defaultValues
		
		def setDefaultValues(self, defaultValues):
			self.defaultValues = forceUnicodeList(defaultValues)
			if self.possibleValues and self.defaultValues:
				for defaultValue in self.defaultValues:
					if not defaultValue in self.possibleValues:
						raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
							% (defaultValue, possibleValues))
			elif not self.possibleValues and self.defaultValues:
				self.possibleValues = self.defaultValues
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'UnicodeProductProperty'
		return ProductProperty.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return UnicodeProductProperty.fromHash(json.loads(jsonString))
	
ProductProperty.subClasses['UnicodeProductProperty'] = UnicodeProductProperty

class BoolProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', defaultValues = [ True ]):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, name, description, [ True, False ], defaultValues, False, False)
		self.defaultValues = forceBoolList(defaultValues)
		if (len(self.defaultValues) > 1):
			raise BackendBadValueError(u"Bool product property cannot have multiple default values: %s" % self.defaultValues)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'BoolProductProperty'
		return ProductProperty.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return BoolProductProperty.fromHash(json.loads(jsonString))
	
ProductProperty.subClasses['BoolProductProperty'] = BoolProductProperty

class ProductOnDepot(Relationship):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, depotId, locked=False):
		self.setProductId(productId)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setDepotId(depotId)
		self.setLocked(locked)
	
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
		if not hash.has_key('type'): hash['type'] = 'ProductOnDepot'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductOnDepot.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', depotId '%s'>" \
			% (self.getType(), self.productId, self.depotId)
	
Relationship.subClasses['ProductOnDepot'] = ProductOnDepot


class ProductState(Relationship):
	subClasses = {}
	
	def __init__(self, productId, hostId, installationStatus='not_installed', actionRequest='none', actionProgress='', productVersion='', packageVersion='', lastStateChange=''):
		self.setProductId(productId)
		self.setHostId(hostId)
		self.setInstallationStatus(installationStatus)
		self.setActionRequest(actionRequest)
		self.setActionProgress(actionProgress)
		self.setProductVersion(productVersion)
		self.setPackageVersion(packageVersion)
		self.setLastStateChange(lastStateChange)
	
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getHostId(self):
		return self.hostId
	
	def setHostId(self, hostId):
		self.hostId = forceHostId(hostId)
	
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
	
	def getProductVersion(self):
		return self.productVersion
	
	def setProductVersion(self, productVersion):
		self.productVersion = forceProductVersion(productVersion)
	
	def getPackageVersion(self):
		return self.packageVersion
	
	def setPackageVersion(self, packageVersion):
		self.packageVersion = forcePackageVersion(packageVersion)
	
	def getLastStateChange(self):
		return self.lastStateChange
	
	def setLastStateChange(self, lastStateChange):
		if not lastStateChange:
			lastStateChange = time.strftime( "%Y%m%d%H%M%S", time.localtime() )
		self.lastStateChange = forceOpsiTimestamp(lastStateChange)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductState'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s hostId '%s', productId '%s'>" \
			% (self.getType(), self.hostId, self.productId)
	
Relationship.subClasses['ProductState'] = ProductState

class ProductPropertyState(Relationship):
	subClasses = {}
	
	def __init__(self, productId, name, hostId, values=[]):
		self.setProductId(productId)
		self.setName(name)
		self.setHostId(hostId)
		self.setValues(values)
	
	def getProductId(self):
		return self.productId
	
	def setProductId(self, productId):
		self.productId = forceProductId(productId)
	
	def getHostId(self):
		return self.hostId
	
	def setHostId(self, hostId):
		self.hostId = forceHostId(hostId)
	
	def getName(self):
		return self.name
	
	def setName(self, name):
		self.name = forceUnicodeLower(name)
	
	def getValues(self):
		return self.values
	
	def setValues(self, values):
		self.values = forceList(values)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'ProductPropertyState'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductPropertyState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', hostId '%s', name '%s'>" \
			% (self.getType(), self.productId, self.hostId, self.name)
	
Relationship.subClasses['ProductPropertyState'] = ProductPropertyState

class Group(Object):
	subClasses = {}
	
	def __init__(self, id, description='', notes='', parentGroupId=''):
		Object.__init__(self, id, description, notes)
		self.setId(id)
		self.setParentGroupId(parentGroupId)
	
	def getId(self):
		return self.id
	
	def setId(self, id):
		self.id = forceGroupId(id)
	
	def getParentGroupId(self):
		return self.parentGroupId
	
	def setParentGroupId(self, parentGroupId):
		if not parentGroupId:
			self.parentGroupId = u''
		else:
			self.parentGroupId = forceGroupId(parentGroupId)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'Group'
		return Object.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return Group.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', parentGroupId '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.parentGroupId)
	
Object.subClasses['Group'] = Group

class HostGroup(Group):
	subClasses = {}
	
	def __init__(self, id, description='', notes='', parentGroupId=''):
		Group.__init__(self, id, description, notes, parentGroupId)
	
	@staticmethod
	def fromHash(hash):
		if not hash.has_key('type'): hash['type'] = 'HostGroup'
		return Group.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return HostGroup.fromHash(json.loads(jsonString))
	
Group.subClasses['HostGroup'] = HostGroup

class ObjectToGroup(Relationship):
	subClasses = {}
	
	def __init__(self, groupId, objectId):
		self.setGroupId(groupId)
		self.setObjectId(objectId)
	
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
		if not hash.has_key('type'): hash['type'] = 'ObjectToGroup'
		return Relationship.fromHash(hash)
	
	@staticmethod
	def fromJson(jsonString):
		return ObjectToGroup.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s groupId '%s', objectId '%s'>" \
			% (self.getType(), self.groupId, self.objectId)
	
Relationship.subClasses['ObjectToGroup'] = ObjectToGroup











