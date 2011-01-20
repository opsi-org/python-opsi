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

__version__ = '4.0.2'

# Imports
from Queue import Queue, Empty, Full
from urllib import urlencode
from httplib import HTTPConnection, HTTPSConnection, HTTPException, FakeSocket
from socket import error as SocketError, timeout as SocketTimeout
import socket, time
from sys import version_info
if (version_info >= (2,6)):
	import ssl as ssl_module
#try:
#	#import pycurl
#except:
#	pycurl = None
	
# OPSI imports
from OPSI.Types import *
from OPSI.Logger import *
logger = Logger()

connectionPools = {}
totalRequests = 0

def non_blocking_connect_http(self, connectTimeout=0):
	''' Non blocking connect, needed for KillableThread '''
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
	#sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
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
		self.sock = ssl_module.wrap_socket(self.sock, self.key_file, self.cert_file)
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
	
	def addData(self, data):
		self.data += data
	
	def curlHeader(self, header):
		header = header.strip()
		if header.upper().startswith('HTTP'):
			try:
				(version, status, reason) = header.split(None, 2)
				self.version = 9
				if (version == 'HTTP/1.0'):
					self.version = 10
				elif version.startswith('HTTP/1.'):
					self.version = 11
				self.status = int(status.strip())
				self.reason = reason.strip()
			except Exception, e:
				pass
		elif (header.count(':') > 0):
			(k, v) = header.split(':', 1)
			k = k.lower().strip()
			v = v.strip()
			if (k == 'content-length'):
				try:
					v = int(v)
					if (v < 0): v = 0
				except:
					return
			self.headers[k] = v
	
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
	
	def __init__(self, host, port, socketTimeout=None, connectTimeout=None, retryTime=0, maxsize=1, block=False, reuseConnection=False):
		self.host              = forceUnicode(host)
		self.port              = forceInt(port)
		self.socketTimeout     = forceInt(socketTimeout or 0)
		self.connectTimeout    = forceInt(connectTimeout or 0)
		self.retryTime         = forceInt(retryTime)
		self.block             = forceBool(block)
		self.reuseConnection   = forceBool(reuseConnection)
		self.pool              = None
		self.usageCount        = 1
		self.num_connections   = 0
		self.num_requests      = 0
		self.httplibDebugLevel = 0
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
							conn.sock.close()
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
		self.num_connections += 1
		logger.info(u"Starting new HTTP connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
		conn = HTTPConnection(host=self.host, port=self.port)
		non_blocking_connect_http(conn, self.connectTimeout)
		logger.info(u"Connection established to: %s" % self.host)
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
			if self.reuseConnection:
				self._put_conn(conn)
			else:
				self._put_conn(None)
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
		
		conn = None
		# Check host
		if assert_same_host and not self.is_same_host(url):
			host = "%s://%s" % (self.scheme, self.host)
			if self.port:
				host = "%s:%d" % (host, self.port)
			raise HostChangedError(u"Connection pool with host '%s' tried to open a foreign host: %s" % (host, url))
		
		try:
			# Request a connection from the queue
			conn = self._get_conn()
			
			if self.httplibDebugLevel:
				conn.set_debuglevel(self.httplibDebugLevel)
			
			# Make the request
			self.num_requests += 1
			
			global totalRequests
			totalRequests += 1
			#logger.essential("totalRequests: %d" % totalRequests)
			
			conn.request(method, url, body=body, headers=headers)
			if self.socketTimeout:
				conn.sock.settimeout(self.socketTimeout)
			else:
				conn.sock.settimeout(None)
			httplib_response = conn.getresponse()
			#logger.debug(u"\"%s %s %s\" %s %s" % (method, url, conn._http_vsn_str, httplib_response.status, httplib_response.length))
			
			# from_httplib will perform httplib_response.read() which will have
			# the side effect of letting us use this connection for another
			# request.
			response = HTTPResponse.from_httplib(httplib_response)
			
			# Put the connection back to be reused
			if self.reuseConnection:
				self._put_conn(conn)
			else:
				logger.debug(u"Closing connection: %s" % conn)
				self._put_conn(None)
				try:
					conn.sock.close()
					conn.close()
				except:
					pass
		
		except (SocketTimeout, Empty, HTTPException, SocketError), e:
			try:
				logger.debug(u"Request to host '%s' failed, retry: %s, firstTryTime: %s, now: %s, retryTime: %s, connectTimeout: %s, socketTimeout: %s (%s)" \
					% (self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.socketTimeout, forceUnicode(e)))
			except:
				try:
					logger.debug(u"Request to host '%s' failed, retry: %s, firstTryTime: %s, now: %s, retryTime: %s, connectTimeout: %s, socketTimeout: %s" \
						% (self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.socketTimeout))
				except:
					pass
			
			self._put_conn(None)
			try:
				if conn:
					conn.sock.close()
					conn.close()
			except:
				pass
			if retry and (now - firstTryTime < self.retryTime):
				logger.debug(u"Request to '%s' failed: %s, retrying" % (self.host, forceUnicode(e)))
				time.sleep(0.01)
				return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			else:
				raise
		except Exception:
			self._put_conn(None)
			try:
				if conn:
					conn.sock.close()
					conn.close()
			except:
				pass
			raise
			
		# Handle redirection
		if redirect and response.status in [301, 302, 303, 307] and 'location' in response.headers: # Redirect, retry
			logger.info(u"Redirecting %s -> %s" % (url, response.headers.get('location')))
			time.sleep(0.01)
			self._put_conn(None)
			try:
				if conn:
					conn.sock.close()
					conn.close()
			except:
				pass
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

class CurlHTTPConnectionPool(HTTPConnectionPool):
	
	scheme = 'http'
	
	def __init__(self, host, port, socketTimeout=None, connectTimeout=None, retryTime=0, maxsize=1, block=False, reuseConnection=True):
		if not pycurl:
			raise Exception(u"pycurl not available")
		HTTPConnectionPool.__init__(self, host, port, socketTimeout, connectTimeout, retryTime, maxsize, block, reuseConnection)
		
	def _new_conn(self):
		logger.info(u"Creating new curl HTTP connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
		conn = pycurl.Curl()
		self.num_connections += 1
		return conn
	
	def urlopen(self, method, url, body=None, headers={}, retry=True, redirect=True, assert_same_host=True, firstTryTime=None):
		now = time.time()
		if not firstTryTime:
			firstTryTime = now
		
		conn = None
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
			
			global totalRequests
			totalRequests += 1
			#logger.essential("totalRequests: %d" % totalRequests)
			
			response = HTTPResponse()
			conn.setopt(pycurl.SSL_VERIFYPEER, 0)
			conn.setopt(pycurl.SSL_VERIFYHOST, False)
			conn.setopt(pycurl.WRITEFUNCTION, response.addData)
			conn.setopt(pycurl.HEADERFUNCTION, response.curlHeader)
			conn.setopt(conn.URL, (u'%s://%s:%d%s' % (self.scheme, self.host, self.port, url)).encode('ascii', 'replace') )
			h = []
			for (k, v) in headers.items():
				h.append((u"%s: %s" % (k, v)).encode('ascii', 'replace'))
			conn.setopt(pycurl.HTTPHEADER, h)
			conn.setopt(pycurl.CONNECTTIMEOUT, self.connectTimeout or 0)
			conn.setopt(pycurl.TIMEOUT, self.socketTimeout or 0)
			#conn.setopt(pycurl.NOSIGNAL, 1)
			if redirect:
				conn.setopt(pycurl.FOLLOWLOCATION, 1)
				conn.setopt(pycurl.MAXREDIRS, 5)
			else:
				conn.setopt(pycurl.FOLLOWLOCATION, 0)
			if body:
				conn.setopt(pycurl.POSTFIELDS, body)
			conn.perform()
			
			# Put the connection back to be reused
			self._put_conn(None)
			try:
				conn.sock.close()
				conn.close()
			except:
				pass
		
		except Exception, e:
			logger.debug(u"Request to host '%s' failed, retry: %s, firstTryTime: %s, now: %s, retryTime: %s, connectTimeout: %s, socketTimeout: %s, (%s)" \
					% (self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.socketTimeout, e))
			self._put_conn(None)
			try:
				conn.sock.close()
				conn.close()
			except:
				pass
			if retry and (now - firstTryTime < self.retryTime):
				logger.debug(u"Request to '%s' failed: %s, retrying" % (self.host, e))
				time.sleep(0.01)
				return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			else:
				raise
		
		return response

class CurlHTTPSConnectionPool(CurlHTTPConnectionPool):
	
	scheme = 'https'
	
	def _new_conn(self):
		logger.info(u"Creating new curl HTTPS connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
		conn = pycurl.Curl()
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
		scheme = scheme.lower()
	parts = url.split('/', 1)
	host = parts[0]
	if (len(parts) > 1):
		baseurl += parts[1]
	if (host.find('@') != -1):
		(username, host) = host.split('@', 1)
		if (username.find(':') != -1):
			(username, password) = username.split(':', 1)
	if (host.find(':') != -1):
		(host, port) = host.split(':', 1)
		port = int(port)
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
	curl = False
	if kw.has_key('preferCurl'):
		if kw['preferCurl'] and pycurl:
			curl = True
		del kw['preferCurl']
	global connectionPools
	if curl:
		poolKey = u'curl:%s:%d' % (host, port)
	else:
		poolKey = u'httplib:%s:%d' % (host, port)
	if not connectionPools.has_key(poolKey):
		if scheme in ('https', 'webdavs'):
			if curl:
				connectionPools[poolKey] = CurlHTTPSConnectionPool(host, port=port, **kw)
			else:
				connectionPools[poolKey] = HTTPSConnectionPool(host, port=port, **kw)
		else:
			if curl:
				connectionPools[poolKey] = CurlHTTPConnectionPool(host, port=port, **kw)
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



	
if (__name__ == '__main__'):
	logger.setConsoleLevel(LOG_DEBUG2)
	logger.setConsoleColor(True)
	pool = HTTPSConnectionPool(host = 'download.uib.de', port = 443, connectTimeout=5)
	resp = pool.urlopen('GET', url = '/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	print resp.data
	time.sleep(5)
	#pool = CurlHTTPSConnectionPool(host = 'download.uib.de', port = 443, connectTimeout=5)
	#resp = pool.urlopen('GET', url = '/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	#print resp.data
	#pool = CurlHTTPConnectionPool(host = 'www.uib.de', port = 80, socketTimeout=None, connectTimeout=5, reuseConnection=True)
	#resp = pool.urlopen('GET', url = '/www/home/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	#print resp.headers
	#resp = pool.urlopen('GET', url = '/www/home/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	#print resp.data
	#print resp.headers
	#print resp.status
	#print resp.version
	#print resp.reason
	#print resp.strict
	


