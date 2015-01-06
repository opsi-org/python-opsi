#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - SharedAlgorithm   =
   = = = = = = = = = = = = = = = = = = = = = = =

   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org

   Copyright (C) 2010-2014 uib GmbH

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
   @author: Jan Schneider <j.schneider@uib.de>, Rupert Röder <r.roeder@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

# OPSI imports
from OPSI.Logger import *
from OPSI.Object import *
from OPSI.Types import OpsiProductOrderingError, BackendUnaccomplishableError
from OPSI.Types import forceInt, forceBool

# Get logger instance
logger = Logger()
TESTTHIS=True
def_debugprint=\
u'''
def debugprint(s):
	if TESTTHIS:
		print(s)
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
		logger.debug(u"addActionRequest: requiredAction %s " % requiredAction)
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
			logger.error(u"   product '%s' defines dependency to product '%s', which is not avaliable on depot" \
								% (productId, dependency.requiredProductId))
			setActionRequestToNone = True

		elif (not dependency.requiredProductVersion is None and dependency.requiredProductVersion != availableProductsByProductId[dependency.requiredProductId].productVersion):
			logger.error(u"   product '%s' defines dependency to product '%s', but product version '%s' is not available" \
								% (productId, dependency.requiredProductId, dependency.requiredProductVersion))
			setActionRequestToNone = True
		elif (not dependency.requiredPackageVersion is None and dependency.requiredPackageVersion != availableProductsByProductId[dependency.requiredProductId].packageVersion):
			logger.error(u"   product '%s' defines dependency to product '%s', but package version '%s' is not available" \
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
		#debugprint (u"%s " % productOnClient)
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient
		#debugprint (u"%s " % 	productOnClientsByClientIdAndProductId)

	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Adding dependent productOnClients for client '%s'" % clientId)

		addedInfo = {}
		for productId in productOnClientByProductId.keys():
			addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo)
	return productOnClientByProductId.values()
'''

class_OrderRequirement = \
u'''
class OrderRequirement:
	# Represents a request for ordering of two elements with a notice if it is fulfilled

	def __init__(self, prior, posterior, fulfilled=False):
		self.prior     = forceInt(prior)
		self.posterior = forceInt(posterior)
		self.fulfilled = forceBool(fulfilled)

	def __unicode__(self):
		return u"<OrderRequirement prior '%s', posterior '%s', fulfilled '%s'>" % (self.prior, self.posterior, self.fulfilled)

	def __str__(self):
		return self.__unicode__().encode("ascii", "replace")

	def __repr__(self):
		return self.__str__()
'''

