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

__version__ = '3.5'

# Imports
import ldap, ldap.modlist
from ldaptor.protocols import pureldap

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI.Backend.Backend import *

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                    CLASS LDAPBACKEND                                               =
# ======================================================================================================
class LDAPBackend(ConfigDataBackend):
	
	def __init__(self,**kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self._address  = 'localhost'
		self._username = None
		self._password = None
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('address'):
				self._address = value
			elif option in ('username'):
				self._username = value
			elif option in ('password'):
				self._password = value
		
		# Default values
		self._baseDn = 'dc=uib,dc=local'
		self._opsiBaseDn = 'cn=opsi,' + self._baseDn
		self._hostsContainerDn = 'cn=hosts,' + self._opsiBaseDn
		self._groupsContainerDn = 'cn=groups,' + self._opsiBaseDn
		self._productsContainerDn = 'cn=products,' + self._opsiBaseDn
		self._productClassesContainerDn = 'cn=productClasses,' + self._opsiBaseDn
		self._productStatesContainerDn = 'cn=productStates,' + self._opsiBaseDn
		self._generalConfigsContainerDn = 'cn=generalConfigs,' + self._opsiBaseDn
		self._networkConfigsContainerDn = 'cn=networkConfigs,' + self._opsiBaseDn
		self._productPropertiesContainerDn = 'cn=productProperties,' + self._opsiBaseDn
		self._hostAttributeDescription = 'opsiDescription'
		self._hostAttributeNotes = 'opsiNotes'
		self._hostAttributeHardwareAddress = 'opsiHardwareAddress'
		self._hostAttributeIpAddress = 'opsiIpAddress'
		self._createClientCommand = ''
		self._deleteClient = True
		self._deleteClientCommand = ''
		self._createServerCommand = ''
		self._deleteServer = False
		self._deleteServerCommand = ''
		self._clientObjectSearchFilter = ''
		self._serverObjectSearchFilter = ''
		self._defaultDomain = None
		
		self._mappings = [
			{ 'opsiAttribute': 'ipAddress', 'ldapAttribute': 'opsiIpAddress' },
			{ 'opsiAttribute': 'ipAddress', 'ldapAttribute': 'opsiIpAddress' }
		]
		
		self._opsiAttributeToLdapAttribute = {}
		for mapping in self._mappings:
			self._opsiAttributeToLdapAttribute[mapping['opsiAttribute']] = mapping['ldapAttribute']
		
		self._ldapAttributeToOpsiAttribute = {}
		for mapping in self._mappings:
			self._ldapAttributeToOpsiAttribute[mapping['ldapAttribute']] = mapping['opsiAttribute']
		
		logger.info(u"Connecting to ldap server '%s' as user '%s'" % (self._address, self._username))
		self._ldap = LDAPSession(
				host	 = self._address,
				username = self._username, 
				password = self._password )
		self._ldap.connect()
		
	
	# -------------------------------------------------
	# -     HELPERS                                   -
	# -------------------------------------------------
		
	def _objectFilterToLDAPFilter(self, filter):
		pass
		
	def _createOrganizationalRole(self, dn):
		''' This method will add a oprganizational role object
		    with the specified DN, if it does not already exist. '''
		organizationalRole = LDAPObject(dn)
		if organizationalRole.exists(self._ldap):
			logger.info(u"Organizational role '%s' already exists" % dn)
		else:
			logger.debug(u"Creating organizational role '%s'" % dn)
			organizationalRole.new('organizationalRole')
			organizationalRole.writeToDirectory(self._ldap)
			logger.info(u"Organizational role '%s' created" % dn)
	
	def base_delete(self):
		ConfigDataBackend.base_delete(self)
		ldapobj = LDAPObject(self._opsiBaseDn)
		if ldapobj.exists(self._ldap):
			ldapobj.deleteFromDirectory(self._ldap, recursive = True)
		
		
	def base_create(self):
		ConfigDataBackend.base_create(self)
		
		# Create some containers
		self._createOrganizationalRole(self._opsiBaseDn)
		self._createOrganizationalRole(self._hostsContainerDn)
		self._createOrganizationalRole(self._generalConfigsContainerDn)
		self._createOrganizationalRole(self._networkConfigsContainerDn)
		self._createOrganizationalRole(self._groupsContainerDn)
		self._createOrganizationalRole(self._productsContainerDn)
		self._createOrganizationalRole(self._productClassesContainerDn)
		self._createOrganizationalRole(self._productStatesContainerDn)
		self._createOrganizationalRole(self._productPropertiesContainerDn)
	
	def _ldapObjectToOpsiObject(self, ldapObject):
		ldapObject.readFromDirectory(self._ldap)
		opsiClassName = None
		if   'opsiConfigserver' in ldapObject.getObjectClasses():
			opsiClassName = 'OpsiConfigserver'
		elif 'opsiDepotserver'  in ldapObject.getObjectClasses():
			opsiClassName = 'OpsiDepotserver'
		elif 'opsiClient'       in ldapObject.getObjectClasses():
			opsiClassName = 'OpsiClient'
		else:
			raise Exception(u"Unhandled ldap objectclasses %s" % ldapObject.getObjectClasses())
		
		opsiObjectHash = {}
		for (attribute, value) in ldapObject.getAttributeDict(valuesAsList = True).items():
			logger.debug(u"LDAP attribute is: %s" % attribute)
			if attribute in ('cn', 'objectClass'):
				continue
			if (attribute == 'opsiHostId'):
				attribute = 'id'
			elif (attribute == 'opsiHostKey'):
				attribute = 'opsiHostKey'
			elif (attribute == 'opsiMaximumBandwidth'):
				attribute = 'maxBandwidth'
			
			else:
				attribute = attribute.replace('Timestamp', '')
				attribute = attribute[4].lower() + attribute[5:]
			
			logger.debug(u"Opsi attribute is: %s" % attribute)
			opsiValue = None
			if value:
				opsiValue = value[0]
			opsiObjectHash[attribute] = opsiValue
		
		Class = eval(opsiClassName)
		return Class.fromHash(opsiObjectHash)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		#bool(False) == False
		#bool(0) == False
		#bool(1) = True
		#bool(None) = False
		#bool([None]) = True
		#bool(['']) = False
		#bool('')  = False
		#bool(' ') = True
		
		#Create a new host
		#if self._createOrganizationalRole(_self._hostsContainerDn
		
		objectClasses = []
		if isinstance(host, OpsiClient):
			objectClasses = ['opsiClient']
		elif isinstance(host, OpsiConfigserver):
			objectClasses = ['opsiConfigserver', 'opsiDepotserver']
		elif isinstance(host, OpsiDepotserver):
			objectClasses = ['opsiDepotserver']
		
		ldapObj = LDAPObject('cn=%s,%s' % (host.id, self._hostsContainerDn))
		ldapObj.new(*objectClasses,
				opsiHostId            = host.id,
				opsiDescription       = host.description,
				opsiNotes             = host.notes,
				opsiHardwareAddress   = host.hardwareAddress,
				opsiIpAddress         = host.ipAddress,
				opsiInventoryNumber   = host.inventoryNumber or '',
				opsiHostKey           = host.opsiHostKey
		)
		if isinstance(host, OpsiClient):
			
			ldapObj.setAttribute('opsiCreatedTimestamp',  host.created)
			ldapObj.setAttribute('opsiLastSeenTimestamp', host.lastSeen)
		
		
		elif isinstance(host, OpsiDepotserver) or isinstance(host, OpsiConfigserver):
			
			ldapObj.setAttribute('opsiDepotLocalUrl',       host.depotLocalUrl)
			ldapObj.setAttribute('opsiDepotRemoteUrl',      host.depotRemoteUrl)
			ldapObj.setAttribute('opsiRepositoryLocalUrl',  host.repositoryLocalUrl)
			ldapObj.setAttribute('opsiRepositoryRemoteUrl', host.repositoryRemoteUrl)
			ldapObj.setAttribute('opsiNetworkAddress',      host.networkAddress)
			ldapObj.setAttribute('opsiMaximumBandwidth',    host.maxBandwidth)
		
		logger.critical(u"Try to create Host in ldap")
		ldapObj.writeToDirectory(self._ldap)
		
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
	
	def host_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.host_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting hosts, filter: %s" % filter)
		hosts = []
		
		
		# "type"
		# "id"
		# "description"
		# "ipAddress"
		# ...
		# 
		# filter = {}
		# filter = {"type" = "OpsiClient"}
		# (objectClass=opsiClient)
		# filter = {"type" = ["OpsiClient", "OpsiDeposerver"]}
		# (|(objectClass=opsiClient)(objectClass=opsiDepotserver))
		# filter = {"type" = None}
		# (objectClass=opsiHost)
		# filter = {"ipAddress" = [ None, "" ] }
		# (&(objectClass=opsiHost)(!(ipAddress=*)))
		# filter = {"type" = "OpsiClient", "id" = "*clien*" }
		# (&(objectClass=opsiClient)(opsiHostId=*clien*))
		# filter = {"type" = "OpsiClient", "id" = "*clien" }
		# filter = { "id" = "clien*" }
		# filter = { "id" = ["client1.uib.local", "client2.uib.local"], "description" = ["desc1", "desc2"] }
		
		
		# pureldap.LDAPFilter_equalityMatch      => string
		# pureldap.LDAPFilter_substrings_initial => string*
		# pureldap.LDAPFilter_substrings_final   => *string
		# pureldap.LDAPFilter_substrings_any     => *string*
		
		# False:
		#    None, 0, False, "", [], {}
		
		# (objectClass=opsiHost)
		
		
		
		
		
		ldapFilter = None
		if filter.get('type'):
			filters = []
			for objectType in forceList(filter['type']):
				objectClass = None
				if   (objectType == 'OpsiClient'):
					objectClass = 'opsiClient'
				elif (objectType == 'OpsiDepotserver'):
					objectClass = 'opsiDepotserver'
				elif (objectType == 'OpsiConfigserver'):
					objectClass = 'opsiConfigserver'
				if objectClass:
					filters.append(
						pureldap.LDAPFilter_equalityMatch(
							attributeDesc  = pureldap.LDAPAttributeDescription('objectClass'),
							assertionValue = pureldap.LDAPAssertionValue(objectClass)
						)
					)
			if filters:
				if (len(filters) == 1):
					ldapFilter = filters[0]
				else:
					ldapFilter = pureldap.LDAPFilter_or(filters)
		if not ldapFilter:
			ldapFilter = objectClassFilter = pureldap.LDAPFilter_equalityMatch(
				attributeDesc  = pureldap.LDAPAttributeDescription('objectClass'),
				assertionValue = pureldap.LDAPAssertionValue('opsiHost')
			)
		
		andFilters = []
		for (attribute, values) in filter.items():
			if (attribute == 'type'):
				continue
			if (attribute == 'id'):
				attribute = 'opsiHostId'
			
			if self._opsiAttributeToLdapAttribute.get(attribute):
				attribute = self._opsiAttributeToLdapAttribute.get(attribute)
			else:
				attribute = 'opsi' + attribute[0].upper() + attribute[1:]
			
			filters = []
			for value in forceList(values):
				if (value == None):
					filters.append(
						pureldap.LDAPFilter_not(
							pureldap.LDAPFilter_present(attribute)
						)
					)
					
				else:
					filters.append(
						pureldap.LDAPFilter_equalityMatch(
							attributeDesc  = pureldap.LDAPAttributeDescription(attribute),
							assertionValue = pureldap.LDAPAssertionValue(value)
						)
					)
			if filters:
				if (len(filters) == 1):
					andFilters.append(filters[0])
				else:
					andFilters.append(pureldap.LDAPFilter_or(filters))
		if andFilters:
			newFilter = None
			if (len(andFilters) == 1):
				newFilter = andFilters[0]
			else:
				newFilter = pureldap.LDAPFilter_and(andFilters)
			ldapFilter = pureldap.LDAPFilter_and( [ldapFilter, newFilter] )
		
		logger.comment(ldapFilter.asText())
		search = LDAPObjectSearch(self._ldap, self._hostsContainerDn, filter=ldapFilter.asText() )
		for ldapObject in search.getObjects():
			hosts.append( self._ldapObjectToOpsiObject(ldapObject) )
		
		return hosts
		
		#Convert LDAPObject to OPSI-Objects
		##### Notizen
		#if isinstance(host, OpsiClient):
		#	objectClass = 'opsiClient'
		#elif isinstance(host, OpsiDepotserver):
		#	objectClass = 'opsiDepotserver'
		#elif isinstance(host, OpsiConfigserver):
		#	objectClass = 'opsiConfigserver'
		#ldapObj = LDAPObject('cn=%s,%s' % (host.id, self._hostsContainerDn))
		#ldapObj.new(objectClass,
		#		opsiHostId            = host.id,
		#		opsiDescription       = host.description or None,
		#		opsiNotes             = host.notes or None,
		#		opsiHardwareAddress   = host.hardwareAddress,
		#		opsiIpAddress         = host.ipAddress,
		#		opsiInventoryNumber   = host.inventoryNumber or None,
		#		opsiHostKey           = host.opsiHostKey
		#)
		#if isinstance(host, OpsiClient):
		#	
		#	ldapObj.setAttribute('opsiCreatedTimestamp',  host.created)
		#	ldapObj.setAttribute('opsiLastSeenTimestamp', host.lastSeen)
		#
		#
		#elif isinstance(host, OpsiDepotserver) or isinstance(host, OpsiConfigserver):
		#	
		#	ldapObj.setAttribute('opsiDepotLocalUrl',       host.depotLocalUrl)
		#	ldapObj.setAttribute('opsiDepotRemoteUrl',      host.depotRemoteUrl)
		#	ldapObj.setAttribute('opsiRepositoryLocalUrl',  host.repositoryLocalUrl)
		#	ldapObj.setAttribute('opsiRepositoryRemoteUrl', host.repositoryRemoteUrl)
		#	ldapObj.setAttribute('opsiNetworkAddress',      host.networkAddress)
		#	ldapObj.setAttribute('opsiMaximumBandwidth',    host.maxBandwidth)
		############# Notizen
		
		
		#if (res):
		#	hosthash = {}
		#	hostobj = []
		#	for resLdapObj in res:
		#		print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
		#		resLdapObj.readFromDirectory(self._ldap)
		#		for (key, value) in resLdapObj.getAttributeDict().items():
		#			#if not key.startswith('opsi') or not value:
		#			#	continue
		#			if value:
		#				hosthash[key] = value
		#				
		#		print hosthash
		#		if (hosthash):
		#			if (hosthash['objectClass'] == 'opsiClient'):
		#				opsiclient = OpsiClient.fromHash(hosthash)
		#				
		#					id        	= hosthash['opsiHostId'],
		#					opsiHostKey 	= hosthash['opsiHostKey'],
		#					description	= hosthash['opsiDescription'],
		#					notes		= hosthash['opsiNotes'],
		#					hardwareAddress = hosthash['opsiHardwareAddress'],
		#					ipAddress       = hosthash['opsiIpAddress'],
		#					inventoryNumber = hosthash['opsiInventoryNumber'],
		#					created         = hosthash['opsiCreatedTimestamp'],
		#					lastSeen        = hosthash['opsiLastSeenTimestamp']
		#				)
		#				hosts.append(opsiclient)
		#			elif (hosthash['objectClass'] == 'OpsiDepotserver'):
		#				opsiclient = OpsiDepotserver(
		#					id        	   = hosthash['opsiHostId'],
		#					depotLocalUrl      = hosthash['opsiDepotLocalUrl'],
		#					depotRemoteUrl     = hosthash['opsiDepotRemoteUrl']
		#					repositoryLocalUrl = hosthash['opsiRepositoryLocalUrl']
		#					repositoryRemoteUrl= hosthash['opsiRepositoryRemoteUrl']
		#					description= hosthash['opsiDescription']
		#					notes= hosthash['opsiNotes']
		#					
		#					
		#					
		#					networkAddress= hosthash['opsiDepotRemoteUrl']
		#					maxBandwith= hosthash['opsiDepotRemoteUrl']
		#					
		#					
		#					
		#					
		#					'opsiNotes': 'Config 1', 
		#					'opsiNetworkAddress': '192.168.1.0/24', 
		#					'objectClass': 'opsiDepotserver', 
		#					'opsiHostId': 'erollinux.uib.local', 
		#					'opsiRepositoryLocalUrl': 'file:///var/lib/opsi/products', 
		#					'opsiDepotRemoteUrl': 'smb://config1/opt_pcbin', 
		#					'opsiDepotLocalUrl': 'file:///opt/pcbin/install', 
		#					'opsiInventoryNumber': '00000000001', 
		#					'opsiMaximumBandwidth': '10000', 
		#					'opsiRepositoryRemoteUrl': 'webdavs://config1.uib.local:4447/products', 
		#					'opsiHostKey': '71234545689056789012123678901234', 
		#					'opsiDescription': 'The configserver', 
		#					'cn': 'erollinux.uib.local'}
		#					
		#					
		#					opsiHostKey 	= hosthash['opsiHostKey'],
		#					description	= hosthash['opsiDescription'],
		#					notes		= hosthash['opsiNotes'],
		#					hardwareAddress = hosthash['opsiHardwareAddress'],
		#					ipAddress       = hosthash['opsiIpAddress'],
		#					inventoryNumber = hosthash['opsiInventoryNumber'],
		#					created         = hosthash['opsiCreatedTimestamp'],
		#					lastSeen        = hosthash['opsiLastSeenTimestamp']
		#				)
		#				hosts.append(opsiclient)
		#	print hosts
		#	
		#	
		#		
		#		
		#return hosts
		#	
		#searchFilter = pureldap.LDAPFilter_and(
		#	[
		#		pureldap.LDAPFilter_equalityMatch(
		#			attributeDesc  = pureldap.LDAPAttributeDescription('objectClass'),
		#			assertionValue = pureldap.LDAPAssertionValue('addressbookPerson')
		#		)
		#	]
		#	+ filters)
                #
		#	
		#(&()())
		#
		#myfilter = ''
		#if filter is None:
		#	return ''
		#for (key,val) in filter:
		#	if myfilter == '':
		#		myfilter = "(%s=%s)" % (key, val)
		#	else:
		#		myfilter = ",%s=%s" % (key, val)
		#return myfilter
		#
		#
		#type = forceList(filter.get('type', []))
		#if 'OpsiDepotServer' in type and not 'OpsiConfigserver' in type:
		#	type.append('OpsiConfigserver')
		#	filter['type'] = type
		#(attributes, filter) = self._adjustAttributes(Host, attributes, filter)
		#
		##for hostContainerDn in self._hostsContainerDn:
		#search = LDAPObjectSearch(self._ldap, self._hostsContainerDn, self._objectFilterToLDAPFilter(filter))
		#hosts.extend( search.getObjects() )
		#	
		##for res in 
		#print "======================="
		#print hosts
		#
		#
		##for hostContainerDn in self._hostsContainerDn:
		##	search = LDAPObjectSearch(self._ldap, hostContainerDn,)
		##	hosts.extend(search.getObjects())
		#
		##print hosts
		#return []
	
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes=[], **filter)
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes=[], **filter)
	
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
	
	def product_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes=[], **filter)
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
	
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
	
	def productPropertyState_updateObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		ConfigDataBackend.group_insertObject(self, group)
	
	def group_updateObject(self, group):
		ConfigDataBackend.group_updateObject(self, group)
	
	def group_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
	
	def group_deleteObjects(self, groups):
		ConfigDataBackend.group_deleteObjects(self, groups)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
	
	def objectToGroup_updateObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)


	
	
		






