#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2014 uib GmbH <info@uib.de>

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
Typeforcing and Exceptions.

This module contains various methods to ensure force a special type
on an object.

It also is home to various exception classes.

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

__version__ = '4.0.6.1'

import datetime
import os
import re
import sys
import time
import types

from OPSI.Logger import Logger

encoding = sys.getfilesystemencoding()
logger = Logger()


def forceList(var):
	if type(var) not in (types.ListType, types.TupleType):
		return [var]
	return list(var)


def forceUnicode(var):
	if type(var) is types.UnicodeType:
		return var
	elif type(var) is types.StringType:
		return unicode(var, 'utf-8', 'replace')
	elif (os.name == 'nt') and type(var) is WindowsError:
		return u"[Error %s] %s" % (var.args[0], var.args[1].decode(encoding))

	if hasattr(var, '__unicode__'):
		try:
			return var.__unicode__()
		except:
			pass

	try:
		return unicode(var)
	except:
		pass

	if hasattr(var, '__repr__'):
		var = var.__repr__()
		if type(var) is types.UnicodeType:
			return var
		return unicode(var, 'utf-8', 'replace')

	return unicode(var)


def forceUnicodeLower(var):
	return forceUnicode(var).lower()


def forceUnicodeUpper(var):
	return forceUnicode(var).upper()


def forceUnicodeList(var):
	return [forceUnicode(element) for element in forceList(var)]


def forceDictList(var):
	return [forceDict(element) for element in forceList(var)]


def forceUnicodeLowerList(var):
	return [forceUnicodeLower(element) for element in forceList(var)]


def forceBool(var):
	if type(var) is types.BooleanType:
		return var

	if type(var) in (types.UnicodeType, types.StringType):
		if var.lower() in ('true', 'yes', 'on', '1'):
			return True
		elif var.lower() in ('false', 'no', 'off', '0'):
			return False

	return bool(var)


def forceBoolList(var):
	return [forceBool(element) for element in forceList(var)]


def forceInt(var):
	if type(var) is types.IntType:
		return var
	try:
		return int(var)
	except Exception as e:
		raise ValueError(u"Bad int value '%s': %s" % (var, e))


def forceIntList(var):
	return [forceInt(element) for element in forceList(var)]


def forceUnsignedInt(var):
	var = forceInt(var)
	if var < 0:
		var = -1 * var
	return var


def forceOct(var):
	if type(var) is types.IntType:
		return var

	try:
		tmp = forceUnicode(var)
		var = ''
		for i in xrange(len(tmp)):
			x = forceInt(tmp[i])
			if x > 7:
				raise Exception('"{0}" is too big')
			elif i == 0 and x != '0':
				var += '0'
			var += str(x)
		var = eval(var)
		return var
	except Exception as e:
		raise ValueError(u"Bad oct value '%s': %s" % (var, e))


def forceFloat(var):
	if type(var) is types.FloatType:
		return var
	try:
		return float(var)
	except Exception as e:
		raise ValueError(u"Bad float value '%s': %s" % (var, e))


def forceDict(var):
	if var is None:
		return {}
	elif type(var) is types.DictType:
		return var

	raise ValueError(u"Not a dict '%s'" % var)


def forceTime(var):
	if type(var) is time.struct_time:
		return var
	if type(var) in (types.IntType, types.FloatType):
		return time.localtime(var)
	raise ValueError(u"Not a time '%s'" % var)


_HARDWARE_ID_REGEX = re.compile('^[a-fA-F0-9]{4}$')
def forceHardwareVendorId(var):
	var = forceUnicodeUpper(var)
	if not re.search(_HARDWARE_ID_REGEX, var):
		raise ValueError(u"Bad hardware vendor id '%s'" % var)
	return var


def forceHardwareDeviceId(var):
	var = forceUnicodeUpper(var)
	if not re.search(_HARDWARE_ID_REGEX, var):
		raise ValueError(u"Bad hardware device id '%s'" % var)
	return var


