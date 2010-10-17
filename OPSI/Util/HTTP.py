#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - HTTP    =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   Based on urllib3
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 Andrey Petrov
   Copyright (C) 2010 uib GmbH
   
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

__version__ = '4.0.1'

# Imports
from Queue import Queue, Empty, Full
from urllib import urlencode
from httplib import HTTPConnection, HTTPSConnection, HTTPException, FakeSocket
from socket import error as SocketError, timeout as SocketTimeout
import socket, time
from sys import version_info

# OPSI imports
from OPSI.Types import *
from OPSI.Logger import *
logger = Logger()

connectionPools = {}

def non_blocking_connect_http(self, connectTimeout=0):
	''' Non blocking connect, needed for KillableThread '''
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(3.0)
	started = time.time()
	lastError = None
	while True:
		try:
			if (connectTimeout > 0) and ((time.time()-started) >= connectTimeout):
				raise OpsiTimeoutError(u"Timed out after %d seconds (%s)" % (connectTimeout, forceUnicode(lastError)))
			sock.connect((self.host, self.port))
			break
		except socket.error, e:
			logger.debug(e)
			if e[0] in (106, 10056):
				# Transport endpoint is already connected
				break
			if e[0] not in (114, ) or not lastError:
				lastError = e
			time.sleep(0.5)
	sock.settimeout(None)
	self.sock = sock
	
def non_blocking_connect_https(self, connectTimeout=0):
	non_blocking_connect_http(self, connectTimeout)
	if (version_info >= (2,6)):
		import ssl
		self.sock = ssl.wrap_socket(self.sock, self.key_file, self.cert_file)
	else:
		ssl = socket.ssl(self.sock, self.key_file, self.cert_file)
		self.sock = FakeSocket(self.sock, ssl)


class HTTPError(Exception):
	"Base exception used by this module."
	pass

class TimeoutError(HTTPError):
	"Raised when a socket timeout occurs."
	pass

class HostChangedError(HTTPError):
	"Raised when an existing pool gets a request for a foreign host."
	pass

class HTTPResponse(object):
	"""
	HTTP Response container.
	
	Similar to httplib's HTTPResponse but the data is pre-loaded.
	"""
	def __init__(self, data='', headers={}, status=0, version=0, reason=None, strict=0):
		self.data    = data
		self.headers = headers
		self.status  = status
		self.version = version
		self.reason  = reason
		self.strict  = strict
	
	@staticmethod
	def from_httplib(r):
		"""
		Given an httplib.HTTPResponse instance, return a corresponding
		urllib3.HTTPResponse object.
		
		NOTE: This method will perform r.read() which will have side effects
		on the original http.HTTPResponse object.
		"""
		return HTTPResponse(
			data    = r.read(),
			headers = dict(r.getheaders()),
			status  = r.status,
			version = r.version,
			reason  = r.reason,
			strict  = r.strict)
	
	# Backwards-compatibility methods for httplib.HTTPResponse
	def getheaders(self):
		return self.headers
	
	def getheader(self, name, default=None):
		return self.headers.get(name, default)

