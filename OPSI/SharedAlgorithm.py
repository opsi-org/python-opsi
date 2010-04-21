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



def addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo = {}):
	logger.debug(u"checking dependencies for product '%s', action '%s'" % (productId, productOnClientByProductId[productId].actionRequest))
	
	poc = productOnClientByProductId[productId]
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
			logger.warning(u"   => setting action request for product '%s' to 'none'!" % productId)
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
		logger.debug(u"   => adding action '%s' for product '%s'" % (requiredAction, dependency.requiredProductId))
		
		if addedInfo.has_key(dependency.requiredProductId):
			logger.warning(u"   => Product dependency loop detected, skipping")
			continue
		
		if not productOnClientByProductId.has_key(dependency.requiredProductId):
			productOnClientByProductId[dependency.requiredProductId] = ProductOnClient(
				productId          = dependency.requiredProductId,
				productType        = availableProductsByProductId[dependency.requiredProductId].getType(),
				clientId           = poc.clientId,
				installationStatus = u'not_installed',
				actionRequest      = u'none',
			)
		addedInfo[dependency.requiredProductId] = {
			'addedForProduct': productId,
			'requiredAction':  requiredAction,
			'requirementType': dependency.requirementType
		}
		productOnClientByProductId[dependency.requiredProductId].setActionRequest(requiredAction)
		
		addActionRequest(productOnClientByProductId, dependency.requiredProductId, productDependenciesByProductId, availableProductsByProductId, addedInfo)

def addDependendProductOnClients(productOnClients, availableProducts, productDependencies):
	availableProductsByProductId = {}
	for availableProduct in availableProducts:
		availableProductsByProductId[availableProduct.id] = availableProduct
	
	productDependenciesByProductId = {}
	for productDependency in productDependencies:
		if not productDependenciesByProductId.has_key(productDependency.productId):
			productDependenciesByProductId[productDependency.productId] = []
		productDependenciesByProductId[productDependency.productId].append(productDependency)
	
	productOnClientsByClientIdAndProductId = {}
	for productOnClient in productOnClients:
		if not productOnClientsByClientIdAndProductId.has_key(productOnClient.clientId):
			productOnClientsByClientIdAndProductId[productOnClient.clientId] = {}
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient
	
	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Adding dependend productOnClients for client '%s'" % clientId)
		
		addedInfo = {}
		for productId in productOnClientByProductId.keys():
			addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo)
		
	return productOnClientByProductId.values()

def generateProductOnClientSequence(productOnClients, availableProducts, productDependencies):
	productDependenciesByProductId = {}
	for productDependency in productDependencies:
		if not productDependenciesByProductId.has_key(productDependency.productId):
			productDependenciesByProductId[productDependency.productId] = []
		productDependenciesByProductId[productDependency.productId].append(productDependency)
	
	productOnClientsByClientIdAndProductId = {}
	for productOnClient in productOnClients:
		if not productOnClientsByClientIdAndProductId.has_key(productOnClient.clientId):
			productOnClientsByClientIdAndProductId[productOnClient.clientId] = {}
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient
	
	logger.debug(u"Sorting available products by priority")
	priorityToProductIds = {}
	availableProductsByProductId = {}
	for availableProduct in availableProducts:
		availableProductsByProductId[availableProduct.id] = availableProduct
		if not priorityToProductIds.has_key(availableProduct.priority):
			priorityToProductIds[availableProduct.priority] = []
		priorityToProductIds[availableProduct.priority].append(availableProduct.id)
		
	priorities = priorityToProductIds.keys()
	priorities.sort()
	priorities.reverse()
	
	productSequence = []
	for priority in priorities:
		productSequence.extend(priorityToProductIds[priority])
	
	logger.debug(u"Sequence of available products after priority sorting:")
	for i in range(len(productSequence)):
		logger.debug(u"   [%2.0f] %s" % (i, productSequence[i]))
	
	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Sorting available products by dependency for client '%s'" % clientId)
		sequence = []
		for productId in productSequence:
			if productId in productOnClientByProductId.keys():
				sequence.append(productId)
		
		#for run in (1, 2):
		for productId in productOnClientByProductId.keys():
			if (productOnClientByProductId[productId].actionRequest == 'none') or not productDependenciesByProductId.get(productId):
				continue
			
			requiredProductId = None
			requirementType = None
			for dependency in productDependenciesByProductId[productId]:
				if not productOnClientByProductId.get(dependency.requiredProductId):
					continue
				if (dependency.productAction != productOnClientByProductId[dependency.requiredProductId].actionRequest):
					continue
				
				requiredProductId = dependency.requiredProductId
				requirementType = dependency.requirementType
				break
			
			if not requirementType in ('before', 'after'):
				continue
			
			ppos = sequence.index(productId)
			dpos = sequence.index(requiredProductId)
			if (requirementType == 'before') and (ppos < dpos):
				logger.debug("#################### Before")
				#if (run == 2):
				#	raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
				#					% (info['addedForProduct'], requiredProductId))
				sequence.remove(requiredProductId)
				sequence.insert(ppos, requiredProductId)
			elif (requirementType == 'after') and (dpos < ppos):
				logger.debug("#################### After")
				#if (run == 2):
				#	raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
				#					% (info['addedForProduct'], requiredProductId))
				sequence.remove(requiredProductId)
				sequence.insert(ppos+1, requiredProductId)
			
		logger.debug(u"Sequence of available products after dependency sorting (client %s):" % clientId)
		for i in range(len(sequence)):
			logger.debug(u"   [%2.0f] %s" % (i, sequence[i]))
	
