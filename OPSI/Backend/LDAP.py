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
#from OPSI import Tools

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
		self._configContainerDn = 'cn=configs,' + self._opsiBaseDn
		self._configStateContainerDn = 'cn=configState,' + self._opsiBaseDn
		self._groupsContainerDn = 'cn=groups,' + self._opsiBaseDn
		self._productsContainerDn = 'cn=products,' + self._opsiBaseDn
		self._productClassesContainerDn = 'cn=productClasses,' + self._opsiBaseDn
		self._productStatesContainerDn = 'cn=productStates,' + self._opsiBaseDn
		self._generalConfigsContainerDn = 'cn=generalConfigs,' + self._opsiBaseDn
		self._networkConfigsContainerDn = 'cn=networkConfigs,' + self._opsiBaseDn
		self._productPropertiesContainerDn = 'cn=productProperties,' + self._opsiBaseDn
		self._productOnDepotContainerDn = 'cn=productOnDepot,' + self._opsiBaseDn
		self._productOnClientContainerDn = 'cn=productOnClient,' + self._opsiBaseDn
		self._productPropertyStatesContainerDn = 'cn=productPropertyStates,' + self._opsiBaseDn
		self._objectToGroupContainerDn = 'cn=objectToGroup,' + self._opsiBaseDn
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
				{
					'opsiClass':     'OpsiHost',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiHost' ],
					'attributes': [
						{ 'opsiAttribute': 'id',              'ldapAttribute': 'opsiHostId' },
						{ 'opsiAttribute': 'ipAddress',       'ldapAttribute': 'opsiIpAddress' },
						{ 'opsiAttribute': 'hardwareAddress', 'ldapAttribute': 'opsiHardwareAddress' },
						{ 'opsiAttribute': 'description',     'ldapAttribute': 'opsiDescription' },
						{ 'opsiAttribute': 'notes',           'ldapAttribute': 'opsiNotes' },
						{ 'opsiAttribute': 'inventoryNumber', 'ldapAttribute': 'opsiInventoryNumber' }
					]
				},
				{
					'opsiClass':      'OpsiClient',
					'opsiSuperClass': 'OpsiHost',
					'objectClasses':  [ 'opsiHost', 'opsiClient' ],
					'attributes': [
						{ 'opsiAttribute': 'created',         'ldapAttribute': 'opsiCreatedTimestamp' },
						{ 'opsiAttribute': 'lastSeen',        'ldapAttribute': 'opsiLastSeenTimestamp' },
						{ 'opsiAttribute': 'opsiHostKey',     'ldapAttribute': 'opsiHostKey' }
					]
				},
				{
					'opsiClass':      'OpsiDepotserver',
					'opsiSuperClass': 'OpsiHost',
					'objectClasses':  [ 'opsiHost', 'opsiDepotserver' ],
					'attributes': [
						{ 'opsiAttribute': 'depotLocalUrl',       'ldapAttribute': 'opsiDepotLocalUrl' },
						{ 'opsiAttribute': 'depotRemoteUrl',      'ldapAttribute': 'opsiDepotRemoteUrl' },
						{ 'opsiAttribute': 'repositoryLocalUrl',  'ldapAttribute': 'opsiRepositoryLocalUrl' },
						{ 'opsiAttribute': 'repositoryRemoteUrl', 'ldapAttribute': 'opsiRepositoryRemoteUrl' },
						{ 'opsiAttribute': 'networkAddress',      'ldapAttribute': 'opsiNetworkAddress' },
						{ 'opsiAttribute': 'maxBandwidth',        'ldapAttribute': 'opsiMaximumBandwidth' },
						{ 'opsiAttribute': 'opsiHostKey',         'ldapAttribute': 'opsiHostKey' }
					]
				 },
				 {
					'opsiClass':      'OpsiConfigserver',
					'opsiSuperClass': 'OpsiDepotserver',
					'objectClasses':  [ 'opsiHost', 'opsiDepotserver', 'opsiConfigserver' ],
					'attributes': [
					]
				 },
				 {
					'opsiClass':     'Config',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiConfig' ],
					'attributes': [
						{ 'opsiAttribute': 'id',              'ldapAttribute': 'opsiConfigId' },
						{ 'opsiAttribute': 'description',     'ldapAttribute': 'opsiDescription' },
						{ 'opsiAttribute': 'defaultValues',   'ldapAttribute': 'opsiDefaultValue' },
						{ 'opsiAttribute': 'possibleValues',  'ldapAttribute': 'opsiPossibleValue' },
						{ 'opsiAttribute': 'editable',        'ldapAttribute': 'opsiEditable' },
						{ 'opsiAttribute': 'multiValue',      'ldapAttribute': 'opsiMultiValue' }
					]
				},
				{
					'opsiClass':      'UnicodeConfig',
					'opsiSuperClass': 'Config',
					'objectClasses':  [ 'opsiConfig', 'opsiUnicodeConfig' ],
					'attributes': [
					]
				 },
				 {
					'opsiClass':      'BoolConfig',
					'opsiSuperClass': 'Config',
					'objectClasses':  [ 'opsiConfig', 'opsiBoolConfig' ],
					'attributes': [
					]
				 },
				 {
					'opsiClass':     'ConfigState',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiConfigState' ],
					'attributes': [
						{ 'opsiAttribute': 'configId',        'ldapAttribute': 'opsiConfigId' },
						{ 'opsiAttribute': 'objectId',        'ldapAttribute': 'opsiObjectId' },
						{ 'opsiAttribute': 'values',          'ldapAttribute': 'opsiValue' }
					]
				},
				{
					'opsiClass':     'Product',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProduct' ],
					'attributes': [
						{ 'opsiAttribute': 'id',                    'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'productVersion',        'ldapAttribute': 'opsiProductVersion' },
						{ 'opsiAttribute': 'packageVersion',        'ldapAttribute': 'opsiPackageVersion' },
						{ 'opsiAttribute': 'name',                  'ldapAttribute': 'opsiProductName' },
						{ 'opsiAttribute': 'licenseRequired',       'ldapAttribute': 'opsiProductLicenseRequired' },
						{ 'opsiAttribute': 'setupScript',           'ldapAttribute': 'opsiSetupScript' },
						{ 'opsiAttribute': 'uninstallScript',       'ldapAttribute': 'opsiUninstallScript' },
						{ 'opsiAttribute': 'updateScript',          'ldapAttribute': 'opsiUpdateScript' },
						{ 'opsiAttribute': 'alwaysScript',          'ldapAttribute': 'opsiAlwaysScript' },
						{ 'opsiAttribute': 'onceScript',            'ldapAttribute': 'opsiOnceScript' },
						{ 'opsiAttribute': 'customScript',          'ldapAttribute': 'opsiCustomScript' },
						{ 'opsiAttribute': 'userLoginScript',       'ldapAttribute': 'opsiUserLoginScript' },
						{ 'opsiAttribute': 'priority',        	    'ldapAttribute': 'opsiProductPriority' },
						{ 'opsiAttribute': 'description',           'ldapAttribute': 'description' },
						{ 'opsiAttribute': 'advice',                'ldapAttribute': 'opsiProductAdvice' },
						{ 'opsiAttribute': 'changelog',             'ldapAttribute': 'opsiProductChangeLog' },
						{ 'opsiAttribute': 'windowsSoftwareIds',    'ldapAttribute': 'opsiWindowsSoftwareId' },
						{ 'opsiAttribute': 'productClassIds',       'ldapAttribute': 'opsiProductClassId' }
						
					]
				},
				{
					'opsiClass':      'LocalbootProduct',
					'opsiSuperClass': 'Product',
					'objectClasses':  [ 'opsiProduct', 'opsiLocalBootProduct' ],
					'attributes': [
					]
				 },
				 {
					'opsiClass':     'NetbootProduct',
					'opsiSuperClass': 'Product',
					'objectClasses': [ 'opsiProduct', 'opsiNetBootProduct' ],
					'attributes': [
						{ 'opsiAttribute': 'pxeConfigTemplate',    'ldapAttribute': 'opsiPxeConfigTemplate' }
					]
				},
				{
					'opsiClass':     'ProductProperty',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProductProperty' ],
					'attributes': [
						{ 'opsiAttribute': 'productId',             'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'propertyId',            'ldapAttribute': 'opsiPropertyId' },
						{ 'opsiAttribute': 'productVersion',        'ldapAttribute': 'opsiProductVersion' },
						{ 'opsiAttribute': 'packageVersion',        'ldapAttribute': 'opsiPackageVersion' },
						{ 'opsiAttribute': 'description',           'ldapAttribute': 'opsiDescription' },
						{ 'opsiAttribute': 'requiredProductId',     'ldapAttribute': 'opsiRequiredProductId' },
						{ 'opsiAttribute': 'possibleValues',        'ldapAttribute': 'opsiPossibleValue' },
						{ 'opsiAttribute': 'defaultValues',         'ldapAttribute': 'opsiDefaultValue' },
						{ 'opsiAttribute': 'editable',              'ldapAttribute': 'opsiEditable' },
						{ 'opsiAttribute': 'multiValue',            'ldapAttribute': 'opsiMultiValue' }
					]
				},
				{
					'opsiClass':      'UnicodeProductProperty',
					'opsiSuperClass': 'ProductProperty',
					'objectClasses':  [ 'opsiProductProperty', 'opsiUnicodeProductProperty' ],
					'attributes': [
					]
				 },
				 {
					'opsiClass':     'BoolProductProperty',
					'opsiSuperClass': 'ProductProperty',
					'objectClasses': [ 'opsiProductProperty', 'opsiBoolProductProperty' ],
					'attributes': [
						{ 'opsiAttribute': 'pxeConfigTemplate',    'ldapAttribute': 'opsiPxeConfigTemplate' }
					]
				},
				{
					'opsiClass':     'ProductDependency',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProductDependency' ],
					'attributes': [
						{ 'opsiAttribute': 'productId',                     'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'productVersion',                'ldapAttribute': 'opsiProductVersion' },
						{ 'opsiAttribute': 'packageVersion',                'ldapAttribute': 'opsiPackageVersion' },
						{ 'opsiAttribute': 'requiredProductId',             'ldapAttribute': 'opsiRequiredProductId' },
						{ 'opsiAttribute': 'requiredAction',                'ldapAttribute': 'opsiActionRequired' },
						{ 'opsiAttribute': 'productAction',                 'ldapAttribute': 'opsiProductAction' },
						{ 'opsiAttribute': 'requiredProductVersion',        'ldapAttribute': 'opsiRequiredProductVersion' },
						{ 'opsiAttribute': 'requiredPackageVersion',        'ldapAttribute': 'opsiRequiredPackageVersion' },
						{ 'opsiAttribute': 'requiredInstallationStatus',    'ldapAttribute': 'opsiInstallationStatusRequired' },
						{ 'opsiAttribute': 'requirementType',               'ldapAttribute': 'opsiRequirementType' }
					]
				},
				{
					'opsiClass':     'ProductOnDepot',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProductOnDepot' ],
					'attributes': [
						{ 'opsiAttribute': 'productId',                     'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'productType',                   'ldapAttribute': 'opsiProductType' },
						{ 'opsiAttribute': 'productVersion',                'ldapAttribute': 'opsiProductVersion' },
						{ 'opsiAttribute': 'packageVersion',                'ldapAttribute': 'opsiPackageVersion' },
						{ 'opsiAttribute': 'depotId',                       'ldapAttribute': 'opsiDepotId' },
						{ 'opsiAttribute': 'locked',                        'ldapAttribute': 'opsiLocked' }
					]
				},
				{
					'opsiClass':     'ProductOnClient',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProductOnClient' ],
					'attributes': [
						{ 'opsiAttribute': 'productId',                     'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'productType',                   'ldapAttribute': 'opsiProductType' },
						{ 'opsiAttribute': 'clientId',                      'ldapAttribute': 'opsiClientId' },
						{ 'opsiAttribute': 'installationStatus',            'ldapAttribute': 'opsiProductInstallationStatus' },
						{ 'opsiAttribute': 'actionRequest',                 'ldapAttribute': 'opsiProductActionRequest' },
						{ 'opsiAttribute': 'actionProgress',                'ldapAttribute': 'opsiProductActionProgress' },
						{ 'opsiAttribute': 'productVersion',                'ldapAttribute': 'opsiProductVersion' },
						{ 'opsiAttribute': 'packageVersion',                'ldapAttribute': 'opsiPackageVersion' },
						{ 'opsiAttribute': 'lastStateChange',               'ldapAttribute': 'lastStateChange' }
					]
				},
				{
					'opsiClass':     'ProductPropertyState',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiProductPropertyState' ],
					'attributes': [
						{ 'opsiAttribute': 'productId',                     'ldapAttribute': 'opsiProductId' },
						{ 'opsiAttribute': 'propertyId',                    'ldapAttribute': 'opsiPropertyId' },
						{ 'opsiAttribute': 'objectId',                      'ldapAttribute': 'opsiObjectId' },
						{ 'opsiAttribute': 'values',                        'ldapAttribute': 'opsiProductPropertyValues' }
					]
				},
				{
					'opsiClass':     'HostGroup',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiHostGroup' ],
					'attributes': [
						{ 'opsiAttribute': 'id',                     'ldapAttribute': 'opsiGroupId' },
						{ 'opsiAttribute': 'description',                    'ldapAttribute': 'opsiDescription' },
						{ 'opsiAttribute': 'notes',                      'ldapAttribute': 'opsiNotes' },
						{ 'opsiAttribute': 'parentGroupId',                        'ldapAttribute': 'opsiParentGroupId' }
					]
				},
				{
					'opsiClass':     'ObjectToGroup',
					'opsiSuperClass': None,
					'objectClasses': [ 'opsiObjectToGroup' ],
					'attributes': [
						{ 'opsiAttribute': 'groupId',                     'ldapAttribute': 'opsiGroupId' },
						{ 'opsiAttribute': 'objectId',                    'ldapAttribute': 'opsiObjectId' }
					]
				}
			]
		
		self._opsiAttributeToLdapAttribute = {}
		self._ldapAttributeToOpsiAttribute = {}
		self._opsiClassToLdapClasses = {}
		for mapping in self._mappings:
			self._opsiClassToLdapClasses[ mapping['opsiClass'] ] = mapping['objectClasses']
			self._opsiAttributeToLdapAttribute[ mapping['opsiClass'] ] = {}
			self._ldapAttributeToOpsiAttribute[ mapping['opsiClass'] ] = {}
			if mapping.get('opsiSuperClass'):
				self._opsiAttributeToLdapAttribute[ mapping['opsiClass'] ] = dict( self._opsiAttributeToLdapAttribute[ mapping['opsiSuperClass'] ] )
				self._ldapAttributeToOpsiAttribute[ mapping['opsiClass'] ] = dict( self._ldapAttributeToOpsiAttribute[ mapping['opsiSuperClass'] ] )
			for attribute in mapping['attributes']:
				self._opsiAttributeToLdapAttribute[ mapping['opsiClass'] ][ attribute['opsiAttribute'] ] = attribute['ldapAttribute']
				self._ldapAttributeToOpsiAttribute[ mapping['opsiClass'] ][ attribute['ldapAttribute'] ] = attribute['opsiAttribute']
		
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
		
		ldapFilter = None
		filters = []
		objectTypes = []
		for objectType in forceList(filter.get('type')):
			if not objectType in objectTypes:
				objectTypes.append(objectType)
			objectClasses = self._opsiClassToLdapClasses.get(objectType)
			if not objectClasses:
				continue
			
			classFilters = []
			for objectClass in objectClasses:
				classFilters.append(
					pureldap.LDAPFilter_equalityMatch(
						attributeDesc  = pureldap.LDAPAttributeDescription('objectClass'),
						assertionValue = pureldap.LDAPAssertionValue(objectClass)
					)
				)
			
			if classFilters:
				if (len(classFilters) == 1):
					filters.append(classFilters[0])
				else:
					filters.append(pureldap.LDAPFilter_and(classFilters))
			
		if filters:
			if (len(filters) == 1):
				ldapFilter = filters[0]
			else:
				ldapFilter = pureldap.LDAPFilter_or(filters)
		
		if not ldapFilter:
			ldapFilter = pureldap.LDAPFilter_present('objectClass')
		
		
		andFilters = []
		for (attribute, values) in filter.items():
			if (attribute == 'type'):
				continue
			if (attribute == 'cn'):
				continue
				
			if values is None:
				continue
			
			mappingFound = False
			for objectType in objectTypes:
				if self._opsiAttributeToLdapAttribute[objectType].has_key(attribute):
					attribute = self._opsiAttributeToLdapAttribute[objectType][attribute]
					mappingFound = True
					break
			
			if not mappingFound:
				logger.error(u"No mapping found for opsi attribute '%s' of classes %s" % (attribute, objectTypes))
			
			filters = []
			for value in forceList(values):
				if (value == None):
					filters.append(
						pureldap.LDAPFilter_not(
							pureldap.LDAPFilter_present(attribute)
						)
					)
					
				else:
					if type(value) is bool:
						if value: value = u'TRUE'
						else: value = u'FALSE'
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
		
		return ldapFilter.asText()
		
	
		
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
	
	def backend_deleteBase(self):
		ConfigDataBackend.backend_deleteBase(self)
		ldapobj = LDAPObject(self._opsiBaseDn)
		if ldapobj.exists(self._ldap):
			ldapobj.deleteFromDirectory(self._ldap, recursive = True)
		
		
	def backend_createBase(self):
		ConfigDataBackend.backend_createBase(self)
		
		# Create some containers
		self._createOrganizationalRole(self._opsiBaseDn)
		self._createOrganizationalRole(self._hostsContainerDn)
		self._createOrganizationalRole(self._configContainerDn)
		self._createOrganizationalRole(self._configStateContainerDn)
		self._createOrganizationalRole(self._generalConfigsContainerDn)
		self._createOrganizationalRole(self._networkConfigsContainerDn)
		self._createOrganizationalRole(self._groupsContainerDn)
		self._createOrganizationalRole(self._productsContainerDn)
		self._createOrganizationalRole(self._productClassesContainerDn)
		self._createOrganizationalRole(self._productStatesContainerDn)
		self._createOrganizationalRole(self._productPropertiesContainerDn)
		self._createOrganizationalRole(self._productOnDepotContainerDn)
		self._createOrganizationalRole(self._productOnClientContainerDn)
		self._createOrganizationalRole(self._productPropertyStatesContainerDn)
		self._createOrganizationalRole(self._objectToGroupContainerDn)
	
	
	def backend_exit(self):
		pass
	
	def _ldapObjectToOpsiObject(self, ldapObject, attributes=[]):
		'''
			Method to convert ldap-Object to opsi-Object
		
		'''
		self._ldapAttributeToOpsiAttribute
		self._opsiClassToLdapClasses
		
		
		ldapObject.readFromDirectory(self._ldap)
		
		logger.info(u"Searching opsi class for ldap objectClasses: %s" % ldapObject.getObjectClasses())
		opsiClassName = None
		for (opsiClass, ldapClasses) in self._opsiClassToLdapClasses.items():
			logger.debug(u"Testing opsi class '%s' (ldapClasses: %s)" % (opsiClass, ldapClasses))
			matched = True
			for objectClass in ldapObject.getObjectClasses():
				if not objectClass in ldapClasses:
					matched = False
					continue
			for objectClass in ldapClasses:
				if not objectClass in ldapObject.getObjectClasses():
					matched = False
					continue
			
			if matched:
				logger.debug(u"Matched")
				opsiClassName = opsiClass
				break
		
		if not opsiClassName:
			raise Exception(u"Failed to get opsi class for ldap objectClasses: %s" % ldapObject.getObjectClasses())
		
		# [ 'opsiHost', 'opsiDepotserver', 'opsiConfigserver' ],
		# Mapped ldap objectClasses ['opsiHost', 'opsiDepotserver'] to opsi class: OpsiConfigserver
		logger.info(u"Mapped ldap objectClasses %s to opsi class: %s" % (ldapObject.getObjectClasses(), opsiClassName))
		
		Class = eval(opsiClassName)
		identAttributes = mandatoryConstructorArgs(Class)
		if attributes:
			for identAttribute in identAttributes:
				if not identAttribute in attributes:
					attributes.append(identAttribute)
		
		opsiObjectHash = {}
		for (attribute, value) in ldapObject.getAttributeDict(valuesAsList = False).items():
			logger.debug(u"LDAP attribute is: %s" % attribute)
			if attribute in ('objectClass', 'cn'):
				continue
			
			if self._ldapAttributeToOpsiAttribute[opsiClassName].has_key(attribute):
				attribute = self._ldapAttributeToOpsiAttribute[opsiClassName][attribute]
			else:
				logger.error(u"No mapping found for ldap attribute '%s' of class '%s'" % (attribute, opsiClassName))
			
			if attribute in ('cn'):
				continue
			
			if not attributes or attribute in attributes:
				opsiObjectHash[attribute] = value
		
		return Class.fromHash(opsiObjectHash)
	
	def _opsiObjectToLdapObject(self, opsiObject, dn):
		'''
			Method to convert Opsi-Object to ldap-Object
		'''
		
		objectClasses = []
		
		for (opsiClass, ldapClasses) in self._opsiClassToLdapClasses.items():
			if (opsiObject.getType() == opsiClass):
				objectClasses = ldapClasses
				break
		
		if not objectClasses:
			raise Exception(u"Failed to get ldapClasses for OpsiClass: %s" % opsiObject)
			
		
		ldapObj = LDAPObject(dn)
		ldapObj.new(*objectClasses)
		for (attribute, value) in opsiObject.toHash().items():
			if (attribute == 'type'):
				continue
			if (attribute == 'productClassIds'):
				value = []
			if self._opsiAttributeToLdapAttribute[opsiObject.getType()].has_key(attribute):
				attribute = self._opsiAttributeToLdapAttribute[opsiObject.getType()][attribute]
			else:
				logger.error(u"No mapping found for opsi attribute '%s' of class '%s'" % (attribute, opsiObject.getType()))
			ldapObj.setAttribute(attribute, value)
		
		return ldapObj

		
	def _updateLdapObject(self, ldapObject, opsiObject):
		ldapObject.readFromDirectory(self._ldap)
		newLdapObject = self._opsiObjectToLdapObject(opsiObject, ldapObject.getDn())
		for (attribute, value) in newLdapObject.getAttributeDict(valuesAsList=True).items():
			if attribute in ('cn', 'objectClass'):
				continue
			if not value:
				continue
			ldapObject.setAttribute(attribute, value)
		ldapObject.writeToDirectory(self._ldap)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		dn = 'cn=%s,%s' % (host.id, self._hostsContainerDn)
		logger.info(u"Creating host: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(host, dn)
		ldapObject.writeToDirectory(self._ldap)
		
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		dn = 'cn=%s,%s' % (host.id, self._hostsContainerDn)
		logger.info(u"Updating host: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, host)
		
	def host_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.host_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting hosts, filter: %s" % filter)
		hosts = []
		
		if not filter.get('type'):
			filter['type'] = [ 'OpsiClient', 'OpsiDepotserver', 'OpsiConfigserver']
		
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._hostsContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			hosts.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return hosts
		
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		logger.error(u"DELETING hosts %s" % hosts)
		for host in forceObjectClassList(hosts, Host):
			dn = 'cn=%s,%s' % (host.id, self._hostsContainerDn)
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting host: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		
		dn = 'cn=%s,%s' % (config.id, self._configContainerDn)
		
		logger.info(u"Creating Config: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(config, dn)
		ldapObject.writeToDirectory(self._ldap)
		
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
		dn = 'cn=%s,%s' % (config.id, self._configContainerDn)
		logger.info(u"Updating config: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, config)
		
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting configs, filter %s" % filter)
		configs = []
		
		if not filter.get('type'):
			filter['type'] = [ 'Config', 'UnicodeConfig', 'BoolConfig']
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._configContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			configs.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return configs
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		
		logger.error(u"DELETING configs %s" % configs)
		for config in forceObjectClassList(configs, Config):
			dn = 'cn=%s,%s' % (config.id, self._configContainerDn)
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting configs: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
		
		containerDn = 'cn=%s,%s' % (configState.objectId, self._configStateContainerDn)
		self._createOrganizationalRole(containerDn)
		dn = 'cn=%s,%s' % (configState.configId, containerDn)
		
		logger.info(u"Creating ConfigState: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(configState, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
		
		dn = 'cn=%s,cn=%s,%s' % (configState.configId, configState.objectId, self._configStateContainerDn)
		
		logger.info(u"Updating configState: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, configState)
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting configState, filter %s" % filter)
		configStates = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ConfigState']
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._configStateContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			configStates.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return configStates
		
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
	
		logger.error(u"DELETING configStates %s" % configStates)
		for configState in forceObjectClassList(configStates, ConfigState):
			dn = 'cn=%s,cn=%s,%s' % (configState.configId, configState.objectId, self._configStateContainerDn)
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting configState: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		
		dn = 'cn=%s_%s-%s,%s' % (product.id, product.productVersion, product.packageVersion, self._productsContainerDn)
		
		logger.info(u"Creating Product: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(product, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		
		dn = 'cn=%s_%s-%s,%s' % (product.id, product.productVersion, product.packageVersion, self._productsContainerDn)
		logger.info(u"Updating product: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, product)
		
	def product_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
	
		logger.info(u"Getting products, filter %s" % filter)
		products = []
		
		if not filter.get('type'):
			filter['type'] = [ 'Product', 'LocalbootProduct', 'NetbootProduct' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productsContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			products.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return products
		
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
	
	
		logger.error(u"DELETING products %s" % products)
		for product in forceObjectClassList(products, Product):
			dn = 'cn=%s_%s-%s,%s' % (product.id, product.productVersion, product.packageVersion, self._productsContainerDn)
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting products: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
				
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		
		containerDn = 'cn=productProperties,cn=%s_%s-%s,%s' \
			% (productProperty.productId, productProperty.productVersion, productProperty.packageVersion, self._productsContainerDn)
		
		self._createOrganizationalRole(containerDn)
		
		dn = 'cn=%s,%s' % (productProperty.propertyId, containerDn)
		
		logger.info(u"Creating ProductProperty: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(productProperty, dn)
		ldapObject.writeToDirectory(self._ldap)
		
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		
		containerDn = 'cn=productProperties,cn=%s_%s-%s,%s' \
			% (productProperty.productId, productProperty.productVersion, productProperty.packageVersion, self._productsContainerDn)
		
		dn = 'cn=%s,%s' % (productProperty.propertyId, containerDn)
		
		logger.info(u"Updating ProductProperty: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, productProperty)
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productProperty, filter %s" % filter)
		properties = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productsContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			properties.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return properties
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		
		logger.error(u"DELETING productProperties %s" % productProperties)
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			containerDn = 'cn=productProperties,cn=%s_%s-%s,%s' \
				% (productProperty.productId, productProperty.productVersion, productProperty.packageVersion, self._productsContainerDn)
			
			dn = 'cn=%s,%s' % (productProperty.propertyId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting configState: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		
		containerDn = 'cn=productDependencies,cn=%s_%s-%s,%s' \
			% (productDependency.productId, productDependency.productVersion, productDependency.packageVersion, self._productsContainerDn)
		self._createOrganizationalRole(containerDn)
		
		containerDn = 'cn=%s,%s' % (productDependency.productAction, containerDn)
		self._createOrganizationalRole(containerDn)
		
		dn = 'cn=%s,%s' % (productDependency.requiredProductId, containerDn)
		
		logger.info(u"Creating productDependency: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(productDependency, dn)
		ldapObject.writeToDirectory(self._ldap)
		
	def productDependency_updateObject(self, productDependency):
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		
		containerDn = 'cn=productDependencies,cn=%s_%s-%s,%s' \
			% (productDependency.productId, productDependency.productVersion, productDependency.packageVersion, self._productsContainerDn)
		containerDn = 'cn=%s,%s' % (productDependency.productAction, containerDn)
		dn = 'cn=%s,%s' % (productDependency.requiredProductId, containerDn)
		
		logger.info(u"Updating ProductDependency: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, productDependency)
		
	def productDependency_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productDependency, filter %s" % filter)
		dependencies = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ProductDependency' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productsContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			dependencies.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return dependencies
	
	def productDependency_deleteObjects(self, productDependencies):
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		
		logger.error(u"DELETING productDependency %s" % productDependencies)
		for productDependency in forceObjectClassList(productDependencies, ProductDependency):
			containerDn = 'cn=productDependencies,cn=%s_%s-%s,%s' \
				% (productDependency.productId, productDependency.productVersion, productDependency.packageVersion, self._productsContainerDn)
			containerDn = 'cn=%s,%s' % (productDependency.productAction, containerDn)
			dn = 'cn=%s,%s' % (productDependency.requiredProductId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting productDependency: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		
		#containerDn = 'cn=productDependencies,cn=%s_%s-%s,%s' \
		#	% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion, self._productOnDepotContainerDn)
		
		containerDn = 'cn=%s,%s' % (productOnDepot.depotId, self._productOnDepotContainerDn)
		self._createOrganizationalRole(containerDn)
		
		dn = 'cn=%s,%s' % (productOnDepot.productId, containerDn)
		
		logger.info(u"Creating ProductOnDepot: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(productOnDepot, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
	
		containerDn = 'cn=%s,%s' % (productOnDepot.depotId, self._productOnDepotContainerDn)
		dn = 'cn=%s,%s' % (productOnDepot.productId, containerDn)
		
		logger.info(u"Updating ProductOnDepot: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, productOnDepot)
		
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productOnDepot, filter %s" % filter)
		products = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ProductOnDepot' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productOnDepotContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			products.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return products
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
		logger.error(u"DELETING productOnDepot %s" % productOnDepots)
		for productOnDepot in forceObjectClassList(productOnDepots, ProductOnDepot):
			containerDn = 'cn=%s,%s' % (productOnDepot.depotId, self._productOnDepotContainerDn)
			dn = 'cn=%s,%s' % (productOnDepot.productId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting productOnDepot: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
		
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		
		#containerDn = 'cn=productDependencies,cn=%s_%s-%s,%s' \
		#	% (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion, self._productOnDepotContainerDn)
		
		containerDn = 'cn=%s,%s' % (productOnClient.clientId, self._productOnClientContainerDn)
		self._createOrganizationalRole(containerDn)
		
		dn = 'cn=%s,%s' % (productOnClient.productId, containerDn)
		
		logger.info(u"Creating ProductOnClient: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(productOnClient, dn)
		ldapObject.writeToDirectory(self._ldap)
		
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		
		containerDn = 'cn=%s,%s' % (productOnClient.clientId, self._productOnClientContainerDn)
		dn = 'cn=%s,%s' % (productOnClient.productId, containerDn)
		
		logger.info(u"Updating ProductOnClient: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, productOnClient)
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productOnClient, filter %s" % filter)
		products = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ProductOnClient' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productOnClientContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			products.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return products
		
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		
		logger.error(u"DELETING productOnClient %s" % productOnClients)
		for productOnClient in forceObjectClassList(productOnClients, ProductOnClient):
			containerDn = 'cn=%s,%s' % (productOnClient.clientId, self._productOnClientContainerDn)
			dn = 'cn=%s,%s' % (productOnClient.productId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting productOnClient: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
		
		containerDn = 'cn=%s,%s' % (productPropertyState.objectId, self._productPropertyStatesContainerDn)
		self._createOrganizationalRole(containerDn)
		containerDn = 'cn=%s,%s' % (productPropertyState.productId, containerDn)
		self._createOrganizationalRole(containerDn)
		
		dn = 'cn=%s,%s' % (productPropertyState.propertyId, containerDn)
		
		logger.info(u"Creating ProductPropertyState: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(productPropertyState, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def productPropertyState_updateObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
		
		containerDn = 'cn=%s,cn=%s,%s' % (productPropertyState.productId, productPropertyState.objectId, self._productPropertyStatesContainerDn)
		dn = 'cn=%s,%s' % (productPropertyState.propertyId, containerDn)
		
		logger.info(u"Updating ProductPropertyState: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, productOnClient)
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting ProductPropertyState, filter %s" % filter)
		propertyStates = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ProductPropertyState' ]
			
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._productPropertyStatesContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			propertyStates.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return propertyStates
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
		
		logger.error(u"DELETING productPropertyStates %s" % productPropertyStates)
		for productPropertyState in forceObjectClassList(productPropertyStates, ProductPropertyState):
			containerDn = 'cn=%s,cn=%s,%s' % (productPropertyState.productId, productPropertyState.objectId, self._productPropertyStatesContainerDn)
			dn = 'cn=%s,%s' % (productPropertyState.propertyId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting productPropertyStates: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		ConfigDataBackend.group_insertObject(self, group)
		
		dn = 'cn=%s,%s' % (group.id, self._groupsContainerDn)
		logger.info(u"Creating group: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(group, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def group_updateObject(self, group):
		ConfigDataBackend.group_updateObject(self, group)
		
		dn = 'cn=%s,%s' % (group.id, self._groupsContainerDn)
		logger.info(u"Updating group: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, group)
	
	def group_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting groups, filter: %s" % filter)
		groups = []
		
		if not filter.get('type'):
			filter['type'] = [ 'HostGroup' ]
		
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._groupsContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			groups.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return groups
	
	def group_deleteObjects(self, groups):
		ConfigDataBackend.group_deleteObjects(self, groups)
		
		logger.error(u"DELETING groups %s" % groups)
		for group in forceObjectClassList(groups, HostGroup):
			dn = 'cn=%s,%s' % (group.id, self._groupsContainerDn)
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting group: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
		
		containerDn = 'cn=%s,%s' % (objectToGroup.groupId, self._objectToGroupContainerDn)
		self._createOrganizationalRole(containerDn)
		dn = 'cn=%s,%s' % (objectToGroup.objectId, containerDn)
		
		logger.info(u"Creating objectToGroup: %s" % dn)
		ldapObject = self._opsiObjectToLdapObject(objectToGroup, dn)
		ldapObject.writeToDirectory(self._ldap)
	
	def objectToGroup_updateObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
		
		containerDn = 'cn=%s,%s' % (objectToGroup.groupId, self._objectToGroupContainerDn)
		dn = 'cn=%s,%s' % (objectToGroup.objectId, containerDn)
		
		logger.info(u"Updating objectToGroup: %s" % dn)
		ldapObject = LDAPObject(dn)
		self._updateLdapObject(ldapObject, objectToGroup)
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting objectToGroup, filter: %s" % filter)
		objectToGroups = []
		
		if not filter.get('type'):
			filter['type'] = [ 'ObjectToGroup' ]
		
		ldapFilter = self._objectFilterToLDAPFilter(filter)
		
		search = LDAPObjectSearch(self._ldap, self._objectToGroupContainerDn, filter=ldapFilter )
		for ldapObject in search.getObjects():
			objectToGroups.append( self._ldapObjectToOpsiObject(ldapObject, attributes) )
		return objectToGroups
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		
		logger.error(u"DELETING objectToGroups %s" % objectToGroups)
		for objectToGroup in forceObjectClassList(objectToGroups, ObjectToGroup):
			containerDn = 'cn=%s,%s' % (objectToGroup.groupId, self._objectToGroupContainerDn)
			dn = 'cn=%s,%s' % (objectToGroup.objectId, containerDn)
			
			ldapObj = LDAPObject(dn)
			if ldapObj.exists(self._ldap):
				logger.info(u"Deleting objectToGroups: %s" % dn)
				ldapObj.deleteFromDirectory(self._ldap, recursive = True)











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
	
	def getAttributeDict(self, valuesAsList=False):
		''' Get all attributes of object as dict.
		    All values in self._new are lists by default, 
		    a list of length 0 becomes the value None
		    if there is only one item the item's value is used '''
		ret = {}
		
		for (key, values) in self._new.items():
			if (values == [' ']):
				values = [u'']
			for i in range(len(values)):
				if   values[i] == u'TRUE':  self._new[key][i] = True
				elif values[i] == u'FALSE': self._new[key][i] = False
			if ( len(values) > 1 or valuesAsList):
				ret[key] = values
			else:
				ret[key] = values[0]
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
		for i in range(len(values)):
			if   values[i] == u'TRUE':  values[i] = True
			elif values[i] == u'FALSE': values[i] = False
		if ( len(values) > 1 or valuesAsList):
			return values
		return values[0]
	
	def setAttribute(self, attribute, value):
		ldapValue = []
		if not value is None:
			value = forceList(value)
			for v in value:
				if type(v) is bool:
					if v: v = u'TRUE'
					else: v = u'FALSE'
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










