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

import os, ConfigParser

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
		
		self.__clientConfigDir = u'/tmp/file31/clients'
		self.__depotConfigDir = u'/tmp/file31/depots'
		self.__opsiHostKeyFile = u'/tmp/file31/pckeys'
		
		self._defaultDomain = u'uib.local'
		
		# Return hostid of localhost
		self.__serverId = socket.getfqdn()
		parts = self.__serverId.split('.')
		if (len(parts) < 3):
			self.__serverId = parts[0] + '.' + self._defaultDomain
		self.__serverId = self.__serverId.lower()

		
		
	def _getClientIniFile(self, client):
		return os.path.join(self.__clientConfigDir, client.getId() + u'.ini')
	
	def base_create(self):
		pass
	
	def base_delete(self):
		pass
	
	
	
	
	
	
	def _filterHosts( type = '', hosts = [], opsiHostKeyFile = None, attributes = [], **filter ):
		configDir = None
		if   ( type == 'OpsiClient'       ): configDir = self.__clientConfigDir
		elif ( type == 'OpsiConfigserver' ): configDir = self.__serverConfigDir
		elif ( type == 'OpsiDepotserver'  ): configDir = self.__depotConfigDir
		else:
			logger.error(u"Unknown type handle: '%s'" % type)
			return
		
		for item in forceList(os.listdir(configDir)):
			hostFile = os.path.join(configDir, item)
			hostId = None
			host = None
			
			if   ( type == 'OpsiClient' ) and ( hostFile.lower.endswith('.ini') ):
				try:
					hostId = forceHostId(hostFile[:-4])
				except Exception, e:
					logger.error(u"Not a client .ini file: '%s'" % hostFile )
					continue #no client .ini, next file
				
				logger.debug2(u"Adding client for filtering: '%s'" % hostId)
				host = OpsiClient(id = hostId)
			
			elif ( type == 'OpsiConfigserver' ):
				logger.debug2(u"Adding server for filtering: '%s'" % hostId)
				host = OpsiConfigserver(id = __serverId)
			
			elif ( type == 'OpsiDepotserver'  ) and ( os.path.isdir(hostFile) ):
				try:
					hostId = forceHostId(item)
					hostFile = os.path.join(hostFile, 'depot.ini')
				except Exception, e:
					logger.error(u"Not a depot path: '%s'" % hostFile )
					continue #bad .ini, next file
				
				logger.debug2(u"Adding depot for filtering: '%s'" % hostId)
				host = OpsiDepotserver(id = hostId)
			
			if ( opsiHostKeyFile ):
				host.setOpsiHostKey(opsiHostKeyFile.getOpsiHostKey(host.getId()))
				
			if ( readIniFile ):
				logger.debug2(u"Reading .ini: '%s'" % hostFile)
				
				iniFile = IniFile(filename = hostFile, ignoreCase = True)
				# Getting ConfigParser instance (ini)
				ini = iniFile.parse()
				
				for section in ini.sections():
					for (key, value) in ini.items(section):
						if   ( key == 'description' ):
							host.setDescription(value)
						elif ( key == 'notes' ):
							host.setNotes(value)
						elif ( key == 'hardwareaddress' ):
							host.setHardwareAddress(value)
						elif ( key == 'ipaddress' ):
							host.setIpAddress(value)
						elif ( key == 'inventorynumber' ):
							host.setInventoryNumber(value)
						elif ( key == 'created' ):
							host.setCreated(value)
						elif ( key == 'lastSeen' ):
							host.setLastSeen(value)