# ======================================================================================================
# =                                     CLASS LDAPOBJECT                                               =
# ======================================================================================================

class LDAPObject:
	''' This class handles ldap objects. '''
	
	def __init__(self, dn):
		''' Constructor of the Object class. '''
		if not dn:
			raise BackendIOError(u"Cannot create Object, dn not defined")
		self._dn = dn
		self._old = self._new = {}
		self._existsInBackend = False
	
	def getObjectClasses(self):
		''' Returns object's objectClasses '''
		return self.getAttribute('objectClass', default=[], valuesAsList=True )
	
	def addObjectClass(self, objectClass):
		try:
			self.addAttributeValue('objectClass', objectClass)
		except Exception, e:
			logger.warning(u"Failed to add objectClass '%s' to '%s': %s" \
						% (objectClass, self.getDn(), e) )
		
	def removeObjectClass(self, objectClass):
		try:
			self.deleteAttributeValue('objectClass', objectClass)
		except Exception, e:
			logger.warning(u"Failed to delete objectClass '%s' from '%s': %s" \
						% (objectClass, self.getDn(), e) )
	
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
			objectSearch = LDAPObjectSearch(ldapSession, self._dn, scope=ldap.SCOPE_BASE)
		except BackendMissingDataError:
			logger.debug(u"exists(): object '%s' does not exist" % self._dn)
			return False
		logger.debug(u"exists(): object '%s' does exist" % self._dn)
		return True
	
	def getContainer(self):
		return self.getParent()
	
	def getParent(self):
		parts = ( ldap.explode_dn(self._dn, notypes=0) )[1:]
		if (parts <= 1):
			raise BackendBadValueError(u"Object '%s' has no parent" % self._dn)
		return LDAPObject(','.join(parts))
	
	def new(self, *objectClasses, **attributes):
		''' Creates a new object. '''
		if ( len(objectClasses) <= 0 ):
			raise BackendBadValueError(u"No objectClasses defined!")
		
		self._new['objectClass'] = objectClasses
		
		self._new['cn'] = [ self.getCn() ]
		
		
		for (attribute, value) in attributes.items():
			self.setAttribute(attribute, value)
		
		logger.debug(u"Created new LDAP-Object: %s" % self._new)
			
	def deleteFromDirectory(self, ldapSession, recursive = False):
		''' Deletes an object from ldap directory. '''
		if recursive:
			objects = []
			try:
				objectSearch = LDAPObjectSearch(ldapSession, self._dn, scope=ldap.SCOPE_ONELEVEL)
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
			raise BackendIOError(u"Cannot read object (dn: '%s') from ldap: %s" % (self._dn, e))
		
		self._existsInBackend = True
		self._old = result[0][1]
		# Copy the dict
		self._new = self._old.copy()
		# Copy the lists
		for attr in self._new:
			self._new[attr] = list(self._new[attr])

	def writeToDirectory(self, ldapSession):
		''' Writes the object to the ldap tree. '''
		logger.info(u"Writing object %s to directory" % self.getDn())
		if self._existsInBackend:
			if not self._readAllAttributes:
				raise BackendIOError(u"Not all attributes have been read from backend - not writing to backend!")
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
			if (values == [' ']):
				values = [u'']
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
					logger.warning(u"Opsi key-value-pair %s overwrites attribute" % k)
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
			raise BackendMissingDataError(u"Attribute '%s' does not exist" % attribute)
		values = self._new[attribute]
		if (values == [' ']):
			values = [u'']
		if ( len(values) > 1 or valuesAsList):
			return values
		return values[0]
	
	def setAttribute(self, attribute, value):
		ldapValue = []
		if not value is None:
			value = forceList(value)
			for v in value:
				if (v == u''):
					v = u' '
				ldapValue.append(forceUnicode(v).encode('utf-8'))
		logger.debug(u"Setting attribute '%s' to '%s'" % (attribute, value))
		self._new[attribute] = ldapValue
	
	def addAttributeValue(self, attribute, value):
		''' Add a value to an object's attribute. '''
		values = forceList(self._new.get(attribute, []))
		if value in values:
			return
		values.append(value)
		self.setAttribute(attribute, values)
		
	def deleteAttributeValue(self, attribute, value):
		''' Delete a value from the list of attribute values. '''
		values = forceList(self._new.get(attribute, []))
		if not value in values:
			return
		values.remove(value)
		self.setAttribute(attribute, values)
	


