#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - SharedAlgorithm   =
   = = = = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 uib GmbH
   
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

__version__ = '4.0'

# OPSI imports
from OPSI.Logger import *
from OPSI.Object import *

# Get logger instance
logger = Logger()



def addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId):
	logger.debug(u"checking dependencies for product '%s', action '%s'" % (productId, productOnClientByProductId[productId].actionRequest))
	
	poc = productOnClientByProductId[productId]
	if poc.
	if (poc.actionRequest == 'none') or not productDependenciesByProductId.get(productId):
		return
	
	for dependency in productDependenciesByProductId[productId]:
		if (dependency.productAction != poc.actionRequest):
			continue
		
		logger.debug(u"   need to check dependency to product '%s'" % (dependency.requiredProductId))
		logger.debug(u"   product '%s' requires product '%s', productVersion '%s', packageVersion '%s' on action '%s'" \
					% (productId, dependency.requiredProductId, dependency.requiredProductVersion,
					   dependency.requiredPackageVersion, dependency.productAction))
		
		requiredAction     = dependency.requiredAction
		installationStatus = 'not_installed'
		actionRequest      = 'none'
		if productOnClientByProductId.has_key(dependency.requiredProductId):
			installationStatus = productOnClientByProductId[dependency.requiredProductId].installationStatus
			actionRequest      = productOnClientByProductId[dependency.requiredProductId].actionRequest
		if not requiredAction:
			if   (dependency.requiredInstallationStatus == installationStatus):
				logger.debug(u"   required installation status '%s' is fulfilled" % dependency.requiredInstallationStatus)
				continue
			elif (dependency.requiredInstallationStatus == 'installed'):
				requiredAction = 'setup'
			elif (dependency.requiredInstallationStatus == 'not_installed'):
				requiredAction = 'uninstall'
		
		# An action is required => check if possible
		logger.debug(u"   need to set action '%s' for product '%s' to fulfill dependency" % (requiredAction, dependency.requiredProductId))
		
		setActionRequestToNone = False
		if not availableProductsByProductId.has_key(dependency.requiredProductId):
			logger.warning(u"   product '%s' defines dependency to product '%s', which is not avaliable" \
								% (productId, dependency.requiredProductId))
			setActionRequestToNone = True
		
		elif (not dependency.requiredProductVersion is None and dependency.requiredProductVersion != availableProductsByProductId[dependency.requiredProductId].productVersion):
			logger.warning(u"   product '%s' defines dependency to product '%s', but product version '%s' is not available" \
								% (productId, dependency.requiredProductId, dependency.requiredProductVersion))
			setActionRequestToNone = True
		elif (not dependency.requiredPackageVersion is None and dependency.requiredPackageVersion != availableProductsByProductId[dependency.requiredProductId].packageVersion):
			logger.warning(u"   product '%s' defines dependency to product '%s', but package version '%s' is not available" \
								% (productId, dependency.requiredProductId, dependency.requiredPackageVersion))
			setActionRequestToNone = True
		
		if setActionRequestToNone:
			logger.warning(u"   => setting action request for product '%s' on client '%s' to 'none'!" % (productId, clientId))
			productOnClientByProductId[productId].actionRequest = 'none'
			return
		
		if   (actionRequest == requiredAction):
			logger.debug(u"   => required action '%s' is already set" % requiredAction)
			continue
		elif (actionRequest != 'none'):
			logger.error(u"   => cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
						% (productId, dependency.requiredProductId, requiredAction, actionRequest))
			continue
			#raise BackendUnaccomplishableError(u"Cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
			#		% (productId, dependency.requiredProductId, requiredAction, productOnClientsByProductId[dependency.requiredProductId].actionRequest))
		logger.debug(u"   need to add action '%s' for product '%s'" % (requiredAction, dependency.requiredProductId))
		
		#if addedInfo.has_key(dependency.requiredProductId):
		#	logger.warning(u"   => Product dependency loop detected, skipping")
		#	continue
		
		if not productOnClientByProductId.has_key(dependency.requiredProductId):
			productOnClientByProductId[dependency.requiredProductId] = ProductOnClient(
				productId          = dependency.requiredProductId,
				productType        = availableProductsByProductId[dependency.requiredProductId].productType,
				clientId           = poc.clientId,
				installationStatus = u'not_installed',
				actionRequest      = u'none',
			)
		#addedInfo[dependency.requiredProductId] = {
		#	'addedForProduct': requiredAction,
		#	'requiredAction':  requiredAction,
		#	'requirementType': dependency.requirementType
		#}
		productOnClientByProductId[dependency.requiredProductId].setActionRequest(requiredAction)
		
		addActionRequest(productOnClientByProductId, dependency.requiredProductId, productDependenciesByProductId, availableProductsByProductId)
		

def addDependendProductOnClients(productOnClients, availableProducts, productDependencies):
	productOnClientsByClientIdAndProductId = {}
	productDependenciesByProductId = {}
	availableProductsByProductId = {}
	
	for availableProduct in availableProducts:
		availableProductsByProductId[availableProduct.id] = availableProduct
	
	for productDependency in productDependencies:
		if not productDependenciesByProductId.has_key(productDependency.productId):
			productDependenciesByProductId[productDependency.productId] = []
		productDependenciesByProductId[productDependency.productId].append(productDependency)
	
	for productOnClient in productOnClients:
		if not productOnClientsByClientIdAndProductId.has_key(productOnClient.clientId):
			productOnClientsByClientIdAndProductId[productOnClient.clientId] = {}
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient
	
	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Adding dependend productOnClients for client %s" % clientId)
		
		#addedInfo = {}
		for productId in productOnClientByProductId.keys():
			addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId)
		
	
	
	
	
	
	
	
	
	
	
	
	
