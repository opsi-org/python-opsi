#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - BackendManager  =
   = = = = = = = = = = = = = = = = = = = = = =
   
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

import os, sys, new, inspect, re, types, socket, copy

if (os.name == 'posix'):
	import PAM, pwd, grp
elif (os.name == 'nt'):
	import win32security, win32net

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from Backend import *
from OPSI.Util import objectToBeautifiedText
from OPSI.Util.File.Opsi import BackendACLFile, BackendDispatchConfigFile

# Get logger instance
logger = Logger()

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                  CLASS BACKENDMANAGER                                              =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class BackendManager(ExtendedBackend):
	def __init__(self, **kwargs):
		self._backend = None
		self._backendAccessControl = None
		self._backendConfigDir = None
		self._options = {}
		
		username = None
		password = None
		dispatch = False
		extend = False
		extensionConfigDir = None
		accessControl = False
		depotBackend = False
		
		loadBackend = None
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('username'):
				username = value
			elif option in ('password'):
				password = value
			elif option in ('backend'):
				if type(value) in (str, unicode):
					loadBackend = value
				else:
					self._backend = value
			elif (option == 'backendconfigdir'):
				self._backendConfigDir = value
			elif option in ('dispatchconfig', 'dispatchconfigfile') and value:
				dispatch = True
			elif option in ('depotbackend'):
				depotBackend = forceBool(value)
			elif option in ('extensionconfigdir') and value:
				extensionConfigDir = value
				extend = True
			elif option in ('extend'):
				extend = forceBool(value)
			elif option in ('acl', 'aclfile') and value:
				accessControl = True
		
		if loadBackend:
			self._backend = self.__loadBackend(loadBackend)
		
		if not dispatch and not self._backend:
			raise BackendConfigurationError(u"Neither backend nor dispatch config given")
		if dispatch:
			self._backend = BackendDispatcher(**kwargs)
		if extend or depotBackend:
			# DepotserverBackend/BackendExtender need ExtendedConfigDataBackend backend
			self._backend = ExtendedConfigDataBackend(self._backend)
		if depotBackend:
			self._backend = DepotserverBackend(self._backend)
		if accessControl:
			self._backend = BackendAccessControl(backend = self._backend, **kwargs)
		if extensionConfigDir:
			self._backend = BackendExtender(self._backend, **kwargs)
		self._createInstanceMethods()
	
	def __loadBackend(self, name):
		if not self._backendConfigDir:
			raise BackendConfigurationError(u"Backend config dir not given")
		if not os.path.exists(self._backendConfigDir):
			raise BackendConfigurationError(u"Backend config dir '%s' not found" % self._backendConfigDir)
		if not re.search('^[a-zA-Z0-9-_]+$', name):
			raise ValueError(u"Bad backend config name '%s'" % name)
		backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % name)
		if not os.path.exists(backendConfigFile):
			raise BackendConfigurationError(u"Backend config file '%s' not found" % backendConfigFile)
		
		l = {'socket': socket, 'os': os, 'sys': sys, 'module': '', 'config': {}}
		execfile(backendConfigFile, l)
		if not l['module']:
			raise BackendConfigurationError(u"No module defined in backend config file '%s'" % backendConfigFile)
		if not type(l['config']) is dict:
			raise BackendConfigurationError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
		exec(u'from %s import %sBackend' % (l['module'], l['module']))
		return eval(u'%sBackend(**l["config"])' % l['module'])
	
	
