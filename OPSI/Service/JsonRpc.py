# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2010-2018 uib GmbH

# http://www.uib.de/

# All rights reserved.

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
Support for JSON-RPC.

Information about the JSON-RPC standard can be found at
http://www.jsonrpc.org/specification

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import sys
import time
import traceback

from OPSI.Exceptions import OpsiBadRpcError, OpsiRpcError
from OPSI.Logger import Logger, LOG_INFO
from OPSI.Types import forceUnicode
from OPSI.Util import deserialize


logger = Logger()


class JsonRpc(object):
	def __init__(self, instance, interface, rpc):
		self._instance = instance
		self._interface = interface
		self.started = None
		self.ended = None
		self.type = rpc.get('type')
		self.rpcVersion = rpc.get('jsonrpc', None)
		self.tid = rpc.get('tid', rpc.get('id'))
		self.action = rpc.get('action')
		self.method = rpc.get('method')
		self.params = rpc.get('params', rpc.get('data')) or []
		self.result = None
		self.exception = None
		self.traceback = None

		if not self.tid:
			raise OpsiBadRpcError(u"No transaction id ((t)id) found in rpc")

		if not self.method:
			raise OpsiBadRpcError(u"No method found in rpc")

	def isStarted(self):
		return bool(self.started)

	def hasEnded(self):
		return bool(self.ended)

	def getMethodName(self):
		if self.action:
			return u'%s_%s' % (self.action, self.method)

		return self.method

	def getDuration(self):
		if not self.started or not self.ended:
			return None

		return round(self.ended - self.started, 3)

	def execute(self, result=None):
		self.result = None
		params = [param for param in self.params]
		self.started = time.time()

		try:
			methodInterface = None
			for m in self._interface:
				if self.getMethodName() == m['name']:
					methodInterface = m
					break

			if not methodInterface:
				raise OpsiRpcError(u"Method '%s' is not valid" % self.getMethodName())

			keywords = {}
			if methodInterface['keywords']:
				parameterCount = 0
				if methodInterface['args']:
					parameterCount += len(methodInterface['args'])
				if methodInterface['varargs']:
					parameterCount += len(methodInterface['varargs'])

				if len(params) >= parameterCount:
					kwargs = params.pop(-1)
					if not isinstance(kwargs, dict):
						raise TypeError(u"kwargs param is not a dict: %s" % params[-1])

					for (key, value) in kwargs.items():
						keywords[str(key)] = deserialize(value)

				del parameterCount

			params = deserialize(params)

			pString = forceUnicode(params)[1:-1]
			if keywords:
				pString = u'{0}, {1}'.format(pString, forceUnicode(keywords))

			if len(pString) > 200:
				pString = u'{0}...'.format(pString[:200])

			logger.notice(u"-----> Executing: %s(%s)" % (self.getMethodName(), pString))

			instance = self._instance
			if keywords:
				self.result = eval("instance.%s(*params, **keywords)" % self.getMethodName())
			else:
				self.result = eval("instance.%s(*params)" % self.getMethodName())

			logger.info(u'Got result')
			logger.debug2("RPC ID {0}: {1!r}", self.tid, self.result)
		except Exception as error:
			logger.logException(error, LOG_INFO)
			logger.error(u'Execution error: %s' % forceUnicode(error))
			self.exception = error
			self.traceback = []
			try:
				for tbInfo in traceback.format_tb(sys.exc_info()[2]):
					self.traceback.append(tbInfo)
			except AttributeError as attre:
				message = u"Failed to collect traceback: {0}".format(attre)
				logger.warning(message)
				self.traceback.append(message)
		finally:
			self.ended = time.time()

	def getResponse(self):
		response = {}
		if self.type == 'rpc':
			response['tid'] = self.tid
			response['action'] = self.action
			response['method'] = self.method
			if self.exception:
				response['type'] = 'exception'
				response['message'] = {
					'class': self.exception.__class__.__name__,
					'message': forceUnicode(self.exception)
				}
				response['where'] = self.traceback
			else:
				response['type'] = 'rpc'
				response['result'] = self.result
		else:
			response['id'] = self.tid
			if self.rpcVersion == '2.0':
				response['jsonrpc'] = '2.0'

			if self.exception:
				if self.rpcVersion == '2.0':
					try:
						code = int(getattr(self.exception, 'errno'))
					except Exception:
						code = 0

					response['error'] = {
						'code': code,
						'message': forceUnicode(self.exception),
						'data': {'class': self.exception.__class__.__name__}
					}
				else:
					response['error'] = {
						'class': self.exception.__class__.__name__,
						'message': forceUnicode(self.exception)
					}

				if self.rpcVersion != '2.0':  # TODO: das macht keinen Sinn!
					response['result'] = None
			else:
				if self.rpcVersion != '2.0':
					response['error'] = None
				response['result'] = self.result

		return response

	def __getstate__(self):
		state = self.__dict__
		state['_instance'] = None
		state['_interface'] = None
		return state
