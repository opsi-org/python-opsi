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

# OPSI imports
from OPSI.Logger import *
from Object import *
from Backend import *

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                    CLASS LDAPBACKEND                                               =
# ======================================================================================================
class LDAPBackend(DataBackend):
	
	def __init__(self, username = 'opsi', password = 'opsi', address = 'localhost', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		
		## Parse arguments
		#for (option, value) in kwargs.items():
		#	if   (option.lower() == 'database'):
		#		self._database = value
		#
		
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
		
		logger.info(u"Connecting to ldap server '%s' as user '%s'" % (self._address, self._username))
		self._ldap = LDAPSession(
				host	 = self._address,
				username = self._username, 
				password = self._password )
		self._ldap.connect()
		
		
	def base_delete(self):
		DataBackend.base_delete(self)
		
	def base_create(self):
		DataBackend.base_create(self)
	
		# Create some containers
		self.createOrganizationalRole(self._opsiBaseDn)
		for hostContainerDn in self._hostsContainerDn:
			self.createOrganizationalRole(hostContainerDn)
		self.createOrganizationalRole(self._generalConfigsContainerDn)
		self.createOrganizationalRole(self._networkConfigsContainerDn)
		self.createOrganizationalRole(self._groupsContainerDn)
		self.createOrganizationalRole(self._productsContainerDn)
		self.createOrganizationalRole(self._productClassesContainerDn)
		self.createOrganizationalRole(self._productStatesContainerDn)
		self.createOrganizationalRole(self._productPropertiesContainerDn)
		
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		DataBackend.host_insertObject(self, host)
	
	def host_updateObject(self, host):
		DataBackend.host_updateObject(self, host)
	
	def host_getObjects(self, attributes=[], **filter):
		DataBackend.host_getObjects(self, attributes=[], **filter)
	
	def host_deleteObjects(self, hosts):
		DataBackend.host_deleteObjects(self, hosts)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		DataBackend.config_insertObject(self, config)
	
	def config_updateObject(self, config):
		DataBackend.config_updateObject(self, config)
		
	def config_getObjects(self, attributes=[], **filter):
		DataBackend.config_getObjects(self, attributes=[], **filter)
	
	def config_deleteObjects(self, configs):
		DataBackend.config_deleteObjects(self, configs)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		DataBackend.configState_insertObject(self, configState)
	
	def configState_updateObject(self, configState):
		DataBackend.configState_updateObject(self, configState)
	
	def configState_getObjects(self, attributes=[], **filter):
		DataBackend.configState_getObjects(self, attributes=[], **filter)
	
	def configState_deleteObjects(self, configStates):
		DataBackend.configState_deleteObjects(self, configStates)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		DataBackend.product_insertObject(self, product)
	
	def product_updateObject(self, product):
		DataBackend.product_updateObject(self, product)
	
	def product_getObjects(self, attributes=[], **filter):
		DataBackend.product_getObjects(self, attributes=[], **filter)
	
	def product_deleteObjects(self, products):
		DataBackend.product_deleteObjects(self, products)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		DataBackend.productProperty_insertObject(self, productProperty)
	
	def productProperty_updateObject(self, productProperty):
		DataBackend.productProperty_updateObject(self, productProperty)
	
	def productProperty_getObjects(self, attributes=[], **filter):
		DataBackend.productProperty_getObjects(self, attributes=[], **filter)
	
	def productProperty_deleteObjects(self, productProperties):
		DataBackend.productProperty_deleteObjects(self, productProperties)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		DataBackend.productOnDepot_insertObject(self, productOnDepot)
	
	def productOnDepot_updateObject(self, productOnDepot):
		DataBackend.productOnDepot_updateObject(self, productOnDepot)
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		DataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		DataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		DataBackend.productOnClient_insertObject(self, productOnClient)
		
	def productOnClient_updateObject(self, productOnClient):
		DataBackend.productOnClient_updateObject(self, productOnClient)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		DataBackend.productOnClient_getObjects(self, attributes=[], **filter)
	
	def productOnClient_deleteObjects(self, productOnClients):
		DataBackend.productOnClient_deleteObjects(self, productOnClients)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		DataBackend.productPropertyState_insertObject(self, productPropertyState)
	
	def productPropertyState_updateObject(self, productPropertyState):
		DataBackend.productPropertyState_updateObject(self, productPropertyState)
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		DataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		DataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		DataBackend.group_insertObject(self, group)
	
	def group_updateObject(self, group):
		DataBackend.group_updateObject(self, group)
	
	def group_getObjects(self, attributes=[], **filter):
		DataBackend.group_getObjects(self, attributes=[], **filter)
	
	def group_deleteObjects(self, groups):
		DataBackend.group_deleteObjects(self, groups)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		DataBackend.objectToGroup_insertObject(self, objectToGroup)
	
	def objectToGroup_updateObject(self, objectToGroup):
		DataBackend.objectToGroup_updateObject(self, objectToGroup)
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		DataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		DataBackend.objectToGroup_deleteObjects(self, objectToGroups)


	
	# -------------------------------------------------
	# -     HELPERS                                   -
	# -------------------------------------------------
	def createOrganizationalRole(self, dn):
		''' This method will add a oprganizational role object
		    with the specified DN, if it does not already exist. '''
		organizationalRole = Object(dn)
		if organizationalRole.exists(self._ldap):
			logger.info(u"Organizational role '%s' already exists" % dn)
		else:
			logger.info(u"Creating organizational role '%s'" % dn)
			organizationalRole.new('organizationalRole')
			organizationalRole.writeToDirectory(self._ldap)
		logger.info(u"Organizational role '%s' created" % dn)
		


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
			raise BackendMissingDataError(u"No results for search in baseDn: '%s', filter: '%s', scope: %s" \
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

