#						elif ( key == '' ) and ( section == '' ):
#							host.(value)
						else:
							logger.error(u"Unknown option '%s' in file '%s'" \
								(key, hostfile))
					
					
					
					
					
					
					
					
					
					
					
					
					
					
				
				clientHash = client.toHash()
				
				matchedAll = True
				
				for key in filter.keys():
					filterValues = forceList(filter.get(key, []))
					if not filterValues:
						continue
					
					matched = False
					
					for filterValue in filterValues:
						if filterValue is None:
							if clientHash.get(key) is None:
								matched = True
						elif clientHash.get(key) is None:
							matched = False
						elif re.search('^%s$' % filterValue.replace('*', '.*'), clientHash[key]):
							matched = True
						if matched:
							logger.info(u"Matched %s=%s" % (key, filterValue))
							break
					if not matched:
						matchedAll = False
						break
				
				if not matchedAll:
					continue
				
				hosts.append(client)
				logger.info(u"Added a matching Client: '%s'" % clientId)
		
		
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		if isinstance(host, OpsiClient):
			logger.info(u'Creating OpsiClient: %s' % host.getId())
			
			newIniFile = IniFile(filename = self._getClientIniFile(host))
			newIniFile.delete()
			newIniFile.create()
			newIni = newIniFile.parse()
			newIni.add_section(u'info')
			
			if not host.getDescription() is None:
				newIni.set(u'info', u'description',     host.getDescription().replace(u'\n', u'\\n').replace(u'%', u''))
			if not host.getNotes() is None:
				newIni.set(u'info', u'notes',           host.getNotes().replace(u'\n', u'\\n').replace(u'%', u''))
			if not host.getHardwareAddress() is None:
				newIni.set(u'info', u'macaddress',      host.getHardwareAddress())
			if not host.getIpAddress() is None:
				newIni.set(u'info', u'ipaddress',       host.getIpAddress())
			if not host.getCreated() is None:
				newIni.set(u'info', u'created',         host.getCreated())
			if not host.getInventoryNumber() is None:
				newIni.set(u'info', u'inventorynumber', host.getInventoryNumber())
			if not host.getLastSeen() is None:
				newIni.set(u'info', u'lastseen',        host.getLastSeen())
			
			newIniFile.generate(newIni)
			
			logger.debug(u"Setting opsiHostKey for host '%s' in file %s" \
				% (host.getId(), self.__opsiHostKeyFile))
			opsiHostKeys = OpsiHostKeyFile(filename = self.__opsiHostKeyFile)
			opsiHostKeys.create()
			opsiHostKeys.setOpsiHostKey(host.getId(), host.getOpsiHostKey())
			opsiHostKeys.generate()
			
			logger.info(u'Created OpsiClient: %s' % host.getId())
			
		elif isinstance(host, OpsiConfigserver):
			logger.info(u'Creating OpsiConfigserver: %s' % host.getId())
			
			pass
		
		elif isinstance(host, OpsiDepotserver):
			logger.info(u'Creating OpsiDepotserver: %s' % host.getId())
			
			pass
		
		else:
			raise BackendBadValueError(u'Cannot create host %s: unhandled host type: %s' \
				% (host, host.getType()))
		
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		logger.info(u'Updating Host: %s' % host.getId())
		
	def host_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.host_getObjects(self, attributes, **filter)
		
		logger.info(u'Getting Hosts, filter: %s' % filter)
		
		readIniFile = True
		if ( len(attributes) == 1 ) and ( attributes[0] == 'id' ):
			readIniFile = False
			for key in filter.keys():
				if key not in ('type', 'id'):
					readIniFile = True
					break
		
		hosts = []
		
		opsiHostKeyFile = None #create only, when necessary
		
		filterOpsiHostKeys = forceList(filter.get('opsiHostKey', []))
		
		if ( filterOpsiHostKeys ) or ( 'opsiHostKey' in attributes ):
			opsiHostKeyFile = OpsiHostKeyFile(filename = self.__opsiHostKeyFile)
			opsiHostKeyFile.parse()
		
		filterTypes = forceList(filter.get('type', []))
		
		if ( not filterTypes ) or ( 'OpsiClient' in filterTypes ):
			logger.debug(u"Filtering OpsiClients.")
			
			_filterHosts( type = 'OpsiClient', hosts = hosts, opsiHostKeyFile = opsiHostKeyFile, attributes = attributes, **filter )
		
		if ( not filterTypes ) or ( 'OpsiConfigserver' in filterTypes ):
			logger.debug(u"Filtering OpsiConfigserver.")
			
			_filterHosts( type = 'OpsiConfigserver', hosts = hosts, opsiHostKeyFile = opsiHostKeyFile, attributes = attributes, **filter )
		
		if ( not filterTypes ) or ( 'OpsiDepotserver' in filterTypes ):
			logger.debug(u"Filtering OpsiDepotserver.")
			
			_filterHosts( type = 'OpsiDepotserver', hosts = hosts, opsiHostKeyFile = opsiHostKeyFile, attributes = attributes, **filter )
		
		
		
		
		
#		def getDepotIds_list(self):
#		depotIds = []
#		for d in os.listdir(self.__depotConfigDir):
#			if os.path.isdir( os.path.join(self.__depotConfigDir, d) ):
#				depotIds.append( d.lower() )
#		return depotIds
		
		
		
		
		
		return	hosts
		
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		for host in forceObjectClassList(hosts, Host):
			if isinstance(host, OpsiClient):
				logger.info(u'Deleting OpsiClient: %s' % host.getId())
				
				pass
			elif isinstance(host, OpsiConfigserver):
				logger.info(u'Deleting OpsiConfigserver: %s' % host.getId())
				
				pass
			elif isinstance(host, OpsiDepotserver):
				logger.info(u'Deleting OpsiDepotserver: %s' % host.getId())
				
				
				
				
				
#		def deleteDepot(self, depotId):
#		depotId = self._preProcessHostId(depotId)
#		if not depotId in self.getDepotIds_list():
#			logger.error("Cannot delete depot '%s': does not exist" % depotId)
#			return
#		rmdir( os.path.join(self.__depotConfigDir, depotId), recursive=True )
				
				
				
				
				
				pass
			else:
				logger.warning(u'Deleting unhandled host: %s host type: %s' \
					% (host, host.getType()))
				
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