_OPSI_TIMESTAMP_REGEX = re.compile('^(\d{4})-?(\d{2})-?(\d{2})\s?(\d{2}):?(\d{2}):?(\d{2})\.?\d*$')
_OPSI_DATE_REGEX = re.compile('^(\d{4})-?(\d{2})-?(\d{2})$')
def forceOpsiTimestamp(var):
	if not var:
		var = u'0000-00-00 00:00:00'
	if isinstance(var, datetime.datetime):
		var = str(var)
	var = forceUnicode(var)
	match = re.search(_OPSI_TIMESTAMP_REGEX, var)
	if not match:
		match = re.search(_OPSI_DATE_REGEX, var)
		if not match:
			raise ValueError(u"Bad opsi timestamp: '%s'" % var)
		return u'%s-%s-%s 00:00:00' % ( match.group(1), match.group(2), match.group(3) )
	return u'%s-%s-%s %s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )


_FQDN_REGEX = re.compile('^[a-z0-9][a-z0-9\-]{,63}\.((\w+\-+)|(\w+\.))*\w{1,63}\.\w{2,16}\.?$')
def forceFqdn(var):
	var = forceObjectId(var)
	if not _FQDN_REGEX.search(var):
		raise ValueError(u"Bad fqdn: '%s'" % var)
	if var.endswith('.'):
		var = var[:-1]
	return var
forceHostId = forceFqdn


def forceHostIdList(var):
	return [forceHostId(element) for element in forceList(var)]


_HARDWARE_ADDRESS_REGEX = re.compile('^([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})$')
def forceHardwareAddress(var):
	var = forceUnicodeLower(var)
	if not var:
		return var
	match = re.search(_HARDWARE_ADDRESS_REGEX, var)
	if not match:
		raise ValueError(u"Bad hardware address: %s" % var)
	return u'%s:%s:%s:%s:%s:%s' % ( match.group(1), match.group(2), match.group(3), match.group(4), match.group(5), match.group(6) )


