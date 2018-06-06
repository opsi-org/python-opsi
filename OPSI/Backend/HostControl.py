# -*- coding: utf-8 -*-

# This file is part of python-opsi.
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
HostControl backend.

This backend can be used to control hosts.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import socket
import struct
import time

from contextlib import closing

try:
	from httplib import HTTPSConnection
except ImportError:
	# Python 3 compatibility
	from http.client import HTTPSConnection

from OPSI.Backend.Base import ExtendedBackend
from OPSI.Exceptions import BackendMissingDataError, BackendUnaccomplishableError
from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Types import (forceBool, forceDict, forceHostId, forceHostIdList,
						forceInt, forceIpAddress, forceList, forceUnicode,
						forceUnicodeList)
from OPSI.Util import fromJson, toJson
from OPSI.Util.HTTP import closingConnection, non_blocking_connect_https
from OPSI.Util.Thread import KillableThread

__all__ = ('RpcThread', 'ConnectionThread', 'HostControlBackend')

logger = Logger()


def _configureHostcontrolBackend(backend, kwargs):
	"""
	Configure `backend` to the values given in `kwargs`.

	Keys in `kwargs` will be treated as lowercase.
	Supported keys are 'broadcastaddresses', 'hostrpctimeout', \
'maxconnections' opsiclientdport' and 'resolvehostaddress'.
	Unrecognized options will be ignored.

	:type backend: HostControlBackend or HostControlSafeBackend
	:type kwargs: dict
	"""
	for option, value in kwargs.items():
		option = option.lower()
		if option == 'opsiclientdport':
			backend._opsiclientdPort = forceInt(value)
		elif option == 'hostrpctimeout':
			backend._hostRpcTimeout = forceInt(value)
		elif option == 'resolvehostaddress':
			backend._resolveHostAddress = forceBool(value)
		elif option == 'maxconnections':
			backend._maxConnections = forceInt(value)
		elif option == 'broadcastaddresses':
			try:
				backend._broadcastAddresses = forceDict(value)
			except ValueError:
				# This is an old-style configuraton. Old default
				# port was 12287 so we assume this as the default
				# and convert everything to the new format.
				backend._broadcastAddresses = {bcAddress: (12287, ) for bcAddress in forceUnicodeList(value)}
				logger.warning(
					"Your hostcontrol backend configuration uses the old "
					"format for broadcast addresses. The new format "
					"allows to also set a list of ports to send the "
					"broadcast to.\nPlease use this new "
					"value in the future: {0!r}", backend._broadcastAddresses
				)

			newAddresses = {bcAddress: tuple(forceInt(port) for port in ports)
							for bcAddress, ports
							in backend._broadcastAddresses.items()}
			backend._broadcastAddresses = newAddresses

	if backend._maxConnections < 1:
		backend._maxConnections = 1


class RpcThread(KillableThread):
	def __init__(self, hostControlBackend, hostId, address, username, password, method, params=[], hostPort=0):
		KillableThread.__init__(self)
		self.hostControlBackend = hostControlBackend
		self.hostId = forceHostId(hostId)
		self.address = forceIpAddress(address)
		self.username = forceUnicode(username)
		self.password = forceUnicode(password)
		self.method = forceUnicode(method)
		self.params = forceList(params)
		self.error = None
		self.result = None
		self.started = 0
		self.ended = 0
		if hostPort:
			self.hostPort = forceInt(hostPort)
		else:
			self.hostPort = self.hostControlBackend._opsiclientdPort

	def run(self):
		self.started = time.time()
		timeout = self.hostControlBackend._hostRpcTimeout
		if timeout < 0:
			timeout = 0

		try:
			query = toJson(
				{
					'id': 1,
					'method': self.method,
					'params': self.params
				}
			).encode('utf-8')

			connection = HTTPSConnection(
				host=self.address,
				port=self.hostPort,
				timeout=timeout
			)
			with closingConnection(connection) as connection:
				non_blocking_connect_https(connection, timeout)
				connection.putrequest('POST', '/opsiclientd')
				connection.putheader('content-type', 'application/json')
				connection.putheader('content-length', str(len(query)))
				auth = u'{0}:{1}'.format(self.username, self.password)
				connection.putheader('Authorization', 'Basic ' + base64.b64encode(auth.encode('latin-1')))
				connection.endheaders()
				connection.send(query)

				response = connection.getresponse()
				response = response.read()
				response = fromJson(unicode(response, 'utf-8'))

				if response and isinstance(response, dict):
					self.error = response.get('error')
					self.result = response.get('result')
				else:
					self.error = u"Bad response from client: %s" % forceUnicode(response)
		except Exception as e:
			self.error = forceUnicode(e)
		finally:
			self.ended = time.time()


