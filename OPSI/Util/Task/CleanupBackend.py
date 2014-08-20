# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013 uib GmbH <info@uib.de>

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
opsi python library - Util - Task - Backend Cleanup

Functionality to clean up an OPSI Backend.

The aim of this module is to remove obsolete data from the backend to
ensure having clean data.

The everyday method for this job is :py:func:`cleanupBackend`.
For more specialised cleanup you should use the corresponding methods.

.. versionadded:: 4.0.4.2

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import unicode_literals

import re

import OPSI.Util.Task.ConfigureBackend as backendUtil
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.MySQL import MySQL
from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceUnicodeLower
from OPSI.Util.File.Opsi import BackendDispatchConfigFile

LOGGER = Logger()


def cleanupBackend(backend=None):
	"""
	Clean up data from your backends.

	This method uses different cleanup methods to ensure that no
	obsolete data is present in your backend.

	:param backend: the backend to check. If ``None`` this will create a \
BackendManager from default paths.
	:type backend: OPSI.Backend.Backend
	"""
	def usesMysqlBackend():
		LOGGER.notice(u"Parsing dispatch.conf")
		bdc = BackendDispatchConfigFile(u'/etc/opsi/backendManager/dispatch.conf')
		dispatchConfig = bdc.parse()
		for entry in dispatchConfig:
			(regex, backends) = entry
			if not re.search(regex, 'backend_createBase'):
				continue

			if 'mysql' in backends:
				return True

		return False

	if backend is None:
		backend = BackendManager(
			dispatchConfigFile=u'/etc/opsi/backendManager/dispatch.conf',
			backendConfigDir=u'/etc/opsi/backends',
			extensionConfigDir=u'/etc/opsi/backendManager/extend.d',
			depotbackend=False
		)

		try:
			if usesMysqlBackend():
				LOGGER.notice(u"Mysql-backend detected. Trying to cleanup mysql-backend first")
				# ToDo: backendConfigFile should be as dynamic as possible
				# What if we have 2 mysql backends set up?
				cleanUpMySQL()
		except Exception as error:
			LOGGER.warning(error)

	LOGGER.notice(u"Cleaning up groups")
	cleanUpGroups(backend)

	LOGGER.notice(u"Cleaning up products")
	cleanUpProducts(backend)

	LOGGER.debug('Getting current depots...')
	depotIds = [depot.id for depot in backend.host_getObjects(type=["OpsiConfigserver", "OpsiDepotserver"])]
	LOGGER.debug('Depots are: {0}'.format(depotIds))

	LOGGER.debug('Getting current products...')
	productIdents = []
	for product in backend.product_getObjects():
		if not product.getIdent(returnType='unicode') in productIdents:
			productIdents.append(product.getIdent(returnType='unicode'))
	LOGGER.debug('Product idents are: {0}'.format(productIdents))

	LOGGER.notice(u"Cleaning up product on depots")
	cleanUpProductOnDepots(backend, depotIds, productIdents)

	LOGGER.notice(u"Cleaning up product on clients")
	cleanUpProductOnClients(backend)

	LOGGER.notice(u"Cleaning up product properties")
	productPropertyIdents = []
	deleteProductProperties = []
	productPropertiesToCleanup = {}
	for productProperty in backend.productProperty_getObjects():
		productIdent = u"%s;%s;%s" % (productProperty.productId, productProperty.productVersion, productProperty.packageVersion)
		if not productProperty.editable and productProperty.possibleValues:
			productPropertyIdent = u"%s;%s" % (productIdent, productProperty.propertyId)
			productPropertiesToCleanup[productPropertyIdent] = productProperty
		if not productIdent in productIdents:
			LOGGER.info(u"Marking productProperty %s of non existent product '%s' for deletion" % (productProperty, productIdent))
			deleteProductProperties.append(productProperty)
		else:
			productPropertyIdent = u'%s;%s' % (productProperty.productId, productProperty.propertyId)
			if not productPropertyIdent in productPropertyIdents:
				productPropertyIdents.append(productPropertyIdent)
	if deleteProductProperties:
		backend.productProperty_deleteObjects(deleteProductProperties)

	LOGGER.notice(u"Cleaning up product property states")
	deleteProductPropertyStates = []
	for productPropertyState in backend.productPropertyState_getObjects():
		productPropertyIdent = u'%s;%s' % (productPropertyState.productId, productPropertyState.propertyId)
		if not productPropertyIdent in productPropertyIdents:
			LOGGER.info(u"Marking productPropertyState %s of non existent productProperty '%s' for deletion" % (productPropertyState, productPropertyIdent))
			deleteProductPropertyStates.append(productPropertyState)
	if deleteProductPropertyStates:
		backend.productPropertyState_deleteObjects(deleteProductPropertyStates)

	for depot in backend.host_getObjects(type='OpsiDepotserver'):
		objectIds = [depot.id]
		for clientToDepot in backend.configState_getClientToDepotserver(depotIds=depot.id):
			if not clientToDepot['clientId'] in objectIds:
				objectIds.append(clientToDepot['clientId'])
		productOnDepotIdents = {}
		for productOnDepot in backend.productOnDepot_getObjects(depotId=depot.id):
			productIdent = u"%s;%s;%s" % (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion)
			productOnDepotIdents[productOnDepot.productId] = productIdent
		if not productOnDepotIdents:
			continue
		deleteProductPropertyStates = []
		updateProductPropertyStates = []
		for productPropertyState in backend.productPropertyState_getObjects(
				objectId=objectIds,
				productId=productOnDepotIdents.keys(),
				propertyId=[]):
			productIdent = productOnDepotIdents.get(productPropertyState.productId)
			if not productIdent:
				continue
			productPropertyIdent = u"%s;%s" % (productIdent, productPropertyState.propertyId)
			productProperty = productPropertiesToCleanup.get(productPropertyIdent)
			if not productProperty:
				continue
			changed = False
			newValues = []
			removeValues = []
			changedValues = []
			for value in productPropertyState.values:
				if value in productProperty.possibleValues:
					newValues.append(value)
					continue
				if productProperty.getType() == 'BoolProductProperty' and forceBool(value) in productProperty.possibleValues:
					newValues.append(forceBool(value))
					changedValues.append(value)
					changed = True
					continue
				if productProperty.getType() == 'UnicodeProductProperty':
					newValue = None
					for possibleValue in productProperty.possibleValues:
						if forceUnicodeLower(possibleValue) == forceUnicodeLower(value):
							newValue = possibleValue
							break
					if newValue:
						newValues.append(newValue)
						changedValues.append(value)
						changed = True
						continue
				removeValues.append(value)
				changed = True
			if changed:
				if not newValues:
					LOGGER.info(u"Marking productPropertyState %s for deletion: no value in possible values (%s)" % (productPropertyState, removeValues))
					deleteProductPropertyStates.append(productPropertyState)
				else:
					productPropertyState.setValues(newValues)
					LOGGER.info(u"Marking productPropertyState %s for update: values not in possible values: %s, values corrected: %s" % (productPropertyState, removeValues, changedValues))
					updateProductPropertyStates.append(productPropertyState)
		if deleteProductPropertyStates:
			backend.productPropertyState_deleteObjects(deleteProductPropertyStates)
		if updateProductPropertyStates:
			backend.productPropertyState_updateObjects(updateProductPropertyStates)

	LOGGER.notice(u"Cleaning up config states")
	cleanUpConfigStates(backend)

	LOGGER.notice(u"Cleaning up audit softwares")
	cleanUpAuditSoftwares(backend)

	LOGGER.notice(u"Cleaning up audit software on clients")
	cleanUpAuditSoftwareOnClients(backend)


