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

def_echo = \
u'''
def echo(string):
	return string
'''

def_addActionRequest = \
u'''
def addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo = {}):
	logger.debug(u"checking dependencies for product '%s', action '%s'" % (productId, productOnClientByProductId[productId].actionRequest))
	
	poc = productOnClientByProductId[productId]
	if (poc.actionRequest == 'none') or not productDependenciesByProductId.get(productId):
		return
	
	for dependency in productDependenciesByProductId[productId]:
		if (dependency.productAction != poc.actionRequest):
			continue
		
		logger.debug(u"   need to check dependency to product '%s'" % (dependency.requiredProductId))
		if dependency.requiredAction:
			logger.debug(u"   product '%s' requires action '%s' of product '%s', productVersion '%s', packageVersion '%s' on action '%s'" \
						% (productId, dependency.requiredAction, dependency.requiredProductId, dependency.requiredProductVersion,
						   dependency.requiredPackageVersion, dependency.productAction))
		elif dependency.requiredInstallationStatus:
			logger.debug(u"   product '%s' requires status '%s' of product '%s', productVersion '%s', packageVersion '%s' on action '%s'" \
						% (productId, dependency.requiredInstallationStatus, dependency.requiredProductId, dependency.requiredProductVersion,
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
			# return
			continue
		
		if   (actionRequest == requiredAction):
			logger.debug(u"   => required action '%s' is already set" % requiredAction)
			continue
		elif actionRequest not in (None, 'none'):
			logger.error(u"   => cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
						% (productId, dependency.requiredProductId, requiredAction, actionRequest))
			continue
			#raise BackendUnaccomplishableError(u"Cannot fulfill dependency of product '%s' to product '%s': action '%s' needed but action '%s' already set" \
			#		% (productId, dependency.requiredProductId, requiredAction, productOnClientsByProductId[dependency.requiredProductId].actionRequest))
		logger.info(u"   => adding action '%s' for product '%s'" % (requiredAction, dependency.requiredProductId))
		
		if addedInfo.has_key(dependency.requiredProductId):
			logger.warning(u"   => Product dependency loop detected, skipping")
			continue
		
		if not productOnClientByProductId.has_key(dependency.requiredProductId):
			productOnClientByProductId[dependency.requiredProductId] = ProductOnClient(
				productId          = dependency.requiredProductId,
				productType        = availableProductsByProductId[dependency.requiredProductId].getType(),
				clientId           = poc.clientId,
				installationStatus = None,
				actionRequest      = u'none',
			)
		addedInfo[dependency.requiredProductId] = {
			'addedForProduct': productId,
			'requiredAction':  requiredAction,
			'requirementType': dependency.requirementType
		}
		productOnClientByProductId[dependency.requiredProductId].setActionRequest(requiredAction)
		
		addActionRequest(productOnClientByProductId, dependency.requiredProductId, productDependenciesByProductId, availableProductsByProductId, addedInfo)
'''

def_addDependentProductOnClients = \
u'''
def addDependentProductOnClients(productOnClients, availableProducts, productDependencies):
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
'''

def_generateProductOnClientSequence = \
u'''
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
		# add id to collection 
		availableProductsByProductId[availableProduct.id] = availableProduct
		# if necessary initialize priorityToProductIds [priority]
		if not priorityToProductIds.has_key(availableProduct.priority):
			priorityToProductIds[availableProduct.priority] = []
		# set id as value for priorityToProductIds [priority]
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
	
	sortedProductOnClients = []
	
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
				logger.debug("Requirement type is 'before', moving product '%s' up in sequence." % requiredProductId)
				#if (run == 2):
				#	raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
				#					% (productId, requiredProductId))
				sequence.remove(requiredProductId)
				sequence.insert(ppos, requiredProductId)
			elif (requirementType == 'after') and (dpos < ppos):
				logger.debug("Requirement type is 'after', moving product '%s' down in sequence." % requiredProductId)
				#if (run == 2):
				#	raise BackendUnaccomplishableError(u"Cannot resolve sequence for products '%s', '%s'" \
				#					% (productId, requiredProductId))
				sequence.remove(requiredProductId)
				sequence.insert(ppos+1, requiredProductId)
			
		logger.debug(u"Sequence of available products after dependency sorting (client %s):" % clientId)
		for i in range(len(sequence)):
			logger.debug(u"   [%2.0f] %s" % (i, sequence[i]))
			productOnClient = productOnClientByProductId[sequence[i]]
			productOnClient.setActionSequence(i+1)
			sortedProductOnClients.append(productOnClient)
	return sortedProductOnClients
'''

