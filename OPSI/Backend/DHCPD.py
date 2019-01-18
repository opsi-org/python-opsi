# -*- coding: utf-8 -*-

# This file is part of python-opsi.
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
DHCPD Backend.

This backend works edits the configuration of the DHCPD and restarts
the daemon afterwards.

:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import socket
import threading

import OPSI.System as System
from OPSI.Backend.Backend import ConfigDataBackend
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Exceptions import (BackendIOError, BackendBadValueError,
	BackendMissingDataError, BackendUnableToConnectError,
	BackendUnaccomplishableError)
from OPSI.Logger import Logger
from OPSI.Object import OpsiClient, Host
from OPSI.Types import forceBool, forceDict, forceHostId, forceObjectClass, forceUnicode
from OPSI.Util.File import DHCPDConfFile
from OPSI.Util import getfqdn

__all__ = ('DHCPDBackend', )

logger = Logger()


class DHCPDBackend(ConfigDataBackend):

	def __init__(self, **kwargs):
		self._name = 'dhcpd'

		ConfigDataBackend.__init__(self, **kwargs)

		self._dhcpdConfigFile = System.Posix.locateDHCPDConfig(u'/etc/dhcp3/dhcpd.conf')
		self._reloadConfigCommand = '/usr/bin/sudo {command}'.format(
			command=System.Posix.getDHCPDRestartCommand(default='/etc/init.d/dhcp3-server restart')
		)

		self._fixedAddressFormat = u'IP'
		self._defaultClientParameters = {
			'next-server': socket.gethostbyname(getfqdn()),
			'filename': u'linux/pxelinux.0'
		}
		self._dhcpdOnDepot = False

		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'dhcpdconfigfile':
				self._dhcpdConfigFile = value
			elif option == 'reloadconfigcommand':
				self._reloadConfigCommand = value
			elif option == 'defaultclientparameters':
				self._defaultClientParameters = forceDict(value)
			elif option == 'fixedaddressformat':
				if value not in (u'IP', u'FQDN'):
					raise BackendBadValueError(u"Bad value '%s' for fixedAddressFormat, possible values are %s" % (value, u', '.join(('IP', 'FQDN'))))
				self._fixedAddressFormat = value
			elif option == 'dhcpdondepot':
				self._dhcpdOnDepot = forceBool(value)

		if self._defaultClientParameters.get('next-server') and self._defaultClientParameters['next-server'].startswith(u'127'):
			raise BackendBadValueError(u"Refusing to use ip address '%s' as default next-server" % self._defaultClientParameters['next-server'])

		self._dhcpdConfFile = DHCPDConfFile(self._dhcpdConfigFile)
		self._reloadEvent = threading.Event()
		self._reloadEvent.set()
		self._reloadLock = threading.Lock()
		self._reloadThread = None
		self._depotId = forceHostId(getfqdn())
		self._opsiHostKey = None
		self._depotConnections = {}

	def _triggerReload(self):
		if not self._reloadConfigCommand:
			return
		if not self._reloadEvent.isSet():
			return

		class ReloadThread(threading.Thread):
			def __init__(self, reloadEvent, reloadLock, reloadConfigCommand):
				threading.Thread.__init__(self)
				self._reloadEvent = reloadEvent
				self._reloadLock = reloadLock
				self._reloadConfigCommand = reloadConfigCommand

			def run(self):
				self._reloadEvent.clear()
				self._reloadEvent.wait(2)

				with self._reloadLock:
					try:
						result = System.execute(self._reloadConfigCommand)
						for line in result:
							if 'error' in line:
								raise RuntimeError(u'\n'.join(result))
					except Exception as error:
						logger.critical(u"Failed to restart dhcpd: {0}".format(error))

				self._reloadEvent.set()

		self._reloadThread = ReloadThread(self._reloadEvent, self._reloadLock, self._reloadConfigCommand)
		self._reloadThread.start()

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
					raise BackendMissingDataError(u"Failed to get opsi host key for depot '{0}'".format(self._depotId))
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
		try:
			depotId = configStates[0].values[0]
		except IndexError:
			configs = self._context.config_getObjects(id=u'clientconfig.depot.id')  # pylint: disable=maybe-no-member
			if not configs or not configs[0].defaultValues:
				raise BackendUnaccomplishableError(u"Failed to get depotserver for client '%s', config 'clientconfig.depot.id' not set and no defaults found" % clientId)
			depotId = configs[0].defaultValues[0]

		return depotId

	def backend_exit(self):
		if self._reloadThread:
			self._reloadThread.join(10)

	def _dhcpd_updateHost(self, host):
		host = forceObjectClass(host, Host)

		if self._dhcpdOnDepot:
			depotId = self._getResponsibleDepotId(host.id)  # pylint: disable=maybe-no-member
			if depotId != self._depotId:
				logger.info(u"Not responsible for client '%s', forwarding request to depot '%s'" % (host.id, depotId))  # pylint: disable=maybe-no-member
				return self._getDepotConnection(depotId).dhcpd_updateHost(host.id)  # pylint: disable=maybe-no-member
		self.dhcpd_updateHost(host)

	def dhcpd_updateHost(self, host):
		host = forceObjectClass(host, Host)

		if not host.hardwareAddress:  # pylint: disable=maybe-no-member
			logger.warning(u"Cannot update dhcpd configuration for client %s: hardware address unknown" % host)
			return

		hostname = host.id.split('.')[0]  # pylint: disable=maybe-no-member

		ipAddress = host.ipAddress  # pylint: disable=maybe-no-member
		if not ipAddress:
			try:
				logger.info(u"Ip addess of client {0} unknown, trying to get host by name", host)
				ipAddress = socket.gethostbyname(host.id)  # pylint: disable=maybe-no-member
				logger.info(u"Client fqdn resolved to {0!r}", ipAddress)
			except Exception as error:
				logger.debug(u"Failed to get IP by hostname: {0}", error)
				with self._reloadLock:
					self._dhcpdConfFile.parse()
					currentHostParams = self._dhcpdConfFile.getHost(hostname)

				if currentHostParams:
					logger.debug(
						'Trying to use address for {0} from existing DHCP '
						'configuration.', hostname
					)

					if currentHostParams.get('fixed-address'):
						ipAddress = currentHostParams['fixed-address']
					else:
						raise BackendIOError(u"Cannot update dhcpd configuration for client {0}: ip address unknown and failed to get ip address from DHCP configuration file.".format(host.id))  # pylint: disable=maybe-no-member
				else:
					raise BackendIOError(u"Cannot update dhcpd configuration for client {0}: ip address unknown and failed to get host by name".format(host.id))  # pylint: disable=maybe-no-member

		fixedAddress = ipAddress
		if self._fixedAddressFormat == 'FQDN':
			fixedAddress = host.id  # pylint: disable=maybe-no-member

		parameters = forceDict(self._defaultClientParameters)
		if not self._dhcpdOnDepot:
			try:
				depot = self._context.host_getObjects(id=self._getResponsibleDepotId(host.id))[0]  # pylint: disable=maybe-no-member
				if depot.ipAddress:
					parameters['next-server'] = depot.ipAddress
			except Exception as error:
				logger.error(u"Failed to get depot info: %s" % error)

		with self._reloadLock:
			try:
				self._dhcpdConfFile.parse()
				currentHostParams = self._dhcpdConfFile.getHost(hostname)
				if currentHostParams and (currentHostParams.get('hardware', ' ').split(' ')[1] == host.hardwareAddress) \
					and (currentHostParams.get('fixed-address') == fixedAddress) \
					and (currentHostParams.get('next-server') == parameters['next-server']):

					logger.debug(u"DHCPD config of host '%s' unchanged, no need to update config file" % host)
					return

				self._dhcpdConfFile.addHost(
					hostname=hostname,
					hardwareAddress=host.hardwareAddress,  # pylint: disable=maybe-no-member
					ipAddress=ipAddress,
					fixedAddress=fixedAddress,
					parameters=parameters
				)
				self._dhcpdConfFile.generate()
			except Exception as error:
				logger.error(error)

		self._triggerReload()

	def _dhcpd_deleteHost(self, host):
		host = forceObjectClass(host, Host)
		if self._dhcpdOnDepot:
			for depot in self._context.host_getObjects(id=self._depotId):  # pylint: disable=maybe-no-member
				if depot.id != self._depotId:
					self._getDepotConnection(depot.id).dhcpd_deleteHost(host.id)  # pylint: disable=maybe-no-member
		self.dhcpd_deleteHost(host)

	def dhcpd_deleteHost(self, host):
		host = forceObjectClass(host, Host)

		with self._reloadLock:
			try:
				self._dhcpdConfFile.parse()
				if not self._dhcpdConfFile.getHost(host.id.split('.')[0]):  # pylint: disable=maybe-no-member
					return
				self._dhcpdConfFile.deleteHost(host.id.split('.')[0])  # pylint: disable=maybe-no-member
				self._dhcpdConfFile.generate()
			except Exception as error:
				logger.error(error)

		self._triggerReload()

	def host_insertObject(self, host):
		if not isinstance(host, OpsiClient):
			return

		logger.debug(u"host_insertObject %s" % host)
		self._dhcpd_updateHost(host)

	def host_updateObject(self, host):
		if not isinstance(host, OpsiClient):
			return

		if not host.ipAddress and not host.hardwareAddress:
			# Not of interest
			return

		logger.debug(u"host_updateObject %s" % host)
		try:
			self._dhcpd_updateHost(host)
		except Exception as exc:
			logger.info(exc)

	def host_deleteObjects(self, hosts):
		logger.debug(u"host_deleteObjects %s" % hosts)

		errors = []
		for host in hosts:
			if not isinstance(host, OpsiClient):
				continue

			try:
				self._dhcpd_deleteHost(host)
			except Exception as error:
				errors.append(forceUnicode(error))

		if errors:
			raise RuntimeError(u', '.join(errors))

	def configState_insertObject(self, configState):
		if configState.configId != 'clientconfig.depot.id':
			return

		for host in self._context.host_getObjects(id=configState.objectId):
			self.host_updateObject(host)

	def configState_updateObject(self, configState):
		if configState.configId != 'clientconfig.depot.id':
			return

		for host in self._context.host_getObjects(id=configState.objectId):
			self.host_updateObject(host)

	def configState_deleteObjects(self, configStates):
		for configState in configStates:
			if configState.configId != 'clientconfig.depot.id':
				continue

			for host in self._context.host_getObjects(id=configState.objectId):
				self.host_updateObject(host)