def cleanUpMySQL(backendConfigFile=u'/etc/opsi/backends/mysql.conf'):
	"""
	Clean up an MySQL backend.

	**This does not work with any backend other than MySQL.**

	:param backendConfigFile: The configuration file of the currently \
used MySQL backend.
	:type backendConfigFile: str
	"""
	config = backendUtil.getBackendConfiguration(backendConfigFile)
	LOGGER.info(u"Current mysql backend config: %s" % config)

	LOGGER.notice(
		"Connection to database '{database}' on '{address}' as user "
		"'{username}'".format(**config)
	)
	mysql = MySQL(**config)

	LOGGER.notice("Cleaning up defaultValues in productProperties")
	deleteIds = []
	found = []
	for res in mysql.getSet("SELECT * FROM PRODUCT_PROPERTY_VALUE WHERE isDefault like '1'"):
		ident = ';'.join([res['propertyId'], res['productId'],
			res['productVersion'], res['productVersion'], res['value']]
		)
		if ident not in found:
			found.append(ident)
		else:
			if res['value'] in ('0', '1') and res['product_property_id'] not in deleteIds:
				deleteIds.append(res['product_property_id'])

	for ID in deleteIds:
		LOGGER.notice("Deleting PropertyValue id: {0}".format(ID))
		mysql.execute("DELETE FROM `PRODUCT_PROPERTY_VALUE` where "
			"`product_property_id` = '{0}'".format(ID)
		)


def cleanUpGroups(backend):
	"""
	This checks if a group has a parent set that does not exist and
	removes non-existing parents.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	updatedGroups = []
	groupIds = []
	groups = backend.group_getObjects(type='HostGroup')
	for group in groups:
		groupIds.append(group.id)
	for group in groups:
		if group.getParentGroupId() and group.getParentGroupId() not in groupIds:
			LOGGER.info(
				"Removing parent group id '{parentGroupId}' from group "
				"'{groupId}' because parent group does not exist".format(
					parentGroupId=group.parentGroupId,
					groupId=group.id
				)
			)
			group.parentGroupId = None
			updatedGroups.append(group)

	if updatedGroups:
		backend.group_createObjects(updatedGroups)


def cleanUpProducts(backend):
	"""
	This will delete any unreferenced product from the backend.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	productIds = []
	productIdents = []

	for productOnDepot in backend.productOnDepot_getObjects():
		productIdent = ";".join([productOnDepot.productId,
			productOnDepot.productVersion, productOnDepot.packageVersion]
		)
		if not productIdent in productIdents:
			productIdents.append(productIdent)
	deleteProducts = []
	for product in backend.product_getObjects():
		if not product.getIdent(returnType='unicode') in productIdents:
			LOGGER.info("Marking unreferenced product {0} for deletion".format(product))
			deleteProducts.append(product)
		else:
			if not product.id in productIds:
				productIds.append(product.id)

	if deleteProducts:
		backend.product_deleteObjects(deleteProducts)


