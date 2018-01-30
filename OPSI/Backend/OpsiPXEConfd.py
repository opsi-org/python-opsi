# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2018 uib GmbH <info@uib.de>
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
OpsiPXEConfd-Backend

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import socket
import threading
import time
from contextlib import closing, contextmanager

from OPSI.Backend.Backend import ConfigDataBackend
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Exceptions import (BackendMissingDataError, BackendUnableToConnectError,
	BackendUnaccomplishableError)
from OPSI.Logger import Logger
from OPSI.Object import OpsiClient
from OPSI.Types import forceInt, forceUnicode, forceHostId
from OPSI.Util import getfqdn

__all__ = ('ServerConnection', 'OpsiPXEConfdBackend', 'createUnixSocket')

logger = Logger()


class ServerConnection:
	def __init__(self, port, timeout=10):
		self.port = port
		self.timeout = forceInt(timeout)

	def sendCommand(self, cmd):
		with createUnixSocket(self.port, timeout=self.timeout) as unixSocket:
			unixSocket.send(forceUnicode(cmd).encode('utf-8'))

			result = ''
			try:
				for part in iter(lambda: unixSocket.recv(4096), ''):
					logger.debug("Received {!r}", part)
					result += forceUnicode(part)
			except Exception as error:
				raise RuntimeError(u"Failed to receive: %s" % error)

		if result.startswith(u'(ERROR)'):
			raise RuntimeError(u"Command '%s' failed: %s" % (cmd, result))

		return result


@contextmanager
def createUnixSocket(port, timeout=5.0):
	logger.notice(u"Creating unix socket '%s'" % port)
	_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	_socket.settimeout(timeout)
	try:
		with closing(_socket) as unixSocket:
			unixSocket.connect(port)
			yield unixSocket
	except Exception as error:
		raise RuntimeError(u"Failed to connect to socket '%s': %s" % (port, error))


