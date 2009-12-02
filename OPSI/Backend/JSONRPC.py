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
import json, base64, urllib, httplib, new, stat, socket, time, threading

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from Backend import *
from OPSI import Object

# Get logger instance
logger = Logger()

METHOD_POST = 1
METHOD_GET = 2

def non_blocking_connect_http(self, connectTimeout=0):
	''' Non blocking connect, needed for KillableThread '''
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setblocking(0)
	started = time.time()
	while True:
		try:
			if (connectTimeout > 0) and ((time.time()-started) >= connectTimeout):
				raise socket.timeout(u"Timed out after %d seconds" % connectTimeout)
			sock.connect((self.host, self.port))
		except socket.error, e:
			if e[0] in (106, 10056):
				# Transport endpoint is already connected
				break
			if e[0] not in (114, 115, 10035):
				if sock:
					sock.close()
				raise
			time.sleep(0.1)
	sock.setblocking(1)
	self.sock = sock
	
def non_blocking_connect_https(self, connectTimeout=0):
	non_blocking_connect_http(self, connectTimeout)
	try:
		import ssl
		self.sock = ssl.wrap_socket(self.sock, self.key_file, self.cert_file)
	except ImportError, e:
		# python < 2.6
		ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
		self.sock = httplib.FakeSocket(self.sock, ssl)



