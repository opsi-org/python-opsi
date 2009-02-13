#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Cache     =
   = = = = = = = = = = = = = = = = = = =
   
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '0.1'

# Imports
import time, types, new, json

# OPSI imports
from OPSI.Backend.Backend import *
from OPSI.Logger import *
from OPSI.Util import *
from OPSI import Tools

# Get logger instance
logger = Logger()



class DataBackendReplicator(object):
	def __init__(self, readBackend, writeBackend, newServerId=None, cleanupFirst=True):
		self.__readBackend  = readBackend
		self.__writeBackend = writeBackend
		self.__newServerId  = newServerId
		self.__cleanupFirst = cleanupFirst
		self.__oldServerId  = ''
		self.__serverIds = []
		self.__depotIds = []
		self.__clientIds = {}
		self.__groupIds = []
		self.__productIds = {}
		self.__progressSubject = ProgressSubject(id='replicator')
		
	def getServersIds(self):
		if not self.__serverIds:
			self.__serverIds = self.__readBackend.getServerIds_list()
		return self.__serverIds
	
	def getDepotIds(self):
		if not self.__depotIds:
			self.__depotIds = self.__readBackend.getDepotIds_list()
		return self.__depotIds
	
	def getClientIds(self, depotIds=[]):
		if not self.__clientIds:
			for depotId in self.getDepotIds():
				self.__clientIds[depotId] = self.__readBackend.getClientIds_list(depotIds = [ depotId ])
		clientIds = []
		for (depotId, ids) in self.__clientIds.items():
			if not depotIds or depotId in depotIds:
				clientIds.extend(ids)
		return clientIds
	
	def getGroupIds(self):
		if not self.__groupIds:
			self.__groupIds = self.__readBackend.getGroupIds_list()
		return self.__groupIds
	
	def getProductIds(self, productType='', depotId=''):
		if not self.__productIds:
			for depotId in self.getDepotIds():
				self.__productIds[depotId] = {}
				for productType in ('localboot', 'netboot'):
					self.__productIds[depotId][productType] = self.__readBackend.getProductIds_list(productType = productType, objectId = depotId)
		productIds = []
		if not depotId:
			depotId = self.getServersIds()[0]
		for (dId, pTypes) in self.__productIds.items():
			if (dId == depotId):
				for (pType, pIds) in pTypes.items():
					if not productType or (productType == pType):
						productIds.extend(pIds)
		return productIds
	
	def replicate(self, depotIds=[], clientIds=[], productIds=[]):
		if depotIds:
			self.__depotIds = depotIds
		if clientIds:
			for depotId in self.getDepotIds():
				self.__clientIds[depotId] = []
				for clientId in self.__readBackend.getClientIds_list(depotIds = [ depotId ]):
					if clientId in clientIds:
						self.__clientIds[depotId].append(clientId)
		if productIds:
			for depotId in self.getDepotIds():
				self.__productIds[depotId] = {}
				for productType in ('localboot', 'netboot'):
					self.__productIds[depotId][productType] = []
					for productId in self.__readBackend.getProductIds_list(productType = productType, objectId = depotId):
						if productId in productIds:
							self.__productIds[depotId][productType].append(productId)
		self.createOpsiBase()
		
		if self.__cleanupFirst:
			self.deleteGeneralConfigs()
			self.deleteNetworkConfigs()
			self.deleteProducts()
			self.deleteClients()
			self.deleteGroups()
			self.deleteServers()
			self.deleteDepots()
		
		self.replicateServers()
		self.replicateDepots()
		self.replicateClients()
		self.replicateGroups()
		self.replicateGeneralConfigs()
		self.replicateNetworkConfigs()
		self.replicateProducts()
		self.replicateProductStates()
		self.replicateProductProperties()
		
	def createOpsiBase(self):
		logger.info("Creating opsi base")
		self.__progressSubject.setMessage("Creating opsi base.")
		self.__writeBackend.createOpsiBase()
	
	def deleteServers(self):
		logger.info("Deleting servers")
		self.__progressSubject.setMessage("Deleting servers.")
		for serverId in self.__writeBackend.getServerIds_list():
			self.__writeBackend.deleteServer(serverId)
	
	def replicateServers(self):
		logger.info("Replicating servers")
		self.__progressSubject.setMessage("Replicating servers.")
		serverIds = self.getServersIds()
		for i in range(len(serverIds)):
			serverId = serverIds[i]
			server = self.__readBackend.getHost_hash(serverId)
			logger.info("      Replicating server '%s' (%s/%s)" % (server.get('hostId'), i+1, len(serverIds)))
			self.__progressSubject.setMessage("      Replicating server '%s' (%s/%s)" % (server.get('hostId'), i+1, len(serverIds)))
			try:
				newServerId = server.get('hostId')
				if self.__newServerId:
					self._oldServerId = server.get('hostId')
					newServerId = self.__newServerId
				
				serverName = newServerId.split('.')[0]
				domain = '.'.join( newServerId.split('.')[1:] )
				self.__writeBackend.createServer(	serverName	= serverName, 
							domain		= domain,
							description	= server.get('description', ''),
							notes		= server.get('notes', '') )
				
				self.__writeBackend.setOpsiHostKey( newServerId, self.__readBackend.getOpsiHostKey(server.get('hostId')) )
				self.__writeBackend.setPcpatchPassword( newServerId, self.__readBackend.getPcpatchPassword(server.get('hostId')) )
				
			except Exception, e:
				logger.error(e)
				raise
	
	def deleteDepots(self):
		logger.info("Deleting depots")
		self.__progressSubject.setMessage("Deleting depots.")
		for depotId in self.__writeBackend.getDepotIds_list():
			self.__writeBackend.deleteDepot(depotId)
	
	def replicateDepots(self):
		logger.info("Replicating depots")
		self.__progressSubject.setMessage("Replicating depots.")
		depotIds = self.getDepotIds()
		for i in range(len(depotIds)):
			depotId = depotIds[i]
			depot = self.__readBackend.getDepot_hash(depotId)
			host = self.__readBackend.getHost_hash(depotId)
			logger.info("      Replicating depot '%s' (%s/%s)" % (depotId, i+1, len(depotIds)) )
			self.__progressSubject.setMessage("      Replicating depot '%s' (%s/%s)" % (depotId, i+1, len(depotIds)) )
			try:
				newDepotId = depotId
				if self.__newServerId and (self.__oldServerId == depotId):
					newDepotId = self.__newServerId
				
				depotName = newDepotId.split('.')[0]
				domain = '.'.join( newDepotId.split('.')[1:] )
				
				self.__writeBackend.createDepot(
							depotName		= depotName,
							domain			= domain,
							description		= depot.get('description', ''),
							notes			= depot.get('notes', ''),
							depotLocalUrl		= depot.get('depotLocalUrl', ''),
							depotRemoteUrl		= depot.get('depotRemoteUrl', ''),
							repositoryLocalUrl	= depot.get('repositoryLocalUrl', ''),
							repositoryRemoteUrl	= depot.get('repositoryRemoteUrl', ''),
							network			= depot.get('network', ''),
							maxBandwidth		= depot.get('repositoryMaxBandwidth', '')
				)
				self.__writeBackend.setOpsiHostKey( newDepotId, self.__readBackend.getOpsiHostKey(depotId) )
			
			except Exception, e:
				logger.error(e)
				raise Exception("Failed to convert depot '%s': %s" % (depotId, e))
	
	def deleteClients(self):
		logger.info("Deleting clients")
		self.__progressSubject.setMessage("Deleting clients.")
		for clientId in self.__writeBackend.getClientIds_list():
			self.__writeBackend.deleteClient(clientId)
	
	def replicateClients(self):
		logger.info("Replicating clients")
		self.__progressSubject.setMessage("Replicating clients.")
		clientIds = self.getClientIds()
		for i in range(len(clientIds)):
			clientId = clientIds[i]
			client = self.__readBackend.getHost_hash(clientId)
			hardwareAddress = self.__readBackend.getMacAddress(clientId)
			logger.info("      Replicating client '%s' (%s/%s)" % (client.get('hostId'), i+1, len(clientIds)) )
			self.__progressSubject.setMessage("      Replicating client '%s' (%s/%s)" % (client.get('hostId'), i+1, len(clientIds)) )
			try:
				clientName = client.get('hostId').split('.')[0]
				domain = '.'.join( client.get('hostId').split('.')[1:] )
				self.__writeBackend.createClient(
							clientName	= clientName,
							domain		= domain,
							description	= client.get('description', ''),
							notes		= client.get('notes', ''),
							hardwareAddress = hardwareAddress )
				
				if client.get('lastSeen'):
					self.__writeBackend.setHostLastSeen(client.get('hostId'), client.get('lastSeen'))
				
				opsiHostKey = self.__readBackend.getOpsiHostKey( client.get('hostId') )
				self.__writeBackend.setOpsiHostKey( client.get('hostId'), opsiHostKey )
				serverKey = self.__writeBackend.getOpsiHostKey( self.__writeBackend.getServerId(client.get('hostId')) )
				encryptedPcpatchPass = self.__writeBackend.getPcpatchPassword( self.__writeBackend.getServerId(client.get('hostId')) )
				self.__writeBackend.setPcpatchPassword( client.get('hostId'), Tools.blowfishEncrypt(opsiHostKey, Tools.blowfishDecrypt(serverKey, encryptedPcpatchPass)) )
			
			except Exception, e:
				logger.error(e)
				raise
		
	def deleteGroups(self):
		logger.info("Deleting groups")
		self.__progressSubject.setMessage("Deleting groups.")
		for groupId in self.__writeBackend.getGroupIds_list():
			self.__writeBackend.deleteGroup(groupId)
		
	def replicateGroups(self):
		logger.info("Replicating groups")
		self.__progressSubject.setMessage("Replicating groups.")
		knownClientIds = self.getClientIds()
		groupIds = self.getGroupIds()
		for i in range(len(groupIds)):
			groupId = groupIds[i]
			logger.info("      Converting group '%s' (%s/%s)" % (groupId, i+1, len(groupIds)) )
			self.__progressSubject.setMessage("      Converting group '%s' (%s/%s)" % (groupId, i+1, len(groupIds)) )
			clientIds = []
			for clientId in self.__readBackend.getClientIds_list(groupId = groupId):
				if self.__newServerId and (self.__newServerId == clientId):
					continue
				if not clientId in knownClientIds:
					continue
				clientIds.append(clientId)
			
			try:
				self.__writeBackend.createGroup(
							groupId	= groupId,
							members	= clientIds )
			except Exception, e:
				logger.error(e)
				raise
	
	def deleteGeneralConfigs(self):
		logger.info("Deleting general configs")
		self.__progressSubject.setMessage("Deleting general configs.")
		self.__writeBackend.deleteGeneralConfig(self.__writeBackend.getServerId())
		for clientId in self.__writeBackend.getClientIds_list():
			try:
				self.__writeBackend.deleteGeneralConfig(clientId)
			except Exception, e:
				logger.error(e)
				raise
		
	def replicateGeneralConfigs(self):
		logger.info("Replicating general configs")
		self.__progressSubject.setMessage("Replicating general configs.")
		generalConfig = self.__readBackend.getGeneralConfig_hash()
		self.__writeBackend.setGeneralConfig(generalConfig)
		for clientId in self.getClientIds():
			logger.info("      Searching general config for client '%s'" % clientId)
			self.__progressSubject.setMessage("      Searching general config for client '%s'" % clientId)
			
			gc = self.__readBackend.getGeneralConfig_hash(clientId)
			new = False
			
			for (key, value) in gc.items():
				if not generalConfig.has_key(key):
					new = True
					break
				elif (generalConfig.get(key) != value):
					new = True
					break
				
			if new:
				logger.info("            Converting general config")
				self.__progressSubject.setMessage("            Converting general config.")
				self.__writeBackend.setGeneralConfig(gc , clientId)
	
	def deleteNetworkConfigs(self):
		logger.info("Deleting network configs")
		self.__progressSubject.setMessage("Deleting network configs.")
		self.__writeBackend.deleteNetworkConfig(self.__writeBackend.getServerId())
		for clientId in self.__writeBackend.getClientIds_list():
			try:
				self.__writeBackend.deleteNetworkConfig(clientId)
			except Exception, e:
				logger.error(e)
				raise
	
	def replicateNetworkConfigs(self):
		logger.info("Replicating network configs")
		self.__progressSubject.setMessage("Replicating network configs.")
		networkConfig = self.__readBackend.getNetworkConfig_hash()
		if self.__newServerId:
			networkConfig['opsiServer'] = self.__newServerId
			if (networkConfig.get('depotId') == self.__oldServerId):
				networkConfig['depotId'] = self.__newServerId
		
		self.__writeBackend.setNetworkConfig(networkConfig)
		
		for clientId in self.getClientIds():
			logger.info("      Searching network config for client '%s'" % clientId)
			self.__progressSubject.setMessage("      Searching network config for client '%s'" % clientId)
			
			nc = self.__readBackend.getNetworkConfig_hash(clientId)
			if self.__newServerId:
				nc['opsiServer'] = self.__newServerId
				if (nc.get('depotId') == self.__oldServerId):
					nc['depotId'] = self.__newServerId
			new = False
			
			for (key, value) in nc.items():
				if not networkConfig.has_key(key):
					new = True
					break
				elif (networkConfig.get(key) != value):
					new = True
					break
				
			if new:
				logger.info("            Converting network config")
				self.__progressSubject.setMessage("            Converting network config.")
				self.__writeBackend.setNetworkConfig(nc , clientId)
	
	def deleteProducts(self):
		logger.info("Deleting products")
		self.__progressSubject.setMessage("Deleting products.")
		for depotId in self.__writeBackend.getDepotIds_list():
			for productId in self.__writeBackend.getProductIds_list(objectId = depotId):
				self.__writeBackend.deleteProduct(productId = productId, depotIds = [ depotId ])
		
	def replicateProducts(self):
		objectId=None
		depotIds = self.getDepotIds()
		for i in range(len(depotIds)):
			depotId = depotIds[i]
			newDepotId = depotId
			if self.__newServerId and (self.__oldServerId == depotId):
				newDepotId = self.__newServerId
			for type in ('netboot', 'localboot'):
				logger.info("Converting %s products on depot '%s'." % (type, depotId) )
				self.__progressSubject.setMessage("Converting %s products on depot '%s'." % (type, depotId) )
				productIds = self.getProductIds(productType = type, depotId = depotId)
				for j in range(len(productIds)):
					productId = productIds[j]
					logger.info("      Converting product '%s' of depot '%s' (%s/%s)" % (productId, depotId, j+1, len(productIds)) )
					self.__progressSubject.setMessage("      Converting product '%s' of depot '%s' (%s/%s)" % (productId, depotId, j+1, len(productIds)) )
					
					product = self.__readBackend.getProduct_hash(productId = productId, depotId = depotId)
					try:
						setupScript = product.get('setupScript', '')
						uninstallScript	= product.get('uninstallScript', '')
						updateScript = product.get('updateScript', '')
						alwaysScript = product.get('alwaysScript', '')
						onceScript = product.get('onceScript', '')
						
						regexPath = re.compile('^\w:\\\\.*\\\\%s\\\\(.*)$' % productId, re.IGNORECASE)
						regexURL = re.compile('^\w+:/.*/%s/(.*)$' % productId, re.IGNORECASE)
						
						for script in ('setupScript', 'uninstallScript', 'updateScript', 'alwaysScript', 'onceScript'):
							
							if not eval(script):
								continue
							match = re.search(regexPath, eval(script))
							if match:
								logger.info("Changing scriptname from '%s' to '%s'" % (eval(script), match.group(1)))
								exec("%s = '%s'" % (script, match.group(1)))
								continue
							match = re.search(regexURL, eval(script))
							if match:
								logger.info("Changing scriptname from '%s' to '%s'" % (eval(script), match.group(1)))
								exec("%s = '%s'" % (script, match.group(1)))
							
						self.__writeBackend.createProduct(	productType		= type, 
									productId		= productId,
									name			= product.get('name'),
									productVersion		= product.get('productVersion', '1.0'),
									packageVersion		= product.get('packageVersion', '1'),
									licenseRequired		= product.get('licenseRequired', 0),
									setupScript		= setupScript,
									uninstallScript		= uninstallScript,
									updateScript		= updateScript,
									alwaysScript		= alwaysScript,
									onceScript		= onceScript,
									priority		= product.get('priority', 0),
									description		= product.get('description', ''),
									advice			= product.get('advice', ''),
									productClassNames	= product.get('productClassNames', []),
									pxeConfigTemplate	= product.get('pxeConfigTemplate', None),
									windowsSoftwareIds	= product.get('windowsSoftwareIds', []),
									depotIds		= [ newDepotId ] )
					except Exception, e:
						logger.logException(e)
						raise
					
					for dependency in self.__readBackend.getProductDependencies_listOfHashes(productId = productId, depotId = depotId):
						logger.info("            Converting product dependency '%s'" \
							% dependency.get('requiredProductId', dependency.get('requiredProductClassId')) )
						self.__progressSubject.setMessage("            Converting product dependency '%s'" \
							% dependency.get('requiredProductId', dependency.get('requiredProductClassId')) )
						self.__writeBackend.createProductDependency(
								productId			= productId,
								action				= dependency.get('action'),
								requiredProductId		= dependency.get('requiredProductId'),
								requiredProductClassId		= dependency.get('requiredProductClassId'),
								requiredAction			= dependency.get('requiredAction'),
								requiredInstallationStatus	= dependency.get('requiredInstallationStatus'),
								requirementType			= dependency.get('requirementType'),
								depotIds			= [ newDepotId ] )
						
					for definition in self.__readBackend.getProductPropertyDefinitions_listOfHashes(productId = productId, depotId = depotId):
						logger.info("            Converting product property definition '%s'" % definition.get('name') )
						self.__progressSubject.setMessage("            Converting product property definition '%s'" % definition.get('name') )
						self.__writeBackend.createProductPropertyDefinition(
								productId 	= productId,
								name		= definition.get('name'),
								description	= definition.get('description'),
								defaultValue	= definition.get('default'),
								possibleValues	= definition.get('values'),
								depotIds	= [ newDepotId ] )
				self.__progressSubject.setMessage("")
	
	def replicateProductStates(self):
		logger.info("Replicating product states")
		self.__progressSubject.setMessage("Replicating product states.")
		
		clientIds = self.getClientIds()
		i = 0
		for (clientId, states) in self.__readBackend.getProductStates_hash(clientIds, {}).items():
			depotId = self.__writeBackend.getDepotId(clientId)
			productIds = self.getProductIds(depotId = depotId)
			i += 1
			logger.info("      Converting product states of client '%s' (%s/%s)" % ( clientId, i, len(clientIds) ) )
			self.__progressSubject.setMessage("      Converting product states of client '%s' (%s/%s)" % ( clientId, i, len(clientIds) ) )
			for state in states:
				if state.get('productId') not in productIds:
					logger.debug("Skipping product state replication of product '%s': product not installed on depot" % state.get('productId'))
					continue
				
				self.__progressSubject.setMessage("               Converting product state for product '%s' on '%s' (%s/%s)" \
								% ( state.get('productId'), clientId, i, len(clientIds) ) )
				try:
					self.__writeBackend.setProductState(
							state.get('productId'),
							clientId,
							installationStatus = state.get('installationStatus'),
							actionRequest = state.get('actionRequest'),
							productVersion = state.get('productVersion'),
							packageVersion = state.get('packageVersion'),
							lastStateChange = state.get('lastStateChange'),
							licenseKey = "" )
					#self.__writeBackend.setProductInstallationStatus(state.get('productId'), hostId, state.get('installationStatus'))
					#if state.get('actionRequest') and state.get('actionRequest') not in ('undefined', 'none'):
					#	self.__writeBackend.setProductActionRequest(state.get('productId'), hostId, state.get('actionRequest'))
				except Exception, e:
					logger.error(e)
					raise
	
	def replicateProductProperties(self):
		logger.info("Replicating product properties.")
		self.__progressSubject.setMessage("Replicating product properties.")
		for depotId in self.getDepotIds():
			i = 0
			productIds = self.getProductIds(depotId = depotId)
			clientIds = self.getClientIds(depotIds = [ depotId ])
			newDepotId = depotId
			if self.__newServerId and (self.__oldServerId == depotId):
				newDepotId = self.__newServerId
			for productId in productIds:
				i += 1
				logger.info("      Replicating product properties for product '%s' (%s/%s)" % (productId, i, len(productIds)) )
				self.__progressSubject.setMessage("      Replicating product properties for product '%s' (%s/%s)" % (productId, i, len(productIds)) )
				productProperties = self.__readBackend.getProductProperties_hash(productId, objectId = depotId)
				try:
					self.__writeBackend.setProductProperties(productId, productProperties, objectId = newDepotId)
				except Exception, e:
					logger.error(e)
					raise
				
				for clientId in clientIds:
					logger.info("            Replicating product properties for product '%s' on '%s' (%s/%s)" % (productId, clientId, i, len(productIds)) )
					self.__progressSubject.setMessage("            Replicating product properties for product '%s' on '%s' (%s/%s)" % (productId, clientId, i, len(productIds)) )
					pp = self.__readBackend.getProductProperties_hash(productId, clientId)
					new = False
					
					for (key, value) in pp.items():
						if not productProperties.has_key(key):
							new = True
							break
						elif (productProperties.get(key) != value):
							new = True
							break
						
					if new:
						try:
							self.__writeBackend.setProductProperties(productId, pp, clientId)
						except Exception, e:
							logger.error(e)
							raise


