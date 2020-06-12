# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2019 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded legacy extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/40_admin_tasks.conf``.


:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Exceptions import BackendMissingDataError
from OPSI.Object import (OpsiClient, LocalbootProduct, ProductOnClient,
						 OpsiDepotserver, ProductOnDepot, UnicodeConfig,
						 ConfigState)
from OPSI.Types import forceList

import pytest


def testSetActionRequestWhereOutdatedRequiresExistingActionRequestAndProductId(backendManager):
	with pytest.raises(TypeError):
		backendManager.setActionRequestWhereOutdated()

	with pytest.raises(TypeError):
		backendManager.setActionRequestWhereOutdated('setup')

	with pytest.raises(BackendMissingDataError):
		backendManager.setActionRequestWhereOutdated('setup', 'unknownProductId')


def testSetActionRequestWhereOutdated(backendManager):
	backend = backendManager

	client_with_old_product = OpsiClient(id='clientwithold.test.invalid')
	client_with_current_product = OpsiClient(id='clientwithcurrent.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')
	client_unknown_status = OpsiClient(id='clientunkown.test.invalid')
	clients = [client_with_old_product, client_with_current_product,
			   client_without_product, client_unknown_status]

	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot, client_with_old_product,
								client_with_current_product,
								client_without_product, client_unknown_status])

	old_product = LocalbootProduct('thunderheart', '1', '1')
	new_product = LocalbootProduct('thunderheart', '1', '2')

	backend.product_createObjects([old_product, new_product])

	with pytest.raises(ValueError):
		backend.setActionRequestWhereOutdated('invalid', 'thunderheart')

	poc = ProductOnClient(
		clientId=client_with_old_product.id,
		productId=old_product.id,
		productType=old_product.getType(),
		productVersion=old_product.productVersion,
		packageVersion=old_product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	poc2 = ProductOnClient(
		clientId=client_with_current_product.id,
		productId=new_product.id,
		productType=new_product.getType(),
		productVersion=new_product.productVersion,
		packageVersion=new_product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	poc3 = ProductOnClient(
		clientId=client_unknown_status.id,
		productId=old_product.id,
		productType=old_product.getType(),
		productVersion=old_product.productVersion,
		packageVersion=old_product.packageVersion,
		installationStatus='unknown',
	)

	backend.productOnClient_createObjects([poc, poc2, poc3])

	installedProductOnDepot = ProductOnDepot(
		productId=new_product.id,
		productType=new_product.getType(),
		productVersion=new_product.productVersion,
		packageVersion=new_product.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	for client in clients:
		clientDepotMappingConfigState = ConfigState(
			configId=u'clientconfig.depot.id',
			objectId=client.getId(),
			values=depot.getId()
		)

		backend.configState_createObjects(clientDepotMappingConfigState)

	# Starting the checks
	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_without_product.id)
	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_old_product.id, actionRequest="setup")
	assert backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_current_product.id)
	assert backend.productOnClient_getObjects(productId=old_product.id, clientId=client_unknown_status.id, installationStatus='unknown')

	clientIDs = backend.setActionRequestWhereOutdated('setup', new_product.id)

	assert 1 == len(clientIDs)
	assert client_with_old_product.id, list(clientIDs)[0]
	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_without_product.id)
	poc = backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_old_product.id)[0]
	assert "setup" == poc.actionRequest

	poc = backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_current_product.id)[0]
	assert "setup" != poc.actionRequest

	poc = backend.productOnClient_getObjects(productId=old_product.id, clientId=client_unknown_status.id)[0]
	assert "setup" != poc.actionRequest
	assert "unknown" == poc.installationStatus


def testUninstallWhereInstalledFailsWithoutExistingProductId(backendManager):
	with pytest.raises(TypeError):
		backendManager.uninstallWhereInstalled()

	with pytest.raises(BackendMissingDataError):
		backendManager.uninstallWhereInstalled('unknownProductId')


