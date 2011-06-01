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

__version__ = '4.0'

import os, sys, new, inspect, re, types, socket, copy

if (os.name == 'posix'):
	import PAM, pwd, grp
elif (os.name == 'nt'):
	import win32security, win32net

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import BaseObject
from OPSI.Backend.Backend import *
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Backend.Depotserver import DepotserverBackend
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Util import objectToBeautifiedText
from OPSI.Util.File.Opsi import BackendACLFile, BackendDispatchConfigFile

# Get logger instance
logger = Logger()

DISTRIBUTOR = 'unknown'
try:
	f = os.popen('lsb_release -i 2>/dev/null')
	DISTRIBUTOR = f.read().split(':')[1].strip()
	f.close()
except Exception, e:
	pass
DISTRIBUTION = 'unknown'
try:
	f = os.popen('lsb_release -d 2>/dev/null')
	DISTRIBUTION = f.read().split(':')[1].strip()
	f.close()
except Exception, e:
	pass

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                  CLASS BACKENDMANAGER                                              =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class BackendManager(ExtendedBackend):
	def __init__(self, **kwargs):
		self._backend = None
		self._backendConfigDir = None
		self._options = {}
		self._overwrite = True
		self._context = self
		
		Backend.__init__(self, **kwargs)
		
		username = None
		password = None
		dispatch = False
		extend = False
		extensionConfigDir = None
		extensionClass = None
		accessControl = False
		depotBackend = False
		hostControlBackend = False
		
		loadBackend = None
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('username',):
				username = value
			elif option in ('password',):
				password = value
			elif option in ('backend',):
				if type(value) in (str, unicode):
					loadBackend = value
				else:
					self._backend = value
				del kwargs[option]
			elif option in ('backendconfigdir',):
				self._backendConfigDir = value
			elif option in ('dispatchconfig', 'dispatchconfigfile') and value:
				dispatch = True
			elif option in ('depotbackend',):
				depotBackend = forceBool(value)
			elif option in ('hostcontrolbackend',):
				hostControlBackend = forceBool(value)
			elif option in ('extensionconfigdir',) and value:
				extensionConfigDir = value
				extend = True
			elif option in ('extensionclass',):
				extensionClass = value
				extend = True
			elif option in ('extend',):
				extend = forceBool(value)
			elif option in ('acl', 'aclfile') and value:
				accessControl = True
		
		if loadBackend:
			logger.info(u"* BackendManager is loading backend '%s'" % loadBackend)
			self._backend = self.__loadBackend(loadBackend)
			# self._backend is now a ConfigDataBackend
		
		if not dispatch and not self._backend:
			raise BackendConfigurationError(u"Neither backend nor dispatch config given")
		
		if dispatch:
			logger.info(u"* BackendManager is creating BackendDispatcher")
			self._backend = BackendDispatcher(context = self, **kwargs)
			# self._backend is now a BackendDispatcher which is a ConfigDataBackend
		if extend or depotBackend:
			logger.info(u"* BackendManager is creating ExtendedConfigDataBackend")
			# DepotserverBackend/BackendExtender need ExtendedConfigDataBackend backend
			self._backend = ExtendedConfigDataBackend(self._backend)
			# self._backend is now an ExtendedConfigDataBackend
		if depotBackend:
			logger.info(u"* BackendManager is creating DepotserverBackend")
			self._backend = DepotserverBackend(self._backend)
		if hostControlBackend:
			logger.info(u"* BackendManager is creating HostControlBackend")
			hcc = {}
			try:
				hcc = self.__loadBackendConfig('hostcontrol')['config']
			except Exception, e:
				logger.error(e)
			self._backend = HostControlBackend(self._backend, **hcc)
		if accessControl:
			logger.info(u"* BackendManager is creating BackendAccessControl")
			self._backend = BackendAccessControl(backend = self._backend, **kwargs)
		if extensionConfigDir or extensionClass:
			logger.info(u"* BackendManager is creating BackendExtender")
			self._backend = BackendExtender(self._backend, **kwargs)
		
		self._createInstanceMethods()
	
	def __loadBackendConfig(self, name):
		if not self._backendConfigDir:
			raise BackendConfigurationError(u"Backend config dir not given")
		if not os.path.exists(self._backendConfigDir):
			raise BackendConfigurationError(u"Backend config dir '%s' not found" % self._backendConfigDir)
		if not re.search('^[a-zA-Z0-9-_]+$', name):
			raise ValueError(u"Bad backend config name '%s'" % name)
		name = name.lower()
		backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % name)
		if not os.path.exists(backendConfigFile):
			raise BackendConfigurationError(u"Backend config file '%s' not found" % backendConfigFile)
		
		l = {'socket': socket, 'os': os, 'sys': sys, 'module': '', 'config': {}}
		execfile(backendConfigFile, l)
		return l
		
	def __loadBackend(self, name):
		config = self.__loadBackendConfig(name)
		if not config['module']:
			raise BackendConfigurationError(u"No module defined in backend config file '%s'" % backendConfigFile)
		if not type(config['config']) is dict:
			raise BackendConfigurationError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
		config['config']['name'] = name
		exec(u'from %s import %sBackend' % (config['module'], config['module']))
		return eval(u'%sBackend(**config["config"])' % config['module'])
	
