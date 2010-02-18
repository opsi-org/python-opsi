#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - OpsiPXEConfd    =
   = = = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

# Imports
import socket

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *
from OPSI.Backend.JSONRPC import JSONRPCBackend

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                   CLASS SERVERCONNECTION                                           =
# ======================================================================================================
class ServerConnection:
	def __init__(self, port):
		self.port = port
	
	def createUnixSocket(self):
		logger.notice(u"Creating unix socket '%s'" % self.port)
		self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self._socket.settimeout(5.0)
		try:
			self._socket.connect(self.port)
		except Exception, e:
			raise Exception(u"Failed to connect to socket '%s': %s" % (self.port, e))
	
	def sendCommand(self, cmd):
		self.createUnixSocket()
		self._socket.send( forceUnicode(cmd).encode('utf-8') )
		result = None
		try:
			result = forceUnicode(self._socket.recv(4096))
		except Exception, e:
			raise Exception(u"Failed to receive: %s" % e)
		self._socket.close()
		if result.startswith(u'(ERROR)'):
			raise Exception(u"Command '%s' failed: %s" % (cmd, result))
		return result
		
# ======================================================================================================
# =                                 CLASS OPSIPXECONFDBACKEND                                          =
# ======================================================================================================
class OpsiPXEConfdBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		self._name = 'opsipxeconfd'
		
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._port    = u'/var/run/opsipxeconfd/opsipxeconfd.socket'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('port',):
				self._port = value
		
		self._depotId = forceHostId(socket.getfqdn())
		self._opsiHostKey = None
		self._depotConnections  = {}
		
	def _getDepotConnection(self, depotId):
		depotId = forceHostId(depotId)
		if (depotId == self._depotId):
			return self
		if not self._depotConnections.get(depotId):
			if not self._opsiHostKey:
				depots = self._context.host_getObjects(id = self._depotId)
				if not depots or not depots[0].getOpsiHostKey():
					raise BackendMissingDataError(u"Failed to get opsi host key for depot '%s': %s" % (self._depotId, e))
				self._opsiHostKey = depots[0].getOpsiHostKey()
			
			self._depotConnections[depotId] = JSONRPCBackend(
								address  = u'https://%s:4447/rpc/backend/%s' % (depotId, self._name),
								username = self._depotId,
								password = self._opsiHostKey)
		return self._depotConnections[depotId]
	
	def _getResponsibleDepotId(self, clientId):
		configStates = self._context.configState_getObjects(configId = u'clientconfig.depot.id', objectId = clientId)
		if configStates and configStates[0].values:
			depotId = configStates[0].values[0]
		else:
			configs = self._context.config_getObjects(id = u'clientconfig.depot.id')
			if not configs or not configs[0].defaultValues:
				raise Exception(u"Failed to get depotserver for client '%s', config 'clientconfig.depot.id' not set and no defaults found" % clientId)
			depotId = configs[0].defaultValues[0]
		return depotId
	
	def _pxeBootConfigurationUpdateNeeded(self, productOnClient):
		if (productOnClient.productType != 'NetbootProduct'):
			logger.debug(u"Not a netboot product: '%s', nothing to do" % productOnClient.productId)
			return False
		if not productOnClient.actionRequest:
			logger.debug(u"No action request update for product '%s', client '%s', nothing to do" % (productOnClient.productId, productOnClient.clientId))
			return False
		return True
	
	def _updateByProductOnClient(self, productOnClient):
		if not self._pxeBootConfigurationUpdateNeeded(productOnClient):
			return
		depotId = self._getResponsibleDepotId(productOnClient.clientId)
		if (depotId != self._depotId):
			logger.info(u"Not responsible for client '%s', forwarding request to depot '%s'" % (productOnClient.clientId, depotId))
			return self._getDepotConnection(depotId).opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId)
		self.opsipxeconfd_updatePXEBootConfiguration(productOnClient.clientId)
		
	def opsipxeconfd_updatePXEBootConfiguration(self, clientId):
		logger.info(u"Updating pxe boot configuration for client '%s'" % clientId)
		
		command = u'update %s' % clientId
		try:
			sc = ServerConnection(self._port)
			logger.info(u"Sending command '%s'" % command)
			result = sc.sendCommand(command)
			logger.info(u"Got result '%s'" % result)
		except Exception, e:
			raise BackendIOError(u"Failed to update PXE boot configuration: %s" % e)
	
	def backend_exit(self):
		for connection in self._depotConnections.values():
			try:
				self._depotConnections.backend_exit()
			except:
				pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_updateObject(self, host):
		if not isinstance(host, OpsiClient):
			return
		
		if not host.ipAddress and not host.hardwareAddress:
			# Not of interest
			return
		
		self.opsipxeconfd_updatePXEBootConfiguration(host.id)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		self._updateByProductOnClient(productOnClient)
		
	def productOnClient_updateObject(self, productOnClient):
		self._updateByProductOnClient(productOnClient)
		
	def productOnClient_deleteObjects(self, productOnClients):
		for productOnClient in productOnClients:
			self._updateByProductOnClient(productOnClient)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		if (configState.configId != 'clientconfig.depot.id'):
			return
		self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)
		
	def configState_updateObject(self, configState):
		if (configState.configId != 'clientconfig.depot.id'):
			return
		self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)
		
	def configState_deleteObjects(self, configStates):
		for configState in configStates:
			if (configState.configId != 'clientconfig.depot.id'):
				continue
			self.opsipxeconfd_updatePXEBootConfiguration(configState.objectId)
			
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