# ======================================================================================================
# =                                    CLASS LDAPObjectSearch                                              =
# ======================================================================================================

class LDAPObjectSearch:
	''' This class simplifies object searchs. '''
	
	def __init__(self, ldapSession, baseDn='', scope=ldap.SCOPE_SUBTREE, filter='(ObjectClass=*)'):
		''' ObjectSearch constructor. '''
		
		if not baseDn:
			baseDn = ldapSession.baseDn
		
		logger.debug( u'Searching object => baseDn: %s, scope: %s, filter: %s' 
				% (baseDn, scope, filter) )
		
		# Storage for matching DNs
		self._dns = []
		self._ldap = ldapSession
		
		# Execute search
		try:
			result = self._ldap.search( 	baseDn = baseDn, 
							scope = scope, 
							filter = filter, 
							attributes = ['dn'] )
		except Exception, e:
			logger.debug(u'LDAPObjectSearch search error: %s' % e)
			raise
		
		for r in result:
			logger.debug( u'Found dn: %s' % r[0] )
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
		#if ( len(self._dns) <= 0 ):
		#	raise BackendMissingDataError("No objects found")
		objects = []
		for dn in self._dns:
			objects.append( LDAPObject(dn) )
		return objects
	
	def getLDAPObject(self):
		''' Returns the first object found as Object instance. '''
		if ( len(self._dns) <= 0 ):
			#raise BackendMissingDataError("No object found")
			return None
		return LDAPObject(self._dns[0])


