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
OBJTYPES = ['host', 'config', 'configState', 'product', 'productProperty', 'productDependency', 'productOnDepot', 'productOnClient', 'productPropertyState', 'group', 'objectToGroup']



# ======================================================================================================
# =                                 CLASS BACKENDREPLICATOR                                            =
# ======================================================================================================

class BackendReplicator:
	def __init__(self, readBackend, writeBackend, newServerId=None, cleanupFirst=True, verify=True):
		self.__readBackend  = readBackend
		self.__writeBackend = writeBackend
		
		self._extendedReadBackend = ExtendedConfigDataBackend(self.__readBackend)
		self._extendedWriteBackend = ExtendedConfigDataBackend(self.__writeBackend)
		
		self.__newServerId  = None
		if newServerId:
			self.__newServerId = forceHostId(newServerId)
		self.__cleanupFirst = forceBool(cleanupFirst)
		self.__verify       = forceBool(verify)
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
	
	def check(self, rb, wb):
		for objType in OBJTYPES:
			readIdents = []
			writeIdents = []
			
			for readObj in eval('rb.%s_getObjects()' % (objType)):
				readIdents.append(readObj.getIdent(returnType = 'unicode'))
			for writeObj in eval('wb.%s_getObjects()' % (objType)):
				writeIdents.append(writeObj.getIdent(returnType = 'unicode'))
			
			if self.__cleanupFirst:
				self.__overallProgressSubject.setMessage(u"%s: #readIdents: '%s' #writeIdents: '%s'" % (objType, readIdents, writeIdents))
				assert len(readIdents) == len(writeIdents)
			
			for readIdent in readIdents:
				isSameIdent = False
				for writeIdent in writeIdents:
					if readIdent == writeIdent:
						isSameIdent = True
						break
				self.__overallProgressSubject.setMessage(u"readIdent '%s' is in writeIdents: '%s'" % (readIdent, isSameIdent))
				assert isSameIdent
				self.__overallProgressSubject.addToState(1)
	
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
		
		rb = self._extendedReadBackend
		wb = self._extendedWriteBackend
		
		
		
		if self.__cleanupFirst:
			print
			self.__overallProgressSubject.reset()
			self.__overallProgressSubject.setEnd(12)
			for objType in OBJTYPES:
				self.__overallProgressSubject.setMessage(u"Deleting %s" % objType)
				self.__overallProgressSubject.addToState(1)
				eval('wb.%s_deleteObjects(wb.%s_getObjects())' % (objType, objType))
			
			self.__overallProgressSubject.setMessage(u"Cleaning done!")
			self.__overallProgressSubject.addToState(1)
		
		
		
		print
		self.__overallProgressSubject.reset()
		self.__overallProgressSubject.setEnd(27)
		
		
		
		self.__overallProgressSubject.setMessage(u"Getting servers")
		self.__overallProgressSubject.addToState(1)
		objs = rb.host_getObjects(type = 'OpsiConfigserver', id = serverIds)
		self.__overallProgressSubject.setMessage(u"Creating servers")
		self.__overallProgressSubject.addToState(1)
		wb.host_createObjects(objs)
		
		self.__overallProgressSubject.setMessage(u"Getting depots")
		self.__overallProgressSubject.addToState(1)
		objs = rb.host_getObjects(type = 'OpsiDepotserver', id = depotIds)
		self.__overallProgressSubject.setMessage(u"Creating depots")
		self.__overallProgressSubject.addToState(1)
		wb.host_createObjects(objs)
		
		self.__overallProgressSubject.setMessage(u"Getting clients")
		self.__overallProgressSubject.addToState(1)
		objs = rb.host_getObjects(type = 'OpsiClient', id = clientIds)
		self.__overallProgressSubject.setMessage(u"Creating clients")
		self.__overallProgressSubject.addToState(1)
		wb.host_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.host_getObjects())                 == len(wb.host_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting configs")
		self.__overallProgressSubject.addToState(1)
		objs = rb.config_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating configs")
		self.__overallProgressSubject.addToState(1)
		wb.config_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.config_getObjects())               == len(wb.config_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting configStates")
		self.__overallProgressSubject.addToState(1)
		objs = rb.configState_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating configStates")
		self.__overallProgressSubject.addToState(1)
		wb.configState_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.configState_getObjects())          == len(wb.configState_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting products")
		self.__overallProgressSubject.addToState(1)
		objs = rb.product_getObjects(id = productIds)
		self.__overallProgressSubject.setMessage(u"Creating products")
		self.__overallProgressSubject.addToState(1)
		wb.product_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.product_getObjects())              == len(wb.product_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting productProperties")
		self.__overallProgressSubject.addToState(1)
		objs = rb.productProperty_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating productProperties")
		self.__overallProgressSubject.addToState(1)
		wb.productProperty_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.productProperty_getObjects())      == len(wb.productProperty_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting productDependencies")
		self.__overallProgressSubject.addToState(1)
		objs = rb.productDependency_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating productDependencies")
		self.__overallProgressSubject.addToState(1)
		wb.productDependency_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.productDependency_getObjects())    == len(wb.productDependency_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting productOnDepots")
		self.__overallProgressSubject.addToState(1)
		objs = rb.productOnDepot_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating productOnDepots")
		self.__overallProgressSubject.addToState(1)
		wb.productOnDepot_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.productOnDepot_getObjects())       == len(wb.productOnDepot_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting productOnClients")
		self.__overallProgressSubject.addToState(1)
		objs = rb.productOnClient_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating productOnClients")
		self.__overallProgressSubject.addToState(1)
		wb.productOnClient_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.productOnClient_getObjects())      == len(wb.productOnClient_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting productPropertyStates")
		self.__overallProgressSubject.addToState(1)
		objs = rb.productPropertyState_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating productPropertyStates")
		self.__overallProgressSubject.addToState(1)
		wb.productPropertyState_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.productPropertyState_getObjects()) == len(wb.productPropertyState_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting groups")
		self.__overallProgressSubject.addToState(1)
		objs = rb.group_getObjects(id = groupIds)
		
		#sort objs
		sortedObjs = []
		unsortedObjs = []
		while True:
			for obj in objs:
				objCanBeAppended = False
				if (obj.getParentGroupId() == None):
					objCanBeAppended = True
				else:
					for sortedObj in sortedObjs:
						if (sortedObj.getId() == obj.getParentGroupId()):
							objCanBeAppended = True
							break
				
				if objCanBeAppended:
					sortedObjs.append(obj)
				else:
					unsortedObjs.append(obj)
			
			if len(unsortedObjs) == 0:
				objs = sortedObjs
				break
			else:
				objs = unsortedObjs
				unsortedObjs = []
		
		self.__overallProgressSubject.setMessage(u"Creating groups")
		self.__overallProgressSubject.addToState(1)
		wb.group_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.group_getObjects())                == len(wb.group_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Getting objectToGroups")
		self.__overallProgressSubject.addToState(1)
		objs = rb.objectToGroup_getObjects()
		self.__overallProgressSubject.setMessage(u"Creating objectToGroups")
		self.__overallProgressSubject.addToState(1)
		wb.objectToGroup_createObjects(objs)
		
		if self.__cleanupFirst and self.__verify: assert len(rb.objectToGroup_getObjects())        == len(wb.objectToGroup_getObjects())
		
		self.__overallProgressSubject.setMessage(u"Replicating done!")
		self.__overallProgressSubject.addToState(1)
		
		
		
		print
		self.__overallProgressSubject.reset()
		self.__overallProgressSubject.setEnd(63)
		
		
		
		self.__overallProgressSubject.setMessage(u"Checking ...")
		self.__overallProgressSubject.addToState(1)
		if self.__verify:
			self.check(rb, wb)
		self.__overallProgressSubject.setMessage(u"Checking done!")
		self.__overallProgressSubject.addToState(1)
		
		print
		print
		print
	
	
	



