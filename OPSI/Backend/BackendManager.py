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
from Backend import *

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                  CLASS BACKENDMANAGER                                              =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''

class BackendManager(DataBackend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		
		self._backendConfig = { '.*': ['MySQL'] }
		self._backends = {}
		self._compositionConfigDir = '/etc/opsi/backendManager/compose.d'
		
		for (option, value) in kwargs.items():
			if (option.lower() == 'backendconfig'):
				self._backendConfig = value
			if (option.lower() == 'compositionconfigdir'):
				self._compositionConfigDir = value
			
		self.__loadBackends()
		self.__createInstanceMethods()
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
	
	def __loadBackends(self):
		backends = []
		for value in self._backendConfig.values():
			if not type(value) is list:
				value = [ value ]
			for value in value:
				if value in backends:
					continue
				backends.append(value)
		for backend in backends:
			self._backends[backend] = {}
			exec(u'from %s import %sBackend' % (backend, backend))
			exec(u'self._backends[backend]["instance"] = %sBackend(username = "opsi", password = "opsi", args = {"database": "opsi"})' % backend)
		
	def __createInstanceMethods(self):
		for member in inspect.getmembers(DataBackend, inspect.ismethod):
			methodName = member[0]
			if methodName.startswith('_'):
				# Not a public method
				continue
			logger.debug2(u"Found public DataBackend method '%s'" % methodName)
			
			methodBackends = None
			for (regex, backend) in self._backendConfig.items():
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
	
	def _executeMethod(self, methodBackends, methodName, **kwargs):
		logger.debug(u"Executing method '%s' on backends: %s" % (methodName, methodBackends))
		result = None
		for methodBackend in methodBackends:
			res = eval(u'self._backends[methodBackend]["instance"].%s(**kwargs)' % methodName)
			if type(result) is list and type(res) is list:
				result.extend(res)
			elif type(result) is dict and type(res) is dict:
				result.update(res)
			else:
				result = res
		return result
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
