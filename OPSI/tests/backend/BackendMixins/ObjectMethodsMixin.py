from OPSI.Object import *

class ObjectMethodsMixin(object):

	def test_createDuplicateProductProperies(self):
		self.backend.productProperty_createObjects([self.expected.productProperty4, self.expected.productProperty1, self.expected.productProperty4, self.expected.productProperty4, self.expected.productProperty4])
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.expected.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.expected.productProperties), len(productProperties)))

	def test_getProductDependenciesFromBackend(self):
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies),len(self.expected.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
		
	def test_updateProductDependencies(self):
		self.expected.productDependency2.requiredProductVersion = "2.0"
		self.expected.productDependency2.requirementType = None
		self.backend.productDependency_updateObject(self.expected.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
		for productDependency in productDependencies:
			if productDependency.getIdent() == self.expected.productDependency2.getIdent():
				self.assertEqual(productDependency.getRequiredProductVersion(), u"2.0", u"Expected required version to be %s but got %s." % (u"2.0", productDependency.getRequiredProductVersion()))
				self.assertEqual(productDependency.getRequirementType(),'before', u"Expected requirement type to be '%s' but got '%s.'" % ('before',productDependency.getRequirementType()))

	def test_deleteProductDependency(self):
		self.backend.productDependency_deleteObjects(self.expected.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies) - 1, u"Expected %s product dependencies but got %s from backend." % (len(self.expected.productDependencies) - 1, len(productDependencies)))
		
	def test_createDuplicateProductDependency(self):
		self.backend.productDependency_createObjects(self.expected.productDependencies)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.expected.productDependencies), u"Expected %s product dependencies but got %s from backend." % (len(self.expected.productDependencies), len(productDependencies)))
	
	
	def test_processProductOnClientSequence(self):
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.expected.client1.getId())
		self.backend.productOnClient_deleteObjects(productOnClients)
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.expected.client1.getId())
		
		# setup of product2 requires product3 setup before
		# setup of product2 requires product4 installed before
		# setup of product4 requires product5 installed before
		# resulting sequence:
		#  (product3 (setup))
		#  product5 (setup)
		#  product4 (setup)
		#  product2 (setup)
		
		productOnClient1 = ProductOnClient(
			productId          = self.expected.product2.getId(),
			productType        = self.expected.product2.getType(),
			clientId           = self.expected.client1.getId(),
			installationStatus = 'not_installed',
			actionRequest      = 'setup'
		)
		self.backend.backend_setOptions({'processProductOnClientSequence': True, 'addDependentProductOnClients': True})
		self.backend.productOnClient_createObjects([productOnClient1])
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.expected.client1.getId())
		posProduct2 = -1
		posProduct3 = -1
		posProduct4 = -1
		posProduct5 = -1
		for productOnClient in productOnClients:
			if (productOnClient.productId == self.expected.product2.getId()):
				posProduct2 = productOnClient.actionSequence
			elif (productOnClient.productId == self.expected.product3.getId()):
				posProduct3 = productOnClient.actionSequence
			elif (productOnClient.productId == self.expected.product4.getId()):
				posProduct4 = productOnClient.actionSequence
			elif (productOnClient.productId == self.expected.product5.getId()):
				posProduct5 = productOnClient.actionSequence
		if (posProduct2 == -1) or (posProduct3 == -1) or (posProduct4 == -1) or (posProduct5 == -1):
			raise Exception(u"Processing of product on client sequence failed")
		self.assertGreater(posProduct2, posProduct3, u"Wrong sequence: product3 not before product2")
		self.assertGreater(posProduct2, posProduct4, u"Wrong sequence: product4 not before product2")
		self.assertGreater(posProduct2, posProduct5, u"Wrong sequence: product5 not before product2")
		self.assertGreater(posProduct4, posProduct5, u"Wrong sequence: product5 not before product4")
