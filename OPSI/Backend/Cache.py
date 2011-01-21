#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - Cache   =
   = = = = = = = = = = = = = = = = = =
   
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

import inspect, time, codecs, threading
from sys import version_info
if (version_info >= (2,6)):
	import json
else:
	import simplejson as json

from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *
from OPSI.Backend.Replicator import BackendReplicator
from OPSI.Util import blowfishDecrypt

logger = Logger()

class BackendModificationListener(object):
	def objectInserted(self, backend, obj):
		pass
	
	def objectUpdated(self, backend, obj):
		pass
	
	def objectsDeleted(self, backend, objs):
		pass
	
	def backendModified(self, backend):
		pass
	
class ClientCacheBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._workBackend = None
		self._masterBackend = None
		self._clientId = None
		self._depotId = None
		self._backendChangeListeners = []
		
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('workbackend',):
				self._workBackend = value
			elif option in ('masterbackend',):
				self._masterBackend = value
			elif option in ('clientid',):
				self._clientId = forceHostId(value)
			elif option in ('depotid',):
				self._depotId = forceHostId(value)
			elif option in ('backendinfo',):
				self._backendInfo = value
		
		if not self._workBackend:
			raise Exception(u"Work backend undefined")
		if not self._clientId:
			raise Exception(u"Client id undefined")
		if not self._depotId:
			raise Exception(u"Depot id undefined")
		
		self._workBackend._setContext(self)
		self._createInstanceMethods()
	
	def addBackendChangeListener(self, backendChangeListener):
		if backendChangeListener in self._backendChangeListeners:
			return
		self._backendChangeListeners.append(backendChangeListener)
		
	def removeBackendChangeListener(self, backendChangeListener):
		if not backendChangeListener in self._backendChangeListeners:
			return
		self._backendChangeListeners.remove(backendChangeListener)
	
	def _fireEvent(self, event, *args)
		class FireEventThread(threading.Thread):
			def __init__(self, listener, method, *args):
				threading.Thread.__init__(self)
				self._listener = listener
				self._method = method
				self._args = args
				
			def run(self):
				try:
					meth = getattr(self._listener, self._method)
					meth(*self._args)
				except Exception, e:
					logger.logException(e)
		
		for bcl in self._backendChangeListeners:
			FireEventThread(bcl, event, *args).start()
	
	def _setMasterBackend(self, masterBackend):
		self._masterBackend = masterBackend
	
	def _updateMasterFromWorkBackend(self):
		auditHardwareOnHosts = self._workBackend.auditHardwareOnHost_getObjects()
		if auditHardwareOnHosts:
			self._masterBackend.auditHardwareOnHost_setObsolete(self._clientId)
			self._masterBackend.auditHardwareOnHost_updateObjects(auditHardwareOnHosts)
		
	def _replicateMasterToWorkBackend(self):
		if not self._masterBackend:
			raise Exception(u"Master backend undefined")
		self._workBackend.backend_deleteBase()
		self._workBackend.backend_createBase()
		self._cacheBackendInfo(self._masterBackend.backend_info())
		br = BackendReplicator(readBackend = self._masterBackend, writeBackend = self._workBackend)
		br.replicate(
			serverIds  = [ ],
			depotIds   = [ self._depotId ],
			clientIds  = [ self._clientId ],
			groupIds   = [ ],
			productIds = [ ],
			audit      = False,
			license    = False)
		for productOnClient in self._workBackend.productOnClient_getObjects(clientId = self._clientId):
			if productOnClient.actionRequest in (None, 'none'):
				continue
			if not self._masterBackend.licensePool_getObjects(productIds = [ productOnClient.productId ]):
				continue
			print productOnClient.toHash()
			try:
				licenseOnClient = self._masterBackend.licenseOnClient_getOrCreateObject(clientId = self._clientId, productId = productOnClient.productId)
				for licensePool in self._masterBackend.licensePool_getObjects(id = licenseOnClient.licensePoolId):
					self._workBackend.licensePool_insertObject(licensePool)
				for softwareLicense in self._masterBackend.softwareLicense_getObjects(id = licenseOnClient.softwareLicenseId):
					self._workBackend.softwareLicense_insertObject(softwareLicense)
				self._workBackend.licenseOnClient_insertObject(licenseOnClient)
			except Exception, e:
				logger.error(e)
		password = self._masterBackend.user_getCredentials(username = 'pcpatch', hostId = self._clientId)['password']
		opsiHostKey = self._workBackend.host_getObjects(id = self._clientId)[0].getOpsiHostKey()
		logger.notice(u"Creating opsi passwd file '%s'" % self._opsiPasswdFile)
		self.user_setCredentials(
			username = 'pcpatch',
			password = blowfishDecrypt(opsiHostKey, password)
		)
		auditHardwareConfig = self._masterBackend.auditHardware_getConfig()
		f = codecs.open(self._auditHardwareConfigFile, 'w', 'utf8')
		result = f.write(json.dumps(auditHardwareConfig))
		f.close()
		self._workBackend._setAuditHardwareConfig(auditHardwareConfig)
		self._workBackend.backend_createBase()
		
	def _createInstanceMethods(self):
		for Class in (Backend, ConfigDataBackend):
			for member in inspect.getmembers(Class, inspect.ismethod):
				methodName = member[0]
				# 'accessControl_authenticated'
				if methodName.startswith('_') or methodName in ('backend_info', 'user_getCredentials', 'user_setCredentials', 'auditHardware_getConfig'):
					continue
				
				(argString, callString) = getArgAndCallString(member[1])
				
				logger.debug2(u"Adding method '%s' to execute on work backend" % methodName)
				exec(u'def %s(self, %s): return self._executeOnWorkBackend("%s", %s)' % (methodName, argString, methodName, callString))
				setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
	
	def _executeOnWorkBackend(self, methodName, **kwargs):
		logger.info(u"Executing method '%s' on work backend %s" % (methodName, self._workBackend))
		meth = getattr(self._workBackend, methodName)
		result = meth(**kwargs)
		action = None
		if (methodName.find('_') != -1):
			action = methodName.split('_', 1)[1]
		if action in ('insertObject', 'updateObject', 'deleteObjects'):
			if (action == 'insertObject'):
				self._fireEvent('objectInserted', kwargs.values()[0])
			if (action == 'updateObject'):
				self._fireEvent('objectUpdated', kwargs.values()[0])
			if (action == 'deleteObjects'):
				self._fireEvent('objectsDeleted', kwargs.values()[0])
			self._fireEvent('backendModified')
		return result
	
	def _cacheBackendInfo(self, backendInfo):
		f = codecs.open(self._opsiModulesFile, 'w', 'utf-8')
		modules = backendInfo['modules']
		for (module, state) in modules.items():
			if module in ('customer', 'expires'):
				continue
			if state:
				state = 'yes'
			else:
				state = 'no'
			f.write('%s = %s\n' % (module.lower(), state))
		f.write('customer = %s\n' % modules.get('customer', ''))
		f.write('expires = %s\n' % modules.get('expires', time.strftime("%Y-%m-%d", time.localtime(time.time()))))
		f.write('signature = %s\n' % modules.get('signature', ''))
		f.close()
		f = codecs.open(self._opsiVersionFile, 'w', 'utf-8')
		f.write(backendInfo.get('opsiVersion', '').strip())
		f.close()
		