def cleanUpProductOnDepots(backend, depotIds, existingProductIdents):
	"""
	Deletes obsolete information that occurs if either a depot or a \
product is not existing anymore.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	:param depotIds: IDs of the existing depot.
	:type depotIds: [str, ]
	:param existingProductIdents: Idents of the existing products.
	:type existingProductIdents: [str, ]
	"""
	deleteProductOnDepots = []
	for productOnDepot in backend.productOnDepot_getObjects():
		productIdent = ";".join([productOnDepot.productId,
			productOnDepot.productVersion, productOnDepot.packageVersion])
		if not productOnDepot.depotId in depotIds:
			LOGGER.info(
				"Marking product on depot {poc} for deletion, because "
				"opsiDepot-Server '{depotId}' not found".format(
					poc=productOnDepot,
					depotId=productOnDepot.depotId
				)
			)
			deleteProductOnDepots.append(productOnDepot)
		elif not productIdent in existingProductIdents:
			LOGGER.info(
				"Marking product on depot {0} with missing product reference "
				"for deletion".format(productOnDepot)
			)
			deleteProductOnDepots.append(productOnDepot)

	if deleteProductOnDepots:
		backend.productOnDepot_deleteObjects(deleteProductOnDepots)


def cleanUpProductOnClients(backend):
	"""
	Delete :py:class:`ProductOnClient` if the client does not exist or \
is either *not_installed* without an action request set.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	deleteProductOnClients = []
	clientIds = []
	for client in backend.host_getObjects(type=["OpsiClient"]):
		clientIds.append(client.id)
	for productOnClient in backend.productOnClient_getObjects():
		if productOnClient.clientId not in clientIds:
			LOGGER.info(
				"Marking productOnClient {0} for deletion, client "
				"doesn't exists".format(productOnClient)#
			)
			deleteProductOnClients.append(productOnClient)
		elif (productOnClient.installationStatus == 'not_installed'
				and productOnClient.actionRequest == 'none'):
			LOGGER.info(
				"Marking productOnClient {0} for "
				"deletion".format(productOnClient)
			)
			deleteProductOnClients.append(productOnClient)

	if deleteProductOnClients:
		backend.productOnClient_deleteObjects(deleteProductOnClients)

	deleteProductOnClients = []
	productIds = []
	for product in backend.product_getObjects():
		if not product.getId() in productIds:
			productIds.append(product.getId())
	for productOnClient in backend.productOnClient_getObjects():
		if not productOnClient.productId in productIds:
			LOGGER.info(
				"Marking productOnClient {0} for "
				"deletion".format(productOnClient)
			)
			deleteProductOnClients.append(productOnClient)

	if deleteProductOnClients:
		backend.productOnClient_deleteObjects(deleteProductOnClients)


def cleanUpConfigStates(backend):
	"""
	Deletes configStates if the corresponding config is nonexisting.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	deleteConfigStates = []
	configIds = backend.config_getIdents()
	for configState in backend.configState_getObjects():
		if not configState.configId in configIds:
			LOGGER.info(
				"Marking configState {configState} of non existent config "
				"'{config}' for deletion".format(
					configState=configState,
					config=configState.configId
				)
			)
			deleteConfigStates.append(configState)

	if deleteConfigStates:
		backend.configState_deleteObjects(deleteConfigStates)


def cleanUpAuditSoftwares(backend):
	"""
	Deletes unreferenced audit software.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	idents = []
	for aso in backend.auditSoftwareOnClient_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if not ident in idents:
			idents.append(ident)

	for aso in backend.auditSoftware_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if not ident in idents:
			LOGGER.info(u"Deleting unreferenced audit software '%s'" % ident)
			backend.auditSoftware_delete(aso['name'], aso['version'],
				aso['subVersion'], aso['language'], aso['architecture']
			)


def cleanUpAuditSoftwareOnClients(backend):
	"""
	Deletes unreferenced auditSoftwareOnClients.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	idents = []
	for aso in backend.auditSoftware_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if not ident in idents:
			idents.append(ident)

	for aso in backend.auditSoftwareOnClient_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if not ident in idents:
			LOGGER.info(u"Deleting audit software on client '%s'" % ident)
			backend.auditSoftwareOnClient_delete(aso['name'], aso['version'],
				aso['subVersion'], aso['language'], aso['architecture'],
				aso['clientId']
			)
