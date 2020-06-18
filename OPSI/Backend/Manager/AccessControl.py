# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2019 uib GmbH <info@uib.de>

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
Backend access control.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import time
import functools
import inspect
import os
import re
import types
from typing import List
from functools import lru_cache
from hashlib import md5
try:
	# python3-pycryptodome installs into Cryptodome
	from Cryptodome.Hash import MD5
	from Cryptodome.Signature import pkcs1_15
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Hash import MD5
	from Crypto.Signature import pkcs1_15

from OPSI.Backend.Base import (
	ConfigDataBackend, ExtendedConfigDataBackend,
	getArgAndCallString)
from OPSI.Backend.Depotserver import DepotserverBackend
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.HostControlSafe import HostControlSafeBackend
from OPSI.Exceptions import (
	BackendAuthenticationError, BackendConfigurationError, BackendIOError,
	BackendMissingDataError, BackendPermissionDeniedError,
	BackendUnaccomplishableError)
from OPSI.Logger import Logger, LOG_INFO
from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Object import (
	mandatoryConstructorArgs,
	BaseObject, Object, OpsiClient, OpsiDepotserver)
from OPSI.Types import forceBool, forceList, forceUnicode, forceUnicodeList
from OPSI.Util import getPublicKey
from OPSI.Util.File.Opsi import BackendACLFile, OpsiConfFile

__all__ = ('BackendAccessControl', 'BackendAccessControlManager')

logger = Logger()

class UserStore:
	def __init__(self):
		self.username = None
		self.password = None
		self.userGroups = set()
		self.host = None
		self.authenticated = False
		self.isAdmin = False
		self.isReadOnly = False