class_Requirements = \
u'''
class Requirements:
	# Comprises a list with ordering requirements and ordered lists of them

	def __init__(self, allItemsCount):
		self.list = []
		self.orderByPrior=[]
		self.orderByPosterior=[]

	def add(self, requirement):
		assert isinstance(requirement, OrderRequirement), "not an OrderRequirement"
		self.list.append(requirement)
		# Extend the other lists by dummy valuesnoInListOrderedByPriors
		self.orderByPrior.append(-1)
		self.orderByPosterior.append(-1)
		logger.debug2(u"Length of list: %d" % len(self.list))
		logger.debug2(u"Length of orderByPrior: %d" % len(self.orderByPrior))

		# Continue building the transform map of list indices
		# such that the transformed list is ordered by its prior values
		# therefore:
		#  Determine first the place of the added item
		#  in the ordered sequence i -> list[orderByPrior[i]]
		#  then fix orderByPrior such that it gets this place
		i = 0
		located = False
		while (i < len(self.list)-1) and not located:
			logger.debug2("Requirement.prior: %s, self.list[self.orderByPrior[i]].prior: %s " % (requirement.prior, self.list[self.orderByPrior[i]].prior))
			if (requirement.prior > self.list[self.orderByPrior[i]].prior):
				i += 1
			else:
				located = True
				# we take the first place that fits to the ordering
				# shift all items by one place
				j = len(self.list) - 1
				while (j > i):
					self.orderByPrior[j] = self.orderByPrior[j-1]
					j -= 1
				# finally we map place i to the new element
				self.orderByPrior[i] = len(self.list) - 1

		if not located:
			# noInListOrderedByPriors
			# if i = len(self.list) - 1 nothing is moved
			self.orderByPrior[i] = len(self.list) - 1

		logger.debug2(u"Set orderByPrior[%d] = %d" % (i, (len(self.list) - 1) ))

		# The analogous procedure to get a transformation
		# i -> orderByPosterior[i] such that the sequence
		# i ->  self.list[orderByPosterior[i]]
		# is ordered by the posterior values

		i = 0
		located = False
		while (i < len(self.list) - 1) and not located:
			logger.debug2("Requirement.posterior %s, self.list[self.orderByPosterior[i]].posterior) %s " % (requirement.posterior, self.list[self.orderByPosterior[i]].posterior))
			if requirement.posterior > self.list[self.orderByPosterior[i]].posterior:
				i += 1
			else:
				located = True
				# We take the first place that fits to the ordering
				# shift all items by one place
				j = len(self.list) - 1
				while (j > i):
					self.orderByPosterior[j] = self.orderByPosterior[j-1]
					j -= 1
				# Finally we map place i to the new element
				self.orderByPosterior[i] = len(self.list) - 1

		if not located:
			# If i = len(self.list) - 1 nothing is moved
			self.orderByPosterior[i] = len(self.list) - 1


	def posteriorIndexOf(self, posti):
		# Searches first occurrence of posti as posterior value in the posterior-ordered sequence of requirements

		j = 0
		searching = True
		while (j < len(self.list)) and searching:
			candidate = self.list[self.orderByPosterior[j]]
			if candidate.fulfilled or (candidate.posterior < posti):
				j += 1
			else:
				searching = False

		if searching:
			# All candidates were less than the comparevalue or were not to be regarded any more
			return -1
		else:
			# Candidate is not fulfilled and has posterior value >= posti
			if (candidate.posterior == posti):
				return j
			else:
				# There are no more possible occurrences of posterior
				return -1

	def indexOfFirstNotFulfilledRequirementOrderedByPrior(self):
		i = 0
		found = False
		while not found and (i < len(self.list)):
			if (self.list[self.orderByPrior[i]].fulfilled):
				i = i + 1
			else:
				found = True
		if not found:
			return -1
		else:
			return i

	def firstPriorNotOccurringAsPosterior(self, startI):
		j = startI
		found = False
		candidate = self.list[self.orderByPrior[startI]].prior
		lastcandidate = -1
		errorS0 = u'Potentially conflicting requirements for:'

		while (j < len(self.list)) and not found:
			if not self.list[self.orderByPrior[j]].fulfilled and (self.posteriorIndexOf(candidate) == -1):
				# If requ j still not fulfilled and candidate does not occur
				# as posterior among the not fulfilled
				# then we adopt candidate (i.e. the prior element of requ j in requ list ordered by priors)
				# as next element in our ordered sequence
				found = True
			else:
				if (self.posteriorIndexOf(candidate) > -1) and ( lastcandidate != candidate ):
					errorS0 = u"%s %s" % (errorS0, candidate)
					lastcandidate = candidate
				# Go on searching
				j += 1
				if (j < len(self.list)):
					candidate = self.list[self.orderByPrior[j]].prior
		if found:
			noInListOrderedByPriors = j
			return (candidate, noInListOrderedByPriors)

		logger.error(errorS0 + u'  (raise error)')
		raise OpsiProductOrderingError(errorS0)


	def getCount(self):
		return len(self.list)

	def getRequList(self):
		return self.list

	def getOrderByPrior(self):
		return self.orderByPrior

	def getOrderByPosteriors(self):
		return self.orderByPosteriors
'''

