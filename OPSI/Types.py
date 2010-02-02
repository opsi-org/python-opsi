#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - Types   =
   = = = = = = = = = = = = = = = = = =
   
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

__version__ = '0.1'

# Imports
import re

# OPSI imports
from OPSI.Logger import *

# Get logger instance
logger = Logger()

def forceList(var):
	if not type(var) is list:
		var = [ var ]
	return var

def forceDict(var):
	if var is None:
		var = {}
	if not type(var) is dict:
		raise ValueError(u"Bad dict value '%s'" % var)
	return var

def forceUnicode(var):
	if type(var) is unicode:
		return var
	if type(var) is str:
		return unicode(var, 'utf-8', 'replace')
	return unicode(var)
	

def forceUnicodeLower(var):
	return forceUnicode(var).lower()

def forceUnicodeList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceUnicode(var[i])
	return var

def forceDictList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceDict(var[i])
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
		raise ValueError(u"Bad int value '%s': %s" % (var, e))

def forceIntList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceInt(var[i])
	return var

def forceUnsignedInt(var):
	var = forceInt(var)
	if (var < 0):
		var = var*(-1)
	return var

def forceOct(var):
	if type(var) is int:
		return var
	try:
		tmp = forceUnicode(var)
		var = ''
		for i in range(len(tmp)):
			x = forceInt(tmp[i])
			if (x > 7):
				raise Exception('too big')
			if (i == 0) and (x != '0'):
				var += '0'
			var += str(x)
		var = eval(var)
		return var
	except Exception, e:
		raise ValueError(u"Bad oct value '%s': %s" % (var, e))

def forceFloat(var):
	if type(var) is float:
		return var
	try:
		return float(var)
	except Exception, e:
		raise ValueError(u"Bad float value '%s': %s" % (var, e))

def forceDict(var):
	if type(var) is dict:
		return var
	raise ValueError(u"Not a dict '%s'" % var)

opsiTimestampRegex = re.compile('^(\d{4})-?(\d{2})-?(\d{2})\s?(\d{2}):?(\d{2}):?(\d{2})$')
opsiDateRegex = re.compile('^(\d{4})-?(\d{2})-?(\d{2})$')
def forceOpsiTimestamp(var):
	if not var:
		var = u'0000-00-00 00:00:00'
	var = forceUnicode(var)
	match = re.search(opsiTimestampRegex, var)
	if not match:
		match = re.search(opsiDateRegex, var)
		if not match:
			raise ValueError(u"Bad opsi timestamp: '%s'" % var)
		return u'%s-%s-%s 00:00:00' % ( match.group(1), match.group(2), match.group(3) )
	return u'%s-%s-%s %s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )

hostIdRegex = re.compile('^[a-z0-9][a-z0-9\-]{,63}\.[a-z0-9][a-z0-9\-]*\.[a-z]{2,}$')
def forceHostId(var):
	var = forceObjectId(var)
	match = re.search(hostIdRegex, var)
	if not match:
		raise ValueError(u"Bad host id: '%s'" % var)
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
		raise ValueError(u"Bad hardware address: %s" % var)
	return u'%s:%s:%s:%s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )

ipAddressRegex = re.compile('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
def forceIPAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(ipAddressRegex, var):
		raise ValueError(u"Bad ip address: '%s'" % var)
	return var

networkAddressRegex = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/([0-3][0-9]*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$')
def forceNetworkAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(networkAddressRegex, var):
		raise ValueError(u"Bad network address: '%s'" % var)
	return var

urlRegex = re.compile('^[a-z0-9]+://[/a-z0-9]')
def forceUrl(var):
	var = forceUnicodeLower(var)
	if not re.search(urlRegex, var):
		raise ValueError(u"Bad url: '%s'" % var)
	return var

opsiHostKeyRegex = re.compile('^[0-9a-f]{32}$')
def forceOpsiHostKey(var):
	var = forceUnicodeLower(var)
	if not re.search(opsiHostKeyRegex, var):
		raise ValueError(u"Bad opsi host key: '%s'" % var)
	return var

productVersionRegex = re.compile('^[\w\.]+$')
def forceProductVersion(var):
	var = forceUnicode(var)
	match = re.search(productVersionRegex, var)
	if not match:
		raise ValueError(u"Bad product version: '%s'" % var)
	return var

def forceProductVersionList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceProductVersion(var[i])
	return var

packageVersionRegex = re.compile('^[\w\.]+$')
def forcePackageVersion(var):
	var = forceUnicode(var)
	match = re.search(packageVersionRegex, var)
	if not match:
		raise ValueError(u"Bad package version: '%s'" % var)
	return var

def forcePackageVersionList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forcePackageVersion(var[i])
	return var

productIdRegex = re.compile('^[a-zA-Z0-9\_\.-]+$')
def forceProductId(var):
	var = forceObjectId(var)
	match = re.search(productIdRegex, var)
	if not match:
		raise ValueError(u"Bad product id: '%s'" % var)
	return var

def forceProductIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceProductId(var[i])
	return var

def forceProductType(var):
	v = forceUnicodeLower(var)
	if v in ('localboot', 'localbootproduct'):
		var = u'LocalbootProduct'
	elif v in ('netboot', 'netbootproduct'):
		var = u'NetbootProduct'
	else:
		raise ValueError(u"Unknown product type: '%s'" % var)
	return var

productPropertyIdRegex = re.compile('^\S+$')
def forceProductPropertyId(var):
	var = forceUnicodeLower(var)
	match = re.search(productPropertyIdRegex, var)
	if not match:
		raise ValueError(u"Bad product property id: '%s'" % var)
	return var

configIdRegex = re.compile('^\S+$')
def forceConfigId(var):
	var = forceUnicodeLower(var)
	match = re.search(configIdRegex, var)
	if not match:
		raise ValueError(u"Bad config id: '%s'" % var)
	return var

def forceProductPropertyType(var):
	v = forceUnicodeLower(var)
	if v in ('unicode', 'unicodeproductproperty'):
		var = u'UnicodeProductProperty'
	elif v in ('bool', 'boolproductproperty'):
		var = u'BoolProductProperty'
	else:
		raise ValueError(u"Unknown product property type: '%s'" % var)
	return var

def forceProductPriority(var):
	var = forceInt(var)
	if (var < -100): var = -100
	if (var >  100): var =  100
	return var

def forceFilename(var):
	return forceUnicode(var)

def forceInstallationStatus(var):
	var = forceUnicodeLower(var)
	if var:
		if (var == 'undefined'):
			var = None
		elif var not in ('installed', 'not_installed', 'failed'):
			raise ValueError(u"Bad installation status: '%s'" % var)
	return var

def forceActionRequest(var):
	var = forceUnicodeLower(var)
	if var:
		if (var == 'undefined'):
			var = None
		elif var not in ('setup', 'uninstall', 'update', 'always', 'once', 'custom', 'none'):
			raise ValueError(u"Bad action request: '%s'" % var)
	return var

def forceActionRequestList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceActionRequest(var[i])
	return var
	
def forceActionProgress(var):
	return forceUnicode(var)

def forceRequirementType(var):
	var = forceUnicodeLower(var)
	if not var:
		return None
	if not var in ('before', 'after'):
		raise ValueError(u"Bad requirement type: '%s'" % var)
	return var
	
def forceObjectClass(var, objectClass):
	import OPSI.Object
	if type(var) in (unicode, str):
		try:
			var = OPSI.Object.fromJson(var)
		except Exception, e:
			logger.debug(u"Failed to get object from json '%s': %s" % (var, e))
	if type(var) is dict and var.has_key('type'):
		try:
			c = eval('OPSI.Object.%s' % var['type'])
			if issubclass(c, objectClass):
				var = c.fromHash(var)
		except Exception, e:
			logger.debug(u"Failed to get object from dict '%s': %s" % (var, e))
		
	if not isinstance(var, objectClass):
		raise ValueError(u"Not a %s: '%s'" % (objectClass, var))
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
		raise ValueError(u"Bad group id: '%s'" % var)
	return var

def forceGroupIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceGroupId(var[i])
	return var

objectIdRegex = re.compile('^[a-z0-9][a-z0-9-_. ]*$')
def forceObjectId(var):
	var = forceUnicodeLower(var)
	match = re.search(objectIdRegex, var)
	if not match:
		raise ValueError(u"Bad object id: '%s'" % var)
	return var

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
		raise ValueError(u"Bad domain: '%s'" % var)
	return var

hostnameRegex = re.compile('^[a-z0-9][a-z0-9\-]*$')
def forceHostname(var):
	var = forceUnicodeLower(var)
	match = re.search(hostnameRegex, var)
	if not match:
		raise ValueError(u"Bad hostname: '%s'" % var)
	return var

licenseContractIdRegex = re.compile('^[a-z0-9][a-z0-9-_. :]*$')
def forceLicenseContractId(var):
	var = forceUnicodeLower(var)
	match = re.search(licenseContractIdRegex, var)
	if not match:
		raise ValueError(u"Bad license contract id: '%s'" % var)
	return var

def forceLicenseContractIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceLicenseContractId(var[i])
	return var

softwareLicenseIdRegex = re.compile('^[a-z0-9][a-z0-9-_. :]*$')
def forceSoftwareLicenseId(var):
	var = forceUnicodeLower(var)
	match = re.search(softwareLicenseIdRegex, var)
	if not match:
		raise ValueError(u"Bad software license id: '%s'" % var)
	return var

def forceSoftwareLicenseIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceSoftwareLicenseId(var[i])
	return var

licensePoolIdRegex = re.compile('^[a-z0-9][a-z0-9-_. :]*$')
def forceLicensePoolId(var):
	var = forceUnicodeLower(var)
	match = re.search(licensePoolIdRegex, var)
	if not match:
		raise ValueError(u"Bad license pool id: '%s'" % var)
	return var

def forceLicensePoolIdList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceLicensePoolId(var[i])
	return var

def forceAuditState(var):
	var = forceInt(var)
	if var not in (0, 1):
		raise ValueError(u"Bad audit state value '%s': %s" % (var, e))
	return var

languageCodeRegex = re.compile('^([a-z]{2})[-_]?([a-z]{2})?$')
def forceLanguageCode(var):
	var = forceUnicodeLower(var)
	match = languageCodeRegex.search(var)
	if not match:
		raise ValueError(u"Bad language code: '%s'" % var)
	var = match.group(1)
	if match.group(2):
		var += u'_' + match.group(2).upper()
	return var

def forceLanguageCodeList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceLanguageCode(var[i])
	return var

architectureRegex = re.compile('^(x86|x64)$')
def forceArchitecture(var):
	var = forceUnicodeLower(var)
	if not architectureRegex.search(var):
		raise ValueError(u"Bad architecture: '%s'" % var)
	return var

def forceArchitectureList(var):
	var = forceList(var)
	for i in range(len(var)):
		var[i] = forceArchitecture(var[i])
	return var


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                      EXCEPTION CLASSES                                             =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class OpsiError(Exception):
	""" Base class for OPSI Backend exceptions. """
	
	ExceptionShortDescription = "Opsi error"
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

class BackendConfigurationError(OpsiError):
	""" Exception raised if a configuration error occurs in the backend. """
	ExceptionShortDescription = u"Backend configuration error"

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

class RepositoryError(OpsiError):
	ExceptionShortDescription = u"Repository error"

class OpsiAuthenticationError(OpsiError):
	ExceptionShortDescription = u"Opsi authentication error"

class OpsiBadRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi bad rpc error"

class OpsiRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi rpc error"































