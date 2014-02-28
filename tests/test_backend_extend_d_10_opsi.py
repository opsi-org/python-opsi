#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import unittest


from OPSI.Object import (OpsiClient, LocalbootProduct, ProductOnClient,
						 ProductDependency, OpsiDepotserver, ProductOnDepot,
						 UnicodeConfig, ConfigState)

from .Backends.File import ExtendedFileBackendMixin


class BackendExtendedThroughOPSITestCase(unittest.TestCase, ExtendedFileBackendMixin):
	def setUp(self):
		self.setUpBackend()
		self.backendManager = self.backend
		self.fillBackend()

	def fillBackend(self):
		client = OpsiClient(
			id='backend-test-1.vmnat.local',
			description='Unittest Test client.'
		)

		depot = OpsiDepotserver(
			id='depotserver1.some.test',
			description='Test Depot',
		)

		self.backendManager.host_createObjects([client, depot])

		firstProduct = LocalbootProduct('already_installed', '1.0', '1.0')
		secondProduct = LocalbootProduct('to_install', '1.0', '1.0')

		prodDependency = ProductDependency(
			productId=firstProduct.id,
			productVersion=firstProduct.productVersion,
			packageVersion=firstProduct.packageVersion,
			productAction='setup',
			requiredProductId=secondProduct.id,
			# requiredProductVersion=secondProduct.productVersion,
			# requiredPackageVersion=secondProduct.packageVersion,
			requiredAction='setup',
			requiredInstallationStatus='installed',
			requirementType='after'
		)

		self.backendManager.product_createObjects([firstProduct, secondProduct])
		self.backendManager.productDependency_createObjects([prodDependency])

		poc = ProductOnClient(
			clientId=client.id,
			productId=firstProduct.id,
			productType=firstProduct.getType(),
			productVersion=firstProduct.productVersion,
			packageVersion=firstProduct.packageVersion,
			installationStatus='installed',
			actionResult='successful'
		)

		self.backendManager.productOnClient_createObjects([poc])

		firstProductOnDepot = ProductOnDepot(
			productId=firstProduct.id,
			productType=firstProduct.getType(),
			productVersion=firstProduct.productVersion,
			packageVersion=firstProduct.packageVersion,
			depotId=depot.getId(),
			locked=False
		)

		secondProductOnDepot = ProductOnDepot(
			productId=secondProduct.id,
			productType=secondProduct.getType(),
			productVersion=secondProduct.productVersion,
			packageVersion=secondProduct.packageVersion,
			depotId=depot.getId(),
			locked=False
		)

		self.backendManager.productOnDepot_createObjects([firstProductOnDepot, secondProductOnDepot])

		clientConfigDepotId = UnicodeConfig(
			id=u'clientconfig.depot.id',
			description=u'Depotserver to use',
			possibleValues=[],
			defaultValues=[depot.id]
		)

		self.backendManager.config_createObjects(clientConfigDepotId)

		clientDepotMappingConfigState = ConfigState(
			configId=clientConfigDepotId.getId(),
			objectId=client.getId(),
			values=depot.getId()
		)

		self.backendManager.configState_createObjects(clientDepotMappingConfigState)

	def tearDown(self):
		self.tearDownBackend()

	def testBackendDoesNotCreateProductsOnClientsOnItsOwn(self):
		pocs = self.backendManager.productOnClient_getObjects()
		self.assertEqual(
			1,
			len(pocs),
			'Expected to have only one ProductOnClient but got {n} instead: '
			'{0}'.format(pocs, n=len(pocs))
		)

	def testSetProductActionRequestWithDependenciesSetsProductsToSetup(self):
		"""
		An product action request should set product that are dependencies to \
setup even if they are already installed on a client.
		"""
		self.backendManager.setProductActionRequestWithDependencies(
			'to_install',
			'backend-test-1.vmnat.local',
			'setup'
		)

		productsOnClient = self.backendManager.productOnClient_getObjects()
		self.assertEqual(
			2,
			len(productsOnClient),
			'Expected to have two ProductOnClients. Instead we got {n}: '
			'{0}'.format(productsOnClient, n=len(productsOnClient))
		)

		productThatShouldBeReinstalled = None
		for poc in productsOnClient:
			self.assertEqual(
				'backend-test-1.vmnat.local',
				poc.clientId,
				'Wrong client id. Expected it to be "{0}" but got: '
				'{1}'.format('backend-test-1.vmnat.local', poc.clientId)
			)

			if poc.productId == 'already_installed':
				productThatShouldBeReinstalled = poc

		if productThatShouldBeReinstalled is None:
			self.fail('Could not find a product "{0}" on the client.'.format('already_installed'))

		self.assertEquals(productThatShouldBeReinstalled.productId, 'already_installed')
		self.assertEquals(productThatShouldBeReinstalled.actionRequest, 'setup')


if __name__ == '__main__':
	unittest.main()
