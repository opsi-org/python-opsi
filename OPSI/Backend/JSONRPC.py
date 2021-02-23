# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

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
JSONRPC backend.

This backend executes the calls on a remote backend via JSONRPC.

:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""

import re
import base64
import json
import socket
import time
import threading
import types
from hashlib import md5
from queue import Queue, Empty

import lz4.frame
try:
	# pyright: reportMissingImports=false
	# python3-pycryptodome installs into Cryptodome
	from Cryptodome.Hash import MD5
	from Cryptodome.Signature import pkcs1_15
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Hash import MD5
	from Crypto.Signature import pkcs1_15

from OPSI import __version__
from OPSI.Backend import no_export
from OPSI.Backend.Base import Backend
from OPSI.Backend.Backend import DeferredCall
from OPSI.Exceptions import (
	OpsiAuthenticationError, OpsiConnectionError, OpsiError,
	OpsiServiceVerificationError, OpsiRpcError, OpsiTimeoutError)
from OPSI.Logger import Logger
from OPSI.Types import (
	forceBool, forceFilename, forceFloat, forceInt, forceList, forceUnicode
)
from OPSI.Util import serialize, deserialize
from OPSI.Util.HTTP import (
	createBasicAuthHeader, getSharedConnectionPool, urlsplit
)
from OPSI.Util.HTTP import deflateDecode, gzipEncode, gzipDecode
from OPSI.Util import getPublicKey

__all__ = ('JSONRPC', 'JSONRPCThread', 'RpcQueue', 'JSONRPCBackend')

_GZIP_COMPRESSION = 'gzip'
_LZ4_COMPRESSION = 'lz4'

logger = Logger()


class JSONRPC(DeferredCall):  # pylint: disable=too-many-instance-attributes
	def __init__(self, jsonrpcBackend, baseUrl, method, params=None, retry=True, callback=None):  # pylint: disable=too-many-arguments
		if params is None:
			params = []
		DeferredCall.__init__(self, callback=callback)
		self.jsonrpcBackend = jsonrpcBackend
		self.baseUrl = baseUrl
		self.id = self.jsonrpcBackend._getRpcId()  # pylint: disable=invalid-name
		self.method = method
		self.params = params
		self.retry = retry

	def execute(self):
		self.process()

	def getRpc(self):
		return {
			"id": self.id,
			"method": self.method,
			"params": serialize(self.params)
		}

	def processResult(self, result):
		try:
			if result.get('error'):
				logger.debug('Result from RPC contained error!')
				error = result['error']
				# Error occurred
				if isinstance(error, dict) and error.get('message'):
					message = error['message']

					try:
						exceptionClass = eval(error.get('class', 'Exception'))  # pylint: disable=eval-used
						# This seems to cut of more than wanted
						#index = message.find(':')
						#if index != -1 and len(message) > index:
						#	message = message[index + 1:].lstrip()
						exception = exceptionClass(f"{message} (error on server)")
					except Exception:  # pylint: disable=broad-except
						exception = OpsiRpcError(message)

					raise exception

				raise OpsiRpcError(f'{error} (error on server)')

			self.result = deserialize(
				result.get('result'),
				preventObjectCreation=self.method.endswith('_getHashes')
			)
		except Exception as err:  # pylint: disable=broad-except
			logger.error(err, exc_info=True)
			self.error = err

	def process(self):
		logger.debug("Executing jsonrpc method %s on host %s", self.method, self.jsonrpcBackend._host)  # pylint: disable=protected-access

		try:
			rpc = json.dumps(self.getRpc())
			logger.trace("jsonrpc request: %s", rpc)
			response = self.jsonrpcBackend._request(baseUrl=self.baseUrl, data=rpc, retry=self.retry)  # pylint: disable=protected-access
			if isinstance(response, bytes):
				response = response.decode()
			logger.trace("jsonrpc response: %s", response)
			self.processResult(json.loads(response))
		except Exception as err:  # pylint: disable=broad-except
			if self.method not in ('backend_exit', 'exit'):
				logger.debug("Failed to process method '%s': %s", self.method, err, exc_info=True)
				logger.info("Failed to process method '%s': %s", self.method, err)
				self.error = err
		finally:
			self._gotResult()