class_OrderBuild = \
u'''
class OrderBuild:
	# Describes the building of an ordering

	def __init__(self,elementCount, requs, completing):
		self.ordering = []
		self.elementCount = elementCount
		self.completing = completing
		self.errorFound = False
		self.allFulfilled = False
		#logger.debug(u"requs is Requirements:  %s is really %s " %(requs, Requirements))
		assert isinstance(requs, Requirements), "not Requirements"
		self.requs = requs
		self.indexIsAmongPosteriors = []
		j = 0
		while (j < elementCount):
			self.indexIsAmongPosteriors.append(False)
			j += 1
		self.indexUsed = []
		j = 0
		while (j < elementCount):
			self.indexUsed.append(False)
			j += 1
		self.usedCount = 0
		logger.debug(u"OrderBuild initialized")

	def proceed(self):
		result = True
		lastSortedCount = 0
		#logger.debug(u"proceed usedCount, elementCount %s, %s " % (self.usedCount, self.elementCount))
		if (self.usedCount >= self.elementCount):
			return result

		indexRequToFulfill = self.requs.indexOfFirstNotFulfilledRequirementOrderedByPrior()
		#logger.debug(u"proceed indexRequToFulfill %s " % indexRequToFulfill)
		if (indexRequToFulfill == -1):
			self.allFulfilled = True
			# Get the posteriors that did not occur as priors
			j = 0
			while (j < self.elementCount):
				if self.indexIsAmongPosteriors[j] and not self.indexUsed[j]:
					self.ordering.append(j)
					self.indexUsed[j] = True
					self.usedCount = self.usedCount + 1
				j += 1
			lastSortedCount = self.usedCount

			if self.completing:
				# Take rest from list
				j = 0
				while (j < self.elementCount):
					if not self.indexUsed[j]:
						self.ordering.append(j)
						self.indexUsed[j] = True
						self.usedCount = self.usedCount + 1
					j += 1

				# Move the sorted items to the end of the list
				if (lastSortedCount > 0):
					newordering = []
					k = 0
					while (k < self.elementCount):
						newordering.append(k)
						k += 1

					# Rearrange not sorted elements
					for k in range(self.elementCount - lastSortedCount):
						newordering[k] = self.ordering[lastSortedCount + k]

					# Sorted elements
					for k in range(lastSortedCount):
						newordering[self.elementCount - lastSortedCount + k] = self.ordering[k]

					# Put back
					self.ordering = newordering
		else:
			# At indexRequToFulfill we found a not fulfilled requirement, lets try to fulfill a requirement
			# look only at not fulfilled reqirements
			# Find the first one, in ordering by priors, with the property that it does not occur as posterior
			# take it as newEntry for the ordered list
			# Automatically any requirement is fulfilled where newEntry is the prior; do the markings



			(newEntry, requNoInListOrderedByPriors) = self.requs.firstPriorNotOccurringAsPosterior(indexRequToFulfill)

			#logger.debug(u"proceed newEntry %s " % newEntry)

			if (newEntry == -1):
				result = False
			else:
				self.ordering.append(newEntry)
				#logger.debug(u"proceed appended newEntry %s " % newEntry)
				#self.ordering[self.usedCount] = newEntry
				self.usedCount = self.usedCount + 1
				# Mark all requirements with candidate in prior position as fulfilled and collect the posteriors
				k = requNoInListOrderedByPriors
				orderByPrior = self.requs.getOrderByPrior()
				requK = self.requs.getRequList()[orderByPrior[k]]
				while (k < self.requs.getCount()) and (newEntry == requK.prior):
					#logger.debug(u"proceed k %s " % k)
					requK.fulfilled = True
					#logger.debug(u"proceed requK %s " % requK)
					#logger.debug(u"proceed  indexIsAmongPosteriors %s " % self.indexIsAmongPosteriors)
					self.indexIsAmongPosteriors[ requK.posterior ] = True
					k += 1
					#logger.debug(u"proceed k %s " % k)
					if (k < self.requs.getCount()):
						requK = self.requs.getRequList()[orderByPrior[k]]
				self.indexUsed[newEntry] = True

			logger.debug(u"proceed newEntry %s " % newEntry)

		logger.debug(u"proceed result %s " % result)
		return result

	def getOrdering(self):
		return self.ordering
'''