class HTTPConnectionPool(object):
	
	scheme = 'http'
	
	def __init__(self, host, port, socketTimeout=None, connectTimeout=None, retryTime=0, maxsize=1, block=False):
		self.host            = forceUnicode(host)
		self.port            = forceInt(port)
		self.socketTimeout   = forceInt(socketTimeout)
		self.connectTimeout  = forceInt(connectTimeout)
		self.retryTime       = forceInt(retryTime)
		self.block           = forceBool(block)
		self.pool            = None
		self.usageCount      = 1
		self.num_connections = 0
		self.num_requests    = 0
		self.adjustSize(maxsize)
	
	def increaseUsageCount(self):
		self.usageCount += 1
	
	def decreaseUsageCount(self):
		self.usageCount -= 1
		if (self.usageCount == 0):
			destroyPool(self)
	
	free = decreaseUsageCount
	
	def delPool(self):
		if self.pool:
			while True:
				try:
					conn = self.pool.get(block = False)
					if conn:
						try:
							conn.close()
						except:
							pass
					time.sleep(0.001)
				except Empty, e:
					break
		
	def adjustSize(self, maxsize):
		if (maxsize < 1):
			raise Exception(u"Connection pool size %d is invalid" % maxsize)
		self.maxsize = forceInt(maxsize)
		self.delPool()
		self.pool = Queue(self.maxsize)
		# Fill the queue up so that doing get() on it will block properly
		[self.pool.put(None) for i in xrange(self.maxsize)]
		
	def __del__(self):
		self.delPool()
	
	def _new_conn(self):
		"""
		Return a fresh HTTPConnection.
		"""
		logger.info(u"Starting new HTTP connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
		conn = HTTPSConnection(host=self.host, port=self.port)
		non_blocking_connect_http(conn, self.connectTimeout)
		logger.info(u"Connection established to: %s" % self.host)
		self.num_connections += 1
		return conn

	def _get_conn(self, timeout=None):
		"""
		Get a connection. Will return a pooled connection if one is available.
		Otherwise, a fresh connection is returned.
		"""
		conn = None
		try:
			conn = self.pool.get(block=self.block, timeout=timeout)
		except Empty, e:
			pass # Oh well, we'll create a new connection then
		
		return conn or self._new_conn()

	def _put_conn(self, conn):
		"""
		Put a connection back into the pool.
		If the pool is already full, the connection is discarded because we
		exceeded maxsize. If connections are discarded frequently, then maxsize
		should be increased.
		"""
		try:
			self.pool.put(conn, block=False)
			if conn is None:
				self.num_connections -= 1
		except Full, e:
			# This should never happen if self.block == True
			logger.warning(u"HttpConnectionPool is full, discarding connection: %s" % self.host)
		
	def is_same_host(self, url):
		return url.startswith('/') or get_host(url) == (self.scheme, self.host, self.port)
	
	def getConnection(self):
		conn = self._get_conn()
		conn.sock.settimeout(self.socketTimeout)
		return conn
	
	def getConnection(self):
		return self._get_conn()
	
	def endConnection(self, conn):
		if conn:
			httplib_response = conn.getresponse()
			response = HTTPResponse.from_httplib(httplib_response)
			self._put_conn(conn)
			return response
		self._put_conn(None)
		return None
	
	def urlopen(self, method, url, body=None, headers={}, retry=True, redirect=True, assert_same_host=True, firstTryTime=None):
		"""
		Get a connection from the pool and perform an HTTP request.
		
		method
			HTTP request method (such as GET, POST, PUT, etc.)
		
		body
			Data to send in the request body (useful for creating POST requests,
			see HTTPConnectionPool.post_url for more convenience).
		
		headers
			Custom headers to send (such as User-Agent, If-None-Match, etc.)
		
		retry
			Retry on connection failure in between self.retryTime seconds
		
		redirect
			Automatically handle redirects (status codes 301, 302, 303, 307),
			each redirect counts as a retry.
		"""
		now = time.time()
		if not firstTryTime:
			firstTryTime = now
		
		# Check host
		if assert_same_host and not self.is_same_host(url):
			host = "%s://%s" % (self.scheme, self.host)
			if self.port:
				host = "%s:%d" % (host, self.port)
			raise HostChangedError("Connection pool with host '%s' tried to open a foreign host: %s" % (host, url))
		
		try:
			# Request a connection from the queue
			conn = self._get_conn()
			
			# Make the request
			self.num_requests += 1
			conn.request(method, url, body=body, headers=headers)
			conn.sock.settimeout(self.socketTimeout)
			httplib_response = conn.getresponse()
			#logger.debug(u"\"%s %s %s\" %s %s" % (method, url, conn._http_vsn_str, httplib_response.status, httplib_response.length))
			
			# from_httplib will perform httplib_response.read() which will have
			# the side effect of letting us use this connection for another
			# request.
			response = HTTPResponse.from_httplib(httplib_response)
			
			# Put the connection back to be reused
			self._put_conn(conn)
			

		except (SocketTimeout, Empty), e:
			# Timed out either by socket or queue
			raise TimeoutError(u"Request timed out after %f seconds" % self.socketTimeout)
		
		except (HTTPException, SocketError), e:
			logger.debug(u"Request to host '%s' failed, retry: %s, firstTryTime: %s, now: %s, retryTime: %s (%s)" \
					% (self.host, retry, firstTryTime, now, self.retryTime, e))
			if retry and (now - firstTryTime < self.retryTime):
				logger.debug(u"Request to '%s' failed: %s, retrying" % (self.host, e))
				time.sleep(0.01)
				self._put_conn(None)
				return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			else:
				raise
		except Exception:
			self._put_conn(None)
			raise
			
		# Handle redirection
		if redirect and response.status in [301, 302, 303, 307] and 'location' in response.headers: # Redirect, retry
			logger.info(u"Redirecting %s -> %s" % (url, response.headers.get('location')))
			time.sleep(0.01)
			self._put_conn(None)
			return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			
		return response
	
class HTTPSConnectionPool(HTTPConnectionPool):
	"""
	Same as HTTPConnectionPool, but HTTPS.
	"""
	
	scheme = 'https'
	
	def _new_conn(self):
		"""
		Return a fresh HTTPSConnection.
		"""
		logger.info(u"Starting new HTTPS connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
		conn = HTTPSConnection(host=self.host, port=self.port)
		non_blocking_connect_https(conn, self.connectTimeout)
		logger.info(u"Connection established to: %s" % self.host)
		self.num_connections += 1
		return conn

def urlsplit(url):
	url = forceUnicode(url)
	scheme = None
	baseurl = u'/'
	port = None
	username = None
	password = None
	if (url.find('://') != -1):
		(scheme, url) = url.split('://', 1)
		sceme = scheme.lower()
	parts = url.split('/', 1)
	host = parts[0]
	if (len(parts) > 1):
		baseurl += parts[1]
	if (host.find(':') != -1):
		(host, port) = host.split(':', 1)
		port = int(port)
	if (host.find('@') != -1):
		(username, host) = host.split('@', 1)
		if (username.find(':') != -1):
			(username, password) = username.split(':', 1)
	return (scheme, host, port, baseurl, username, password)
	
def getSharedConnectionPoolFromUrl(url, **kw):
	"""
	Given a url, return an HTTP(S)ConnectionPool instance of its host.
	
	This is a shortcut for not having to determine the host of the url
	before creating an HTTP(S)ConnectionPool instance.
	
	Passes on whatever kw arguments to the constructor of
	HTTP(S)ConnectionPool. (e.g. timeout, maxsize, block)
	"""
	(scheme, host, port, baseurl, username, password) = urlsplit(url)
	if not port:
		if scheme in ('https', 'webdavs'):
			port = 443
		else:
			port = 80
	return getSharedConnectionPool(scheme, host, port, **kw)
	
def getSharedConnectionPool(scheme, host, port, **kw):
	scheme = forceUnicodeLower(scheme)
	host = forceUnicode(host)
	port = forceInt(port)
	global connectionPools
	poolKey = u'%s:%d' % (host, port)
	if not connectionPools.has_key(poolKey):
		if scheme in ('https', 'webdavs'):
			connectionPools[poolKey] = HTTPSConnectionPool(host, port=port, **kw)
		else:
			connectionPools[poolKey] = HTTPConnectionPool(host, port=port, **kw)
	else:
		connectionPools[poolKey].increaseUsageCount()
		maxsize = kw.get('maxsize', 0)
		if (maxsize > connectionPools[poolKey].maxsize):
			connectionPools[poolKey].adjustSize(maxsize)
	return connectionPools[poolKey]

def destroyPool(pool):
	global connectionPools
	for (k, p) in connectionPools.items():
		if (p == pool):
			del connectionPools[k]
			break