if (__name__ == '__main__'):
	from OPSI.Backend.SQLite import SQLiteBackend
	from OPSI.Backend.JSONRPC import JSONRPCBackend
	
	logger.setConsoleColor(True)
	logger.setConsoleLevel(LOG_NOTICE)
	
	workBackend = SQLiteBackend(database = ':memory:')
	#workBackend = SQLiteBackend(database = '/tmp/opsi-cache.sqlite')
	
	serviceBackend = JSONRPCBackend(
		address  = 'https://bonifax.uib.local:4447/rpc',
		username = 'cachetest.uib.local',
		password = '12c1e40a6d3038d3eb2b4d489e978973')
	
	cb = ClientCacheBackend(
		workBackend   = workBackend,
		masterBackend = serviceBackend,
		depotId       = 'bonifax.uib.local',
		clientId      = 'cachetest.uib.local'
	)
	
	#workBackend._sql.execute('PRAGMA synchronous=OFF')
	cb._replicateMasterToWorkBackend()
	
	be = ExtendedConfigDataBackend(cb)
	
	#cb.host_insertObject( OpsiClient(id = 'cachetest.uib.local', description = 'description') )
	#print cb.host_getObjects()
	#print workBackend._sql.getSet('select * from HOST')
	#for productPropertyState in cb.productPropertyState_getObjects(objectId = 'cachetest.uib.local'):
	#	print productPropertyState.toHash()
	#for productOnClient in cb.productOnClient_getObjects(clientId = 'cachetest.uib.local'):
	#	print productOnClient.toHash()
	
	print be.licenseOnClient_getOrCreateObject(clientId = 'cachetest.uib.local', productId = 'license-test-oem')
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
