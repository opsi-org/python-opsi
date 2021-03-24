# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import re
import types
import threading
from urllib.parse import urlparse
import gzip
import requests
import msgpack
try:
	import orjson as json
except ImportError:
	import json
import lz4.frame

#from OPSI.Backend import no_export
from OPSI.Backend.Base import Backend
from OPSI.Util import serialize, deserialize
from OPSI.Exceptions import OpsiRpcError

from opsicommon import __version__
from opsicommon.logging import logger, secret_filter


_GZIP_COMPRESSION = 'gzip'
_LZ4_COMPRESSION = 'lz4'
_DEFAULT_HTTP_PORT = 4444
_DEFAULT_HTTPS_PORT = 4447

class JSONRPCBackend(Backend):  # pylint: disable=too-many-instance-attributes

	def __init__(self, address, **kwargs):  # pylint: disable=too-many-branches,too-many-statements
		"""
		Backend for JSON-RPC access to another opsi service.

		:param compression: Should requests be compressed?
		:type compression: bool
		"""

		self._name = 'jsonrpc'

		Backend.__init__(self, **kwargs)

		self._application = 'opsi-jsonrpc-backend/%s' % __version__
		#self._session_id = None
		self._compression = False
		self._connect_on_init = True
		self._connected = False
		self._retry_time = 5
		#self._host = None
		#self._port = None
		#self._baseUrl = '/rpc'
		#self._protocol = 'https'
		#self._socketTimeout = None
		#self._connectTimeout = 30
		#self._connectionPool = None
		#self._connectionPoolSize = 2
		self._interface = None
		self._rpc_id = 0
		self._rpc_id_lock = threading.Lock()
		#self._async = False
		#self._rpcQueue = None
		#self._rpcQueuePollingTime = 0.01
		#self._rpcQueueSize = 10
		self._ca_cert_file = None
		self._verify_server_cert = False
		self._proxy_url = None
		self.server_name = None
		self._base_url = None
		self._username = None
		self._password = None
		self._serialization = "json"


		#retry = True
		session_id = None
		for option, value in kwargs.items():
			option = option.lower()
			if option == 'application':
				self._application = str(value)
			elif option == 'sessionid':
				session_id = str(value)
			elif option == 'compression':
				if isinstance(value, bool):
					self._compression = value
				else:
					value = str(value).strip().lower()
					if value in ('true', 'false'):
						self._compression = value == "true"
					elif value == _GZIP_COMPRESSION:
						self._compression = _GZIP_COMPRESSION
					elif value == _LZ4_COMPRESSION:
						self._compression = _LZ4_COMPRESSION
			elif option == 'connectoninit':
				self._connectOnInit = bool(value)
			elif option == 'connecttimeout' and value not in (None, ""):
				self._connectTimeout = int(value)
			#elif option == 'connectionpoolsize' and value not in (None, ""):
			#	self._connectionPoolSize = int(value)
			elif option in ('timeout', 'sockettimeout') and value not in (None, ""):
				self._socket_timeout = int(value)
			#elif option == 'retry':
			#	retry = bool(value)
			elif option == 'retrytime':
				self._retry_time = int(value)
			#elif option == 'rpcqueuepollingtime':
			#	self._rpcQueuePollingTime = forceFloat(value)
			#elif option == 'rpcqueuesize':
			#	self._rpcQueueSize = forceInt(value)
			elif option == 'verifyservercert':
				self._verify_server_cert = bool(value)
			elif option == 'cacertfile' and value not in (None, ""):
				self._ca_cert_file = str(value)
			elif option == 'proxyurl' and value not in (None, ""):
				self._proxy_url = str(value)
			elif option == 'serialization' and value not in (None, ""):
				if value in ("json", "msgpack"):
					self._serialization = value
				else:
					logger.error("Invalid serialization '%s', using %s", value, self._serialization)

		#if not retry:
		#	self._retryTime = 0

		if self._password:
			secret_filter.add_secrets(self._password)

		"""
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
		"""
		self._set_address(address)

		self._session = requests.Session()
		self._session.auth = (self._username, self._password)
		self._session.headers.update({
			'User-Agent': self._application
		})
		if session_id:
			cookie_name, cookie_value = session_id.split("=")
			self._session.cookies.set(
				cookie_name, cookie_value, domain=urlparse(self._base_url).hostname
			)

		if self._connect_on_init:
			self._connect()

	@property
	def server_version(self):
		try:
			if self.server_name:
				match = re.search(r"^opsi\D+(\d+\.\d+\.\d+\.\d+)", self.server_name)
				if match:
					return [int(v) for v in match.group(1).split('.')]
		except Exception as err:  # pylint: disable=broad-except
			logger.warning("Failed to parse server version '%s': %s", self.server_name, err)
		return None

	serverVersion = server_version

	def _set_address(self, address):
		url = urlparse(address)
		if url.scheme not in ('http', 'https'):
			raise ValueError(f"Protocol {url.scheme} not supported")

		port = url.port
		if not port:
			port = _DEFAULT_HTTP_PORT if url.scheme == "http" else _DEFAULT_HTTPS_PORT

		path = url.path
		if not path or path == "/":
			path = "/rpc"

		self._base_url = f"{url.scheme}://{url.hostname}:{port}{path}"
		self._username = url.username
		self._password = url.password


	def _execute_rpc(self, method, params=None):  # pylint: disable=too-many-branches,too-many-statements
		params = params or []

		rpc_id = 0
		with self._rpc_id_lock:
			self._rpc_id += 1
			rpc_id = self._rpc_id

		headers = {
			'Accept-Encoding': 'gzip, lz4'
		}

		data = {
			"jsonrpc": "2.0",
			"id": rpc_id,
			"method": method,
			"params": serialize(params)
		}

		if self._serialization == "msgpack":
			headers['Accept'] = headers['Content-Type'] = 'application/msgpack'
			data = msgpack.dumps(data)
		else:
			headers['Accept'] = headers['Content-Type'] = 'application/json'
			data = json.dumps(data)

		if self._compression:
			compression = self._compression
			if compression is True:
				# Auto choose later by server version
				# opsiconfd 4.2.0.96 (uvicorn)
				compression = _GZIP_COMPRESSION
				sv = self.server_version
				if sv and (sv[0] > 4 or (sv[0] == 4 and sv[1] > 1)):
					compression = _LZ4_COMPRESSION

			if compression == _LZ4_COMPRESSION:
				logger.trace("Compressing data with lz4")
				headers['Content-Encoding'] = 'lz4'
				headers['Accept-Encoding'] = 'lz4'
				data = lz4.frame.compress(data, compression_level=0, block_linked=True)
			else:
				logger.trace("Compressing data with gzip")
				headers['Content-Encoding'] = 'gzip'
				headers['Accept-Encoding'] = 'gzip'
				data = gzip.compress(data)

		logger.debug("JSONRPC request to %s: id=%d, method=%s", self._base_url, rpc_id, method)
		response = self._session.post(self._base_url, headers=headers, data=data)
		content_type = response.headers.get("content-type", "")
		content_encoding = response.headers.get("content-encoding", "")
		logger.debug(
			"Got response status=%s, Content-Type=%s, Content-Encoding=%s",
			response.status_code, content_type, content_encoding
		)

		data = response.content
		if "lz4" in content_encoding:
			logger.trace("Decompressing data with lz4")
			data = lz4.frame.decompress(data)
		elif "gzip" in content_encoding:
			logger.trace("Decompressing data with gzip")
			data = gzip.decompress(data)

		if content_type == "application/msgpack":
			data = msgpack.loads(data)
		else:
			data = json.loads(data)

		if data.get('error'):
			logger.debug('Result from RPC contained error!')
			error = data['error']
			# Error occurred
			if isinstance(error, dict) and error.get('message'):
				message = error['message']
				#try:
				#	exception_class = eval(error.get('class', 'Exception'))  # pylint: disable=eval-used
				#	exception = exceptionClass(f"{message} (error on server)")
				#except Exception:  # pylint: disable=broad-except
				#	exception = OpsiRpcError(message)
				raise OpsiRpcError(f"{message} (error on server)")
			raise OpsiRpcError(f'{error} (error on server)')

		data = deserialize(
			data.get('result'),
			preventObjectCreation=method.endswith('_getHashes')
		)

		return data

	def _create_instance_methods(self):
		for method in self._interface:
			try:
				method_name = method['name']

				if method_name in ('backend_exit', 'backend_getInterface'):
					continue

				args = method['args']
				varargs = method['varargs']
				keywords = method['keywords']
				defaults = method['defaults']

				arg_string = []
				call_string = []
				for i, argument in enumerate(args):
					if argument == 'self':
						continue

					if isinstance(defaults, (tuple, list)) and len(defaults) + i >= len(args):
						default = defaults[len(defaults) - len(args) + i]
						if isinstance(default, str):
							default = "{0!r}".format(default).replace('"', "'")
						arg_string.append(f'{argument}={default}')
					else:
						arg_string.append(argument)
					call_string.append(argument)

				if varargs:
					for vararg in varargs:
						arg_string.append(f'*{vararg}')
						call_string.append(vararg)

				if keywords:
					arg_string.append(f'**{keywords}')
					call_string.append(keywords)

				arg_string = ', '.join(arg_string)
				call_string = ', '.join(call_string)

				logger.trace("%s: arg string is: %s", method_name, arg_string)
				logger.trace("%s: call string is: %s", method_name, call_string)
				exec(f'def {method_name}(self, {arg_string}): return self._execute_rpc("{method_name}", [{call_string}])')  # pylint: disable=exec-used
				setattr(self, method_name, types.MethodType(eval(method_name), self))  # pylint: disable=eval-used
			except Exception as err:  # pylint: disable=broad-except
				logger.critical("Failed to create instance method '%s': %s", method, err)

	def _connect(self):
		logger.devel("Connecting to service %s", self._base_url)
		self._interface = self._execute_rpc('backend_getInterface')
		self._create_instance_methods()
		logger.info("Connected to service %s", self._base_url)
		self._connected = True

	def backend_exit(self):
		if self._connected:
			try:
				self._execute_rpc('backend_exit')###################, retry=False)
			except Exception:  # pylint: disable=broad-except
				pass
