
from OPSI.Object import *

class ExtendedBackendMixin(object):
	
	
	
	def test_OpsiClientOnDepotServer(self):

		clients = self.backend.host_getObjects(type = 'OpsiClient')
		clientToDepots = self.backend.configState_getClientToDepotserver()
		self.assertEqual(len(clientToDepots), len(clients), u"Expected %s clients, but got %s from backend." % (len(clientToDepots), len(clients)))
		
		for depotserver in self.expected.depotservers:
			productOnDepots = self.backend.productOnDepot_getObjects(depotId = depotserver.id)
			expectedProducts = filter(lambda x: x.depotId == depotserver.id, self.expected.productOnDepots)
			for productOnDepot in productOnDepots:
				self.assertIn(productOnDepot, expectedProducts, u"Expected products %s do be on depotserver %s, but depotserver found %s." % (expectedProducts, depotserver.id, productOnDepot.productId))
				
		for clientToDepot in clientToDepots:
			self.assertIn(clientToDepot['depotId'], map((lambda x: x.id),self.expected.depotservers), u"Expected client %s to be in depot %s, but couldn't find it." %(clientToDepot['depotId'], depotserver.id))

	def test_createProductOnClient(self):
		poc = ProductOnClient(
				productId          = 'product6',
				productType        = 'LocalbootProduct',
				clientId           = 'client1.uib.local',
				installationStatus = 'not_installed',
				actionRequest      = 'setup'
		)
		self.backend.productOnClient_createObjects(poc)
		
		productOnClients = map((lambda x: (x.actionRequest == 'setup') and x), self.backend.productOnClient_getObjects(clientId = 'client1.uib.local'))
		self.assertIn ( poc, productOnClients, u"'%s' not in '%s'" % (poc, productOnClients))

	def test_selectProductOnClientWithDefault(self):
		
		poc = ProductOnClient(
				productId          = 'product6',
				productType        = 'LocalbootProduct',
				clientId           = 'client1.uib.local',
				installationStatus = 'not_installed',
				actionRequest      = 'setup'
		)
		self.backend.productOnClient_createObjects(poc)
		
		self.backend.productOnClient_delete(
			productId          = 'product7',
			clientId           = 'client1.uib.local')
			
		productOnClients = map((lambda x: x.productId), self.backend.productOnClient_getObjects(clientId = 'client1.uib.local', productId = ['product6', 'product7']))
		productOnClients.sort()
		self.assertEqual(productOnClients, [u'product6',u'product7'], u"Expected result to be '%s', but got %s from backend." % (productOnClients, ['product6', 'product7']))
#		
	def test_selectProductOnClientsByWildcard(self):
		
		poc = ProductOnClient(
				productId          = 'product6',
				productType        = 'LocalbootProduct',
				clientId           = 'client1.uib.local',
				installationStatus = 'not_installed',
				actionRequest      = 'setup'
		)
		
		self.backend.productOnClient_createObjects(poc)
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = 'client1.uib.local', productId = ['*6*'])
		self.assertEqual(productOnClients, [poc], "Expected product %s on client %s, but got %s from backend" % (poc.productId, poc.clientId, productOnClients))