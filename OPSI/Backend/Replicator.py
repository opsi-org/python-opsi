#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Replicator  =
   = = = = = = = = = = = = = = = = = = = =
   
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
import time

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Util.Message import *

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                 CLASS BACKENDREPLICATOR                                            =
# ======================================================================================================

class BackendReplicator:
	def __init__(self, readBackend, writeBackend, newServerId=None, cleanupFirst=True):
		self.__readBackend  = readBackend
		self.__writeBackend = writeBackend
		self.__newServerId  = None
		if newServerId:
			self.__newServerId = forceHostId(newServerId)
		self.__cleanupFirst = forceBool(cleanupFirst)
		self.__oldServerId  = u''
		self.__serverIds    = []
		self.__depotIds     = []
		self.__clientIds    = []
		self.__groupIds     = []
		self.__productIds   = []
		
		self.__overallProgressSubject = ProgressSubject(id = u'overall_replication', title = u'Replicating', end=100, fireAlways=True)
		self.__currentProgressSubject = ProgressSubject(id = u'current_replication', fireAlways = True)
		
	def getCurrentProgressSubject(self):
		return self.__currentProgressSubject
	
	def getOverallProgressSubject(self):
		return self.__overallProgressSubject
	
	def replicate(self, serverIds=[], depotIds=[], clientIds=[], groupIds=[], productIds=[]):
		'''
		Replicate (a part) of a opsi configuration database
		An empty list passed as a param means: replicate all known
		None as the only element of a list means: replicate none
		'''
		serverIds  = forceList(serverIds)
		depotIds   = forceList(depotIds)
		clientIds  = forceList(clientIds)
		groupIds   = forceList(serverIds)
		productIds = forceList(productIds)
		
		logger.info(u"Replicating: serverIds=%s, depotIds=%s, clientIds=%s, groupIds=%s, productIds=%s" \
				% (serverIds, depotIds, clientIds, groupIds, productIds))
		
		
		
		self.__overallProgressSubject.setMessage(u"TEST")
		for i in range(100):
			self.__overallProgressSubject.addToState(1)
			time.sleep(0.1)
		
		return
		# Servers
		knownServerIds = self.__readBackend.host_getIdents(type = 'OpsiConfigserver', returnType = 'unicode')
		if serverIds:
			for serverId in serverIds:
				if serverId in knownServerIds:
					self.__serverIds.append(serverId)
		else:
			self.__serverIds = knownServerIds
		
		# Converting servers
		self.__currentProgressSubject.reset()
		self.__currentProgressSubject.setEnd(len(self.__serverIds))
		self.__currentProgressSubject.setMessage(u'Converting servers')
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
	
	
	
