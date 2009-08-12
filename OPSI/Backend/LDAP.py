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
	
	def __init__(self, username = '', password = '', address = 'localhost', **kwargs):
		DataBackend.__init__(self, username, password, address, **kwargs)
		
		## Parse arguments
		#for (option, value) in kwargs.items():
		#	if   (option.lower() == 'database'):
		#		self._database = value
		#
	
	def base_delete(self):
		DataBackend.base_delete(self)
		
	def base_create(self):
		DataBackend.base_create(self)
		
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