class BackendDispatcher(ConfigDataBackend):
	def __init__(self, **kwargs):
		
		self._dispatchConfigFile = None
		self._dispatchConfig = None
		self._dispatchIgnoreModules = []
		self._backendConfigDir = None
		self._backends = {}
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   (option == 'dispatchconfig'):
				self._dispatchConfig = value
			elif (option == 'dispatchconfigfile'):
				self._dispatchConfigFile = value
			elif option in ('dispatchignoremodules') and value:
				self._dispatchIgnoreModules = forceList(value)
			elif (option == 'backendconfigdir'):
				self._backendConfigDir = value
		
		if self._dispatchConfigFile:
			logger.info(u"Loading dispatch config file '%s'" % self._dispatchConfigFile)
			self.__loadDispatchConfig()
		if not self._dispatchConfig:
			raise BackendConfigurationError(u"Dispatcher not configured")
		self.__loadBackends()
		self._createInstanceMethods()
	
	def dispatcher_getConfig(self):
		return self._dispatchConfig
	
	def dispatcher_getBackendNames(self):
		return self._backends.keys()
	
	def backend_setOptions(self, options):
		options = forceDict(options)
		for be in self._backends.keys():
			beOptions = self._backends[be]['instance'].backend_getOptions()
			for (key, value) in options.items():
				if key in beOptions.keys():
					beOptions[key] = value
			self._backends[be]['instance'].backend_setOptions(beOptions)
		
	def backend_getOptions(self):
		options = {}
		for be in self._backends.keys():
			options.update(self._backends[be]['instance'].backend_getOptions())
		return options
		
	def __loadDispatchConfig(self):
		if not self._dispatchConfigFile:
			raise BackendConfigurationError(u"No dispatch config file defined")
		if not os.path.exists(self._dispatchConfigFile):
			raise BackendConfigurationError(u"Dispatch config file '%s' not found" % self._dispatchConfigFile)
		try:
			self._dispatchConfig = BackendDispatchConfigFile(self._dispatchConfigFile).parse()
			logger.debug(u"Read dispatch config from file '%s':" % self._dispatchConfigFile)
			logger.debug(objectToBeautifiedText(self._dispatchConfig))
		except Exception, e:
			raise BackendConfigurationError(u"Failed to load dispatch config file '%s': %s" % (self._dispatchConfigFile, e))
	
	def __loadBackends(self):
		backends = []
		if not self._backendConfigDir:
			raise BackendConfigurationError(u"Backend config dir not given")
		if not os.path.exists(self._backendConfigDir):
			raise BackendConfigurationError(u"Backend config dir '%s' not found" % self._backendConfigDir)
		for i in range(len(self._dispatchConfig)):
			if not type(self._dispatchConfig[i][1]) is list:
				self._dispatchConfig[i][1] = [ self._dispatchConfig[i][1] ]
			for value in self._dispatchConfig[i][1]:
				if not value:
					raise BackendConfigurationError(u"Bad dispatcher config '%s'" % self._dispatchConfig[i])
				if value in backends:
					continue
				backends.append(value)
		
		for backend in backends:
			self._backends[backend] = {}
			backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % backend)
			if not os.path.exists(backendConfigFile):
				raise BackendConfigurationError(u"Backend config file '%s' not found" % backendConfigFile)
			l = {'socket': socket, 'os': os, 'sys': sys, 'module': '', 'config': {}}
			logger.info(u"Loading backend config '%s'" % backendConfigFile)
			execfile(backendConfigFile, l)
			if not l['module']:
				raise BackendConfigurationError(u"No module defined in backend config file '%s'" % backendConfigFile)
			if l['module'] in self._dispatchIgnoreModules:
				logger.notice(u"Ignoring module '%s', backend '%s'" % (l['module'], backend))
				del self._backends[backend]
				continue
			if not type(l['config']) is dict:
				raise BackendConfigurationError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
			exec(u'from %s import %sBackend' % (l['module'], l['module']))
			exec(u'self._backends[backend]["instance"] = %sBackend(**l["config"])' % l['module'])
	
	def _createInstanceMethods(self):
		for member in inspect.getmembers(ConfigDataBackend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public ConfigDataBackend method '%s'" % methodName)
			methodBackends = []
			for i in range(len(self._dispatchConfig)):
				(regex, backends) = self._dispatchConfig[i]
				if not re.search(regex, methodName):
					continue
				
				for backend in forceList(backends):
					if not backend in self._backends.keys():
						logger.debug(u"Ignoring backend '%s': backend not available" % backend)
						continue
					logger.debug(u"Matched '%s' for method '%s', using backend '%s'" % (regex, methodName, backend))
					methodBackends.append(backend)
				break
			if not methodBackends:
				continue
			
			(argString, callString) = getArgAndCallString(member[1])
			
			exec(u'def %s(self, %s): return self._executeMethod(%s, "%s", %s)' % (methodName, argString, methodBackends, methodName, callString))
			setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
			
			for be in self._backends.keys():
				# Rename original method to realcall_<methodName>
				setattr(self._backends[be]['instance'], 'realcall_' + methodName, getattr(self._backends[be]['instance'], methodName))
				# Create new method <methodName> which will be called if <methodName> will be called on this object
				# If the method <methodName> is called from backend object (self.<methodName>) the method will be called on this instance
				setattr(self._backends[be]['instance'], methodName, new.instancemethod(eval(methodName), self, self.__class__))
	
	def _executeMethod(self, methodBackends, methodName, **kwargs):
		logger.debug(u"Executing method '%s' on backends: %s" % (methodName, methodBackends))
		result = None
		for methodBackend in methodBackends:
			res = eval(u'self._backends[methodBackend]["instance"].realcall_%s(**kwargs)' % methodName)
			if type(result) is list and type(res) is list:
				result.extend(res)
			elif type(result) is dict and type(res) is dict:
				result.update(res)
			elif not res is None:
				result = res
		return result
	
class BackendExtender(ExtendedBackend):
	def __init__(self, backend, **kwargs):
		if not isinstance(backend, ExtendedConfigDataBackend) and not isinstance(backend, DepotserverBackend)
			if not isinstance(backend, BackendAccessControl) or (not isinstance(backend._backend, ExtendedConfigDataBackend) and not isinstance(backend._backend, DepotserverBackend)):
				raise Exception("BackendExtender needs instance of ExtendedConfigDataBackend or DepotserverBackend as backend, got %s" % backend.__class__.__name__)
		
		ExtendedBackend.__init__(self, backend)
		
		self._extensionConfigDir = '/etc/opsi/backendManager/compose.d'
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if (option == 'extensionconfigdir'):
				self._extensionConfigDir = value
		
		if not self._backend:
			raise BackendConfigurationError(u"No backend specified")
		
		self.__loadExtensionConf()
		
		
		
	def __loadExtensionConf(self):
		if not self._extensionConfigDir:
			logger.info(u"No extensions loaded: '%s' does not exist" % self._extensionConfigDir)
			return
		try:
			confFiles = []
			files = os.listdir(self._extensionConfigDir)
			files.sort()
			for f in files:
				if not f.endswith('.conf'):
					continue
				confFiles.append( os.path.join(self._extensionConfigDir, f) )
			
			for confFile in confFiles:
				try:
					logger.info(u"Reading config file '%s'" % confFile)
					execfile(confFile)
				except Exception, e:
					raise Exception(u"Error reading file '%s': %s" % (confFile, e))
				
				for (key, val) in locals().items():
					if ( type(val) == types.FunctionType ):
						logger.debug2(u"Extending backend with instancemethod: '%s'" % key )
						setattr( self, key, new.instancemethod(val, self, self.__class__) )
		except Exception, e:
			raise BackendConfigurationError(u"Failed to read extensions from '%s': %s" % (self._extensionConfigDir, e))
	

class BackendAccessControl(object):
	
	def __init__(self, backend, **kwargs):
		
		self._backend       = backend
		self._username      = None
		self._password      = None
		self._acl           = None
		self._aclFile       = None
		self._pamService    = 'common-auth'
		self._userGroups    = []
		self._host          = None
		self._authenticated = False
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('username'):
				self._username = value
			elif option in ('password'):
				self._password = value
			elif option in ('acl'):
				self._acl = value
			elif option in ('aclfile'):
				self._aclFile = value
			elif option in ('pamservice'):
				self._pamService = value
			
		if not self._acl:
			self._acl = [ ['.*', [ {'type': u'sys_group', 'ids': [u'opsiadmin'], 'self': False, 'denyAttributes': [], 'allowAttributes': []} ] ] ]
		if not self._username:
			raise BackendAuthenticationError(u"No username specified")
		if not self._password:
			raise BackendAuthenticationError(u"No password specified")
		if not self._backend:
			raise BackendAuthenticationError(u"No backend specified")
		if isinstance(self._backend, BackendAccessControl):
			raise BackendConfigurationError(u"Cannot use BackendAccessControl instance as backend")
		
		# TODO: forceACL
		#for i in range(len(self._acl)):
		#	self._acl[i][0] = re.compile(self._acl[i][0])
		#	self._acl[i][1] = forceUnicodeList(self._acl[i][1])
			
		try:
			if re.search('^[^\.]+\.[^\.]+\.\S+$', self._username):
				# Username starts with something like hostname.domain.tld:
				# Assuming it is a host passing his FQDN as username
				self._username = self._username.lower()
				
				logger.debug(u"Trying to authenticate by opsiHostKey...")
				
				if not hasattr(self._backend, 'host_getObjects'):
					raise Exception(u"Passed backend has no method 'host_getObjects', cannot authentidate host '%s'" % self._username)
				
				host = self._backend.host_getObjects(id = self._username)
				if not host:
					raise Exception(u"Host '%s' not found" % self._username)
				self._host = host[0]
				
				if not self._host.opsiHostKey:
					raise Exception(u"OpsiHostKey not found for host '%s'" % self._username)
					
				logger.confidential(u"Client '%s', key sent '%s', key stored '%s'" \
						% (self._username, self._password, self._host.opsiHostKey))
				
				if (self._password != self._host.opsiHostKey):
					raise BackendAuthenticationError(u"OpsiHostKey authentication failed for host '%s': wrong key" \
										% self._host.id)
				
				logger.info(u"OpsiHostKey authentication successful for host '%s'" % self._host.id)
			else:
				# System user trying to log in with username and password
				logger.debug(u"Trying to authenticate by operating system...")
				self._authenticateUser()
				# Authentication did not throw exception => authentication successful
				logger.info(u"Operating system authentication successful for user '%s', groups '%s'" \
									% (self._username, ','.join(self._userGroups)))
		except Exception, e:
			raise BackendAuthenticationError(u"%s" % e)
		
		self._createInstanceMethods()
		if self._aclFile:
			self.__loadACLFile()
		self._authenticated = True
	
	def accessControl_authenticated(self):
		return self._authenticated
	
	def accessControl_userIsAdmin(self):
		return self._isMemberOfGroup('opsiadmin')
	
	def __loadACLFile(self):
		try:
			if not self._aclFile:
				raise Exception(u"No acl file defined")
			if not os.path.exists(self._aclFile):
				raise Exception(u"Acl file '%s' not found" % self._aclFile)
			self._acl = BackendACLFile(self._aclFile).parse()
			logger.debug(u"Read acl from file '%s':" % self._aclFile)
			logger.debug(objectToBeautifiedText(self._acl))
		except Exception, e:
			logger.logException(e)
			raise BackendConfigurationError(u"Failed to load acl file '%s': %s" % (self._aclFile, e))
	
	def _createInstanceMethods(self):
		for member in inspect.getmembers(self._backend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public method '%s'" % methodName)
			
			(argString, callString) = getArgAndCallString(member[1])
			
			exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))
			setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
	
	def _authenticateUser(self):
		''' Authenticate a user by the underlying operating system.
		    Throws BackendAuthenticationError on failure. '''
		if (os.name == 'posix'):
			# Posix os => authenticate by PAM
			self._pamAuthenticateUser()
		elif (os.name == 'nt'):
			# NT os => authenticate by windows-login
			self._winAuthenticateUser()
		else:
			# Other os, not implemented yet
			raise NotImplemetedError("Sorry, operating system '%s' not supported yet!" % os.name)
		
	def _winAuthenticateUser(self):
		'''
		Authenticate a user by Windows-Login on current machine
		'''
		logger.confidential(u"Trying to authenticate user '%s' with password '%s' by win32security" % (self._username, self._password))
		
		try:
			win32security.LogonUser(self._username, 'None', self._password, win32security.LOGON32_LOGON_NETWORK, win32security.LOGON32_PROVIDER_DEFAULT)
			
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
							if (username.lower() == self._username.lower()):
								self._userGroups.append(groupname)
								logger.debug(u"User '%s' is member of group '%s'" % (self._username, groupname))
						if (uresume == 0):
							break
					if (gresume == 0):
						break
		except Exception, e:
			# Something failed => raise authentication error
			raise BackendAuthenticationError(u"Win32security authentication failed for user '%s': %s" % (self._username, e))
		
	def _pamAuthenticateUser(self):
		'''
		Authenticate a user by PAM (Pluggable Authentication Modules).
		Important: the uid running this code needs access to /etc/shadow 
		if os uses traditional unix authentication mechanisms.
		'''
		logger.confidential(u"Trying to authenticate user '%s' with password '%s' by PAM" % (self._username, self._password))
		
		
		class AuthConv:
			''' Handle PAM conversation '''
			def __init__(_, user, password):
				_.user = user
				_.password = password
			
			def __call__(_, auth, query_list, userData=None):
				response = []
				for i in range(len(query_list)):
					(query, type) = query_list[i]
					logger.debug(u"PAM conversation: query '%s', type '%s'" % (query, type))
					if (type == PAM.PAM_PROMPT_ECHO_ON):
						response.append((_.user, 0))
					elif (type == PAM.PAM_PROMPT_ECHO_OFF):
						response.append((_.password, 0))
					elif (type == PAM.PAM_PROMPT_ERROR_MSG) or (type == PAM.PAM_PROMPT_TEXT_INFO):
						response.append(('', 0));
					else:
						return None
				return response
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
			except:
				pass
			auth.authenticate()
			auth.acct_mgmt()
			
			self._userGroups = [ grp.getgrgid( pwd.getpwnam(self._username)[3] )[0] ]
			logger.debug(u"Primary group of user '%s' is '%s'" % (self._username, self._userGroups[0]))
			groups = grp.getgrall()
			for group in groups:
				if self._username in group[3]:
					self._userGroups.append(group[0])
					logger.debug(u"User '%s' is member of group '%s'" % (self._username, group[0]))
		
		except Exception, e:
			raise BackendAuthenticationError(u"PAM authentication failed for user '%s': %s" % (self._username, e))
	
	def _isMemberOfGroup(self, ids):
		for id in forceUnicodeList(ids):
			if id in self._userGroups:
				return True
		return False
		
	def _isUser(self, ids):
		for id in forceUnicodeList(ids):
			if (id == self._username):
				return True
		return False
		
	def _isOpsiDepotserver(self, ids=[]):
		if not self._host or not isinstance(self._host, OpsiDepotserver):
			return False
		if not ids:
			return True
		for id in forceUnicodeList(ids):
			if (id == self._host.id):
				return True
		return False
		
	def _isOpsiClient(self, ids=[]):
		if not self._host or not isinstance(self._host, OpsiClient):
			return False
		if not ids:
			return True
		for id in forceUnicodeList(ids):
			if (id == self._host.id):
				return True
		return False
	
	def _isSelf(self, **params):
		if not params:
			return False
		for (param, value) in params.items():
			if type(value) is types.ClassType and issubclass(value, Object) and (value.id == self._username):
				return True
			if param in ('id', 'objectId', 'hostId', 'clientId', 'serverId', 'depotId') and (value == self._username):
				return True
		return False
	
	def _executeMethod(self, methodName, **kwargs):
		granted = False
		newKwargs = {}
		acl = None
		logger.debug(u"Access control for method '%s' params %s" % (methodName, kwargs))
		for (regex, acl) in self._acl:
			logger.debug2(u"Testing acl %s: %s for method '%s'" % (regex, acl, methodName))
			if not re.search(regex, methodName):
				continue
			logger.info(u"Found matching acl %s for method '%s'" % (acl, methodName))
			for entry in acl:
				aclType = entry.get('type')
				ids = entry.get('ids', [])
				newGranted = False
				if (aclType == 'all'):
					newGranted = True
				elif (aclType == 'opsi_depotserver'):
					newGranted = self._isOpsiDepotserver(ids)
				elif (aclType == 'opsi_client'):
					newGranted = self._isOpsiClient(ids)
				elif (aclType == 'sys_group'):
					newGranted = self._isMemberOfGroup(ids)
				elif (aclType == 'sys_user'):
					newGranted = self._isUser(ids)
				elif (aclType == 'self'):
					newGranted = 'partial'
				else:
					logger.error(u"Unhandled acl entry type: %s" % aclType)
					continue
				
				if (entry.get('denyAttributes') or entry.get('allowAttributes')):
					newGranted = 'partial'
				
				if newGranted:
					granted = newGranted
				if granted is True:
					break
			if granted:
				acl = entry
				if granted is True:
					break
			
		logger.debug("acl: %s" % acl)
		if granted:
			if (str(granted) == 'partial'):
				logger.debug(u"Partial access to method '%s' granted to user '%s' by acl %s" % (methodName, self._username, acl))
			else:
				logger.debug(u"Access to method '%s' granted to user '%s' by acl %s" % (methodName, self._username, acl))
		else:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s'" % (methodName, self._username))
		
		try:
			if (str(granted) == 'partial'):
				# Filter incoming params
				newKwargs = self._filterParams(kwargs, [acl])
			else:
				newKwargs = kwargs
		except Exception, e:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s': %s" % (methodName, self._username, e))
		
		logger.debug2("kwargs:    %s" % kwargs)
		logger.debug2("newKwargs: %s" % newKwargs)
		
		result = eval(u'self._backend.%s(**newKwargs)' % methodName)
		
		if (str(granted) == 'partial'):
			# Filter result
			result = self._filterResult(result, [acl])
		
		return result
		
	
	def _filterParams(self, params, acls):
		newParams = {}
		for (key, value) in params.items():
			if not value:
				newParams[key] = value
			elif (key == 'attributes'):
				newParams[key] = self._filterAttributes(value, acls)
			elif key in ('id', 'objectId', 'hostId', 'clientId', 'depotId', 'serverId'):
				granted = False
				for acl in acls:
					if (acl.get('type') != 'self') or (value == self._username):
						granted = True
						break
				if not granted:
					raise BackendPermissionDeniedError(u"Access to %s '%s' denied" % (key, value))
				newParams[key] = value
			else:
				valueList = forceList(value)
				if issubclass(valueList[0].__class__, BaseObject):
					newParams[key] = self._filterObjects(value, acls)
				else:
					newParams[key] = value
				if not newParams.get(key):
					raise BackendPermissionDeniedError(u"Access to given object(s) denied")
		return newParams
	
	def _filterResult(self, result, acls):
		if result:
			resultList = forceList(result)
			if issubclass(resultList[0].__class__, BaseObject):
				return self._filterObjects(result, acls, raiseOnTruncate = False)
		return result
	
	def _filterAttributes(self, attributes, acls):
		newAttributes = []
		for attribute in attributes:
			for acl in acls:
				if not (acl.get('denyAttributes', []) and not acl.get('allowAttributes', [])):
					logger.debug2(u"Allowing all attributes: %s" % attributes)
					# full access, do not check other acls
					return attributes
				if attribute in acl.get('denyAttributes', []):
					continue
				if acl.get('allowAttributes', []) and not attribute in acl['allowAttributes']:
					continue
				newAttributes.append(attribute)
		return newAttributes
		
	def _filterObjects(self, objects, acls, raiseOnTruncate=True):
		newObjects = []
		for entry in forceList(objects):
			hash = entry.toHash()
			for acl in acls:
				if (acl.get('type') == 'self'):
					if ( hash.get('id', hash.get('objectId', hash.get('hostId', hash.get('clientId', hash.get('depotId', hash.get('serverId')))))) == self._username ):
						if not (acl.get('denyAttributes', []) and not acl.get('allowAttributes', [])):
							newObjects.append(entry)
							logger.debug2(u"Granting full access to %s" % entry)
							# full access, do not check other acls
							break
					else:
						# next acl
						continue
				
				if (acl.get('denyAttributes', []) or acl.get('allowAttributes', [])):
					newHash = { 'type': hash.get('type') }
					for arg in mandatoryConstructorArgs(entry.__class__):
						newHash[arg] = hash.get(arg)
					for (key, value) in hash.items():
						if key in newHash.keys():
							continue
						if key in acl.get('denyAttributes', []):
							if not value is None and raiseOnTruncate:
								raise BackendPermissionDeniedError(u"Access to attribute '%s' denied" % key)
							continue
						if acl.get('allowAttributes', []) and not key in acl['allowAttributes']:
							if not value is None and raiseOnTruncate:
								raise BackendPermissionDeniedError(u"Access to attribute '%s' denied" % key)
							continue
						newHash[key] = value
					logger.debug2(u"Granting partial access to %s" % entry)
					newObjects.append(entry.__class__.fromHash(newHash))
		if not type(objects) in (list, tuple):
			if not newObjects:
				return None
			return newObjects[0]
		return newObjects
	