def_generateProductOnClientSequence=\
'''
def generateProductOnClientSequence(productOnClients, sortedList):
	productOnClientsByClientIdAndProductId = {}
	for productOnClient in productOnClients:
		if not productOnClientsByClientIdAndProductId.has_key(productOnClient.clientId):
			productOnClientsByClientIdAndProductId[productOnClient.clientId] = {}
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient

	productOnClients = []
	for (clientId, productOnClientsByProductId) in productOnClientsByClientIdAndProductId.items():
		sequence = 0
		#logger.debug(u"sortedList %s " % sortedList)
		for productId in sortedList:
			#logger.debug(u"handle product %s for client %s  " %(productId, clientId))
			if productOnClientsByProductId.has_key(productId):
				productOnClientsByProductId[productId].actionSequence = sequence
				productOnClients.append(productOnClientsByProductId[productId])
				del productOnClientsByProductId[productId]
				sequence += 1
		#logger.debug(u"sortedList %s " % sortedList)
		if sortedList:
			logger.debug(u"handle remaining if existing  " )
			for productId in productOnClientsByProductId.keys():
				#logger.debug(u"handle product %s for client %s  " %(productId, clientId) )
				productOnClientsByProductId[productId].actionSequence = sequence
				productOnClients.append(productOnClientsByProductId[productId])
				sequence += 1
	return productOnClients
'''