# ======================================================================================================
# =                                   CLASS CACHEBACKEND                                             =
# ======================================================================================================
class CacheBackend(DataBackend):
	
	def __init__(self, username = '', password = '', address = '', backendManager=None, args={}):
		
		self.__backendManager = backendManager
		self.__possibleMethods = None
		self.__cacheOnly = False
		self.__mainOnly = False
		self.__cachedExecutions = []
		
		# Default values
		self.__mainBackend  = None
		self.__cacheBackend = None
		self.__workBackend = None
		self.__cleanupBackend = False
		self.__cachedExecutionsFile = ''
		self._defaultDomain = None
		
		# Parse arguments
		for (option, value) in args.items():
			if   (option.lower() == 'mainbackend'):          self.__mainBackend = value
			elif (option.lower() == 'cachebackend'):         self.__cacheBackend = value
			elif (option.lower() == 'workbackend'):          self.__workBackend = value
			elif (option.lower() == 'cleanupbackend'):       self.__cleanupBackend = bool(value)
			elif (option.lower() == 'cachedexecutionsfile'): self.__cachedExecutionsFile = value
			else:
				logger.warning("Unknown argument '%s' passed to CacheBackend constructor" % option)
		
		if not self.__mainBackend or not self.__cacheBackend or not self.__workBackend:
			raise Exception("MainBackend, cacheBackend and workingBackend needed")
		
		self.__cacheReplicator = DataBackendReplicator(
					readBackend  = self.__mainBackend,
					writeBackend = self.__cacheBackend,
					cleanupFirst = self.__cleanupBackend )
		
		self.__workReplicator = DataBackendReplicator(
					readBackend  = self.__cacheBackend,
					writeBackend = self.__workBackend,
					cleanupFirst = self.__cleanupBackend )
		
		for method in self.getPossibleMethods_listOfHashes():
			if (method['name'].lower() == "getpossiblemethods_listofhashes"):
				# Method already implemented
				continue
			
			# Create instance method
			params = ['self']
			params.extend( method.get('params', []) )
			paramsWithDefaults = list(params)
			for i in range(len(params)):
				if params[i].startswith('*'):
					params[i] = params[i][1:]
					paramsWithDefaults[i] = params[i] + '="__UNDEF__"'
			
			logger.debug2("Creating instance method '%s'" % method['name'])
			
			if (len(params) == 2):
				logger.debug2('def %s(%s):\n  if type(%s) == list: %s = [ %s ]\n  return self._exec(method = "%s", params = (%s))'\
					% (method['name'], ', '.join(paramsWithDefaults), params[1], params[1], params[1], method['name'], ', '.join(params[1:])) )
				exec 'def %s(%s):\n  if type(%s) == list: %s = [ %s ]\n  return self._exec(method = "%s", params = (%s))'\
					% (method['name'], ', '.join(paramsWithDefaults), params[1], params[1], params[1], method['name'], ', '.join(params[1:]))
			else:
				logger.debug2('def %s(%s): return self._exec(method = "%s", params = (%s))'\
					% (method['name'], ', '.join(paramsWithDefaults), method['name'], ', '.join(params[1:])) )
				exec 'def %s(%s): return self._exec(method = "%s", params = (%s))'\
					% (method['name'], ', '.join(paramsWithDefaults), method['name'], ', '.join(params[1:]))
			
			setattr(self.__class__, method['name'], new.instancemethod(eval(method['name']), None, self.__class__))
		
		self.readCachedExecutionsFile()
	
	def readCachedExecutionsFile(self):
		if not self.__cachedExecutionsFile:
			logger.warning("Cached executions file not given")
			return
		logger.notice("Reading cached executions from file '%s'" % self.__cachedExecutionsFile)
		if not os.path.exists(self.__cachedExecutionsFile):
			logger.warning("File '%s' does not exist" % self.__cachedExecutionsFile)
			return
		self.__cachedExecutions = []
		f = open(self.__cachedExecutionsFile)
		for line in f.readlines():
			self.__cachedExecutions.append(json.read(line.strip()))
		f.close()
		
	def writeCachedExecutionsFile(self, lastOnly=False):
		if not self.__cachedExecutionsFile:
			logger.warning("Cached executions file not given")
			return
		logger.notice("Writing cached executions to file '%s'" % self.__cachedExecutionsFile)
		f = None
		ces = []
		if lastOnly:
			f = open(self.__cachedExecutionsFile, 'a')
			if (len(self.__cachedExecutions) > 0):
				ces = [ self.__cachedExecutions[-1] ]
		else:
			f = open(self.__cachedExecutionsFile, 'w')
			ces = self.__cachedExecutions
		for ce in ces:
			f.write(json.write(ce) + '\n')
		f.close()
		
	def addCachedExecution(self, method, params=[]):
		self.__cachedExecutions.append({'method': method, 'params': params})
		self.writeCachedExecutionsFile(lastOnly=True)
	
	def getCachedExecutions(self):
		return self.__cachedExecutions
	
	def buildCache(self, depotIds=[], clientIds=[], productIds=[]):
		self.__cacheReplicator.replicate(depotIds = depotIds, clientIds = clientIds, productIds = productIds)
		for depotId in self.__cacheBackend.getDepotIds_list():
			# Do not store depot keys
			self.__cacheBackend.setOpsiHostKey(depotId, '00000000000000000000000000000000')
		self.__workReplicator.replicate(depotIds = depotIds, clientIds = clientIds, productIds = productIds)
		for depotId in self.__cacheBackend.getDepotIds_list():
			# Do not store depot keys
			self.__workBackend.setOpsiHostKey(depotId, '00000000000000000000000000000000')
		
	def writebackCache(self):
		self.__cacheOnly = False
		self.__mainOnly = True
		for i in range(len(self.__cachedExecutions)):
			try:
				ce = self.__cachedExecutions[i]
				self._execCachedExecution(ce['method'], params = ce['params'])
			except Exception, e:
				self.__cachedExecutions = self.__cachedExecutions[i:]
				raise
		self.__cachedExecutions = []
		self.writeCachedExecutionsFile()
		
	def workCached(self, cached):
		if cached:
			self.__cacheOnly = True
			self.__mainOnly = False
		else:
			self.__cacheOnly = False
		
	def getPossibleMethods_listOfHashes(self):
		if not self.__possibleMethods:
			self.__possibleMethods = []
			for (n, t) in self.__cacheBackend.__class__.__dict__.items():
				# Extract a list of all "public" functions (functionname does not start with '_') 
				if ( (type(t) == types.FunctionType or type(t) == types.MethodType )
				      and not n.startswith('_') ):
					argCount = t.func_code.co_argcount
					argNames = list(t.func_code.co_varnames[1:argCount])
					argDefaults = t.func_defaults
					if ( argDefaults != None and len(argDefaults) > 0 ):
						offset = argCount - len(argDefaults) - 1
						for i in range( len(argDefaults) ):
							argNames[offset+i] = '*' + argNames[offset+i]		
					self.__possibleMethods.append( { 'name': n, 'params': argNames} )
		return self.__possibleMethods
	
	def _getParams(self, **options):
		params = []
		logger.debug("Options: %s" % options)
		if options.has_key('params'):
			ps = options['params']
			if not isinstance(ps, tuple) and not isinstance(ps, list):
				ps = [ ps ]
			
			for p in ps:
				if (p == '__UNDEF__'):
					p = None
				logger.debug2("Appending param: %s, type: %s" % (p, type(p)))
				params.append(p)
		return params
		
	def _exec(self, method, **options):
		params = self._getParams(**options)
		if not self.__cacheOnly:
			try:
				logger.notice('Executing on main backend: %s(%s)' % (method, str(params)[1:-1]))
				be = self.__mainBackend
				result = eval('be.%s(*params)' % method)
				return result
			except Exception, e:
				if self.__mainOnly:
					raise
				logger.info("Main backend failed, using cache: %s" % e)
		
		logger.notice('Executing on cache backend: %s(%s)' % (method, str(params)[1:-1]))
		be = self.__workBackend
		result = eval('be.%s(*params)' % method)
		self.addCachedExecution(method = method, params = params)
		return result
		
		raise BackendIOException("Failed to execute")
		
	def _execCachedExecution(self, method, **options):
		params = self._getParams(**options)
		
		if method in ('setProductActionRequest', 'unsetProductActionRequest'):
			cachedActionRequest = ''
			for ar in self.__cacheBackend.getProductActionRequests_listOfHashes(clientId = params[1]):
				if (ar['productId'] == params[0]):
					cachedActionRequest = ar['actionRequest']
					break
			actionRequest = ''
			for ar in self.__mainBackend.getProductActionRequests_listOfHashes(clientId = params[1]):
				if (ar['productId'] == params[0]):
					actionRequest = ar['actionRequest']
					break
			if (cachedActionRequest != actionRequest):
				logger.warning("Action request for client '%s', product '%s' changed from '%s' to '%s', updating cache with new value" \
					% (params[1], params[0], cachedActionRequest, actionRequest))
				self.__workBackend.setProductActionRequest(productId = params[0], clientId = params[1], actionRequest = actionRequest)
				self.__cacheBackend.setProductActionRequest(productId = params[0], clientId = params[1], actionRequest = actionRequest)
				return
		
		logger.notice('Executing on main backend: %s(%s)' % (method, str(params)[1:-1]))
		be = self.__mainBackend
		result = eval('be.%s(*params)' % method)
		return result
		
		
		
		
		
