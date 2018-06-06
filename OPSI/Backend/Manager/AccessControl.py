# -*- coding: utf-8 -*-

# This file is part of python-opsi.
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
Backend access control.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import inspect
import os
import re
import types

from OPSI.Backend.Base import (
	ConfigDataBackend, ExtendedConfigDataBackend,
	getArgAndCallString)
from OPSI.Backend.Depotserver import DepotserverBackend
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.HostControlSafe import HostControlSafeBackend
from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Exceptions import (
	BackendAuthenticationError, BackendConfigurationError, BackendIOError,
	BackendMissingDataError, BackendPermissionDeniedError,
	BackendUnaccomplishableError)
from OPSI.Logger import Logger, LOG_INFO
from OPSI.Object import (
	mandatoryConstructorArgs,
	BaseObject, OpsiClient, OpsiDepotserver)
from OPSI.Types import forceBool, forceList, forceUnicode, forceUnicodeList
from OPSI.Util.File.Opsi import BackendACLFile, OpsiConfFile

if os.name == 'posix':
	import grp
	import PAM
	import pwd
elif os.name == 'nt':
	import win32net
	import win32security

__all__ = ('BackendAccessControl', )

logger = Logger()

try:
	from OPSI.System.Posix import Distribution
	DISTRIBUTOR = Distribution().distributor or 'unknown'
except ImportError:
	# Probably running on Windows.
	DISTRIBUTOR = 'unknown'