class BackendDispatcher(Backend):
	def __init__(self, **kwargs):
		Backend.__init__(self, **kwargs)
		
		self._dispatchConfigFile = None
		self._dispatchConfig = None
		self._dispatchIgnoreModules = []
		self._backendConfigDir = None
		self._backends = {}
		self._options = {}
		self._context = self
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('dispatchconfig',):
				self._dispatchConfig = value
			elif option in ('dispatchconfigfile',):
				self._dispatchConfigFile = value
			elif option in ('dispatchignoremodules',) and value:
				self._dispatchIgnoreModules = forceList(value)
			elif option in ('backendconfigdir',):
				self._backendConfigDir = value
			elif option in ('context',):
				self._context = value
		
		if self._dispatchConfigFile:
			logger.info(u"Loading dispatch config file '%s'" % self._dispatchConfigFile)
			self.__loadDispatchConfig()
		if not self._dispatchConfig:
			raise BackendConfigurationError(u"Dispatcher not configured")
		self.__loadBackends()
		self._createInstanceMethods()
	
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
			backendInstance = None
			l["config"]["context"] = self
			if (sys.version_info >= (2,5)):
				b = __import__(l['module'], globals(), locals(), "%sBackend" % l['module'], -1)
				self._backends[backend]["instance"] = getattr(b, "%sBackend"%l['module'])(**l['config'])
			else:
				exec('from %s import %sBackend' % (l['module'], l['module']))
				exec('b = %sBackend(**l["config"])' % l['module'])
				self._backends[backend]["instance"] = b
			
	def _createInstanceMethods(self):
		logger.debug(u"BackendDispatcher is creating instance methods")
		for Class in (ConfigDataBackend,):#, ExtendedConfigDataBackend):
			for member in inspect.getmembers(Class, inspect.ismethod):
				methodName = member[0]
				if methodName.startswith('_'):
					# Not a public method
					continue
				logger.debug2(u"Found public %s method '%s'" % (Class.__name__, methodName))
				
				if hasattr(self, methodName):
					logger.debug(u"%s: overwriting method %s" % (self.__class__.__name__, methodName))
					continue
				
				methodBackends = []
				for i in range(len(self._dispatchConfig)):
					(regex, backends) = self._dispatchConfig[i]
					if not re.search(regex, methodName):
						continue
					
					for backend in forceList(backends):
						if not backend in self._backends.keys():
							logger.debug(u"Ignoring backend '%s': backend not available" % backend)
							continue
						methodBackends.append(backend)
					logger.debug(u"'%s' matches method '%s', dispatching to backends: %s" % (regex, methodName, u', '.join(methodBackends)))
					break
				if not methodBackends:
					continue
				
				(argString, callString) = getArgAndCallString(member[1])
				
				exec(u'def %s(self, %s): return self._dispatchMethod(%s, "%s", %s)' % (methodName, argString, methodBackends, methodName, callString))
				setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
				
				#for be in self._backends.keys():
				#	setattr(self._backends[be]['instance'], '_realcall_' + methodName, getattr(self._backends[be]['instance'], methodName))
				#	setattr(self._backends[be]['instance'], methodName, new.instancemethod(eval(methodName), self, self.__class__))
				
	def _dispatchMethod(self, methodBackends, methodName, **kwargs):
		logger.debug(u"Dispatching method '%s' to backends: %s" % (methodName, methodBackends))
		result = None
		objectIdents = []
		for methodBackend in methodBackends:
			meth = getattr(self._backends[methodBackend]["instance"], methodName)
			res =  meth(**kwargs)
			if type(res) is types.ListType:
				# Remove duplicates
				newRes = []
				for r in res:
					if isinstance(r, BaseObject):
						ident = r.getIdent()
						if ident in objectIdents:
							continue
						objectIdents.append(ident)
					newRes.append(r)
				res = newRes
			if type(result) is types.ListType and type(res) is types.ListType:
				result.extend(res)
			elif type(result) is types.DictType and type(res) is types.DictType:
				result.update(res)
			elif not res is None:
				result = res
		return result
	
	def backend_setOptions(self, options):
		Backend.backend_setOptions(self, options)
		for be in self._backends.values():
			be['instance'].backend_setOptions(options)
		
	def backend_getOptions(self):
		options = Backend.backend_getOptions(self)
		for be in self._backends.values():
			options.update(be['instance'].backend_getOptions())
		return options
	
	def backend_exit(self):
		for be in self._backends.values():
			be['instance'].backend_exit()
	
	def dispatcher_getConfig(self):
		return self._dispatchConfig
	
	def dispatcher_getBackendNames(self):
		return self._backends.keys()
	