class JSONRPCThread(JSONRPC, threading.Thread):
	def __init__(self, jsonrpcBackend, baseUrl, method, params=None, retry=True, callback=None):  # pylint: disable=too-many-arguments
		if params is None:
			params = []
		threading.Thread.__init__(self)
		JSONRPC.__init__(
			self,
			jsonrpcBackend=jsonrpcBackend,
			baseUrl=baseUrl,
			method=method,
			params=params,
			retry=retry,
			callback=callback
		)

	def execute(self):
		self.start()
		return self.waitForResult()

	def run(self):
		self.process()


class RpcQueue(threading.Thread):
	def __init__(self, jsonrpcBackend, size, poll=0.01):
		threading.Thread.__init__(self)
		self.jsonrpcBackend = jsonrpcBackend
		self.size = size
		self.queue = Queue(size)
		self.poll = poll
		self.stopped = False
		self.jsonrpcs = {}
		self.idle = threading.Event()

	def add(self, jsonrpc):
		logger.debug('Adding jsonrpc %s to queue (current queue size: %s)', jsonrpc, self.queue.qsize())
		self.queue.put(jsonrpc, block=True)
		logger.trace('Added jsonrpc %s to queue', jsonrpc)

	def stop(self):
		self.stopped = True

	def run(self):
		logger.debug("RpcQueue started")
		self.idle.set()
		while not self.stopped or not self.queue.empty():
			self.idle.wait()
			jsonrpcs = []
			while not self.queue.empty():
				self.idle.clear()
				try:
					jsonrpc = self.queue.get(block=False)
					if jsonrpc:
						logger.debug('Got jsonrpc %s from queue', jsonrpc)
						jsonrpcs.append(jsonrpc)
						if len(jsonrpcs) >= self.size:
							break
				except Empty:
					break
			if jsonrpcs:
				self.process(jsonrpcs=jsonrpcs)
			time.sleep(self.poll)
		logger.debug("RpcQueue stopped (empty: %s, stopped: %s)", self.queue.empty(), self.stopped)

	def process(self, jsonrpcs):  # pylint: disable=too-many-branches
		self.jsonrpcs = {}
		for jsonrpc in forceList(jsonrpcs):
			self.jsonrpcs[jsonrpc.id] = jsonrpc
		if not self.jsonrpcs:
			return
		logger.info("Executing bunched jsonrpcs: %s", self.jsonrpcs)
		isExit = False
		try:
			retry = False
			baseUrl = None
			rpc = []
			for jsonrpc in self.jsonrpcs.values():
				isExit = jsonrpc.method in ('backend_exit', 'exit')

				if jsonrpc.retry:
					retry = True

				if not baseUrl:
					baseUrl = jsonrpc.baseUrl
				elif baseUrl != jsonrpc.baseUrl:
					raise OpsiRpcError(
						f"Can't execute jsonrpcs with different base urls at once: ({baseUrl} != {jsonrpc.baseUrl})"
					)
				rpc.append(jsonrpc.getRpc())
			rpc = json.dumps(rpc)
			logger.trace("jsonrpc: %s", rpc)

			response = self.jsonrpcBackend._request(baseUrl=baseUrl, data=rpc, retry=retry)  # pylint: disable=protected-access
			logger.debug("Got response from host %s", self.jsonrpcBackend._host)  # pylint: disable=protected-access
			try:
				response = forceList(json.loads(response))
			except Exception as err:  # pylint: disable=broad-except
				raise OpsiRpcError("Failed to json decode response {response}: {err}") from err

			for resp in response:
				try:
					responseId = resp['id']
				except KeyError as err:
					raise KeyError(
						f"Failed to get id from: {resp} ({response}): {err}"
					) from err

				try:
					jsonrpc = self.jsonrpcs[responseId]
				except KeyError as err:
					raise KeyError(
						f"Failed to get jsonrpc with id {responseId}: {err}"
					) from err

				try:
					jsonrpc.processResult(resp)
				except Exception as err:  # pylint: disable=broad-except
					raise RuntimeError(
						f"Failed to process response {resp} with jsonrpc {jsonrpc}: {err}"
					) from err
		except Exception as err:  # pylint: disable=broad-except
			if not isExit:
				logger.error(err)

			for jsonrpc in self.jsonrpcs.values():
				jsonrpc.error = err
				jsonrpc._gotResult()  # pylint: disable=protected-access

		self.jsonrpcs = {}
		self.idle.set()