_IP_ADDRESS_REGEX = re.compile('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
def forceIPAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(_IP_ADDRESS_REGEX, var):
		raise ValueError(u"Bad ip address: '%s'" % var)
	return var
forceIpAddress = forceIPAddress


def forceHostAddress(var):
	var = forceUnicodeLower(var)
	try:
		try:
			try:
				var = forceIpAddress(var)
			except Exception:
				var = forceFqdn(var)
		except Exception:
			var = forceHostname(var)
	except Exception:
		raise ValueError(u"Bad host address: '%s'" % var)
	return var


_NETMASK_REGEX = re.compile('^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')
def forceNetmask(var):
	var = forceUnicodeLower(var)
	if not re.search(_NETMASK_REGEX, var):
		raise ValueError(u"Bad netmask: '%s'" % var)
	return var


_NETWORK_ADDRESS_REGEX = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/([0-3]?[0-9]|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$')
def forceNetworkAddress(var):
	var = forceUnicodeLower(var)
	if not re.search(_NETWORK_ADDRESS_REGEX, var):
		raise ValueError(u"Bad network address: '%s'" % var)
	return var


_URL_REGEX = re.compile('^[a-z0-9]+://[/a-zA-Z0-9]')
def forceUrl(var):
	"""
	Forces ``var`` to be an valid URL.

	:returntype: unicode
	"""
	var = forceUnicode(var)
	if not _URL_REGEX.search(var):
		raise ValueError(u"Bad url: '{0}'".format(var))
	return var


_OPSI_HOST_KEY_REGEX = re.compile('^[0-9a-f]{32}$')
def forceOpsiHostKey(var):
	var = forceUnicodeLower(var)
	if not re.search(_OPSI_HOST_KEY_REGEX, var):
		raise ValueError(u"Bad opsi host key: '%s'" % var)
	return var


_PRODUCT_VERSION_REGEX = re.compile('^[a-z0-9\.]{1,32}$')
def forceProductVersion(var):
	var = forceUnicode(var)
	if not _PRODUCT_VERSION_REGEX.search(var):
		raise ValueError(u"Bad product version: '%s'" % var)
	return var


def forceProductVersionList(var):
	return [forceProductVersion(element) for element in forceList(var)]


_PACKAGE_VERSION_REGEX = re.compile('^[a-z0-9\.]{1,16}$')
def forcePackageVersion(var):
	var = forceUnicode(var)
	if not _PACKAGE_VERSION_REGEX.search(var):
		raise ValueError(u"Bad package version: '%s'" % var)
	return var


def forcePackageVersionList(var):
	return [forcePackageVersion(element) for element in forceList(var)]


_PRODUCT_ID_REGEX = re.compile('^[a-z0-9-_\.]{1,128}$')
def forceProductId(var):
	var = forceObjectId(var)
	if not _PRODUCT_ID_REGEX.search(var):
		raise ValueError(u"Bad product id: '%s'" % var)
	return var


def forceProductIdList(var):
	return [forceProductId(element) for element in forceList(var)]


_PACKAGE_CUSTOM_NAME_REGEX = re.compile('^[a-zA-Z0-9]+$')
def forcePackageCustomName(var):
	var = forceUnicodeLower(var)
	if not _PACKAGE_CUSTOM_NAME_REGEX.search(var):
		raise ValueError(u"Bad package custom name: '%s'" % var)
	return var


def forceProductType(var):
	v = forceUnicodeLower(var)
	if v in ('localboot', 'localbootproduct'):
		return u'LocalbootProduct'
	elif v in ('netboot', 'netbootproduct'):
		return u'NetbootProduct'
	else:
		raise ValueError(u"Unknown product type: '%s'" % var)


_PRODUCT_PROPERTY_ID_REGEX = re.compile('^\S+$')
def forceProductPropertyId(var):
	var = forceUnicodeLower(var)
	if not _PRODUCT_PROPERTY_ID_REGEX.search(var):
		raise ValueError(u"Bad product property id: '%s'" % var)
	return var


CONFIG_ID_REGEX = re.compile('^\S+$')
def forceConfigId(var):
	var = forceUnicodeLower(var)
	if not CONFIG_ID_REGEX.search(var):
		raise ValueError(u"Bad config id: '%s'" % var)
	return var


def forceProductPropertyType(var):
	v = forceUnicodeLower(var)
	if v in ('unicode', 'unicodeproductproperty'):
		return u'UnicodeProductProperty'
	elif v in ('bool', 'boolproductproperty'):
		return u'BoolProductProperty'
	else:
		raise ValueError(u"Unknown product property type: '%s'" % var)


def forceProductPriority(var):
	var = forceInt(var)
	if var < -100:
		var = -100
	elif var > 100:
		var = 100

	return var


def forceBootConfigurationPriority(var):
	var = forceInt(var)
	if var < 0:
		var =   0
	elif var > 100:
		var = 100

	return var


def forceFilename(var):
	return forceUnicode(var)


def forceProductTargetConfiguration(var):
	var = forceUnicodeLower(var)
	if var and var not in ('installed', 'always', 'forbidden', 'undefined'):
		raise ValueError(u"Bad product target configuration: '%s'" % var)
	return var


def forceInstallationStatus(var):
	var = forceUnicodeLower(var)
	if var and var not in ('installed', 'not_installed', 'unknown'):
		raise ValueError(u"Bad installation status: '%s'" % var)
	return var


def forceActionRequest(var):
	var = forceUnicodeLower(var)
	if var:
		if var == 'undefined':
			var = None
		elif var not in ('setup', 'uninstall', 'update', 'always', 'once', 'custom', 'none'):
			raise ValueError(u"Bad action request: '%s'" % var)

	return var


def forceActionRequestList(var):
	return [forceActionRequest(element) for element in forceList(var)]


def forceActionProgress(var):
	return forceUnicode(var)


def forceActionResult(var):
	var = forceUnicodeLower(var)
	if var and var not in ('failed', 'successful', 'none'):
		raise ValueError(u"Bad action result: '%s'" % var)
	return var


def forceRequirementType(var):
	var = forceUnicodeLower(var)
	if not var:
		return None
	elif var not in ('before', 'after'):
		raise ValueError(u"Bad requirement type: '%s'" % var)
	return var


def forceObjectClass(var, objectClass):
	import OPSI.Object
	from OPSI.Util import fromJson
	exception = None
	if type(var) in (types.UnicodeType, types.StringType) and var.lstrip() and var.lstrip().startswith('{'):
		try:
			var = fromJson(var)
		except Exception as e:
			exception = e
			logger.debug(u"Failed to get object from json '%s': %s" % (var, e))

	if type(var) is types.DictType:
		if 'type' not in var:
			raise ValueError(u"Key 'type' missing in hash '%s'" % var)

		try:
			c = eval('OPSI.Object.%s' % var['type'])
			if issubclass(c, objectClass):
				var = c.fromHash(var)
		except Exception as e:
			exception = e
			logger.debug(u"Failed to get object from dict '%s': %s" % (var, e))

	if not isinstance(var, objectClass):
		if exception:
			raise ValueError(u"Not a %s: '%s': %s" % (objectClass, var, exception))
		else:
			raise ValueError(u"Not a %s: '%s'" % (objectClass, var))

	return var


def forceObjectClassList(var, objectClass):
	return [forceObjectClass(element, objectClass) for element in forceList(var)]


_GROUP_ID_REGEX = re.compile('^[a-z0-9][a-z0-9-_. ]*$')
def forceGroupId(var):
	var = forceObjectId(var)
	if not _GROUP_ID_REGEX.search(var):
		raise ValueError(u"Bad group id: '%s'" % var)
	return var


def forceGroupType(var):
	lowercaseValue = forceUnicodeLower(var)

	if lowercaseValue == 'hostgroup':
		return u'HostGroup'
	elif lowercaseValue == 'productgroup':
		return u'ProductGroup'
	else:
		raise ValueError(u"Unknown group type: '%s'" % var)


def forceGroupTypeList(var):
	return [forceGroupType(element) for element in forceList(var)]


def forceGroupIdList(var):
	return [forceGroupId(element) for element in forceList(var)]


_OBJECT_ID_REGEX = re.compile('^[a-z0-9][a-z0-9-_. ]*$')
def forceObjectId(var):
	var = forceUnicodeLower(var).strip()
	if not _OBJECT_ID_REGEX.search(var):
		raise ValueError(u"Bad object id: '%s'" % var)
	return var


def forceObjectIdList(var):
	return [forceObjectId(element) for element in forceList(var)]


_EMAIL_REGEX = re.compile('^(([A-Za-z0-9]+_+)|([A-Za-z0-9]+\-+)|([A-Za-z0-9]+\.+)|([A-Za-z0-9]+\++))*[A-Za-z0-9]+@((\w+\-+)|(\w+\.))*\w*')
def forceEmailAddress(var):
	var = forceUnicodeLower(var)
	if not _EMAIL_REGEX.search(var):
		raise ValueError(u"Bad email address: '%s'" % var)
	return var


_DOMAIN_REGEX = re.compile('^((\w+\-+)|(\w+\.))*\w{1,63}\.\w{2,16}\.?$')
def forceDomain(var):
	var = forceUnicodeLower(var)
	if not _DOMAIN_REGEX.search(var):
		raise ValueError(u"Bad domain: '%s'" % var)
	return var


_HOSTNAME_REGEX = re.compile('^[a-z0-9][a-z0-9\-]*$')
def forceHostname(var):
	var = forceUnicodeLower(var)
	if not _HOSTNAME_REGEX.search(var):
		raise ValueError(u"Bad hostname: '%s'" % var)
	return var


_LICENSE_CONTRACT_ID_REGEX = re.compile('^[a-z0-9][a-z0-9-_\. :]*$')
def forceLicenseContractId(var):
	var = forceUnicodeLower(var)
	if not _LICENSE_CONTRACT_ID_REGEX.search(var):
		raise ValueError(u"Bad license contract id: '%s'" % var)
	return var


def forceLicenseContractIdList(var):
	return [forceLicenseContractId(element) for element in forceList(var)]


_SOFTWARE_LICENSE_ID_REGEX = re.compile('^[a-z0-9][a-z0-9-_\. :]*$')
def forceSoftwareLicenseId(var):
	var = forceUnicodeLower(var)
	if not _SOFTWARE_LICENSE_ID_REGEX.search(var):
		raise ValueError(u"Bad software license id: '%s'" % var)
	return var


def forceSoftwareLicenseIdList(var):
	return [forceSoftwareLicenseId(element) for element in forceList(var)]


_LICENSE_POOL_ID_REGEX = re.compile('^[a-z0-9][a-z0-9-_\. :]*$')
def forceLicensePoolId(var):
	var = forceUnicodeLower(var)
	if not _LICENSE_POOL_ID_REGEX.search(var):
		raise ValueError(u"Bad license pool id: '%s'" % var)
	return var


def forceLicensePoolIdList(var):
	return [forceLicensePoolId(element) for element in forceList(var)]


def forceAuditState(var):
	var = forceInt(var)
	if var not in (0, 1):
		raise ValueError(u"Bad audit state value: {0}".format(var))
	return var


_LANGUAGE_CODE_REGEX = re.compile('^([a-z]{2,3})[-_]?([a-z]{4})?[-_]?([a-z]{2})?$')
def forceLanguageCode(var):
	var = forceUnicodeLower(var)
	match = _LANGUAGE_CODE_REGEX.search(var)
	if not match:
		raise ValueError(u"Bad language code: '%s'" % var)
	var = match.group(1)
	if match.group(2):
		var += u'-' + match.group(2)[0].upper() + match.group(2)[1:]
	if match.group(3):
		var += u'-' + match.group(3).upper()
	return var


def forceLanguageCodeList(var):
	return [forceLanguageCode(element) for element in forceList(var)]


_ARCHITECTURE_REGX = re.compile('^(x86|x64)$')
def forceArchitecture(var):
	var = forceUnicodeLower(var)
	if not _ARCHITECTURE_REGEX.search(var):
		raise ValueError(u"Bad architecture: '%s'" % var)
	return var


def forceArchitectureList(var):
	return [forceArchitecture(element) for element in forceList(var)]


def forceUniqueList(_list):
	cleanedList = []
	for entry in _list:
		if entry not in cleanedList:
			cleanedList.append(entry)
	return cleanedList


def args(*vars, **typeVars):
	"""Function to populate an object with passed on keyword args.
	This is intended to be used as a decorator.
	Classes using this decorator must explicitly inherit from object or a subclass of object.

	.. code-block:: python

		@args()			#works
		class Foo(object):
			pass

		@args()			#works
		class Bar(Foo):
			pass

		@args()			#does not work
		class Foo():
			pass

		@args()			#does not work
		class Foo:
			pass
	"""
	vars = list(vars)
	def wrapper(cls):

		def new(typ, *args, **kwargs):
			if getattr(cls, "__base__", None) in (object, None):
				obj = object.__new__(typ) ### Suppress deprecation warning
			else:
				obj = cls.__base__.__new__(typ, *args, **kwargs)

			vars.extend(typeVars.keys())
			ka = kwargs.copy()

			for var in vars:
				varName = var.lstrip("_")
				if ka.has_key(varName):
					if typeVars.has_key(var):
						func = typeVars[var]
						ka[var] = func(ka[varName])
					else:
						ka[var] = ka[varName]
				else:
					ka[var] = None
			for key, value in ka.iteritems():
				if getattr(obj, key, None) is None:
					setattr(obj, key, value)
			return obj

		cls.__new__ = staticmethod(new)
		return cls
	return wrapper


# EXCEPTION CLASSES
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


class OpsiBackupFileError(OpsiError):
	ExceptionShortDescription = u"Opsi backup file error"


class OpsiBackupFileNotFound(OpsiBackupFileError):
	ExceptionShortDescription = u"Opsi backup file not found"


class OpsiBackupBackendNotFound(OpsiBackupFileError):
	ExceptionShortDescription = u"Opsi backend not found in backup"


class OpsiAuthenticationError(OpsiError):
	ExceptionShortDescription = u"Opsi authentication error"


class OpsiServiceVerificationError(OpsiError):
	ExceptionShortDescription = u"Opsi service verification error"


class OpsiBadRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi bad rpc error"


class OpsiRpcError(OpsiError):
	ExceptionShortDescription = u"Opsi rpc error"


class OpsiConnectionError(OpsiError):
	ExceptionShortDescription = u"Opsi connection error"


class OpsiTimeoutError(OpsiError):
	ExceptionShortDescription = u"Opsi timeout error"


class OpsiProductOrderingError(OpsiError):
	ExceptionShortDescription = u"A condition for ordering cannot be fulfilled"


class OpsiVersionError(OpsiError):
	ExceptionShortDescription = u"Opsi version error"


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


class BackendAuthenticationError(OpsiAuthenticationError):
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


class CanceledException(Exception):
	ExceptionShortDescription = u"CanceledException"
