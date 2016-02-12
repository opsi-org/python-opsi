#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Algorithms to get a product order for an installation.

.. versionchanged:: 4.0.6.1

:author: Niko Wenselowski <n.wenselowski@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Rupert Röder <r.roeder@uib.de>
:license: GNU Affero General Public License version 3
"""

from collections import defaultdict

from OPSI.Logger import Logger
from OPSI.Object import ProductOnClient
from OPSI.Types import OpsiProductOrderingError, BackendUnaccomplishableError
from OPSI.Types import forceInt, forceBool

__version__ = '4.0.6.41'

logger = Logger()


class CircularProductDependencyError(BackendUnaccomplishableError):
	ExceptionShortDescription = "A circular dependency between products."


def addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo=None):
	logger.debug(u"checking dependencies for product '%s', action '%s'" % (productId, productOnClientByProductId[productId].actionRequest))
	addedInfo = addedInfo or {}

	poc = productOnClientByProductId[productId]
	if poc.actionRequest == 'none' or not productDependenciesByProductId.get(productId):
		return

	for dependency in productDependenciesByProductId[productId]:
		if dependency.productAction != poc.actionRequest:
			continue

		logger.debug(u"   need to check dependency to product '%s'" % (dependency.requiredProductId))
		if dependency.requiredAction:
			logger.debug(
				u"   product '%s' requires action '%s' of product '%s', "
				u"productVersion '%s', packageVersion '%s' on "
				u"action '%s'" % (
					productId, dependency.requiredAction,
					dependency.requiredProductId,
					dependency.requiredProductVersion,
					dependency.requiredPackageVersion, dependency.productAction
				)
			)
		elif dependency.requiredInstallationStatus:
			logger.debug(
				u"   product '%s' requires status '%s' of product '%s', "
				u"productVersion '%s', packageVersion '%s' on action '%s'" % (
					productId, dependency.requiredInstallationStatus,
					dependency.requiredProductId,
					dependency.requiredProductVersion,
					dependency.requiredPackageVersion, dependency.productAction
				)
			)

		requiredAction = dependency.requiredAction
		installationStatus = 'not_installed'
		actionRequest = 'none'
		if dependency.requiredProductId in productOnClientByProductId:
			installationStatus = productOnClientByProductId[dependency.requiredProductId].installationStatus
			actionRequest = productOnClientByProductId[dependency.requiredProductId].actionRequest
		logger.debug(u"addActionRequest: requiredAction %s " % requiredAction)
		if not requiredAction:
			if dependency.requiredInstallationStatus == installationStatus:
				logger.debug(u"   required installation status '%s' is fulfilled" % dependency.requiredInstallationStatus)
				continue
			elif dependency.requiredInstallationStatus == 'installed':
				requiredAction = 'setup'
			elif dependency.requiredInstallationStatus == 'not_installed':
				requiredAction = 'uninstall'

		# An action is required => check if possible
		logger.debug(u"   need to set action '%s' for product '%s' to fulfill dependency" % (requiredAction, dependency.requiredProductId))

		setActionRequestToNone = False
		if dependency.requiredProductId not in availableProductsByProductId:
			logger.error(u"   product '%s' defines dependency to product '%s', which is not avaliable on depot" % (productId, dependency.requiredProductId))
			setActionRequestToNone = True

		elif dependency.requiredProductVersion is not None and dependency.requiredProductVersion != availableProductsByProductId[dependency.requiredProductId].productVersion:
			logger.error(
				u"   product '%s' defines dependency to product '%s', "
				u"but product version '%s' is not available" % (
					productId, dependency.requiredProductId,
					dependency.requiredProductVersion
				)
			)
			setActionRequestToNone = True
		elif dependency.requiredPackageVersion is not None and dependency.requiredPackageVersion != availableProductsByProductId[dependency.requiredProductId].packageVersion:
			logger.error(
				u"   product '%s' defines dependency to product '%s', "
				u"but package version '%s' is not available" % (
					productId, dependency.requiredProductId,
					dependency.requiredPackageVersion
				)
			)
			setActionRequestToNone = True

		if setActionRequestToNone:
			logger.warning(u"   => setting action request for product '%s' to 'none'!" % productId)
			productOnClientByProductId[productId].actionRequest = 'none'
			continue

		if actionRequest == requiredAction:
			logger.debug(u"   => required action '%s' is already set" % requiredAction)
			continue
		elif actionRequest not in (None, 'none'):
			logger.error(
				u"   => cannot fulfill dependency of product '%s' to "
				u"product '%s': action '%s' needed but action '%s' "
				u"already set" % (
					productId, dependency.requiredProductId,
					requiredAction, actionRequest
				)
			)
			continue
		logger.info(u"   => adding action '%s' for product '%s'" % (requiredAction, dependency.requiredProductId))

		if dependency.requiredProductId in addedInfo:
			logger.warning(u"   => Product dependency loop detected, skipping")
			logger.debug(
				u"Circular dependency at {productId}. Processed product: {0}"
				u"addedInfo: {1}".format(
					productId,
					addedInfo,
					productId=dependency.requiredProductId
				)
			)
			continue

		if dependency.requiredProductId not in productOnClientByProductId:
			productOnClientByProductId[dependency.requiredProductId] = ProductOnClient(
				productId=dependency.requiredProductId,
				productType=availableProductsByProductId[dependency.requiredProductId].getType(),
				clientId=poc.clientId,
				installationStatus=None,
				actionRequest=u'none',
			)

		addedInfo[dependency.requiredProductId] = {
			'addedForProduct': productId,
			'requiredAction': requiredAction,
			'requirementType': dependency.requirementType
		}
		productOnClientByProductId[dependency.requiredProductId].setActionRequest(requiredAction)

		addActionRequest(productOnClientByProductId, dependency.requiredProductId, productDependenciesByProductId, availableProductsByProductId, addedInfo)


def addDependentProductOnClients(productOnClients, availableProducts, productDependencies):
	availableProductsByProductId = {}
	for availableProduct in availableProducts:
		availableProductsByProductId[availableProduct.id] = availableProduct

	productDependenciesByProductId = defaultdict(list)
	for productDependency in productDependencies:
		productDependenciesByProductId[productDependency.productId].append(productDependency)

	productOnClientsByClientIdAndProductId = defaultdict(dict)
	for productOnClient in productOnClients:
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient

	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Adding dependent productOnClients for client '%s'" % clientId)

		addedInfo = {}
		for productId in productOnClientByProductId.keys():
			addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo)

	return productOnClientByProductId.values()


class OrderRequirement(object):
	"""
	Represents a request for ordering of two elements with a notice
	if it is fulfilled.
	"""

	def __init__(self, prior, posterior, fulfilled=False):
		self.prior = forceInt(prior)
		self.posterior = forceInt(posterior)
		self.fulfilled = forceBool(fulfilled)

	def __unicode__(self):
		return (u"<OrderRequirement(prior={prio!r}, posterior={post!r}, "
				u"fulfilled={ful!r}>".format(
					prio=self.prior, post=self.posterior, ful=self.fulfilled))

	def __str__(self):
		return self.__unicode__().encode("ascii", "replace")

	def __repr__(self):
		return self.__str__()


class Requirements(object):
	# Comprises a list with ordering requirements and ordered lists of them

	def __init__(self):
		self.list = []
		self.orderByPrior = []
		self.orderByPosterior = []

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
		while (i < len(self.list) - 1) and not located:
			logger.debug2("Requirement.prior: %s, self.list[self.orderByPrior[i]].prior: %s " % (requirement.prior, self.list[self.orderByPrior[i]].prior))
			if requirement.prior > self.list[self.orderByPrior[i]].prior:
				i += 1
			else:
				located = True
				# we take the first place that fits to the ordering
				# shift all items by one place
				j = len(self.list) - 1
				while j > i:
					self.orderByPrior[j] = self.orderByPrior[j - 1]
					j -= 1
				# finally we map place i to the new element
				self.orderByPrior[i] = len(self.list) - 1

		if not located:
			# noInListOrderedByPriors
			# if i = len(self.list) - 1 nothing is moved
			self.orderByPrior[i] = len(self.list) - 1

		logger.debug2(u"Set orderByPrior[%d] = %d" % (i, (len(self.list) - 1)))

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
				while j > i:
					self.orderByPosterior[j] = self.orderByPosterior[j - 1]
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
			if candidate.posterior == posti:
				return j
			else:
				# There are no more possible occurrences of posterior
				return -1

	def indexOfFirstNotFulfilledRequirementOrderedByPrior(self):
		i = 0
		found = False
		while not found and (i < len(self.list)):
			if self.list[self.orderByPrior[i]].fulfilled:
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
		candidatesCausingProblemes = []

		while (j < len(self.list)) and not found:
			if not self.list[self.orderByPrior[j]].fulfilled and self.posteriorIndexOf(candidate) == -1:
				# If requ j still not fulfilled and candidate does not occur
				# as posterior among the not fulfilled
				# then we adopt candidate (i.e. the prior element of requ j in requ list ordered by priors)
				# as next element in our ordered sequence
				found = True
			else:
				if (self.posteriorIndexOf(candidate) > -1) and (lastcandidate != candidate):
					candidatesCausingProblemes.append(candidate)
					lastcandidate = candidate

				# Go on searching
				j += 1
				if j < len(self.list):
					candidate = self.list[self.orderByPrior[j]].prior

		if found:
			noInListOrderedByPriors = j
			return (candidate, noInListOrderedByPriors)

		errorMessage = u'Potentially conflicting requirements for: {0}'.format(candidatesCausingProblemes)
		logger.error(errorMessage)
		raise OpsiProductOrderingError(errorMessage, candidatesCausingProblemes)

	def getCount(self):
		return len(self.list)

	def getRequList(self):
		return self.list

	def getOrderByPrior(self):
		return self.orderByPrior

	def getOrderByPosteriors(self):
		return self.orderByPosterior


class OrderBuild(object):
	# Describes the building of an ordering

	def __init__(self, elementCount, requs, completing):
		self.ordering = []
		self.elementCount = elementCount
		self.completing = completing
		self.errorFound = False
		self.allFulfilled = False

		assert isinstance(requs, Requirements), "not Requirements"
		self.requs = requs
		self.indexIsAmongPosteriors = []
		j = 0
		while j < elementCount:
			self.indexIsAmongPosteriors.append(False)
			j += 1

		self.indexUsed = []
		j = 0
		while j < elementCount:
			self.indexUsed.append(False)
			j += 1

		self.usedCount = 0
		logger.debug(u"OrderBuild initialized")

	def proceed(self):
		result = True
		lastSortedCount = 0

		if self.usedCount >= self.elementCount:
			return result

		indexRequToFulfill = self.requs.indexOfFirstNotFulfilledRequirementOrderedByPrior()
		if indexRequToFulfill == -1:
			self.allFulfilled = True
			# Get the posteriors that did not occur as priors
			j = 0
			while j < self.elementCount:
				if self.indexIsAmongPosteriors[j] and not self.indexUsed[j]:
					self.ordering.append(j)
					self.indexUsed[j] = True
					self.usedCount = self.usedCount + 1
				j += 1
			lastSortedCount = self.usedCount

			if self.completing:
				# Take rest from list
				j = 0
				while j < self.elementCount:
					if not self.indexUsed[j]:
						self.ordering.append(j)
						self.indexUsed[j] = True
						self.usedCount = self.usedCount + 1
					j += 1

				# Move the sorted items to the end of the list
				if lastSortedCount > 0:
					newordering = []
					k = 0
					while k < self.elementCount:
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
			# At indexRequToFulfill we found a not fulfilled requirement,
			# lets try to fulfill a requirement
			# look only at not fulfilled reqirements
			# Find the first one, in ordering by priors, with the
			# property that it does not occur as posterior
			# take it as newEntry for the ordered list
			# Automatically any requirement is fulfilled where newEntry
			# is the prior; do the markings

			(newEntry, requNoInListOrderedByPriors) = self.requs.firstPriorNotOccurringAsPosterior(indexRequToFulfill)

			if newEntry == -1:
				result = False
			else:
				self.ordering.append(newEntry)
				self.usedCount = self.usedCount + 1
				# Mark all requirements with candidate in prior position
				# as fulfilled and collect the posteriors
				k = requNoInListOrderedByPriors
				orderByPrior = self.requs.getOrderByPrior()
				requK = self.requs.getRequList()[orderByPrior[k]]
				while (k < self.requs.getCount()) and (newEntry == requK.prior):
					requK.fulfilled = True
					self.indexIsAmongPosteriors[requK.posterior] = True
					k += 1
					if k < self.requs.getCount():
						requK = self.requs.getRequList()[orderByPrior[k]]
				self.indexUsed[newEntry] = True

			logger.debug(u"proceed newEntry %s " % newEntry)

		logger.debug(u"proceed result %s " % result)
		return result

	def getOrdering(self):
		return self.ordering


def generateProductOnClientSequence(productOnClients, sortedList):
	productOnClientsByClientIdAndProductId = defaultdict(dict)
	for productOnClient in productOnClients:
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient

	productOnClients = []
	for productOnClientsByProductId in productOnClientsByClientIdAndProductId.values():
		sequence = 0
		for productId in sortedList:
			if productId in productOnClientsByProductId:
				productOnClientsByProductId[productId].actionSequence = sequence
				productOnClients.append(productOnClientsByProductId[productId])
				del productOnClientsByProductId[productId]
				sequence += 1

		if sortedList:
			logger.debug(u"handle remaining if existing  ")
			for productId in productOnClientsByProductId.keys():
				productOnClientsByProductId[productId].actionSequence = sequence
				productOnClients.append(productOnClientsByProductId[productId])
				sequence += 1

	return productOnClients


def generateProductSequence_algorithm1(availableProducts, productDependencies):
	logger.notice(u"Generating product sequence with algorithm 1.")

	# Build priority classes and indices
	logger.debug(u"*********running algorithm1")
	logger.debug(u"availableProducts %s " % availableProducts)

	productIds = []
	productIndex = {}

	priorityClasses = defaultdict(list)

	productById = {}
	for product in availableProducts:
		productIds.append(product.id)
		productById[product.id] = product
		productIndex[product.id] = len(productIds) - 1

		prio = str(0)
		if product.priority:
			prio = str(product.priority)

		priorityClasses[prio] .append(product.id)

	logger.debug(u"productById %s " % productById)
	logger.debug(u"productIndex %s " % productIndex)
	logger.debug(u"priorityClasses %s " % priorityClasses)

	# Requirements are list of pairs
	# (installproduct_prior, installrproduct_posterior)
	# We treat only setup requirements
	setupRequirements = []

	for dependency in productDependencies:
		if dependency.productAction != u"setup":
			continue
		if dependency.requiredInstallationStatus != u"installed" and dependency.requiredAction != u"setup":
			continue
		if dependency.requirementType == u"before":
			setupRequirements.append((dependency.requiredProductId, dependency.productId))
		elif dependency.requirementType == u"after":
			setupRequirements.append((dependency.productId, dependency.requiredProductId))

	# requirements are list of pairs (index_prior, index_posterior)
	requirements = []

	# TODO: the following code may be a duplicate. Refactor?
	for (prod1, prod2) in setupRequirements:
		logger.debug(u"product1: {0}".format(prod1))
		logger.debug(u"product2: {0}".format(prod2))
		if prod1 not in productById:
			logger.warning(u"Product %s is requested but not available" % prod1)
			continue

		prio1 = productById[prod1].priority
		if not prio1:
			prio1 = 0

		if prod2 not in productById:
			logger.warning(u"Product %s is requested but not available" % prod2)
			continue

		prio2 = productById[prod2].priority
		if not prio2:
			prio2 = 0

		requirements.append([productIndex[prod1], productIndex[prod2]])

	logger.debug(u"requirements %s " % requirements)

	sortedList = []
	requs = requirements
	logger.debug(u"requs %s " % requs)

	try:
		requObjects = Requirements()
		for item in requs:
			requObj = OrderRequirement(item[0], item[1], False)
			logger.debug(u"requObj %s " % requObj)
			requObjects.add(requObj)

		ob = OrderBuild(len(availableProducts), requObjects, False)
		try:
			for _ in availableProducts:
				ob.proceed()
				logger.debug(u"ordering {0!r}".format(ob.getOrdering()))
		except OpsiProductOrderingError as error:
			logger.warning(u"algo1 catched OpsiProductOrderingError: {0}".format(error))
			for i, product in enumerate(availableProducts):
				logger.warning(u" product {0} {1}".format(i, product.getId()))

			raise OpsiProductOrderingError(
				u'Potentially conflicting requirements for: {0}'.format(
					', '.join([availableProducts[index].id for index in error.problematicRequirements])
				)
			)

		ordering = ob.getOrdering()
		logger.debug(u"completed ordering '%s' " % ordering)

		for idx in ordering:
			sortedList.append(productIds[idx])

		logger.debug(u"sortedList algo1 '%s' " % sortedList)
	except OpsiProductOrderingError as error:
		logger.warning(u"algo1 outer catched OpsiProductOrderingError: {0}".format(error))
		raise error

	logger.debug(u"+++++++++show sorted list %s " % sortedList)

	mixedSortedList = []
	shrinkingSortedList = [element for element in sortedList]

	prioClassStart = 100

	while shrinkingSortedList:
		prioClassHead = -100
		productHeading = None
		for productId in shrinkingSortedList:
			logger.debug(u"product %s " % productId)
			prioClass = productById[productId].priority
			if prioClass >= prioClassHead:
				prioClassHead = prioClass
				productHeading = productId

			logger.debug(u"product %s has priority class %s, prioClassHead now  %s " % (productId, prioClass, prioClassHead))

		# get all products with priority class <= prioClassHead
		prioList = range(0, prioClassStart - prioClassHead)
		for p in prioList:
			q = prioClassStart - p
			qs = str(q)
			if qs in priorityClasses:
				for productId in priorityClasses[qs]:
					logger.debug(u"append to mixed list %s " % productId)
					if productId not in mixedSortedList:
						mixedSortedList.append(productId)
		logger.debug(u"mixed list %s " % mixedSortedList)
		logger.debug(u"sorted list was %s " % shrinkingSortedList)
		qs = str(prioClassHead)
		logger.debug(u"mix to this the elements of prio class  %s, i.e. %s " % (qs, priorityClasses[qs]))
		for productId in priorityClasses[qs]:
			if productId not in shrinkingSortedList:
				mixedSortedList.append(productId)
		logger.debug(u"mixed list, added elements not in sorted list %s " % mixedSortedList)
		logger.debug(u"add elements from sorted list up to productHeading %s " % productHeading)

		while shrinkingSortedList:
			productId = shrinkingSortedList.pop(0)
			logger.debug(u"add element %s  from %s " % (productId, shrinkingSortedList))
			mixedSortedList.append(productId)

			if productId == productHeading:
				break

		logger.debug(u"+++++++++++mixed list with elements of sorted List %s " % mixedSortedList)

		prioClassStart = prioClassHead - 1
		logger.debug(u"new prioClassStart %s " % prioClassStart)

	logger.debug(u"++++++++")
	logger.debug(u"++  sortedList %s " % sortedList)
	logger.debug(u"++ mixedSortedList %s " % mixedSortedList)

	return mixedSortedList


def generateProductOnClientSequence_algorithm1(productOnClients, availableProducts, productDependencies):
	logger.notice(u"Generating productOnClient sequence with algorithm 1.")
	sortedProductList = generateProductSequence_algorithm2(availableProducts, productDependencies)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients


def generateProductSequence_algorithm2(availableProducts, productDependencies):
	logger.notice(u"Generating product sequence with algorithm 2.")

	# Build priority classes and indices
	logger.debug(u"*********running algorithm2")
	logger.debug(u"availableProducts %s " % availableProducts)

	productIds = []
	priorityClasses = defaultdict(list)
	productIndexInClass = {}
	productById = {}
	for product in availableProducts:
		productIds.append(product.id)
		productById[product.id] = product
		prio = str(0)
		if product.priority:
			prio = str(product.priority)

		priorityClasses[prio].append(product.id)
		productIndexInClass[product.id] = len(priorityClasses[prio]) - 1

	logger.debug(u"productIndexInClass %s " % productIndexInClass)
	logger.debug(u"priorityClasses %s " % priorityClasses)

	# Requirements are list of pairs (install_prior, install_posterior)
	# We treat only setup requirements
	setupRequirements = []

	for dependency in productDependencies:
		if dependency.productAction != u"setup":
			continue
		if dependency.requiredInstallationStatus != u"installed" and dependency.requiredAction != u"setup":
			continue
		if dependency.requirementType == u"before":
			setupRequirements.append((dependency.requiredProductId, dependency.productId))
		elif dependency.requirementType == u"after":
			setupRequirements.append((dependency.productId, dependency.requiredProductId))

	requirementsByClasses = defaultdict(list)

	for (prod1, prod2) in setupRequirements:
		logger.debug(u"First product: {0}".format(prod1))
		if prod1 not in productById:
			logger.warning(u"Product %s is requested but not available" % prod1)
			continue

		logger.debug(u"Second product: {0}".format(prod2))
		if prod2 not in productById:
			logger.warning(u"Product %s is requested but not available" % prod2)
			continue

		prio1 = productById[prod1].priority or 0
		prio2 = productById[prod2].priority or 0

		logger.debug(u"Priority {0}: {1}".format(prod1, prio1))
		logger.debug(u"Priority {0}: {1}".format(prod2, prio2))
		if prio1 > prio2:
			logger.debug(u"The ordering is guaranteed by priority handling")
		elif prio1 < prio2:
			logger.warning(u"Dependency declaration between %s and %s contradicts priority declaration, will be ignored" % (prod1, prod2))
		else:
			prioclasskey = str(prio1)
			requirementsByClasses[prioclasskey].append([productIndexInClass[prod1], productIndexInClass[prod2]])

	prioRange = list(reversed(range(-100, 101)))

	foundClasses = []
	orderingsByClasses = {}
	sortedList = []
	try:
		for p in prioRange:
			prioclasskey = str(p)
			if prioclasskey not in priorityClasses:
				continue
			foundClasses.append(prioclasskey)
			prioclass = priorityClasses[prioclasskey]

			if prioclasskey in requirementsByClasses:
				requs = requirementsByClasses[prioclasskey]
				requObjects = Requirements()
				for item in requs:
					requObjects.add(OrderRequirement(item[0], item[1], False))

				ob = OrderBuild(len(prioclass), requObjects, True)
				try:
					for _ in prioclass:
						ob.proceed()
				except OpsiProductOrderingError as error:
					logger.warning(u"algo2 catched OpsiProductOrderingError: {0}".format(error))
					for i, prio in enumerate(prioclass):
						logger.warning(u" product {0} {1}".format(i, prio))

					raise OpsiProductOrderingError(
						u"Potentially conflicting requirements for: {0}".format(
							', '.join([prioclass[index] for index in error.problematicRequirements])
						)
					)

				orderingsByClasses[prioclasskey] = ob.getOrdering()
				logger.debug(u"prioclasskey, ordering '%s' , '%s'" % (prioclasskey, ob.getOrdering()))

		for prioclasskey in foundClasses:
			prioclass = priorityClasses[prioclasskey]
			logger.debug(u"prioclasskey has prioclass %s, %s " % (prioclasskey, prioclass))
			if prioclasskey in orderingsByClasses:
				ordering = orderingsByClasses[prioclasskey]

				logger.debug(u"prioclasskey in found classes, ordering '%s',  '%s'" % (prioclasskey, ob.getOrdering()))

				for idx in ordering:
					sortedList.append(prioclass[idx])
			else:
				for element in prioclass:
					sortedList.append(element)

		logger.debug(u"sortedList algo2  '%s' " % sortedList)
	except OpsiProductOrderingError as error:
		logger.warning(u"algo2 outer catched OpsiProductOrderingError: {0}".format(error))
		raise error

	return sortedList


def generateProductOnClientSequence_algorithm2(productOnClients, availableProducts, productDependencies):
	logger.notice(u"Generating productOnClient sequence with algorithm 2.")
	sortedProductList = generateProductSequence_algorithm2(availableProducts, productDependencies)
	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients


def _generateProductOnClientSequence_algorithm3(productOnClients, availableProducts, productDependencies):
	"""
	Generate a product on client sequence for installation.

	This is the *old* variant and only available for historic reasons.
	"""
	logger.notice(u"Generating productOnClient sequence with algorithm 3.")

	logger.debug(u"*********  running algorithm3")
	productDependenciesByProductId = defaultdict(list)
	for productDependency in productDependencies:
		productDependenciesByProductId[productDependency.productId].append(productDependency)

	productOnClientsByClientIdAndProductId = defaultdict(dict)
	for productOnClient in productOnClients:
		productOnClientsByClientIdAndProductId[productOnClient.clientId][productOnClient.productId] = productOnClient

	logger.debug(u"Sorting available products by priority")
	priorityToProductIds = defaultdict(list)
	availableProductsByProductId = {}
	for availableProduct in availableProducts:
		# add id to collection
		availableProductsByProductId[availableProduct.id] = availableProduct
		# set id as value for priorityToProductIds [priority]
		priorityToProductIds[availableProduct.priority].append(availableProduct.id)

	priorities = reversed(sorted(priorityToProductIds.keys()))

	productSequence = []
	for priority in priorities:
		productSequence.extend(priorityToProductIds[priority])

	logger.debug2(u"Sequence of available products after priority sorting:")
	for i, product in enumerate(productSequence):
		logger.debug2(u"   [{0}] {1}".format(i, product))

	sortedProductOnClients = []

	for (clientId, productOnClientByProductId) in productOnClientsByClientIdAndProductId.items():
		logger.debug(u"Sorting available products by dependency for client '%s'" % clientId)
		sequence = [productId for productId in productSequence
					if productId in productOnClientByProductId]

		run = 0
		sequenceChanged = True
		while sequenceChanged:
			if run > 5:
				raise BackendUnaccomplishableError(u"Cannot resolve sequence for products %s after %d runs" % (productOnClientByProductId.keys(), run))
			run += 1
			sequenceChanged = False
			for productId in productOnClientByProductId.keys():
				if productOnClientByProductId[productId].actionRequest == 'none' or not productDependenciesByProductId.get(productId):
					continue

				requiredProductId = None
				requirementType = None
				for dependency in productDependenciesByProductId[productId]:
					if not productOnClientByProductId.get(dependency.requiredProductId):
						continue
					if dependency.productAction != productOnClientByProductId[dependency.requiredProductId].actionRequest:
						continue

					requiredProductId = dependency.requiredProductId
					requirementType = dependency.requirementType

					if requirementType not in ('before', 'after'):
						continue

					ppos = sequence.index(productId)
					dpos = sequence.index(requiredProductId)
					if requirementType == 'before' and ppos < dpos:
						logger.info("%s requires %s before, moving product '%s' in sequence one before '%s'." % (productId, requiredProductId, requiredProductId, productId))
						sequence.remove(requiredProductId)
						sequence.insert(ppos, requiredProductId)
						sequenceChanged = True
					elif requirementType == 'after' and dpos < ppos:
						logger.info("%s requires %s after, moving product '%s' in sequence one before '%s'." % (productId, requiredProductId, productId, requiredProductId))
						sequence.remove(productId)
						sequence.insert(dpos, productId)
						sequenceChanged = True
					else:
						logger.debug("%s requires %s %s => no sequence change required." % (productId, requiredProductId, requirementType))

		logger.debug2(u"Sequence of available products after dependency sorting (client %s):" % clientId)
		for i, productId in enumerate(sequence):
			logger.debug2(u"   [{0}] {1}".format(i, productId))
			productOnClient = productOnClientByProductId[productId]
			productOnClient.setActionSequence(i + 1)
			sortedProductOnClients.append(productOnClient)

	return sortedProductOnClients