class BackendAccessControl:

	def __init__(self, backend, **kwargs):

		self._backend = backend
		self._context = backend
		self._acl = None
		self._aclFile = None
		self._user_store = UserStore()
		self._auth_module = None

		pam_service = None
		kwargs = {k.lower(): v for k, v in kwargs.items()}
		for (option, value) in kwargs.items():
			if option == 'acl':
				self._acl = value
			elif option == 'aclfile':
				self._aclFile = value
			elif option == 'pamservice':
				logger.debug("Using PAM service %s", value)
				pam_service = value
			elif option in ('context', 'accesscontrolcontext'):
				self._context = value
			elif option in ('user_store', 'userstore'):
				self._user_store = value
			elif option in ('auth_module', 'authmodule'):
				self._auth_module = value

		if not self._backend:
			raise BackendAuthenticationError(u"No backend specified")
		if isinstance(self._backend, BackendAccessControl):
			raise BackendConfigurationError(u"Cannot use BackendAccessControl instance as backend")
		
		if not self._auth_module:
			try:
				ldap_conf = OpsiConfFile().get_ldap_auth_config()
				if ldap_conf:
					logger.debug("Using ldap auth with config: %s", ldap_conf)
					
					backendinfo = self._context.backend_info()
					modules = backendinfo['modules']
					helpermodules = backendinfo['realmodules']

					if not all(key in modules for key in ('expires', 'customer')):
						logger.info("Missing important information about modules. Probably no modules file installed.")
					elif not modules.get('customer'):
						logger.error("Disabling ldap authentication: no customer in modules file")
					elif not modules.get('valid'):
						logger.error("Disabling ldap authentication: modules file invalid")
					elif (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
						logger.error("Disabling ldap authentication: modules file expired")
					else:
						logger.info("Verifying modules file signature")
						publicKey = getPublicKey(data=base64.decodebytes(b"AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP"))
						data = ""
						mks = list(modules.keys())
						mks.sort()
						for module in mks:
							if module in ("valid", "signature"):
								continue
							if module in helpermodules:
								val = helpermodules[module]
								if int(val) > 0:
									modules[module] = True
							else:
								val = modules[module]
								if val is False:
									val = "no"
								if val is True:
									val = "yes"
							data += "%s = %s\r\n" % (module.lower().strip(), val)

						verified = False
						if modules["signature"].startswith("{"):
							s_bytes = int(modules['signature'].split("}", 1)[-1]).to_bytes(256, "big")
							try:
								pkcs1_15.new(publicKey).verify(MD5.new(data.encode()), s_bytes)
								verified = True
							except ValueError:
								# Invalid signature
								pass
						else:
							h_int = int.from_bytes(md5(data.encode()).digest(), "big")
							s_int = publicKey._encrypt(int(modules["signature"]))
							verified = h_int == s_int
						
						if not verified:
							logger.error("Disabling ldap authentication: modules file invalid")
						else:
							logger.debug("Modules file signature verified (customer: %s)", modules.get('customer'))

							if modules.get("directory-connector"):
								import OPSI.Backend.Manager.Authentication.LDAP
								self._auth_module = OPSI.Backend.Manager.Authentication.LDAP.LDAPAuthentication(**ldap_conf)
							else:
								logger.error("Disabling ldap authentication: directory-connector missing in modules file")
			
			except Exception as e:
				logger.debug(e)
			if not self._auth_module:
				if os.name == 'posix':
					import OPSI.Backend.Manager.Authentication.PAM
					self._auth_module = OPSI.Backend.Manager.Authentication.PAM.PAMAuthentication(pam_service)
				elif os.name == 'nt':
					import OPSI.Backend.Manager.Authentication.NT
					self._auth_module = OPSI.Backend.Manager.Authentication.NT.NTAuthentication()

		self._createInstanceMethods()
		if self._aclFile:
			self.__loadACLFile()
		
		if not self._acl:
			admin_groupname = OPSI_ADMIN_GROUP
			if self._auth_module:
				admin_groupname = self._auth_module.get_admin_groupname()
			self._acl = [[r'.*', [{'type': u'sys_group', 'ids': [admin_groupname], 'denyAttributes': [], 'allowAttributes': []}]]]

		# Pre-compiling regex patterns for speedup.
		for i, (pattern, acl) in enumerate(self._acl):
			self._acl[i] = (re.compile(pattern), acl)

		if kwargs.get('username') and kwargs.get('password'):
			self.authenticate(kwargs['username'], kwargs['password'], kwargs.get('forcegroups'))

	@property
	def user_store(self):
		if callable(self._user_store):
			return self._user_store()
		return self._user_store

	@user_store.setter
	def user_store(self, user_store):
		self._user_store = user_store
	
	def authenticate(self, username: str, password: str, forceGroups: List[str] = None):
		self.user_store.authenticated = False
		self.user_store.username = username
		self.user_store.password = password
		
		if not self.user_store.username:
			raise BackendAuthenticationError("No username specified")
		if not self.user_store.password:
			raise BackendAuthenticationError("No password specified")
		try:
			if re.search(r'^[^.]+\.[^.]+\.\S+$', self.user_store.username):
				# Username starts with something like hostname.domain.tld:
				# Assuming it is a host passing his FQDN as username
				logger.debug(u"Trying to authenticate by opsiHostKey...")
				self.user_store.username = self.user_store.username.lower()

				try:
					host = self._context.host_getObjects(id=self.user_store.username)
				except AttributeError as aerr:
					logger.debug(u"%s", aerr)
					raise BackendUnaccomplishableError(u"Passed backend has no method 'host_getObjects', cannot authenticate host '%s'" % self.user_store.username)

				try:
					self.user_store.host = host[0]
				except IndexError as ierr:
					logger.debug(u"%s", ierr)
					raise BackendMissingDataError(u"Host '%s' not found in backend %s" % (self.user_store.username, self._context))

				if not self.user_store.host.opsiHostKey:
					raise BackendMissingDataError(u"OpsiHostKey not found for host '%s'" % self.user_store.username)

				logger.confidential(u"Client %s, key sent %s, key stored %s", self.user_store.username, self.user_store.password, self.user_store.host.opsiHostKey)

				if self.user_store.password != self.user_store.host.opsiHostKey:
					raise BackendAuthenticationError(u"OpsiHostKey authentication failed for host '%s': wrong key" % self.user_store.host.id)

				logger.info(u"OpsiHostKey authentication successful for host %s", self.user_store.host.id)

				self.user_store.authenticated = True
				self.user_store.isAdmin = self._isOpsiDepotserver()
				self.user_store.isReadOnly = False
			else:
				# System user trying to log in with username and password
				logger.debug("Trying to authenticate by user authentication module %s", self._auth_module)
				
				if not self._auth_module:
					raise BackendAuthenticationError("Authentication module unavailable")
				
				try:
					self._auth_module.authenticate(self.user_store.username, self.user_store.password)
				except Exception as error:
					raise BackendAuthenticationError("Authentication failed for user '%s': %s" % (self.user_store.username, error))
				
				# Authentication did not throw exception => authentication successful
				self.user_store.authenticated = True
				if forceGroups:
					self.user_store.userGroups = forceUnicodeList(forceGroups)
					logger.info("Forced groups for user %s: %s", self.user_store.username, ', '.join(self.user_store.userGroups))
				else:
					self.user_store.userGroups = self._auth_module.get_groupnames(self.user_store.username)
				self.user_store.isAdmin = self._auth_module.user_is_admin(self.user_store.username)
				self.user_store.isReadOnly = self._auth_module.user_is_read_only(self.user_store.username, set(forceGroups) if forceGroups else None)

				logger.info(u"Authentication successful for user '%s', groups '%s'", self.user_store.username, ','.join(self.user_store.userGroups))
		
		except Exception as e:
			raise BackendAuthenticationError(forceUnicode(e))
		
		
	
	def accessControl_authenticated(self):
		return self.user_store.authenticated

	def accessControl_userIsAdmin(self):
		return self.user_store.isAdmin
	
	def accessControl_userIsReadOnlyUser(self):
		return self.user_store.isReadOnly

	def __loadACLFile(self):
		try:
			if not self._aclFile:
				raise BackendConfigurationError(u"No acl file defined")

			self._acl = _readACLFile(self._aclFile)
			logger.debug(u"Read acl from file %s: %s", self._aclFile, self._acl)
		except Exception as error:
			logger.logException(error)
			raise BackendConfigurationError(u"Failed to load acl file '%s': %s", self._aclFile, error)

	def _createInstanceMethods(self):
		protectedMethods = set()
		for Class in (ExtendedConfigDataBackend, ConfigDataBackend, DepotserverBackend, HostControlBackend, HostControlSafeBackend):
			methodnames = (name for name, _ in inspect.getmembers(Class, inspect.isfunction) if not name.startswith('_'))
			for methodName in methodnames:
				protectedMethods.add(methodName)

		for methodName, functionRef in inspect.getmembers(self._backend, inspect.ismethod):
			if methodName.startswith('_'):
				# Not a public method
				continue

			argString, callString = getArgAndCallString(functionRef)

			if methodName in protectedMethods:
				logger.debug2(u"Protecting %s method '%s'", Class.__name__, methodName)
				exec(u'def %s(self, %s): return self._executeMethodProtected("%s", %s)' % (methodName, argString, methodName, callString))
			else:
				logger.debug2(u"Not protecting %s method '%s'", Class.__name__, methodName)
				exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))

			setattr(self, methodName, types.MethodType(eval(methodName), self))
	
	def _isMemberOfGroup(self, ids):
		for groupId in forceUnicodeList(ids):
			if groupId in self.user_store.userGroups:
				return True
		return False

	def _isUser(self, ids):
		return forceBool(self.user_store.username in forceUnicodeList(ids))

	def _isOpsiDepotserver(self, ids=[]):
		if not self.user_store.host or not isinstance(self.user_store.host, OpsiDepotserver):
			return False
		if not ids:
			return True

		for hostId in forceUnicodeList(ids):
			if hostId == self.user_store.host.id:
				return True
		return False

	def _isOpsiClient(self, ids=[]):
		if not self.user_store.host or not isinstance(self.user_store.host, OpsiClient):
			return False

		if not ids:
			return True

		return forceBool(self.user_store.host.id in forceUnicodeList(ids))

	def _isSelf(self, **params):
		if not params:
			return False
		for (param, value) in params.items():
			if isinstance(value, types.ClassType) and issubclass(value, Object) and (value.id == self.user_store.username):
				return True
			if param in ('id', 'objectId', 'hostId', 'clientId', 'serverId', 'depotId') and (value == self.user_store.username):
				return True
		return False

	def _executeMethod(self, methodName, **kwargs):
		meth = getattr(self._backend, methodName)
		return meth(**kwargs)

	def _executeMethodProtected(self, methodName, **kwargs):
		granted = False
		newKwargs = {}
		acls = []
		logger.debug(u"Access control for method %s with params %s", methodName, kwargs)
		for regex, acl in self._acl:
			logger.debug2(u"Testing if ACL pattern %s matches method %s", regex.pattern, methodName)
			if not regex.search(methodName):
				logger.debug2(u"No match -> skipping.")
				continue

			logger.debug(u"Found matching acl for method %s: %s", acl, methodName)
			for entry in acl:
				aclType = entry.get('type')
				ids = entry.get('ids', [])
				newGranted = False
				if aclType == 'all':
					newGranted = True
				elif aclType == 'opsi_depotserver':
					newGranted = self._isOpsiDepotserver(ids)
				elif aclType == 'opsi_client':
					newGranted = self._isOpsiClient(ids)
				elif aclType == 'sys_group':
					newGranted = self._isMemberOfGroup(ids)
				elif aclType == 'sys_user':
					newGranted = self._isUser(ids)
				elif aclType == 'self':
					newGranted = 'partial_object'
				else:
					logger.error(u"Unhandled acl entry type: %s", aclType)
					continue

				if newGranted is False:
					continue

				if entry.get('denyAttributes') or entry.get('allowAttributes'):
					newGranted = 'partial_attributes'

				if newGranted:
					acls.append(entry)
					granted = newGranted

				if granted is True:
					break
			break

		logger.debug("Method %s using acls: %s", methodName, acls)
		if granted is True:
			logger.debug(u"Full access to method %s granted to user %s by acl %s", methodName, self.user_store.username, acls[0])
			newKwargs = kwargs
		elif granted is False:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s'" % (methodName, self.user_store.username))
		else:
			logger.debug(u"Partial access to method %s granted to user %s by acls %s", methodName, self.user_store.username, acls)
			try:
				newKwargs = self._filterParams(kwargs, acls)
				if not newKwargs:
					raise BackendPermissionDeniedError(u"No allowed param supplied")
			except Exception as error:
				logger.logException(error, LOG_INFO)
				raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s': %s" % (methodName, self.user_store.username, error))

		logger.debug2("newKwargs: %s", newKwargs)

		meth = getattr(self._backend, methodName)
		result = meth(**newKwargs)

		if granted is True:
			return result

		return self._filterResult(result, acls)

	def _filterParams(self, params, acls):
		logger.debug(u"Filtering params: %s", params)
		for (key, value) in tuple(params.items()):
			valueList = forceList(value)
			if not valueList:
				continue

			if issubclass(valueList[0].__class__, BaseObject) or isinstance(valueList[0], dict):
				valueList = self._filterObjects(valueList, acls, exceptionOnTruncate=False)
				if isinstance(value, list):
					params[key] = valueList
				else:
					if valueList:
						params[key] = valueList[0]
					else:
						del params[key]
		return params

	def _filterResult(self, result, acls):
		if result:
			resultList = forceList(result)
			if issubclass(resultList[0].__class__, BaseObject) or isinstance(resultList[0], dict):
				resultList = self._filterObjects(result, acls, exceptionOnTruncate=False, exceptionIfAllRemoved=False)
				if isinstance(result, list):
					return resultList
				else:
					if resultList:
						return resultList[0]
					else:
						return None
		return result

	def _filterObjects(self, objects, acls, exceptionOnTruncate=True, exceptionIfAllRemoved=True):
		logger.info(u"Filtering objects by acls")
		newObjects = []
		for obj in forceList(objects):
			isDict = isinstance(obj, dict)
			if isDict:
				objHash = obj
			else:
				objHash = obj.toHash()

			allowedAttributes = set()
			for acl in acls:
				if acl.get('type') == 'self':
					objectId = None
					for identifier in ('id', 'objectId', 'hostId', 'clientId', 'depotId', 'serverId'):
						try:
							objectId = objHash[identifier]
							break
						except KeyError:
							pass

					if not objectId or objectId != self.user_store.username:
						continue

				if acl.get('allowAttributes'):
					attributesToAdd = acl['allowAttributes']
				elif acl.get('denyAttributes'):
					attributesToAdd = (
						attribute for attribute in objHash
						if attribute not in acl['denyAttributes']
					)
				else:
					attributesToAdd = list(objHash.keys())

				for attribute in attributesToAdd:
					allowedAttributes.add(attribute)

			if not allowedAttributes:
				continue

			if not isDict:
				allowedAttributes.add('type')

				for attribute in mandatoryConstructorArgs(obj.__class__):
					allowedAttributes.add(attribute)

			keysToDelete = set()
			for key in objHash.keys():
				if key not in allowedAttributes:
					if exceptionOnTruncate:
						raise BackendPermissionDeniedError(u"Access to attribute '%s' denied" % key)
					keysToDelete.add(key)

			for key in keysToDelete:
				del objHash[key]

			if isDict:
				newObjects.append(objHash)
			else:
				newObjects.append(obj.__class__.fromHash(objHash))

		orilen = len(objects)
		newlen = len(newObjects)
		if newlen < orilen:
			logger.warning(u"%s objects removed by acl, %s objects left".format((orilen - newlen), newlen))
			if newlen == 0 and exceptionIfAllRemoved:
				raise BackendPermissionDeniedError(u"Access denied")

		return newObjects


@lru_cache(maxsize=None)
def _readACLFile(path):
	if not os.path.exists(path):
		raise BackendIOError(u"Acl file '%s' not found" % path)

	return BackendACLFile(path).parse()
