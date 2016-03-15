from OPSI.Object import *

class ObjectMethodsMixin(object):


	def test_getHostsHostOnBackend(self):
		hosts = self.backend.host_getObjects()
		self.assertEqual(len(hosts), len(self.expected.hosts), u"Expected '%s' hosts, but found '%s' on backend." % (len(self.expected.hosts), len(hosts)))

	def test_verifyHosts(self):
		hosts = self.backend.host_getObjects()
		for host in hosts:
			self.assertIsNotNone(host.getOpsiHostKey(), u"Host key for host '%s': '%s' is not expected." % (host.getId(), host.getOpsiHostKey()))
			for h in self.expected.hosts:
				if (host.id == h.id):
					h1 = h.toHash()
					h2 = host.toHash()
					h1['lastSeen'] = None
					h2['lastSeen'] = None
					h1['created'] = None
					h2['created'] = None
					h1['inventoryNumber'] = None
					h2['inventoryNumber'] = None
					h1['notes'] = None
					h2['notes'] = None
					h1['opsiHostKey'] = None
					h2['opsiHostKey'] = None
					h1['isMasterDepot'] = None
					h2['isMasterDepot'] = None
					self.assertEqual(h1, h2 , u"Expected host to be %s, got %s" % (h1, h2))

	def test_createDepotserverOnBackend(self):
		hosts = self.backend.host_getObjects(type = 'OpsiConfigserver')
		self.assertEqual(len(hosts), len(self.expected.configservers), u"Expected '%s' depotserver, but found '%s' on backend." % (len(self.expected.hosts), len(hosts)))

	def test_clientsOnBackend(self):
		hosts = self.backend.host_getObjects( type = [ self.expected.clients[0].getType() ] )
		self.assertEqual( len(hosts), len(self.expected.clients), u"Expected %s cients, but found '%s' on backend." %  (len(self.expected.clients),len(hosts)))
		ids = []
		for host in hosts:
			ids.append(host.getId())
		for client in self.expected.clients:
			self.assertIn(client.getId(), ids, u"Client '%s' not found in '%s'" % (client.getId(), ids))

	def test_selectClientsOnBackend(self):
		hosts = self.backend.host_getObjects( id = [ self.expected.client1.getId(), self.expected.client2.getId() ] )
		self.assertEqual(len(hosts), 2, u"Expected 2 Cients, but found '%s' on backend." %  len(hosts))

		ids = []
		for host in hosts:
			ids.append(host.getId())
		self.assertIn(self.expected.client1.getId(),ids, u"Client '%s' not found in '%s'" % (self.expected.client1.getId(), ids))
		self.assertIn(self.expected.client2.getId(),ids, u"Client '%s' not found in '%s'" % (self.expected.client1.getId(), ids))
		
	
	def test_hostAttributes(self):
		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = [ None ] )
		count = 0
		for host in self.expected.hosts:
			if host.getIpAddress() is None:
				count += 1
		
		self.assertEqual(len(hosts), count)
		for host in hosts:
			self.assertIsNone(host.getIpAddress(), u"Expected IP address of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getIpAddress()))
			self.assertIsNone(host.getInventoryNumber(), u"Expected inventory number of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getInventoryNumber()))
			self.assertIsNotNone(host.getNotes(), u"Expected notes of host %s not to be None" % (host.getId()))
			self.assertIsNotNone(host.getDescription(), u"Expected description of host %s not to be None" % (host.getId()))

		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = None )
		self.assertEqual(len(hosts), len(self.expected.hosts), u"Expected '%s' hosts, but found '%s'" % (len(self.expected.hosts), len(hosts)))
		
		for host in hosts:
			self.assertIsNone(host.getIpAddress(), u"Expected IP address of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getIpAddress()))
			self.assertIsNone(host.getInventoryNumber(), u"Expected inventory number of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getInventoryNumber()))

	def test_selectClientsByDescription(self):
		#hosts = self.backend.host_getObjects( id = [ self.expected.client1.getId(), self.expected.client2.getId() ], description = self.expected.client2.getDescription() )   # TODO: Better?
		hosts = self.backend.host_getObjects( type = [ self.expected.clients[0].getType() ], description = self.expected.client2.getDescription() )
		
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].id, self.expected.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.expected.client2.getId(), self.expected.client2.getId(), hosts[0].id))
		self.assertEqual(hosts[0].description, self.expected.client2.getDescription(), u"Expected description of client %s to be '%s', got: '%s'" % (self.expected.client2.getId(), self.expected.client2.getDescription(), hosts[0].description))
		
		
	def test_selectClientById(self):
		hosts = self.backend.host_getObjects(attributes=['id', 'description'], id = self.expected.client1.getId())
		
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].id, self.expected.client1.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.expected.client1.getId(), self.expected.client1.getId(), hosts[0].id))
		self.assertEqual(hosts[0].description, self.expected.client1.getDescription(), u"Expected description of client %s to be '%s', got: '%s'" % (self.expected.client1.getId(), self.expected.client1.getDescription(), hosts[0].description))
		
		
	def test_deleteClientFromBackend(self):
		
		self.backend.host_deleteObjects(self.expected.client2)
		
		hosts = self.backend.host_getObjects( type = [ self.expected.client1.getType() ] )
		self.assertEqual(len(hosts), len(self.expected.clients) - 1, u"Expected %s Clients but found %s on backend." % (len(self.expected.clients) - 1, len(hosts)))
		
		ids = []
		for host in hosts:
			ids.append(host.getId())
			
		self.assertNotIn(self.expected.client2.getId(), ids, "Found Client %s in %s, expected id to be deleted." %(self.expected.client2.getId(), ids))
		
		del(self.expected.clients[self.expected.clients.index(self.expected.client2)])
		for client in self.expected.clients:
			self.assertIn(client.getId(), ids, u"'%s' not in '%s'" % (client.getId(), ids))
			
	def test_updateObjectOnBackend(self):
		self.expected.client2.setDescription('Updated')
		self.backend.host_updateObject(self.expected.client2)
		hosts = self.backend.host_getObjects( description = 'Updated' )
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].getId(), self.expected.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.expected.client2.getId(), self.expected.client2.getId(), hosts[0].id))

	def test_createObjectOnBackend(self):
		self.backend.host_deleteObjects(self.expected.client2)
		
		self.expected.client2.setDescription(u'Test client 2')
		self.backend.host_createObjects(self.expected.client2)
		hosts = self.backend.host_getObjects( attributes = ['id', 'description'], id = self.expected.client2.getId() )
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].getId(), self.expected.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.expected.client2.getId(), self.expected.client2.getId(), hosts[0].id))
		self.assertEqual(hosts[0].getDescription(), u'Test client 2', u"Expected description of Client %s to be '%s', got: '%s'" % (self.expected.client2.getId(), 'Test client 2',hosts[0].getDescription()))
		
		
	def test_getConfigFromBackend(self):
		configs = self.backend.config_getObjects()
		self.assertEqual(len(configs),len(self.expected.configs), u"Expected %s config objects, but found '%s' on backend." % (len(configs),len(self.expected.configs)))
		
	def test_verifyConfigs(self):
		configs = self.backend.config_getObjects()

		ids = []
		for config in configs:
			ids.append(config.id)
		for config in self.expected.configs:
			self.assertIn(config.id, ids)
		
		for config in configs:
			for c in self.expected.configs:
				if (config.id == c.id):
					self.assertEqual(config, c, u"Expected config to be %s, got %s" % (c, config))
				
	def test_getConfigByDefaultValues(self):
		configs = self.backend.config_getObjects(defaultValues = self.expected.config2.defaultValues)
		self.assertEqual(len(configs), 1, u"Expected one config object, but found '%s' on backend." % len(configs))
		self.assertEqual( configs[0].getId(), self.expected.config2.getId(), u"Expected ID of config %s to be '%s', got: '%s'" % (self.expected.config2.getId(), self.expected.config2.getId(), configs[0].id))
		
	def test_getConfigByPossibleValues(self):
		configs = self.backend.config_getObjects(possibleValues = [])
		self.assertEqual(len(configs),len(self.expected.configs), u"Expected %s config objects, but found '%s' on backend." % (len(configs),len(self.expected.configs)))
		
		configs = self.backend.config_getObjects(possibleValues = self.expected.config1.possibleValues, defaultValues = self.expected.config1.defaultValues)
		self.assertEqual(len(configs), 1, u"Expected one config object, but found '%s' on backend." % len(configs))
		self.assertEqual( configs[0].getId(), self.expected.config1.getId(), u"Expected ID of config %s to be '%s', got: '%s'" % (self.expected.config1.getId(), self.expected.config1.getId(), configs[0].id))
		
		configs = self.backend.config_getObjects(possibleValues = self.expected.config5.possibleValues, defaultValues = self.expected.config5.defaultValues)
		self.assertEqual(len(configs), 2, u"Expected two config objects, but found '%s' on backend." % len(configs))
		for config in configs:
			self.assertIn(config.getId(), (self.expected.config3.id, self.expected.config5.id), u"'%s' not in '%s'" % (config.getId(), (self.expected.config3.id, self.expected.config5.id)))
		
	def test_getMultiValueConfigs(self):
		multiValueConfigNames = []
		for config in self.expected.configs:
			if config.getMultiValue():
				multiValueConfigNames.append(config.id)
		configs = self.backend.config_getObjects( attributes = [], multiValue = True )
		self.assertEqual(len(configs), len(multiValueConfigNames),  u"Expected %s config objects, but found '%s' on backend." % (len(multiValueConfigNames),len(configs)))
		for config in configs:
			self.assertIn(config.id, multiValueConfigNames, u"'%s' not in '%s'" % (config.id, multiValueConfigNames))
			
	def test_deleteConfigFromBackend(self):
		self.backend.config_deleteObjects(self.expected.config1)
		configs = self.backend.config_getObjects()
		self.assertEqual(len(configs), len(self.expected.configs) - 1, u"Expected %s config objects, but found '%s' on backend." % (len(self.expected.configs) - 1, len(configs)))
			
			
	def test_updateConfig(self):
		self.expected.config3.setDescription(u'Updated')
		self.expected.config3.setPossibleValues(['1', '2', '3'])
		self.expected.config3.setDefaultValues(['1', '2'])
		self.backend.config_updateObject(self.expected.config3)
		
		configs = self.backend.config_getObjects(description = u'Updated')
		self.assertEqual(len(configs), 1, u"Expected one config object, but found '%s' on backend." % len(configs))
		self.assertEqual(len(configs[0].getPossibleValues()), 3, u"Expected three possible values, but found '%s'." % len(configs[0].getPossibleValues()))
		for i in ['1', '2', '3']:
			self.assertIn(i, configs[0].getPossibleValues(), u"%s not in %s" % (i, configs[0].getPossibleValues()))
		self.assertEqual(len(configs[0].getDefaultValues()),2, u"Expected two possible values, but found '%s'." % len(configs[0].getDefaultValues()))
		for i in ['1', '2']:
			self.assertIn(i, configs[0].getDefaultValues(), u"%s not in %s" % (i, configs[0].getDefaultValues()))
			
	def test_getConfigStatesFromBackend(self):
		configStates = self.backend.configState_getObjects()
		for state in self.expected.configStates:
			self.assertIn(state, configStates, u"Expected config state %s on backend, but did not find it." % state)
		

	def test_getConfigStateByClientID(self):
		client1ConfigStates = []
		for configState in self.expected.configStates:
			if configState.getObjectId() == self.expected.client1.getId():
				client1ConfigStates.append(configState)
		configStates = self.backend.configState_getObjects( attributes = [], objectId = self.expected.client1.getId() )
		for configState in configStates:
			self.assertIn( configState.objectId , self.expected.client1.getId(), u"got: '%s', expected: '%s'" % (configState.objectId, self.expected.client1.getId()))
	

	def test_deleteConfigStateFromBackend(self):
		self.backend.configState_deleteObjects(self.expected.configState2)
		configStates = self.backend.configState_getObjects()
		self.assertNotIn(self.expected.configState2, configStates, "Expected config state %s to be deleted, but found it on backend." % self.expected.configState2.configId)

	def test_updateConfigState(self):
		self.expected.configState3.setValues([True])
		self.backend.configState_updateObject(self.expected.configState3)
		configStates = self.backend.configState_getObjects(objectId = self.expected.configState3.getObjectId(), configId = self.expected.configState3.getConfigId())
		self.assertEqual(len(configStates), 1, u"Expected one config state, but found '%s' on backend." % len(configStates))
		self.assertEqual(configStates[0].getValues(), [True], u"Expected config state %s do have values %s, got '%s'" % (configStates[0].getObjectId(), [True], configStates[0].getValues()))

	def test_selectConfigStateFromBackend(self):
		configStates = self.backend.configState_getObjects(objectId = self.expected.configState4.getObjectId(), configId = self.expected.configState4.getConfigId())
		self.assertEqual(len(configStates),1, u"Expected one config state, but found '%s' on backend." % len(configStates))
		self.assertEqual(configStates[0].getValues()[0], self.expected.configState4.getValues()[0], u"Expected config state %s to have values ==>>>%s<<<==, got ==>>>%s<<<==" \
					% (self.expected.configState4.getObjectId(), self.expected.configState4.getValues()[0],configStates[0].getValues()[0]))
		

	def test_getProductsFromBackend(self):
		products = self.backend.product_getObjects()
		self.assertEqual(len(products), len(self.expected.products), u"Expected %s products, but found '%s' on backend." % (len(self.expected.products), len(products)))
		
	def test_getProductsByType(self):
		products = self.backend.product_getObjects(type = 'Product')
		self.assertEqual(len(products), len(self.expected.products), u"Expected %s products, but found '%s' on backend." % (len(self.expected.products), len(products)))

	def test_verifyProducts(self):
		products = self.backend.product_getObjects(type = self.expected.localbootProducts[0].getType())
		self.assertEqual(len(products),len(self.expected.localbootProducts), u"Expected %s products, but found '%s' on backend." % (len(self.expected.localbootProducts), len(products)))
		ids = []
		for product in products:
			ids.append(product.getId())
		for product in self.expected.localbootProducts:
			self.assertIn(product.id, ids, u"'%s' not in '%s'" % (product.id, ids))
		
		for product in products:
			#logger.debug(product)
			for p in self.expected.products:
				if (product.id == p.id) and (product.productVersion == p.productVersion) and (product.packageVersion == p.packageVersion):
					product = product.toHash()
					p = p.toHash()
					for (attribute, value) in p.items():
						if (attribute == 'productClassIds'):
							#logger.warning(u"Skipping productClassIds attribute test!!!")
							continue
						if not value is None:
							
							if type(value) is list:
								for v in value:
									self.assertIn(v, product[attribute], u"'%s' not in '%s'" % (v, product[attribute]))
							else:
								self.assertEqual( value, product[attribute], u"Value for attribute %s of product %s is: '%s', expected: '%s'" % (attribute, product['id'], product[attribute], value ))
					break
				
	def test_updateProducts(self):
		self.expected.product2.setName(u'Product 2 updated')
		self.expected.product2.setPriority(60)
		products = self.backend.product_updateObject(self.expected.product2)
		products = self.backend.product_getObjects( attributes = ['name', 'priority'], id = 'product2' )
		self.assertEqual(len(products), 1, u"Expected one product, but got '%s' from backend." % len(products))
		self.assertEqual(products[0].getName(), u'Product 2 updated', u"Expected product name to be '%s', but got '%s'." % (u'Product 2 updated',products[0].getName()))
		self.assertEqual(products[0].getPriority(), 60, u"Expected product priority to be %s but got %s'" % (products[0].getPriority(),60))
	
	def test_getProductPropertiesFromBackend(self):
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.expected.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.expected.productProperties),len(productProperties)))
		
	def test_verifyProductProperties(self):

		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.expected.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.expected.productProperties), len(productProperties)))
		for productProperty in productProperties:
			#logger.debug(productProperty)
			for p in self.expected.productProperties:
				if (productProperty.productId == p.productId)           and (productProperty.propertyId == p.propertyId) and \
				   (productProperty.productVersion == p.productVersion) and (productProperty.packageVersion == p.packageVersion):
					productProperty = productProperty.toHash()
					p = p.toHash()
					for (attribute, value) in p.items():
						if not value is None:
							if type(value) is list:
								for v in value:
									assert v in productProperty[attribute], u"'%s' not in '%s'" % (v, productProperty[attribute])
							else:
								assert value == productProperty[attribute], u"got: '%s', expected: '%s'" % (productProperty[attribute], value)
					break
		

	def test_updateProductProperty(self):
		self.expected.productProperty2.setDescription(u'updatedfortest')
		self.backend.productProperty_updateObject(self.expected.productProperty2)
		productProperties = self.backend.productProperty_getObjects( attributes = [],\
			description = u'updatedfortest')
		
		self.assertEqual(len(productProperties), 1, u"Expected one product property object, but got %s from backend" % len(productProperties))
		self.assertEqual(productProperties[0].getDescription(), u'updatedfortest', u"Expected description of product property %s to be '%s', got '%s'" % (productProperties[0].getProductId(), u'updatedfortest',productProperties[0].getDescription()))
		
		
	def test_deleteProductPropert(self):
		self.backend.productProperty_deleteObjects(self.expected.productProperty2)
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.expected.productProperties) - 1, u"Expected %s product properties, but got %s from backend." % (len(self.expected.productProperties) - 1, len(productProperties)))

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
		
	def test_getProductOnDepotsFromBackend(self):
		productOnDepots = self.backend.productOnDepot_getObjects( attributes = ['productId'] )
		self.assertEqual(len(productOnDepots), len(self.expected.productOnDepots), u"Expected %s products on depots, but got %s from backend." % (len(self.expected.productOnDepots), len(productOnDepots)))
		

	def test_deleteProductOnDepot(self):
		self.backend.productOnDepot_deleteObjects(self.expected.productOnDepot1)
		productOnDepots = self.backend.productOnDepot_getObjects()
		self.assertEqual(len(productOnDepots), len(self.expected.productOnDepots) - 1, u"Expected %s products on depots, but got %s from backend." % (len(self.expected.productOnDepots) - 1, len(productOnDepots)))


	def test_createDuplicateProductsOnDepots(self):
		self.backend.productOnDepot_createObjects(self.expected.productOnDepots)
		productOnDepots = self.backend.productOnDepot_getObjects()
		self.assertEqual(len(productOnDepots),len(self.expected.productOnDepots), u"Expected %s products on depots, but got %s from backend." % (len(self.expected.productOnDepots), len(productOnDepots)))