class ConnectionThread(KillableThread):
	def __init__(self, hostControlBackend, hostId, address):
		KillableThread.__init__(self)
		self.hostControlBackend = hostControlBackend
		self.hostId = forceHostId(hostId)
		self.address = forceIpAddress(address)
		self.result = False
		self.started = 0
		self.ended = 0

	def run(self):
		self.started = time.time()
		timeout = self.hostControlBackend._hostReachableTimeout
		if timeout < 0:
			timeout = 0

		logger.info(u"Trying connection to '%s:%d'" % (self.address, self.hostControlBackend._opsiclientdPort))
		try:
			conn = HTTPSConnection(
				host=self.address,
				port=self.hostControlBackend._opsiclientdPort,
				timeout=timeout
			)
			with closingConnection(conn) as conn:
				non_blocking_connect_https(conn, self.hostControlBackend._hostReachableTimeout)
				if conn:
					self.result = True
		except Exception as e:
			logger.logException(e, LOG_DEBUG)
			logger.debug(e)
		self.ended = time.time()


class HostControlBackend(ExtendedBackend):

	def __init__(self, backend, **kwargs):
		self._name = 'hostcontrol'

		ExtendedBackend.__init__(self, backend)

		self._opsiclientdPort = 4441
		self._hostRpcTimeout = 15
		self._hostReachableTimeout = 3
		self._resolveHostAddress = False
		self._maxConnections = 50
		self._broadcastAddresses = {"255.255.255.255": (7, 9, 12287)}

		_configureHostcontrolBackend(self, kwargs)

	def __repr__(self):
		try:
			return u'<{0}(resolveHostAddress={1!r}, maxConnections={2!r})>'.format(
				self.__class__.__name__, self._resolveHostAddress, self._maxConnections
			)
		except AttributeError:
			# Can happen during initialisation
			return u'<{0}()>'.format(self.__class__.__name__)

	def _getHostAddress(self, host):
		address = None
		if self._resolveHostAddress:
			try:
				address = socket.gethostbyname(host.id)
			except socket.error as lookupError:
				logger.debug2("Failed to lookup ip address for {0}: {1!r}", host.id, lookupError)
		if not address:
			address = host.ipAddress
		if not address and not self._resolveHostAddress:
			try:
				address = socket.gethostbyname(host.id)
			except socket.error:
				raise BackendUnaccomplishableError(u"Failed to resolve ip address for host '%s'" % host.id)
		if not address:
			raise BackendUnaccomplishableError(u"Failed to get ip address for host '%s'" % host.id)
		return address

	def _opsiclientdRpc(self, hostIds, method, params=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = forceHostIdList(hostIds)
		method = forceUnicode(method)
		params = forceList(params)
		if not timeout:
			timeout = self._hostRpcTimeout
		timeout = forceInt(timeout)

		result = {}
		rpcts = []
		for host in self._context.host_getObjects(id=hostIds):  # pylint: disable=maybe-no-member
			try:
				try:
					port = None
					configState = self._context.configState_getObjects(configId="opsiclientd.control_server.port", objectId=host.id)
					if configState:
						logger.notice("Custom Port for opsiclientd found %s" % type(int(configState[0].values[0])))
						port = int(configState[0].values[0])
				except Exception as e:
					logger.critical("Exception: %s" % e)
					pass
				address = self._getHostAddress(host)
				rpcts.append(
					RpcThread(
						hostControlBackend=self,
						hostId=host.id,
						hostPort=port,
						address=address,
						username=u'',
						password=host.opsiHostKey,
						method=method,
						params=params
					)
				)
			except Exception as e:
				result[host.id] = {"result": None, "error": forceUnicode(e)}

		runningThreads = 0
		while rpcts:
			newRpcts = []
			for rpct in rpcts:
				if rpct.ended:
					if rpct.error:
						logger.error(u"Rpc to host %s failed, error: %s" % (rpct.hostId, rpct.error))
						result[rpct.hostId] = {"result": None, "error": rpct.error}
					else:
						logger.info(u"Rpc to host %s successful, result: %s" % (rpct.hostId, rpct.result))
						result[rpct.hostId] = {"result": rpct.result, "error": None}
					runningThreads -= 1
					continue

				if not rpct.started:
					if runningThreads < self._maxConnections:
						logger.debug(u"Starting rpc to host %s" % rpct.hostId)
						rpct.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - rpct.started
					if timeRunning >= timeout + 5:
						# thread still alive 5 seconds after timeout => kill
						logger.error(u"Rpc to host %s (address: %s) timed out after %0.2f seconds, terminating" % (rpct.hostId, rpct.address, timeRunning))
						result[rpct.hostId] = {"result": None, "error": u"timed out after %0.2f seconds" % timeRunning}
						if not rpct.ended:
							try:
								rpct.terminate()
							except Exception as e:
								logger.error(u"Failed to terminate rpc thread: %s" % e)
						runningThreads -= 1
						continue
				newRpcts.append(rpct)
			rpcts = newRpcts
			time.sleep(0.1)

		return result

	def hostControl_start(self, hostIds=[]):
		''' Switches on remote computers using WOL. '''
		hosts = self._context.host_getObjects(attributes=['hardwareAddress'], id=hostIds)  # pylint: disable=maybe-no-member
		result = {}
		for host in hosts:
			try:
				if not host.hardwareAddress:
					raise BackendMissingDataError(u"Failed to get hardware address for host '%s'" % host.id)

				mac = host.hardwareAddress.replace(':', '')
				data = ''.join(['FFFFFFFFFFFF', mac * 16])  # Pad the synchronization stream.

				# Split up the hex values and pack.
				payload = ''
				for i in range(0, len(data), 2):
					payload = ''.join([
						payload,
						struct.pack('B', int(data[i:i + 2], 16))])

				for broadcastAddress, targetPorts in self._broadcastAddresses.items():
					logger.debug(u"Sending data to network broadcast {0} [{1}]", broadcastAddress, data)

					for port in targetPorts:
						logger.debug("Broadcasting to port {0!r}", port)
						with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)) as sock:
							sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
							sock.sendto(payload, (broadcastAddress, port))

				result[host.id] = {"result": "sent", "error": None}
			except Exception as error:
				logger.logException(error, LOG_DEBUG)
				result[host.id] = {"result": None, "error": forceUnicode(error)}
		return result

	def hostControl_shutdown(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No host ids given")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='shutdown', params=[])

	def hostControl_reboot(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No host ids given")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='reboot', params=[])

	def hostControl_fireEvent(self, event, hostIds=[]):
		event = forceUnicode(event)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='fireEvent', params=[event])

	def hostControl_showPopup(self, message, hostIds=[]):
		message = forceUnicode(message)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='showPopup', params=[message])

	def hostControl_uptime(self, hostIds=[]):
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='uptime', params=[])

	def hostControl_getActiveSessions(self, hostIds=[]):
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='getActiveSessions', params=[])

	def hostControl_opsiclientdRpc(self, method, params=[], hostIds=[], timeout=None):
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method=method, params=params, timeout=timeout)

	def hostControl_reachable(self, hostIds=[], timeout=None):
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = forceHostIdList(hostIds)

		if not timeout:
			timeout = self._hostReachableTimeout
		timeout = forceInt(timeout)

		result = {}
		threads = []
		for host in self._context.host_getObjects(id=hostIds):  # pylint: disable=maybe-no-member
			try:
				address = self._getHostAddress(host)
				threads.append(
					ConnectionThread(
						hostControlBackend=self,
						hostId=host.id,
						address=address
					)
				)
			except Exception as e:
				logger.debug("Problem found: '%s'" % e)
				result[host.id] = False

		runningThreads = 0
		while threads:
			newThreads = []
			for thread in threads:
				if thread.ended:
					result[thread.hostId] = thread.result
					runningThreads -= 1
					continue

				if not thread.started:
					if runningThreads < self._maxConnections:
						logger.debug(u"Trying to check host reachable %s" % thread.hostId)
						thread.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - thread.started
					if timeRunning >= timeout + 5:
						# thread still alive 5 seconds after timeout => kill
						logger.error(u"Reachable check to host %s address %s timed out after %0.2f  seconds, terminating" % (thread.hostId, thread.address, timeRunning))
						result[thread.hostId] = False
						if not thread.ended:
							try:
								thread.terminate()
							except Exception as e:
								logger.error(u"Failed to terminate reachable thread: %s" % e)
						runningThreads -= 1
						continue
				newThreads.append(thread)
			threads = newThreads
			time.sleep(0.1)
		return result

	def hostControl_execute(self, command, hostIds=[], waitForEnding=True, captureStderr=True, encoding=None, timeout=300):
		command = forceUnicode(command)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(
			hostIds=hostIds, method='execute',
			params=[command, waitForEnding, captureStderr, encoding, timeout]
		)