def_generateProductSequence_algorithm1 = \
'''
def generateProductSequence_algorithm1(availableProducts, productDependencies):
	# Build priority classes and indices
	logger.debug(u"*********running algorithm1")
	debugprint("******* running algorithm1 ***")
	logger.debug(u"availableProducts %s " % availableProducts )

	productIds = []
	productIndex = {}

	priorityClasses = {}

	productById = {}
	for product in availableProducts:
		productIds.append(product.id)
		productById[product.id] = product
		productIndex[product.id] = len(productIds)-1

		prio = str(0)
		if product.priority:
			prio = str(product.priority)
		if not priorityClasses.has_key(prio):
			priorityClasses[prio] = []
		priorityClasses[prio] .append(product.id)


	logger.debug(u"productById %s " % productById)
	logger.debug(u"productIndex %s " % productIndex)
	logger.debug(u"priorityClasses %s " % priorityClasses)

	# Requirements are list of pairs (installproduct_prior, installrproduct_posterior)
	# We treat only setup requirements
	setupRequirements = []

	#requirements are list of pairs (index_prior, index_posterior)
	requirements = []

	for dependency in productDependencies:
		if (dependency.productAction != u"setup"):
			continue
		if (dependency.requiredInstallationStatus != u"installed") and (dependency.requiredAction != u"setup"):
			continue
		if (dependency.requirementType == u"before"):
			setupRequirements.append([ dependency.requiredProductId, dependency.productId ])
		elif (dependency.requirementType == u"after"):
			setupRequirements.append([ dependency.productId, dependency.requiredProductId ])


	for requ in setupRequirements:
		prod1 = requ[0]
		prod2 = requ[1]

		logger.debug(u"requ %s" % requ)
		if not productById.has_key(prod1):
			logger.warning(u"Product %s is requested but not available" %  prod1)
			continue
		prio1 = productById[prod1].priority
		if not prio1:
			prio1 = 0


		if not productById.has_key(prod2):
			logger.warning(u"Product %s is requested but not available" %  prod2)
			continue
		prio2 = productById[prod2].priority
		if not prio2:
			prio2 = 0


		requirements.append([productIndex[prod1],productIndex[prod2]])

	logger.debug(u"requirements %s " % requirements)

	prioRange = []
	for r in range(201):
		prioRange.append(100 - r)

	foundClasses = []
	sortedList = []
	try:
		requs = requirements

		logger.debug(u"requs %s " % requs)

		requObjects = []

		requObjects = Requirements(len(requirements))
		for item in requs:
			requObj = OrderRequirement(item[0], item[1], False)
			logger.debug(u"requObj %s " % requObj)
			requObjects.add(requObj)

		#logger.debug(u"requObjects %s " % requObjects)

		ob = OrderBuild(len(availableProducts), requObjects, False)
		try:
			for k in range(len(availableProducts)):
				ob.proceed()
				logger.debug(u"ordering '%s' " % ob.getOrdering())

		except OpsiProductOrderingError as e:
			logger.warning(u"algo1 catched OpsiProductOrderingError")
			for i in range(len(availableProducts)):
				logger.warning(u" product %s %s " % (i, availableProducts[i].getId()))
			raise e

		ordering = ob.getOrdering()
		logger.debug(u"completed ordering '%s' " % ordering)


		for idx in ordering:
			sortedList.append(productIds[idx])

		logger.debug(u"sortedList algo1 '%s' " % sortedList)

	except OpsiProductOrderingError as e:
		logger.warning(u"algo1 outer catched OpsiProductOrderingError")
		sortedList = []


	mixedSortedList = []
	logger.debug(u"+++++++++show sorted list %s " % sortedList)

	shrinkingSortedList = []
	for element in sortedList:
		shrinkingSortedList.append(element)

	prioClassStart = 100

	while len(shrinkingSortedList) > 0:

		prioClassHead = -100

		productHeading = None
		for productId in shrinkingSortedList:
			logger.debug(u"product %s " %productId)
			prioClass = productById[productId].priority
			if prioClass >= prioClassHead :
				prioClassHead = prioClass
				productHeading = productId

			logger.debug(u"product %s has priority class %s, prioClassHead now  %s " %(productId, prioClass, prioClassHead))


		#get all products with priority class <= prioClassHead

		prioList = range(0, prioClassStart - prioClassHead)
		for p in prioList:
			q = prioClassStart - p
			#logger.debug(u" prio %s " % (q))
			qs = str(q)
			if priorityClasses.has_key(qs):
				for productId in priorityClasses[qs]:
					logger.debug(u"append to mixed list %s " %productId)
					if productId not in mixedSortedList:
						mixedSortedList.append(productId)
		logger.debug(u"mixed list %s " % mixedSortedList)
		logger.debug(u"sorted list was %s " % shrinkingSortedList)
		qs = str(prioClassHead)
		logger.debug(u"mix to this the elements of prio class  %s, i.e. %s " % (qs, priorityClasses[qs] ))
		for productId in priorityClasses[qs]:
			if productId not in shrinkingSortedList:
				mixedSortedList.append(productId)
		logger.debug(u"mixed list, added elements not in sorted list %s " % mixedSortedList)
		logger.debug(u"add elements from sorted list up to productHeading %s " % productHeading)

		while len(shrinkingSortedList) >= 1:
			productId = shrinkingSortedList[0]
			logger.debug(u"add element %s  from %s "  %(productId, shrinkingSortedList) )
			mixedSortedList.append(productId)
			shrinkingSortedList.remove(productId)
			if productId == productHeading:
				break
		logger.debug(u"+++++++++++mixed list with elements of sorted List %s " % mixedSortedList)

		prioClassStart = prioClassHead-1
		logger.debug(u"new prioClassStart %s " % prioClassStart)



	logger.debug(u"++++++++")
	logger.debug(u"++  sortedList %s " % sortedList)
	logger.debug(u"++ mixedSortedList %s " % mixedSortedList)

	return mixedSortedList
'''


def_generateProductOnClientSequence_algorithm1 = \
'''
def generateProductOnClientSequence_algorithm1(productOnClients, availableProducts, productDependencies):
	sortedProductList = generateProductSequence_algorithm2(availableProducts, productDependencies)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients
'''


