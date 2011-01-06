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

import inspect, time, codecs

from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *
from OPSI.Backend.Replicator import BackendReplicator

logger = Logger()

class CacheBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._workBackend = None
		self._masterBackend = None
		self._clientId = None
		self._depotId = None
		
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
		
	def _setMasterBackend(self, masterBackend):
		self._masterBackend = masterBackend
	
	def _replicateMasterToWorkBackend(self):
		if not self._masterBackend:
			raise Exception(u"Master backend undefined")
		self._cacheBackendInfo(self._masterBackend.backend_info())
		br = BackendReplicator(readBackend = self._masterBackend, writeBackend = self._workBackend)
		br.replicate(
			serverIds  = [ ],
			depotIds   = [ self._depotId ],
			clientIds  = [ self._clientId ],
			groupIds   = [ ],
			productIds = [ ],
			audit      = False)
		
	def _createInstanceMethods(self):
		for Class in (Backend, ConfigDataBackend):
			for member in inspect.getmembers(Class, inspect.ismethod):
				methodName = member[0]
				if methodName.startswith('_') or (methodName == 'backend_info'):
					continue
				
				(argString, callString) = getArgAndCallString(member[1])
				
				logger.debug2(u"Adding method '%s' to execute on work backend" % methodName)
				exec(u'def %s(self, %s): return self._executeOnWorkBackend("%s", %s)' % (methodName, argString, methodName, callString))
				setattr(self, methodName, new.instancemethod(eval(methodName), self, self.__class__))
		
	def _executeOnWorkBackend(self, methodName, **kwargs):
		logger.info(u"Executing method '%s' on work backend %s" % (methodName, self._workBackend))
		meth = getattr(self._workBackend, methodName)
		return meth(**kwargs)
	
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
	
	serviceBackend = JSONRPCBackend(
		address  = 'https://bonifax.uib.local:4447/rpc',
		username = 'cachetest.uib.local',
		password = '12c1e40a6d3038d3eb2b4d489e978973')
	cb = CacheBackend(
		workBackend    = workBackend,
		serviceBackend = serviceBackend,
		depotId        = 'bonifax.uib.local',
		clientId       = 'cachetest.uib.local'
	)
	cb._replicateServiceToWorkBackend()
	
	#cb.host_insertObject( OpsiClient(id = 'test1.uib.local', description = 'description') )
	print cb.host_getObjects()
	#print cb._workBackend._sql.getSet('select * from HOST')
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