def testUninstallWhereInstalled(backendManager):
	backend = backendManager
	client_with_product = OpsiClient(id='clientwith.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')
	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot, client_with_product,
								client_without_product])

	product = LocalbootProduct('thunderheart', '1', '1', uninstallScript='foo.bar')
	productWithoutScript = LocalbootProduct('installOnly', '1', '1')

	backend.product_createObjects([product, productWithoutScript])

	installedProductOnDepot = ProductOnDepot(
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		depotId=depot.id,
		locked=False
	)
	installedProductOnDepot2 = ProductOnDepot(
		productId=productWithoutScript.id,
		productType=productWithoutScript.getType(),
		productVersion=productWithoutScript.productVersion,
		packageVersion=productWithoutScript.packageVersion,
		depotId=depot.id,
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot,
										  installedProductOnDepot2])

	assert not backend.uninstallWhereInstalled('thunderheart')

	poc = ProductOnClient(
		clientId=client_with_product.id,
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	pocWithoutScript = ProductOnClient(
		clientId=client_with_product.id,
		productId=productWithoutScript.id,
		productType=productWithoutScript.getType(),
		productVersion=productWithoutScript.productVersion,
		packageVersion=productWithoutScript.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	backend.productOnClient_createObjects([poc, pocWithoutScript])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)
	backend.config_createObjects(clientConfigDepotId)

	clientIDs = backend.uninstallWhereInstalled(product.id)

	assert 1 == len(clientIDs)
	pocAfter = backend.productOnClient_getObjects(productId=product.id, clientId=client_with_product.id)
	assert 1 == len(pocAfter)
	pocAfter = pocAfter[0]
	assert "uninstall" == pocAfter.actionRequest

	clientIDs = backend.uninstallWhereInstalled(productWithoutScript.id)
	assert 0 == len(clientIDs)


def testUpdateWhereInstalledFailsWithoutKnownProduct(backendManager):
	with pytest.raises(TypeError):
		backendManager.updateWhereInstalled()

	with pytest.raises(BackendMissingDataError):
		backendManager.updateWhereInstalled('unknownProductId')


def testUpdateWhereInstalled(backendManager):
	backend = backendManager

	client_with_old_product = OpsiClient(id='clientwithold.test.invalid')
	client_with_current_product = OpsiClient(id='clientwithcurrent.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')

	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot, client_with_old_product,
								client_with_current_product,
								client_without_product])

	old_product = LocalbootProduct('thunderheart', '1', '1')
	new_product = LocalbootProduct('thunderheart', '1', '2',
								   updateScript='foo.opsiscript')

	backend.product_createObjects([old_product, new_product])

	assert not backend.updateWhereInstalled('thunderheart')

	poc = ProductOnClient(
		clientId=client_with_old_product.id,
		productId=old_product.id,
		productType=old_product.getType(),
		productVersion=old_product.productVersion,
		packageVersion=old_product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	poc2 = ProductOnClient(
		clientId=client_with_current_product.id,
		productId=new_product.id,
		productType=new_product.getType(),
		productVersion=new_product.productVersion,
		packageVersion=new_product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)

	backend.productOnClient_createObjects([poc, poc2])

	installedProductOnDepot = ProductOnDepot(
		productId=new_product.id,
		productType=new_product.getType(),
		productVersion=new_product.productVersion,
		packageVersion=new_product.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	# Starting the checks
	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_without_product.id)
	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_old_product.id, actionRequest="setup")
	assert backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_current_product.id)

	clientIDs = backend.updateWhereInstalled('thunderheart')

	assert not backend.productOnClient_getObjects(productId=new_product.id, clientId=client_without_product.id)
	poc = backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_old_product.id)[0]
	assert "update" == poc.actionRequest
	poc = backend.productOnClient_getObjects(productId=new_product.id, clientId=client_with_current_product.id)[0]
	assert "update" == poc.actionRequest

	assert 2 == len(clientIDs)
	assert client_with_old_product.id in clientIDs
	assert client_with_current_product.id in clientIDs


def testSetupWhereInstalledFailsWithoutExistingProductId(backendManager):
	with pytest.raises(TypeError):
		backendManager.setupWhereInstalled()

	with pytest.raises(BackendMissingDataError):
		backendManager.setupWhereInstalled('unknownProductId')


def testSetupWhereInstalled(backendManager):
	backend = backendManager

	client_with_product = OpsiClient(id='clientwith.test.invalid')
	client_with_failed_product = OpsiClient(id='failedclient.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')

	clients = set([client_with_product, client_without_product, client_with_failed_product])
	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot])
	backend.host_createObjects(clients)

	product = LocalbootProduct('thunderheart', '1', '1', setupScript='foo.bar')

	backend.product_createObjects([product])

	installedProductOnDepot = ProductOnDepot(
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		depotId=depot.id,
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot])

	assert not backend.setupWhereInstalled('thunderheart')

	poc = ProductOnClient(
		clientId=client_with_product.id,
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)
	pocFailed = ProductOnClient(
		clientId=client_with_failed_product.id,
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		installationStatus='unknown',
		actionResult='failed'
	)
	backend.productOnClient_createObjects([poc, pocFailed])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	for client in clients:
		clientDepotMappingConfigState = ConfigState(
			configId=u'clientconfig.depot.id',
			objectId=client.getId(),
			values=depot.getId()
		)

		backend.configState_createObjects(clientDepotMappingConfigState)

	clientIDs = backend.setupWhereInstalled(product.id)
	assert 1 == len(clientIDs)
	assert client_with_product.id == forceList(clientIDs)[0]

	assert not backend.productOnClient_getObjects(productId=product.id, clientId=client_without_product.id)

	pocAfter = backend.productOnClient_getObjects(productId=product.id, clientId=client_with_product.id)
	assert 1 == len(pocAfter)
	pocAfter = pocAfter[0]
	assert "setup" == pocAfter.actionRequest

	pocFailed = backend.productOnClient_getObjects(productId=product.id, clientId=client_with_failed_product.id)
	assert 1 == len(pocFailed)
	pocFailed = pocFailed[0]
	assert "setup" != pocFailed.actionRequest
	assert 'successful' == poc.actionResult