# ======================================================================================================
# =                                   CLASS JSONRPCBACKEND                                             =
# ======================================================================================================
class JSONRPCBackend(Backend):
	
	def __init__(self, username = '', password = '', address = 'localhost', **kwargs):
		Backend.__init__(self, username, password, address, **kwargs)
		
		self.__address = address
		self.__username = username
		self.__password = password
		
		self.__sessionId = None
		
		# Default values
		self.__defaultHttpPort = 4444
		self.__defaultHttpsPort = 4447
		self.__protocol = u'https'
		self.__method = METHOD_POST
		self.__timeout = None
		self.__connectTimeout = 30
		self.__connectOnInit = True
		self.__interface = None
		self.__retry = True
		self.__rpcLock = threading.Lock()
		self.__application = 'opsi jsonrpc module version %s' % __version__
		
		if ( self.__address.find('/') == -1 and self.__address.find('=') == -1 ):
			if (self.__protocol == 'https'):
				self.__address = u'%s://%s:4447/rpc' % (self.__protocol, self.__address)
			else:
				self.__address = u'%s://%s:4444/rpc' % (self.__protocol, self.__address)
		
		socket.setdefaulttimeout(self.__timeout)
		if self.__connectOnInit:
			self._connect()
	
	def __del__(self):
		try:
			self.exit()
		except:
			pass
	
	def exit(self):
		self._jsonRPC('exit')
		self._disconnect()
	
	def _createInstanceMethods(self):
		for method in self.__interface:
			try:
				methodName = method['name']
				args       = method['args']
				varargs    = method['varargs']
				keywords   = method['keywords']
				defaults   = method['defaults']
				
				if (methodName == 'exit'):
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
				setattr(self,methodName, new.instancemethod(eval(methodName), self, self.__class__))
			except Exception, e:
				logger.critical(u"Failed to create instance method '%s': %s" % (method, e))
	
	def _disconnect(self):
		if self.__connection:
			self.__connection.close()
		
	def _connect(self):
		# Split address which should be something like http(s)://xxxxxxxxxx:yy/zzzzz
		parts = self.__address.split('/')
		if ( len(parts) < 3 or ( parts[0] != 'http:' and parts[0] != 'https:') ):
			raise BackendBadValueError(u"Bad address: '%s'" % self.__address)
		
		# Split port from host
		hostAndPort = parts[2].split(':')
		host = hostAndPort[0]
		port = self.__defaultHttpsPort
		if (parts[0][:-1] == 'http'):
			self.__protocol = 'http'
			port = self.__defaultHttpPort
		if ( len(hostAndPort) > 1 ):
			port = int(hostAndPort[1])
		self.__baseUrl = u'/' + u'/'.join(parts[3:])
		
		# Connect to host
		try:
			if (self.__protocol == 'https'):
				logger.info(u"Opening https connection to %s:%s" % (host, port))
				self.__connection = httplib.HTTPSConnection(host, port)
				non_blocking_connect_https(self.__connection, self.__connectTimeout)
			else:
				logger.info(u"Opening http connection to %s:%s" % (host, port))
				self.__connection = httplib.HTTPConnection(host, port)
				non_blocking_connect_http(self.__connection, self.__connectTimeout)
				
			self.__connection.connect()
			
			if not self.__interface:
				self.__retry = False
				try:
					self.__interface = self._jsonRPC(u'getInterface')
				finally:
					self.__retry = True
			self._createInstanceMethods()
			
			logger.info(u"Successfully connected to '%s:%s'" % (host, port))
		except Exception, e:
			logger.logException(e)
			raise BackendIOError(u"Failed to connect to '%s': %s" % (self.__address, e))
		
		
	
	def _jsonRPC(self, method, params=[]):
		
		logger.debug(u"Executing jsonrpc method '%s'" % method)
		self.__rpcLock.acquire()
		try:
			# Get params
			params = Object.serialize(params)
			
			# Create json-rpc object
			jsonrpc = ''
			if hasattr(json, 'dumps'):
				# python 2.6 json module
				jsonrpc = json.dumps( { "id": 1, "method": method, "params": params } )
			else:
				jsonrpc = json.write( { "id": 1, "method": method, "params": params } )
			logger.debug2(u"jsonrpc string: %s" % jsonrpc)
			
			logger.debug2(u"requesting: '%s', query '%s'" % (self.__address, jsonrpc))
			response = self.__request(self.__baseUrl, jsonrpc)
			
			# Read response
			if hasattr(json, 'loads'):
				# python 2.6 json module
				response = json.loads(response)
			else:
				response = json.read(response)
			
			if response.get('error'):
				# Error occurred
				raise Exception( u'on server: %s' % response.get('error') )
			
			# Return result as json object
			result = Object.deserialize(response.get('result'))
			return result
		finally:
			self.__rpcLock.release()
		
	def __request(self, baseUrl, query='', maxRetrySeconds=5, started=None):
		''' Do a http request '''
		
		now = time.time()
		if not started:
			started = now
		
		if type(query) is types.StringType:
			query = unicode(query, 'utf-8')
		query = query.encode('utf-8')
		
		response = None
		try:
			if (self.__method == METHOD_GET):
				# Request the resulting url
				logger.debug(u"Using method GET")
				get = baseUrl + '?' + urllib.quote(query)
				logger.debug(u"requesting: %s" % get)
				self.__connection.putrequest('GET', get)
			else:
				logger.debug(u"Using method POST")
				self.__connection.putrequest('POST', baseUrl)
				self.__connection.putheader('content-type', 'application/json-rpc')
				self.__connection.putheader('content-length', len(query))
			
			# Add some http headers
			self.__connection.putheader('user-agent', self.__application)
			self.__connection.putheader('Accept', 'application/json-rpc')
			self.__connection.putheader('Accept', 'text/plain')
			if self.__sessionId:
				# Add sessionId cookie to header
				self.__connection.putheader('Cookie', self.__sessionId)
			
			# Add basic authorization header
			auth = urllib.unquote(self.__username + ':' + self.__password)
			self.__connection.putheader('Authorization', 'Basic '+ base64.encodestring(auth).strip() )
			
			self.__connection.endheaders()
			if (self.__method == METHOD_POST):
				logger.debug2(u"Sending query")
				self.__connection.send(query)
			
			# Get response
			logger.debug2(u"Getting response")
			response = self.__connection.getresponse()
			
			# Get cookie from header
			cookie = response.getheader('Set-Cookie', None)
			if cookie:
				# Store sessionId cookie
				self.__sessionId = cookie.split(';')[0].strip()
		
		except Exception, e:
			logger.debug(u"Request to '%s' failed, retry: %s, started: %s, now: %s, maxRetrySeconds: %s" \
					% (self.__address, self.__retry, started, now, maxRetrySeconds))
			if self.__retry and (now - started < maxRetrySeconds):
				logger.warning(u"Request to '%s' failed: %s, trying to reconnect" % (self.__address, e))
				self._connect()
				return self.__request(baseUrl, query=query, maxRetrySeconds=maxRetrySeconds, started=started)
			else:
				logger.logException(e)
				raise BackendIOError(u"Request to '%s' failed: %s" % (self.__address, e))
		
		try:
			# Return response content (body)
			return response.read()
		except Exception, e:
			raise BackendIOError(u"Cannot read '%s'" % e)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

