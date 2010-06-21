

class ExtendedBackendMixin(object):
	
	
	
	def test_OpsiClientOnDepotServer(self):

		clients = self.backend.host_getObjects(type = 'OpsiClient')
		clientToDepots = self.backend.configState_getClientToDepotserver()
		self.assertEqual(len(clientToDepots), len(clients), u"Expected %s clients, but got %s from backend." % (len(clientToDepots), len(clients)))
		
		for depotserver in self.depotservers:
			productOnDepots = self.backend.productOnDepot_getObjects(depotId = depotserver.id)
			expectedProducts = filter(lambda x: x.depotId == depotserver.id, self.productOnDepots)
			for productOnDepot in productOnDepots:
				self.assertIn(productOnDepot, expectedProducts, u"Expected products %s do be on depotserver %s, but depotserver found %s." % (expectedProducts, depotserver.id, productOnDepot.productId))
				
		for clientToDepot in clientToDepots:
			self.assertIn(clientToDepot['depotId'], map((lambda x: x.id),self.depotservers), u"Expected client %s to be in depot %s, but couldn't find it." %(clientToDepot['depotId'], depotserver.id))



	def fppExtendedBackend(self):


		
		# TODO
		
		# depotserver1: client1, client2, client3, client4
		# depotserver2: client5, client6, client7
		
		# depotserver1: product6_1.0-1, product7_1.0-1, product9_1.0-1
		# depotserver2: product6_1.0-1, product7_1.0-2, product9_1.0-1
		
		# product6_1.0-1: setup requires product7_1.0-1
		# product7_1.0-1: setup requires product9
		
		self.backend.productOnClient_create(
			productId          = 'product6',
			productType        = 'LocalbootProduct',
			clientId           = 'client1.uib.local',
			installationStatus = 'not_installed',
			actionRequest      = 'setup')
		
		self.backend.productOnClient_delete(
			productId          = 'product7',
			clientId           = 'client1.uib.local')
		
		self.backend.productOnClient_delete(
			productId          = 'product9',
			clientId           = 'client1.uib.local')
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = 'client1.uib.local')
		setup = []
		for productOnClient in productOnClients:
			logger.info(u"Got productOnClient: %s" % productOnClient)
			if (productOnClient.actionRequest == 'setup'):
				setup.append(productOnClient.productId)
		assert 'product6' in setup, u"'%s' not in '%s'" % ('product6', setup)
		#assert 'product7' in setup, u"'%s' not in '%s'" % ('product7', setup)
		#assert 'product9' in setup, u"'%s' not in '%s'" % ('product9', setup)
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = 'client1.uib.local', productId = ['product6', 'product7'])
		for productOnClient in productOnClients:
			logger.info(u"Got productOnClient: %s" % productOnClient)
			assert productOnClient.productId in ('product6', 'product7'), u"'%s' not in '%s'" % (productOnClient.productId, ('product6', 'product7'))
#			, u"Product id filter failed, got product id: %s" % productOnClient.productId
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = 'client1.uib.local', productId = ['*6*'])
		for productOnClient in productOnClients:
			logger.info(u"Got productOnClient: %s" % productOnClient)
			assert productOnClient.productId in ('product6'), u"'%s' not in '%s'" % (productOnClient.productId, ('product6'))
#			, u"Product id filter failed, got product id: %s" % productOnClient.productId
		
		self.backend.productOnClient_create(
			productId          = 'product6',
			productType        = 'LocalbootProduct',
			clientId           = 'client5.uib.local',
			installationStatus = 'not_installed',
			actionRequest      = 'setup')
		
		self.backend.productOnClient_delete(
			productId          = 'product7',
			clientId           = 'client5.uib.local')
		
		self.backend.productOnClient_delete(
			productId          = 'product9',
			clientId           = 'client5.uib.local')
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = 'client5.uib.local')
		setup = []
		for productOnClient in productOnClients:
			if (productOnClient.actionRequest == 'setup'):
				setup.append(productOnClient.productId)
		#assert not 'product6' in setup, u"'%s' is in '%s'" % ('product6', setup)
		assert not 'product7' in setup, u"'%s' is in '%s'" % ('product7', setup)
		assert not 'product9' in setup, u"'%s' is in '%s'" % ('product9', setup)
		