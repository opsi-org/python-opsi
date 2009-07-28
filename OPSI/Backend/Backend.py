#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Backend   =
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

__version__ = '3.5'

from OPSI.Logger import *
from OPSI.Backend.Object import *
logger = Logger()

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                                                                                    =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''


'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                        CLASS BACKEND                                               =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class Backend:
	def __init__(self, username = '', password = '', address = '', **kwargs):
		pass

'''= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
=                                      CLASS DATABACKEND                                             =
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='''
class DataBackend(Backend):
	
	def __init__(self, username = '', password = '', address = '', **kwargs):
		pass
	
	def base_create(self):
		raise NotImplemented
	
	def base_delete(self):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_create(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			logger.info("Creating host '%s'" % host)
			if self.host_get(attributes = ['id'], id = host.id):
				logger.info("Host '%s' already exists, updating" % host)
				self.host_update(host)
			self.host_insert(host)
		
	def host_insert(self, host):
		raise NotImplemented
	
	def host_update(self, host):
		raise NotImplemented
	
	def host_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def host_delete(self, hosts):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_create(self, configs):
		for config in forceObjectClassList(configs, Config):
			logger.info("Creating config %s" % config)
			if self.config_get(attributes = ['name'], name = config.name):
				logger.info("Config '%s' already exists, updating" % config)
				self.config_update(config)
			self.config_insert(config)
	
	def config_insert(self, config):
		raise NotImplemented
	
	def config_update(self, config):
		raise NotImplemented
	
	def config_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def config_delete(self, configs):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_create(self, products):
		for product in forceObjectClassList(products, Product):
			logger.info("Creating product %s" % product)
			if self.product_get(attributes = ['productId'], id = product.id, productVersion = product.productVersion, packageVersion = product.packageVersion):
				logger.info("Product '%s' already exists, updating" % product)
				self.product_update(product)
			self.product_insert(product)
	
	def product_insert(self, product):
		raise NotImplemented
	
	def product_update(self, product):
		raise NotImplemented
	
	def product_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def product_delete(self, products):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_create(self, productProperties):
		for productProperty in forceObjectClassList(productProperties, ProductProperty):
			logger.info("Creating product property %s" % productProperty)
			if self.productProperty_get(	attributes = ['productId'],
						productId = productProperty.productId,
						productVersion = productProperty.productVersion,
						packageVersion = productProperty.packageVersion,
						name = productProperty.name):
				logger.info("Product property '%s' already exists, updating" % productProperty)
				self.productProperty_update(productProperty)
			self.productProperty_insert(productProperty)
	
	def productProperty_insert(self, productProperty):
		raise NotImplemented
	
	def productProperty_update(self, productProperty):
		raise NotImplemented
	
	def productProperty_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def productProperty_delete(self, productProperties):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_create(self, productOnDepots):
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		for productOnDepot in productOnDepots:
			logger.info("Creating productOnDepot '%s'" % productOnDepot)
			if self.productOnDepot_get(productId = productOnDepot.productId, depotId = productOnDepot.depotId):
				logger.info("ProductOnDepot '%s' already exists, updating" % productOnDepot)
				self.productOnDepot_update(productOnDepot)
			self.productOnDepot_insert(productOnDepot)
	
	def productOnDepot_insert(self, productOnDepot):
		raise NotImplemented
	
	def productOnDepot_update(self, productOnDepot):
		raise NotImplemented
	
	def productOnDepot_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def productOnDepot_delete(self, productOnDepots):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductStates                                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productState_create(self, productStates):
		productStates = forceObjectClassList(productStates, ProductState)
		for productState in productStates:
			logger.info("Creating productState '%s'" % productState)
			if self.productState_get(productId = productState.productId, hostId = productState.hostId):
				logger.info("ProductState '%s' already exists, updating" % productState)
				self.productState_update(productState)
			self.productState_insert(productState)
	
	def productState_insert(self, productState):
		raise NotImplemented
	
	def productState_update(self, productState):
		raise NotImplemented
	
	def productState_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def productState_delete(self, productStates):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_create(self, productPropertyStates):
		productStates = forceObjectClassList(productPropertyStates, ProductPropertyState)
		for productPropertyState in productPropertyStates:
			logger.info("Creating productPropertyState '%s'" % productPropertyState)
			if self.productPropertyState_get(productId = productPropertyState.productId, hostId = productPropertyState.hostId, name = productPropertyState.name):
				logger.info("ProductPropertyState '%s' already exists, updating" % productPropertyState)
				self.productPropertyState_update(productPropertyState)
			self.productPropertyState_insert(productPropertyState)
	
	def productPropertyState_insert(self, productPropertyState):
		raise NotImplemented
	
	def productPropertyState_update(self, productPropertyState):
		raise NotImplemented
	
	def productPropertyState_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def productPropertyState_delete(self, productPropertyStates):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_create(self, groups):
		groups = forceObjectClassList(groups, Group)
		for group in groups:
			logger.info("Creating group '%s'" % group)
			if self.group_get(id = group.id):
				logger.info("Group '%s' already exists, updating" % group)
				self.group_update(group)
			self.group_insert(group)
	
	def group_insert(self, group):
		raise NotImplemented
	
	def group_update(self, group):
		raise NotImplemented
	
	def group_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def group_delete(self, groups):
		raise NotImplemented
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_create(self, objectToGroups):
		objectToGroups = forceObjectClassList(objectToGroups, ObjectToGroup)
		for objectToGroup in objectToGroups:
			logger.info("Creating objectToGroup '%s'" % objectToGroup)
			if self.objectToGroup_get(groupId = objectToGroup.groupId, objectId = objectToGroup.objectId):
				logger.info("ObjectToGroup '%s' already exists, updating" % objectToGroup)
				self.objectToGroup_update(objectToGroup)
			self.objectToGroup_insert(objectToGroup)
	
	def objectToGroup_insert(self, objectToGroup):
		raise NotImplemented
	
	def objectToGroup_update(self, objectToGroup):
		raise NotImplemented
	
	def objectToGroup_get(self, attributes=[], **filter):
		raise NotImplemented
	
	def objectToGroup_delete(self, objectToGroups):
		raise NotImplemented










