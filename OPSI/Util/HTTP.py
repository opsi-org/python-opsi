# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# Based on urllib3
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2010 Andrey Petrov
# Copyright (C) 2010-2019 uib GmbH <info@uib.de>

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
opsi python library - HTTP


.. versionadded:: 4.0.6.9

	Added functions :py:func:`deflateEncode`, :py:func:`deflateDecode`,
	:py:func:`gzipEncode` and :py:func:`gzipDecode`.


:license: GNU Affero General Public License version 3
"""

import base64
import gzip
import ssl as ssl_module
import socket
import time
import zlib
import collections
from contextlib import contextmanager
from functools import lru_cache
from queue import Queue, Empty, Full
from http.client import HTTPConnection, HTTPSConnection, HTTPException
from socket import error as SocketError, timeout as SocketTimeout
from urllib.parse import urlparse

from OpenSSL import crypto

from OPSI.Exceptions import OpsiTimeoutError, OpsiServiceVerificationError
from OPSI.Types import (
	forceBool, forceFilename, forceInt, forceUnicode, forceUnicodeLower
)
from OPSI.Logger import Logger

logger = Logger()

connectionPools = {}
totalRequests = 0  # pylint: disable=invalid-name


def non_blocking_connect_http(self, connectTimeout=0):
	''' Non blocking connect, needed for KillableThread '''
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(3.0)
	started = time.time()
	lastError = None
	while True:
		try:
			if time.time() - started >= connectTimeout > 0:
				raise OpsiTimeoutError(f"Timed out after {connectTimeout} seconds (last error: {lastError})")
			sock.connect((self.host, self.port))
			break
		except socket.error as error:
			logger.debug(error, exc_info=True)
			if error.args[0] in (106, 10056):
				# Transport endpoint is already connected
				break

			if error.args[0] not in (114, ) or not lastError:
				lastError = error
			time.sleep(0.5)
	sock.settimeout(None)
	self.sock = sock


def non_blocking_connect_https(self, connectTimeout=0, verifyByCaCertsFile=None):
	non_blocking_connect_http(self, connectTimeout)
	logger.debug2("verifyByCaCertsFile is: '%s'", verifyByCaCertsFile)
	if verifyByCaCertsFile:
		self.sock = ssl_module.wrap_socket(
			self.sock, keyfile=self.key_file, certfile=self.cert_file,
			cert_reqs=ssl_module.CERT_REQUIRED, ca_certs=verifyByCaCertsFile
		)
	else:
		self.sock = ssl_module.wrap_socket(
			self.sock, keyfile=self.key_file, certfile=self.cert_file, cert_reqs=ssl_module.CERT_NONE
		)


def getPeerCertificate(httpsConnectionOrSSLSocket, asPEM=True):
	logger.debug2("Trying to get peer cert from %s", httpsConnectionOrSSLSocket)
	sock = httpsConnectionOrSSLSocket
	if hasattr(sock, "sock"):
		sock = sock.sock
	try:
		if not sock:
			raise RuntimeError("Socket not initialized")
		cert = crypto.load_certificate(crypto.FILETYPE_ASN1, sock.getpeercert(binary_form=True))
		if not asPEM:
			return cert
		return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
	except Exception as error:  # pylint: disable=broad-except
		logger.warning("Failed to get peer cert: %s", error)
		return None


class HTTPError(Exception):
	"Base exception used by this module."


class TimeoutError(HTTPError):  # pylint: disable=redefined-builtin
	"Raised when a socket timeout occurs."


class HostChangedError(HTTPError):
	"Raised when an existing pool gets a request for a foreign host."


class HTTPResponse:
	"""
	HTTP Response container.

	Similar to httplib's HTTPResponse but the data is pre-loaded.
	"""
	def __init__(self, data='', headers=None, status=0, version=0, reason=None):  # pylint: disable=too-many-arguments
		self.data = data
		self.headers = HTTPHeaders(headers or {})
		self.status = status
		self.version = version
		self.reason = reason

	def addData(self, data):
		self.data += data

	@staticmethod
	def from_httplib(r):  # pylint: disable=invalid-name
		"""
		Given an httplib.HTTPResponse instance, return a corresponding
		urllib3.HTTPResponse object.

		NOTE: This method will perform r.read() which will have side effects
		on the original http.HTTPResponse object.
		"""
		logger.debug2("Creating HTTPResponse from httplib...")
		return HTTPResponse(
			data=r.read(),
			headers=HTTPHeaders(r.getheaders()),
			status=r.status,
			version=r.version,
			reason=r.reason
		)

	# Backwards-compatibility methods for httplib.HTTPResponse
	def getheaders(self):
		return self.headers

	def getheader(self, name, default=None):
		return self.headers.get(name, default)


class HTTPHeaders(collections.MutableMapping):
	"""
	A dictionary that maintains ``Http-Header-Case`` for all keys.

	Heavily influeced by HTTPHeaders from tornado.
	"""

	def __init__(self, *args, **kwargs):
		self._dict = {}
		self.update(*args, **kwargs)

	def __setitem__(self, name, value):
		key = self.normalizeKey(name)
		self._dict[key] = value

	def __getitem__(self, name):
		key = self.normalizeKey(name)
		return self._dict[key]

	def __delitem__(self, name):
		key = self.normalizeKey(name)
		del self._dict[key]

	def __len__(self):
		return len(self._dict)

	def __iter__(self):
		return iter(self._dict)

	@staticmethod
	@lru_cache(maxsize=512)
	def normalizeKey(key):
		return "-".join([w.capitalize() for w in key.split("-")])

	def copy(self):
		# defined in dict but not in MutableMapping.
		return HTTPHeaders(self)

	# Use our overridden copy method for the copy.copy module.
	# This makes shallow copies one level deeper, but preserves
	# the appearance that HTTPHeaders is a single container.
	__copy__ = copy

	def __str__(self):
		return "\n".join("%s: %s" % (name, value) for name, value in self.items())

	__unicode__ = __str__  # lazy

	def __repr__(self):
		return f"{self.__class__.__name__}({self._dict})"


class HTTPConnectionPool:  # pylint: disable=too-many-instance-attributes

	scheme = 'http'

	def __init__(  # pylint: disable=too-many-arguments
		self, host, port, socketTimeout=None, connectTimeout=None,
		retryTime=0, maxsize=1, block=False, reuseConnection=False,
		proxyURL=None
	):

		self.host = forceUnicode(host)
		self.port = forceInt(port)
		self.socketTimeout = forceInt(socketTimeout or 0)
		self.connectTimeout = forceInt(connectTimeout or 0)
		self.retryTime = forceInt(retryTime)
		self.block = forceBool(block)
		self.reuseConnection = forceBool(reuseConnection)
		self.proxyURL = forceUnicode(proxyURL or "")
		self.pool = None
		self.usageCount = 1
		self.num_connections = 0
		self.num_requests = 0
		self.httplibDebugLevel = 0
		self.peerCertificate = None
		self.serverVerified = False
		self.verifyServerCert = False
		self.caCertFile = None
		self.adjustSize(maxsize)

	def increaseUsageCount(self):
		self.usageCount += 1

	def decreaseUsageCount(self):
		self.usageCount -= 1
		if self.usageCount == 0:
			destroyPool(self)

	free = decreaseUsageCount

	def delPool(self):
		if getattr(self, "pool", None):
			while True:
				try:
					conn = self.pool.get(block=False)
					if conn:
						closeConnection(conn)

					time.sleep(0.001)
				except Empty:
					break

	def adjustSize(self, maxsize):
		if maxsize < 1:
			raise ValueError("Connection pool size %d is invalid" % maxsize)
		self.maxsize = forceInt(maxsize)
		self.delPool()
		self.pool = Queue(self.maxsize)
		# Fill the queue up so that doing get() on it will block properly
		for _ in range(self.maxsize):
			self.pool.put(None)

	def __del__(self):
		self.delPool()

	def _new_conn(self):
		"""
		Return a fresh HTTPConnection.
		"""
		self.num_connections += 1
		if self.proxyURL:
			headers = {}
			try:
				url = urlparse(self.proxyURL)
				if url.password:
					logger.setConfidentialStrings(url.password)
				logger.debug("Starting new HTTP connection (%d) to %s:%d over proxy-url %s", self.num_connections, self.host, self.port, self.proxyURL)

				conn = HTTPConnection(host=url.hostname, port=url.port)
				if url.username and url.password:
					logger.debug("Proxy Authentication detected, setting auth with user: %s", url.username)
					headers['Proxy-Authorization'] = createBasicAuthHeader(
						url.username,
						url.password
					)
				conn.set_tunnel(self.host, self.port, headers)
				logger.debug("Connection established to: %s", self.host)
			except Exception as err:  # pylint: disable=broad-except
				logger.error(err)
		else:
			logger.debug("Starting new HTTP connection (%d) to %s:%d", self.num_connections, self.host, self.port)
			conn = HTTPConnection(host=self.host, port=self.port)
			non_blocking_connect_http(conn, self.connectTimeout)
			logger.debug("Connection established to: %s", self.host)
		return conn

	def _get_conn(self, timeout=None):
		"""
		Get a connection. Will return a pooled connection if one is available.
		Otherwise, a fresh connection is returned.
		"""
		try:
			conn = self.pool.get(block=self.block, timeout=timeout)
		except Empty:
			# Oh well, we'll create a new connection then
			conn = None

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
		except Full:
			# This should never happen if self.block == True
			logger.warning("HttpConnectionPool is full, discarding connection: %s", self.host)

	def get_host(self, url):  # pylint: disable=no-self-use
		(scheme, host, port, _baseurl, _username, _password) = urlsplit(url)
		return (scheme, host, port)

	def is_same_host(self, url):
		return url.startswith('/') or self.get_host(url) == (self.scheme, self.host, self.port)

	def getPeerCertificate(self, asPem=False):
		if not self.peerCertificate:
			return None
		if asPem:
			return self.peerCertificate
		return crypto.load_certificate(crypto.FILETYPE_PEM, self.peerCertificate)

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

	def urlopen(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
		self, method, url, body=None, headers=None, retry=True, redirect=True, assert_same_host=True, firstTryTime=None
	):
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
		if not headers:
			headers = {}
		now = time.time()
		if not firstTryTime:
			firstTryTime = now

		conn = None
		if assert_same_host and not self.is_same_host(url):
			host = "%s://%s" % (self.scheme, self.host)
			if self.port:
				host = "%s:%d" % (host, self.port)
			raise HostChangedError("Connection pool with host '%s' tried to open a foreign host: %s" % (host, url))

		try:
			conn = self._get_conn()

			if self.httplibDebugLevel:
				conn.set_debuglevel(self.httplibDebugLevel)

			self.num_requests += 1

			global totalRequests  # pylint: disable=global-statement,invalid-name
			totalRequests += 1

			logger.debug2("Request headers: '%s'", headers)
			logger.debug2("Handing data to connection...")
			conn.request(method, url, body=body, headers=headers)
			if self.socketTimeout:
				conn.sock.settimeout(self.socketTimeout)
			else:
				conn.sock.settimeout(None)

			if not self.peerCertificate and self.scheme.endswith("s"):
				self.peerCertificate = getPeerCertificate(conn, asPEM=True)

			httplib_response = conn.getresponse()

			# from_httplib will perform httplib_response.read() which will have
			# the side effect of letting us use this connection for another
			# request.
			response = HTTPResponse.from_httplib(httplib_response)
			logger.debug2("Response headers: '%s'", response.headers)

			# Put the connection back to be reused
			if self.reuseConnection:
				self._put_conn(conn)
			else:
				logger.debug("Closing connection: %s", conn)
				self._put_conn(None)
				closeConnection(conn)
		except (SocketTimeout, Empty, HTTPException, SocketError) as error:
			logger.debug(error, exc_info=True)
			logger.debug(
				"Request to host '%s' failed, retry: %s, firstTryTime: %s, now: %s, retryTime: %s, connectTimeout: %s, socketTimeout: %s ('%s')",
				self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.socketTimeout, error
			)

			self._put_conn(None)
			closeConnection(conn)

			if retry and (now - firstTryTime < self.retryTime):
				logger.debug("Request to '%s' failed: %s", self.host, forceUnicode(error))
				logger.debug("Waiting before retry...")
				time.sleep(0.2)
				return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			if retry:
				logger.warning("Connecting to '%s' did not succeed after retrying.", self.host)
			raise
		except Exception:
			self._put_conn(None)
			closeConnection(conn)
			raise

		# Handle redirection
		if redirect and response.status in (301, 302, 303, 307) and 'location' in response.headers:
			logger.info("Redirecting %s -> %s", url, response.headers.get('location'))
			time.sleep(0.1)
			self._put_conn(None)
			closeConnection(conn)
			return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)

		return response


class HTTPSConnectionPool(HTTPConnectionPool):
	"""
	Same as HTTPConnectionPool, but HTTPS.
	"""

	scheme = 'https'

	def __init__(  # pylint: disable=too-many-arguments
		self, host, port, socketTimeout=None, connectTimeout=None,
		retryTime=0, maxsize=1, block=False, reuseConnection=False,
		verifyServerCert=False, caCertFile=None, proxyURL=None
	):
		super().__init__(
			host, port, socketTimeout, connectTimeout,
			retryTime, maxsize, block, reuseConnection,
			proxyURL
		)
		self.serverVerified = False
		self.verifyServerCert = False
		self.caCertFile = None

		if caCertFile:
			self.caCertFile = forceFilename(caCertFile)
		self.verifyServerCert = forceBool(verifyServerCert)

		if self.verifyServerCert:
			if not self.caCertFile:
				raise ValueError("Server certificate verfication enabled but no CA cert file given")
			logger.info("Server certificate verfication by CA file '%s' enabled for host '%s'", self.caCertFile, self.host)

		if not self.verifyServerCert:
			ssl_module._create_default_https_context = ssl_module._create_unverified_context

	def _new_conn(self):
		"""
		Return a fresh HTTPSConnection.
		"""
		self.num_connections += 1
		if self.proxyURL:
			headers = {}
			try:
				url = urlparse(self.proxyURL)
				if url.password:
					logger.setConfidentialString(url.password)
				logger.debug("Starting new HTTPS connection (%d) to %s:%d over proxy-url %s", self.num_connections, self.host, self.port, self.proxyURL)
				conn = HTTPSConnection(host=url.hostname, port=url.port)
				if url.username and url.password:
					logger.debug("Proxy Authentication detected, setting auth with user: %s", url.username)
					headers['Proxy-Authorization'] = createBasicAuthHeader(
						url.username,
						url.password
					)
				conn.set_tunnel(self.host, self.port, headers)
				logger.debug("Connection established to: %s", self.host)
			except Exception as err:  # pylint: disable=broad-except
				logger.error(err, exc_info=True)
		else:
			logger.debug("Starting new HTTPS connection (%d) to %s:%d", self.num_connections, self.host, self.port)
			conn = HTTPSConnection(host=self.host, port=self.port)
			logger.debug("Connection established to: %s", self.host)

		if self.verifyServerCert:
			try:
				non_blocking_connect_https(conn, self.connectTimeout, self.caCertFile)
				self.serverVerified = True
				logger.debug("Server verified.")
			except ssl_module.SSLError as err:
				logger.debug("Verification failed: '%s'", err, exc_info=True)
				raise OpsiServiceVerificationError(f"Failed to verify server cert by CA: {err}") from err
			self.peerCertificate = getPeerCertificate(conn, asPEM=True)

		return conn


def urlsplit(url):
	_url = urlparse(url)
	return (_url.scheme, _url.hostname, _url.port, _url.path, _url.username, _url.password)


def getSharedConnectionPoolFromUrl(url, **kw):
	"""
	Given a url, return an HTTP(S)ConnectionPool instance of its host.

	This is a shortcut for not having to determine the host of the url
	before creating an HTTP(S)ConnectionPool instance.

	Passes on whatever kw arguments to the constructor of
	HTTP(S)ConnectionPool. (e.g. timeout, maxsize, block)
	"""
	(scheme, host, port, _baseurl, _username, _password) = urlsplit(url)
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

	poolKey = 'httplib:%s:%d' % (host, port)
	global connectionPools  # pylint: disable=global-statement,invalid-name

	if poolKey not in connectionPools:
		if scheme in ('https', 'webdavs'):
			connectionPools[poolKey] = HTTPSConnectionPool(host, port=port, **kw)
		else:
			connectionPools[poolKey] = HTTPConnectionPool(host, port=port, **kw)
	else:
		connectionPools[poolKey].increaseUsageCount()
		maxsize = kw.get('maxsize', 0)
		if maxsize > connectionPools[poolKey].maxsize:
			connectionPools[poolKey].adjustSize(maxsize)

	return connectionPools[poolKey]


def destroyPool(pool):
	global connectionPools  # pylint: disable=global-statement,invalid-name
	for key, poolinstance in connectionPools.items():
		if poolinstance == pool:
			del connectionPools[key]
			break

def deflateEncode(data, level=1):
	"""
	Compress data with deflate.

	:type data: str
	:type level: int
	:param level: Compression level
	:rtype: bytes
	"""
	if not isinstance(data, bytes):
		data = data.encode()
	return zlib.compress(data, level)

def deflateDecode(data):
	"""
	Decompress data with deflate.

	:type data: bytes
	:rtype: str
	"""
	return zlib.decompress(data)

def gzipEncode(data, level=1):
	"""
	Compress data with gzip.

	:type data: str
	:type level: int
	:param level: Compression level
	:rtype: bytes
	"""
	if not isinstance(data, bytes):
		data = data.encode()
	return gzip.compress(data, level)

def gzipDecode(data):
	"""
	Decompress data with gzip.

	:type data: bytes
	:rtype: str
	"""
	return gzip.decompress(data)

@contextmanager
def closingConnection(connection):
	"This contextmanager closes the connection afterwards."
	try:
		yield connection
	finally:
		closeConnection(connection)


def closeConnection(connection):
	"Close the given connection and any socket that may be open on it."
	try:
		connection.sock.close()
	except Exception:  # pylint: disable=broad-except
		pass

	try:
		connection.close()
	except Exception:  # pylint: disable=broad-except
		pass


def createBasicAuthHeader(username: str, password: str) -> bytes:
	"""
	Creates an header for basic auth.
	"""
	auth = '%s:%s' % (username, password)
	return b'Basic ' + base64.b64encode(auth.encode('latin-1'))