def_generateProductSequence_algorithm2 = \
'''
def generateProductSequence_algorithm2(availableProducts, productDependencies):
	# Build priority classes and indices

	logger.debug(u"*********running algorithm2")
	debugprint("******* running algorithm2")
	logger.debug(u"availableProducts %s " % availableProducts )

	productIds = []
	priorityClasses = {}
	productIndexInClass = {}
	productById = {}
	for product in availableProducts:
		productIds.append(product.id)
		productById[product.id] = product
		prio = str(0)
		if product.priority:
			prio = str(product.priority)
		if not priorityClasses.has_key(prio):
			priorityClasses[prio] = []
		priorityClasses[prio] .append(product.id)
		productIndexInClass[product.id] = len(priorityClasses[prio])-1

	logger.debug(u"productIndexInClass %s " % productIndexInClass)
	logger.debug(u"priorityClasses %s " % priorityClasses)

	# Requirements are list of pairs (install_prior, install_posterior)
	# We treat only setup requirements
	setupRequirements = []

	for dependency in productDependencies:
		if (dependency.productAction != u"setup"):
			continue
		if (dependency.requiredInstallationStatus != u"installed") and (dependency.requiredAction != u"setup"):
			continue
		if (dependency.requirementType == u"before"):
			setupRequirements.append([ dependency.requiredProductId, dependency.productId ])
		elif (dependency.requirementType == u"after"):
			setupRequirements.append([ dependency.productId, dependency.requiredProductId ])

	requirementsByClasses = {}

	for requ in setupRequirements:
		prod1 = requ[0]
		prod2 = requ[1]

		logger.debug(u"Product 1 %s" % prod1)
		if not productById.has_key(prod1):
			logger.warning(u"Product %s is requested but not available" %  prod1)
			continue
		prio1 = productById[prod1].priority
		if not prio1:
			prio1 = 0

		logger.debug(u"Product 2 %s" % prod2)
		if not productById.has_key(prod2):
			logger.warning(u"Product %s is requested but not available" %  prod2)
			continue
		prio2 = productById[prod2].priority
		if not prio2:
			prio2 = 0

		logger.debug(u"Priority product 1 %s" % prio1)
		logger.debug(u"Priority product 2 %s" % prio2)
		if (prio1 > prio2):
			logger.notice(u"The ordering is guaranteed by priority handling")
		elif (prio1 < prio2):
			logger.warning(u"Dependency declaration between %s and %s contradicts priority declaration, will be ignored" % (prod1, prod2))
		else:
			prioclasskey = str(prio1)
			if not requirementsByClasses.has_key(prioclasskey):
				requirementsByClasses[prioclasskey] = []
			requirementsByClasses[prioclasskey].append([productIndexInClass[prod1],productIndexInClass[prod2]])

	prioRange = []
	for r in range(201):
		prioRange.append(100 - r)

	foundClasses = []
	orderingsByClasses = {}
	sortedList = []
	try:
		for p in prioRange:
			prioclasskey = str(p)
			if not priorityClasses.has_key(prioclasskey):
				continue
			foundClasses.append(prioclasskey)
			prioclass = priorityClasses[prioclasskey]

			if requirementsByClasses.has_key(prioclasskey):
				requs = requirementsByClasses[prioclasskey]
				requObjects = Requirements(len(prioclass))
				for item in requs:
					requObjects.add(OrderRequirement(item[0], item[1], False))

				ob = OrderBuild(len(prioclass), requObjects, True)
				try:
					for k in range(len(prioclass)):
						ob.proceed()

				except OpsiProductOrderingError as e:
					logger.warning(u"algo2 catched OpsiProductOrderingError")
					for i in range(len(prioclass)):
						logger.warning(u" product %s %s " % (i, prioclass[i]))
					raise e

				orderingsByClasses[prioclasskey] = ob.getOrdering()
				logger.debug(u"prioclasskey, ordering '%s' , '%s'" % (prioclasskey,ob.getOrdering()))

		for prioclasskey in foundClasses:
			prioclass =  priorityClasses[prioclasskey]
			logger.debug(u"prioclasskey has prioclass %s, %s " % (prioclasskey, prioclass))
			if orderingsByClasses.has_key(prioclasskey):
				ordering = orderingsByClasses[prioclasskey]

				logger.debug(u"prioclasskey in found classes, ordering '%s',  '%s'" % (prioclasskey,ob.getOrdering()))


				for idx in ordering:
					sortedList.append(prioclass[idx])
			else:
				for element in prioclass:
					sortedList.append(element)

		logger.debug(u"sortedList algo2  '%s' " % sortedList)

	except OpsiProductOrderingError as e:
		logger.warning(u"algo2 outer catched OpsiProductOrderingError")
		sortedList = []

	return sortedList
'''