def testSetupWhereNotInstalledFailsWithoutExistingProductId(backendManager):
	with pytest.raises(TypeError):
		backendManager.setupWhereInstalled()

	with pytest.raises(BackendMissingDataError):
		backendManager.setupWhereNotInstalled('unknownProductId')


def testSetupWhereNotInstalled(backendManager):
	backend = backendManager

	client_with_current_product = OpsiClient(id='clientwithcurrent.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')

	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot,
								client_with_current_product,
								client_without_product])

	product = LocalbootProduct('thunderheart', '1', '1', setupScript='foo.bar')

	backend.product_createObjects([product])

	poc = ProductOnClient(
		clientId=client_with_current_product.id,
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		installationStatus='installed',
		actionResult='successful'
	)

	backend.productOnClient_createObjects([poc])

	installedProductOnDepot = ProductOnDepot(
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	for client in (client_with_current_product, client_without_product):
		clientDepotMappingConfigState = ConfigState(
			configId=u'clientconfig.depot.id',
			objectId=client.getId(),
			values=depot.getId()
		)

		backend.configState_createObjects(clientDepotMappingConfigState)

	# Starting the checks
	assert not backend.productOnClient_getObjects(productId=product.id, clientId=client_without_product.id)
	assert backend.productOnClient_getObjects(productId=product.id, clientId=client_with_current_product.id)

	clientIDs = backend.setupWhereNotInstalled(product.id)

	assert 1 == len(clientIDs)
	poc = backend.productOnClient_getObjects(productId=product.id, clientId=client_without_product.id)[0]
	assert "setup" == poc.actionRequest


def testSetupWhereFailed(backendManager):
	backend = backendManager

	client_with_failed_product = OpsiClient(id='clientwithcurrent.test.invalid')
	client_without_product = OpsiClient(id='clientwithout.test.invalid')

	depot = OpsiDepotserver(id='depotserver1.test.invalid')

	backend.host_createObjects([depot,
								client_with_failed_product,
								client_without_product])

	product = LocalbootProduct('thunderheart', '1', '1', setupScript='foo.bar')

	backend.product_createObjects([product])

	poc = ProductOnClient(
		clientId=client_with_failed_product.id,
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		actionResult='failed',
	)

	backend.productOnClient_createObjects([poc])

	installedProductOnDepot = ProductOnDepot(
		productId=product.id,
		productType=product.getType(),
		productVersion=product.productVersion,
		packageVersion=product.packageVersion,
		depotId=depot.getId(),
		locked=False
	)

	backend.productOnDepot_createObjects([installedProductOnDepot])

	clientConfigDepotId = UnicodeConfig(
		id=u'clientconfig.depot.id',
		description=u'Depotserver to use',
		possibleValues=[],
		defaultValues=[depot.id]
	)

	backend.config_createObjects(clientConfigDepotId)

	for client in (client_with_failed_product, client_without_product):
		clientDepotMappingConfigState = ConfigState(
			configId=u'clientconfig.depot.id',
			objectId=client.getId(),
			values=depot.getId()
		)

		backend.configState_createObjects(clientDepotMappingConfigState)

	# Starting the checks
	assert not backend.productOnClient_getObjects(productId=product.id, clientId=client_without_product.id)
	assert backend.productOnClient_getObjects(productId=product.id, clientId=client_with_failed_product.id)

	clientIDs = backend.setupWhereFailed(product.id)

	assert 1 == len(clientIDs)
	poc = backend.productOnClient_getObjects(productId=product.id, clientId=client_with_failed_product.id)[0]
	assert "setup" == poc.actionRequest
	assert 'failed' == poc.actionResult
