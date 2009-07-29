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

opsiTimestampRegex = re.compile('^(\d{4})-?(\d{2})-?(\d{2})\s?(\d{2}):?(\d{2}):?(\d{2})$')
def forceOpsiTimestamp(var):
	if not var:
		var = u'0000-00-00 00:00:00'
	var = forceUnicode(var)
	match = re.search(opsiTimestampRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad opsi timestamp: %s" % var)
	return u'%s-%s-%s %s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )

hostIdRegex = re.compile('^[a-z0-9][a-z0-9\-]{,63}\.[a-z0-9][a-z0-9\-]*\.[a-z]{2,}$')
def forceHostId(var):
	var = forceObjectId(var)
	match = re.search(hostIdRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad host id: %s" % var)
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
	if not var:
		return var
	if not re.search(ipAddressRegex, var):
		raise BackendBadValueError(u"Bad ip address: %s" % var)
	return var

networkAddressRegex = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/([0-3][0-9]*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$')
def forceNetworkAddress(var):
	var = forceUnicodeLower(var)
	if not var:
		return var
	if not re.search(networkAddressRegex, var):
		raise BackendBadValueError(u"Bad network address: %s" % var)
	return var

urlRegex = re.compile('^[a-z0-9]+://[/a-z0-9]')
def forceUrl(var):
	var = forceUnicodeLower(var)
	if not var:
		return var
	if not re.search(urlRegex, var):
		raise BackendBadValueError(u"Bad url: %s" % var)
	return var

opsiHostKeyRegex = re.compile('^[0-9a-f]{32}$')
def forceOpsiHostKey(var):
	var = forceUnicodeLower(var)
	if not var:
		return var
	if not re.search(opsiHostKeyRegex, var):
		raise BackendBadValueError(u"Bad opsi host key: %s" % var)
	return var

productVersionRegex = re.compile('^[\w\.]+$')
def forceProductVersion(var):
	var = forceUnicode(var)
	match = re.search(productVersionRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: %s" % var)
	return var

packageVersionRegex = re.compile('^[\w\.]+$')
def forcePackageVersion(var):
	var = forceUnicode(var)
	match = re.search(packageVersionRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: %s" % var)
	return var
	
productIdRegex = re.compile('^[a-zA-Z0-9\_\.-]+$')
def forceProductId(var):
	var = forceObjectId(var)
	match = re.search(productIdRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad product id: %s" % var)
	return var

def forceFilename(var):
	return forceUnicode(var)

def forceInstallationStatus(var):
	var = forceUnicodeLower(var)
	if var and var not in ('installed', 'not_installed'):
		raise BackendBadValueError(u"Bad installation status: %s" % var)
	return var

def forceActionRequest(var):
	var = forceUnicodeLower(var)
	if var and var not in ('setup', 'uninstall', 'update', 'always', 'once', 'none'):
		raise BackendBadValueError(u"Bad action request: %s" % var)
	return var

def forceActionProgress(var):
	return forceUnicode(var)

def forceObjectClass(var, objectClass):
	if not isinstance(var, objectClass):
		raise BackendBadValueError(u"Not a %s: %s" % (objectClass, var))
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
		raise BackendBadValueError(u"Bad group id: %s" % var)
	return var

def forceObjectId(var):
	return forceUnicodeLower(var)

domainRegex = re.compile('^[a-z0-9][a-z0-9\-]*\.[a-z]{2,}$')
def forceDomain(var):
	var = forceUnicodeLower(var)
	match = re.search(domainRegex, var)
	if not match:
		raise BackendBadValueError(u"Bad domain: %s" % var)
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
	def _fromHash(hash, Class):
		kwargs = {}
		if hash.get('type') in Class.subClasses.keys():
			Class = Class.subClasses[hash['type']]
		
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		
		return Class(**kwargs)
	
	@staticmethod
	def fromHash(hash):
		return Entity._fromHash(hash, Entity)
	
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
	def _fromHash(hash, Class):
		kwargs = {}
		for varname in Class.__init__.func_code.co_varnames[1:]:
			if hash.has_key(varname):
				kwargs[varname] = hash[varname]
		return Class(**kwargs)
	
	@staticmethod
	def fromHash(hash):
		return Entity._fromHash(hash, Entity)
	
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
		self.id = forceObjectId(id)
		self.description = forceUnicode(description)
		self.notes = forceUnicode(notes)
	
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
		self.id = forceHostId(id)
		self.hardwareAddress = forceHardwareAddress(hardwareAddress)
		self.ipAddress = forceIPAddress(ipAddress)
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
	
	@staticmethod
	def fromHash(hash):
		return Host._fromHash(hash, Host)
	
	@staticmethod
	def fromJson(jsonString):
		return Host.fromHash(json.loads(jsonString))
Object.subClasses['Host'] = Host

class OpsiClient(Host):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', description='', notes='', hardwareAddress='', ipAddress='', created='', lastSeen=''):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress)
		self.lastSeen = forceOpsiTimestamp(lastSeen)
		self.created = created
		if not self.created:
			self.created = time.strftime( "%Y%m%d%H%M%S", time.localtime() )
		self.created = forceOpsiTimestamp(self.created)
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
	
	def __unicode__(self):
		return u"<%s id '%s', description '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.hardwareAddress, self.ipAddress)
Host.subClasses['OpsiClient'] = OpsiClient

class OpsiDepot(Host):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
		     description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		Host.__init__(self, id, description, notes, hardwareAddress, ipAddress)
		self.opsiHostKey = forceOpsiHostKey(opsiHostKey)
		self.depotLocalUrl = forceUrl(depotLocalUrl)
		self.depotRemoteUrl = forceUrl(depotRemoteUrl)
		self.repositoryLocalUrl = forceUrl(repositoryLocalUrl)
		self.repositoryRemoteUrl = forceUrl(repositoryRemoteUrl)
		self.network = forceNetworkAddress(network)
		
	def __unicode__(self):
		return u"<%s id '%s', description '%s', notes '%s', hardwareAddress '%s', ipAddress '%s'>" \
			% (self.getType(), self.id, self.description, self.notes, self.hardwareAddress, self.ipAddress)
Host.subClasses['OpsiDepot'] = OpsiDepot

class OpsiConfigserver(OpsiDepot):
	subClasses = {}
	
	def __init__(self, id, opsiHostKey='', depotLocalUrl='', depotRemoteUrl='', repositoryLocalUrl='', repositoryRemoteUrl='',
		     description='', notes='', hardwareAddress='', ipAddress='', network='0.0.0.0/0', maxBandwidth=0):
		OpsiDepot.__init__(self, id, opsiHostKey, depotLocalUrl, depotRemoteUrl, repositoryLocalUrl, repositoryRemoteUrl,
		     description, notes, hardwareAddress, ipAddress, network, maxBandwidth)
	
OpsiDepot.subClasses['OpsiConfigserver'] = OpsiConfigserver

class Config(Entity):
	subClasses = {}
	
	def __init__(self, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		self.name = forceUnicodeLower(name)
		self.description = forceUnicode(description)
		self.possibleValues = forceList(possibleValues)
		self.defaultValues = forceList(defaultValues)
		self.editable = forceBool(editable)
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
		
	@staticmethod
	def fromHash(hash):
		return Config._fromHash(hash, Config)
	
	@staticmethod
	def fromJson(jsonString):
		return Config.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s name '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.name, self.description, self.possibleValues, self.defaultValues, self.multiValue)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Entity.subClasses['Config'] = Config

class UnicodeConfig(Config):
	subClasses = {}
	
	def __init__(self, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		Config.__init__(self, name, description, possibleValues, defaultValues, editable, multiValue)
		self.possibleValues = forceUnicodeList(possibleValues)
		self.defaultValues = forceUnicodeList(defaultValues)
		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if not defaultValue in self.possibleValues:
					raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
						% (defaultValue, possibleValues))
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues
Config.subClasses['UnicodeConfig'] = UnicodeConfig

class BoolConfig(Config):
	subClasses = {}
	
	def __init__(self, name, description='', defaultValues = [ True ]):
		Config.__init__(self, name, description, [ True, False ], forceBoolList(defaultValues), False, False)
		if (len(self.defaultValues) > 1):
			raise BackendBadValueError(u"Bool config cannot have multiple default values: %s" % self.defaultValues)
		
Config.subClasses['BoolConfig'] = BoolConfig

class Product(Entity):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name="", licenseRequired=False,
		     setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		     priority=0, description="", advice="", productClassIds=[], windowsSoftwareIds=[]):
		self.id = forceProductId(id)
		self.productVersion = forceProductVersion(productVersion)
		self.packageVersion = forcePackageVersion(packageVersion)
		self.name = forceUnicode(name)
		self.licenseRequired = forceBool(licenseRequired)
		self.setupScript = forceFilename(setupScript)
		self.uninstallScript = forceFilename(uninstallScript)
		self.updateScript = forceFilename(updateScript)
		self.alwaysScript = forceFilename(alwaysScript)
		self.onceScript = forceFilename(onceScript)
		self.priority = forceInt(priority)
		self.description = forceUnicode(description)
		self.advice = forceUnicode(advice)
		self.productClassIds = forceUnicodeList(productClassIds)
		self.windowsSoftwareIds = forceUnicodeList(windowsSoftwareIds)
	
	@staticmethod
	def fromHash(hash):
		return Product._fromHash(hash, Product)
	
	@staticmethod
	def fromJson(jsonString):
		return Product.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s id '%s', name '%s'>" \
			% (self.getType(), self.id, self.name)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Entity.subClasses['Product'] = Product

class LocalbootProduct(Product):
	subClasses = {}
	
	def __init__(self, id, productVersion, packageVersion, name="", licenseRequired=False,
		     setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		     priority=0, description="", advice="", productClassNames=[], windowsSoftwareIds=[]):
		Product.__init__(self, id, productVersion, packageVersion, name, licenseRequired,
		     setupScript, uninstallScript, updateScript, alwaysScript, onceScript,
		     priority, description, advice, productClassNames, windowsSoftwareIds)
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
Product.subClasses['NetbootProduct'] = NetbootProduct

class ProductProperty(Entity):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=False, multiValue=False):
		self.productId = forceProductId(productId)
		self.productVersion = forceProductVersion(productVersion)
		self.packageVersion = forcePackageVersion(packageVersion)
		self.name = forceUnicodeLower(name)
		self.description = forceUnicode(description)
		self.possibleValues = forceList(possibleValues)
		self.defaultValues = forceList(defaultValues)
		self.editable = forceBool(editable)
		self.multiValue = forceBool(multiValue)
		if (len(self.defaultValues) > 1):
			self.multiValue = True
	
	@staticmethod
	def fromHash(hash):
		return ProductProperty._fromHash(hash, ProductProperty)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductProperty.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s name '%s', description '%s', possibleValues %s, defaultValues %s, multiValue: %s>" \
			% (self.getType(), self.name, self.description, self.possibleValues, self.defaultValues, self.multiValue)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Entity.subClasses['ProductProperty'] = ProductProperty

class UnicodeProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', possibleValues=[], defaultValues=[], editable=True, multiValue=False):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, name, description, possibleValues, defaultValues, editable, multiValue)
		self.possibleValues = forceUnicodeList(possibleValues)
		self.defaultValues = forceUnicodeList(defaultValues)
		if self.possibleValues and self.defaultValues:
			for defaultValue in self.defaultValues:
				if not defaultValue in self.possibleValues:
					raise BackendBadValueError(u"Default value '%s' not in possible values: %s" \
						% (defaultValue, possibleValues))
		elif not self.possibleValues and self.defaultValues:
			self.possibleValues = self.defaultValues
ProductProperty.subClasses['UnicodeProductProperty'] = UnicodeProductProperty

class BoolProductProperty(ProductProperty):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, name, description='', defaultValues = [ True ]):
		ProductProperty.__init__(self, productId, productVersion, packageVersion, name, description, [ True, False ], defaultValues, False, False)
		self.defaultValues = forceBoolList(defaultValues)
		if (len(self.defaultValues) > 1):
			raise BackendBadValueError(u"Bool product property cannot have multiple default values: %s" % self.defaultValues)
ProductProperty.subClasses['BoolProductProperty'] = BoolProductProperty

class ProductOnDepot(Relationship):
	subClasses = {}
	
	def __init__(self, productId, productVersion, packageVersion, depotId, locked=False):
		self.productId = forceProductId(productId)
		self.productVersion = forceProductVersion(productVersion)
		self.packageVersion = forcePackageVersion(packageVersion)
		self.depotId = forceHostId(depotId)
		self.locked = forceBool(locked)
	
	@staticmethod
	def fromHash(hash):
		return ProductOnDepot._fromHash(hash, ProductOnDepot)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductOnDepot.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', depotId '%s'>" \
			% (self.getType(), self.productId, self.depotId)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Relationship.subClasses['ProductOnDepot'] = ProductOnDepot


class ProductState(Relationship):
	subClasses = {}
	
	def __init__(self, productId, hostId, installationStatus='not_installed', actionRequest='none', actionProgress='', productVersion='', packageVersion='', lastStateChange=''):
		self.productId = forceProductId(productId)
		self.hostId = forceHostId(hostId)
		self.installationStatus = forceInstallationStatus(installationStatus)
		self.actionRequest = forceActionRequest(actionRequest)
		self.actionProgress = forceActionProgress(actionProgress)
		self.productVersion = forceProductVersion(productVersion)
		self.packageVersion = forcePackageVersion(packageVersion)
		self.lastStateChange = lastStateChange
		if not self.lastStateChange:
			self.lastStateChange = time.strftime( "%Y%m%d%H%M%S", time.localtime() )
		self.lastStateChange = forceOpsiTimestamp(self.lastStateChange)
	
	@staticmethod
	def fromHash(hash):
		return ProductState._fromHash(hash, ProductState)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s hostId '%s', productId '%s'>" \
			% (self.getType(), self.hostId, self.productId)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Relationship.subClasses['ProductState'] = ProductState

class ProductPropertyState(Relationship):
	subClasses = {}
	
	def __init__(self, productId, name, hostId, values=[]):
		self.productId = forceProductId(productId)
		self.name = forceUnicodeLower(name)
		self.hostId = forceHostId(hostId)
		self.values = forceList(values)
	
	@staticmethod
	def fromHash(hash):
		return ProductPropertyState._fromHash(hash, ProductPropertyState)
	
	@staticmethod
	def fromJson(jsonString):
		return ProductPropertyState.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s productId '%s', hostId '%s', name '%s'>" \
			% (self.getType(), self.productId, self.hostId, self.name)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Relationship.subClasses['ProductPropertyState'] = ProductPropertyState

class Group(Object):
	subClasses = {}
	
	def __init__(self, id, description='', notes='', parentGroupId=''):
		Object.__init__(self, id, description, notes)
		self.id = forceGroupId(id)
		if not parentGroupId:
			self.parentGroupId = ''
		else:
			self.parentGroupId = forceGroupId(parentGroupId)
	
	@staticmethod
	def fromHash(hash):
		return Group._fromHash(hash, Group)
	
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
Group.subClasses['HostGroup'] = HostGroup

class ObjectToGroup(Relationship):
	subClasses = {}
	
	def __init__(self, groupId, objectId):
		self.groupId = forceGroupId(groupId)
		self.objectId = forceObjectId(objectId)
	
	@staticmethod
	def fromHash(hash):
		return ObjectToGroup._fromHash(hash, ObjectToGroup)
	
	@staticmethod
	def fromJson(jsonString):
		return ObjectToGroup.fromHash(json.loads(jsonString))
	
	def __unicode__(self):
		return u"<%s groupId '%s', objectId '%s'>" \
			% (self.getType(), self.groupId, self.objectId)
		
	def __repr__(self):
		return unicode(self).encode("utf-8")
	
	__str__ = __repr__
Relationship.subClasses['ObjectToGroup'] = ObjectToGroup