def_generateProductOnClientSequence_algorithm2 = \
'''
def generateProductOnClientSequence_algorithm2(productOnClients, availableProducts, productDependencies):
	sortedProductList = generateProductSequence_algorithm2(availableProducts, productDependencies)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients
'''

def_generateProductOnClientSequence_algorithm3 = \
u'''
def generateProductOnClientSequence_algorithm3(productOnClients, availableProducts, productDependencies):
	logger.debug(u"*********  running algorithm3")
	debugprint("******* running algorithm3")
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

	logger.debug2(u"Sequence of available products after priority sorting:")
	for i in range(len(productSequence)):
		logger.debug2(u"   [%2.0f] %s" % (i, productSequence[i]))

	sortedProductOnClients = []

	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Sorting available products by dependency for client '%s'" % clientId)
		sequence = []
		for productId in productSequence:
			if productId in productOnClientByProductId.keys():
				sequence.append(productId)

		run = 0
		sequenceChanged = True
		while sequenceChanged:
			if (run > 5):
				raise BackendUnaccomplishableError(u"Cannot resolve sequence for products %s after %d runs" \
					% (productOnClientByProductId.keys(), run))
			run += 1
			sequenceChanged = False
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

					if not requirementType in ('before', 'after'):
						continue

					ppos = sequence.index(productId)
					dpos = sequence.index(requiredProductId)
					if (requirementType == 'before') and (ppos < dpos):
						logger.info("%s requires %s before, moving product '%s' in sequence one before '%s'." % (productId, requiredProductId, requiredProductId, productId))
						sequence.remove(requiredProductId)
						sequence.insert(ppos, requiredProductId)
						sequenceChanged = True
					elif (requirementType == 'after') and (dpos < ppos):
						logger.info("%s requires %s after, moving product '%s' in sequence one before '%s'." % (productId, requiredProductId, productId, requiredProductId))
						sequence.remove(productId)
						sequence.insert(dpos, productId)
						sequenceChanged = True
					else:
						logger.debug("%s requires %s %s => no sequence change required." % (productId, requiredProductId, requirementType))
		logger.debug2(u"Sequence of available products after dependency sorting (client %s):" % clientId)
		for i in range(len(sequence)):
			logger.debug2(u"   [%2.0f] %s" % (i, sequence[i]))
			productOnClient = productOnClientByProductId[sequence[i]]
			productOnClient.setActionSequence(i+1)
			sortedProductOnClients.append(productOnClient)
	return sortedProductOnClients
'''




def_showState = \
'''
def showState(productOnClients, availableProducts, productDependencies, start=True):
	# show situation



	if not start:
		debugprint ("result:")

		debugprint("productOnClients:")
		if not productOnClients  or productOnClients == []:
			debugprint("no ordering")
		else:
			for productOnClient in productOnClients:
				#debugprint("[%d] %s" % (productOnClient.getActionSequence(), productOnClient))
				debugprint("%s" % (productOnClient))


	debugprint("---")
	if start:
		for product in availableProducts:
			debugprint("%s  priority: %s " % (product.id, product.priority))
		debugprint("---")
		for dependency in deps:
			debugprint("%s " % (dependency))
	debugprint("---")
'''

