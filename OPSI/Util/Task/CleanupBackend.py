# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

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

import re

import OPSI.Util.Task.ConfigureBackend as backendUtil
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Backend.MySQL import MySQL
from OPSI.Logger import Logger
from OPSI.Types import forceBool, forceUnicodeLower
from OPSI.Util import chunk
from OPSI.Util.File.Opsi import BackendDispatchConfigFile

LOGGER = Logger()
_CHUNK_SIZE = 500


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
			if not re.search(regex, u'backend_createBase'):
				continue

			if 'mysql' in backends:
				return True

		return False

	LOGGER.debug("Cleaning backend chunk size: %s", _CHUNK_SIZE)

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

	LOGGER.debug(u'Getting current depots...')
	depotIds = set(depot.id for depot in backend.host_getObjects(type=["OpsiConfigserver", "OpsiDepotserver"]))  # pylint: disable=maybe-no-member
	LOGGER.debug(u'Depots are: %s', depotIds)

	LOGGER.debug(u'Getting current products...')
	productIdents = set(product.getIdent(returnType='unicode') for product in backend.product_getObjects())
	LOGGER.debug(u'Product idents are: %s', productIdents)

	LOGGER.notice(u"Cleaning up product on depots")
	cleanUpProductOnDepots(backend, depotIds, productIdents)

	LOGGER.notice(u"Cleaning up product on clients")
	cleanUpProductOnClients(backend)

	LOGGER.notice(u"Cleaning up product properties")
	productPropertyIdents = set()
	deleteProductProperties = []
	productPropertiesToCleanup = {}
	for productProperty in backend.productProperty_getObjects():  # pylint: disable=maybe-no-member
		productIdent = u"%s;%s;%s" % (productProperty.productId, productProperty.productVersion, productProperty.packageVersion)
		if not productProperty.editable and productProperty.possibleValues:
			productPropertyIdent = u"%s;%s" % (productIdent, productProperty.propertyId)
			productPropertiesToCleanup[productPropertyIdent] = productProperty

		if productIdent not in productIdents:
			LOGGER.info(u"Marking productProperty %s of non existent product '%s' for deletion", productProperty, productIdent)
			deleteProductProperties.append(productProperty)
		else:
			productPropertyIdent = u'%s;%s' % (productProperty.productId, productProperty.propertyId)
			productPropertyIdents.add(productPropertyIdent)

	if deleteProductProperties:
		for productProperties in chunk(deleteProductProperties, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting product properties: '%s'", productProperties)
			backend.productProperty_deleteObjects(productProperties)  # pylint: disable=maybe-no-member

	LOGGER.notice(u"Cleaning up product property states")
	deleteProductPropertyStates = []
	for productPropertyState in backend.productPropertyState_getObjects():  # pylint: disable=maybe-no-member
		productPropertyIdent = u'%s;%s' % (productPropertyState.productId, productPropertyState.propertyId)
		if productPropertyIdent not in productPropertyIdents:
			LOGGER.info(u"Marking productPropertyState %s of non existent productProperty '%s' for deletion", productPropertyState, productPropertyIdent)
			deleteProductPropertyStates.append(productPropertyState)

	if deleteProductPropertyStates:
		for productPropertyStates in chunk(deleteProductPropertyStates, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting product property states: '%s'", productPropertyStates)
			backend.productPropertyState_deleteObjects(productPropertyStates)  # pylint: disable=maybe-no-member

	for depot in backend.host_getObjects(type='OpsiDepotserver'):  # pylint: disable=maybe-no-member
		objectIds = set(ClientToDepot['clientId'] for ClientToDepot in backend.configState_getClientToDepotserver(depotIds=depot.id))
		objectIds.add(depot.id)

		productOnDepotIdents = {}
		for productOnDepot in backend.productOnDepot_getObjects(depotId=depot.id):  # pylint: disable=maybe-no-member
			productIdent = u"%s;%s;%s" % (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion)
			productOnDepotIdents[productOnDepot.productId] = productIdent

		if not productOnDepotIdents:
			continue

		deleteProductPropertyStates = []
		updateProductPropertyStates = []
		for productPropertyState in backend.productPropertyState_getObjects(  # pylint: disable=maybe-no-member
				objectId=objectIds,
				productId=list(productOnDepotIdents),
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
				if productProperty.getType() == u'BoolProductProperty' and forceBool(value) in productProperty.possibleValues:
					newValues.append(forceBool(value))
					changedValues.append(value)
					changed = True
					continue
				if productProperty.getType() == u'UnicodeProductProperty':
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
					LOGGER.info(u"Marking productPropertyState %s for deletion: no value in possible values (%s)", productPropertyState, removeValues)
					deleteProductPropertyStates.append(productPropertyState)
				else:
					productPropertyState.setValues(newValues)
					LOGGER.info(u"Marking productPropertyState %s for update: values not in possible values: %s, values corrected: %s", productPropertyState, removeValues, changedValues)
					updateProductPropertyStates.append(productPropertyState)

		if deleteProductPropertyStates:
			for productPropertyStates in chunk(deleteProductPropertyStates, _CHUNK_SIZE):
				LOGGER.debug(u"Deleting product property states: '%s'", productPropertyStates)
				backend.productPropertyState_deleteObjects(productPropertyStates)  # pylint: disable=maybe-no-member
			del deleteProductPropertyStates

		if updateProductPropertyStates:
			for productPropertyStates in chunk(updateProductPropertyStates, _CHUNK_SIZE):
				LOGGER.debug(u"Updating product property states: '%s'", productPropertyStates)
				backend.productPropertyState_updateObjects(productPropertyStates)  # pylint: disable=maybe-no-member
			del updateProductPropertyStates

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
	LOGGER.info(u"Current mysql backend config: %s", config)

	LOGGER.notice(
		u"Connection to database '{database}' on '{address}' as user "
		u"'{username}'".format(**config)
	)
	mysql = MySQL(**config)

	LOGGER.notice(u"Cleaning up defaultValues in productProperties")
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
		LOGGER.notice(u"Deleting PropertyValue id: %s", ID)
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
	groups = backend.group_getObjects(type='HostGroup')
	groupIds = set(group.id for group in groups)

	for group in groups:
		if group.getParentGroupId() and group.getParentGroupId() not in groupIds:
			LOGGER.info(
				u"Removing parent group id '{parentGroupId}' from group "
				u"'{groupId}' because parent group does not exist".format(
					parentGroupId=group.parentGroupId,
					groupId=group.id
				)
			)
			group.parentGroupId = None
			updatedGroups.append(group)

	if updatedGroups:
		for group in chunk(updatedGroups, _CHUNK_SIZE):
			LOGGER.debug(u"Updating groups: %s", group)
			backend.group_createObjects(group)


def cleanUpProducts(backend):
	"""
	This will delete any unreferenced product from the backend.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	productIdents = set()
	for productOnDepot in backend.productOnDepot_getObjects():
		productIdent = ";".join((
			productOnDepot.productId,
			productOnDepot.productVersion,
			productOnDepot.packageVersion
		))
		productIdents.add(productIdent)

	deleteProducts = []
	for product in backend.product_getObjects():
		if product.getIdent(returnType='unicode') not in productIdents:
			LOGGER.info(u"Marking unreferenced product %s for deletion", product)
			deleteProducts.append(product)

	for products in chunk(deleteProducts, _CHUNK_SIZE):
		LOGGER.debug(u"Deleting products: '%s'", products)
		backend.product_deleteObjects(products)


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
		if productOnDepot.depotId not in depotIds:
			LOGGER.info(
				u"Marking product on depot {poc} for deletion, because "
				u"opsiDepot-Server '{depotId}' not found".format(
					poc=productOnDepot,
					depotId=productOnDepot.depotId
				)
			)
			deleteProductOnDepots.append(productOnDepot)
		elif productIdent not in existingProductIdents:
			LOGGER.info(
				u"Marking product on depot %s with missing product reference "
				u"for deletion", productOnDepot
			)
			deleteProductOnDepots.append(productOnDepot)

	if deleteProductOnDepots:
		for productOnDepots in chunk(deleteProductOnDepots, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting products on depots: %s", productOnDepots)
			backend.productOnDepot_deleteObjects(productOnDepots)


def cleanUpProductOnClients(backend):
	"""
	Delete :py:class:`ProductOnClient` if the client does not exist or \
is either *not_installed* without an action request set.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	deleteProductOnClients = []
	clientIds = set(client.id for client in backend.host_getObjects(type=["OpsiClient"]))

	for productOnClient in backend.productOnClient_getObjects():
		if productOnClient.clientId not in clientIds:
			LOGGER.info(
				u"Marking productOnClient %s for deletion, client "
				u"doesn't exists", productOnClient
			)
			deleteProductOnClients.append(productOnClient)
		elif (productOnClient.installationStatus == u'not_installed'
				and productOnClient.actionRequest == u'none'):
			LOGGER.info(
				u"Marking productOnClient %s for "
				u"deletion", productOnClient
			)
			deleteProductOnClients.append(productOnClient)

	if deleteProductOnClients:
		for productOnClients in chunk(deleteProductOnClients, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting products on clients: '%s'", productOnClients)
			backend.productOnClient_deleteObjects(productOnClients)

	deleteProductOnClients = []
	productIds = set(product.getId() for product in backend.product_getObjects())
	for productOnClient in backend.productOnClient_getObjects():
		if productOnClient.productId not in productIds:
			LOGGER.info(
				u"Marking productOnClient %s for "
				u"deletion", productOnClient
			)
			deleteProductOnClients.append(productOnClient)

	if deleteProductOnClients:
		for productOnClients in chunk(deleteProductOnClients, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting products on clients: '%s'", productOnClients)
			backend.productOnClient_deleteObjects(productOnClients)


def cleanUpConfigStates(backend):
	"""
	Deletes configStates if the corresponding config is nonexisting.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	deleteConfigStates = []
	configIds = set(backend.config_getIdents())

	for configState in backend.configState_getObjects():
		if configState.configId not in configIds:
			LOGGER.info(
				u"Marking configState {configState} of non existent config "
				u"'{config}' for deletion".format(
					configState=configState,
					config=configState.configId
				)
			)
			deleteConfigStates.append(configState)

	if deleteConfigStates:
		for configStates in chunk(deleteConfigStates, _CHUNK_SIZE):
			LOGGER.debug(u"Deleting config states: '%s'", configStates)
			backend.configState_deleteObjects(configStates)


def cleanUpAuditSoftwares(backend):
	"""
	Deletes unreferenced audit software.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	idents = set('%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso for aso in backend.auditSoftwareOnClient_getHashes())

	for aso in backend.auditSoftware_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if ident not in idents:
			LOGGER.info(u"Deleting unreferenced audit software %s", ident)
			backend.auditSoftware_delete(aso['name'], aso['version'],
				aso['subVersion'], aso['language'], aso['architecture']
			)


def cleanUpAuditSoftwareOnClients(backend):
	"""
	Deletes unreferenced auditSoftwareOnClients.

	:param backend: The backend where the data should be cleaned.
	:type backend: OPSI.Backend.Backend
	"""
	idents = set('%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso for aso in backend.auditSoftware_getHashes())

	for aso in backend.auditSoftwareOnClient_getHashes():
		ident = '%(name)s;%(version)s;%(subVersion)s;%(language)s;%(architecture)s' % aso
		if ident not in idents:
			LOGGER.info(u"Deleting audit software on client '%s'", ident)
			backend.auditSoftwareOnClient_delete(aso['name'], aso['version'],
				aso['subVersion'], aso['language'], aso['architecture'],
				aso['clientId']
			)
