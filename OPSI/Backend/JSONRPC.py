#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - JSONRPC   =
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

__version__ = '4.0'

# Imports
import base64, urllib, httplib, new, stat, socket, time, threading, zlib
from twisted.conch.ssh import keys

from sys import version_info
if (version_info >= (2,6)):
	import json
else:
	import simplejson as json

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from Backend import *
from OPSI import Object
from OPSI.Util import non_blocking_connect_http, non_blocking_connect_https, serialize, deserialize

# Get logger instance
logger = Logger()

METHOD_POST = 1
METHOD_GET = 2


# ======================================================================================================
# =                                   CLASS JSONRPCBACKEND                                             =
# ======================================================================================================
class JSONRPCBackend(Backend):
	
	def __init__(self, **kwargs):
		self._name = 'jsonrpc'
		
		Backend.__init__(self, **kwargs)
		
		self._application = 'opsi jsonrpc module version %s' % __version__
		self._sessionId   = None
		self._deflate     = False
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('address',):
				self._address = value
			if option in ('application',):
				self._application = str(value)
			if option in ('sessionid',):
				self._sessionId = str(value)
			if option in ('deflate',):
				self._deflate = bool(value)
		
		# Default values
		self._defaultHttpPort = 4444
		self._defaultHttpsPort = 4447
		self._protocol = u'https'
		self._method = METHOD_POST
		self._timeout = None
		self._connectTimeout = 20
		self._connectOnInit = True
		self._connected = False
		self._interface = None
		self._retry = True
		self._rpcLock = threading.Lock()
		self._backendOptions = {}
		self._legacyOpsi = False
		
		if ( self._address.find('/') == -1 and self._address.find('=') == -1 ):
			if (self._protocol == 'https'):
				self._address = u'%s://%s:4447/rpc' % (self._protocol, self._address)
			else:
				self._address = u'%s://%s:4444/rpc' % (self._protocol, self._address)
		
		socket.setdefaulttimeout(self._timeout)
		if self._connectOnInit:
			self._connect()
	
	def isOpsi35(self):
		return not self._legacyOpsi
	
	def isOpsi4(self):
		return not self._legacyOpsi
	
	def isLegacyOpsi(self):
		return self._legacyOpsi
	
	def jsonrpc_getSessionId(self):
		return self._sessionId
		
	def backend_exit(self):
		if self._connected:
			if self._legacyOpsi:
				self._jsonRPC('exit')
			else:
				self._jsonRPC('backend_exit')
			self._disconnect()
	
	def backend_setOptions(self, options):
		self._backendOptions = options
		if self._connected:
			self._jsonRPC('backend_setOptions', [ self._backendOptions ])
	
	def _createInstanceMethods34(self):
		for method in self._interface:
			# Create instance method
			params = ['self']
			params.extend( method.get('params', []) )
			paramsWithDefaults = list(params)
			for i in range(len(params)):
				if params[i].startswith('*'):
					params[i] = params[i][1:]
					paramsWithDefaults[i] = params[i] + '="__UNDEF__"'
			
			logger.debug2("Creating instance method '%s'" % method['name'])
			
			
			if (len(params) == 2):
				logger.debug2('def %s(%s):\n  if type(%s) == list: %s = [ %s ]\n  return self._jsonRPC(method = "%s", params = [%s])'\
					% (method['name'], ', '.join(paramsWithDefaults), params[1], params[1], params[1], method['name'], ', '.join(params[1:])) )
				exec 'def %s(%s):\n  if type(%s) == list: %s = [ %s ]\n  return self._jsonRPC(method = "%s", params = [%s])'\
					% (method['name'], ', '.join(paramsWithDefaults), params[1], params[1], params[1], method['name'], ', '.join(params[1:]))
			else:
				logger.debug2('def %s(%s): return self._jsonRPC(method = "%s", params = [%s])'\
					% (method['name'], ', '.join(paramsWithDefaults), method['name'], ', '.join(params[1:])) )
				exec 'def %s(%s): return self._jsonRPC(method = "%s", params = [%s])'\
					% (method['name'], ', '.join(paramsWithDefaults), method['name'], ', '.join(params[1:]))
			
			setattr(self.__class__, method['name'], new.instancemethod(eval(method['name']), None, self.__class__))
		
	def _createInstanceMethods(self, modules=None, mysqlBackend=False):
		licenseManagementModule = True
		if modules:
			licenseManagementModule = False
			if not modules.get('customer'):
				logger.notice(u"Disabling mysql backend and license management module: no customer in modules file")
				if mysqlBackend:
					raise Exception(u"MySQL backend in use but not licensed")
				
			elif not modules.get('valid'):
				logger.notice(u"Disabling mysql backend and license management module: modules file invalid")
				if mysqlBackend:
					raise Exception(u"MySQL backend in use but not licensed")
				
			elif (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
				logger.notice(u"Disabling mysql backend and license management module: modules file expired")
				if mysqlBackend:
					raise Exception(u"MySQL backend in use but not licensed")
			else:
				logger.info(u"Verifying modules file signature")
				publicKey = keys.Key.fromString(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
				data = u''
				mks = modules.keys()
				mks.sort()
				for module in mks:
					if module in ('valid', 'signature'):
						continue
					val = modules[module]
					if (val == False): val = 'no'
					if (val == True):  val = 'yes'
					data += u'%s = %s\r\n' % (module.lower().strip(), val)
				if not bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ])):
					logger.error(u"Disabling mysql backend and license management module: modules file invalid")
					if mysqlBackend:
						raise Exception(u"MySQL backend in use but not licensed")
				else:
					logger.notice(u"Modules file signature verified (customer: %s)" % modules.get('customer'))
					
					if modules.get('license_management'):
						licenseManagementModule = True
					
					if mysqlBackend and not modules.get('mysql_backend'):
						raise Exception(u"MySQL backend in use but not licensed")
					
		
		for method in self._interface:
			try:
				methodName = method['name']
				args       = method['args']
				varargs    = method['varargs']
				keywords   = method['keywords']
				defaults   = method['defaults']
				
				if methodName in ('backend_setOptions', 'backend_exit'):
					continue
				
				argString = u''
				callString = u''
				for i in range(len(args)):
					if (args[i] == 'self'):
						continue
					if (argString):	 argString  += u', '
					if (callString): callString += u', '
					argString  += args[i]
					callString += args[i]
					if type(defaults) in (tuple, list) and (len(defaults) + i >= len(args)):
						default = defaults[len(defaults)-len(args)+i]
						if type(default) is str:
							default = u"'%s'" % default
						elif type(default) is unicode:
							default = u"u'%s'" % default
						argString += u'=%s' % unicode(default)
				if varargs:
					for vararg in varargs:
						if (argString):	 argString  += u', '
						if (callString): callString += u', '
						argString  += u'*%s' % vararg
						callString += vararg
				if keywords:
					if (argString):	 argString  += u', '
					if (callString): callString += u', '
					argString  += u'**%s' % keywords
					callString += keywords
					
				logger.debug2(u"Arg string is: %s" % argString)
				logger.debug2(u"Call string is: %s" % callString)
				
				if not licenseManagementModule and (methodName.find("license") != -1):
					exec(u'def %s(self, %s): return' % (methodName, argString))
				else:
					exec(u'def %s(self, %s): return self._jsonRPC("%s", [%s])' % (methodName, argString, methodName, callString))
				setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
			except Exception, e:
				logger.critical(u"Failed to create instance method '%s': %s" % (method, e))
	
	def _disconnect(self):
		if self._connection:
			self._connection.close()
		self._connected = False
		
	def _connect(self):
		# Split address which should be something like http(s)://xxxxxxxxxx:yy/zzzzz
		parts = self._address.split('/')
		if ( len(parts) < 3 or ( parts[0] != 'http:' and parts[0] != 'https:') ):
			raise BackendBadValueError(u"Bad address: '%s'" % self._address)
		
		# Split port from host
		hostAndPort = parts[2].split(':')
		host = hostAndPort[0]
		port = self._defaultHttpsPort
		if (parts[0][:-1] == 'http'):
			self._protocol = 'http'
			port = self._defaultHttpPort
		if ( len(hostAndPort) > 1 ):
			port = int(hostAndPort[1])
		self._baseUrl = u'/' + u'/'.join(parts[3:])
		
		# Connect to host
		try:
			if (self._protocol == 'https'):
				logger.info(u"Opening https connection to %s:%s" % (host, port))
				self._connection = httplib.HTTPSConnection(host, port)
				non_blocking_connect_https(self._connection, self._connectTimeout)
			else:
				logger.info(u"Opening http connection to %s:%s" % (host, port))
				self._connection = httplib.HTTPConnection(host, port)
				non_blocking_connect_http(self._connection, self._connectTimeout)
				
			self._connection.connect()
			
			modules = None
			mysqlBackend = False
			if not self._interface:
				self._retry = False
				try:
					try:
						self._interface = self._jsonRPC(u'backend_getInterface')
						try:
							modules = self._jsonRPC(u'getOpsiInformation_hash')['modules']
							logger.confidential(u"Modules: %s" % modules)
							if not modules:
								modules = {'customer': None}
							for entry in self._jsonRPC(u'dispatcher_getConfig'):
								for bn in entry[1]:
									if (bn.lower().find("sql") != -1) and (len(entry[0]) <= 4) and (entry[0].find('*') != -1):
										mysqlBackend = True
						except Exception, e:
							logger.info(e)
					except Exception, e:
						logger.debug(u"backend_getInterface failed: %s, trying getPossibleMethods_listOfHashes" % e)
						self._interface = self._jsonRPC(u'getPossibleMethods_listOfHashes')
						logger.info(u"Legacy opsi")
						self._legacyOpsi = True
						self._deflate = False
				finally:
					self._retry = True
			
			if self._legacyOpsi:
				self._createInstanceMethods34()
			else:
				self._createInstanceMethods(modules, mysqlBackend)
			
			logger.info(u"Successfully connected to '%s:%s'" % (host, port))
			self._connected = True
			
			if self._backendOptions:
				self._rpcLock.release()
				try:
					self.backend_setOptions(self._backendOptions)
				finally:
					self._rpcLock.acquire()
		except Exception, e:
			logger.logException(e)
			raise BackendIOError(u"Failed to connect to '%s': %s" % (self._address, e))
	
	def _jsonRPC(self, method, params=[]):
		if self._legacyOpsi:
			for i in range(len(params)):
				if (params[i] == '__UNDEF__'):
					params[i] = None
		
		logger.debug(u"Executing jsonrpc method '%s'" % method)
		self._rpcLock.acquire()
		try:
			# Get params
			params = serialize(params)
			
			# Create json-rpc object
			jsonrpc = json.dumps( { "id": 1, "method": method, "params": params } )
			logger.debug2(u"jsonrpc string: %s" % jsonrpc)
			
			logger.debug2(u"requesting: '%s', query '%s'" % (self._address, jsonrpc))
			response = self._request(self._baseUrl, jsonrpc)
			
			# Read response
			response = json.loads(response)
			
			if response.get('error'):
				# Error occurred
				raise Exception(u'Error on server: %s' % response.get('error'))
			
			# Return result python object
			result = deserialize(response.get('result'))
			return result
		finally:
			self._rpcLock.release()
		
	def _request(self, baseUrl, query='', maxRetrySeconds=5, started=None):
		''' Do a http request '''
		now = time.time()
		if not started:
			started = now
		
		if type(query) is types.StringType:
			query = unicode(query, 'utf-8')
		query = query.encode('utf-8')
		
		response = None
		try:
			if (self._method == METHOD_GET):
				# Request the resulting url
				logger.debug(u"Using method GET")
				get = baseUrl + '?' + urllib.quote(query)
				logger.debug(u"requesting: %s" % get)
				self._connection.putrequest('GET', get)
			else:
				logger.debug(u"Using method POST")
				self._connection.putrequest('POST', baseUrl)
				if self._deflate:
					logger.debug2(u"Compressing query")
					self._connection.putheader('content-type', 'gzip-application/json-rpc')
					level = 1
					query = zlib.compress(query, level)
				else:
					self._connection.putheader('content-type', 'application/json-rpc')
				self._connection.putheader('content-length', len(query))
			
			# Add some http headers
			self._connection.putheader('user-agent', self._application)
			if self._deflate:
				self._connection.putheader('Accept', 'gzip-application/json-rpc')
			self._connection.putheader('Accept', 'application/json-rpc')
			self._connection.putheader('Accept', 'text/plain')
			if self._sessionId:
				# Add sessionId cookie to header
				self._connection.putheader('Cookie', self._sessionId)
			
			# Add basic authorization header
			#auth = urllib.unquote(self._username + ':' + self._password)
			auth = u'%s:%s' % (self._username, self._password)
			self._connection.putheader('Authorization', 'Basic '+ base64.encodestring(auth.encode('latin-1')).strip())
			
			self._connection.endheaders()
			if (self._method == METHOD_POST):
				logger.debug2(u"Sending query")
				self._connection.send(query)
				
			# Get response
			logger.debug2(u"Getting response")
			response = self._connection.getresponse()
			
			# Get cookie from header
			cookie = response.getheader('Set-Cookie', None)
			if cookie:
				# Store sessionId cookie
				self._sessionId = cookie.split(';')[0].strip()
			
		except Exception, e:
			logger.debug(u"Request to '%s' failed, retry: %s, started: %s, now: %s, maxRetrySeconds: %s" \
					% (self._address, self._retry, started, now, maxRetrySeconds))
			if self._retry and (now - started < maxRetrySeconds):
				logger.debug(u"Request to '%s' failed: %s, trying to reconnect" % (self._address, e))
				self._connect()
				return self._request(baseUrl, query=query, maxRetrySeconds=maxRetrySeconds, started=started)
			else:
				logger.logException(e)
				raise BackendIOError(u"Request to '%s' failed: %s" % (self._address, e))
		
		try:
			logger.debug(u"Content-Type: %s" % response.getheader('content-type', None))
			if response.getheader('content-type', '').lower().startswith('gzip'):
				logger.debug(u"Expecting compressed data from server")
				res = zlib.decompress(response.read())
				logger.debug2(res)
				return res
			else:
				res = response.read()
				logger.debug2(res)
				return res
			
		except Exception, e:
			raise BackendIOError(u"Cannot read '%s'" % e)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