exec(def_debugprint)
exec(def_addActionRequest)
exec(def_addDependentProductOnClients)
exec(class_OrderRequirement)
exec(class_Requirements)
exec(class_OrderBuild)
exec(def_generateProductOnClientSequence)
exec(def_generateProductSequence_algorithm1)
exec(def_generateProductSequence_algorithm2)
exec(def_showState)
exec(def_generateProductOnClientSequence_algorithm1)
exec(def_generateProductOnClientSequence_algorithm2)
exec(def_generateProductOnClientSequence_algorithm3)



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
		priority           = 0,
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
		priority           = 0,
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
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)


	sysessential = LocalbootProduct(
		id                 = 'sysessential',
		name               = u'Sys Essential',
		productVersion     = '1.10.0',
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 55,
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

	jedit = LocalbootProduct(
		id                 = 'jedit',
		name               = u'jEdit',
		productVersion     = '5.1.0',
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

	jeditDependency1 = ProductDependency(
		productId                  = jedit.id,
		productVersion             = jedit.productVersion,
		packageVersion             = jedit.packageVersion,
		productAction              = 'setup',
		requiredProductId          = javavm.id,
		requiredProductVersion     = javavm.productVersion,
		requiredPackageVersion     = javavm.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)


	ultravncDependency1 = ProductDependency(
		productId                  = ultravnc.id,
		productVersion             = ultravnc.productVersion,
		packageVersion             = ultravnc.packageVersion,
		productAction              = 'setup',
		requiredProductId          = javavm.id,
		requiredProductVersion     = javavm.productVersion,
		requiredPackageVersion     = javavm.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)

	sysessentialDependency1 = ProductDependency(
		productId                  = sysessential.id,
		productVersion             =sysessential.productVersion,
		packageVersion             = sysessential.packageVersion,
		productAction              = 'setup',
		requiredProductId          = ultravnc.id,
		requiredProductVersion     = ultravnc.productVersion,
		requiredPackageVersion     = ultravnc.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	firefoxDependency1 = ProductDependency(
		productId                  = firefox.id,
		productVersion             =firefox.productVersion,
		packageVersion             = firefox.packageVersion,
		productAction              = 'setup',
		requiredProductId          = ultravnc.id,
		requiredProductVersion     = ultravnc.productVersion,
		requiredPackageVersion     = ultravnc.packageVersion,
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

	productOnClient5 = ProductOnClient(
		productId          = sysessential.getId(),
		productType        =sysessential .getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)

	productOnClient6 = ProductOnClient(
		productId          = javavm.getId(),
		productType        = javavm .getType(),
		clientId           = 'client2.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	debugprint("**********************************************************")
	debugprint("**********************************************************")

	debugprint("CASE: priority levels and dependency do not interfer")

	availProducts = [ opsiAgent, ultravnc, flashplayer, javavm, jedit, firefox,sysessential ]
	logger.debug(u"availProducts %s " % availProducts)
	deps = [ flashplayerDependency1, javavmDependency1, jeditDependency1, ultravncDependency1 ]
	logger.debug(u"deps %s " % deps)

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)


	assert len(productOnClients) == 6, "length not 6"




	debugprint("algorithm 1:")
	debugprint("========================")

	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm1(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")

	debugprint("algorithm 2:")
	debugprint("========================")



	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm2(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)


	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")

	debugprint("algorithm 3:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	productOnClients = generateProductOnClientSequence_algorithm3(productOnClients, availProducts, deps)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")




	debugprint("CASE: the sysessential dependency tries to move the product ultravnc to front in contradiction to priority ")

	deps.append(sysessentialDependency1)

	debugprint("algorithm 1:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm1(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")

	debugprint("algorithm 2:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)


	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm2(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)


	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")


	debugprint("algorithm 3:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	productOnClients = generateProductOnClientSequence_algorithm3(productOnClients, availProducts, deps)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")




	debugprint("CASE: circular dependency ultravnc depends on javavm, javavm on firefox and, now added, firefox on ultravnc  ")
	deps.remove(sysessentialDependency1)
	deps.append(firefoxDependency1)


	debugprint("algorithm 1:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm1(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")

	debugprint("algorithm 2:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	sortedProductList = generateProductSequence_algorithm2(availProducts, deps)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)


	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")


	debugprint("algorithm 3:")
	debugprint("========================")

	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	showState(productOnClients, availProducts, deps)

	productOnClients = addDependentProductOnClients(
		productOnClients,
		availProducts,
		deps)

	showState(productOnClients, availProducts, deps)

	productOnClients = generateProductOnClientSequence_algorithm3(productOnClients, availProducts, deps)

	showState(productOnClients, availProducts, deps, False)

	debugprint("**********************************************************")



