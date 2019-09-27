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


:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import gzip
import os
import re
import socket
import time
import zlib
import urlparse
from contextlib import contextmanager
from io import BytesIO
from collections import MutableMapping

try:
	from cStringIO import StringIO
except ImportError:
	from io import StringIO

from Queue import Queue, Empty, Full
from httplib import HTTPConnection, HTTPSConnection, HTTPException
from socket import error as SocketError, timeout as SocketTimeout
import ssl as ssl_module
from OpenSSL import crypto

from OPSI.Exceptions import (OpsiAuthenticationError, OpsiTimeoutError,
	OpsiServiceVerificationError)
from OPSI.Types import forceBool, forceFilename, forceInt, forceUnicode, forceUnicodeLower
from OPSI.Logger import LOG_DEBUG, LOG_INFO, Logger
from OPSI.Util import encryptWithPublicKeyFromX509CertificatePEMFile, randomString

logger = Logger()

connectionPools = {}
totalRequests = 0

try:
	# We are running a new version of Python that implements PEP 476:
	# https://www.python.org/dev/peps/pep-0476/
	# To not break our expected behaviour we patch the default context
	# until we have a correct certificate check implementation.
	# TODO: remove this workaround when support for TLS1.1+ is implemented
	ssl_module._create_default_https_context = ssl_module._create_unverified_context
except AttributeError:
	pass


def non_blocking_connect_http(self, connectTimeout=0):
	''' Non blocking connect, needed for KillableThread '''
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(3.0)
	started = time.time()
	lastError = None
	while True:
		try:
			if connectTimeout > 0 and ((time.time() - started) >= connectTimeout):
				raise OpsiTimeoutError(u"Timed out after {0:d} seconds (last error: {1})".format(connectTimeout, forceUnicode(lastError)))
			sock.connect((self.host, self.port))
			break
		except socket.error as error:
			logger.logException(error, LOG_DEBUG)
			logger.debug(error)
			if error[0] in (106, 10056):
				# Transport endpoint is already connected
				break
			if error[0] not in (114, ) or not lastError:
				lastError = error
			time.sleep(0.5)
	sock.settimeout(None)
	self.sock = sock


def non_blocking_connect_https(self, connectTimeout=0, verifyByCaCertsFile=None):
	non_blocking_connect_http(self, connectTimeout)
	logger.debug2(u"verifyByCaCertsFile is: {0!r}", verifyByCaCertsFile)
	if verifyByCaCertsFile:
		logger.debug(u"verifyByCaCertsFile is: {0!r}", verifyByCaCertsFile)
		self.sock = ssl_module.wrap_socket(self.sock, keyfile=self.key_file, certfile=self.cert_file, cert_reqs=ssl_module.CERT_REQUIRED, ca_certs=verifyByCaCertsFile)
		logger.debug(u"Server verified by CA")
	else:
		self.sock = ssl_module.wrap_socket(self.sock, keyfile=self.key_file, certfile=self.cert_file, cert_reqs=ssl_module.CERT_NONE)


def getPeerCertificate(httpsConnectionOrSSLSocket, asPEM=True):
	logger.debug2("Trying to get peer cert...")
	sock = httpsConnectionOrSSLSocket
	try:
		sock = sock.sock
	except AttributeError:
		pass

	try:
		cert = crypto.load_certificate(crypto.FILETYPE_ASN1, sock.getpeercert(binary_form=True))

		if not asPEM:
			return cert

		return crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
	except Exception as error:
		logger.debug2(u"Failed to get peer cert: {0}", error)
		return None


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
	def __init__(self, data='', headers=None, status=0, version=0, reason=None, strict=0):
		self.data = data
		self.headers = HTTPHeaders(headers or {})
		self.status = status
		self.version = version
		self.reason = reason
		self.strict = strict

	def addData(self, data):
		self.data += data

	@staticmethod
	def from_httplib(r):
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
			reason=r.reason,
			strict=r.strict
		)

	# Backwards-compatibility methods for httplib.HTTPResponse
	def getheaders(self):
		return self.headers

	def getheader(self, name, default=None):
		return self.headers.get(name, default)


class HTTPHeaders(MutableMapping):
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
		return "{}({!r})".format(self.__class__.__name__, self._dict)


