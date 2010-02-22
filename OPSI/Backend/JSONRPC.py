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

__version__ = '3.5'

# Imports
import base64, urllib, httplib, new, stat, socket, time, threading

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
from OPSI.Util import non_blocking_connect_http, non_blocking_connect_https

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
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('address',):
				self._address = value
			if option in ('application',):
				self._application = str(value)
			if option in ('sessionid',):
				self._sessionId = str(value)
		
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
		
	def _createInstanceMethods(self):
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
			
			if not self._interface:
				self._retry = False
				try:
					try:
						self._interface = self._jsonRPC(u'backend_getInterface')
					except Exception, e:
						logger.debug("backend_getInterface failed: %s, trying getPossibleMethods_listOfHashes" % e)
						self._interface = self._jsonRPC(u'getPossibleMethods_listOfHashes')
						logger.info(u"Legacy opsi")
						self._legacyOpsi = True
				finally:
					self._retry = True
			
			if self._legacyOpsi:
				self._createInstanceMethods34()
			else:
				self._createInstanceMethods()
			
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
		
		logger.debug(u"Executing jsonrpc method '%s'" % method)
		self._rpcLock.acquire()
		try:
			# Get params
			params = Object.serialize(params)
			
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
			
			# Return result as json object
			result = Object.deserialize(response.get('result'))
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
				self._connection.putheader('content-type', 'application/json-rpc')
				self._connection.putheader('content-length', len(query))
			
			# Add some http headers
			self._connection.putheader('user-agent', self._application)
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
			# Return response content (body)
			return response.read()
		except Exception, e:
			raise BackendIOError(u"Cannot read '%s'" % e)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

