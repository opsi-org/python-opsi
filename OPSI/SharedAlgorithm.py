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

.. versionchanged:: 4.0.7.1

   Refactored algorithm 1.


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

logger = Logger()

BOTTOM = -100


class CircularProductDependencyError(BackendUnaccomplishableError):
	ExceptionShortDescription = "A circular dependency between products."


def addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo=None):
	logger.debug(u"Checking dependencies for product {0!r}, action {1!r}", productId, productOnClientByProductId[productId].actionRequest)
	addedInfo = addedInfo or {}

	poc = productOnClientByProductId[productId]
	if poc.actionRequest == 'none' or not productDependenciesByProductId.get(productId):
		return

	for dependency in productDependenciesByProductId[productId]:
		if dependency.productAction != poc.actionRequest:
			continue

		logger.debug(u"   need to check dependency to product {0!r}", dependency.requiredProductId)
		if dependency.requiredAction:
			logger.debug(
				u"   product {0!r} requires action {1!r} of product {2!r}, "
				u"productVersion {3!r}, packageVersion {4!r} on "
				u"action {5!r}",
				productId,
				dependency.requiredAction,
				dependency.requiredProductId,
				dependency.requiredProductVersion,
				dependency.requiredPackageVersion,
				dependency.productAction
			)
		elif dependency.requiredInstallationStatus:
			logger.debug(
				u"   product {0!r} requires status {1!r} of product {2!r}, "
				u"productVersion {3!r}, packageVersion {4!r} on action {5!r}",
				productId,
				dependency.requiredInstallationStatus,
				dependency.requiredProductId,
				dependency.requiredProductVersion,
				dependency.requiredPackageVersion,
				dependency.productAction
			)

		requiredAction = dependency.requiredAction
		installationStatus = 'not_installed'
		actionRequest = 'none'
		if dependency.requiredProductId in productOnClientByProductId:
			installationStatus = productOnClientByProductId[dependency.requiredProductId].installationStatus
			actionRequest = productOnClientByProductId[dependency.requiredProductId].actionRequest
		logger.debug(u"addActionRequest: requiredAction {0}", requiredAction)
		if not requiredAction:
			if dependency.requiredInstallationStatus == installationStatus:
				logger.debug(u"   required installation status {0!r} is fulfilled", dependency.requiredInstallationStatus)
				continue
			elif dependency.requiredInstallationStatus == 'installed':
				requiredAction = 'setup'
			elif dependency.requiredInstallationStatus == 'not_installed':
				requiredAction = 'uninstall'

		# An action is required => check if possible
		logger.debug(u"   need to set action {0!r} for product {1!r} to fulfill dependency", requiredAction, dependency.requiredProductId)

		setActionRequestToNone = False
		if dependency.requiredProductId not in availableProductsByProductId:
			logger.info(u"   product {0!r} defines dependency to product {1!r}, which is not avaliable on depot", productId, dependency.requiredProductId)
			setActionRequestToNone = True

		elif dependency.requiredProductVersion is not None and dependency.requiredProductVersion != availableProductsByProductId[dependency.requiredProductId].productVersion:
			logger.info(
				u"   product {0!r} defines dependency to product {1!r}, "
				u"but product version {2!r} is not available",
				productId,
				dependency.requiredProductId,
				dependency.requiredProductVersion
			)
			setActionRequestToNone = True
		elif dependency.requiredPackageVersion is not None and dependency.requiredPackageVersion != availableProductsByProductId[dependency.requiredProductId].packageVersion:
			logger.info(
				u"   product {0!r} defines dependency to product {1!r}, "
				u"but package version {2!r} is not available",
				productId,
				dependency.requiredProductId,
				dependency.requiredPackageVersion
			)
			setActionRequestToNone = True

		if setActionRequestToNone:
			logger.notice(u"   => setting action request for product {0!r} to 'none'!", productId)
			productOnClientByProductId[productId].actionRequest = 'none'
			continue

		if actionRequest == requiredAction:
			logger.debug(u"   => required action {0!r} is already set", requiredAction)
			continue
		elif actionRequest not in (None, 'none'):
			logger.info(
				u"   => cannot fulfill dependency of product {0!r} to "
				u"product {1!r}: action {2!r} needed but action {3!r} "
				u"already set",
				productId,
				dependency.requiredProductId,
				requiredAction,
				actionRequest
			)
			continue
		logger.info(u"   => adding action {0!r} for product {1!r}", requiredAction, dependency.requiredProductId)

		if dependency.requiredProductId in addedInfo:
			logger.warning(u"   => Product dependency loop detected, skipping")
			logger.debug(
				u"Circular dependency at {2}. Processed product: {0}"
				u"addedInfo: {1}",
				productId,
				addedInfo,
				dependency.requiredProductId
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
		logger.debug(u"Adding dependent productOnClients for client {0!r}", clientId)

		addedInfo = {}
		for productId in productOnClientByProductId.keys():
			addActionRequest(productOnClientByProductId, productId, productDependenciesByProductId, availableProductsByProductId, addedInfo)

	return productOnClientByProductId.values()


class XClassifiedProduct(object):
	"""
	has String member id, int members priority, revisedPriority, and a member that is intendend to be a reference to a Product
	"""

	def __init__(self, product):
		self.id = product.id
		self.priority = product.priority  # handle this variable as final
		self.revisedPriority = product.priority  # start value which may be modified
		self.product = product  # keep pointer to the original standard product structure

	def __unicode__(self):
		return u'<{classname}(productId={0!r}, priority={1}, revisedPriority={2})>'.format(self.id, self.priority, self.revisedPriority, classname=self.__class__.__name__)

	def __str__(self):
		return self.__unicode__().encode("ascii", "replace")

	def __repr__(self):
		return self.__str__()


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
		logger.debug2(u"Length of list: {0}", len(self.list))
		logger.debug2(u"Length of orderByPrior: {0}", len(self.orderByPrior))

		# Continue building the transform map of list indices
		# such that the transformed list is ordered by its prior values
		# therefore:
		#  Determine first the place of the added item
		#  in the ordered sequence i -> list[orderByPrior[i]]
		#  then fix orderByPrior such that it gets this place
		i = 0
		located = False
		while (i < len(self.list) - 1) and not located:
			logger.debug2("Requirement.prior: {0}, self.list[self.orderByPrior[i]].prior: {1}", requirement.prior, self.list[self.orderByPrior[i]].prior)
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

		logger.debug2(u"Set orderByPrior[{0}] = {1}", i, (len(self.list) - 1))

		# The analogous procedure to get a transformation
		# i -> orderByPosterior[i] such that the sequence
		# i ->  self.list[orderByPosterior[i]]
		# is ordered by the posterior values

		i = 0
		located = False
		while (i < len(self.list) - 1) and not located:
			logger.debug2("Requirement.posterior {0}, self.list[self.orderByPosterior[i]].posterior) {1}", requirement.posterior, self.list[self.orderByPosterior[i]].posterior)
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

			logger.debug(u"proceed newEntry {0}", newEntry)

		logger.debug(u"proceed result {0}", result)
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


def generateProductOnClientSequenceX(productOnClients, sortedList):
	fProductId2ProductOnClients = {}
	for productOnClient in productOnClients:
		if productOnClient.productId not in fProductId2ProductOnClients:
			fProductId2ProductOnClients[productOnClient.productId] = []
		fProductId2ProductOnClients[productOnClient.productId].append(productOnClient)
		# the list should contain exactly one element, if applied to a list "productOnClients" from one depot

	result = []

	givenIds = fProductId2ProductOnClients.keys()

	if sortedList:
		for productId in sortedList:
			for prod in fProductId2ProductOnClients[productId].values():
				result.append(prod)
			givenIds.remove(productId)

	# add remainings ids
	for productId in givenIds:
		for prod in fProductId2ProductOnClients[productId].values():
			result.append(prod)

	return result


def getSetupRequirements(productDependencies):
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

	return setupRequirements


def generateProductSequence_algorithm1(availableProducts, productDependencies):
	logger.notice(u"Generating product sequence by algorithm 1.")
	setupRequirements = getSetupRequirements(productDependencies)

	return generateProductSequenceFromRequPairs_algorithm1(availableProducts, setupRequirements)


def modifySortingClassesForAlgorithm1(products, setupRequirements):
	# idea:
	# we reconstruct the priority chain
	# by pushing the products upwards into it when required by a dependency

	recursionNecessary = False

	fId2Prod = {}
	for prod in products:
		fId2Prod[prod.id] = prod
		logger.debug(u"prod  {0}", prod)

	fLevel2Prodlist = {}
	# state of priorityClasses
	for px in reversed(range(BOTTOM, 101)):
		fLevel2Prodlist[px] = []

	for prod in products:
		fLevel2Prodlist[prod.revisedPriority].append(prod)

	requsByPosterior = {}
	for requ in setupRequirements:
		if requ[1] not in requsByPosterior:
			requsByPosterior[requ[1]] = []

		requsByPosterior[requ[1]].append(requ)

	for px in range(BOTTOM, 101):
		logger.debug2(u"we are about to correct level {0}...", px)
		if not fLevel2Prodlist[px]:
			logger.debug2(u"no elements in this level")
			pass
		else:
			for posti in fLevel2Prodlist[px]:
				logger.debug2(u"posti {0}", posti)
				if posti.id in requsByPosterior:
					removeRequs = []
					for requ in requsByPosterior[posti.id]:
						if requ[0] not in fId2Prod:
							logger.notice(u"product {0!r} should be arranged before product {1!r} but is not available", requ[0], requ[1])
							removeRequs.append(requ)
						else:
							if fId2Prod[requ[0]].revisedPriority < px:
								logger.notice(
									u"product {0} must be pushed upwards from level {1} to level {2}, the level of {3}, to meet the requirement first {0}, later {4}",
									requ[0], fId2Prod[requ[0]].revisedPriority, px, posti.id, requ[1]
								)
								fId2Prod[requ[0]].revisedPriority = px
								recursionNecessary = True

					for requ in removeRequs:
						requsByPosterior[posti.id].remove(requ)

	return recursionNecessary


def generateProductSequenceFromRequPairs_algorithm1(availableProducts, setupRequirements):
	logger.debug(u"availableProducts {0}", availableProducts)

	xProducts = []
	for product in availableProducts:
		xProducts.append(XClassifiedProduct(product))

	requsByPosterior = {}
	for requ in setupRequirements:
		if requ[1] not in requsByPosterior:
			requsByPosterior[requ[1]] = []

		requsByPosterior[requ[1]].append(requ)

	# recursively modify the priority levels
	# we move prods upwards as long as there are movements necessary
	# the algorithm halts since the moves are only upwards and are bounded
	ready = False
	while not ready:
		ready = not modifySortingClassesForAlgorithm1(xProducts, setupRequirements)
		if ready:
			logger.debug(u"recursion finished")
		else:
			logger.debug(u"was modified, step to next recursion")

	# we map xProduct onto Product
	for product in xProducts:
		product.priority = product.revisedPriority

	return generateProductSequenceFromRequPairs_algorithm2(xProducts, setupRequirements)


def generateProductSequence_algorithm2(availableProducts, productDependencies):
	logger.notice(u"Generating product sequence by algorithm 2:")
	setupRequirements = getSetupRequirements(productDependencies)

	return generateProductSequenceFromRequPairs_algorithm2(availableProducts, setupRequirements)


def generateProductSequenceFromRequPairs_algorithm2(availableProducts, setupRequirements):
	# Build priority classes and indices
	logger.debug(u"availableProducts {0}", availableProducts)

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

	logger.debug(u"productIndexInClass {0}", productIndexInClass)
	logger.debug(u"priorityClasses {0}", priorityClasses)

	requirementsByClasses = defaultdict(list)

	for (prod1, prod2) in setupRequirements:
		logger.debug(u"First product: {0}", prod1)
		if prod1 not in productById:
			logger.info(u"Product {0} is requested but not available", prod1)
			continue

		logger.debug(u"Second product: {0}".format(prod2))
		if prod2 not in productById:
			logger.info(u"Product {0} is requested but not available", prod2)
			continue

		prio1 = productById[prod1].priority or 0
		prio2 = productById[prod2].priority or 0

		logger.debug(u"Priority {0}: {1}", prod1, prio1)
		logger.debug(u"Priority {0}: {1}", prod2, prio2)
		if prio1 > prio2:
			logger.debug(u"The ordering is guaranteed by priority handling")
		elif prio1 < prio2:
			logger.warning(u"Dependency declaration between {0} and {1} contradicts priority declaration, will be ignored", prod1, prod2)
		else:
			prioclasskey = str(prio1)
			requirementsByClasses[prioclasskey].append([productIndexInClass[prod1], productIndexInClass[prod2]])

	foundClasses = []
	orderingsByClasses = {}
	sortedList = []
	try:
		for priority in reversed(range(BOTTOM, 101)):
			prioclasskey = str(priority)
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
					logger.warning(u"algo2 caught OpsiProductOrderingError: {0}", error)
					for i, prio in enumerate(prioclass):
						logger.warning(u" product {0} {1}", i, prio)

					raise OpsiProductOrderingError(
						u"Potentially conflicting requirements for: {0}".format(
							', '.join([prioclass[index] for index in error.problematicRequirements])
						)
					)

				orderingsByClasses[prioclasskey] = ob.getOrdering()
				logger.debug(u"prioclasskey, ordering {0!r}, {1!r}", prioclasskey, ob.getOrdering())

		for prioclasskey in foundClasses:
			prioclass = priorityClasses[prioclasskey]
			logger.debug(u"prioclasskey has prioclass {0}, {1}", prioclasskey, prioclass)
			if prioclasskey in orderingsByClasses:
				ordering = orderingsByClasses[prioclasskey]

				logger.debug(u"prioclasskey in found classes, ordering {0!r}, {1!r}", prioclasskey, ob.getOrdering())

				for idx in ordering:
					sortedList.append(prioclass[idx])
			else:
				for element in prioclass:
					sortedList.append(element)

		logger.debug(u"sortedList algo2 {0!r}", sortedList)
	except OpsiProductOrderingError as error:
		logger.error(u"algo2 outer catched OpsiProductOrderingError: {0}", error)
		raise error

	return sortedList


def generateProductOnClientSequence_algorithm1(productOnClients, availableProducts, productDependencies):
	logger.notice(u"Generating productOnClient sequence with algorithm 1.")

	setupRequirements = getSetupRequirements(productDependencies)
	sortedProductList = generateProductSequenceFromRequPairs_algorithm1(availableProducts, setupRequirements)

	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients


def generateProductOnClientSequence_algorithm2(productOnClients, availableProducts, productDependencies):
	logger.notice(u"Generating productOnClient sequence with algorithm 2.")

	setupRequirements = getSetupRequirements(productDependencies)
	sortedProductList = generateProductSequenceFromRequPairs_algorithm2(availableProducts, setupRequirements)

	productOnClients = generateProductOnClientSequence(productOnClients, sortedProductList)
	return productOnClients
