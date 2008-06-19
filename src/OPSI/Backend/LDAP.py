#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - LDAP    =
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '0.9'

# Imports
import ldap, ldap.modlist, re
import copy as pycopy

# OPSI imports
from OPSI.Backend.Backend import *
from OPSI.Logger import *
from OPSI.Product import *
from OPSI import Tools

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                     CLASS LDAPBACKEND                                              =
# ======================================================================================================
class LDAPBackend(DataBackend):
	
	def __init__(self, username = '', password = '', address = '', backendManager=None, session=None, args={}):
		''' LDAPBackend constructor. '''
		
		self._address = address
		self._username = username
		self._password = password
		
		self._backendManager = backendManager
		
		# Default values
		self._baseDn = 'dc=uib,dc=local'
		self._opsiBaseDn = 'cn=opsi,' + self._baseDn
		self._hostsContainerDn = 'cn=hosts,' + self._opsiBaseDn
		self._groupsContainerDn = 'cn=groups,' + self._opsiBaseDn
		self._productsContainerDn = 'cn=products,' + self._opsiBaseDn
		#self._productDependenciesContainerDn = 'cn=productDependencies,' + self._opsiBaseDn
		self._productClassesContainerDn = 'cn=productClasses,' + self._opsiBaseDn
		#self._productClassDependenciesContainerDn = 'cn=productClassDependencies,' + self._opsiBaseDn
		self._productLicensesContainerDn = 'cn=productLicenses,' + self._opsiBaseDn
		self._productStatesContainerDn = 'cn=productStates,' + self._opsiBaseDn
		#self._policiesContainerDn = 'cn=policies,' + self._opsiBaseDn
		#self._productPropertyPoliciesContainerDn = 'cn=productProperties,' + self._policiesContainerDn 
		#self._productDeploymentPoliciesContainerDn = 'cn=productDeployments,' + self._policiesContainerDn 
		#self._networkConfigPoliciesContainerDn = 'cn=networkConfigs,' + self._policiesContainerDn 
		#self._generalConfigPoliciesContainerDn = 'cn=generalConfigs,' + self._policiesContainerDn 
		#self._policyReferenceAttributeName = 'opsiPolicyReference'
		#self._policyReferenceObjectClass = 'opsiPolicyReference'
		
		### NEW ###
		self._generalConfigsContainerDn = 'cn=generalConfigs,' + self._opsiBaseDn
		self._networkConfigsContainerDn = 'cn=networkConfigs,' + self._opsiBaseDn
		self._productPropertiesContainerDn = 'cn=productProperties,' + self._opsiBaseDn
		self._hostAttributeDescription = 'description'
		self._hostAttributeNotes = 'opsiNotes'
		self._hostAttributeHardwareAddress = 'opsiHardwareAddress'
		self._hostAttributeIpAddress = 'opsiIpAddress'
		###########
		
		self._defaultDomain = None
		
		# Parse arguments
		for (option, value) in args.items():
			if   (option.lower() == 'basedn'):					self._baseDn = value
			elif (option.lower() == 'opsibasedn'):					self._opsiBaseDn = value
			elif (option.lower() == 'hostscontainerdn'):				self._hostsContainerDn = value
			elif (option.lower() == 'groupscontainerdn'):				self._groupsContainerDn = value
			elif (option.lower() == 'productscontainerdn'):			self._productsContainerDn = value
			elif (option.lower() == 'productdependenciescontainerdn'):		self._productDependenciesContainerDn = value
			elif (option.lower() == 'productclassescontainerdn'):			self._productClassesContainerDn = value
			elif (option.lower() == 'productclassdependenciescontainerdn'):	self._productClassDependenciesContainerDn = value
			elif (option.lower() == 'productlicensescontainerdn'):			self._productLicensesContainerDn = value
			elif (option.lower() == 'policiescontainerdn'):			self._policiesContainerDn = value
			elif (option.lower() == 'productpropertypoliciescontainerdn'):	self._productPropertyPoliciesContainerDn = value
			elif (option.lower() == 'productstatescontainerdn'):			self._productStatesContainerDn = value
			elif (option.lower() == 'productdeploymentpoliciescontainerdn'):	self._productDeploymentPoliciesContainerDn = value
			elif (option.lower() == 'networkconfigpoliciescontainerdn'):		self._networkConfigPoliciesContainerDn = value
			elif (option.lower() == 'generalconfigpoliciescontainerdn'):		self._generalConfigPoliciesContainerDn = value
			elif (option.lower() == 'defaultdomain'): 				self._defaultDomain = value
			elif (option.lower() == 'host'):					self._address = value
			elif (option.lower() == 'binddn'):					self._username = value
			elif (option.lower() == 'bindpw'):					self._password = value
			elif (option.lower() == 'policyreferenceattributename'):		self._policyReferenceAttributeName = value
			elif (option.lower() == 'policyreferenceobjectclass'):			self._policyReferenceObjectClass = value
			else:
				logger.warning("Unknown argument '%s' passed to LDAPBackend constructor" % option)
		
		if session:
			self._ldap = session
		else:
			logger.info("Connecting to ldap server '%s' as user '%s'" % (self._address, self._username))
			self._ldap = Session(	host	 = self._address,
						username = self._username, 
						password = self._password )
			self._ldap.baseDn = self._baseDn
			self._ldap.connect()
		
	
	def exit(self):
		self._ldap.disconnect()
	
	def createOpsiBase(self):
		# Create some containers
		self.createOrganizationalRole(self._opsiBaseDn)
		self.createOrganizationalRole(self._hostsContainerDn)
		self.createOrganizationalRole(self._generalConfigsContainerDn)
		self.createOrganizationalRole(self._networkConfigsContainerDn)
		self.createOrganizationalRole(self._groupsContainerDn)
		self.createOrganizationalRole(self._productsContainerDn)
		self.createOrganizationalRole(self._productClassesContainerDn)
		self.createOrganizationalRole(self._productStatesContainerDn)
		self.createOrganizationalRole(self._productPropertiesContainerDn)
		self.createOrganizationalRole(self._productLicensesContainerDn)
		
	
	def getHostContainerDn(self, domain = None):
		if not domain:
			domain = self._defaultDomain
		#elif (self._defaultDomain and domain != self._defaultDomain):
		#	raise NotImplementedError ("Multiple domains not supported yet, domain was '%s', default domain is %s''" 
		#					% (domain, self._defaultDomain))
		return self._hostsContainerDn
	
	def getHostId(self, hostDn):
		host = Object(hostDn)
		host.readFromDirectory(self._ldap, 'opsiHostId')
		return host.getAttribute('opsiHostId').lower()
	
	def getHostDn(self, hostId):
		''' Get a host's DN by host's ID. '''
		hostId = self._preProcessHostId(hostId)
		
		parts = hostId.split('.')
		if ( len(parts) < 3 ):
			raise BackendBadValueError("Bad hostId '%s'" % hostId)
		hostName = parts[0]
		domain = '.'.join(parts[1:])
		# Search hostname in host conatiner of the domain
		try:
			search = ObjectSearch(self._ldap, self.getHostContainerDn(domain), 
					filter='(&(objectClass=opsiHost)(opsiHostId=%s))' % hostId)
			return search.getDn()
		except BackendMissingDataError, e:
			#raise BackendMissingDataError("Host '%s' does not exist: %s" % (hostId, e))
			return "cn=%s,%s" % (hostId, self.getHostContainerDn(domain) )
	
	def getObjectDn(self, objectId):
		''' Get a object's DN by object's ID. '''
		
		if (objectId.find('=') != -1):
			# Object seems to be a dn
			return objectId
		elif (objectId == self._defaultDomain):
			# Object is the default domain
			return self._baseDn
		else:
			# Object is a host
			return self.getHostDn(objectId)
	
	# -------------------------------------------------
	# -     GENERAL CONFIG                            -
	# -------------------------------------------------
	def setGeneralConfig(self, config, objectId = None): # OK
		if not objectId:
			# Set global (server)
			objectId = self.getServerId()
		
		objectId = objectId.lower()
		
		configNew = {}
		for (key, value) in config.items():
			configNew[key.lower()] = str(value)
		config = configNew
		
		generalConfigObj = Object( 'cn=%s,%s' % ( self.getServerId(), self._generalConfigsContainerDn ) )
		if (objectId != self.getServerId()) and (objectId != self._defaultDomain):
			# General config for special host
			for (key, value) in self.getGeneralConfig_hash( objectId = self.getServerId() ).items():
				key = key.lower()
				if not config.has_key(key):
					continue
				if (value == config[key]):
					del config[key]
			generalConfigObj = Object( 'cn=%s,%s' % ( objectId, self._generalConfigsContainerDn ) )
		
		# Delete generalconfig object
		if generalConfigObj.exists(self._ldap):
			generalConfigObj.deleteFromDirectory(self._ldap)
		if not config:
			return
		
		# Create new generalconfig object
		generalConfigObj.new('opsiGeneralConfig')
		
		for (key, value) in config.items():
			generalConfigObj.addAttributeValue('opsiKeyValuePair', '%s=%s' % (key, value))
		
		# Write config object to ldap
		generalConfigObj.writeToDirectory(self._ldap)
		
	def getGeneralConfig_hash(self, objectId = None): # OK
		if not objectId:
			# Get global (server)
			objectId = self.getServerId()
		
		objectId = objectId.lower()
		
		generalConfig = {}
		try:
			generalConfigObj = Object( 'cn=%s,%s' % ( self.getServerId(), self._generalConfigsContainerDn ) )
			generalConfigObj.readFromDirectory(self._ldap)
			generalConfig = generalConfigObj.getAttributeDict(unpackOpsiKeyValuePairs = True)
		except BackendIOError, e:
			logger.warning("Failed to get generalConfig for server '%s': %s" % (self.getServerId(), e))
		
		if (objectId != self.getServerId()) and (objectId != self._defaultDomain):
			# General config for special host
			generalConfigObj = Object( 'cn=%s,%s' % ( objectId, self._generalConfigsContainerDn ) )
			if generalConfigObj.exists(self._ldap):
				generalConfigObj.readFromDirectory(self._ldap)
				generalConfig.update( generalConfigObj.getAttributeDict(unpackOpsiKeyValuePairs = True) )
		
		for key in ('objectClass', 'cn'):
			if generalConfig.has_key(key):
				del generalConfig[key]
		
		return generalConfig
	
	def deleteGeneralConfig(self, objectId): # OK
		if (objectId == self._defaultDomain):
			objectId = self.getServerId()
		
		objectId = objectId.lower()
		
		generalConfigObj = Object( 'cn=%s,%s' % ( objectId, self._generalConfigsContainerDn ) )
		if generalConfigObj.exists(self._ldap):
			generalConfigObj.deleteFromDirectory(self._ldap)
		
	# -------------------------------------------------
	# -     NETWORK FUNCTIONS                         -
	# -------------------------------------------------
	def setNetworkConfig(self, config, objectId = None): # OK
		if not objectId:
			# Set global (server)
			objectId = self.getServerId()
		
		objectId = objectId.lower()
		
		configNew = {}
		for (key, value) in config.items():
			key = key.lower()
			if key not in (	'opsiserver', 'utilsdrive', 'depotdrive', 'configdrive', 'utilsurl', 'depoturl', 'configurl', \
						'depotid', 'windomain', 'nextbootservertype', 'nextbootserviceurl' ):
				logger.error("Unknown networkConfig key '%s'" % key)
				continue
			if (key == 'depoturl'):
				logger.error("networkConfig: Setting key 'depotUrl' is no longer supported, use depotId")
				continue
			if key in ('configurl', 'utilsurl'):
				logger.error("networkConfig: Setting key '%s' is no longer supported" % key)
				continue
			configNew[key] = value
		config = configNew
		
		networkConfigObj = Object( 'cn=%s,%s' % ( self.getServerId(), self._networkConfigsContainerDn ) )
		if (objectId != self.getServerId()) and (objectId != self._defaultDomain):
			# General config for special host
			for (key, value) in self.getNetworkConfig_hash( objectId = self.getServerId() ).items():
				key = key.lower()
				if not config.has_key(key):
					continue
				if (value == config[key]):
					del config[key]
			networkConfigObj = Object( 'cn=%s,%s' % ( objectId, self._networkConfigsContainerDn ) )
		
		# Delete generalconfig object
		if networkConfigObj.exists(self._ldap):
			networkConfigObj.deleteFromDirectory(self._ldap)
		if not config:
			return
		
		# Create new generalconfig object
		networkConfigObj.new('opsiNetworkConfig')
		
		for (key, value) in config.items():
			if (key == 'opsiserver'):
				networkConfigObj.setAttribute('opsiConfigserverReference', self.getgetHostDn(value))
			elif (key == 'depotid'):
				networkConfigObj.setAttribute('opsiDepotserverReference', self.getgetHostDn(value))
			elif (key == 'configdrive'):
				networkConfigObj.setAttribute('opsiConfigDrive', value)
			elif (key == 'utilsdrive'):
				networkConfigObj.setAttribute('opsiUtilsDrive', value)
			elif (key == 'depotdrive'):
				networkConfigObj.setAttribute('opsiDepotDrive', value)
			elif (key == 'windomain'):
				networkConfigObj.setAttribute('opsiWinDomain', value)
			elif (key == 'nextbootserviceurl'):
				networkConfigObj.setAttribute('opsiNextBootServiceURL', value)
			elif (key == 'nextbootservertype'):
				networkConfigObj.setAttribute('opsiNextBootServerType', value)
		
		# Write config object to ldap
		networkConfigObj.writeToDirectory(self._ldap)
		
	def getNetworkConfig_hash(self, objectId = None): # OK
		
		if not objectId:
			objectId = self.getServerId()
		objectId = objectId.lower()
		
		networkConfig = { 
			'opsiServer': 	self.getServerId(objectId),
			'utilsDrive':	'',
			'depotDrive':	'',
			'configDrive':	'',
			'utilsUrl':	'',
			'depotId':	self.getDepotId(), # leave this as default !
			'depotUrl':	'',
			'configUrl':	'',
			'winDomain':	'',
			'nextBootServerType': '',
			'nextBootServiceURL': ''}
		
		try:
			networkConfigObj = Object( 'cn=%s,%s' % ( self.getServerId(), self._networkConfigsContainerDn ) )
			networkConfigObj.readFromDirectory(self._ldap)
			for (key, value) in networkConfigObj.getAttributeDict().items():
				if not key.startswith('opsi') or not value:
					continue
				if (key == 'opsiConfigserverReference'):
					networkConfig['opsiServer'] = self.getHostId(value)
				elif (key == 'opsiDepotserverReference'):
					networkConfig['depotId'] = self.getHostId(value)
				else:
					# cut "opsiX" from key
					networkConfig[key[4].lower() + key[5:]] = value
		except BackendIOError, e:
			logger.warning("Failed to get networkConfig for server '%s': %s" % (self.getServerId(), e))
		
		if (objectId != self.getServerId()) and (objectId != self._defaultDomain):
			# Network config for special host
			networkConfigObj = Object( 'cn=%s,%s' % ( objectId, self._networkConfigsContainerDn ) )
			if networkConfigObj.exists(self._ldap):
				networkConfigObj.readFromDirectory(self._ldap)
				for (key, value) in networkConfigObj.getAttributeDict().items():
					if not key.startswith('opsi') or not value:
						continue
					if (key == 'opsiConfigserverReference'):
						networkConfig['opsiServer'] = self.getHostId(value)
					elif (key == 'opsiDepotserverReference'):
						networkConfig['depotId'] = self.getHostId(value)
					else:
						# cut "opsiX" from key
						networkConfig[key[4].lower() + key[5:]] = value
	
	def deleteNetworkConfig(self, objectId): # OK
		if (objectId == self._defaultDomain):
			objectId = self.getServerId()
		
		objectId = objectId.lower()
		
		networkConfigObj = Object( 'cn=%s,%s' % ( objectId, self._networkConfigsContainerDn ) )
		if networkConfigObj.exists(self._ldap):
			networkConfigObj.deleteFromDirectory(self._ldap)
	
	# -------------------------------------------------
	# -     HOST FUNCTIONS                            -
	# -------------------------------------------------
	def createServer(self, serverName, domain, description=None, notes=None): # OK
		if not re.search(HOST_NAME_REGEX, serverName):
			raise BackendBadValueError("Unallowed char in hostname")
		
		if not domain:
			domain = self._defaultDomain
		
		hostId = self._preProcessHostId(serverName + '.' + domain)
		
		# Create or update server object
		server = Object( self.getHostDn(hostId) )
		if server.exists(self._ldap):
			server.readFromDirectory(self._ldap)
			server.addObjectClass('opsiDepotserver')
			server.addObjectClass('opsiConfigserver')
		else:
			server.new('opsiConfigserver', 'opsiDepotserver')
		
		server.setAttribute('opsiHostId', [ hostId ])
		if description:
			server.setAttribute(self._hostAttributeDescription, [ description ])
		else:
			server.setAttribute(self._hostAttributeDescription, [ ])
		if notes:
			server.setAttribute(self._hostAttributeNotes, [ notes ])
		else:
			server.setAttribute(self._hostAttributeNotes, [ ])
		
		server.writeToDirectory(self._ldap)
		
		return hostId
	
	def createClient(self, clientName, domain=None, description=None, notes=None, ipAddress=None, hardwareAddress=None): # OK
		if not re.search(HOST_NAME_REGEX, clientName):
			raise BackendBadValueError("Unallowed char in hostname")
		
		if not domain:
			domain = self._defaultDomain
		
		hostId = self._preProcessHostId(clientName + '.' + domain)
		
		# Create or update client object
		client = Object( self.getHostDn(hostId) )
		if client.exists(self._ldap):
			client.readFromDirectory(self._ldap)
			client.addObjectClass('opsiClient')
		else:
			client.new('opsiClient')
		
		client.setAttribute('opsiHostId', [ hostId ])
		if description:
			client.setAttribute(self._hostAttributeDescription, [ description ])
		else:
			client.setAttribute(self._hostAttributeDescription, [ ])
		if notes:
			client.setAttribute(self._hostAttributeNotes, [ notes ])
		else:
			client.setAttribute(self._hostAttributeNotes, [ ])
		if ipAddress:
			client.setAttribute(self._hostAttributeIpAddress, [ ipAddress ])
		else:
			client.setAttribute(self._hostAttributeIpAddress, [ ])
		if hardwareAddress:
			client.setAttribute(self._hostAttributeHardwareAddress, [ hardwareAddress ])
		else:
			client.setAttribute(self._hostAttributeHardwareAddress, [ ])
		
		client.writeToDirectory(self._ldap)
		
		# Create product states container
		self.createOrganizationalRole("cn=%s,%s" % (hostId, self._productStatesContainerDn))
		
		return hostId
	
	def _deleteHost(self, hostId): # OK
		hostId = self._preProcessHostId(hostId)
		
		host = Object( self.getHostDn(hostId) )
		
		# Delete product states container
		productStatesContainer = Object("cn=%s,%s" % (hostId, self._productStatesContainerDn))
		if productStatesContainer.exists(self._ldap):
			productStatesCont.deleteFromDirectory(self._ldap, recursive = True)
		
		# Delete client from groups
		groups = []
		try:
			search = ObjectSearch(self._ldap, self._groupsContainerDn, 
						filter='(&(objectClass=opsiGroup)(uniqueMember=%s))' % host.getDn())
			groups = search.getObjects()
		except BackendMissingDataError, e:
			pass
		
		for group in groups:
			logger.info("Removing host '%s' from group '%s'" % (hostId, group.getCn()))
			group.readFromDirectory(self._ldap)
			group.deleteAttributeValue('uniqueMember', client.getDn())
			group.writeToDirectory(self._ldap)
		
		# Delete host object and possible childs
		if host.exists(self._ldap):
			host.deleteFromDirectory(self._ldap, recursive = True)
	
	def deleteServer(self, serverId): # OK
		return self._deleteHost(serverId)
	
	def deleteClient(self, clientId): # OK
		return self._deleteHost(clientId)
	
	def setHostLastSeen(self, hostId, timestamp): # OK
		hostId = self._preProcessHostId(hostId)
		logger.debug("Setting last-seen timestamp for host '%s' to '%s'" % (hostId, timestamp))
		host = Object( self.getHostDn(hostId) )
		host.readFromDirectory(self._ldap)
		host.setAttribute('opsiLastSeenTimestamp', [ timestamp ])
		host.writeToDirectory(self._ldap)
	
	def setHostDescription(self, hostId, description): # OK
		hostId = self._preProcessHostId(hostId)
		logger.debug("Setting description for host '%s' to '%s'" % (hostId, description))
		host = Object( self.getHostDn(hostId) )
		host.readFromDirectory(self._ldap)
		if description:
			host.setAttribute(self._hostAttributeDescription, [ description ])
		else:
			host.setAttribute(self._hostAttributeDescription, [ ])
		host.writeToDirectory(self._ldap)
	
	def setHostNotes(self, hostId, notes): # OK
		hostId = self._preProcessHostId(hostId)
		logger.debug("Setting notes for host '%s' to '%s'" % (hostId, notes))
		host = Object( self.getHostDn(hostId) )
		host.readFromDirectory(self._ldap)
		if notes:
			host.setAttribute(self._hostAttributeNotes, [ notes ])
		else:
			host.setAttribute(self._hostAttributeNotes, [ notes ])
		host.writeToDirectory(self._ldap)
	
	def getHost_hash(self, hostId): # OK
		hostId = self._preProcessHostId(hostId)
		host = Object( self.getHostDn(hostId) )
		host.readFromDirectory(self._ldap, 'description', 'opsiNotes', 'opsiLastSeenTimestamp')
		return { 	'hostId': 	hostId,
				'description':	host.getAttribute(self._hostAttributeDescription, ""),
				'notes':	host.getAttribute(self._hostAttributeNotes, ""),
				'lastSeen':	host.getAttribute('opsiLastSeenTimestamp', "") }
	
	def getClients_listOfHashes(self, serverId = None, depotId=None, groupId = None, productId = None, installationStatus = None, actionRequest = None, productVersion = None, packageVersion = None):
		# TODO: groups
		if productId:
			productId = productId.lower()
		
		if groupId and not re.search(GROUP_ID_REGEX, groupId):
			raise BackendBadValueError("Bad group-id: '%s'" % groupId)
		
		hostDns = []
		if not serverId:
			# No server id given => search all registered clients
			try:
				# Search all opsiClient objects in host container
				search = ObjectSearch(self._ldap, self.getHostContainerDn(), filter='(objectClass=opsiClient)')
			except BackendMissingDataError:
				# No client found
				logger.warning("No clients found in LDAP")
				return []
			# Map client dns to client ids
			
			hostDns = search.getDns()
		
		else:
			# Specific server given => only search connected clients
			# Create LDAP object
			server = Object( self.getHostDn(serverId) )
			# Try if exists in LDAP
			server.readFromDirectory(self._ldap, 'dn')
			
			# Search all opsiClient objects in host container of server's domain
			clients = []
			try:
				search = ObjectSearch(self._ldap, self.getHostContainerDn( self.getDomain(serverId) ), filter='(objectClass=opsiClient)')
				clients = search.getObjects()
			except BackendMissingDataError:
				logger.warning("No clients found in LDAP")
				return []
			
			for client in clients:
				try:
					# Get client's networkConfig policy
					policySearch = PolicySearch(
							self._ldap, client.getDn(),
							policyContainer = self._networkConfigPoliciesContainerDn,
							policyFilter = '(&(objectClass=opsiPolicyNetworkConfig)(opsiConfigserverReference=%s))' % server.getDn(),
							policyReferenceObjectClass = '',#self._policyReferenceObjectClass,
							policyReferenceAttributeName = '')#self._policyReferenceAttributeName )
					policy = policySearch.getObject()				
				except (BackendMissingDataError, BackendIOError), e:
					logger.warning("Error while searching policy: %s" % e)
					continue
				if not policy.getAttribute('opsiConfigserverReference'):
					continue
				if ( policy.getAttribute('opsiConfigserverReference') == server.getDn() ):
					# Client is connected to the specified server
					hostDns.append(client.getDn())
		
		if groupId:
			filteredHostDns = []
			group = Object( "cn=%s,%s" % (groupId, self._groupsContainerDn) )
			try:
				group.readFromDirectory(self._ldap)
			except BackendMissingDataError, e:
				raise BackendMissingDataError("Group '%s' not found: %s" % (groupId, e))
			
			for member in group.getAttribute('uniqueMember', valuesAsList=True):
				if member in hostDns and not member in filteredHostDns:
					filteredHostDns.append(member)
			hostDns = filteredHostDns
		
		if installationStatus or actionRequest or productVersion or packageVersion:
			filteredHostDns = []
			
			productVersionC = None
			productVersionS = None
			if productVersion not in ('', None):
				productVersionC = '='
				match = re.search('^\s*([<>]?=?)\s*([\w\.]+)\s*$', productVersion)
				if not match:
					raise BackendBadValueError("Bad productVersion: '%s'" % productVersion)
				productVersionC = match.group(1)
				productVersionS = match.group(2)
			
			packageVersionC = None
			packageVersionS = None
			if packageVersion not in ('', None):
				packageVersionC = '='
				match = re.search('^\s*([<>]?=?)\s*([\w\.]+)\s*$', packageVersion)
				if not match:
					raise BackendBadValueError("Bad productVersion: '%s'" % packageVersion)
				packageVersionC = match.group(1)
				packageVersionS = match.group(2)
			
			logger.info("Filtering hostIds by productId: '%s', installationStatus: '%s', actionRequest: '%s'" \
				% (productId, installationStatus, actionRequest))
			
			for hostDn in hostDns:
				# Search product ldap-object
				filter = '(&(objectClass=opsiProductState)(opsiHostReference=%s))' % hostDn
				if productId:
					filter = '(&%s(cn=%s))' % (filter, productId)
				if installationStatus:
					filter = '(&%s(opsiProductInstallationStatus=%s))' % (filter, installationStatus)
				# TODO: action by policy
				if actionRequest:
					filter = '(&%s(opsiProductActionRequestForced=%s))' % (filter, actionRequest)
				
				logger.debug("ProductStates filter: '%s'" % filter)
				
				try:
					hostCn = ((hostDn.split(','))[0].split('='))[1].strip()
					productStateSearch = ObjectSearch(
								self._ldap, 
								"cn=%s,%s" % (hostCn, self._productStatesContainerDn),
								filter = filter )
					
					state = productStateSearch.getObject()
					state.readFromDirectory(self._ldap, 'opsiProductVersion', 'opsiPackageVersion')
					if productVersion not in ('', None):
						v = state.getAttribute('opsiProductVersion', '0')
						if not v: v = '0'
						if not Tools.compareVersions(v, productVersionC, productVersionS):
							continue
					if packageVersion not in ('', None):
						v = state.getAttribute('opsiPackageVersion', '0')
						if not v: v = '0'
						if not Tools.compareVersions(v, packageVersionC, packageVersionS):
							continue
					
					logger.info("Host '%s' matches filter" % hostDn)
					filteredHostDns.append(hostDn)
				except BackendMissingDataError:
					pass
				
					
			hostDns = filteredHostDns
		
		infos = []
		for hostDn in hostDns:
			host = Object(hostDn)
			host.readFromDirectory(self._ldap, 'description', 'opsiNotes', 'opsiLastSeenTimestamp')
			infos.append( { 
				'hostId': 	self.getHostId(host.getDn()),
				'description':	host.getAttribute('description', ""),
				'notes':	host.getAttribute('opsiNotes', ""),
				'lastSeen':	host.getAttribute('opsiLastSeenTimestamp', "") } )
		return infos
	
	def getClientIds_list(self, serverId = None, depotId=None, groupId = None, productId = None, installationStatus = None, actionRequest = None, productVersion = None, packageVersion = None):
		clientIds = []
		for info in self.getClients_listOfHashes(serverId, depotId, groupId, productId, installationStatus, actionRequest, productVersion, packageVersion):
			clientIds.append( info.get('hostId') )
		return clientIds
	
	def getServerIds_list(self): # OK
		# Search all ldap-objects of type opsiConfigserver in the host container
		search = None
		try:
			search = ObjectSearch(self._ldap, self.getHostContainerDn(), filter='(objectClass=opsiConfigserver)')
		except BackendMissingDataError:
			return []
		
		serverDns = search.getDns()
		ids = []
		for serverDn in serverDns:
			ids.append( self.getHostId(serverDn) )
		return ids
		
	def getServerId(self, clientId=None):
		if not clientId:
			(name, aliaslist, addresslist) = socket.gethostbyname_ex(socket.gethostname())
			if ( len(name.split('.')) > 1 ):
				self.fqdn = name
			else:
				raise Exception("Failed to get my own fully qualified domainname")
			return name
		
		# Get opsiConfigserverReference from client's policy
		clientDn = self.getHostDn(clientId)
		policySearch = PolicySearch(	self._ldap, clientDn,
						policyContainer = self._networkConfigPoliciesContainerDn,
						policyFilter = '(objectClass=opsiPolicyNetworkConfig)',
						policyReferenceObjectClass = '',#self._policyReferenceObjectClass,
						policyReferenceAttributeName = '')#self._policyReferenceAttributeName )
		serverDn = policySearch.getAttribute('opsiConfigserverReference')
		# Return server's id
		return self.getHostId(serverDn)
	
	def createDepot(self, depotName, domain, depotLocalUrl, depotRemoteUrl, repositoryLocalUrl, repositoryRemoteUrl, network, description=None, notes=None, maxBandwidth=0): # OK
		if not re.search(HOST_NAME_REGEX, depotName):
			raise BackendBadValueError("Unallowed char in hostname")
		hostId = self._preProcessHostId(depotName + '.' + domain)
		for i in (depotLocalUrl, depotRemoteUrl, repositoryLocalUrl, repositoryRemoteUrl):
			if not i.startswith('file:///') and not i.startswith('smb://') and \
			   not i.startswith('http://') and not i.startswith('https://') and \
			   not i.startswith('webdav://') and not i.startswith('webdavs://'):
				raise BackendBadValueError("Bad url '%s'" % i)
		if not re.search('\d+\.\d+\.\d+\.\d+\/\d+', network):
			raise BackendBadValueError("Bad network '%s'" % network)
		if not description:
			description = ''
		if not notes:
			notes = ''
		if not maxBandwidth:
			maxBandwidth = 0
		
		# Create or update depot object
		depot = Object( self.getHostDn(hostId) )
		exists = depot.exists(self._ldap)
		if exists:
			depot.readFromDirectory(self._ldap)
			depot.addObjectClass('opsiDepotserver')
		else:
			depot.new('opsiDepotserver')
		
		depot.setAttribute('opsiHostId', [ hostId ])
		depot.setAttribute('opsiMaximumBandwidth', [ str( maxBandwidth ) ])
		depot.setAttribute('opsiDepotLocalUrl', [ depotLocalUrl ])
		depot.setAttribute('opsiDepotRemoteUrl', [ depotRemoteUrl ])
		depot.setAttribute('opsiRepositoryLocalUrl', [ repositoryLocalUrl ])
		depot.setAttribute('opsiRepositoryRemoteUrl', [ repositoryRemoteUrl ])
		depot.setAttribute('opsiNetworkAddress', [ network ])
		if description:
			depot.setAttribute(self._hostAttributeDescription, [ description ])
		elif not exists:
			depot.setAttribute(self._hostAttributeDescription, [ ])
		if notes:
			depot.setAttribute(self._hostAttributeNotes, [ notes ])
		elif not exists:
			depot.setAttribute(self._hostAttributeNotes, [ ])
		
		depot.writeToDirectory(self._ldap)
		
		# Create product states container
		self.createOrganizationalRole("cn=%s,%s" % (hostId, self._productStatesContainerDn))
		self.createOrganizationalRole("cn=%s,%s" % (hostId, self._productsContainerDn))
		
		return hostId
	
	def getDepotIds_list(self): # OK
		search = None
		try:
			search = ObjectSearch(self._ldap, self.getHostContainerDn(), filter='(objectClass=opsiDepotserver)')
		except BackendMissingDataError:
			return []
		
		serverDns = search.getDns()
		ids = []
		for serverDn in serverDns:
			ids.append( self.getHostId(serverDn) )
		return ids
	
	def getDepotId(self, clientId=None):
		if clientId:
			clientId = self._preProcessHostId(clientId)
		return
	
	def getDepot_hash(self, depotId): # OK
		depotId = self._preProcessHostId(depotId)
		depot = Object( self.getHostDn(depotId) )
		if not depot.exists(self._ldap):
			raise BackendMissingDataError("Failed to get info for depot-id '%s': File '%s' not found" % (depotId, depotIniFile))
		
		depot.readFromDirectory(self._ldap)
		return {
			'depotLocalUrl':		depot.getAttribute('opsiDepotLocalUrl', ''),
			'depotRemoteUrl':		depot.getAttribute('opsiDepotRemoteUrl', ''),
			'repositoryLocalUrl':		depot.getAttribute('opsiRepositoryLocalUrl', ''),
			'repositoryRemoteUrl':		depot.getAttribute('opsiRepositoryRemoteUrl', ''),
			'network':			depot.getAttribute('opsiNetworkAddress', ''),
			'repositoryMaxBandwidth':	depot.getAttribute('opsiMaximumBandwidth', '0'),
			'description':			depot.getAttribute(self._hostAttributeDescription, ''),
			'notes':			depot.getAttribute(self._hostAttributeNotes, '')
		}
	
	def deleteDepot(self, depotId):
		depotId = self._preProcessHostId(depotId)
		if not depotId in self.getDepotIds_list():
			logger.error("Cannot delte depot '%s': does not exist" % depotId)
			return
		rmdir( os.path.join(self.__depotConfigDir, depotId), recursive=True )
		
	def getOpsiHostKey(self, hostId): # OK
		hostId = self._preProcessHostId(hostId)
		host = Object( self.getHostDn(hostId) )
		# Read client ldap-object from Backend (attribute opsiHostKey only)
		host.readFromDirectory(self._ldap, 'opsiHostKey')
		return host.getAttribute('opsiHostKey')
		
	def setOpsiHostKey(self, hostId, opsiHostKey): # OK
		hostId = self._preProcessHostId(hostId)
		logger.debug("Setting host key for host '%s'" % hostId)
		host = Object( self.getHostDn(hostId) )
		# Read client ldap-object from Backend
		host.readFromDirectory(self._ldap)
		# Set attribute to new value
		host.setAttribute('opsiHostKey', [ opsiHostKey ])
		# Write object to ldap
		host.writeToDirectory(self._ldap)
	
	def deleteOpsiHostKey(self, hostId): # OK
		hostId = self._preProcessHostId(hostId)
		logger.debug("Deleting host key for host '%s'" % hostId)
		host = Object( self.getHostDn(hostId) )
		# Read client ldap-object from Backend
		host.readFromDirectory(self._ldap)
		# Set attribute to new value
		host.setAttribute('opsiHostKey', [ ])
		# Write object to ldap
		host.writeToDirectory(self._ldap)
	
	def createGroup(self, groupId, members = [], description = ""): # OK
		if not re.search(GROUP_ID_REGEX, groupId):
			raise BackendBadValueError("Bad group-id: '%s'" % groupId)
		
		self.deleteGroup(groupId)
		
		# Create group object
		group = Object( "cn=%s,%s" % (groupId, self._groupsContainerDn) )
		group.new('opsiGroup')
		#search = ObjectSearch(self._ldap, self.getHostContainerDn(), filter='(objectClass=opsiClient)')
		if ( type(members) != type([]) and type(members) != type(()) ):
			members = [ members ]
		for member in members:
			group.addAttributeValue('uniqueMember', self.getHostDn(member))
		if description:
			group.setAttribute('description', [ description ])
		group.writeToDirectory(self._ldap)
		
	def getGroupIds_list(self): # OK
		try:
			search = ObjectSearch(self._ldap, self._groupsContainerDn, filter='(objectClass=opsiGroup)')
			groupIds = search.getCns()
			return groupIds
		except BackendMissingDataError, e:
			logger.warning("No groups found: %s" % e)
			return []
	
	def deleteGroup(self, groupId): # OK
		if not re.search(GROUP_ID_REGEX, groupId):
			raise BackendBadValueError("Bad group-id: '%s'" % groupId)
		
		# Create group object
		group = Object( "cn=%s,%s" % (groupId, self._groupsContainerDn) )
		
		# Delete group object from ldap if exists
		if group.exists(self._ldap):
			group.deleteFromDirectory(self._ldap)
	
	# -------------------------------------------------
	# -     PASSWORD FUNCTIONS                        -
	# -------------------------------------------------
	def getPcpatchPassword(self, hostId): # OK
		hostId = self._preProcessHostId(hostId)
		host = Object( self.getHostDn(hostId) )
		# Read client ldap-object from Backend (attribute opsiPcpatchPassword only)
		host.readFromDirectory(self._ldap, 'opsiPcpatchPassword')
		return host.getAttribute('opsiPcpatchPassword')
	
	def setPcpatchPassword(self, hostId, password): # OK
		hostId = self._preProcessHostId(hostId)
		host = Object( self.getHostDn(hostId) )
		# Read client ldap-object from Backend
		host.readFromDirectory(self._ldap)
		# Set attribute to new value
		host.setAttribute('opsiPcpatchPassword', [ password ])
		# Write object to ldap
		host.writeToDirectory(self._ldap)
		
	# -------------------------------------------------
	# -     PRODUCT FUNCTIONS                         -
	# -------------------------------------------------
	def createProduct(self, productType, productId, name, productVersion, packageVersion, licenseRequired=0,
			   setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
			   priority=0, description="", advice="", productClassNames=(), pxeConfigTemplate='', depotIds=[]): # OK
		""" Creates a new product. """
		
		if not re.search(PRODUCT_ID_REGEX, productId):
			raise BackendBadValueError("Unallowed chars in productId!")
		
		productId = productId.lower()
		
		if (productType == 'server'):
			logger.warning("Nothing to do for product type 'server'")
			return
		elif productType not in ['localboot', 'netboot']:
			raise BackendBadValueError("Unknown product type '%s'" % productType)
		
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			depotId = depotId.lower()
			self.createOrganizationalRole( 'cn=%s,%s' % (depotId, self._productStatesContainerDn) )
			self.createOrganizationalRole( 'cn=%s,cn=%s,%s' % (productType, depotId, self._productStatesContainerDn) )
			product = Object( "cn=%s,cn=%s,cn=%s,%s" % (productId, productType, depotId, self._productsContainerDn) )
			if product.exists(self._ldap):
				product.deleteFromDirectory(self._ldap, recursive = True)
			
			# Set product attributes
			product.setAttribute('opsiProductName', [ name ])
			
			if licenseRequired:
				product.setAttribute('opsiProductLicenseRequired', [ 'TRUE' ])
			else:
				product.setAttribute('opsiProductLicenseRequired', [ 'FALSE' ])
			
			product.setAttribute('opsiProductPriority', [ str(priority) ])
			product.setAttribute('opsiProductCreationTimestamp', [ Tools.timestamp() ])
			product.setAttribute('opsiProductVersion', [ str(productVersion) ])
			product.setAttribute('opsiPackageVersion', [ str(packageVersion) ])
			if setupScript:
				product.setAttribute('opsiSetupScript', [ setupScript ])
			if updateScript: 
				product.setAttribute('opsiUpdateScript', [ updateScript ])
			if uninstallScript: 
				product.setAttribute('opsiUninstallScript', [ uninstallScript ])
			if alwaysScript: 
				product.setAttribute('opsiAlwaysScript', [ alwaysScript ])
			if onceScript: 
				product.setAttribute('opsiOnceScript', [ onceScript ])
			if description: 
				product.setAttribute('description', [ description ])
			if advice: 
				product.setAttribute('opsiProductAdvice', [ advice ])
			if productClassNames:
				if ( type(productClassNames) != type(()) and type(productClassNames) != type([]) ):
					productClassNames = [ productClassNames ]
				for productClassName in productClassNames:
					if not productClassName:
						continue
					
					# Test if productClass exists
					productClass = Object( "cn=%s,%s" % ( productClassName, self._productClassesContainerDn ) )
					if productClass.exists(self._ldap):
						productClass.readFromDirectory(self._ldap, 'dn')
					else:
						# Product class does not exist => create it
						productClass.new('opsiProductClass')
						productClass.setAttribute('description', productClassName)
						productClass.writeToDirectory(self._ldap)
					product.addAttributeValue('opsiProductClassProvided', productClass.getDn())
			if pxeConfigTemplate and (productType == 'netboot'):
				product.setAttribute('opsiPxeConfigTemplate', [ pxeConfigTemplate ])
				
			# Write object to ldap
			product.writeToDirectory(self._ldap)
			
			# TODO: productStates
			#for clientId in self.getClientIds_list(serverId = None, depotId = depotId):
		
	def deleteProduct(self, productId, depotIds=[]): # OK
		productId = productId.lower()
		
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			depotId = depotId.lower()
			try:
				search = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId
				)
				product = search.getObject()
				product.deleteFromDirectory(self._ldap, recursive = True)
			except BackendMissingDataError,e:
				# Not found
				pass
		
	def getProduct_hash(self, productId, depotId=None): # OK
		productId = productId.lower()
		# Search product object
		search = ObjectSearch(
				self._ldap,
				"cn=%s,%s" % (depotId, self._productsContainerDn),
				filter='(&(objectClass=opsiProduct)(cn=%s))' % productId
		)
		product = search.getObject()
		product.readFromDirectory(self._ldap)
		
		# Product found => get all attributes
		attributes = product.getAttributeDict()
		if attributes.has_key('opsiProductClassProvided'):
			productClassIds = []
			productClassDns = attributes['opsiProductClassProvided']
			if ( type(productClassDns) != type(()) and type(productClassDns) != type([]) ):
				productClassDns = [productClassDns]
			for productClassDn in productClassDns:
				# Get cn from productClass if exists
				productClass = Object(productClassDn)
				try:
					productClass.readFromDirectory(self._ldap)
				except BackendIOError:
					logger.warning("ProductClass '%s' does not exist" % productClassDn)
					continue
				productClassIds.append(productClass.getAttribute('cn'))
			if productClassIds:
				attributes['opsiProductClassProvided'] = productClassIds
			else:
				del attributes['opsiProductClassProvided']
				
		# Return attributes as hash (dict)
		return {"name":				attributes.get('opsiProductName', ''),
			"description":			attributes.get('description', ''),
			"advice":			attributes.get('opsiProductAdvice', ''),
			"priority":			attributes.get('opsiProductPriority', 0),
			"licenseRequired":		attributes.get('opsiProductLicenseRequired') == 'TRUE',
			"productVersion":		attributes.get('opsiProductVersion', ''),
			"packageVersion":		attributes.get('opsiPackageVersion', ''),
			"creationTimestamp":		attributes.get('opsiProductCreationTimestamp', ''),
			"setupScript":			attributes.get('opsiSetupScript', ''),
			"uninstallScript":		attributes.get('opsiUninstallScript', ''),
			"updateScript":			attributes.get('opsiUpdateScript', ''),
			"onceScript":			attributes.get('opsiOnceScript', ''),
			"alwaysScript":			attributes.get('opsiAlwaysScript', ''),
			"productClassNames":		attributes.get('opsiProductClassProvided'),
			"pxeConfigTemplate":		attributes.get('opsiPxeConfigTemplate', '') }
	
	
	def getProductIds_list(self, productType=None, objectId=None, installationStatus=None): # OK
		
		productIds = []
		if not objectId:
			objectId = self.getDepotId()
		
		objectId = objectId.lower()
		
		if objectId in self.getDepotIds_list():
			
			objectClass = 'opsiProduct'
			if (productType == 'localboot'):
				objectClass = 'opsiLocalBootProduct'
			if (productType == 'netboot'):
				objectClass = 'opsiNetBootProduct'
			if (productType == 'server'):
				objectClass = 'opsiServerProduct'
			
			try:
				search = ObjectSearch(
						self._ldap,
						"cn=%s,%s" % (depotId, self._productsContainerDn),
						filter = '(objectClass=%s)' % objectClass
				)
				productIds.extend( search.getCns() )
			except BackendMissingDataError, e:
				logger.warning("No products found (objectClass: %s)" % objectClass)
		
		else:
			# Get host object
			host = Object( self.getHostDn(objectId) )
			
			productStates = []
			try:
				filter='(objectClass=opsiProductState)'
				if installationStatus:
					filter='(&(objectClass=opsiProductState)(opsiProductInstallationStatus=%s))' % installationStatus
				
				productStateSearch = ObjectSearch(
							self._ldap,
							'cn=%s,%s' % (objectId, self._productStatesContainerDn),
							filter = filter )
				productStates = productStateSearch.getObjects()
			except BackendMissingDataError:
				return productIds
			
			for productState in productStates:
				productState.readFromDirectory(self._ldap)
				try:
					if ( productState.getAttribute('opsiProductReference') ):
						# Get product's cn (productId)
						product = Object( productState.getAttribute('opsiProductReference') )
						product.readFromDirectory(self._ldap, 'objectClass')
						logger.debug("Object classes of '%s': %s" \
							% (product.getDn(), product.getObjectClasses()))
						if (objectClass == 'opsiProduct') or objectClass in product.getObjectClasses():
							productIds.append( product.getCn() )
				except (BackendMissingDataError, BackendIOError):
					continue
		
		logger.debug("Products matching installationStatus '%s' on objectId '%s': %s" \
						% (installationStatus, objectId, productIds))
		return productIds
	
	
	def getProductInstallationStatus_hash(self, productId, objectId): # OK
		productId = productId.lower()
		objectId = objectId.lower()
		
		status = { 
			'productId':		productId,
			'installationStatus':	'not_installed',
			'productVersion':	'',
			'packageVersion':	'',
			'lastStateChange':	'',
			'deploymentTimestamp':	'' }
			
		if objectId in self.getDepotIds_list():
			if productId in self.getProductIds_list(None, objectId):
				status['installationStatus'] = 'installed'
				p = self.getProduct_hash(productId)
				status['productVersion'] = p['productVersion']
				status['packageVersion'] = p['packageVersion']
				status['lastStateChange'] = p['creationTimestamp']
			return status
		
		productState = Object('cn=%s,cn=%s,%s' % (productId, objectId, self._productStatesContainerDn))
		if not productState.exists(self._ldap):
			return status
		
		# Get all attributes
		productState.readFromDirectory(self._ldap)
		attributes = productState.getAttributeDict()
		
		status['installationStatus'] = attributes.get('opsiProductInstallationStatus', 'not_installed')
		status['productVersion'] = 	attributes.get('opsiProductVersion')
		status['packageVersion'] = 	attributes.get('opsiPackageVersion')
		status['lastStateChange'] = 	attributes.get('lastStateChange')
		status['deploymentTimestamp'] = attributes.get('opsiProductDeploymentTimestamp')
		
		return status
	
	def getProductInstallationStatus_listOfHashes(self, objectId): # OK
		objectId = objectId.lower()
		
		installationStatus = []
		
		if objectId in self.getDepotIds_list():
			for productId in self.getProductIds_list(None, objectId):
				p = self.getProduct_hash(productId)
				installationStatus.append( { 
					'productId':		productId,
					'productVersion':	p['productVersion'],
					'packageVersion':	p['packageVersion'],
					'lastStateChange':	p['creationTimestamp'],
					'installationStatus':	'installed'
				} )
			return installationStatus
		
		for productId in self.getProductIds_list(None, self.getDepotId(objectId)):
			installationStatus.append( { 
					'productId':		productId,
					'installationStatus':	'undefined',
					'actionRequest':	'undefined',
					'productVersion':	'',
					'packageVersion':	'',
					'lastStateChange':	'' 
			} )
		
		productStateSearch = None
		try:
			productStateSearch = ObjectSearch(
				self._ldap,
				'cn=%s,%s' % (objectId, self._productStatesContainerDn),
				filter = '(objectClass=opsiProductState)' )
		except BackendMissingDataError:
			return installationStatus
		
		for productState in productStateSearch.getObjects():
			productState.readFromDirectory(self._ldap)
			attributes = productState.getAttributeDict()
			product = Object( productState.getAttribute('opsiProductReference') )
			productId = product.getCn()
			installationStatus.append( 
					{ 'productId':			productId,
					  'installationStatus': 	attributes.get('opsiProductInstallationStatus', 'not_installed'),
					  'productVersion':		attributes.get('opsiProductVersion'),
					  'packageVersion':		attributes.get('opsiPackageVersion'),
					  'lastStateChange':		attributes.get('lastStateChange'),
					  'deploymentTimestamp':	attributes.get('opsiProductDeploymentTimestamp')
					} )
		return installationStatus
		
	
	def setProductState(self, productId, objectId, installationStatus="", actionRequest="", productVersion="", packageVersion="", lastStateChange="", licenseKey=""): # OK
		productId = productId.lower()
		
		if objectId in self.getDepotIds_list():
			return
		
		depotId = self.getDepotId(objectId)
		
		productType = None
		if productId in self.getProductIds_list('netboot', depotId):
			productType = 'netboot'
		elif productId in self.getProductIds_list('localboot', depotId):
			productType = 'localboot'
		else:
			raise Exception("product '%s': is neither localboot nor netboot product" % productId)
		
		if not installationStatus:
			installationStatus = 'undefined'
		if not installationStatus in getPossibleProductInstallationStatus():
			raise BackendBadValueError("InstallationStatus has unsupported value '%s'" %  installationStatus )
		
		if not actionRequest:
			actionRequest = 'undefined'
		if not actionRequest in getPossibleProductActions():
			raise BackendBadValueError("ActionRequest has unsupported value '%s'" % actionRequest)
		
		if not lastStateChange:
			lastStateChange = Tools.timestamp()
		
		product = None
		try:
			search = ObjectSearch(
				self._ldap,
				"cn=%s,%s" % (depotId, self._productsContainerDn),
				filter='(&(objectClass=opsiProduct)(cn=%s))' % productId
			)
			product = search.getObject()
			product.readFromDirectory(self._ldap, 'opsiProductVersion', 'opsiPackageVersion')
		except Exception, e:
			raise BackendBadValueError("Product '%s' does not exist: %s" % (productId, e))
		
		# Create productState container for selected host
		self.createOrganizationalRole( 'cn=%s,%s' % (objectId, self._productStatesContainerDn) )
		
		# Create or load productState object and set the needed attributes
		productState = Object( 'cn=%s,cn=%s,%s' % (productId, objectId, self._productStatesContainerDn) )
		if productState.exists(self._ldap):
			productState.readFromDirectory(self._ldap)
		else:
			productState.new('opsiProductState')
		
		currentInstallationStatus = productState.getAttribute('opsiProductInstallationStatus', '')
		currentActionRequest = productState.getAttribute('opsiProductActionRequestForced', '')
		
		if not productVersion:
			productVersion = ''
			if   (installationStatus == 'installed') or (installationStatus == 'uninstalled') or \
			     (installationStatus == 'installing') or (installationStatus == 'failed'):
				     productVersion = product.getAttribute('opsiProductVersion', '')
			elif (installationStatus == 'undefined') and \
			     ( (currentInstallationStatus == 'installed') or (currentInstallationStatus == 'uninstalled') or \
			       (currentInstallationStatus == 'installing') or (currentInstallationStatus == 'failed') ):
				     productVersion = productState.getAttribute('opsiProductVersion', '')
		
		if not packageVersion:
			packageVersion = ''
			if   (installationStatus == 'installed') or (installationStatus == 'uninstalled') or \
			     (installationStatus == 'installing') or (installationStatus == 'failed'):
				     packageVersion = product.getAttribute('opsiPackageVersion', '')
			elif (installationStatus == 'undefined') and \
			     ( (currentInstallationStatus == 'installed') or (currentInstallationStatus == 'uninstalled') or \
			       (currentInstallationStatus == 'installing') or (currentInstallationStatus == 'failed') ):
				     packageVersion = productState.getAttribute('opsiPackageVersion', '')
		
		if (installationStatus == 'undefined') and currentInstallationStatus:
			installationStatus = currentInstallationStatus
		
		if (actionRequest == 'undefined') and currentActionRequest:
			actionRequest = currentActionRequest
		
		logger.info("Setting product installation status '%s', product action request '%s' for product '%s'" \
					% (installationStatus, actionRequest, productId))
		
		#if (installationStatus != 'undefined') or not productState.getAttribute('opsiProductInstallationStatus', False):
		#	productState.setAttribute( 'opsiProductInstallationStatus', [ installationStatus ] )
		#
		#if (actionRequest == 'undefined') or actionRequest.endswith('by_policy'):
		#	# Do not store, because this would overwrite actionRequests resulting from productDeploymentPolicies
		#	productState.setAttribute( 'opsiProductActionRequestForced', [  ] )
		#else:
		#	productState.setAttribute( 'opsiProductActionRequestForced', [ actionRequest ] )
		
		productState.setAttribute( 'opsiProductActionRequestForced', [ actionRequest ] )
		
		productState.setAttribute( 'opsiHostReference', 	[ self.getHostDn(objectId) ] )
		productState.setAttribute( 'opsiProductReference', 	[ product.getDn() ] )
		productState.setAttribute( 'lastStateChange', 		[ lastStateChange ] )
		
		logger.info("Setting product version '%s', package version '%s' for product '%s'" \
					% (productVersion, packageVersion, productId))
		
		productState.setAttribute( 'opsiProductVersion', 	[ productVersion ] )
		productState.setAttribute( 'opsiPackageVersion', 	[ packageVersion ] )
		
		productState.writeToDirectory(self._ldap)
		
		return
		###############################################################
		# Get licenseReference by licenseKey
		#licenseReference = None
		#if licenseKey:
		#	search = ObjectSearch(self._ldap, "cn=%s,%s" % (product.getCn(), self._productLicensesContainerDn), 
		#				filter='(&(objectClass=opsiProductLicense)(licenseKey=%s))' % licenseKey)
		#	licenseReference = search.getDn()
		#
		## Get deploymentPolicy timestamp
		#deploymentTimestamp = None
		#deploymentPolicy = None
		#if policyId:
		#	deploymentPolicy = Object(deploymentPolicyDn)
		#	deploymentPolicy.readFromDirectory(self._ldap, 'opsiProductDeploymentTimestamp')
		#	deploymentTimestamp = deploymentPolicy.getAttribute('opsiProductDeploymentTimestamp')
		
		## Search for actionRequests resulting from policies
		#if actionRequest:
		#	policyActionRequest = None
		#	try:
		#		policySearch = PolicySearch(	self._ldap, host.getDn(),
		#					policyContainer = self._productDeploymentPoliciesContainerDn,
		#					policyFilter = '(&(objectClass=opsiPolicyProductDeployment)(opsiProductReference=%s))' % product.getDn(),
		#					independenceAttribute = 'cn',
		#					policyReferenceObjectClass = self._policyReferenceObjectClass,
		#					policyReferenceAttributeName = self._policyReferenceAttributeName )
		#		
		#		policyActionRequest = self._getProductActionRequestFromPolicy(policySearch.getObject(), host.getDn())
		#	
		#	except BackendMissingDataError, e:
		#		# No deployment policy exists for host and product
		#		pass
		#	
		#	if (policyActionRequest and policyActionRequest == actionRequest):
		#		# ActionRequest matches action resulting from policy => not forcing an actionRequest !
		#		logger.info("Will not force actionRequest '%s', policy produces the same actionRequest." % actionRequest)
		#		actionRequest = ''
		#
		#if installationStatus in ['not_installed', 'uninstalled']:
		#	logger.info("License key assignement for host '%s' and product '%s' removed" \
		#							% (objectId, productId) )
		#	productState.setAttribute( 'licenseReference', [ ] )
		#elif licenseReference:
		#	productState.setAttribute( 'licenseReference', [ licenseReference ] )
		#
		#if deploymentPolicy:
		#	productState.setAttribute( 'opsiProductDeploymentPolicyReference', [ deploymentPolicy.getDn() ] )
		#if deploymentTimestamp:
		#	productState.setAttribute( 'opsiProductDeploymentTimestamp', [ deploymentTimestamp ] )	
		#
		#productState.writeToDirectory(self._ldap)
		
	def setProductInstallationStatus(self, productId, objectId, installationStatus, policyId="", licenseKey=""): # OK
		self.setProductState(productId, objectId, installationStatus = installationStatus, licenseKey = licenseKey)
	
	def getPossibleProductActions_list(self, productId=None, depotId=None): # OK
		
		if not productId:
			return POSSIBLE_FORCED_PRODUCT_ACTIONS
		productId = productId.lower()
		
		if not depotId:
			depotId = self.getDepotId()
		depotId = depotId.lower()
		
		actions = ['none'] # ['none', 'by_policy']
		# Get product object
		search = ObjectSearch(
				self._ldap,
				"cn=%s,%s" % (depotId, self._productsContainerDn),
				filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
		product = search.getObject()
		
		# Read needed product object values from ldap
		product.readFromDirectory(self._ldap, 'opsiSetupScript', 'opsiUninstallScript', 'opsiUpdateScript', 'opsiOnceScript', 'opsiAlwaysScript')
		
		# Get all attributes
		attributes = product.getAttributeDict()
		
		# If correspondent script exists action is possible
		if attributes.has_key('opsiSetupScript'):	actions.append('setup')
		if attributes.has_key('opsiUninstallScript'):	actions.append('uninstall')
		if attributes.has_key('opsiUpdateScript'):	actions.append('update')
		if attributes.has_key('opsiOnceScript'):	actions.append('once')
		if attributes.has_key('opsiAlwaysScript'):	actions.append('always')
		
		return actions
	
	
	def getPossibleProductActions_hash(self, depotId=None): # OK
		
		if not depotId:
			depotId = self.getDepotId()
		depotId = depotId.lower()
		
		actions = {}
		# Get product objects
		try:
			search = ObjectSearch(
				self._ldap,
				"cn=%s,%s" % (depotId, self._productsContainerDn),
				filter='(objectClass=opsiProduct)')
		except Exception, e:
			logger.warning("No products found: %s" % e)
			return actions
		
		for product in search.getObjects():
			# Read needed product object values from ldap
			product.readFromDirectory(self._ldap, 'opsiSetupScript', 'opsiUninstallScript', 'opsiUpdateScript', 'opsiOnceScript', 'opsiAlwaysScript')
			
			actions[product.getCn()] = ['none'] #['none', 'by_policy']
			
			# Get all attributes
			attributes = product.getAttributeDict()
			
			# If correspondent script exists actin is possible
			if attributes.has_key('opsiSetupScript'):	actions[product.getCn()].append('setup')
			if attributes.has_key('opsiUninstallScript'):	actions[product.getCn()].append('uninstall')
			if attributes.has_key('opsiUpdateScript'):	actions[product.getCn()].append('update')
			if attributes.has_key('opsiOnceScript'):	actions[product.getCn()].append('once')
			if attributes.has_key('opsiAlwaysScript'):	actions[product.getCn()].append('always')
		
		return actions
	
	def getProductActionRequests_listOfHashes(self, clientId): # OK
		
		clientId = self._preProcessHostId(clientId)
		
		actionRequests = []
		productStates = []
		try:
			productStateSearch = ObjectSearch(
						self._ldap, 
						'cn=%s,%s' % (clientId, self._productStatesContainerDn), 
						filter='objectClass=opsiProductState')
			productStates = productStateSearch.getObjects()
		except BackendMissingDataError, e:
			logger.warning("No product states found for client '%s': %s" % (clientId, e))
		
		for productState in productStates:
			actionRequest = ''
			try:
				# Read productState object from ldap
				productState.readFromDirectory(self._ldap)
				actionRequest = productState.getAttribute('opsiProductActionRequestForced')
			except BackendMissingDataError:
				continue
			
			if (actionRequest == 'undefined'):
				continue
			
			# An actionRequest is forced
			product = Object( productState.getAttribute('opsiProductReference') )
			actionRequests.append( { 'productId': 		product.getCn(), 
						  'actionRequest': 	actionRequest } )
		
		return actionRequests
		
	
	def getDefaultNetBootProductId(self, clientId): # OK
		
		clientId = self._preProcessHostId(clientId)
		
		netBootProduct = self.getGeneralConfig(clientId).get('os')
		
		if not netBootProduct:
			raise BackendMissingDataError("No default netboot product for client '%s' found in generalConfig" % clientId )
		return netBootProduct
	
	def setProductActionRequest(self, productId, clientId, actionRequest): # OK
		self.setProductState(productId, clientId, actionRequest = actionRequest)
	
	def unsetProductActionRequest(self, productId, clientId): # OK
		self.setProductState(productId, clientId, actionRequest="none")
	
	def _getProductStates_hash(self, objectIds = [], productType = None): # OK
		result = {}
		if not objectIds or ( (len(objectIds) == 1) and not objectIds[0] ):
			objectIds = self.getClientIds_list()
		elif ( type(objectIds) != type([]) and type(objectIds) != type(()) ):
			objectIds = [ objectIds ]
		
		depotIds = self.getDepotIds_list()
		
		objectClass = 'opsiProduct'
		if (productType == 'localboot'):
			objectClass = 'opsiLocalBootProduct'
		if (productType == 'netboot'):
			objectClass = 'opsiNetBootProduct'
		if (productType == 'server'):
			objectClass = 'opsiServerProduct'
		
		for objectId in objectIds:
			objectId = objectId.lower()
			result[objectId] = []
			
			logger.info("Getting product states for host '%s'" % objectId)
			
			isDepot = (objectId in depotIds)
			depotId = objectId
			if not isDepot:
				depotId = self.getDepotId(objectId)
			
			search = None
			try:
				search = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(objectClass=%s)' % objectClass
				)
			except BackendMissingDataError, e:
				logger.warning("No products found for depot '%s' (objectClass: %s)" % (depotId, objectClass))
				continue
				
			for product in search.getObjects():
				product.readFromDirectory(self._ldap, 'opsiProductVersion', 'opsiPackageVersion', 'opsiProductCreationTimestamp')
				productId = product.getCn()
				if isDepot:
					result[objectId].append( { 	'productId':		productId, 
									'installationStatus':	'installed',
									'actionRequest':	'none',
									'productVersion':	product.getAttribute('opsiProductVersion', ''),
									'packageVersion':	product.getAttribute('opsiPackageVersion', ''),
									'lastStateChange':	product.getAttribute('opsiProductCreationTimestamp') } )
				else:
					state = { 	'productId':		productId, 
							'installationStatus':	'undefined',
							'actionRequest':	'undefined',
							'productVersion':	product.getAttribute('opsiProductVersion', ''),
							'packageVersion':	product.getAttribute('opsiPackageVersion', ''),
							'lastStateChange':	'' }
					
					try:
						# Not using opsiProductReference in search because
						# this could miss some products if client moved from an other depot
						productStateSearch = ObjectSearch(
									self._ldap, 
									'cn=%s,%s' % (objectId, self._productStatesContainerDn),
									filter='(&(objectClass=opsiProductState)(cn=%s))' % productId)
						productState = productStateSearch.getObject()
						state['actionRequest'] = productState.getAttribute('opsiProductActionRequestForced', 'undefined')
						state['installationStatus'] = productState.getAttribute('opsiProductInstallationStatus', 'undefined')
						state['productVersion'] = productState.getAttribute('opsiProductVersion', '')
						state['packageVersion'] = productState.getAttribute('opsiPackageVersion', '')
						state['lastStateChange'] = productState.getAttribute('lastStateChange', '')
						state['deploymentTimestamp'] = productState.getAttribute('opsiProductDeploymentTimestamp', '')
					except BackendMissingDataError, e:
						pass
					result[objectId].append( state )
		return result
		
	def getNetBootProductStates_hash(self, objectIds = []): # OK
		return self._getProductStates_hash(objectIds, 'netboot')
		
	def getLocalBootProductStates_hash(self, objectIds = []): # OK
		return self._getProductStates_hash(objectIds, 'localboot')
		
	def getProductStates_hash(self, objectIds = []): # OK
		return self._getProductStates_hash(objectIds)
	
	def getProductPropertyDefinitions_hash(self, depotId=None): # OK
		if not depotId:
			depotId = self.getDepotId()
		depotId = depotId.lower()
		
		definitions = {}
		
		# Search product property definitions
		search = None
		try:
			search = ObjectSearch(	self._ldap, 
						'cn=%s,%s' % (depotId, self._productsContainerDn),
						filter='objectClass=opsiProductPropertyDefinition')
		except BackendMissingDataError:
			logger.info("No ProductPropertyDefinitions found")
			return definitions
		
		for propertyDefinition in search.getObjects():
			propertyDefinition.readFromDirectory(self._ldap)
			productId = propertyDefinition.getParent().getParent().getCn()
			
			definition = {	"name":	
						propertyDefinition.getAttribute("opsiProductPropertyName").lower(),
					"description":	
						propertyDefinition.getAttribute("description", ""),
					"default":	
						propertyDefinition.getAttribute("opsiProductPropertyDefaultValue", None),
					"values":
						propertyDefinition.getAttribute("opsiProductPropertyPossibleValue", [], valuesAsList=True),
				}
			
			if not definitions.has_key(productId):
				definitions[productId] = []
			
			definitions[productId].append(definition)
		
		return definitions
	
	def getProductPropertyDefinitions_listOfHashes(self, productId, depotId=None): # OK
		productId = productId.lower()
		if not depotId:
			depotId = self.getDepotId()
		depotId = depotId.lower()
		
		definitions = []
		
		# Search product property definition
		search = None
		try:
			productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
			product = productSearch.getObject()
			
			search = ObjectSearch(	self._ldap, 
						"cn=productPropertyDefinitions,%s" % product.getDn(),
						filter='(objectClass=opsiProductPropertyDefinition)')
		except BackendMissingDataError:
			logger.info("No ProductPropertyDefinitions found for product '%s'" % productId)
			return definitions
		
		for propertyDefinition in search.getObjects():
			propertyDefinition.readFromDirectory(self._ldap)
			definitions.append(
				{	"name":	
						propertyDefinition.getAttribute("opsiProductPropertyName").lower(),
					"description":	
						propertyDefinition.getAttribute("description", ""),
					"default":	
						propertyDefinition.getAttribute("opsiProductPropertyDefaultValue", None),
					"values":
						propertyDefinition.getAttribute("opsiProductPropertyPossibleValue", [], valuesAsList=True),
				}
			)
		
		return definitions
	
	def deleteProductPropertyDefinition(self, productId, name, depotIds=[]): # OK
		productId = productId.lower()
		name = name.lower()
		
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			depotId = depotId.lower()
			
			# Search product property object
			search = None
			try:
				productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
				product = productSearch.getObject()
				
				search = ObjectSearch(	self._ldap, 
							"cn=productPropertyDefinitions,%s" % product.getDn(),
							filter='(&(objectClass=opsiProductPropertyDefinition)(cn=%s))' % name)
				
			except BackendMissingDataError, e:
				logger.warning("ProductPropertyDefinition '%s' not found for product '%s' on depot '%s': %s" % (name, productId, depotId, e))
				continue
			
			search.getObject().deleteFromDirectory(self._ldap)
			
			# Delete productPropertyDefinitions container if empty
			self.deleteChildlessObject("cn=productPropertyDefinitions,cn=%s,cn=%s,%s" % (productId, depotId, self._productsContainerDn))
		
	
	def deleteProductPropertyDefinitions(self, productId, depotIds=[]): # OK
		
		productId = productId.lower()
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			depotId = depotId.lower()
			try:
				productSearch = ObjectSearch(
						self._ldap,
						"cn=%s,%s" % (depotId, self._productsContainerDn),
						filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
				product = productSearch.getObject()
				
				container = Object("cn=productPropertyDefinitions,%s" % product.getDn())
				if container.exists(self._ldap):
					container.deleteFromDirectory(self._ldap, recursive = True)
				
			except BackendMissingDataError, e:
				continue
		
	def createProductPropertyDefinition(self, productId, name, description=None, defaultValue=None, possibleValues=[], depotIds=[]): # OK
		productId = productId.lower()
		name = name.lower()
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			depotId = depotId.lower()
			
			# Search product object
			search = None
			try:
				search = ObjectSearch(	self._ldap,
							'cn=%s,%s' % (depotId, self._productsContainerDn),
							filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
				product = search.getObject()
			except BackendMissingDataError:
				logger.warning("Failed to create productPropertyDefinition '%s': product '%s' not found on depot '%s'" \
							% (name, productId, depotId))
				continue
			
			# Create productPropertyDefinitions container beneath product object
			containerDn = "cn=productPropertyDefinitions,%s" % product.getDn()
			self.createOrganizationalRole(containerDn)
			
			# Create ProductPropertyDefinition object
			propertyDefinition = Object("cn=%s,%s" % (name, containerDn))
			
			# Delete ProductPropertyDefinition from ldap if exists
			if propertyDefinition.exists(self._ldap):
				propertyDefinition.deleteFromDirectory(self._ldap)
			
			propertyDefinition.new('opsiProductPropertyDefinition')
			propertyDefinition.setAttribute('opsiProductReference', [ product.getDn() ])
			propertyDefinition.setAttribute('opsiProductPropertyName', [ name ])
			if description:
				propertyDefinition.setAttribute('description', [ description ])
			if defaultValue:
				propertyDefinition.setAttribute('opsiProductPropertyDefaultValue', [ defaultValue ])
			if  possibleValues:
				propertyDefinition.setAttribute('opsiProductPropertyPossibleValue', possibleValues)
			
			propertyDefinition.writeToDirectory(self._ldap)
		
	def getProductProperties_hash(self, productId, objectId = None): # OK
		productId = productId.lower()
		
		if not objectId:
			objectId = self.getDepotId()
		objectId = objectId.lower()
		
		properties = {}
		
		if objectId in self.getDepotIds_list():
			for prop in self.getProductPropertyDefinitions_listOfHashes(productId, objectId):
				properties[prop['name'].lower()] = prop.get('default')
			return properties
		
		for prop in self.getProductPropertyDefinitions_listOfHashes(productId, self.getDepotId(objectId)):
			properties[prop['name'].lower()] = prop.get('default')
		
		productProperty = Object("cn=%s,cn=%s,%s" % (productId, objectId, self._productPropertiesContainerDn))
		if productProperty.exists(self._ldap):
			for (key, value) in productProperty.getAttributeDict(unpackOpsiKeyValuePairs=True).items():
				if key.lower() in properties.keys():
					properties[key.lower()] = value
		return properties
	
	
	def setProductProperties(self, productId, properties, objectId = None): # OK
		productId = productId.lower()
		
		props = {}
		for (key, value) in properties.items():
			props[key.lower()] = value
		properties = props
		
		if not objectId:
			objectId = self.getDepotId()
		objectId = objectId.lower()
		
		if objectId in self.getDepotIds_list():
			propDefs = self.getProductPropertyDefinitions_listOfHashes(productId, objectId)
			self.deleteProductPropertyDefinitions(productId, depotIds=[ objectId ])
			for i in range(len(propDefs)):
				if properties.has_key(propDefs[i]['name'].lower()):
					propDefs[i]['default'] = properties[propDefs[i]['name'].lower()]
				self.createProductPropertyDefinition(
							productId = 		productId, 
							name = 			propDefs[i]['name'].lower(),
							description = 		propDefs[i].get('description'),
							defaultValue =		propDefs[i].get('default'),
							possibleValues =	propDefs[i].get('values'),
							depotIds =		[ objectId ])
		else:
			productProperty = Object("cn=%s,cn=%s,%s" % (productId, objectId, self._productPropertiesContainerDn))
			if productProperty.exists(self._ldap):
				productProperty.deleteFromDirectory(self._ldap)
			productProperty.new('opsiProductProperty')
			for (key, value) in properties.items():
				productProperty.addAttributeValue('opsiKeyValuePair', '%s=%s' % (key, value))
			productProperty.writeToDirectory(self._ldap)
		
	def deleteProductProperty(self, productId, property, objectId = None): # OK
		productId = productId.lower()
		property = property.lower()
		if not objectId:
			objectId = self.getDepotId()
		objectId = objectId.lower()
		
		clientIds = [ objectId ]
		if objectId in self.getDepotIds_list():
			self.deleteProductPropertyDefinition(productId = productId, name = property, depotIds = [ objectId ])
			clientIds = self.getClientIds_list(None, objectId)
		
		for clientId in clientIds:
			productProperty = Object("cn=%s,cn=%s,%s" % (productId, objectId, self._productPropertiesContainerDn))
			if not productProperty.exists(self._ldap):
				logger.warning("Failed to delete productProperty '%s', productId '%s' for client '%s': opsiProductProperty object not found" \
							% (property, productId, clientId))
			productProperty.readFromDirectory(self._ldap)
			opsiKeyValuePairs = productProperty.getAttribute('opsiKeyValuePairs', [], valuesAsList=True)
			newOpsiKeyValuePairs = []
			for opsiKeyValuePair in opsiKeyValuePairs:
				if (opsiKeyValuePair.split('=', 1)[0].lower() != property):
					newOpsiKeyValuePairs.append(opsiKeyValuePair)
			productProperty.setAttribute('opsiKeyValuePairs', newOpsiKeyValuePairs)
			productProperty.writeToDirectory(self._ldap)
	
	def deleteProductProperties(self, productId, objectId = None): # OK
		productId = productId.lower()
		if not objectId:
			objectId = self.getDepotId()
		objectId = objectId.lower()
		
		clientIds = [ objectId ]
		if objectId in self.getDepotIds_list():
			try:
				productSearch = ObjectSearch(
						self._ldap,
						"cn=%s,%s" % (depotId, self._productsContainerDn),
						filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
				product = productSearch.getObject()
				
				container = Object("cn=productPropertyDefinitions,%s" % product.getDn())
				if container.exists(self._ldap):
					container.deleteFromDirectory(self._ldap, recursive = True)
				clientIds = self.getClientIds_list(None, objectId)
			except BackendMissingDataError, e:
				pass
		
		for clientId in clientIds:
			productProperty = Object("cn=%s,cn=%s,%s" % (productId, objectId, self._productPropertiesContainerDn))
			if productProperty.exists(self._ldap):
				productProperty.deleteFromDirectory(self._ldap)
		
	def getProductDependencies_listOfHashes(self, productId = None, depotId=None): # OK
		if productId:
			productId = productId.lower()
		
		if not depotId:
			depotId = self.getDepotId()
		
		productSearch = None
		# Search product objects
		if productId:
			productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
		else:
			productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(objectClass=opsiProduct)')
		
		dependencyList = []
		for product in productSearch.getObjects():
			# Search for product(class) dependencies
			dependencies = []
			try:
				dependencySearch = ObjectSearch(
							self._ldap,
							"cn=productDependencies,%s" % product.getDn(),
							filter='(objectClass=opsiProductDependency)')
				dependencies.extend( dependencySearch.getObjects() )
			except BackendMissingDataError, e:
				# No product dependencies found
				logger.info("No product dependencies found for product '%s'" % product.getCn())
			
			try:
				dependencySearch = ObjectSearch(
							self._ldap,
							"cn=productClassDependencies,%s" % product.getDn(),
							filter='(objectClass=opsiProductClassDependency)')
				dependencies.extend( dependencySearch.getObjects() )
			
			except BackendMissingDataError, e:
				# No productclass dependencies found
				logger.info("No productclass dependencies found for product '%s'" % product.getCn())
			
			for dependency in dependencies:
				# Read dependency object from ldap
				dependency.readFromDirectory(self._ldap)
				try:
					action = dependency.getAttribute('opsiActionRequired')
				except BackendMissingDataError, e:
					action = ''
				try:
					installationStatus = dependency.getAttribute('opsiInstallationStatusRequired')
				except BackendMissingDataError, e:
					installationStatus = ''
				try:
					requirementType = dependency.getAttribute('opsiRequirementType')
				except BackendMissingDataError, e:
					requirementType = ''
				
				dep = { 'productId': product.getCn(),
					'action': dependency.getAttribute('opsiProductAction'),
					'requiredAction': action,
					'requiredInstallationStatus': installationStatus,
					'requirementType': requirementType }
				
				if ( 'opsiProductClassDependency' in dependency.getObjectClasses() ):
					# Dependency is a productclass dependency
					p = Object( dependency.getAttribute('opsiRequiredProductClassReference') )
					dep['requiredProductClassId'] = p.getCn()
				else:
					# Dependency is a product dependency
					p = Object( dependency.getAttribute('opsiRequiredProductReference') )
					dep['requiredProductId'] = p.getCn()
				
				logger.debug("Adding dependency: %s" % dep)
				dependencyList.append( dep )
			
		# Return all dependencies as a list of hashes (dicts)
		return dependencyList
	
	def createProductDependency(self, productId, action, requiredProductId="", requiredProductClassId="", requiredAction="", requiredInstallationStatus="", requirementType="", depotIds=[]): # OK
		
		productId = productId.lower()
		requiredProductId = requiredProductId.lower()
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		try:
			pd = ProductDependency(productId, action, requiredProductId, requiredProductClassId, 
						requiredAction, requiredInstallationStatus, requirementType)
		except Exception, e:
			raise BackendBadValueError(e)
		
		for depotId in depotIds:
			productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
			product = productSearch.getObject()
			
			requiredProduct = None
			requiredProductClass = None
			containerDn = None
			dn = None
			cn = None
			
			if pd.requiredProductId:
				containerDn = "cn=productDependencies,%s" % product.getDn()
				dn = "cn=%s,%s" % (pd.requiredProductId, self._productsContainerDn)
				#requiredProduct.readFromDirectory(self._ldap, 'dn') # Test if exists
				cn = requiredProduct.getCn()
				requiredProduct = Object( dn )
			else:
				containerDn = "cn=productClassDependencies,%s" % product.getDn()
				dn = "cn=%s,%s" % (pd.requiredProductClassId, self._productsContainerDn)
				requiredProductClass = Object( dn )
				#requiredProductClass.readFromDirectory(self._ldap, 'dn') # Test if exists
				cn = requiredProductClass.getCn()
			
			self.createOrganizationalRole(containerDn)
			
			# Dependency object
			productDependency = Object("cn=%s,cn=%s,%s" % (cn, action, containerDn))
			if productDependency.exists(self._ldap):
				productDependency.deleteFromDirectory(self._ldap)
			
			# Set dependency's objectClass
			if requiredProduct:
				productDependency.new('opsiProductDependency')
				productDependency.setAttribute('opsiRequiredProductReference', [ dn ])
			else:
				productDependency.new('opsiProductClassDependency')
				productDependency.setAttribute('opsiRequiredProductClassReference', [ dn ])
			
			# Set dependency's attributes
			productDependency.setAttribute('opsiProductReference', [ product.getDn() ])
			
			productDependency.setAttribute('opsiProductAction', [ pd.action ])
			if requiredAction:
				productDependency.setAttribute('opsiActionRequired', [ pd.requiredAction ])
				productDependency.setAttribute('opsiInstallationStatusRequired', [])
			if requiredInstallationStatus:
				productDependency.setAttribute('opsiActionRequired', [ ])
				productDependency.setAttribute('opsiInstallationStatusRequired', [ pd.requiredInstallationStatus ])
			if requirementType:
				productDependency.setAttribute('opsiRequirementType', [ pd.requirementType ])
			
			# Write dependency to ldap
			productDependency.writeToDirectory(self._ldap)
	
	def deleteProductDependency(self, productId, action="", requiredProductId="", requiredProductClassId="", requirementType="", depotIds=[]): # OK
		productId = productId.lower()
		requiredProductId = requiredProductId.lower()
		
		if action and not action in getPossibleProductActions():
			raise BackendBadValueError("Action '%s' is not known" % action)
		#if not requiredProductId and not requiredProductClassId:
		#	raise BackendBadValueError("Either a required product or a required productClass must be set")
		if requirementType and requirementType not in getPossibleRequirementTypes():
			raise BackendBadValueError("Requirement type '%s' is not known" % requirementType)
		
		if not depotIds:
			depotIds = self.getDepotIds_list()
		
		for depotId in depotIds:
			productSearch = ObjectSearch(
					self._ldap,
					"cn=%s,%s" % (depotId, self._productsContainerDn),
					filter='(&(objectClass=opsiProduct)(cn=%s))' % productId )
			product = productSearch.getObject()
			
			# Search dependency objects
			productDependencies = []
			
			if not action:
				action = "*"
			if not requiredProductId and not requiredProductClassId:
				requiredProductId = "*"
				requiredProductClassId = "*"
			if not requirementType:
				requirementType = "*"
			
			if requiredProductId:
				try:
					search = ObjectSearch(
						self._ldap,
						product.getDn(), 
						filter = '(&(&(&(objectClass=opsiProductDependency)(opsiProductAction=%s))(cn=%s))(opsiRequirementType=%s))' \
						% (action, requiredProductId, requirementType) )
					productDependencies.extend(search.getObjects())
				except BackendMissingDataError, e:
					logger.info("No such dependency: %s" % e)
			
			if requiredProductClassId:
				try:
					search = ObjectSearch(
						self._ldap,
						product.getDn(),
						filter = '(&(&(&(objectClass=opsiProductClassDependency)(opsiProductAction=%s))(cn=%s))(opsiRequirementType=%s))' \
						% (action, requiredProductClassId, requirementType) )
					productDependencies.extend(search.getObjects())
				except BackendMissingDataError, e:
					logger.info("No such dependency: %s" % e)
			
			for productDependency in productDependencies:
				logger.info("Deleting productDependency '%s' of product '%s'" % (productDependency.getDn(), product.getCn()))
				# Delete dependency from ldap
				productDependency.deleteFromDirectory(self._ldap)
				
				# Delete parent object if empty
				parent = productDependency.getParent()
				self.deleteChildlessObject( parent.getDn() )
				#if self.deleteChildlessObject( parent.getDn() ):
				#	# Was deleted, delete parent's parent object if empty
				#	parent = parent.getParent()
				#	self.deleteChildlessObject( parent.getDn() )
	
	def createLicenseKey(self, productId, licenseKey):
		productId = productId.lower()
		# TODO: productLicenses as product child objects in ldap tree ?
		raise NotImplementedError("createLicenseKey() not yet implemeted in LDAP backend")
		
		# Search product object
		search = ObjectSearch(self._ldap, self._productsContainerDn, filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
		product = search.getObject()
		
		# Create organizational role with same cn as product beneath license container
		self.createOrganizationalRole( "cn=%s,%s" % (product.getCn(), self._productLicensesContainerDn) )
		
		# Create license's cn from licensekey
		licenseCn = licenseKey.replace(':','')
		licenseCn = licenseCn.replace('-','')
		licenseCn = licenseCn.replace(' ','')
		licenseCn = licenseCn.replace('/','')
		licenseCn = licenseCn.replace('\\','')
		
		# Create license object
		productLicense = Object( "cn=%s,cn=%s,%s" % (licenseCn, productId, self._productLicensesContainerDn) )
		productLicense.new('opsiProductLicense')
		
		# Set object attributes
		productLicense.setAttribute('licenseKey', [ licenseKey ])
		productLicense.setAttribute('opsiProductReference', [ product.getDn() ])
		
		# Write object to ldap
		productLicense.writeToDirectory(self._ldap)
	
	
	def getLicenseKey(self, productId, clientId):
		productId = productId.lower()
		clientId = self._preProcessHostId(clientId)
		
		logger.debug("Searching licensekey for host '%s' and product '%s'" % (clientId, productId))
		
		freeLicenses = []
		for license in self.getLicenseKeys_listOfHashes(productId):
			hostId = license.get('hostId', '')
			if not hostId:
				freeLicenses.append(license.get('licenseKey', ''))
			elif (hostId == clientId):
				logger.info("Returning licensekey for product '%s' which is assigned to host '%s'"
						% (productId, clientId))
				return license.get('licenseKey', '')
		
		if (len(freeLicenses) <= 0):
			for (key, value) in self.getProductProperties_hash(productId, clientId).items():
				if (key.lower() == 'productkey'):
					freeLicenses.append(value)
		
		if (len(freeLicenses) > 0):
			logger.debug( "%s free license(s) found for product '%s'" % (len(freeLicenses), productId) )
			return freeLicenses[0]
		
		raise BackendMissingDataError("No more licenses available for product '%s'" % productId)
		
	def getLicenseKeys_listOfHashes(self, productId):
		productId = productId.lower()
		
		return []
		
		# Search product object
		search = ObjectSearch(self._ldap, self._productsContainerDn, filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
		product = search.getObject()
		
		result = []
		licenses = {}
		try:
			search = ObjectSearch(self._ldap, "cn=%s,%s" % (product.getCn(), self._productLicensesContainerDn),
				      				filter='(objectClass=opsiProductLicense)')
			
			for license in search.getObjects():
				license.readFromDirectory(self._ldap)
				licenses[license.getDn()] = { "licenseKey": license.getAttribute('licenseKey'), 'hostId': '' }
		
		except BackendMissingDataError, e:
			return result
		
		
		# Search all use licenses (referenced in productStates)
		try:
			productStateSearch = ObjectSearch(
						self._ldap,
						self._productStatesContainerDn,
						filter='(&(objectClass=opsiProductState)(licenseReference=*))')
			
			productStates = productStateSearch.getObjects()
			for productState in productStates:
				
				productState.readFromDirectory(self._ldap, 'licenseReference', 'opsiHostReference')
				hostId = self.getHostId( productState.getAttribute('opsiHostReference') )
				licenseReference = productState.getAttribute('licenseReference')
				
				try:
					search = ObjectSearch(	self._ldap, licenseReference, filter='(objectClass=opsiProductLicense)')
				except BackendMissingDataError, e:
					logger.error("Host '%s' references the not existing license '%s'" % (hostId, licenseReference))
					continue
				
				if licenses.has_key(licenseReference):
					licenses[licenseReference]['hostId'] = hostId
		
		except BackendMissingDataError, e:
			pass
		
		
		for (key, value) in licenses.items():
			result.append(value)
		
		return result
	
	def deleteLicenseKey(self, productId, licenseKey):
		productId = productId.lower()
		search = ObjectSearch(self._ldap, self._productsContainerDn, filter='(&(objectClass=opsiProduct)(cn=%s))' % productId)
		product = search.getObject()
		
		search = ObjectSearch(self._ldap, "cn=%s,%s" % (product.getCn(), self._productLicensesContainerDn),
			      				filter='(&(objectClass=opsiProductLicense)(licenseKey=%s))' % licenseKey)
		
		search.getObject().deleteFromDirectory(self._ldap)
	
	def getProductClassIds_list(self):
		search = ObjectSearch(self._ldap, self._productClassesContainerDn,
				      		filter='(objectClass=opsiProductClass)')
		return search.getCns()
	
	# -------------------------------------------------
	# -     HELPERS                                   -
	# -------------------------------------------------
	def createOrganizationalRole(self, dn):
		''' This method will add a oprganizational role object
		    with the specified DN, if it does not already exist. '''
		organizationalRole = Object(dn)
		logger.info("Trying to create organizational role '%s'" % dn)
		if organizationalRole.exists(self._ldap):
			logger.info("Organizational role '%s' already exists" % dn)
		else:
			organizationalRole.new('organizationalRole')
			organizationalRole.writeToDirectory(self._ldap)
		logger.info("Organizational role '%s' created" % dn)
		#try:
		#	organizationalRole.readFromDirectory(self._ldap, 'dn')
		#	logger.info("Organizational role '%s' already exists" % dn)
		#except BackendIOError:	
		#	organizationalRole.new('organizationalRole', self._policyReferenceObjectClass)
		#	organizationalRole.writeToDirectory(self._ldap)
		#	logger.info("Organizational role '%s' created" % dn)
		
		
	def deleteChildlessObject(self, dn):
		''' This method will delete the ldap object specified by DN, 
		    if exists and no child obejcts exist. '''
		try:
			search = ObjectSearch(self._ldap, dn, filter='(objectClass=*)')
		except BackendMissingDataError:
			# Object does not exist
			return False
		if ( len(search.getDns()) > 1):
			# object has childs
			return False
		search.getObject().deleteFromDirectory(self._ldap)
		return True






# ======================================================================================================
# =                                       CLASS OBJECT                                                 =
# ======================================================================================================

class LDAPObject:
	''' This class handles ldap objects. '''
	
	def __init__(self, dn):
		''' Constructor of the Object class. '''
		if not dn:
			raise BackendIOError("Cannot create Object, dn not defined")
		self._dn = dn
		self._old = self._new = {}
		self._existsInBackend = False
	
	def getObjectClasses(self):
		''' Returns object's objectClasses '''
		return self.getAttribute('objectClass', default=[], valuesAsList=True )
	
	def addObjectClass(self, objectClass):
		try:
			self.addAttributeValue('objectClass', objectClass)
		except Exception:
			pass
	
	def getCn(self):
		''' Returns the RDN without type.
		    assuming all subClasses use CN as RDN this method returns the CN '''
		return ( ldap.explode_dn(self._dn, notypes=1) )[0]
	
	def getRdn(self):
		''' Returns the object's RDN. '''
		return ( ldap.explode_dn(self._dn, notypes=0) )[0]
		
	def getDn(self):
		''' Returns the object's DN. '''
		return self._dn
	
	def getContainerCn(self):
		''' Returns the cn of the object's parent (container). '''
		return ( ldap.explode_dn(self._dn, notypes=1) )[1]
	
	def exists(self, ldapSession):
		try:
			objectSearch = ObjectSearch(ldapSession, self._dn)
		except:
			return False
		return True
	
	def getContainer(self):
		return self.getParent()
	
	def getParent(self):
		parts = ( ldap.explode_dn(self._dn, notypes=0) )[1:]
		if (parts <= 1):
			raise BackendBadValueError("Object '%s' has no parent" % self._dn)
		return Object(','.join(parts))
	
	def new(self, *objectClasses, **attributes):
		''' Creates a new object. '''
		if ( len(objectClasses) <= 0 ):
			raise BackendBadValueError("No objectClasses defined!")
		
		self._new['objectClass'] = objectClasses
		
		self._new['cn'] = [ self.getCn() ]
		
		for attr in attributes:
			self._new[attr] = [ attributes[attr] ]
		
		logger.debug("Created new LDAP-Object: %s" % self._new)
			
	def deleteFromDirectory(self, ldapSession, recursive = False):
		''' Deletes an object from ldap directory. '''
		if recursive:
			objects = []
			try:
				objectSearch = ObjectSearch(ldapSession, self._dn, scope=ldap.SCOPE_ONELEVEL)
				objects = objectSearch.getObjects()
			except:
				pass
			if objects:
				for obj in objects:
					obj.deleteFromDirectory(ldapSession, recursive = True)
		
		return ldapSession.delete(self._dn)
		
	def readFromDirectory(self, ldapSession, *attributes):
		''' If no attributes are given, all attributes are read.
		    If attributes are specified for read speedup,
		    the object can NOT be written back to ldap! '''
		
		self._readAllAttributes = False
		if ( len(attributes) <= 0 ):
			attributes = None
			self._readAllAttributes = True
		
		try:
			result = ldapSession.search(	baseDn     = self._dn,
							scope      = ldap.SCOPE_BASE,
							filter     = "(ObjectClass=*)",
							attributes = attributes )
		except Exception, e:
			raise BackendIOError("Cannot read object (dn: '%s') from ldap: %s" % (self._dn, e))
		
		self._existsInBackend = True
		self._old = result[0][1]
		# Copy the dict
		self._new = self._old.copy()
		# Copy the lists
		for attr in self._new:
			self._new[attr] = list(self._new[attr])

	def writeToDirectory(self, ldapSession):
		''' Writes the object to the ldap tree. '''
		if self._existsInBackend:
			if not self._readAllAttributes:
				raise BackendIOError("Not all attributes have been read from backend - not writing to backend!")
			ldapSession.modifyByModlist(self._dn, self._old, self._new)
		else:
			ldapSession.addByModlist(self._dn, self._new)
	
	def getAttributeDict(self, valuesAsList=False, unpackOpsiKeyValuePairs=False):
		''' Get all attributes of object as dict.
		    All values in self._new are lists by default, 
		    a list of length 0 becomes the value None
		    if there is only one item the item's value is used '''
		ret = {}
		
		for (key, values) in self._new.items():
			if ( len(values) > 1 or valuesAsList):
				ret[key] = values
			else:
				ret[key] = values[0]
		
		if unpackOpsiKeyValuePairs and ret.get('opsiKeyValuePair'):
			opsiKeyValuePairs = ret['opsiKeyValuePair']
			del ret['opsiKeyValuePair']
			if not type(opsiKeyValuePairs) in (list, tuple):
				opsiKeyValuePairs = [ opsiKeyValuePairs ]
			for keyValuePair in opsiKeyValuePairs:
				(k, v) = keyValuePair.split('=', 1)
				if k in ret.keys():
					logger.warning("Opsi key-value-pair %s overwrites attribute" % k)
				if valuesAsList:
					ret[k] = [ v ]
				else:
					ret[k] = v
		return ret
		
	def getAttribute(self, attribute, default='DEFAULT_UNDEFINED', valuesAsList=False ):
		''' Get a specific attribute from object. 
		    Set valuesAsList to a boolean true value to get a list,
		    even if there is only one attribute value. '''
		if not self._new.has_key(attribute):
			if (default != 'DEFAULT_UNDEFINED'):
				return default
			raise BackendMissingDataError("Attribute '%s' does not exist" % attribute)
		values = self._new[attribute]
		if ( len(values) > 1 or valuesAsList):
			return values
		else:
			return values[0]
	
	def setAttribute(self, attribute, value):
		''' Set the attribute to the value given.
		    The value's type should be list. '''
		if ( type(value) != tuple ) and ( type(value) != list ):
			value = [ value ]
		if (value == ['']):
			value = []
		else:
			for i in range(len(value)):
				value[i] = self._encodeValue(value[i])
		logger.debug("Setting attribute '%s' to '%s'" % (attribute, value))
		self._new[attribute] = value
	
	def addAttributeValue(self, attribute, value):
		''' Add a value to an object's attribute. '''
		if not self._new.has_key(attribute):
			self.setAttribute(attribute, [ self._encodeValue(value) ])
			return
		if value in self._new[attribute]:
			#logger.warning("Attribute value '%s' already exists" % value.decode('utf-8', 'ignore'))
			return
		self._new[attribute].append( self._encodeValue(value) )
	
	def deleteAttributeValue(self, attribute, value):
		''' Delete a value from the list of attribute values. '''
		if not self._new.has_key(attribute):
			logger.warning("Failed to delete value '%s' of attribute '%s': does not exists" % (attribute, value))
			return
		for i in range( len(self._new[attribute]) ):
			if (self._new[attribute][i] == value):
				del self._new[attribute][i]
				logger.debug("Value '%s' of attribute '%s' successfuly deleted" % (attribute, value))
				return
	
	def _encodeValue(self, value):
		if not value:
			return value
		if (type(value) != unicode):
			value = value.decode('utf-8', 'replace')
		return value.encode('utf-8')



# ======================================================================================================
# =                                    CLASS OBJECTSEARCH                                              =
# ======================================================================================================

class LDAPObjectSearch:
	''' This class simplifies object searchs. '''
	
	def __init__(self, ldapSession, baseDn='', scope=ldap.SCOPE_SUBTREE, filter='(ObjectClass=*)'):
		''' ObjectSearch constructor. '''
		
		if not baseDn:
			baseDn = ldapSession.baseDn
		
		logger.debug( "Searching object => baseDn: %s, scope: %s, filter: %s" 
				% (baseDn, scope, filter) )
		
		# Storage for matching DNs
		self._dns = []
		self._ldap = ldapSession
		try:
			# Execute search
			result = self._ldap.search( 	baseDn = baseDn, 
							scope = scope, 
							filter = filter, 
							attributes = ['dn'] )
		except ldap.LDAPError, e:
			# Failed
			raise
		
		#if (result == []):
		#	# Nothing found
		#	raise BackendMissingDataError("Cannot find Object in baseDn '%s' matching filter '%s'" 
		#					% (baseDn, filter))
		for r in result:
			logger.debug( "Found dn: %s" % r[0] )
			self._dns.append(r[0])
		
	def getCns(self):
		''' Returns the cns of all objects found. '''
		cns = []
		for dn in self._dns:
			cns.append( ( ldap.explode_dn(dn, notypes=1) )[0] )
		return cns
	
	def getCn(self):
		''' Returns the cn of the first object found. '''
		if ( len(self._dns) >= 1 ):
			return ( ldap.explode_dn(self._dns[0], notypes=1) )[0]
			
	def getDns(self):
		''' Returns the dns of all objects found. '''
		return self._dns
	
	def getDn(self):
		''' Returns the dn of the first object found. '''
		if ( len(self._dns) >= 1 ):
			return self._dns[0]
		
	def getObjects(self):
		''' Returns all objects as Object instances. '''
		if ( len(self._dns) <= 0 ):
			raise BackendMissingDataError("No objects found")
		objects = []
		for dn in self._dns:
			objects.append( Object(dn) )
		return objects
	
	def getObject(self):
		''' Returns the first object found as Object instance. '''
		if ( len(self._dns) <= 0 ):
			raise BackendMissingDataError("No object found")
		return Object(self._dns[0])




# ======================================================================================================
# =                                       CLASS SESSION                                                =
# ======================================================================================================	

class LDAPSession:
	''' This class handles the requests to a ldap server '''
	SCOPE_SUBTREE = ldap.SCOPE_SUBTREE
	SCOPE_BASE = ldap.SCOPE_BASE
	
	def __init__(self, host='127.0.0.1', username='', password='', ldap=None):
		''' Session constructor. '''
		self._host = host
		self._username = username
		self._password = password
		self._commandCount = 0
		self._searchCount = 0
		self._deleteCount = 0
		self._addCount = 0
		self._modifyCount = 0
		self._ldap = ldap
		self.baseDn = ''
	
	def getCommandCount(self):	
		''' Get number of all commands (requests) sent to ldap server. '''
		return self._commandCount
	def getSearchCount(self):
		''' Get number of all search commands (requests) sent to ldap server. '''
		return self._searchCount
	def getDeleteCount(self):	
		''' Get number of all delete commands (requests) sent to ldap server. '''
		return self._deleteCount
	def getAddCount(self):		
		''' Get number of all add commands (requests) sent to ldap server. '''
		return self._addCount
	def getModifyCount(self):
		''' Get number of all modify commands (requests) sent to ldap server. '''
		return self._modifyCount
	def getCommandStatistics(self):
		''' Get number of all commands as dict. '''
		return { 	'total': 	self._commandCount, 
				'search':	self._searchCount, 
				'delete':	self._deleteCount, 
				'add': 		self._addCount, 
				'modify':	self._modifyCount }
	
	def connect(self):
		''' Connect to a ldap server. '''
		self._ldap = ldap.open(self._host)
		self._ldap.protocol_version = ldap.VERSION3
		try:
			self._ldap.bind_s(self._username, self._password, ldap.AUTH_SIMPLE)
			logger.info('Successfully connected to LDAP-Server.')
		except ldap.LDAPError, e:
			logger.error("Bind to LDAP failed: %s" % e)
			raise BackendIOError("Bind to LDAP server '%s' as '%s' failed: %s" % (self._host, self._username, e))
	
	def disconnect(self):
		''' Disconnect from ldap server '''
		self._ldap.unbind()
	
	def search(self, baseDn, scope, filter, attributes):
		''' This function is used to search in a ldap directory. '''
		self._commandCount += 1
		self._searchCount += 1
		logger.debug("Searching in baseDn: %s, scope: %s, filter: '%s', attributes: '%s' " \
					% (baseDn, scope, filter, attributes) )
		try:
			result = self._ldap.search_s(baseDn, scope, filter, attributes)
		except ldap.LDAPError, e:
			if (e.__class__ == ldap.FILTER_ERROR):
				# Bad search filter
				logger.critical("Bad search filter: '%s' " % e)
			
			raise BackendMissingDataError("Error searching in baseDn '%s', filter '%s', scope %s : %s" \
					% (baseDn, filter, scope, e) )
		if (result == []):
			raise BackendMissingDataError("No results for search in baseDn: '%s', filter: '%s', scope: %s" \
					% (baseDn, filter, scope) )
		return result
	
	def delete(self, dn):
		''' This function is used to delete an object in a ldap directory. '''
		self._commandCount += 1
		self._deleteCount += 1
		logger.debug("Deleting Object from LDAP, dn: '%s'" % dn)
		try:
			self._ldap.delete_s(dn)
		except ldap.LDAPError, e:
			raise BackendIOError(e)
	
	def modifyByModlist(self, dn, old, new):
		''' This function is used to modify an object in a ldap directory. '''
		self._commandCount += 1
		self._modifyCount += 1
		
		logger.debug("[old]: %s" % old)
		logger.debug("[new]: %s" % new)
		attrs = ldap.modlist.modifyModlist(old,new)
		logger.debug("[change]: %s" % attrs)
		if (attrs == []):
			logger.debug("Object '%s' unchanged." % dn)
			return
		logger.debug("Modifying Object in LDAP, dn: '%s'" % dn)
		try:
			self._ldap.modify_s(dn,attrs)
		except ldap.LDAPError, e:
			raise BackendIOError(e)
		except TypeError, e:
			raise BackendBadValueError(e)
		
		
	def addByModlist(self, dn, new):
		''' This function is used to add an object to the ldap directory. '''
		self._commandCount += 1
		self._addCount += 1
		
		attrs = ldap.modlist.addModlist(new)
		logger.debug("Adding Object to LDAP, dn: '%s'" % dn)
		logger.debug("attrs: '%s'" % attrs)
		try:
			self._ldap.add_s(dn,attrs)
		except ldap.LDAPError, e:
			raise BackendIOError(e)
		except TypeError, e:
			raise BackendBadValueError(e)


Object = LDAPObject
ObjectSearch = LDAPObjectSearch
Session = LDAPSession

if (__name__ == "__main__"):
	defaultDomain = "uib.local"
	be = LDAPBackend(
			username = 'cn=admin,dc=uib,dc=local',
			password = 'linux123',
			address = '127.0.0.1',
			args = { "defaultDomain": defaultDomain }
	)
	print "Creating base"
	be.createOpsiBase()
	print "Creating server"
	hostId = be.createServer( serverName = "test-server", domain = defaultDomain, description = "Test Config Server", notes = "Note 1\nNote 2\n" )
	print "Creating depot"
	hostId = be.createDepot( depotName = "test-server", domain = defaultDomain, depotLocalUrl = 'file:///opt/pcbin/install', depotRemoteUrl = "smb://test-server/opt_pcbin/install", repositoryLocalUrl="file:///var/lib/opsi/products", repositoryRemoteUrl="webdavs://%s:4447/products" % hostId, network = "192.168.1.0/24", maxBandwidth=10000)
	print "Getting servers"
	print "  =>>>", be.getServerIds_list()
	print "Getting depots"
	print "  =>>>", be.getDepotIds_list()
	print "Getting depot info for %s" % hostId
	print "  =>>>", be.getDepot_hash( depotId = hostId )
	print "Creating client"
	hostId = be.createClient( clientName = "test-client", domain = defaultDomain, description = "Test Client", notes = "Note 1\nNote 2\n", ipAddress = "192.168.1.100", hardwareAddress = "00:00:01:02:03:04" )
	print "Getting host info for %s" % hostId
	print "  =>>>", be.getHost_hash( hostId = hostId )
	print "Getting generalconfig for %s" % defaultDomain
	print "  =>>>", be.getGeneralConfig_hash(objectId = defaultDomain)
	print "Deleting generalconfig for %s" % defaultDomain
	be.deleteGeneralConfig(objectId = defaultDomain)
	print "Setting generalconfig for %s" % defaultDomain
	be.setGeneralConfig( config = { "test1": "test1", "test2": ["test2"] } , objectId = defaultDomain)
	print "Getting generalconfig for %s" % defaultDomain
	print "  =>>>", be.getGeneralConfig_hash(objectId = defaultDomain)
	print "Setting generalconfig for %s" % hostId
	be.setGeneralConfig( config = { "test1": "test1", "test2": hostId } , objectId = hostId)
	print "Getting generalconfig for %s" % hostId
	print "  =>>>", be.getGeneralConfig_hash(objectId = hostId)
	be.setGeneralConfig( config = { "test1": "test1", "test2": ["test2"] } , objectId = hostId)
	print "Getting generalconfig for %s" % hostId
	print "  =>>>", be.getGeneralConfig_hash(objectId = hostId)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