class JSONRPCBackend(Backend):  # pylint: disable=too-many-instance-attributes

	_DEFAULT_HTTP_PORT = 4444
	_DEFAULT_HTTPS_PORT = 4447

	def __init__(self, address, **kwargs):  # pylint: disable=too-many-branches,too-many-statements
		"""
		Backend for JSON-RPC access to another opsi service.

		:param compression: Should requests be compressed?
		:type compression: bool
		"""

		self._name = 'jsonrpc'

		Backend.__init__(self, **kwargs)

		self._application = 'opsi JSONRPCBackend/%s' % __version__
		self._sessionId = None
		self._compression = False
		self._connectOnInit = True
		self._connected = False
		self._retryTime = 5
		self._host = None
		self._port = None
		self._baseUrl = '/rpc'
		self._protocol = 'https'
		self._socketTimeout = None
		self._connectTimeout = 30
		self._connectionPool = None
		self._connectionPoolSize = 2
		self._interface = None
		self._rpcId = 0
		self._rpcIdLock = threading.Lock()
		self._async = False
		self._rpcQueue = None
		self._rpcQueuePollingTime = 0.01
		self._rpcQueueSize = 10
		self._caCertFile = None
		self._verifyServerCert = False
		self._proxyURL = None
		self.serverName = None

		if not self._username:
			self._username = ''
		if not self._password:
			self._password = ''

		retry = True
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'application':
				self._application = str(value)
			elif option == 'sessionid':
				self._sessionId = str(value)
			elif option == 'compression':
				self._compression = self._parseCompressionValue(value)
			elif option == 'connectoninit':
				self._connectOnInit = forceBool(value)
			elif option == 'connecttimeout' and value not in (None, ""):
				self._connectTimeout = forceInt(value)
			elif option == 'connectionpoolsize' and value not in (None, ""):
				self._connectionPoolSize = forceInt(value)
			elif option in ('timeout', 'sockettimeout') and value not in (None, ""):
				self._socketTimeout = forceInt(value)
			elif option == 'retry':
				retry = forceBool(value)
			elif option == 'retrytime':
				self._retryTime = forceInt(value)
			elif option == 'rpcqueuepollingtime':
				self._rpcQueuePollingTime = forceFloat(value)
			elif option == 'rpcqueuesize':
				self._rpcQueueSize = forceInt(value)
			elif option == 'verifyservercert':
				self._verifyServerCert = forceBool(value)
			elif option == 'cacertfile' and value not in (None, ""):
				self._caCertFile = forceFilename(value)
			elif option == 'proxyurl' and value not in (None, ""):
				logger.debug("ProxyURL detected: '%s'", value)
				self._proxyURL = forceUnicode(value)

		if not retry:
			self._retryTime = 0

		if self._password:
			logger.addConfidentialString(self._password)

		self._processAddress(address)
		self._connectionPool = getSharedConnectionPool(
			scheme=self._protocol,
			host=self._host,
			port=self._port,
			socketTimeout=self._socketTimeout,
			connectTimeout=self._connectTimeout,
			retryTime=self._retryTime,
			maxsize=self._connectionPoolSize,
			block=True,
			verifyServerCert=self._verifyServerCert,
			caCertFile=self._caCertFile,
			proxyURL=self._proxyURL
		)

		if self._connectOnInit:
			self.connect()

	@property
	def serverVersion(self):
		try:
			if self.serverName:
				match = re.search(r"^opsi\D+(\d+\.\d+\.\d+\.\d+)", self.serverName)
				if match:
					return [int(v) for v in match.group(1).split('.')]
		except Exception as err:  # pylint: disable=broad-except
			logger.warning("Failed to parse server version '%s': %s", self.serverName, err)
		return None

	def _stopRpcQueue(self):
		if self._rpcQueue:
			self._rpcQueue.stop()

	def _startRpcQueue(self):
		if not self._rpcQueue or not self._rpcQueue.is_alive():
			self._rpcQueue = RpcQueue(
				jsonrpcBackend=self,
				size=self._rpcQueueSize,
				poll=self._rpcQueuePollingTime
			)
			self._rpcQueue.setDaemon(True)
			self._rpcQueue.start()

	def __del__(self):
		self._stopRpcQueue()
		if self._connectionPool:
			self._connectionPool.free()

	@no_export
	def getPeerCertificate(self, asPem=False):
		return self._connectionPool.getPeerCertificate(asPem)

	def backend_exit(self):
		if self._connected:
			try:
				self._jsonRPC('backend_exit', retry=False)
			except Exception:  # pylint: disable=broad-except
				pass

		self._stopRpcQueue()

	@no_export
	def setAsync(self, enableAsync):
		if not self._connected:
			raise OpsiConnectionError('Not connected')

		if enableAsync:
			self._startRpcQueue()
			self._async = True
		else:
			self._async = False
			self._stopRpcQueue()

	@no_export
	def setCompression(self, compression):
		"""
		Set the compression to use.

		:param compression: `True` to enable compression, `False` to disable.
		:type compression: bool
		"""
		self._compression = self._parseCompressionValue(compression)

	@staticmethod
	def _parseCompressionValue(compression):
		if isinstance(compression, bool):
			return compression

		value = forceUnicode(compression).strip().lower()
		if value in ('true', 'false'):
			return forceBool(value)
		if value == _GZIP_COMPRESSION:
			return _GZIP_COMPRESSION
		if value == _LZ4_COMPRESSION:
			return _LZ4_COMPRESSION
		return False

	@no_export
	def isCompressionUsed(self):
		"""
		Is compression used?

		:rtype: bool
		"""
		return bool(self._compression)

	@no_export
	def isConnected(self):
		return self._connected

	@no_export
	def connect(self):
		modules = None
		realmodules = {}
		mysqlBackend = False

		asyncStatus = self._async
		self._async = False

		try:  # pylint: disable=too-many-nested-blocks
			try:
				self._interface = self._jsonRPC('backend_getInterface')
				if 'opsiclientd' in self._application:
					try:
						backendInfo = self._jsonRPC('backend_info')
						modules = backendInfo.get('modules', None)
						realmodules = backendInfo.get('realmodules', None)
						if modules:
							logger.confidential("Modules: %s", modules)
						else:
							modules = {'customer': None}

						for meth in self._interface:
							if meth.get('name') == 'dispatcher_getConfig':
								for entry in self._jsonRPC('dispatcher_getConfig'):
									for bn in entry[1]:
										if "sql" in bn.lower() and len(entry[0]) <= 4 and '*' in entry[0]:
											mysqlBackend = True
								break
					except Exception as err:  # pylint: disable=broad-except
						logger.info(str(err))
			except (OpsiAuthenticationError, OpsiTimeoutError, OpsiServiceVerificationError, socket.error) as err:
				logger.debug("Failed to connect: %s", err)
				raise

			self._createInstanceMethods(modules, realmodules, mysqlBackend)

			self._connected = True
			logger.info("%s: Connected to service", self)
		finally:
			self._async = asyncStatus

	def _getRpcId(self):
		with self._rpcIdLock:
			self._rpcId += 1

		return self._rpcId

	def _processAddress(self, address):
		self._protocol = 'https'
		(scheme, host, port, baseurl, username, password) = urlsplit(address)
		if scheme:
			if scheme not in ('http', 'https'):
				raise ValueError("Protocol %s not supported" % scheme)
			self._protocol = scheme

		self._host = host

		if port:
			self._port = port
		elif self._protocol == 'https':
			self._port = self._DEFAULT_HTTPS_PORT
		else:
			self._port = self._DEFAULT_HTTP_PORT

		if baseurl and (baseurl != '/'):
			self._baseUrl = baseurl
		if not self._username and username:
			self._username = username
		if not self._password and password:
			self._password = password

	def jsonrpc_getSessionId(self):
		return self._sessionId

	def _createInstanceMethods(self, modules=None, realmodules={}, mysqlBackend=False):  # pylint: disable=dangerous-default-value,too-many-locals,too-many-branches,too-many-statements
		licenseManagementModule = True
		if modules:
			licenseManagementModule = False
			if not modules.get('customer'):
				logger.notice("Disabling mysql backend and license management module: no customer in modules file")
				if mysqlBackend:
					raise OpsiError("MySQL backend in use but not licensed")

			elif not modules.get('valid'):
				logger.notice("Disabling mysql backend and license management module: modules file invalid")
				if mysqlBackend:
					raise OpsiError("MySQL backend in use but not licensed")

			elif (
				modules.get('expires', '') != 'never' and
				time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0
			):
				logger.notice("Disabling mysql backend and license management module: modules file expired")
				if mysqlBackend:
					raise OpsiError("MySQL backend in use but not licensed")
			else:
				logger.info("Verifying modules file signature")
				publicKey = getPublicKey(
					data=base64.decodebytes(
						b"AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDo"
						b"jY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8"
						b"S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDU"
						b"lk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP"
					)
				)
				data = ""
				mks = list(modules.keys())
				mks.sort()
				for module in mks:
					if module in ("valid", "signature"):
						continue
					if module in realmodules:
						val = realmodules[module]
						if int(val) > 0:
							modules[module] = True
					else:
						val = modules[module]
						if isinstance(val, bool):
							val = "yes" if val else "no"
					data += "%s = %s\r\n" % (module.lower().strip(), val)

				verified = False
				if modules["signature"].startswith("{"):
					s_bytes = int(modules['signature'].split("}", 1)[-1]).to_bytes(256, "big")
					try:
						pkcs1_15.new(publicKey).verify(MD5.new(data.encode()), s_bytes)
						verified = True
					except ValueError:
						# Invalid signature
						pass
				else:
					h_int = int.from_bytes(md5(data.encode()).digest(), "big")
					s_int = publicKey._encrypt(int(modules["signature"]))  # pylint: disable=protected-access
					verified = h_int == s_int

				if not verified:
					logger.error("Disabling mysql backend and license management module: modules file invalid")
					if mysqlBackend:
						raise OpsiError("MySQL backend in use but not licensed")
				else:
					logger.debug("Modules file signature verified (customer: %s)", modules.get("customer"))

					if modules.get("license_management"):
						licenseManagementModule = True

					if mysqlBackend and not modules.get("mysql_backend"):
						raise OpsiError("MySQL backend in use but not licensed")

		for method in self._interface:
			try:
				methodName = method['name']

				if methodName in ('backend_exit', 'backend_getInterface'):
					continue

				args = method['args']
				varargs = method['varargs']
				keywords = method['keywords']
				defaults = method['defaults']

				argString = []
				callString = []
				for i, argument in enumerate(args):
					if argument == 'self':
						continue

					if isinstance(defaults, (tuple, list)) and len(defaults) + i >= len(args):
						default = defaults[len(defaults) - len(args) + i]
						if isinstance(default, str):
							default = "{0!r}".format(default).replace('"', "'")
						argString.append(f'{argument}={default}')
					else:
						argString.append(argument)
					callString.append(argument)

				if varargs:
					for vararg in varargs:
						argString.append(f'*{vararg}')
						callString.append(vararg)

				if keywords:
					argString.append(f'**{keywords}')
					callString.append(keywords)

				argString = ', '.join(argString)
				callString = ', '.join(callString)

				logger.trace("%s: arg string is: %s", argString, methodName)
				logger.trace("%s: call string is: %s", callString, methodName)
				# This would result in not overwriting Backend methods like log_read, log_write, ...
				# if getattr(self, methodName, None) is None:
				if not licenseManagementModule and "license" in methodName:
					exec(f'def {methodName}(self, {argString}): return')  # pylint: disable=exec-used
				else:
					exec(f'def {methodName}(self, {argString}): return self._jsonRPC("{methodName}", [{callString}])')  # pylint: disable=exec-used
				setattr(self, methodName, types.MethodType(eval(methodName), self))  # pylint: disable=eval-used
			except Exception as err:  # pylint: disable=broad-except
				logger.critical("Failed to create instance method '%s': %s", method, err)

	def _jsonRPC(self, method, params=[], retry=True):  # pylint: disable=dangerous-default-value
		if self._async:
			self._startRpcQueue()
			jsonrpc = JSONRPC(jsonrpcBackend=self, baseUrl=self._baseUrl, method=method, params=params, retry=retry)
			self._rpcQueue.add(jsonrpc)
			return jsonrpc

		jsonrpc = JSONRPCThread(jsonrpcBackend=self, baseUrl=self._baseUrl, method=method, params=params, retry=retry)
		return jsonrpc.execute()

	@no_export
	def httpRequest(self, method, url, data=None, headers={}, retry=True):  # pylint: disable=dangerous-default-value,too-many-arguments,too-many-branches
		if 'User-Agent' not in headers:
			headers['User-Agent'] = self._application
		if 'Cookie' not in headers and self._sessionId:
			headers['Cookie'] = self._sessionId
		if 'Authorization' not in headers:
			headers['Authorization'] = createBasicAuthHeader(
				self._username,
				self._password
			)

		if method == "POST":
			if data:
				if not isinstance(data, bytes):
					data = data.encode("utf-8")
			else:
				data = b""

			if data and self._compression:
				compression = self._compression
				if compression is True:
					# Auto choose later by server version
					# opsiconfd 4.2.0.96 (uvicorn)
					compression = _GZIP_COMPRESSION
					sv = self.serverVersion
					if sv and (sv[0] > 4 or (sv[0] == 4 and sv[1] > 1)):
						compression = _LZ4_COMPRESSION

				if compression == _LZ4_COMPRESSION:
					logger.trace("Compressing data with lz4")
					headers['Content-Encoding'] = 'lz4'
					data = lz4.frame.compress(data, compression_level=0, block_linked=True)
					logger.trace("Data compressed.")
				else:
					logger.trace("Compressing data with gzip")
					headers['Content-Encoding'] = 'gzip'
					data = gzipEncode(data)
					logger.trace("Data compressed.")

			headers['Content-Length'] = str(len(data))

		response = self._connectionPool.urlopen(method=method, url=url, body=data, headers=headers, retry=retry)
		if 'server' in response.headers:
			self.serverName = response.headers.get('server')
		return response

	def _request(self, baseUrl, data, retry=True):
		headers = {
			'Accept': 'application/json, text/plain',
			'Accept-Encoding': 'deflate, gzip',
			'Content-Type': 'application/json',
		}

		logger.trace("Request to host %s, url: %s, query: %s", self._host, baseUrl, data)
		logger.debug("Posting request...")
		response = self.httpRequest(method='POST', url=baseUrl, data=data, headers=headers, retry=retry)
		return self._processResponse(response)

	def _processResponse(self, response):
		logger.trace("Processing response...")
		self._readSessionId(response)

		response = self._decompressResponse(response)
		logger.trace("Response is: %s", response)
		return response

	def _readSessionId(self, response):
		"""
		Reads the session ID from the response and saves it for future use.
		"""
		cookie = response.getheader('set-cookie', None)

		if cookie:
			# Store sessionId cookie
			sessionId = cookie.split(';')[0].strip()
			if sessionId != self._sessionId:
				self._sessionId = sessionId

	@staticmethod
	def _decompressResponse(response):
		"""
		Decompress the body of the response based on it's encoding.
		"""
		contentEncoding = response.getheader('Content-Encoding', '').lower()
		logger.trace("Content-Encoding: %s", contentEncoding)

		response = response.data
		if contentEncoding == 'gzip':
			logger.debug("Expecting gzip compressed data from server")
			response = gzipDecode(response)
		elif contentEncoding == "deflate":
			logger.debug("Expecting deflate compressed data from server")
			response = deflateDecode(response)
		elif contentEncoding == "lz4":
			logger.debug("Expecting lz4 compressed data from server")
			response = lz4.frame.decompress(response)

		logger.trace("Response is: %s", response)
		return response

	def getInterface(self):
		return self.backend_getInterface()

	def backend_getInterface(self):
		return self._interface

	def __repr__(self):
		if self._name:
			return f'<{self.__class__.__name__}(address={self._name}, host={self._host}, compression={self._compression})>'
		return f'<{self.__class__.__name__}(host={self._host}, compression={self._compression})>'
