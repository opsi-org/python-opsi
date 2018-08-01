# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2010-2018 uib GmbH <info@uib.de>

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
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import json
import socket
import time
import threading
import types
from hashlib import md5
from queue import Queue, Empty
from sys import version_info
from twisted.conch.ssh import keys

from OPSI import __version__
from OPSI.Backend.Base import Backend
from OPSI.Backend.Backend import DeferredCall
from OPSI.Exceptions import (
	OpsiAuthenticationError, OpsiConnectionError, OpsiError,
	OpsiServiceVerificationError, OpsiRpcError, OpsiTimeoutError)
from OPSI.Logger import Logger, LOG_INFO
from OPSI.Types import (
	forceBool, forceFilename, forceFloat, forceInt, forceList, forceUnicode)
from OPSI.Util import serialize, deserialize
from OPSI.Util.HTTP import getSharedConnectionPool, urlsplit
from OPSI.Util.HTTP import deflateEncode, deflateDecode, gzipDecode

__all__ = ('JSONRPC', 'JSONRPCThread', 'RpcQueue', 'JSONRPCBackend')

logger = Logger()


class JSONRPC(DeferredCall):
	def __init__(self, jsonrpcBackend, baseUrl, method, params=None, retry=True, callback=None):
		if params is None:
			params = []
		DeferredCall.__init__(self, callback=callback)
		self.jsonrpcBackend = jsonrpcBackend
		self.baseUrl = baseUrl
		self.id = self.jsonrpcBackend._getRpcId()
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
						exceptionClass = eval(error.get('class', 'Exception'))
						index = message.find(':')
						if index != -1 and len(message) > index:
							message = message[index + 1:].lstrip()
						exception = exceptionClass(u'%s (error on server)' % message)
					except Exception:
						exception = OpsiRpcError(message)

					raise exception

				raise OpsiRpcError(u'{0} (error on server)'.format(error))

			self.result = deserialize(
				result.get('result'),
				preventObjectCreation=self.method.endswith('_getHashes')
			)
		except Exception as error:
			logger.logException(error)
			self.error = error

	def process(self):
		logger.debug(u"Executing jsonrpc method {0!r} on host {1!r}", self.method, self.jsonrpcBackend._host)

		try:
			rpc = json.dumps(self.getRpc())
			logger.debug2(u"jsonrpc: {0!r}", rpc)

			response = self.jsonrpcBackend._request(baseUrl=self.baseUrl, data=rpc, retry=self.retry)
			self.processResult(json.loads(response))
		except Exception as error:
			if self.method not in ('backend_exit', 'exit'):
				logger.logException("Failed to process method '%s': %s" % (self.method, forceUnicode(error)), LOG_INFO)
				self.error = error
		finally:
			self._gotResult()


class JSONRPCThread(JSONRPC, threading.Thread):
	def __init__(self, jsonrpcBackend, baseUrl, method, params=None, retry=True, callback=None):
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
		logger.debug(u'Adding jsonrpc %s to queue (current queue size: %d)' % (jsonrpc, self.queue.qsize()))
		self.queue.put(jsonrpc, block=True)
		logger.debug2(u'Added jsonrpc %s to queue' % jsonrpc)

	def stop(self):
		self.stopped = True

	def run(self):
		logger.debug(u"RpcQueue started")
		self.idle.set()
		while not self.stopped or not self.queue.empty():
			self.idle.wait()
			jsonrpcs = []
			while not self.queue.empty():
				self.idle.clear()
				try:
					jsonrpc = self.queue.get(block=False)
					if jsonrpc:
						logger.debug(u'Got jsonrpc %s from queue' % jsonrpc)
						jsonrpcs.append(jsonrpc)
						if len(jsonrpcs) >= self.size:
							break
				except Empty:
					break
			if jsonrpcs:
				self.process(jsonrpcs=jsonrpcs)
			time.sleep(self.poll)
		logger.debug(u"RpcQueue stopped (empty: %s, stopped: %s)" % (self.queue.empty(), self.stopped))

	def process(self, jsonrpcs):
		self.jsonrpcs = {}
		for jsonrpc in forceList(jsonrpcs):
			self.jsonrpcs[jsonrpc.id] = jsonrpc
		if not self.jsonrpcs:
			return
		logger.info("Executing bunched jsonrpcs: %s" % self.jsonrpcs)
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
					raise OpsiRpcError(u"Can't execute jsonrpcs with different base urls at once: (%s != %s)" % (baseUrl, jsonrpc.baseUrl))
				rpc.append(jsonrpc.getRpc())
			rpc = json.dumps(rpc)
			logger.debug2(u"jsonrpc: %s" % rpc)

			response = self.jsonrpcBackend._request(baseUrl=baseUrl, data=rpc, retry=retry)
			logger.debug(u"Got response from host %s" % self.jsonrpcBackend._host)
			try:
				response = forceList(json.loads(response))
			except Exception as error:
				raise OpsiRpcError(u"Failed to json decode response %s: %s" % (response, error))

			for resp in response:
				try:
					responseId = resp['id']
				except KeyError as error:
					raise KeyError(u"Failed to get id from: %s (%s): %s" % (resp, response, error))

				try:
					jsonrpc = self.jsonrpcs[responseId]
				except KeyError as error:
					raise KeyError(u"Failed to get jsonrpc with id %s: %s" % (responseId, error))

				try:
					jsonrpc.processResult(resp)
				except Exception as error:
					raise RuntimeError(u"Failed to process response %s with jsonrpc %s: %s" % (resp, jsonrpc, error))
		except Exception as error:
			if not isExit:
				logger.logException(error)

			for jsonrpc in self.jsonrpcs.values():
				jsonrpc.error = error
				jsonrpc._gotResult()

		self.jsonrpcs = {}
		self.idle.set()


