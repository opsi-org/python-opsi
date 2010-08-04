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
from OPSI.Backend.Backend import ExtendedConfigDataBackend

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                 CLASS BACKENDREPLICATOR                                            =
# ======================================================================================================

class BackendReplicator:
	OBJECT_CLASSES = [
		'Host',
		'Product',
		'Config',
		'Group',
		'AuditHardware',
		'AuditSoftware',
		'ProductDependency',
		'ProductProperty',
		'ProductOnDepot',
		'ProductOnClient',
		'ProductPropertyState',
		'ConfigState',
		'ObjectToGroup',
		'AuditHardwareOnHost',
		'AuditSoftwareOnClient',
	]
	
	def __init__(self, readBackend, writeBackend, newServerId=None, oldServerId=None, cleanupFirst=True):
		self.__readBackend  = readBackend
		self.__writeBackend = writeBackend
		
		self._extendedReadBackend = ExtendedConfigDataBackend(self.__readBackend)
		self._extendedWriteBackend = ExtendedConfigDataBackend(self.__writeBackend)
		
		self.__newServerId  = None
		if newServerId:
			self.__newServerId = forceHostId(newServerId)
		self.__oldServerId  = None
		if oldServerId:
			self.__oldServerId = forceHostId(oldServerId)
		self.__cleanupFirst = forceBool(cleanupFirst)
		self.__strict       = False
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
	
	def replicate(self, serverIds=[], depotIds=[], clientIds=[], groupIds=[], productIds=[], audit=True):
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
		audit      = forceBool(audit)
		
		logger.info(u"Replicating: serverIds=%s, depotIds=%s, clientIds=%s, groupIds=%s, productIds=%s, audit: %s" \
				% (serverIds, depotIds, clientIds, groupIds, productIds, audit))
		
		rb = self._extendedReadBackend
		wb = self._extendedWriteBackend
		
		wb.backend_createBase()
		
		self.__overallProgressSubject.reset()
		end = 0
		for objClass in self.OBJECT_CLASSES:
			if not audit and objClass.lower().startswith('audit'):
				continue
			end += 1
		if self.__cleanupFirst:
			end += 1
		self.__overallProgressSubject.setEnd(end)
		
		if self.__cleanupFirst:
			classSequence = list(self.OBJECT_CLASSES)
			classSequence.reverse()
			self.__currentProgressSubject.reset()
			self.__currentProgressSubject.setTitle(u"Cleaning up")
			self.__currentProgressSubject.setEnd(len(self.OBJECT_CLASSES))
			for objClass in classSequence:
				Class = eval(objClass)
				self.__currentProgressSubject.addToState(1)
				eval('wb.%s_deleteObjects(wb.%s_getObjects())' % (Class.backendMethodPrefix, Class.backendMethodPrefix))
			self.__overallProgressSubject.setMessage(u"Cleanup done!")
			self.__overallProgressSubject.addToState(1)
		
		configServer = None
		depotServers = []
		for objClass in self.OBJECT_CLASSES:
			if not audit and objClass.lower().startswith('audit'):
				continue
			
			subClasses = [ None ]
			ids = []
			if (objClass == 'Host'):
				subClasses = [ 'OpsiConfigserver', 'OpsiDepotserver', 'OpsiClient' ]
			
			methodPrefix = eval("%s.backendMethodPrefix" % objClass)
			
			self.__overallProgressSubject.setMessage(u"Replicating %ss" % objClass)
			self.__currentProgressSubject.setTitle(u"Replicating %ss" % objClass)
			for subClass in subClasses:
				if   (subClass == 'OpsiConfigserver'):
					ids = serverIds
				elif (subClass == 'OpsiDepotserver'):
					ids = depotIds
				elif (subClass == 'OpsiClient'):
					ids = clientIds
				elif (objClass == 'Group'):
					ids = groupIds
				elif (objClass == 'Product'):
					ids = productIds
				
				if not subClass:
					subClass = objClass
				Class = eval(subClass)
				
				self.__currentProgressSubject.reset()
				self.__currentProgressSubject.setMessage(u"Reading objects")
				self.__currentProgressSubject.setEnd(1)
				objs = []
				if ids:
					objs = eval('rb.%s_getObjects(type = subClass, id = ids)' % Class.backendMethodPrefix)
				else:
					objs = eval('rb.%s_getObjects(type = subClass)' % Class.backendMethodPrefix)
				self.__currentProgressSubject.addToState(1)
				
				if (objClass == 'Group'):
					# Sort groups
					sortedObjs = []
					groupIds = []
					while True:
						notAddedObjs = []
						for obj in objs:
							if not obj.getParentGroupId() or obj.getParentGroupId() in groupIds:
								if not obj.getParentGroupId():
									logger.debug(u"Adding group '%s' without parent group set" % obj)
								else:
									logger.debug(u"Adding group '%s' with parent group '%s' already added" % (obj, obj.getParentGroupId()))
								sortedObjs.append(obj)
								groupIds.append(obj.getId())
							else:
								logger.debug(u"Cannot add group '%s' parent group '%s' not added yet" % (obj, obj.getParentGroupId()))
								notAddedObjs.append(obj)
						if not notAddedObjs:
							break
						if len(notAddedObjs) == len(objs):
							for obj in notAddedObjs:
								logger.error(u"Failed to add group: %s" % obj)
							break
						objs = notAddedObjs
					objs = sortedObjs
				
				self.__currentProgressSubject.reset()
				self.__currentProgressSubject.setMessage(u"Writing objects")
				if (subClass == 'OpsiConfigserver') and objs:
					configServer = objs[0]
					depotServers.extend(objs)
				if (subClass == 'OpsiDepotserver'):
					depotServers.extend(objs)
				
				if self.__strict:
					self.__currentProgressSubject.setEnd(1)
					exec('wb.%s_createObjects(objs)' % Class.backendMethodPrefix)
					self.__currentProgressSubject.addToState(1)
				else:
					self.__currentProgressSubject.setEnd(len(objs))
					for obj in objs:
						try:
							exec('wb.%s_insertObject(obj)' % Class.backendMethodPrefix)
						except Exception, e:
							logger.logException(e, LOG_DEBUG)
							logger.error(u"Failed to replicate object %s: %s" % (obj, e))
						self.__currentProgressSubject.addToState(1)
				self.__currentProgressSubject.setState(len(objs))
				
			self.__overallProgressSubject.addToState(1)
		
		if self.__newServerId:
			if not self.__oldServerId:
				if configServer:
					self.__oldServerId = configServer.id
				elif depotServers:
					self.__oldServerId = depotServers[0].id
				else:
					logger.error(u"No config/depot servers found")
			
			if self.__oldServerId and (self.__oldServerId != self.__newServerId):
				logger.notice(u"Renaming config server '%s' to '%s'" % (self.__oldServerId, self.__newServerId))
				wb.host_renameOpsiDepotserver(id = self.__oldServerId, newId = self.__newServerId)
				
				newDepots = []
				for depot in wb.host_getObjects(type = 'OpsiDepotserver'):
					hash = depot.toHash()
					del hash['type']
					if (depot.id == self.__newServerId):
						newDepots.append( OpsiConfigserver.fromHash(hash) )
					else:
						newDepots.append( OpsiDepotserver.fromHash(hash) )
				wb.host_createObjects(newDepots)
				
	
	



