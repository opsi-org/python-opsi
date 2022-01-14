# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
HostControl backend.

This backend can be used to control hosts.
"""

import socket
import struct
import time
import ipaddress

from contextlib import closing

from opsicommon.logging import logger
from opsicommon.objects import Host
from opsicommon.client.jsonrpc import JSONRPCClient

from OPSI import __version__
from OPSI.Backend.Base import ExtendedBackend
from OPSI.Exceptions import (
	BackendMissingDataError, BackendUnaccomplishableError
)
from OPSI.Types import (
	forceBool, forceHostId, forceHostIdList, forceInt,
	forceIpAddress, forceList, forceUnicode
)
from OPSI.Util.Thread import KillableThread


__all__ = ('RpcThread', 'ConnectionThread', 'HostControlBackend')


class RpcThread(KillableThread):  # pylint: disable=too-many-instance-attributes

	_USER_AGENT = f'opsi-RpcThread/{__version__}'

	def __init__(self, hostControlBackend, hostId, address, username, password, method, params=[], hostPort=0):  # pylint: disable=dangerous-default-value,too-many-arguments
		KillableThread.__init__(self)
		self.hostControlBackend = hostControlBackend
		self.hostId = forceHostId(hostId)
		self.method = forceUnicode(method)
		self.params = forceList(params)
		self.address = address
		self.error = None
		self.result = None
		self.started = 0
		self.ended = 0
		if hostPort:
			hostPort = forceInt(hostPort)
		else:
			hostPort = self.hostControlBackend._opsiclientdPort

		self.jsonrpc = JSONRPCClient(
			address=f"https://{self.address}:{hostPort}/opsiclientd",
			username=forceUnicode(username),
			password=forceUnicode(password),
			connect_timeout=max(self.hostControlBackend._hostRpcTimeout, 0),
			read_timeout=max(self.hostControlBackend._hostRpcTimeout, 0),
			connect_on_init=False,
			create_methods=False,
			retry=0
		)

	def run(self):
		self.started = time.time()
		try:
			self.result = self.jsonrpc.execute_rpc(self.method, self.params)
		except Exception as err:  # pylint: disable=broad-except
			self.error = str(err)
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
		timeout = max(self.hostControlBackend._hostReachableTimeout, 0)  # pylint: disable=protected-access

		logger.info("Trying connection to '%s:%d'", self.address, self.hostControlBackend._opsiclientdPort)  # pylint: disable=protected-access
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(timeout)
			sock.connect((self.address, self.hostControlBackend._opsiclientdPort))  # pylint: disable=protected-access
			self.result = True
			sock.shutdown(socket.SHUT_RDWR)
			sock.close()
		except Exception as err:  # pylint: disable=broad-except
			logger.info(err, exc_info=True)
		self.ended = time.time()


class HostControlBackend(ExtendedBackend):

	def __init__(self, backend, **kwargs):
		self._name = 'hostcontrol'

		ExtendedBackend.__init__(self, backend, **kwargs)

		self._opsiclientdPort = 4441
		self._hostRpcTimeout = 15
		self._hostReachableTimeout = 3
		self._resolveHostAddress = False
		self._maxConnections = 50
		self._broadcastAddresses = {}

		broadcastAddresses = {
			"0.0.0.0/0": {
				"255.255.255.255": [7, 9, 12287]
			}
		}

		for option, value in kwargs.items():
			option = option.lower()
			if option == 'opsiclientdport':
				backend._opsiclientdPort = forceInt(value)
			elif option == 'hostrpctimeout':
				backend._hostRpcTimeout = forceInt(value)
			elif option == 'resolvehostaddress':
				backend._resolveHostAddress = forceBool(value)
			elif option == 'maxconnections':
				backend._maxConnections = max(forceInt(value), 1)
			elif option == 'broadcastaddresses' and value:
				broadcastAddresses = value

		self._set_broadcast_addresses(broadcastAddresses)

	def __repr__(self):
		try:
			return f'<{self.__class__.__name__}(resolveHostAddress={self._resolveHostAddress}, maxConnections={self._maxConnections})>'
		except AttributeError:
			# Can happen during initialisation
			return f'<{self.__class__.__name__}()>'

	def _set_broadcast_addresses(self, value):
		self._broadcastAddresses = {}
		old_format = False
		if isinstance(value, list):
			old_format: True
			# Old format <list-broadcast-addresses>
			value = {"0.0.0.0/0": {addr: [7, 9, 12287] for addr in value}}

		elif not isinstance(list(value.values())[0], dict):
			old_format: True
			# Old format <broadcast-address>: <port-list>
			value = {"0.0.0.0/0": value}

		# New format <network-address>: <broadcast-address>: <port-list>
		for network_address, broadcast_addresses in value.items():
			net = ipaddress.ip_network(network_address)
			self._broadcastAddresses[net] = {}
			for broadcast_address, ports in broadcast_addresses.items():
				brd = ipaddress.ip_address(broadcast_address)
				self._broadcastAddresses[net][brd] = tuple(forceInt(port) for port in ports)

		if old_format:
			logger.warning(
				"Your hostcontrol backend configuration uses an old format for broadcast addresses. "
				"Please use the following new format:\n"
				'{ "<network-address>": { "<broadcast-address>": <port-list> } }\n'
				'Example: { "0.0.0.0/0": { "255.255.255.255": [7, 9, 12287] } }'
			)

	def _getHostAddress(self, host):
		address = None
		if self._resolveHostAddress:
			try:
				address = socket.gethostbyname(host.id)
			except socket.error as lookupError:
				logger.trace("Failed to lookup ip address for %s: %s", host.id, lookupError)
		if not address:
			address = host.ipAddress
		if not address and not self._resolveHostAddress:
			try:
				address = socket.gethostbyname(host.id)
			except socket.error as err:
				raise BackendUnaccomplishableError(
					f"Failed to resolve ip address for host '{host.id}'"
				) from err
		if not address:
			raise BackendUnaccomplishableError(f"Failed to get ip address for host '{host.id}'")
		return address

	def _opsiclientdRpc(self, hostIds, method, params=[], timeout=None):  # pylint: disable=dangerous-default-value,too-many-locals,too-many-branches,too-many-statements
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
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
				port = None
				try:
					configState = self._context.configState_getObjects(configId="opsiclientd.control_server.port", objectId=host.id)
					port = int(configState[0].values[0])
					logger.info("Using port %s for opsiclientd at %s", port, host.id)
				except IndexError:
					pass  # No values found
				except Exception as err:  # pylint: disable=broad-except
					logger.warning("Failed to read custom opsiclientd port for %s: %s", host.id, err)

				address = self._getHostAddress(host)
				logger.debug("Using address '%s' for host '%s'", address, host)
				rpcts.append(
					RpcThread(
						hostControlBackend=self,
						hostId=host.id,
						hostPort=port,
						address=address,
						username='',
						password=host.opsiHostKey,
						method=method,
						params=params
					)
				)
			except Exception as err:  # pylint: disable=broad-except
				result[host.id] = {"result": None, "error": str(err)}

		runningThreads = 0
		while rpcts:  # pylint: disable=too-many-nested-blocks
			newRpcts = []
			for rpct in rpcts:
				if rpct.ended:
					if rpct.error:
						logger.info("Rpc to host %s failed, error: %s", rpct.hostId, rpct.error)
						result[rpct.hostId] = {"result": None, "error": rpct.error}
					else:
						logger.info("Rpc to host %s successful, result: %s", rpct.hostId, rpct.result)
						result[rpct.hostId] = {"result": rpct.result, "error": None}
					runningThreads -= 1
					continue

				if not rpct.started:
					if runningThreads < self._maxConnections:
						logger.debug("Starting rpc to host %s", rpct.hostId)
						rpct.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - rpct.started
					if timeRunning >= timeout + 5:
						# thread still alive 5 seconds after timeout => kill
						logger.info(
							"Rpc to host %s (address: %s) timed out after %0.2f seconds, terminating",
							rpct.hostId, rpct.address, timeRunning
						)
						result[rpct.hostId] = {"result": None, "error": f"timed out after {timeRunning:0.2f} seconds"}
						if not rpct.ended:
							try:
								rpct.terminate()
							except Exception as err:  # pylint: disable=broad-except
								logger.error("Failed to terminate rpc thread: %s", err)
						runningThreads -= 1
						continue
				newRpcts.append(rpct)
			rpcts = newRpcts
			time.sleep(0.1)

		return result

	def _get_broadcast_addresses_for_host(self, host: Host):  # pylint: disable=inconsistent-return-statements
		if not self._broadcastAddresses:
			return []

		networks = []
		if host.ipAddress:
			ip_address = ipaddress.ip_address(host.ipAddress)
			for ip_network in self._broadcastAddresses:
				if ip_address and ip_address in ip_network:
					networks.append(ip_network)

			if len(networks) > 1:
				# Take bets matching network by prefix length
				networks = [sorted(networks, key=lambda x: x.prefixlen, reverse=True)[0]]
			elif not networks:
				logger.debug("No matching ip network found for host address '%s', using all broadcasts", ip_address.compressed)
				networks = list(self._broadcastAddresses)
		else:
			networks = list(self._broadcastAddresses)

		for network in networks:
			for broadcast, ports in self._broadcastAddresses[network].items():
				yield (broadcast.compressed, ports)

	def hostControl_start(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		''' Switches on remote computers using WOL. '''
		hosts = self._context.host_getObjects(attributes=['hardwareAddress', 'ipAddress'], id=hostIds)  # pylint: disable=maybe-no-member
		result = {}
		for host in hosts:
			try:
				if not host.hardwareAddress:
					raise BackendMissingDataError(f"Failed to get hardware address for host '{host.id}'")

				mac = host.hardwareAddress.replace(':', '')
				data = b''.join([b'FFFFFFFFFFFF', mac.encode("ascii") * 16])  # Pad the synchronization stream.

				# Split up the hex values and pack.
				payload = b''
				for i in range(0, len(data), 2):
					payload = b''.join([
						payload,
						struct.pack('B', int(data[i:i + 2], 16))
					])

				for broadcast_address, target_ports in self._get_broadcast_addresses_for_host(host):
					logger.debug("Sending data to network broadcast %s %s [%s]", broadcast_address, target_ports, data)

					for port in target_ports:
						logger.debug("Broadcasting to port %s", port)
						with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)) as sock:
							sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
							sock.sendto(payload, (broadcast_address, port))

				result[host.id] = {"result": "sent", "error": None}
			except Exception as err:  # pylint: disable=broad-except
				logger.debug(err, exc_info=True)
				result[host.id] = {"result": None, "error": str(err)}
		return result

	def hostControl_shutdown(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No host ids given")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='shutdown', params=[])

	def hostControl_reboot(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No host ids given")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='reboot', params=[])

	def hostControl_fireEvent(self, event, hostIds=[]):  # pylint: disable=dangerous-default-value
		event = forceUnicode(event)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='fireEvent', params=[event])

	def hostControl_showPopup(self, message, hostIds=[], mode="prepend", addTimestamp=True, displaySeconds=0):  # pylint: disable=dangerous-default-value,too-many-arguments
		message = forceUnicode(message)
		displaySeconds = forceInt(displaySeconds)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='showPopup', params=[message, mode, addTimestamp, displaySeconds])

	def hostControl_uptime(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='uptime', params=[])

	def hostControl_getActiveSessions(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='getActiveSessions', params=[])

	def hostControl_opsiclientdRpc(self, method, params=[], hostIds=[], timeout=None):  # pylint: disable=dangerous-default-value
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method=method, params=params, timeout=timeout)

	def hostControl_reachable(self, hostIds=[], timeout=None):  # pylint: disable=dangerous-default-value,too-many-branches
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
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
			except Exception as err:  # pylint: disable=broad-except
				logger.debug("Problem found: '%s'", err)
				result[host.id] = False

		runningThreads = 0
		while threads:  # pylint: disable=too-many-nested-blocks
			newThreads = []
			for thread in threads:
				if thread.ended:
					result[thread.hostId] = thread.result
					runningThreads -= 1
					continue

				if not thread.started:
					if runningThreads < self._maxConnections:
						logger.debug("Trying to check host reachable %s", thread.hostId)
						thread.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - thread.started
					if timeRunning >= timeout + 5:
						# thread still alive 5 seconds after timeout => kill
						logger.error(
							"Reachable check to host %s address %s timed out after %0.2f seconds, terminating",
							thread.hostId, thread.address, timeRunning
						)
						result[thread.hostId] = False
						if not thread.ended:
							try:
								thread.terminate()
							except Exception as err:  # pylint: disable=broad-except
								logger.error("Failed to terminate reachable thread: %s", err)
						runningThreads -= 1
						continue
				newThreads.append(thread)
			threads = newThreads
			time.sleep(0.1)
		return result

	def hostControl_execute(self, command, hostIds=[], waitForEnding=True, captureStderr=True, encoding=None, timeout=300):  # pylint: disable=dangerous-default-value,too-many-arguments
		command = forceUnicode(command)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(
			hostIds=hostIds, method='execute',
			params=[command, waitForEnding, captureStderr, encoding, timeout]
		)
