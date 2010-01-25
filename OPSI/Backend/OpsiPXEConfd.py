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
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._port    = u'/var/run/opsipxeconfd/opsipxeconfd.socket'
		self._depotId = forceHostId(socket.getfqdn())
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('port'):
				self._port = value
			
	def _updateProductOnClient(self, productOnClient):
		if (productOnClient.productType != 'NetbootProduct'):
			logger.debug(u"Not a netboot product: '%s', nothing to do" % productOnClient.productId)
			return
		if not productOnClient.actionRequest:
			logger.debug(u"No action request update for product '%s', client '%s', nothing to do" % (productOnClient.productId, productOnClient.clientId))
			return
		return self._updatePXEBootConfiguration(productOnClient.clientId)
		
	def _updateConfigState(self, configState):
		return self._updatePXEBootConfiguration(configState.objectId)
		
	def _updatePXEBootConfiguration(self, clientId):
		configStates = self.configState_getObjects(configId = u'clientconfig.depot.id', objectId = clientId)
		if configStates and configStates[0].values:
			depotId = configStates[0].values[0]
		else:
			configs = self.config_getObjects(id = u'clientconfig.depot.id')
			if not configs or not configs[0].defaultValues:
				raise Exception(u"Failed to get depotserver for client '%s', config 'clientconfig.depot.id' not set and no defaults found" % clientId)
			depotId = configs[0].defaultValues[0]
		
		if not (depotId == self._depotId):
			logger.info(u"Not responsible for client '%s', forwarding request to depot '%s'" % (clientId, depotId))
			raise NotImplementedError(u"Not responsible for client '%s', forwarding request to depot '%s': NOT IMPLEMENTED" % (clientId, depotId))
		
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
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		self._updateProductOnClient(productOnClient)
		
	def productOnClient_updateObject(self, productOnClient):
		self._updateProductOnClient(productOnClient)
		
	def productOnClient_deleteObjects(self, productOnClients):
		for productOnClient in productOnClients:
			self._updateProductOnClient(productOnClients)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		if (configState.configId != 'clientconfig.depot.id'):
			return
		self._updateConfigState(configState)
		
	def configState_updateObject(self, configState):
		if (configState.configId != 'clientconfig.depot.id'):
			return
		self._updateConfigState(configState)
		
	def configState_deleteObjects(self, configStates):
		for configState in configStates:
			if (configState.configId != 'clientconfig.depot.id'):
				continue
			self._updateConfigState(configState)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