class BackendAccessControl(object):

	def __init__(self, backend, **kwargs):

		self._backend = backend
		self._context = backend
		self._username = None
		self._password = None
		self._acl = None
		self._aclFile = None
		self._pamService = 'common-auth'
		self._userGroups = set()
		self._forceGroups = None
		self._host = None
		self._authenticated = False

		if os.path.exists("/etc/pam.d/opsi-auth"):
			# Prefering our own - if present.
			self._pamService = 'opsi-auth'
		elif 'suse' in DISTRIBUTOR.lower():
			self._pamService = 'sshd'
		elif 'centos' in DISTRIBUTOR.lower() or 'redhat' in DISTRIBUTOR.lower():
			self._pamService = 'system-auth'

		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'username':
				self._username = value
			elif option == 'password':
				self._password = value
			elif option == 'acl':
				self._acl = value
			elif option == 'aclfile':
				self._aclFile = value
			elif option == 'pamservice':
				self._pamService = value
			elif option in ('context', 'accesscontrolcontext'):
				self._context = value
			elif option == 'forcegroups':
				if value is not None:
					self._forceGroups = forceUnicodeList(value)

		if not self._username:
			raise BackendAuthenticationError(u"No username specified")
		if not self._password:
			raise BackendAuthenticationError(u"No password specified")
		if not self._backend:
			raise BackendAuthenticationError(u"No backend specified")
		if isinstance(self._backend, BackendAccessControl):
			raise BackendConfigurationError(u"Cannot use BackendAccessControl instance as backend")

		try:
			if re.search('^[^\.]+\.[^\.]+\.\S+$', self._username):
				# Username starts with something like hostname.domain.tld:
				# Assuming it is a host passing his FQDN as username
				logger.debug(u"Trying to authenticate by opsiHostKey...")
				self._username = self._username.lower()

				try:
					host = self._context.host_getObjects(id=self._username)
				except AttributeError as aerr:
					logger.debug(u"{0!r}", aerr)
					raise BackendUnaccomplishableError(u"Passed backend has no method 'host_getObjects', cannot authenticate host '%s'" % self._username)

				try:
					self._host = host[0]
				except IndexError as ierr:
					logger.debug(u"{0!r}", ierr)
					raise BackendMissingDataError(u"Host '%s' not found in backend %s" % (self._username, self._context))

				if not self._host.opsiHostKey:
					raise BackendMissingDataError(u"OpsiHostKey not found for host '%s'" % self._username)

				logger.confidential(u"Client {0!r}, key sent {1!r}, key stored {2!r}", self._username, self._password, self._host.opsiHostKey)

				if self._password != self._host.opsiHostKey:
					raise BackendAuthenticationError(u"OpsiHostKey authentication failed for host '%s': wrong key" % self._host.id)

				logger.info(u"OpsiHostKey authentication successful for host {0!r}", self._host.id)
			else:
				# System user trying to log in with username and password
				logger.debug(u"Trying to authenticate by operating system...")
				self._authenticateUser()
				# Authentication did not throw exception => authentication successful
				logger.info(u"Operating system authentication successful for user '%s', groups '%s'" % (self._username, ','.join(self._userGroups)))
		except Exception as e:
			raise BackendAuthenticationError(forceUnicode(e))

		self._createInstanceMethods()
		if self._aclFile:
			self.__loadACLFile()
		self._authenticated = True

		if not self._acl:
			self._acl = [['.*', [{'type': u'sys_group', 'ids': [OPSI_ADMIN_GROUP], 'denyAttributes': [], 'allowAttributes': []}]]]

		# Pre-compiling regex patterns for speedup.
		for i, (pattern, acl) in enumerate(self._acl):
			self._acl[i] = (re.compile(pattern), acl)

	def accessControl_authenticated(self):
		return self._authenticated

	def accessControl_userIsAdmin(self):
		return self._isMemberOfGroup(OPSI_ADMIN_GROUP) or self._isOpsiDepotserver()

	def accessControl_userIsReadOnlyUser(self):
		readOnlyGroups = OpsiConfFile().getOpsiGroups('readonly')
		if readOnlyGroups:
			return self._isMemberOfGroup(readOnlyGroups)
		return False

	def __loadACLFile(self):
		try:
			if not self._aclFile:
				raise BackendConfigurationError(u"No acl file defined")
			if not os.path.exists(self._aclFile):
				raise BackendIOError(u"Acl file '%s' not found" % self._aclFile)
			self._acl = BackendACLFile(self._aclFile).parse()
			logger.debug(u"Read acl from file {0!r}: {1!r}", self._aclFile, self._acl)
		except Exception as error:
			logger.logException(error)
			raise BackendConfigurationError(u"Failed to load acl file '%s': %s" % (self._aclFile, error))

	def _createInstanceMethods(self):
		protectedMethods = set()
		for Class in (ExtendedConfigDataBackend, ConfigDataBackend, DepotserverBackend, HostControlBackend, HostControlSafeBackend):
			methodnames = (name for name, _ in inspect.getmembers(Class, inspect.ismethod) if not name.startswith('_'))
			for methodName in methodnames:
				protectedMethods.add(methodName)

		for methodName, functionRef in inspect.getmembers(self._backend, inspect.ismethod):
			if methodName.startswith('_'):
				# Not a public method
				continue

			argString, callString = getArgAndCallString(functionRef)

			if methodName in protectedMethods:
				logger.debug2(u"Protecting %s method '%s'" % (Class.__name__, methodName))
				exec(u'def %s(self, %s): return self._executeMethodProtected("%s", %s)' % (methodName, argString, methodName, callString))
			else:
				logger.debug2(u"Not protecting %s method '%s'" % (Class.__name__, methodName))
				exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))

			setattr(self, methodName, types.MethodType(eval(methodName), self))

	def _authenticateUser(self):
		'''
		Authenticate a user by the underlying operating system.

		:raises BackendAuthenticationError: If authentication fails.
		'''
		if os.name == 'posix':
			self._pamAuthenticateUser()
		elif os.name == 'nt':
			self._winAuthenticateUser()
		else:
			raise NotImplementedError("Sorry, operating system '%s' not supported yet!" % os.name)

	def _winAuthenticateUser(self):
		'''
		Authenticate a user by Windows-Login on current machine

		:raises BackendAuthenticationError: If authentication fails.
		'''
		logger.confidential(u"Trying to authenticate user '%s' with password '%s' by win32security" % (self._username, self._password))

		try:
			win32security.LogonUser(self._username, 'None', self._password, win32security.LOGON32_LOGON_NETWORK, win32security.LOGON32_PROVIDER_DEFAULT)
			if self._forceGroups is not None:
				self._userGroups = set(self._forceGroups)
				logger.info(u"Forced groups for user '%s': %s" % (self._username, self._userGroups))
			else:
				gresume = 0
				while True:
					(groups, total, gresume) = win32net.NetLocalGroupEnum(None, 0, gresume)
					for groupname in (u['name'] for u in groups):
						logger.debug2(u"Found group '%s'" % groupname)
						uresume = 0
						while True:
							(users, total, uresume) = win32net.NetLocalGroupGetMembers(None, groupname, 0, uresume)
							for sid in (u['sid'] for u in users):
								(username, domain, type) = win32security.LookupAccountSid(None, sid)
								if username.lower() == self._username.lower():
									self._userGroups.add(groupname)
									logger.debug(u"User {0!r} is member of group {1!r}", self._username, groupname)
							if uresume == 0:
								break
						if gresume == 0:
							break
		except Exception as e:
			raise BackendAuthenticationError(u"Win32security authentication failed for user '%s': %s" % (self._username, e))

	def _pamAuthenticateUser(self):
		'''
		Authenticate a user by PAM (Pluggable Authentication Modules).
		Important: the uid running this code needs access to /etc/shadow
		if os uses traditional unix authentication mechanisms.

		:raises BackendAuthenticationError: If authentication fails.
		'''
		logger.confidential(u"Trying to authenticate user {0!r} with password {1!r} by PAM", self._username, self._password)

		class AuthConv:
			''' Handle PAM conversation '''
			def __init__(self, user, password):
				self.user = user
				self.password = password

			def __call__(self, auth, query_list, userData=None):
				response = []
				for (query, qtype) in query_list:
					logger.debug(u"PAM conversation: query {0!r}, type {1!r}", query, qtype)
					if qtype == PAM.PAM_PROMPT_ECHO_ON:
						response.append((self.user, 0))
					elif qtype == PAM.PAM_PROMPT_ECHO_OFF:
						response.append((self.password, 0))
					elif qtype in (PAM.PAM_ERROR_MSG, PAM.PAM_TEXT_INFO):
						response.append(('', 0))
					else:
						return None

				return response

		logger.debug2(u"Attempting PAM authentication as user {0!r}...", self._username)
		try:
			# Create instance
			auth = PAM.pam()
			auth.start(self._pamService)
			# Authenticate
			auth.set_item(PAM.PAM_CONV, AuthConv(self._username, self._password))
			# Set the tty
			# Workaround for:
			#   If running as daemon without a tty the following error
			#   occurs with older versions of pam:
			#      pam_access: couldn't get the tty name
			try:
				auth.set_item(PAM.PAM_TTY, '/dev/null')
			except Exception:
				pass
			auth.authenticate()
			auth.acct_mgmt()
			logger.debug2("PAM authentication successful.")

			if self._forceGroups is not None:
				self._userGroups = set(self._forceGroups)
				logger.info(u"Forced groups for user '%s': %s" % (self._username, self._userGroups))
			else:
				logger.debug("Reading groups of user...")
				primaryGroup = forceUnicode(grp.getgrgid(pwd.getpwnam(self._username)[3])[0])
				logger.debug(u"Primary group of user {0!r} is {1!r}", self._username, primaryGroup)

				self._userGroups = set(forceUnicode(group[0]) for group in grp.getgrall() if self._username in group[3])
				self._userGroups.add(primaryGroup)
				logger.debug(u"User {0!r} is member of groups: {1}", self._username, self._userGroups)
		except Exception as e:
			raise BackendAuthenticationError(u"PAM authentication failed for user '%s': %s" % (self._username, e))

	def _isMemberOfGroup(self, ids):
		for groupId in forceUnicodeList(ids):
			if groupId in self._userGroups:
				return True
		return False

	def _isUser(self, ids):
		return forceBool(self._username in forceUnicodeList(ids))

	def _isOpsiDepotserver(self, ids=[]):
		if not self._host or not isinstance(self._host, OpsiDepotserver):
			return False
		if not ids:
			return True

		for hostId in forceUnicodeList(ids):
			if hostId == self._host.id:
				return True
		return False

	def _isOpsiClient(self, ids=[]):
		if not self._host or not isinstance(self._host, OpsiClient):
			return False

		if not ids:
			return True

		return forceBool(self._host.id in forceUnicodeList(ids))

	def _isSelf(self, **params):
		if not params:
			return False
		for (param, value) in params.items():
			if isinstance(value, types.ClassType) and issubclass(value, Object) and (value.id == self._username):
				return True
			if param in ('id', 'objectId', 'hostId', 'clientId', 'serverId', 'depotId') and (value == self._username):
				return True
		return False

	def _executeMethod(self, methodName, **kwargs):
		meth = getattr(self._backend, methodName)
		return meth(**kwargs)

	def _executeMethodProtected(self, methodName, **kwargs):
		granted = False
		newKwargs = {}
		acls = []
		logger.debug(u"Access control for method {0!r} with params {1!r}", methodName, kwargs)
		for regex, acl in self._acl:
			logger.debug2(u"Testing if ACL pattern {0!r} matches method {1!r}", regex.pattern, methodName)
			if not regex.search(methodName):
				logger.debug2(u"No match -> skipping.")
				continue

			logger.debug(u"Found matching acl for method {1!r}: {0}", acl, methodName)
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
					logger.error(u"Unhandled acl entry type: {0}", aclType)
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

		logger.debug("Method {0!r} using acls: {1}", methodName, acls)
		if granted is True:
			logger.debug(u"Full access to method {0!r} granted to user {1!r} by acl {2!r}", methodName, self._username, acls[0])
			newKwargs = kwargs
		elif granted is False:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s'" % (methodName, self._username))
		else:
			logger.debug(u"Partial access to method {0!r} granted to user {1!r} by acls {2!r}", methodName, self._username, acls)
			try:
				newKwargs = self._filterParams(kwargs, acls)
				if not newKwargs:
					raise BackendPermissionDeniedError(u"No allowed param supplied")
			except Exception as e:
				logger.logException(e, LOG_INFO)
				raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s': %s" % (methodName, self._username, e))

		logger.debug2("newKwargs: {0}", newKwargs)

		meth = getattr(self._backend, methodName)
		result = meth(**newKwargs)

		if granted is True:
			return result

		return self._filterResult(result, acls)

	def _filterParams(self, params, acls):
		logger.debug(u"Filtering params: {0}", params)
		for (key, value) in params.items():
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

					if not objectId or objectId != self._username:
						continue

				if acl.get('allowAttributes'):
					attributesToAdd = acl['allowAttributes']
				elif acl.get('denyAttributes'):
					attributesToAdd = (
						attribute for attribute in objHash
						if attribute not in acl['denyAttributes']
					)
				else:
					attributesToAdd = objHash.keys()

				for attribute in attributesToAdd:
					allowedAttributes.add(attribute)

			if not allowedAttributes:
				continue

			if not isDict:
				allowedAttributes.add('type')

				for attribute in mandatoryConstructorArgs(obj.__class__):
					allowedAttributes.add(attribute)

			for key in objHash.keys():
				if key not in allowedAttributes:
					if exceptionOnTruncate:
						raise BackendPermissionDeniedError(u"Access to attribute '%s' denied" % key)
					del objHash[key]

			if isDict:
				newObjects.append(objHash)
			else:
				newObjects.append(obj.__class__.fromHash(objHash))

		orilen = len(objects)
		newlen = len(newObjects)
		if newlen < orilen:
			logger.warning(u"{0} objects removed by acl, {1} objects left".format((orilen - newlen), newlen))
			if newlen == 0 and exceptionIfAllRemoved:
				raise BackendPermissionDeniedError(u"Access denied")

		return newObjects