exec(def_echo)
exec(def_addActionRequest)
exec(def_addDependentProductOnClients)
exec(def_generateProductOnClientSequence)

if (__name__ == "__main__"):
	logger.setConsoleLevel(LOG_DEBUG)
	logger.setConsoleColor(True)
	
	opsiAgent = LocalbootProduct(
		id                 = 'opsi-agent',
		name               = u'opsi client agent',
		productVersion     = '4.0',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 95,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	ultravnc = LocalbootProduct(
		id                 = 'ultravnc',
		name               = u'Ult@VNC',
		productVersion     = '1.0.8.2',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 90,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	firefox = LocalbootProduct(
		id                 = 'firefox',
		name               = u'Mozilla Firefox',
		productVersion     = '3.6',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = "update.ins",
		alwaysScript       = None,
		onceScript         = None,
		priority           = -70,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	flashplayer = LocalbootProduct(
		id                 = 'flashplayer',
		name               = u'Adobe Flashplayer',
		productVersion     = '10.0.45.2',
		packageVersion     = '2',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = -20,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	javavm = LocalbootProduct(
		id                 = 'javavm',
		name               = u'Sun Java',
		productVersion     = '1.6.20',
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	
	
	
	flashplayerDependency1 = ProductDependency(
		productId                  = flashplayer.id,
		productVersion             = flashplayer.productVersion,
		packageVersion             = flashplayer.packageVersion,
		productAction              = 'setup',
		requiredProductId          = firefox.id,
		requiredProductVersion     = firefox.productVersion,
		requiredPackageVersion     = firefox.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	javavmDependency1 = ProductDependency(
		productId                  = javavm.id,
		productVersion             = javavm.productVersion,
		packageVersion             = javavm.packageVersion,
		productAction              = 'setup',
		requiredProductId          = firefox.id,
		requiredProductVersion     = firefox.productVersion,
		requiredPackageVersion     = firefox.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	
	
	
	productOnClient1 = ProductOnClient(
		productId          = flashplayer.getId(),
		productType        = flashplayer.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = flashplayer.getProductVersion(),
		packageVersion     = flashplayer.getPackageVersion(),
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient2 = ProductOnClient(
		productId          = opsiAgent.getId(),
		productType        = opsiAgent.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient3 = ProductOnClient(
		productId          = javavm.getId(),
		productType        = javavm.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient4 = ProductOnClient(
		productId          = ultravnc.getId(),
		productType        = ultravnc.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	
	productOnClients = addDependentProductOnClients(
		[ productOnClient1, productOnClient2, productOnClient3, productOnClient4 ],
		[ opsiAgent, ultravnc, firefox, flashplayer, javavm ],
		[ flashplayerDependency1, javavmDependency1 ])
	
	for productOnClient in productOnClients:
		print productOnClient
	
	assert len(productOnClients) == 5
	
	productOnClients = generateProductOnClientSequence(
		productOnClients,
		[ opsiAgent, ultravnc, firefox, flashplayer, javavm ],
		[ flashplayerDependency1, javavmDependency1 ])
	for productOnClient in productOnClients:
		print "[%d] %s" % (productOnClient.getActionSequence(), productOnClient)
		
	productOnClients = addDependentProductOnClients(
		[ productOnClient1, productOnClient2, productOnClient3, productOnClient4 ],
		[ opsiAgent, ultravnc, firefox, flashplayer, javavm ],
		[ flashplayerDependency1, javavmDependency1 ])
	
	for productOnClient in productOnClients:
		print productOnClient
	




