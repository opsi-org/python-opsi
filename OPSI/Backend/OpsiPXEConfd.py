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

import codecs
import json
import os.path
import socket
import tempfile
import threading
import time
from contextlib import closing, contextmanager
from pipes import quote

from OPSI.Backend.Backend import ConfigDataBackend
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Exceptions import (BackendMissingDataError,
	BackendUnableToConnectError, BackendUnaccomplishableError)
from OPSI.Logger import LOG_DEBUG, Logger
from OPSI.Object import ConfigState, OpsiClient, ProductPropertyState
from OPSI.Types import forceHostId, forceInt, forceUnicode, forceUnicodeList
from OPSI.Util import getfqdn, serialize

__all__ = ('ServerConnection', 'OpsiPXEConfdBackend', 'createUnixSocket')

ERROR_MARKER = u'(ERROR)'

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
					logger.debug2("Received {!r}", part)
					result += forceUnicode(part)
			except Exception as error:
				raise RuntimeError(u"Failed to receive: %s" % error)

		if result.startswith(ERROR_MARKER):
			raise RuntimeError(u"Command '%s' failed: %s" % (cmd, result))

		return result


@contextmanager
def createUnixSocket(port, timeout=5.0):
	logger.notice(u"Creating unix socket {!r}", port)
	_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	_socket.settimeout(timeout)
	try:
		with closing(_socket) as unixSocket:
			unixSocket.connect(port)
			yield unixSocket
	except Exception as error:
		raise RuntimeError(u"Failed to connect to socket '%s': %s" % (port, error))


