#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
HostControl Backend: Safe edition

:copyright: uib GmbH <info@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import socket
import time
import struct

from contextlib import closing

from OPSI.Logger import LOG_DEBUG, Logger
from OPSI.Types import BackendMissingDataError
from OPSI.Types import (forceBool, forceHostIdList, forceInt, forceList,
	forceUnicode, forceUnicodeList)
from OPSI.Backend.Backend import ExtendedBackend
from OPSI.Backend.HostControl import RpcThread, ConnectionThread

__version__ = '4.0.7.2'
__all__ = ['HostControlSafeBackend']

logger = Logger()


class HostControlSafeBackend(ExtendedBackend):
	"""
	This backend is the same as the HostControl-backend but it will not
	allow to call methods without hostId
	"""

	def __init__(self, backend, **kwargs):
		self._name = 'hostcontrolsafe'

		ExtendedBackend.__init__(self, backend)

		self._opsiclientdPort = 4441
		self._hostRpcTimeout = 15
		self._hostReachableTimeout = 3
		self._resolveHostAddress = False
		self._maxConnections = 50
		self._broadcastAddresses = ["255.255.255.255"]

		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'opsiclientdport':
				self._opsiclientdPort = forceInt(value)
			elif option == 'hostrpctimeout':
				self._hostRpcTimeout = forceInt(value)
			elif option == 'resolvehostaddress':
				self._resolveHostAddress = forceBool(value)
			elif option == 'maxconnections':
				self._maxConnections = forceInt(value)
			elif option == 'broadcastaddresses':
				self._broadcastAddresses = forceUnicodeList(value)

		if (self._maxConnections < 1):
			self._maxConnections = 1

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
				raise Exception(u"Failed to resolve ip address for host '%s'" % host.id)
		if not address:
			raise Exception(u"Failed to get ip address for host '%s'" % host.id)
		return address

	def _opsiclientdRpc(self, hostIds, method, params=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = forceHostIdList(hostIds)
		method  = forceUnicode(method)
		params  = forceList(params)
		if not timeout:
			timeout = self._hostRpcTimeout
		timeout = forceInt(timeout)

		result = {}
		rpcts = []
		for host in self._context.host_getObjects(id=hostIds):  # pylint: disable=maybe-no-member
			try:
				address = self._getHostAddress(host)
				rpcts.append(
					RpcThread(
						hostControlBackend = self,
						hostId   = host.id,
						address  = address,
						username = u'',
						password = host.opsiHostKey,
						method   = method,
						params   = params))
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
					if (runningThreads < self._maxConnections):
						logger.debug(u"Starting rpc to host %s" % rpct.hostId)
						rpct.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - rpct.started
					if (timeRunning >= timeout + 5):
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

	def hostControlSafe_start(self, hostIds=[]):
		''' Switches on remote computers using WOL. '''
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hosts = self._context.host_getObjects(attributes=['hardwareAddress'], id=hostIds)  # pylint: disable=maybe-no-member
		result = {}
		for host in hosts:
			try:
				if not host.hardwareAddress:
					raise BackendMissingDataError(u"Failed to get hardware address for host '%s'" % host.id)

				mac = host.hardwareAddress.replace(':', '')

				# Pad the synchronization stream.
				data = ''.join(['FFFFFFFFFFFF', mac * 16])
				send_data = ''

				# Split up the hex values and pack.
				for i in range(0, len(data), 2):
					send_data = ''.join([
						send_data,
						struct.pack('B', int(data[i: i + 2], 16)) ])

				for broadcastAddress in self._broadcastAddresses:
					logger.debug(u"Sending data to network broadcast %s [%s]" % (broadcastAddress, data))
					# Broadcast it to the LAN.
					with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)) as sock:
						sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
						sock.sendto(send_data, (broadcastAddress, 12287))
				result[host.id] = {"result": "sent", "error": None}
			except Exception as e:
				logger.logException(e, LOG_DEBUG)
				result[host.id] = {"result": None, "error": forceUnicode(e)}
		return result

	def hostControlSafe_shutdown(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='shutdown', params=[])

	def hostControlSafe_reboot(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='reboot', params=[])

	def hostControlSafe_fireEvent(self, event, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		event = forceUnicode(event)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='fireEvent', params=[event])

	def hostControlSafe_showPopup(self, message, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		message = forceUnicode(message)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='showPopup', params=[message])

	def hostControlSafe_uptime(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='uptime', params=[])

	def hostControlSafe_getActiveSessions(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='getActiveSessions', params=[])

	def hostControlSafe_opsiclientdRpc(self, method, params=[], hostIds=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method=method, params=params, timeout=timeout)

	def hostControlSafe_reachable(self, hostIds=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
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
						address=address))
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
					if (runningThreads < self._maxConnections):
						logger.debug(u"Trying to check host reachable %s" % thread.hostId)
						thread.start()
						runningThreads += 1
				else:
					timeRunning = time.time() - thread.started
					if (timeRunning >= timeout +5):
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

	def hostControlSafe_execute(self, command, hostIds=[], waitForEnding=True, captureStderr=True, encoding=None, timeout=300):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		command = forceUnicode(command)
		hostIds = self._context.host_getIdents(id=hostIds, returnType='unicode')  # pylint: disable=maybe-no-member
		return self._opsiclientdRpc(hostIds=hostIds, method='execute', params=[command,waitForEnding,captureStderr,encoding,timeout])
