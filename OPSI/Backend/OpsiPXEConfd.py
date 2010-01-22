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
	
# ======================================================================================================
# =                                 CLASS OPSIPXECONFDBACKEND                                          =
# ======================================================================================================
class OpsiPXEConfdBackend(ConfigDataBackend):
	
	def __init__(self):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._port = u'/var/run/opsipxeconfd/opsipxeconfd.socket'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option in ('port'):
				self._port = value
	
	def _updatePXEBootConfiguration(self, productState):
		if (productState.productType != 'NetbootProduct'):
			logger.debug(u"Not a netboot product: '%s', nothing to do" % productState.productId)
			return
		if not productState.actionRequest:
			logger.debug(u"No action request update for product '%s', host '%s', nothing to do" % (productState.productId, productState.hostId))
			return
		
		logger.info(u"Updating pxe boot configuration for host '%s', product '%s'" % (productState.hostId, productState.productId))
		
		command = u'update %s' % productState.hostId
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
	# -   ProductStates                                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productState_insertObject(self, productState):
		self._updatePXEBootConfiguration(productState)
		return []
		
	def productState_updateObject(self, productState):
		self._updatePXEBootConfiguration(productState)
		return []
		
	def productState_getObjects(self, attributes=[], **filter):
		return
	
	def productState_deleteObjects(self, productStates):
		return
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