class JSONRPCBackend(Backend):

	def __init__(self, address, **kwargs):
		self._name = 'jsonrpc'

		Backend.__init__(self, **kwargs)

		self._application = 'opsi jsonrpc module version %s' % __version__
		self._sessionId = None
		self._deflate = False
		self._connectOnInit = True
		self._connected = False
		self._retryTime = 5
		self._defaultHttpPort = 4444
		self._defaultHttpsPort = 4447
		self._host = None
		self._port = None
		self._baseUrl = u'/rpc'
		self._protocol = 'https'
		self._socketTimeout = None
		self._connectTimeout = 30
		self._connectionPoolSize = 2
		self._interface = None
		self._rpcId = 0
		self._rpcIdLock = threading.Lock()
		self._async = False
		self._rpcQueue = None
		self._rpcQueuePollingTime = 0.01
		self._rpcQueueSize = 10
		self._serverCertFile = None
		self._caCertFile = None
		self._verifyServerCert = False
		self._verifyServerCertByCa = False
		self._verifyByCaCertsFile = None
		self._proxyURL = None

		if not self._username:
			self._username = u''
		if not self._password:
			self._password = u''

		retry = True
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'application':
				self._application = str(value)
			elif option == 'sessionid':
				self._sessionId = str(value)
			elif option == 'deflate':
				self._deflate = forceBool(value)
			elif option == 'connectoninit':
				self._connectOnInit = forceBool(value)
			elif option == 'connecttimeout' and value is not None:
				self._connectTimeout = forceInt(value)
			elif option == 'connectionpoolsize' and value is not None:
				self._connectionPoolSize = forceInt(value)
			elif option in ('timeout', 'sockettimeout') and value is not None:
				self._socketTimeout = forceInt(value)
			elif option == 'retry':
				retry = forceBool(value)
			elif option == 'retrytime':
				self._retryTime = forceInt(value)
			elif option == 'rpcqueuepollingtime':
				self._rpcQueuePollingTime = forceFloat(value)
			elif option == 'rpcqueuesize':
				self._rpcQueueSize = forceInt(value)
			elif option == 'servercertfile' and value is not None:
				self._serverCertFile = forceFilename(value)
			elif option == 'verifyservercert':
				self._verifyServerCert = forceBool(value)
			elif option == 'cacertfile' and value is not None:
				self._caCertFile = forceFilename(value)
			elif option == 'verifyservercertbyca':
				self._verifyServerCertByCa = forceBool(value)
			elif option == 'proxyurl' and value is not None:
				logger.debug(u"ProxyURL detected: '%s'" % value)
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
			serverCertFile=self._serverCertFile,
			caCertFile=self._caCertFile,
			verifyServerCertByCa=self._verifyServerCertByCa,
			proxyURL=self._proxyURL
		)

		if self._connectOnInit:
			self.connect()

	def stopRpcQueue(self):
		if self._rpcQueue:
			self._rpcQueue.stop()
			self._rpcQueue.join(20)

	def startRpcQueue(self):
		if not self._rpcQueue or not self._rpcQueue.is_alive():
			self._rpcQueue = RpcQueue(
				jsonrpcBackend=self,
				size=self._rpcQueueSize,
				poll=self._rpcQueuePollingTime
			)
			self._rpcQueue.start()

	def __del__(self):
		self.stopRpcQueue()
		if self._connectionPool:
			self._connectionPool.free()

	def getPeerCertificate(self, asPem=False):
		return self._connectionPool.getPeerCertificate(asPem)

	def backend_exit(self):
		if self._connected:
			try:
				self._jsonRPC('backend_exit', retry=False)
			except Exception:
				pass

		self.stopRpcQueue()

	def setAsync(self, enableAsync):
		if not self._connected:
			raise OpsiConnectionError(u'Not connected')

		if enableAsync:
			self.startRpcQueue()
			self._async = True
		else:
			self._async = False
			self.stopRpcQueue()

	def setDeflate(self, deflate):
		if not self._connected:
			raise OpsiConnectionError(u'Not connected')

		self._deflate = forceBool(deflate)

	def getDeflate(self):
		return self._deflate

	def isConnected(self):
		return self._connected

	def connect(self):
		modules = None
		realmodules = {}
		mysqlBackend = False

		asyncStatus = self._async
		self._async = False

		try:
			try:
				self._interface = self._jsonRPC(u'backend_getInterface')
				if 'opsiclientd' in self._application:
					try:
						backendInfo = self._jsonRPC(u'backend_info')
						modules = backendInfo.get('modules', None)
						realmodules = backendInfo.get('realmodules', None)
						if modules:
							logger.confidential(u"Modules: %s" % modules)
						else:
							modules = {'customer': None}

						for m in self._interface:
							if m.get('name') == 'dispatcher_getConfig':
								for entry in self._jsonRPC(u'dispatcher_getConfig'):
									for bn in entry[1]:
										if "sql" in bn.lower() and len(entry[0]) <= 4 and '*' in entry[0]:
											mysqlBackend = True
								break
					except Exception as error:
						logger.info(forceUnicode(error))
			except (OpsiAuthenticationError, OpsiTimeoutError, OpsiServiceVerificationError, socket.error) as connectionError:
				logger.debug(u"Failed to connect: {0}", connectionError)
				raise

			self._createInstanceMethods(modules, realmodules, mysqlBackend)

			self._connected = True
			logger.info(u"{0}: Connected to service", self)
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
				raise ValueError(u"Protocol %s not supported" % scheme)
			self._protocol = scheme
		self._host = host
		if port:
			self._port = port
		elif self._protocol == 'https':
			self._port = self._defaultHttpsPort
		else:
			self._port = self._defaultHttpPort
		if baseurl and (baseurl != '/'):
			self._baseUrl = baseurl
		if not self._username and username:
			self._username = username
		if not self._password and password:
			self._password = password

	def jsonrpc_getSessionId(self):
		return self._sessionId

	def _createInstanceMethods(self, modules=None, realmodules={}, mysqlBackend=False):
		licenseManagementModule = True
		if modules:
			licenseManagementModule = False
			if not modules.get('customer'):
				logger.notice(u"Disabling mysql backend and license management module: no customer in modules file")
				if mysqlBackend:
					raise OpsiError(u"MySQL backend in use but not licensed")

			elif not modules.get('valid'):
				logger.notice(u"Disabling mysql backend and license management module: modules file invalid")
				if mysqlBackend:
					raise OpsiError(u"MySQL backend in use but not licensed")

			elif (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
				logger.notice(u"Disabling mysql backend and license management module: modules file expired")
				if mysqlBackend:
					raise OpsiError(u"MySQL backend in use but not licensed")
			else:
				logger.info(u"Verifying modules file signature")
				publicKey = keys.Key.fromString(data=base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
				data = u''
				mks = list(modules.keys())
				mks.sort()
				for module in mks:
					if module in ('valid', 'signature'):
						continue

					if module in realmodules:
						val = realmodules[module]
						if int(val) > 0:
							modules[module] = True
					else:
						val = modules[module]
						if val is False:
							val = 'no'
						if val is True:
							val = 'yes'
					data += u'%s = %s\r\n' % (module.lower().strip(), val)
				if not bool(publicKey.verify(md5(data).digest(), [int(modules['signature'])])):
					logger.error(u"Disabling mysql backend and license management module: modules file invalid")
					if mysqlBackend:
						raise OpsiError(u"MySQL backend in use but not licensed")
				else:
					logger.info(u"Modules file signature verified (customer: %s)" % modules.get('customer'))

					if modules.get('license_management'):
						licenseManagementModule = True

					if mysqlBackend and not modules.get('mysql_backend'):
						raise OpsiError(u"MySQL backend in use but not licensed")

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
						# TODO: watch out for Python 3
						if isinstance(default, (str, unicode)):
							default = u"{0!r}".format(default).replace('"', "'")
						argString.append(u'{0}={1}'.format(argument, unicode(default)))
					else:
						argString.append(argument)
					callString.append(argument)

				if varargs:
					for vararg in varargs:
						argString.append(u'*{0}'.format(vararg))
						callString.append(vararg)

				if keywords:
					argString.append(u'**{0}'.format(keywords))
					callString.append(keywords)

				argString = u', '.join(argString)
				callString = u', '.join(callString)

				logger.debug2(u"{1}: arg string is: {0!r}", argString, methodName)
				logger.debug2(u"{1}: call string is: {0!r}", callString, methodName)
				# This would result in not overwriting Backend methods like log_read, log_write, ...
				# if getattr(self, methodName, None) is None:
				if not licenseManagementModule and "license" in methodName:
					exec(u'def %s(self, %s): return' % (methodName, argString))
				else:
					exec(u'def %s(self, %s): return self._jsonRPC("%s", [%s])' % (methodName, argString, methodName, callString))
				setattr(self, methodName, types.MethodType(eval(methodName), self))
			except Exception as error:
				logger.critical(u"Failed to create instance method '%s': %s" % (method, error))

	def _jsonRPC(self, method, params=[], retry=True):
		if self._async:
			self.startRpcQueue()
			jsonrpc = JSONRPC(jsonrpcBackend=self, baseUrl=self._baseUrl, method=method, params=params, retry=retry)
			self._rpcQueue.add(jsonrpc)
			return jsonrpc
		else:
			jsonrpc = JSONRPCThread(jsonrpcBackend=self, baseUrl=self._baseUrl, method=method, params=params, retry=retry)
			return jsonrpc.execute()

	def _request(self, baseUrl, data, retry=True):
		headers = {
			'user-agent': self._application,
			'Accept': 'application/json, text/plain',
			'Accept-Encoding': 'deflate, gzip',
			'content-type': 'application/json',
		}
		if isinstance(data, str):
			data = unicode(data, 'utf-8')
		data = data.encode('utf-8')

		logger.debug2(u"Request to host {0!r}, baseUrl: {1!r}, query: {2!r}".format(self._host, baseUrl, data))

		if self._deflate:
			logger.debug2(u"Compressing data")
			headers['Content-Encoding'] = 'deflate'

			data = deflateEncode(data)
			# Fix for python 2.7
			# http://bugs.python.org/issue12398
			if version_info >= (2, 7):
				data = bytearray(data)
			logger.debug2(u"Data compressed.")

		headers['content-length'] = len(data)

		auth = (self._username + u':' + self._password).encode('latin-1')
		headers['Authorization'] = 'Basic ' + base64.b64encode(auth)

		if self._sessionId:
			headers['Cookie'] = self._sessionId

		logger.debug("Posting request...")
		response = self._connectionPool.urlopen(method='POST', url=baseUrl, body=data, headers=headers, retry=retry)

		return self._processResponse(response)

	def _processResponse(self, response):
		logger.debug2("Processing response...")
		# Get cookie from header
		cookie = response.getheader('set-cookie', None)
		if cookie:
			# Store sessionId cookie
			sessionId = cookie.split(';')[0].strip()
			if sessionId != self._sessionId:
				self._sessionId = sessionId

		contentEncoding = response.getheader('content-encoding', '').lower()
		logger.debug2(u"Content-Encoding: {1}", contentEncoding)

		response = response.data
		if contentEncoding == 'gzip':
			logger.debug(u"Expecting gzip'ed data from server")
			response = gzipDecode(response)
		elif contentEncoding == "deflate":
			logger.debug(u"Expecting deflated data from server")
			response = deflateDecode(response)

		logger.debug2(u"Response is: {0}", response)
		return response

	def getInterface(self):
		return self.backend_getInterface()

	def backend_getInterface(self):
		return self._interface

	def __repr__(self):
		if self._name:
			return u'<{0}(address={1!r}, host={2!r}, deflate={3!r})>'.format(self.__class__.__name__, self._name, self._host, self._deflate)
		else:
			return u'<{0}(host={1!r}, deflate={2!r})>'.format(self.__class__.__name__, self._host, self._deflate)