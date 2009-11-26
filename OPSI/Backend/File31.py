#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =  opsi python library - File31   =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
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
   @author: Jan Schneider <j.schneider@uib.de>, Arne Kerz <a.kerz@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Util.File import IniFile, OpsiHostKeyFile
from Object import *
from Backend import *

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                   CLASS FILE31BACKEND                                              =
# ======================================================================================================
class File31Backend(ConfigDataBackend):
	
	def __init__(self, username = '', password = '', address = 'localhost', **kwargs):
		ConfigDataBackend.__init__(self, username, password, address, **kwargs)
		
		self.__clientConfigDir = u'/tmp'
		self.__opsiHostKeyFile = u'/tmp/pckeys'
		
	def _getClientIniFile(self, client):
		return os.path.join(self.__clientConfigDir, client.getId() + u'.ini')
	
	def base_create(self):
		pass
	
	def base_delete(self):
		pass
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		if isinstance(host, OpsiClient):
			logger.info(u'Creating OpsiClient: %s' % host.getId())
			
			iniFile = IniFile(filename = self._getClientIniFile(host))
			iniFile.delete()
			iniFile.create()
			ini = iniFile.parse()
			ini.add_section(u'info')
			
			if not host.getDescription() is None:
				ini.set(u'info', u'description',     host.getDescription().replace(u'\n', u'\\n').replace(u'%', u''))
			if not host.getNotes() is None:
				ini.set(u'info', u'notes',           host.getNotes().replace(u'\n', u'\\n').replace(u'%', u''))
			if not host.getHardwareAddress() is None:
				ini.set(u'info', u'macaddress',      host.getHardwareAddress())
			if not host.getIpAddress() is None:
				ini.set(u'info', u'ipaddress',       host.getIpAddress())
			if not host.getCreated() is None:
				ini.set(u'info', u'created',         host.getCreated())
			if not host.getInventoryNumber() is None:
				ini.set(u'info', u'inventorynumber', host.getInventoryNumber())
			if not host.getLastSeen() is None:
				ini.set(u'info', u'lastseen',        host.getLastSeen())
			iniFile.generate(ini)
			
			logger.debug(u'Setting opsiHostKey for host '%s' in file %s' \
				% (host.getId(), self.__opsiHostKeyFile))
			opsiHostKeys = OpsiHostKeyFile(filename = self.__opsiHostKeyFile)
			opsiHostKeys.create()
			opsiHostKeys.setOpsiHostKey(host.getId(), host.getOpsiHostKey())
			opsiHostKeys.generate()
			
			logger.info(u'Created OpsiClient: %s' % host.getId())
			
		elif isinstance(host, OpsiConfigserver):
			logger.info(u'Creating OpsiConfigserver: %s' % host.getId())
		elif isinstance(host, OpsiDepotserver):
			logger.info(u'Creating OpsiDepotserver: %s' % host.getId())
		else:
			raise BackendBadValueError(u'Cannot create host %s: unhandled host type: %s' \
				% (host, host.getType()))
		
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
	def host_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.host_getObjects(self, attributes, **filter)
		
		hosts = []
		
		#read from all hosts
		
		#validate filter in all hosts -> hostIds
		
		for hostId in hostIds:
			hosts.append(
				OpsiClient(
					id = hostId,
#					opsiHostKey = ,
#					description = ,
#					notes = ,
#					hardwareAddress = ,
#					ipAddress = ,
#					inventoryNumber = ,
#					created = ,
#					lastSeen = 
				)
			)
		
		return hosts
		
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		for host in forceObjectClassList(hosts, Host):
			if isinstance(host, OpsiConfigserver):
				pass
			if isinstance(host, OpsiDepotserver):
				pass
			if isinstance(host, OpsiClient):
				pass
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes, **filter)
		
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)



















	