if (__name__ == "__main__"):
	logger.setConsoleLevel(LOG_DEBUG)
		
	product2 = LocalbootProduct(
		id                 = 'product2',
		name               = u'Product 2',
		productVersion     = '2.0',
		packageVersion     = 'test',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = "update.ins",
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx']
	)
	
	product3 = LocalbootProduct(
		id                 = 'product3',
		name               = u'Product 3',
		productVersion     = 3,
		packageVersion     = 1,
		licenseRequired    = True,
		setupScript        = "setup.ins",
		uninstallScript    = None,
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 100,
		description        = "---",
		advice             = "---",
		windowsSoftwareIds = []
	)
	
	product4 = LocalbootProduct(
		id                 = 'product4',
		name               = u'Product 4',
		productVersion     = "3.0",
		packageVersion     = 24,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = "uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = "",
		advice             = "",
		windowsSoftwareIds = []
	)
	
	product6 = LocalbootProduct(
		id                 = 'product6',
		name               = u'Product 6',
		productVersion     = "1.0",
		packageVersion     = 1,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = "uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = "",
		advice             = "",
		windowsSoftwareIds = []
	)
	
	product7 = LocalbootProduct(
		id                 = 'product7',
		name               = u'Product 7',
		productVersion     = "1.0",
		packageVersion     = 1,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = "uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = "",
		advice             = "",
		windowsSoftwareIds = []
	)
	
	product9 = LocalbootProduct(
		id                 = 'product9',
		name               = u'Product 9',
		productVersion     = "1.0",
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = "uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		customScript       = "custom.ins",
		priority           = 0,
		description        = "",
		advice             = "",
		windowsSoftwareIds = []
	)
	
	productDependency1 = ProductDependency(
		productId                  = product3.id,
		productVersion             = product3.productVersion,
		packageVersion             = product3.packageVersion,
		productAction              = 'setup',
		requiredProductId          = product2.id,
		requiredProductVersion     = product2.productVersion,
		requiredPackageVersion     = product2.packageVersion,
		requiredAction             = 'setup',
		requiredInstallationStatus = None,
		requirementType            = 'before'
	)
	
	productDependency2 = ProductDependency(
		productId                  = product2.id,
		productVersion             = product2.productVersion,
		packageVersion             = product2.packageVersion,
		productAction              = 'setup',
		requiredProductId          = product4.id,
		requiredProductVersion     = None,
		requiredPackageVersion     = None,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'after'
	)
	
	productDependency3 = ProductDependency(
		productId                  = product6.id,
		productVersion             = product6.productVersion,
		packageVersion             = product6.packageVersion,
		productAction              = 'setup',
		requiredProductId          = product7.id,
		requiredProductVersion     = product7.productVersion,
		requiredPackageVersion     = product7.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'after'
	)
	
	productDependency4 = ProductDependency(
		productId                  = product7.id,
		productVersion             = product7.productVersion,
		packageVersion             = product7.packageVersion,
		productAction              = 'setup',
		requiredProductId          = product9.id,
		requiredProductVersion     = None,
		requiredPackageVersion     = None,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'after'
	)
	
	productOnClient1 = ProductOnClient(
		productId          = product3.getId(),
		productType        = product3.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = product3.getProductVersion(),
		packageVersion     = product3.getPackageVersion(),
		modificationTime   = '2009-07-01 12:00:00'
	)
	
	productOnClients = addDependendProductOnClients(
		[ productOnClient1 ],
		[ product2, product3, product4, product6, product7, product9 ],
		[ productDependency1, productDependency2, productDependency3, productDependency4 ])
	
	for productOnClient in productOnClients:
		print productOnClient
	
	assert len(productOnClients) == 3
	
	generateProductOnClientSequence(
		productOnClients,
		[ product2, product3, product4, product6, product7, product9 ],
		[ productDependency1, productDependency2, productDependency3, productDependency4 ])
	
	productOnClients = addDependendProductOnClients(
		[ productOnClient1 ],
		[ product2, product4, product6, product7, product9 ],
		[ productDependency1, productDependency2, productDependency3, productDependency4 ])
	
	for productOnClient in productOnClients:
		print productOnClient
	
	






