def getClientCacheFilePath(clientId):
	if os.path.exists('/var/run/opsipxeconfd'):
		directory = '/var/run/opsipxeconfd'
	else:
		directory = os.path.join(tempfile.gettempdir(), '.opsipxeconfd')
		try:
			os.makedirs(directory)
		except OSError:
			pass  # directory exists

	return os.path.join(directory, clientId + '.json')


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

	def _collectDataForUpdate(self, productOnClient, depotId):
		logger.debug("Collecting data for opsipxeconfd...")
		clientId = productOnClient.clientId

		try:
			try:
				host = self._context.host_getObjects(
					attributes=["hardwareAddress", "opsiHostKey", "ipAddress"],
					id=clientId
				)[0]
			except IndexError:
				logger.debug("No matching host found - fast exit.")
				return serialize({"host": None, "productOnClient": []})

			productOnClients = self._context.productOnClient_getObjects(
				productType=u'NetbootProduct',
				clientId=clientId,
				actionRequest=['setup', 'uninstall', 'update', 'always', 'once', 'custom']
			)
			try:
				productOnClient = productOnClients[0]
			except IndexError:
				logger.debug("No productOnClient found - fast exit.")
				return serialize({"host": host, "productOnClient": []})

			try:
				productOnDepot = self._context.productOnDepot_getObjects(
					productType=u'NetbootProduct',
					productId=productOnClient.productId,
					depotId=depotId
				)[0]
			except IndexError:
				logger.debug("No productOnDepot found - fast exit.")
				return serialize({
					"host": host,
					"productOnClient": productOnClient,
					"productOnDepot": None
				})

			product = self._context.product_getObjects(
				attributes=['id', 'pxeConfigTemplate'],
				type=u'NetbootProduct',
				id=productOnClient.productId,
				productVersion=productOnClient.productVersion,
				packageVersion=productOnClient.packageVersion
			)[0]

			eliloMode = None
			for configState in self._collectConfigStates(clientId):
				if configState.configId == u"clientconfig.configserver.url":
					serviceAddress = configState.getValues()[0]
				elif configState.configId == u'opsi-linux-bootimage.append':
					bootimageAppend = configState
				elif configState.configId == u"clientconfig.dhcpd.filename":
					try:
						value = configState.getValues()[0]
						if 'elilo' in value:
							if 'x86' in value:
								eliloMode = 'x86'
							else:
								eliloMode = 'x64'
					except IndexError:
						# If we land here there is no default value set
						# and no items are present.
						pass
					except Exception as eliloError:
						logger.debug("Failed to detect elilo setting for {}: {}", clientId, eliloError)

			productPropertyStates = self._collectProductPropertyStates(
				clientId,
				productOnClient.productId,
				depotId
			)
			logger.debug("Collected product property states: {}", productPropertyStates)

			backendinfo = self._context.backend_info()
			backendinfo["hostCount"] = len(self._context.host_getObjects(attributes=['id'], type='OpsiClient'))

			data = {
				"backendInfo": backendinfo,
				"host": host,
				"productOnClient": productOnClient,
				"depotId": depotId,
				"productOnDepot": productOnDepot,
				"elilo": eliloMode,
				"serviceAddress": serviceAddress,
				"product": product,
				"bootimageAppend": bootimageAppend,
				"productPropertyStates": productPropertyStates
			}

			data = serialize(data)
			logger.debug("Collected data of for opsipxeconfd: {!r}", clientId, data)
		except Exception as collectError:
			logger.logException(collectError)
			logger.warning("Failed to collect data of {} for opsipxeconfd: {}", clientId, collectError)
			data = {}

		return data

	def _collectConfigStates(self, clientId):
		configIds = [
			'opsi-linux-bootimage.append',
			"clientconfig.configserver.url",
			"clientconfig.dhcpd.filename",
		]

		configStates = self._context.configState_getObjects(
			objectId=clientId,
			configId=configIds
		)

		if len(configIds) == len(configStates):
			# We have a value set for each of our configIds - exiting.
			return configStates

		existingConfigStateIds = set(cs.configId for cs in configStates)
		missingConfigStateIds = set(configIds) - existingConfigStateIds

		# Create missing config states
		for config in self._context.config_getObjects(id=missingConfigStateIds):
			logger.debug(u"Got default values for {0!r}: {1}", config.id, config.defaultValues)
			# Config state does not exist for client => create default
			cf = ConfigState(
				configId=config.id,
				objectId=clientId,
				values=config.defaultValues
			)
			cf.setGeneratedDefault(True)
			configStates.append(cf)

		return configStates

	def _collectProductPropertyStates(self, clientId, productId, depotId):
		productPropertyStates = self._context.productPropertyState_getObjects(
			objectId=clientId,
			productId=productId
		)

		existingPropertyStatePropertyIds = set(pps.propertyId for pps in productPropertyStates)

		# Create missing product property states
		for pps in self._context.productPropertyState_getObjects(productId=productId, objectId=depotId):
			if pps.propertyId not in existingPropertyStatePropertyIds:
				# Product property for client does not exist => add default (values of depot)
				productPropertyStates.append(
					ProductPropertyState(
						productId=pps.productId,
						propertyId=pps.propertyId,
						objectId=clientId,
						values=pps.values
					)
				)

		return {
			pps.propertyId: u','.join(forceUnicodeList(pps.getValues()))
			for pps
			in productPropertyStates
		}

	def _updateByProductOnClient(self, productOnClient):
		if not self._pxeBootConfigurationUpdateNeeded(productOnClient):
			return

		destinationSupportsCachedData = True
		depotId = self._getResponsibleDepotId(productOnClient.clientId)
		if depotId != self._depotId:
			logger.info(u"Not responsible for client '{}', forwarding request to depot {!r}", productOnClient.clientId, depotId)
			destination = self._getDepotConnection(depotId)

			for method in destination.backend_getInterface():
				if method['name'] == 'opsipxeconfd_updatePXEBootConfiguration':
					if len(method['params']) < 2:
						destinationSupportsCachedData = False
						logger.debug("Depot {} does not support receiving cached data.", depotId)

					break
		else:
			destination = self

		if destinationSupportsCachedData:
			data = self._collectDataForUpdate(productOnClient, depotId)
			destination.opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId, data)
		else:
			destination.opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId)

	def opsipxeconfd_updatePXEBootConfiguration(self, clientId, data=None):
		"""
		Update the boot configuration of a specific client.
		This method will relay calls to opsipxeconfd who does the handling.

		:param clientId: The client whose boot configuration should be updated.
		:type clientId: str
		:param data: Collected data for opsipxeconfd.
		:type data: dict
		"""
		clientId = forceHostId(clientId)
		logger.debug("Updating PXE boot config of {!r}", clientId)

		command = 'update {}'.format(clientId)
		if data:
			cacheFilePath = self._cacheOpsiPXEConfdData(clientId, data)
			if cacheFilePath:
				command = 'update {} {}'.format(clientId, quote(cacheFilePath))

		with self._updateThreadsLock:
			if clientId not in self._updateThreads:
				updater = UpdateThread(self, clientId, command)
				self._updateThreads[clientId] = updater
				updater.start()
			else:
				self._updateThreads[clientId].delay()

	@staticmethod
	def _cacheOpsiPXEConfdData(clientId, data):
		"""
		Save data used by opsipxeconfd to a cache file.

		:param clientId: The client for whom this data is.
		:type clientId: str
		:param data: Collected data for opsipxeconfd.
		:type data: dict
		:rtype: str
		:returns: The path of the cache file. None if no file could be written.
		"""
		destinationFile = getClientCacheFilePath(clientId)
		logger.debug2("Writing data to {}: {!r}", destinationFile, data)
		try:
			with codecs.open(destinationFile, "w", 'utf-8') as outfile:
				json.dump(serialize(data), outfile)
			os.chmod(destinationFile, 0o640)
			return destinationFile
		except (OSError, IOError) as dataFileError:
			logger.logException(dataFileError, logLevel=LOG_DEBUG)
			logger.debug("Writing cache file {!r} failed: {!r}", destinationFile, dataFileError)

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
		hosts = set(configState.objectId for configState
					in configStates
					if configState.configId == 'clientconfig.depot.id')

		errors = []
		for host in hosts:
			try:
				self.opsipxeconfd_updatePXEBootConfiguration(host)
			except Exception as error:
				errors.append(forceUnicode(error))

		if errors:
			raise RuntimeError(u', '.join(errors))


class UpdateThread(threading.Thread):
	_DEFAULT_DELAY = 3.0

	def __init__(self, opsiPXEConfdBackend, clientId, command):
		threading.Thread.__init__(self)
		self._opsiPXEConfdBackend = opsiPXEConfdBackend
		self._clientId = clientId
		self._command = command
		self._delay = self._DEFAULT_DELAY

	def run(self):
		logger.debug("UpdateThread {} waiting until delay is done...", self.name)
		delayReduction = 0.2
		while self._delay > 0:
			time.sleep(delayReduction)
			self._delay -= delayReduction

		with self._opsiPXEConfdBackend._updateThreadsLock:
			try:
				logger.info(u"Updating pxe boot configuration for client '{}'", self._clientId)
				sc = ServerConnection(self._opsiPXEConfdBackend._port, self._opsiPXEConfdBackend._timeout)
				logger.debug(u"Sending command {!r}", self._command)
				result = sc.sendCommand(self._command)
				logger.debug(u"Got result {!r}", result)
			except Exception as error:
				logger.critical(u"Failed to update PXE boot configuration for client '{}': {}", self._clientId, error)
			finally:
				del self._opsiPXEConfdBackend._updateThreads[self._clientId]

	def delay(self):
		self._delay = self._DEFAULT_DELAY
		logger.debug("Resetted delay for UpdateThread {}", self.name)