class OpsiPXEConfdBackend(ConfigDataBackend):

	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)

		self._name = 'opsipxeconfd'
		self._port = u'/var/run/opsipxeconfd/opsipxeconfd.socket'
		self._timeout = 10
		self._depotId = forceHostId(getfqdn())
		self._opsiHostKey = None
		self._depotConnections = {}
		self._updateThreads = {}
		self._updateThreadsLock = threading.Lock()
		self._parseArguments(kwargs)

	def _parseArguments(self, kwargs):
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'port':
				self._port = value
			elif option == 'timeout':
				self._timeout = forceInt(value)

	def _getDepotConnection(self, depotId):
		depotId = forceHostId(depotId)
		if depotId == self._depotId:
			return self

		try:
			return self._depotConnections[depotId]
		except KeyError:
			if not self._opsiHostKey:
				depots = self._context.host_getObjects(id=self._depotId)  # pylint: disable=maybe-no-member
				if not depots or not depots[0].getOpsiHostKey():
					raise BackendMissingDataError(u"Failed to get opsi host key for depot '%s'" % self._depotId)
				self._opsiHostKey = depots[0].getOpsiHostKey()

			try:
				self._depotConnections[depotId] = JSONRPCBackend(
					address=u'https://%s:4447/rpc/backend/%s' % (depotId, self._name),
					username=self._depotId,
					password=self._opsiHostKey
				)
			except Exception as error:
				raise BackendUnableToConnectError(u"Failed to connect to depot '%s': %s" % (depotId, error))

			return self._depotConnections[depotId]

	def _getResponsibleDepotId(self, clientId):
		configStates = self._context.configState_getObjects(configId=u'clientconfig.depot.id', objectId=clientId)  # pylint: disable=maybe-no-member
		if configStates and configStates[0].values:
			depotId = configStates[0].values[0]
		else:
			configs = self._context.config_getObjects(id=u'clientconfig.depot.id')  # pylint: disable=maybe-no-member
			if not configs or not configs[0].defaultValues:
				raise BackendUnaccomplishableError(u"Failed to get depotserver for client '%s', config 'clientconfig.depot.id' not set and no defaults found" % clientId)
			depotId = configs[0].defaultValues[0]
		return depotId

	def _pxeBootConfigurationUpdateNeeded(self, productOnClient):
		if productOnClient.productType != 'NetbootProduct':
			logger.debug(u"Not a netboot product: {0!r}, nothing to do", productOnClient.productId)
			return False

		if not productOnClient.actionRequest:
			logger.debug(u"No action request update for product {0!r}, client {1!r}, nothing to do", productOnClient.productId, productOnClient.clientId)
			return False

		return True

	def _updateByProductOnClient(self, productOnClient):
		if not self._pxeBootConfigurationUpdateNeeded(productOnClient):
			return

		depotId = self._getResponsibleDepotId(productOnClient.clientId)
		if depotId != self._depotId:
			logger.info(u"Not responsible for client '%s', forwarding request to depot '%s'" % (productOnClient.clientId, depotId))
			return self._getDepotConnection(depotId).opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId)

		self.opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId)

	def opsipxeconfd_updatePXEBootConfiguration(self, clientId):
		clientId = forceHostId(clientId)

		with self._updateThreadsLock:
			if clientId not in self._updateThreads:
				command = u'update %s' % clientId

				class UpdateThread(threading.Thread):
					def __init__(self, opsiPXEConfdBackend, clientId, command):
						threading.Thread.__init__(self)
						self._opsiPXEConfdBackend = opsiPXEConfdBackend
						self._clientId = clientId
						self._command = command
						self._updateEvent = threading.Event()
						self._delay = 3.0

					def run(self):
						while self._delay > 0:
							try:
								time.sleep(0.2)
							except Exception:
								pass
							self._delay -= 0.2

						with self._opsiPXEConfdBackend._updateThreadsLock:
							try:
								logger.info(u"Updating pxe boot configuration for client '%s'" % self._clientId)
								sc = ServerConnection(self._opsiPXEConfdBackend._port, self._opsiPXEConfdBackend._timeout)
								logger.info(u"Sending command '%s'" % self._command)
								result = sc.sendCommand(self._command)
								logger.info(u"Got result '%s'" % result)
							except Exception as error:
								logger.critical(u"Failed to update PXE boot configuration for client '%s': %s" % (self._clientId, error))

							del self._opsiPXEConfdBackend._updateThreads[self._clientId]

					def delay(self):
						self._delay = 3.0

				updater = UpdateThread(self, clientId, command)
				self._updateThreads[clientId] = updater
				updater.start()
			else:
				self._updateThreads[clientId].delay()

	def backend_exit(self):
		for connection in self._depotConnections.values():
			try:
				connection.backend_exit()
			except Exception:
				pass

		with self._updateThreadsLock:
			for updateThread in self._updateThreads.values():
				updateThread.join(5)

	def host_updateObject(self, host):
		if not isinstance(host, OpsiClient):
			return

		if not host.ipAddress and not host.hardwareAddress:
			# Not of interest
			return

		self.opsipxeconfd_updatePXEBootConfiguration(host.id)

	def productOnClient_insertObject(self, productOnClient):
		self._updateByProductOnClient(productOnClient)

	def productOnClient_updateObject(self, productOnClient):
		self._updateByProductOnClient(productOnClient)

	def productOnClient_deleteObjects(self, productOnClients):
		errors = []
		for productOnClient in productOnClients:
			try:
				self._updateByProductOnClient(productOnClient)
			except Exception as error:
				errors.append(forceUnicode(error))

		if errors:
			raise RuntimeError(u', '.join(errors))

	def configState_insertObject(self, configState):
		if configState.configId != 'clientconfig.depot.id':
			return

		self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)

	def configState_updateObject(self, configState):
		if configState.configId != 'clientconfig.depot.id':
			return

		self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)

	def configState_deleteObjects(self, configStates):
		errors = []
		for configState in configStates:
			if configState.configId != 'clientconfig.depot.id':
				continue

			try:
				self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)
			except Exception as error:
				errors.append(forceUnicode(error))

		if errors:
			raise RuntimeError(u', '.join(errors))
