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
		self.__serverConfigDir = u'/tmp/file31/servers'
		self.__depotConfigDir = u'/tmp/file31/depots'
		self.__opsiHostKeyFile = u'/tmp/file31/pckeys'
		
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
		
		hosts = []
		
		filterIds          = forceList(filter.get('id', []))
		filterTypes        = forceList(filter.get('type', []))
		filterOpsiHostKeys = forceList(filter.get('opsiHostKey', []))
		
		opsiHostKeyFile = None #create only, when necessary
		
		if ( ( filterOpsiHostKeys ) or ( 'opsiHostKey' in attributes ) ):
			opsiHostKeyFile = OpsiHostKeyFile(filename = self.__opsiHostKeyFile)
			opsiHostKeyFile.parse()
		
		if ( not filterTypes ) or ( 'OpsiClient' in filterTypes ):
			logger.debug(u"Filtering OpsiClients.")
			
			clientConfigFileNames = forceList(os.listdir(self.__clientConfigDir))
			
			for clientConfigFileName in clientConfigFileNames:
				clientConfigFile = os.path.join(self.__clientConfigDir, clientConfigFileName)
				clientId = None
				client = None
				
				if ( clientConfigFileName.lower().endswith('.ini') ):
					try:
						clientId = forceHostId(clientConfigFileName[:-4])
					except Exception, e:
						logger.error(u"Bad .ini file: '%s' in dir: '%s'" \
							% (clientConfigFileName, self.__clientConfigDir))
						
						continue #bad .ini, next file
				else:
					logger.debug2(u"No .ini file: '%s' ignored." % clientConfigFileName)
					
					continue #no .ini, next file
				
				#if ( filterIds ):
				#	matchedId = False
				#	
				#	for filterId in filterIds:
				#		if ( re.search('^%s$' % filterId.replace('*', '.*'), clientId) ):
				#			matchedId = True
				#			break
				#	
				#	if ( matchedId ):
				#		logger.debug2(u"Found a match: '%s' matches '%s'" \
				#			% (clientConfigFileName, filterId))
				#		
				#	else:
				#		continue #no match, next file
				
				client = OpsiClient(id = clientId)
				
				if ( opsiHostKeyFile ):
					client.setOpsiHostKey(opsiHostKeyFile.getOpsiHostKey(client.getId()))
				
				if ( readIniFile ):
					logger.debug2(u"Reading .ini: '%s'" % clientConfigFile)
					
					clientIniFile = IniFile(filename = clientConfigFile)
					clientIni = clientIniFile.parse()
					
					try:
						for (key, value) in clientIni.items(u'info'):
							key = forceUnicodeLower(key)
							
							if   ( key == 'description' ):
								client.setDescription(value)
							elif ( key == 'notes' ):
								client.setNotes(value)
							elif ( key == 'hardwareaddress' ):
								client.setHardwareAddress(value)
							elif ( key == 'ipaddress' ):
								client.setIpAddress(value)
							elif ( key == 'inventorynumber' ):
								client.setInventoryNumber(value)
							elif ( key == 'created' ):
								client.setCreated(value)
							elif ( key == 'lastSeen' ):
								client.setLastSeen(value)
							else:
								logger.error(u"Unknown key '%s' in file '%s'" \
									(key, clientConfigFile))
					except ConfigParser.NoSectionError, e:
						logger.error(u"Failed : %s" % e)
				
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
		
		if ( not filterTypes ) or ( 'OpsiConfigserver' in filterTypes ):
			logger.debug(u"Filtering OpsiConfigserver.")
			
		
		if ( not filterTypes ) or ( 'OpsiDepotserver' in filterTypes ):
			logger.debug(u"Filtering OpsiDepotserver.")
			
		
		return	hosts
		#
		#for type in typelist:
		#	if   ( type == 'OpsiClient' ):
		#		logger.debug(u'Filtering OpsiClients.')
		#		
		#		for clientConfigFile in os.listdir(__clientConfigDir):
		#			if ( clientConfigFile )
		#			#(clientConfigFile is ini?) and (clientConfigFile name is valid?)
		#		
		#		if ( containsOption ):
		#			#parse files
		#			pass
		#	elif ( type == 'OpsiConfigserver' ):
		#		logger.debug(u'Filtering OpsiConfigserver.')
		#		
		#		
		#		
		#		if ( containsOption ):
		#			#parse files
		#			pass
		##	elif ( type == 'OpsiDepotserver' ):
		##		logger.debug(u'Filtering OpsiDepotserver.')
		##		
		##		
		##		
		##		if ( containsOption ):
		##			#parse files
		##			pass
		##	else:
		##		logger.warning(u'Type contains unknown value: %s' type )
		##
		##
		#
		#
		#############
		#test = OpsiClient(id = file)
		#test.getType() => 'OpsiClient'
		#isinstance(test, OpsiClient):
		#	...
		#############
		#
		######################
		#host_getObjects(attributes = ['id'], type = ['OpsiClient', 'OpsiDeposterver'], id = '*client*')
		#filter = {
		#	'type': 'OpsiClient',
		#	'id':   '*client*'
		#}
		#filter.keys() => ['type', 'id']
		#
		#filter.items() => [('type', 'OpsiClient'), ('id', ...)]
		#
		#for (key, value) in filter.items():
		#	value = forceList(value)
		#	
		#
		######################
		#
		#
		#
		#clientfiles = os.listdir(__clientConfigDir)
		#serverfiles = os.listdir(__serverConfigDir)
		#depotfiles = os.listdir(__depotConfigDir)
		#
		#
		#
		#
		#
		#
		#
		#
		#
		#
		#
		#
		#
		#for file in files:
		#	hostIds.append()
		#	hosts.append( OpsiClient(id = file) )
		#
		#
		##read from all hosts
		#
		##validate filter in all hosts -> hostIds
		#
		#
		#
		#
		#
		#
		#
		#hosts = []
		#
		#for hostId in hostIds:
		#	hosts.append(
		#		OpsiClient(
		#					id = hostId,
		##					opsiHostKey = ,
		##					description = ,
		##					notes = ,
		##					hardwareAddress = ,
		##					ipAddress = ,
		##					inventoryNumber = ,
		##					created = ,
		##					lastSeen = 
		#		)
		#	)
		#
		#return hosts
		
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



















	