# ======================================================================================================
# =                                       CLASS SESSION                                                =
# ======================================================================================================	

class LDAPSession:
	''' This class handles the requests to a ldap server '''
	SCOPE_SUBTREE = ldap.SCOPE_SUBTREE
	SCOPE_BASE = ldap.SCOPE_BASE
	
	def __init__(self, host, username, password):
		''' Session constructor. '''
		self._host = host
		self._username = username
		self._password = password
		self._ldap = None
		
		self._commandCount = 0
		self._searchCount = 0
		self._deleteCount = 0
		self._addCount = 0
		self._modifyCount = 0
		
	
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
			logger.info(u'Successfully connected to LDAP-Server.')
		except ldap.LDAPError, e:
			logger.error(u"Bind to LDAP failed: %s" % e)
			raise BackendIOError(u"Bind to LDAP server '%s' as '%s' failed: %s" % (self._host, self._username, e))
	
	def disconnect(self):
		''' Disconnect from ldap server '''
		if not self._ldap:
			return
		try:
			self._ldap.unbind()
		except Exception, e:
			pass
		
	def search(self, baseDn, scope, filter, attributes):
		''' This function is used to search in a ldap directory. '''
		self._commandCount += 1
		self._searchCount += 1
		logger.debug(u"Searching in baseDn: %s, scope: %s, filter: '%s', attributes: '%s' " \
					% (baseDn, scope, filter, attributes) )
		result = []
		try:
			try:
				result = self._ldap.search_s(baseDn, scope, filter, attributes)
			except ldap.LDAPError, e:
				if isinstance(e, ldap.SERVER_DOWN) or (e.__str__().lower().find('ldap connection invalid') != -1):
					# Possibly timed out
					logger.warning(u"LDAP connection possibly timed out: %s, trying to reconnect" % e)
					self.connect()
					result = self._ldap.search_s(baseDn, scope, filter, attributes)
				else:
					raise
		except Exception, e:
			logger.debug(u"LDAP search error %s: %s" % (e.__class__, e))
			if (e.__class__ == ldap.NO_SUCH_OBJECT):
				raise BackendMissingDataError(u"No results for search in baseDn: '%s', filter: '%s', scope: %s" \
					% (baseDn, filter, scope) )
			
			logger.critical(u"LDAP search error %s: %s" % (e.__class__, e))
			raise BackendIOError(u"Error searching in baseDn '%s', filter '%s', scope %s : %s" \
					% (baseDn, filter, scope, e) )
		if (result == []):
			logger.debug(u"No results for search in baseDn: '%s', filter: '%s', scope: %s" \
					% (baseDn, filter, scope) )
		return result
	
	def delete(self, dn):
		''' This function is used to delete an object in a ldap directory. '''
		self._commandCount += 1
		self._deleteCount += 1
		logger.debug(u"Deleting Object from LDAP, dn: '%s'" % dn)
		try:
			try:
				self._ldap.delete_s(dn)
			except ldap.LDAPError, e:
				if isinstance(e, ldap.SERVER_DOWN) or (e.__str__().lower().find('ldap connection invalid') != -1):
					# Possibly timed out
					logger.warning(u"LDAP connection possibly timed out: %s, trying to reconnect" % e)
					self.connect()
					self._ldap.delete_s(dn)
				else:
					raise
		except ldap.LDAPError, e:
			raise BackendIOError(e)
	
	def modifyByModlist(self, dn, old, new):
		''' This function is used to modify an object in a ldap directory. '''
		self._commandCount += 1
		self._modifyCount += 1
		
		logger.debug(u"[old]: %s" % old)
		logger.debug(u"[new]: %s" % new)
		attrs = ldap.modlist.modifyModlist(old,new)
		logger.debug(u"[change]: %s" % attrs)
		if (attrs == []):
			logger.debug(u"Object '%s' unchanged." % dn)
			return
		logger.debug(u"Modifying Object in LDAP, dn: '%s'" % dn)
		try:
			try:
				self._ldap.modify_s(dn,attrs)
			except ldap.LDAPError, e:
				if isinstance(e, ldap.SERVER_DOWN) or (e.__str__().lower().find('ldap connection invalid') != -1):
					# Possibly timed out
					logger.warning(u"LDAP connection possibly timed out: %s, trying to reconnect" % e)
					self.connect()
					self._ldap.modify_s(dn,attrs)
				else:
					raise
		except ldap.LDAPError, e:
			raise BackendIOError(e)
		except TypeError, e:
			raise BackendBadValueError(e)
		
		
	def addByModlist(self, dn, new):
		''' This function is used to add an object to the ldap directory. '''
		self._commandCount += 1
		self._addCount += 1
		
		attrs = ldap.modlist.addModlist(new)
		logger.debug(u"Adding Object to LDAP, dn: '%s'" % dn)
		logger.debug(u"attrs: '%s'" % attrs)
		try:
			try:
				self._ldap.add_s(dn,attrs)
			except ldap.LDAPError, e:
				if isinstance(e, ldap.SERVER_DOWN) or (e.__str__().lower().find('ldap connection invalid') != -1):
					# Possibly timed out
					logger.warning(u"LDAP connection possibly timed out: %s, trying to reconnect" % e)
					self.connect()
					self._ldap.add_s(dn,attrs)
				else:
					raise
		except ldap.LDAPError, e:
			raise BackendIOError(e)
		except TypeError, e:
			raise BackendBadValueError(e)