class BackendExtender(ExtendedBackend):
	def __init__(self, backend, **kwargs):
		if not isinstance(backend, ExtendedBackend) and not isinstance(backend, BackendDispatcher):
			if not isinstance(backend, BackendAccessControl) or (not isinstance(backend._backend, ExtendedBackend) and not isinstance(backend._backend, BackendDispatcher)):
				raise Exception("BackendExtender needs instance of ExtendedBackend or BackendDispatcher as backend, got %s" % backend.__class__.__name__)
		
		ExtendedBackend.__init__(self, backend, overwrite = kwargs.get('overwrite', True))
		
		self._extensionConfigDir = None
		self._extensionClass = None
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if (option == 'extensionconfigdir'):
				self._extensionConfigDir = value
			if (option == 'extensionclass'):
				self._extensionClass = value
		
		self.__createExtensions()
	
	def __createExtensions(self):
		if self._extensionClass:
			for member in inspect.getmembers(self._extensionClass, inspect.ismethod):
				methodName = member[0]
				if methodName.startswith('_'):
					continue
				logger.debug2(u"Extending %s with instancemethod: '%s'" % (self._backend.__class__.__name__, methodName))
				new_function = new.function( member[1].func_code, member[1].func_globals, member[1].func_code.co_name )
				new_method = new.instancemethod( new_function, self, self.__class__ )
				setattr( self, methodName, new_method )
				#setattr( sldworks.ISldWorks, 'OpenDoc6', new_method )
				#setattr( self, methodName, new.instancemethod(member[1], self, self.__class__) )

		if self._extensionConfigDir:
			if not os.path.exists(self._extensionConfigDir):
				logger.error(u"No extensions loaded: '%s' does not exist" % self._extensionConfigDir)
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
						logger.logException(e)
						raise Exception(u"Error reading file '%s': %s" % (confFile, e))
					
					
					for (key, val) in locals().items():
						if ( type(val) == types.FunctionType ):
							logger.debug2(u"Extending %s with instancemethod: '%s'" % (self._backend.__class__.__name__, key))
							setattr( self, key, new.instancemethod(val, self, self.__class__) )
			except Exception, e:
				raise BackendConfigurationError(u"Failed to read extensions from '%s': %s" % (self._extensionConfigDir, e))