class HTTPConnectionPool(object):

	scheme = 'http'

	def __init__(self, host, port, socketTimeout=None, connectTimeout=None,
				retryTime=0, maxsize=1, block=False, reuseConnection=False,
				verifyServerCert=False, serverCertFile=None, caCertFile=None,
				verifyServerCertByCa=False, proxyURL=None):

		self.host = forceUnicode(host)
		self.port = forceInt(port)
		self.socketTimeout = forceInt(socketTimeout or 0)
		self.connectTimeout = forceInt(connectTimeout or 0)
		self.retryTime = forceInt(retryTime)
		self.block = forceBool(block)
		self.reuseConnection = forceBool(reuseConnection)
		self.proxyURL = forceUnicode(proxyURL or u"")
		self.pool = None
		self.usageCount = 1
		self.num_connections = 0
		self.num_requests = 0
		self.httplibDebugLevel = 0
		self.peerCertificate = None
		self.serverVerified = False
		self.verifyServerCert = False
		self.serverCertFile = None
		self.caCertFile = None
		self.verifyServerCertByCa = False

		if isinstance(self, HTTPSConnectionPool):
			if self.host in ('localhost', '127.0.0.1'):
				self.serverVerified = True
				logger.debug(u"No host verification for localhost")
			else:
				if caCertFile:
					self.caCertFile = forceFilename(caCertFile)
				self.verifyServerCertByCa = forceBool(verifyServerCertByCa)

				if self.verifyServerCertByCa:
					if not self.caCertFile:
						raise ValueError(u"Server certificate verfication by CA enabled but no CA cert file given")
					logger.info(u"Server certificate verfication by CA file '%s' enabled for host '%s'" % (self.caCertFile, self.host))
				else:
					self.verifyServerCert = forceBool(verifyServerCert)
					if serverCertFile:
						self.serverCertFile = forceFilename(serverCertFile)
					if self.verifyServerCert:
						if not self.serverCertFile:
							raise ValueError(u"Server verfication enabled but no server cert file given")
						logger.info(u"Server verfication by server certificate enabled for host '%s'" % self.host)
		self.adjustSize(maxsize)

	def increaseUsageCount(self):
		self.usageCount += 1

	def decreaseUsageCount(self):
		self.usageCount -= 1
		if self.usageCount == 0:
			destroyPool(self)

	free = decreaseUsageCount

	def delPool(self):
		if self.pool:
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
			raise ValueError(u"Connection pool size %d is invalid" % maxsize)
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
				url = urlparse.urlparse(self.proxyURL)
				if url.password:
					logger.setConfidentialStrings(url.password)
				logger.debug(u"Starting new HTTP connection (%d) to %s:%d over proxy-url %s" % (self.num_connections, self.host, self.port, self.proxyURL))

				conn = HTTPConnection(host=url.hostname, port=url.port)
				if url.username and url.password:
					logger.debug(u"Proxy Authentication detected, setting auth with user: '%s'" % url.username)
					auth = "{username}:{password}".format(username=url.username, password=url.password)
					headers['Proxy-Authorization'] = 'Basic ' + base64.base64encode(auth)
				conn.set_tunnel(self.host, self.port, headers)
				logger.debug(u"Connection established to: %s" % self.host)
			except Exception as error:
				logger.error(error)
		else:
			logger.debug(u"Starting new HTTP connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
			conn = HTTPConnection(host=self.host, port=self.port)
			non_blocking_connect_http(conn, self.connectTimeout)
			logger.debug(u"Connection established to: %s" % self.host)
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
			logger.warning(u"HttpConnectionPool is full, discarding connection: %s" % self.host)

	def get_host(self, url):
		(scheme, host, port, baseurl, username, password) = urlsplit(url)
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
		if assert_same_host and not self.is_same_host(url):
			host = "%s://%s" % (self.scheme, self.host)
			if self.port:
				host = "%s:%d" % (host, self.port)
			raise HostChangedError(u"Connection pool with host '%s' tried to open a foreign host: %s" % (host, url))

		try:
			conn = self._get_conn()

			if self.httplibDebugLevel:
				conn.set_debuglevel(self.httplibDebugLevel)

			self.num_requests += 1

			global totalRequests
			totalRequests += 1

			randomKey = None
			if isinstance(self, HTTPSConnectionPool) and self.verifyServerCert and not self.serverVerified:
				try:
					logger.info(u"Encoding authorization")
					randomKey = randomString(32).encode('latin-1')
					encryptedKey = encryptWithPublicKeyFromX509CertificatePEMFile(randomKey, self.serverCertFile)
					logger.debug2("Key encrypted...")
					headers['X-opsi-service-verification-key'] = base64.b64encode(encryptedKey)
					for key, value in headers.items():
						if key.lower() == 'authorization':
							logger.debug2("Procesing authorization header...")
							if value.lower().startswith('basic'):
								value = value[5:].strip()
							value = base64.b64decode(value).strip()
							logger.debug2("Decoded authorization header...")
							encodedAuth = encryptWithPublicKeyFromX509CertificatePEMFile(value, self.serverCertFile)
							headers[key] = 'Opsi ' + base64.b64encode(encodedAuth)
				except Exception as error:
					logger.logException(error, LOG_INFO)
					logger.critical(u"Cannot verify server based on certificate file {0!r}: {1}", self.serverCertFile, error)
					randomKey = None

			logger.debug2("Handing data to connection...")
			conn.request(method, url, body=body, headers=headers)
			if self.socketTimeout:
				conn.sock.settimeout(self.socketTimeout)
			else:
				conn.sock.settimeout(None)
			httplib_response = conn.getresponse()

			# from_httplib will perform httplib_response.read() which will have
			# the side effect of letting us use this connection for another
			# request.
			response = HTTPResponse.from_httplib(httplib_response)

			if randomKey:
				logger.debug2("Checking for random key...")
				try:
					key = response.getheader('x-opsi-service-verification-key', None)
					if not key:
						raise ValueError(u"HTTP header 'X-opsi-service-verification-key' missing")
					if key.strip() != randomKey.strip():
						raise OpsiAuthenticationError(u"opsi-service-verification-key '%s' != '%s'" % (key, randomKey))
					self.serverVerified = True
					logger.notice(u"Service verified by opsi-service-verification-key")
				except Exception as error:
					logger.error(u"Service verification failed: {0}", error)
					raise OpsiServiceVerificationError(u"Service verification failed: %s" % error)

			if self.serverCertFile and self.peerCertificate:
				try:
					certDir = os.path.dirname(self.serverCertFile)
					if not os.path.exists(certDir):
						os.makedirs(certDir)
					with open(self.serverCertFile, 'w') as f:
						f.write(self.peerCertificate)
				except Exception as error:
					logger.error(u"Failed to create server cert file {0!r}: {1}", self.serverCertFile, error)

			# Put the connection back to be reused
			if self.reuseConnection:
				self._put_conn(conn)
			else:
				logger.debug(u"Closing connection: {0}", conn)
				self._put_conn(None)
				closeConnection(conn)
		except (SocketTimeout, Empty, HTTPException, SocketError) as error:
			logger.logException(error, logLevel=LOG_DEBUG)
			try:
				logger.debug(
					u"Request to host {0!r} failed, retry: {1}, firstTryTime: {2}, now: {3}, retryTime: {4}, connectTimeout: {5}, socketTimeout: {6} ({7!r})",
					self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.socketTimeout, error
				)
			except Exception as loggingError:
				logger.debug(u"Logging exception failed: {0}", forceUnicode(loggingError))
				logger.debug(u"Trying to log again without original exception.")
				try:
					logger.debug(
						u"Request to host {0!r} failed, retry: {1}, firstTryTime: {2}, now: {3}, retryTime: {4}, connectTimeout: {5}, socketTimeout: {6}",
						self.host, retry, firstTryTime, now, self.retryTime, self.connectTimeout, self.isocketTimeout
					)
				except Exception as error:
					logger.debug(u"Logging message failed: {0!r}", error)
					logger.warning(u"Logging message failed: {0}", forceUnicode(error))

			self._put_conn(None)
			closeConnection(conn)

			if retry and (now - firstTryTime < self.retryTime):
				logger.debug(u"Request to {0!r} failed: {1}", self.host, forceUnicode(error))
				logger.debug(u"Waiting before retry...")
				time.sleep(0.2)
				return self.urlopen(method, url, body, headers, retry, redirect, assert_same_host, firstTryTime)
			else:
				if retry:
					logger.warning("Connecting to {0!r} did not succeed after retrying.", self.host)

				raise
		except Exception:
			self._put_conn(None)
			closeConnection(conn)
			raise

		# Handle redirection
		if redirect and response.status in (301, 302, 303, 307) and 'location' in response.headers:
			logger.info(u"Redirecting %s -> %s" % (url, response.headers.get('location')))
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

	def _new_conn(self):
		"""
		Return a fresh HTTPSConnection.
		"""
		self.num_connections += 1
		if self.proxyURL:
			headers = {}
			try:
				url = urlparse.urlparse(self.proxyURL)
				if url.password:
					logger.setConfidentialString(url.password)
				logger.debug(u"Starting new HTTPS connection (%d) to %s:%d over proxy-url %s" % (self.num_connections, self.host, self.port, self.proxyURL))
				conn = HTTPSConnection(host=url.hostname, port=url.port)
				if url.username and url.password:
					logger.debug(u"Proxy Authentication detected, setting auth with user: '%s'" % url.username)
					auth = "{username}:{password}".format(username=url.username, password=url.password)
					headers['Proxy-Authorization'] = 'Basic ' + base64.base64encode(auth)
				conn.set_tunnel(self.host, self.port, headers)
				logger.debug(u"Connection established to: %s" % self.host)
			except Exception as e:
				logger.logException(e)
		else:
			logger.debug(u"Starting new HTTPS connection (%d) to %s:%d" % (self.num_connections, self.host, self.port))
			conn = HTTPSConnection(host=self.host, port=self.port)
			logger.debug(u"Connection established to: %s" % self.host)

		if self.verifyServerCert or self.verifyServerCertByCa:
			try:
				non_blocking_connect_https(conn, self.connectTimeout, self.caCertFile)
				if not self.verifyServerCertByCa:
					self.serverVerified = True
					logger.debug("Server verified.")
			except ssl_module.SSLError as error:
				logger.debug(u"Verification failed: {0!r}", error)
				if self.verifyServerCertByCa:
					raise OpsiServiceVerificationError(u"Failed to verify server cert by CA: %s" % error)

				logger.debug("Going to try a connect without caCertFile...")
				non_blocking_connect_https(conn, self.connectTimeout)
			except Exception as error:
				logger.debug(u"Verification failed: {0!r}", error)
				raise OpsiServiceVerificationError(forceUnicode(error))

		self.peerCertificate = getPeerCertificate(conn, asPEM=True)
		if self.verifyServerCertByCa:
			logger.debug("Attempting to verify server cert by CA...")
			try:
				if self.peerCertificate:
					commonName = crypto.load_certificate(crypto.FILETYPE_PEM, self.peerCertificate).get_subject().commonName
					host = self.host
					if re.search(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host):
						fqdn = socket.getfqdn(host)
						if fqdn == host:
							raise OpsiServiceVerificationError(u"Failed to get fqdn for ip %s" % host)
						host = fqdn
					if not host or not commonName or (host.lower() != commonName.lower()):
						raise OpsiServiceVerificationError(u"Host '%s' does not match common name '%s'" % (host, commonName))
					self.serverVerified = True
				else:
					raise OpsiServiceVerificationError(u"Failed to get peer certificate")
			except Exception:
				closeConnection(conn)
				raise

		return conn


def urlsplit(url):
	url = forceUnicode(url)
	scheme = None
	baseurl = u'/'
	port = None
	username = None
	password = None
	if url.find('://') != -1:
		(scheme, url) = url.split('://', 1)
		scheme = scheme.lower()
	parts = url.split('/', 1)
	host = parts[0]

	if len(parts) > 1:
		baseurl += parts[1]

	if '@' in host:
		username, host = host.split('@', 1)
		if ':' in username:
			username, password = username.split(':', 1)

	if ':' in host:
		host, port = host.split(':', 1)
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

	poolKey = u'httplib:%s:%d' % (host, port)
	global connectionPools

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
	global connectionPools
	for key, poolinstance in connectionPools.items():
		if poolinstance == pool:
			del connectionPools[key]
			break


def deflateEncode(data, level=1):
	if isinstance(data, unicode):
		data = data.encode('utf-8')
	return zlib.compress(data, level)


def deflateDecode(data):
	return forceUnicode(zlib.decompress(data))


def gzipEncode(data, level=1):
	if isinstance(data, unicode):
		data = data.encode('utf-8')

	inmemoryFile = BytesIO()
	with gzip.GzipFile(fileobj=inmemoryFile, mode="w", compresslevel=level) as gzipfile:
		gzipfile.write(data)

	return inmemoryFile.getvalue()


def gzipDecode(data):
	with gzip.GzipFile(fileobj=StringIO(data), mode="r") as gzipfile:
		uncompressedData = gzipfile.read()

	return forceUnicode(uncompressedData)


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
	except Exception:
		pass

	try:
		connection.close()
	except Exception:
		pass
