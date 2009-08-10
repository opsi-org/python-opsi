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

import new, inspect, re, types

# OPSI imports
from OPSI.Logger import *
from Backend import *
from OPSI.Util.File import OpsiBackendACLFile, OpsiBackendDispatchConfigFile

# Get logger instance
logger = Logger()

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                  CLASS BACKENDMANAGER                                              =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class BackendManager(DataBackend):
	def __init__(self, username = '', password = '', address = '', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		self._compositionConfigDir = '/etc/opsi/backendManager/compose.d'
		self.__loadCompositionConf()
		
	def __loadCompositionConf(self):
		if not self._compositionConfigDir:
			return
		try:
			confFiles = []
			files = os.listdir(self._compositionConfigDir)
			files.sort()
			for f in files:
				if not f.endswith('.conf'):
					continue
				confFiles.append( os.path.join(self._compositionConfigDir, f) )
			
			for confFile in confFiles:
				try:
					logger.info("Reading config file '%s'" % confFile)
					execfile(confFile)
				except Exception, e:
					raise Exception("Error reading file '%s': %s" % (confFile, e))
			
				for (key, val) in locals().items():
					if ( type(val) == types.FunctionType ):
						logger.debug2("Adding composition instancemethod: '%s'" % key )
						setattr( self.__class__, key, new.instancemethod(val, None, self.__class__) )
		except Exception, e:
			raise Exception("Failed to read composition config from '%s': %s" % (self._compositionConfigDir, e))

class BackendDispatcher(DataBackend):
	def __init__(self, username = '', password = '', address = '', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		
		self._dispatchConfigFile = None
		self._dispatchConfig = [ ['.*', []] ]
		self._backendConfigDir = None
		self._backends = {}
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   (option == 'dispatchconfig'):
				self._dispatchConfig = value
			elif (option == 'dispatchconfigfile'):
				self._dispatchConfigFile = value
			elif (option == 'backendconfigdir'):
				self._backendConfigDir = value
		
		if self._dispatchConfigFile:
			logger.info("Loading dispatch config file '%s'" % self._dispatchConfigFile)
			self.__loadDispatchConfig()
		self.__loadBackends()
		self.__createInstanceMethods()
		
	
	def __loadDispatchConfig(self):
		if not self._dispatchConfigFile:
			raise Exception(u"No dispatch config file defined")
		if not os.path.exists(self._dispatchConfigFile):
			raise Exception(u"Dispatch config file '%s' not found" % self._dispatchConfigFile)
		try:
			self._dispatchConfig = OpsiBackendDispatchConfigFile(self._dispatchConfigFile).parse()
			logger.debug(u"Read dispatch config from file '%s':" % self._dispatchConfigFile)
			logger.debug(Tools.objectToBeautifiedText(self._dispatchConfig))
		except Exception, e:
			raise Exception(u"Failed to load dispatch config file '%s': %s" % (self._dispatchConfigFile, e))
	
	def __loadBackends(self):
		backends = []
		if not os.path.exists(self._backendConfigDir):
			raise Exception(u"No backend config dir given")
		for i in range(len(self._dispatchConfig)):
			if not type(self._dispatchConfig[i][1]) is list:
				self._dispatchConfig[i][1] = [ self._dispatchConfig[i][1] ]
			for value in self._dispatchConfig[i][1]:
				if value in backends:
					continue
				backends.append(value)
		for backend in backends:
			self._backends[backend] = {}
			backendConfigFile = os.path.join(self._backendConfigDir, '%s.conf' % backend)
			if not os.path.exists(backendConfigFile):
				raise Exception(u"Backend config file '%s' not found" % backendConfigFile)
			l = {'module': '', 'config': {}}
			execfile(backendConfigFile, l)
			if not l['module']:
				raise Exception(u"No module defined in backend config file '%s'" % backendConfigFile)
			if not type(l['config']) is dict:
				raise TypeError(u"Bad type for config var in backend config file '%s', has to be dict" % backendConfigFile)
			exec(u'from %s import %sBackend' % (l['module'], l['module']))
			exec(u'self._backends[backend]["instance"] = %sBackend(**l["config"])' % l['module'])
			
	def __createInstanceMethods(self):
		for member in inspect.getmembers(DataBackend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public DataBackend method '%s'" % methodName)
			
			methodBackends = None
			for i in range(len(self._dispatchConfig)):
				(regex, backend) = self._dispatchConfig[i]
				if not re.search(regex, methodName):
					continue
				logger.debug(u"Matched '%s' for method '%s', using backend '%s'" % (regex, methodName, backend))
				if backend:
					methodBackends = backend
				break
			if not methodBackends:
				continue
			if not type(methodBackends) is list:
				methodBackends = [ methodBackends ]
			
			argString = u''
			callString = u''
			(args, varargs, varkwargs, argDefaults) = inspect.getargspec(member[1])
			print (args, varargs, varkwargs, argDefaults)
			for i in range(len(args)):
				if (args[i] == 'self'):
					continue
				if (argString):
					argString += u', '
					callString += u', '
				argString += args[i]
				callString += u'%s=%s' % (args[i], args[i])
				if type(argDefaults) is tuple and (len(argDefaults) + i >= len(args)):
					default = argDefaults[len(args)-len(argDefaults)-i]
					if type(default) is str:
						default = u"'%s'" % default
					elif type(default) is unicode:
						default = u"u'%s'" % default
					argString += u'=%s' % default
			if varargs:
				for vararg in varargs:
					argString += u', *%s' % vararg
					callString += u', *%s' % vararg
			if varkwargs:
				argString += u', **%s' % varkwargs
				callString += u', **%s' % varkwargs
			
			exec(u'def %s(self, %s): return self._executeMethod(%s, "%s", %s)' % (methodName, argString, methodBackends, methodName, callString))
			setattr(self.__class__, methodName, new.instancemethod(eval(methodName), self, self.__class__))
			
			for be in self._backends.keys():
				if not be in methodBackends:
					setattr(self._backends[be]['instance'].__class__, methodName, new.instancemethod(eval(methodName), self, self.__class__))
					
	
	def _executeMethod(self, methodBackends, methodName, **kwargs):
		logger.debug(u"Executing method '%s' on backends: %s" % (methodName, methodBackends))
		result = None
		for methodBackend in methodBackends:
			res = eval(u'self._backends[methodBackend]["instance"].%s(**kwargs)' % methodName)
			if type(result) is list and type(res) is list:
				result.extend(res)
			elif type(result) is dict and type(res) is dict:
				result.update(res)
			elif not res is None:
				result = res
		return result
		

class BackendExtender(DataBackend):
	def __init__(self, backend):
		


import os, re, codecs
if (os.name == 'posix'):
	import PAM, pwd, grp
elif (os.name == 'nt'):
	import win32security, win32net
from OPSI import Tools

class BackendAccessControl(DataBackend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		
		self._pamService = 'common-auth'
		self._userGroups = []
		self._host = None
		self._backend = None
		self._aclFile = None
		self._acl = [ ['.*', ['sys_group(opsiadmin)']] ]
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   (option == 'backend'):
				self._backend = value
			elif (option == 'acl'):
				self._acl = value
			elif (option == 'aclfile'):
				self._aclFile = value
			
		if not self._username:
			raise BackendAuthenticationError(u"No username specified")
		if not self._password:
			raise BackendAuthenticationError(u"No password specified")
		if not self._backend:
			raise BackendAuthenticationError(u"No backend specified")
		if isinstance(self._backend, BackendAccessControl):
			raise BackendBadValueError(u"Cannot use BackenAccessControl instance as backend")
			
		for i in range(len(self._acl)):
			self._acl[i][0] = re.compile(self._acl[i][0])
			self._acl[i][1] = forceUnicodeList(self._acl[i][1])
			
		try:
			if re.search('^[^\.]+\.[^\.]+\.\S+$', self._username):
				# Username starts with something like hostname.domain.tld:
				# Assuming it is a host passing his FQDN as username
				self._username = self._username.lower()
				
				logger.debug(u"Trying to authenticate by opsiHostKey...")
				
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
		
		self.__createInstanceMethods()
		if self._aclFile:
			self.__loadACLFile()
		
	def __loadACLFile(self):
		try:
			if not self._aclFile:
				raise Exception(u"No acl file defined")
			if not os.path.exists(self._aclFile):
				raise Exception(u"Acl file '%s' not found" % self._aclFile)
			self._acl = OpsiBackendACLFile(self._aclFile).parse()
			logger.debug(u"Read acl from file '%s':" % self._aclFile)
			logger.debug(Tools.objectToBeautifiedText(self._acl))
		except Exception, e:
			logger.error(u"Failed to load acl file '%s': %s" % (self._aclFile, e))
		
		
	def __createInstanceMethods(self):
		for member in inspect.getmembers(self._backend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public DataBackend method '%s'" % methodName)
			
			argString = u''
			callString = u''
			(args, varargs, varkwargs, argDefaults) = inspect.getargspec(member[1])
			print (args, varargs, varkwargs, argDefaults)
			for i in range(len(args)):
				if (args[i] == 'self'):
					continue
				if (argString):
					argString += u', '
					callString += u', '
				argString += args[i]
				callString += u'%s=%s' % (args[i], args[i])
				if type(argDefaults) is tuple and (len(argDefaults) + i >= len(args)):
					default = argDefaults[len(args)-len(argDefaults)-i]
					if type(default) is str:
						default = u"'%s'" % default
					elif type(default) is unicode:
						default = u"u'%s'" % default
					argString += u'=%s' % default
			if varargs:
				for vararg in varargs:
					argString += u', *%s' % vararg
					callString += u', *%s' % vararg
			if varkwargs:
				argString += u', **%s' % varkwargs
				callString += u', **%s' % varkwargs
			
			exec(u'def %s(self, %s): return self._executeMethod("%s", %s)' % (methodName, argString, methodName, callString))
			setattr(self.__class__, methodName, new.instancemethod(eval(methodName), self, self.__class__))
	
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
	
	def _executeMethod(self, methodName, **kwargs):
		granted = False
		for (regex, acl) in self._acl:
			if not re.search(regex, methodName):
				continue
			logger.debug(u"Using acl %s for method '%s'" % (acl, methodName))
			for entry in acl:
				if (entry == 'all'):
					granted = True
				elif (entry == 'opsi_depotserver'):
					granted = self.isOpsiDepotserver()
				elif entry.startswith('opsi_client'):
					if (entry.replace('opsi_client', '').replace('(', '').replace(')', '').strip() != ''):
						granted = self.isOpsiClient(**kwargs)
					else:
						granted = self.isOpsiClient()
				elif entry.startswith('sys_group'):
					granted = self.isMemberOfGroup(entry.replace('sys_group', '').replace('(', '').replace(')', '').strip())
				elif entry.startswith('sys_user'):
					granted = self.isUser(entry.replace('sys_user', '').replace('(', '').replace(')', '').strip())
				else:
					logger.error(u"Unhandled acl entry: %s" % entry)
					continue
				if granted:
					break
			if granted:
				logger.debug(u"Access to method '%s' granted to user '%s' by acl %s" % (methodName, self._username, acl))
				break
		if not granted:
			raise BackendPermissionDeniedError(u"Access to method '%s' denied for user '%s'" % (methodName, self._username))
		return eval(u'self._backend.%s(**kwargs)' % methodName)
	
	def isMemberOfGroup(self, group):
		group = forceUnicode(group)
		if group in self._userGroups:
			return True
		return False
	
	def isUser(self, user):
		user = forceUnicode(user)
		if (self._username == user):
			return True
		return False
		
	def isOpsiDepotserver(self):
		if self._host and isinstance(self._host, OpsiDepotserver):
			return True
		return False
	
	def isOpsiClient(self, **params):
		if not self._host or not isinstance(self._host, OpsiClient):
			return False
		if not params:
			return True
		for (param, value) in params.items():
			if type(value) is types.ClassType and issubclass(value, Host) and (value.id == self._username):
				return True
			if param in ('id', 'objectId', 'hostId') and (value == self._username):
				return True
		return False
		
		
		
		
		
		
		
		
		
		
		
		
		
		