class BackendAccessControl(object):
	
	def __init__(self, backend, **kwargs):
		
		self._backend       = backend
		self._context       = backend
		self._username      = None
		self._password      = None
		self._acl           = None
		self._aclFile       = None
		self._pamService    = 'common-auth'
		self._userGroups    = []
		self._forceGroups   = None
		self._host          = None
		self._authenticated = False
		
		if (DISTRIBUTOR.lower().find('suse') != -1):
			self._pamService = 'sshd'
		elif (DISTRIBUTOR.lower().find('redhat') != -1) or (DISTRIBUTOR.lower().find('centos') != -1) or (DISTRIBUTOR.lower().find('scientificsl') != -1) or (DISTRIBUTOR.lower().find('sme') != -1):
			self._pamService = 'system-auth'
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('username',):
				self._username = value
			elif option in ('password',):
				self._password = value
			elif option in ('acl',):
				self._acl = value
			elif option in ('aclfile',):
				self._aclFile = value
			elif option in ('pamservice',):
				self._pamService = value
			elif option in ('context', 'accesscontrolcontext'):
				self._context = value
			elif option in ('forcegroups',):
				if not value is None:
					self._forceGroups = forceUnicodeList(value)
			
		if not self._acl:
			self._acl = [ ['.*', [ {'type': u'sys_group', 'ids': [u'opsiadmin'], 'denyAttributes': [], 'allowAttributes': []} ] ] ]
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
				
				if not hasattr(self._context, 'host_getObjects'):
					raise Exception(u"Passed backend has no method 'host_getObjects', cannot authenticate host '%s'" % self._username)
				
				host = self._context.host_getObjects(id = self._username)
				if not host:
					raise Exception(u"Host '%s' not found in backend %s" % (self._username, self._context))
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
		return self._isMemberOfGroup('opsiadmin') or self._isOpsiDepotserver()
	
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
		protectedMethods = []
		for Class in (ExtendedConfigDataBackend, ConfigDataBackend, DepotserverBackend, HostControlBackend):
			for member in inspect.getmembers(Class, inspect.ismethod):
				methodName = member[0]
				if methodName.startswith('_'):
					continue
				if not methodName in protectedMethods:
					protectedMethods.append(methodName)
		
		for member in inspect.getmembers(self._backend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			
			(argString, callString) = getArgAndCallString(member[1])
			
			if methodName in protectedMethods:
				logger.debug2(u"Protecting %s method '%s'" % (Class.__name__, methodName))
				exec(u'def %s(self, %s): return self._executeMethodProtected("%s", %s)' % (methodName, argString, methodName, callString))
			else:
				logger.debug2(u"Not protecting %s method '%s'" % (Class.__name__, methodName))
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
			if not self._forceGroups is None:
				self._userGroups = self._forceGroups
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
					elif (type == PAM.PAM_ERROR_MSG) or (type == PAM.PAM_TEXT_INFO):
						response.append(('', 0))
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
			
			if not self._forceGroups is None:
				self._userGroups = self._forceGroups
				logger.info(u"Forced groups for user '%s': %s" % (self._username, self._userGroups))
			else:
				self._userGroups = [ forceUnicode( grp.getgrgid( pwd.getpwnam(self._username)[3] )[0] ) ]
				logger.debug(u"Primary group of user '%s' is '%s'" % (self._username, self._userGroups[0]))
				groups = grp.getgrall()
				for group in groups:
					if self._username in group[3]:
						gn = forceUnicode(group[0])
						if not gn in self._userGroups:
							self._userGroups.append(gn)
							logger.debug(u"User '%s' is member of group '%s'" % (self._username, gn))
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
		meth = getattr(self._backend, methodName)
		return meth(**kwargs)
	
	def _executeMethodProtected(self, methodName, **kwargs):
		granted = False
		newKwargs = {}
		acls = []
		logger.debug(u"Access control for method '%s' params %s" % (methodName, kwargs))
		for (regex, acl) in self._acl:
			logger.debug2(u"Testing acl %s: %s for method '%s'" % (regex, acl, methodName))
			if not re.search(regex, methodName):
				continue
			logger.debug(u"Found matching acl %s for method '%s'" % (acl, methodName))
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
					newGranted = 'partial_object'
				else:
					logger.error(u"Unhandled acl entry type: %s" % aclType)
					continue
				
				if newGranted is False:
					continue
				
				if (entry.get('denyAttributes') or entry.get('allowAttributes')):
					newGranted = 'partial_attributes'
				
				if newGranted:
					acls.append(entry)
					granted = newGranted
				if granted is True:
					break
			#if granted:
			break
		
		logger.info("Method: %s, using acls: %s" % (methodName, acls))
		if   granted is True:
			logger.debug(u"Full access to method '%s' granted to user '%s' by acl %s" % (methodName, self._username, acls[0]))
			newKwargs = kwargs
		elif granted is False:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s'" % (methodName, self._username))
		else:
			logger.debug(u"Partial access to method '%s' granted to user '%s' by acls %s" % (methodName, self._username, acls))
			try:
				
				newKwargs = self._filterParams(kwargs, acls)
				if not newKwargs:
					raise BackendPermissionDeniedError(u"No allowed param supplied")
			except Exception, e:
				logger.logException(e, LOG_INFO)
				raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s': %s" % (methodName, self._username, e))
		
		logger.debug("newKwargs: %s" % newKwargs)
		
		meth = getattr(self._backend, methodName)
		result = meth(**newKwargs)
		
		if granted is True:
			return result
		
		# Filter result
		return self._filterResult(result, acls)
		
	
	def _filterParams(self, params, acls):
		params = dict(params)
		logger.debug(u"Filtering params: %s" % params)
		for (key, value) in params.items():
			isList = type(value) is list
			valueList = forceList(value)
			if (len(valueList) == 0):
				continue
			if issubclass(valueList[0].__class__, BaseObject) or type(valueList[0]) is types.DictType:
				valueList = self._filterObjects(valueList, acls, exceptionOnTruncate = False)
				if isList:
					params[key] = valueList
				else:
					if (len(valueList) > 0):
						params[key] = valueList[0]
					else:
						del params[key]
		return params
	
	def _filterResult(self, result, acls):
		if result:
			isList = type(result) is list
			resultList = forceList(result)
			if issubclass(resultList[0].__class__, BaseObject) or type(resultList[0]) is types.DictType:
				resultList = self._filterObjects(result, acls, exceptionOnTruncate = False, exceptionIfAllRemoved = False)
				if isList:
					return resultList
				else:
					if (len(resultList) > 0):
						return resultList[0]
					else:
						return None
		return result
	
	def _filterObjects(self, objects, acls, exceptionOnTruncate=True, exceptionIfAllRemoved=True):
		logger.info(u"Filtering objects by acls")
		newObjects = []
		for obj in forceList(objects):
			allowedAttributes = []
			isDict = type(obj) is types.DictType
			if isDict:
				objHash = obj
			else:
				objHash = obj.toHash()
			
			for acl in acls:
				if (acl.get('type') == 'self'):
					objectId = objHash.get('id', objHash.get('objectId', objHash.get('hostId', objHash.get('clientId', objHash.get('depotId', objHash.get('serverId'))))))
					if not objectId or (objectId != self._username):
						continue
				
				if   acl.get('allowAttributes', []):
					for attribute in acl['allowAttributes']:
						if not attribute in allowedAttributes:
							allowedAttributes.append(attribute)
				elif acl.get('denyAttributes', []):
					for attribute in objHash.keys():
						if not attribute in acl['denyAttributes'] and not attribute in allowedAttributes:
							allowedAttributes.append(attribute)
				else:
					for attribute in objHash.keys():
						if not attribute in allowedAttributes:
							allowedAttributes.append(attribute)
			
			if not allowedAttributes:
				continue
			
			if not isDict:
				if not 'type' in allowedAttributes:
					allowedAttributes.append('type')
				for attribute in mandatoryConstructorArgs(obj.__class__):
					if not attribute in allowedAttributes:
						allowedAttributes.append(attribute)
			for key in objHash.keys():
				if not key in allowedAttributes:
					if exceptionOnTruncate:
						raise BackendPermissionDeniedError(u"Access to attribute '%s' denied" % key)
					del objHash[key]
			if isDict:
				newObjects.append(objHash)
			else:
				newObjects.append(obj.__class__.fromHash(objHash))
		orilen = len(objects)
		newlen = len(newObjects)
		if (newlen < orilen):
			logger.warning(u"%d objects removed by acl, %d objects left" % (orilen-newlen, newlen))
			if (newlen == 0) and exceptionIfAllRemoved:
				raise BackendPermissionDeniedError(u"Access denied")
		return newObjects



def backendManagerFactory(user, password, dispatchConfigFile, backendConfigDir,
				extensionConfigDir, aclFile, depotId, postpath, context, **kwargs):
	backendManager = None
	if   (len(postpath) == 2) and (postpath[0] == 'backend'):
		backendManager = BackendManager(
			backend              = postpath[1],
			accessControlContext = context,
			backendConfigDir     = backendConfigDir,
			aclFile              = aclFile,
			username             = user,
			password             = password,
			**kwargs
		)
	elif (len(postpath) == 2) and (postpath[0] == 'extend'):
		extendPath = postpath[1]
		if not re.search('^[a-zA-Z0-9\_\-]+$', extendPath):
			raise ValueError(u"Extension config path '%s' refused" % extendPath)
		backendManager = BackendManager(
			dispatchConfigFile   = dispatchConfigFile,
			backendConfigDir     = backendConfigDir,
			extensionConfigDir   = os.path.join(extensionConfigDir, extendPath),
			aclFile              = aclFile,
			accessControlContext = context,
			depotBackend         = bool(depotId),
			hostControlBackend   = True,
			username             = user,
			password             = password,
			**kwargs
		)
	else:
		backendManager = BackendManager(
			dispatchConfigFile   = dispatchConfigFile,
			backendConfigDir     = backendConfigDir,
			extensionConfigDir   = extensionConfigDir,
			aclFile              = aclFile,
			accessControlContext = context,
			depotBackend         = bool(depotId),
			hostControlBackend   = True,
			username             = user,
			password             = password,
			**kwargs
		)

	return backendManager
	
	
	
if (__name__ == '__main__'):
	cdb = ConfigDataBackend()
	class TestClass(object):
		def testMethod(self, y):
			print "test", y, self
		def testMethod2(self):
			print self.backend_getOptions()
		
	bm = BackendManager( backend = cdb, extensionClass = TestClass )
	bm.testMethod('yyyyyyyy')
	bm.testMethod2()
	
	
	
	
	
	
	
	
	
	
	
	
	
