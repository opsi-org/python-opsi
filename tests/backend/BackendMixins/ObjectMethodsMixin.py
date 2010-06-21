from OPSI.Object import *

class ObjectMethodsMixin(object):


	def test_getHostsHostOnBackend(self):
		hosts = self.backend.host_getObjects()
		self.assertEqual(len(hosts), len(self.hosts), u"Expected '%s' hosts, but found '%s' on backend." % (len(self.hosts), len(hosts)))

	def test_verifyHosts(self):
		hosts = self.backend.host_getObjects()
		for host in hosts:
			self.assertIsNotNone(host.getOpsiHostKey(), u"Host key for host '%s': '%s' is not expected." % (host.getId(), host.getOpsiHostKey()))
			for h in self.hosts:
				if (host.id == h.id):
					host = host.toHash()
					h = h.toHash()
					for (attribute, value) in h.items():
						if not value is None:
							if type(value) is list:
								for v in value:
									self.assertIn(v, host[attribute], u"'%s' not in '%s'" % (v, host[attribute]))
							else:
								self.assertEqual(value, host[attribute], u"Value for attribute %s for host %s is: '%s', expected: '%s'" % (attribute, host['id'], value, host[attribute]))
					break

	def test_createDeposserverOnBackend(self):
		hosts = self.backend.host_getObjects(type = 'OpsiConfigserver')
		self.assertEqual(len(hosts), len(self.configservers), u"Expected '%s' Depotserver, but found '%s' on backend." % (len(self.hosts), len(hosts)))

	def test_clientsOnBackend(self):
		hosts = self.backend.host_getObjects( type = [ self.clients[0].getType() ] )
		self.assertEqual( len(hosts), len(self.clients), u"Expected 2 Cients, but found '%s' on backend." %  len(hosts))
		ids = []
		for host in hosts:
			ids.append(host.getId())
		for client in self.clients:
			self.assertIn(client.getId(), ids, u"Client '%s' not found in '%s'" % (client.getId(), ids))

	def test_selectClientsOnBackend(self):
		hosts = self.backend.host_getObjects( id = [ self.client1.getId(), self.client2.getId() ] )
		self.assertEqual(len(hosts), 2, u"Expected 2 Cients, but found '%s' on backend." %  len(hosts))

		ids = []
		for host in hosts:
			ids.append(host.getId())
		self.assertIn(self.client1.getId(),ids, u"Client '%s' not found in '%s'" % (self.client1.getId(), ids))
		self.assertIn(self.client2.getId(),ids, u"Client '%s' not found in '%s'" % (self.client1.getId(), ids))
		
	
	def test_hostAttributes(self):
		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = [ None ] )
		count = 0
		for host in self.hosts:
			if host.getIpAddress() is None:
				count += 1
		
		self.assertEqual(len(hosts), count)
		for host in hosts:
			self.assertIsNone(host.getIpAddress(), u"Expected IP address of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getIpAddress()))
			self.assertIsNone(host.getInventoryNumber(), u"Expected inventory number of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getInventoryNumber()))
			self.assertIsNotNone(host.getNotes(), u"Expected notes of host %s not to be None" % (host.getId()))
			self.assertIsNotNone(host.getDescription(), u"Expected description of host %s not to be None" % (host.getId()))

		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = None )
		self.assertEqual(len(hosts), len(self.hosts), u"Expected '%s' hosts, but found '%s'" % (len(self.hosts), len(hosts)))
		
		for host in hosts:
			self.assertIsNone(host.getIpAddress(), u"Expected IP address of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getIpAddress()))
			self.assertIsNone(host.getInventoryNumber(), u"Expected inventory number of host %s to be: '%s', got: '%s'" % (host.getId(), None, host.getInventoryNumber()))

	def test_selectClientsByDescription(self):
		#hosts = self.backend.host_getObjects( id = [ self.client1.getId(), self.client2.getId() ], description = self.client2.getDescription() )   # TODO: Better?
		hosts = self.backend.host_getObjects( type = [ self.clients[0].getType() ], description = self.client2.getDescription() )
		
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].id, self.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.client2.getId(), self.client2.getId(), hosts[0].id))
		self.assertEqual(hosts[0].description, self.client2.getDescription(), u"Expected description of client %s to be '%s', got: '%s'" % (self.client2.getId(), self.client2.getDescription(), hosts[0].description))
		
		
	def test_selectClientById(self):
		hosts = self.backend.host_getObjects(attributes=['id', 'description'], id = self.client1.getId())
		
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].id, self.client1.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.client1.getId(), self.client1.getId(), hosts[0].id))
		self.assertEqual(hosts[0].description, self.client1.getDescription(), u"Expected description of client %s to be '%s', got: '%s'" % (self.client1.getId(), self.client1.getDescription(), hosts[0].description))
		
		
	def test_deleteClientFromBackend(self):
		
		self.backend.host_deleteObjects(self.client2)
		
		hosts = self.backend.host_getObjects( type = [ self.client1.getType() ] )
		self.assertEqual(len(hosts), len(self.clients) - 1, u"Expected %s Clients but found %s on backend." % (len(self.clients) - 1, len(hosts)))
		
		ids = []
		for host in hosts:
			ids.append(host.getId())
			
		self.assertNotIn(self.client2.getId(), ids, "Found Client %s in %s, expected id to be deleted." %(self.client2.getId(), ids))
		
		del(self.clients[self.clients.index(self.client2)])
		for client in self.clients:
			self.assertIn(client.getId(), ids, u"'%s' not in '%s'" % (client.getId(), ids))
			
	def test_updateObjectOnBackend(self):
		self.client2.setDescription('Updated')
		self.backend.host_updateObject(self.client2)
		hosts = self.backend.host_getObjects( description = 'Updated' )
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].getId(), self.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.client2.getId(), self.client2.getId(), hosts[0].id))

	def test_createObjectOnBackend(self):
		self.backend.host_deleteObjects(self.client2)
		
		self.client2.setDescription(u'Test client 2')
		self.backend.host_createObjects(self.client2)
		hosts = self.backend.host_getObjects( attributes = ['id', 'description'], id = self.client2.getId() )
		self.assertEqual(len(hosts), 1, u"Expected one Cient, but found '%s' on backend." %  len(hosts))
		self.assertEqual(hosts[0].getId(), self.client2.getId(), u"Expected ID of client %s to be '%s', got: '%s'" % (self.client2.getId(), self.client2.getId(), hosts[0].id))
		self.assertEqual(hosts[0].getDescription(), u'Test client 2', u"Expected description of Client %s to be '%s', got: '%s'" % (self.client2.getId(), 'Test client 2',hosts[0].getDescription()))
		
		
	def test_getConfigFromBackend(self):
		configs = self.backend.config_getObjects()
		self.assertEqual(len(configs),len(self.configs), u"Expected %s config objects, but found '%s' on backend." % (len(configs),len(self.configs)))
		
	def test_verifyConfigs(self):
		configs = self.backend.config_getObjects()

		ids = []
		for config in configs:
			ids.append(config.id)
		for config in self.configs:
			self.assertIn(config.id, ids)
		
		for config in configs:
			for c in self.configs:
				if (config.id == c.id):
					config = config.toHash()
					c = c.toHash()
					for (attribute, value) in c.items():
						if not value is None:
							if type(value) is list:
								for v in value:
									self.assertIn(v,config[attribute], u"'%s' not in '%s'" % (v, config[attribute]))
							else:
								self.assertEqual(value,config[attribute], u"Value for attribute %s of config %s is: '%s', expected: '%s'" % (attribute, config['id'], value, config[attribute]))
					break
				
	def test_getConfigByDefaultValues(self):
		configs = self.backend.config_getObjects(defaultValues = self.config2.defaultValues)
		self.assertEqual(len(configs), 1, u"Expected one config object, but found '%s' on backend." % len(configs))
		self.assertEqual( configs[0].getId(), self.config2.getId(), u"Expected ID of config %s to be '%s', got: '%s'" % (self.config2.getId(), self.config2.getId(), configs[0].id))
		
	def test_getConfigByPossibleValues(self):
		configs = self.backend.config_getObjects(possibleValues = [])
		self.assertEqual(len(configs),len(self.configs), u"Expected %s config objects, but found '%s' on backend." % (len(configs),len(self.configs)))
		
		configs = self.backend.config_getObjects(possibleValues = self.config1.possibleValues, defaultValues = self.config1.defaultValues)
		self.assertEqual(len(configs), 1, u"Expected one config object, but found '%s' on backend." % len(configs))
		self.assertEqual( configs[0].getId(), self.config1.getId(), u"Expected ID of config %s to be '%s', got: '%s'" % (self.config1.getId(), self.config1.getId(), configs[0].id))
		
		configs = self.backend.config_getObjects(possibleValues = self.config5.possibleValues, defaultValues = self.config5.defaultValues)
		self.assertEqual(len(configs), 2, u"Expected two config objects, but found '%s' on backend." % len(configs))
		for config in configs:
			self.assertIn(config.getId(), (self.config3.id, self.config5.id), u"'%s' not in '%s'" % (config.getId(), (self.config3.id, self.config5.id)))
		
	def test_getMultiValueConfigs(self):
		multiValueConfigNames = []
		for config in self.configs:
			if config.getMultiValue():
				multiValueConfigNames.append(config.id)
		configs = self.backend.config_getObjects( attributes = [], multiValue = True )
		self.assertEqual(len(configs), len(multiValueConfigNames),  u"Expected %s config objects, but found '%s' on backend." % (len(multiValueConfigNames),len(configs)))
		for config in configs:
			self.assertIn(config.id, multiValueConfigNames, u"'%s' not in '%s'" % (config.id, multiValueConfigNames))
			
	def test_deleteConfigFromBackend(self):
		self.backend.config_deleteObjects(self.config1)
		configs = self.backend.config_getObjects()
		self.assertEqual(len(configs), len(self.configs) - 1, u"Expected %s config objects, but found '%s' on backend." % (len(self.configs) - 1, len(configs)))
			
			
	def test_updateConfig(self):
		self.config3.setDescription(u'Updated')
		self.config3.setPossibleValues(['1', '2', '3'])
		self.config3.setDefaultValues(['1', '2'])
		self.backend.config_updateObject(self.config3)
		
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
		self.assertEqual(len(configStates), len(self.configStates), u"Expected %s config states, but found '%s' on backend." % (len(self.configStates), configStates))
		

	def test_getConfigStateByClientID(self):
		client1ConfigStates = []
		for configState in self.configStates:
			if configState.getObjectId() == self.client1.getId():
				client1ConfigStates.append(configState)
		configStates = self.backend.configState_getObjects( attributes = [], objectId = self.client1.getId() )
		for configState in configStates:
			self.assertIn( configState.objectId , self.client1.getId(), u"got: '%s', expected: '%s'" % (configState.objectId, self.client1.getId()))
	

	def test_deleteConfigStateFromBackend(self):
		self.backend.configState_deleteObjects(self.configState2)
		configStates = self.backend.configState_getObjects()
		self.assertEqual(len(configStates), len(self.configStates)-1, u"Expected %s config states, but found '%s' on backend." % (len(self.configStates)-1, len(configStates)))
		for configState in configStates:
			self.failIf(configState.objectId == self.configState2.objectId and configState.configId == self.configState2.configId)
		
	def test_updateConfigState(self):
		self.configState3.setValues([True])
		self.backend.configState_updateObject(self.configState3)
		configStates = self.backend.configState_getObjects(objectId = self.configState3.getObjectId(), configId = self.configState3.getConfigId())
		self.assertEqual(len(configStates), 1, u"Expected one config state, but found '%s' on backend." % len(configStates))
		self.assertListEqual(configStates[0].getValues(), [True], u"Expected config state %s do have values %s, got '%s'" % (configStates[0].getObjectId(), [True], configStates[0].getValues()))

	def test_selectConfigStateFromBackend(self):
		configStates = self.backend.configState_getObjects(objectId = self.configState4.getObjectId(), configId = self.configState4.getConfigId())
		self.assertEqual(len(configStates),1, u"Expected one config state, but found '%s' on backend." % len(configStates))
		self.assertEqual(configStates[0].getValues()[0], self.configState4.getValues()[0], u"Expected config state %s do have values %s, got '%s'" % (self.configState4.getObjectId(), self.configState4.getValues()[0],configStates[0].getValues()[0]))
		

	def test_getProductsFromBackend(self):
		products = self.backend.product_getObjects()
		self.assertEqual(len(products), len(self.products), u"Expected %s products, but found '%s' on backend." % (len(self.products), len(products)))
		
	def test_getProductsByType(self):
		products = self.backend.product_getObjects(type = 'Product')
		self.assertEqual(len(products), len(self.products), u"Expected %s products, but found '%s' on backend." % (len(self.products), len(products)))

	def test_verifyProducts(self):
		products = self.backend.product_getObjects(type = self.localbootProducts[0].getType())
		self.assertEqual(len(products),len(self.localbootProducts), u"Expected %s products, but found '%s' on backend." % (len(self.localbootProducts), len(products)))
		ids = []
		for product in products:
			ids.append(product.getId())
		for product in self.localbootProducts:
			self.assertIn(product.id, ids, u"'%s' not in '%s'" % (product.id, ids))
		
		for product in products:
			#logger.debug(product)
			for p in self.products:
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
		self.product2.setName(u'Product 2 updated')
		self.product2.setPriority(60)
		products = self.backend.product_updateObject(self.product2)
		products = self.backend.product_getObjects( attributes = ['name', 'priority'], id = 'product2' )
		self.assertEqual(len(products), 1, u"Expected one product, but got '%s' from backend." % len(products))
		self.assertEqual(products[0].getName(), u'Product 2 updated', u"Expected product name to be '%s', but got '%s'." % (u'Product 2 updated',products[0].getName()))
		self.assertEqual(products[0].getPriority(), 60, u"Expected product priority to be %s but got %s'" % (products[0].getPriority(),60))
	
	def test_getProductPropertiesFromBackend(self):
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.productProperties),len(productProperties)))
		
	def test_verifyProductProperties(self):

		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.productProperties), len(productProperties)))
		for productProperty in productProperties:
			#logger.debug(productProperty)
			for p in self.productProperties:
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
		self.productProperty2.setDescription(u'updatedfortest')
		self.backend.productProperty_updateObject(self.productProperty2)
		productProperties = self.backend.productProperty_getObjects( attributes = [],\
			description = u'updatedfortest')
		
		self.assertEqual(len(productProperties), 1, u"Expected one product property object, but got %s from backend" % len(productProperties))
		self.assertEqual(productProperties[0].getDescription(), u'updatedfortest', u"Expected description of product property %s to be '%s', got '%s'" % (productProperties[0].getProductId(), u'updatedfortest',productProperties[0].getDescription()))
		
		
	def test_deleteProductPropert(self):
		self.backend.productProperty_deleteObjects(self.productProperty2)
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.productProperties) - 1, u"Expected %s product properties, but got %s from backend." % (len(self.productProperties) - 1, len(productProperties)))

	def test_createDuplicateProductProperies(self):
		self.backend.productProperty_createObjects([self.productProperty4, self.productProperty1, self.productProperty4, self.productProperty4, self.productProperty4])
		productProperties = self.backend.productProperty_getObjects()
		self.assertEqual(len(productProperties), len(self.productProperties), u"Expected %s product properties, but got %s from backend." % (len(self.productProperties), len(productProperties)))

	def test_getProductDependenciesFromBackend(self):
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies),len(self.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.productDependencies), len(productDependencies)))
		
	def test_updateProductDependencies(self):
		self.productDependency2.requiredProductVersion = "2.0"
		self.productDependency2.requirementType = None
		self.backend.productDependency_updateObject(self.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		
		self.assertEqual(len(productDependencies), len(self.productDependencies), u"Expected %s product dependencies, but got %s from backend." % (len(self.productDependencies), len(productDependencies)))
		for productDependency in productDependencies:
			if productDependency.getIdent() == self.productDependency2.getIdent():
				self.assertEqual(productDependency.getRequiredProductVersion(), u"2.0", u"Expected required version to be %s but got %s." % (u"2.0", productDependency.getRequiredProductVersion()))
				self.assertEqual(productDependency.getRequirementType(),'after', u"Expected requirement type to be '%s' but got '%s.'" % ('after',productDependency.getRequirementType()))

	def test_deleteProductDependency(self):
		self.backend.productDependency_deleteObjects(self.productDependency2)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.productDependencies) - 1, u"Expected %s product dependencies but got %s from backend." % (len(self.productDependencies) - 1, len(productDependencies)))
		
	def test_createDuplucateProductDependency(self):
		self.backend.productDependency_createObjects(self.productDependencies)
		productDependencies = self.backend.productDependency_getObjects()
		self.assertEqual(len(productDependencies), len(self.productDependencies), u"Expected %s product dependencies but got %s from backend." % (len(self.productDependencies), len(productDependencies)))
	
	def test_getProductOnDepotsFromBackend(self):
		productOnDepots = self.backend.productOnDepot_getObjects( attributes = ['productId'] )
		self.assertEqual(len(productOnDepots), len(self.productOnDepots), u"Expected %s products on depots, but got %s from backend." % (len(self.productOnDepots), len(productOnDepots)))
		

	def test_deleteProductOnDepot(self):
		self.backend.productOnDepot_deleteObjects(self.productOnDepot1)
		productOnDepots = self.backend.productOnDepot_getObjects()
		self.assertEqual(len(productOnDepots), len(self.productOnDepots) - 1, u"Expected %s products on depots, but got %s from backend." % (len(self.productOnDepots) - 1, len(productOnDepots)))


	def test_createDuplicateProductsOnDepots(self):
		self.backend.productOnDepot_createObjects(self.productOnDepots)
		productOnDepots = self.backend.productOnDepot_getObjects()
		self.assertEqual(len(productOnDepots),len(self.productOnDepots), u"Expected %s products on depots, but got %s from backend." % (len(self.productOnDepots), len(productOnDepots)))

	def test_getProductsOnClientsFromBackend(self):
		productOnClients = self.backend.productOnClient_getObjects()
		self.assertEqual(len(productOnClients), len(self.productOnClients), u"Expected %s products on clients, but got %s from backend." % (len(self.productOnClients), len(productOnClients)))
		
	def test_selectProductOnClient(self):
		client1ProductOnClients = []
		for productOnClient in self.productOnClients:
			if (productOnClient.getClientId() == self.client1.id):
				client1ProductOnClients.append(productOnClient)
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.client1.getId())
		for productOnClient in productOnClients:
			self.assertEqual(productOnClient.getClientId(), self.client1.getId(), u"Found product %s on client %s but did not expect it." % (productOnClient.getProductId(), self.client1.getId()))

	def test_selectProductOnClientById(self):
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.client1.getId(), productId = self.product2.getId())
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		self.assertEqual(productOnClients[0].getProductId(), self.product2.getId(), u"Expected product %s on client but got %s" % (self.product2.getId(), productOnClients[0].getProductId()))
		self.assertEqual(productOnClients[0].getClientId(), self.client1.getId(), u"Found product %s on client %s but did not expect it." % (productOnClients[0].getProductId(), self.client1.getId()))

	def test_updateProductsOnClients(self):
		self.productOnClient2.setTargetConfiguration('forbidden')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(targetConfiguration = 'forbidden')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setInstallationStatus('unknown')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(installationStatus = 'unknown')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setActionRequest('custom')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(actionRequest = 'custom')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setLastAction('once')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(lastAction = 'once')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setActionProgress('aUniqueProgress')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(actionProgress = 'aUniqueProgress')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setActionResult('failed')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(actionResult = 'failed')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setInstallationStatus('installed')
		self.productOnClient2.setProductVersion('777777')
		self.productOnClient2.setPackageVersion('1')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(productVersion = '777777')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setPackageVersion('999999')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(packageVersion = '999999')
		self.assertEqual(len(productOnClients), 1, u"Expected one product on client, but found %s on backend." % (len(productOnClients)))
		
		self.productOnClient2.setModificationTime('2010-01-01 05:55:55')
		self.backend.productOnClient_updateObject(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects(modificationTime = '2010-01-01 05:55:55')
		# You cant set modification time on update!
		self.assertEqual(len(productOnClients), 0, u"Modification time cannot be set on update, but backend found %s products on clients." % (len(productOnClients)))
		
		
	def test_deleteProductOnClient(self):
		self.backend.productOnClient_deleteObjects(self.productOnClient2)
		productOnClients = self.backend.productOnClient_getObjects()
		self.assertEqual(len(productOnClients), len(self.productOnClients) - 1, u"Expected %s products on clients, but got %s from backend." % (len(self.productOnClients) - 1, len(productOnClients)))
		
	
	def test_insertPropertyState(self):
		with self.assertRaises(Exception):
			pps0 = ProductPropertyState(
						productId  = self.productProperty1.getProductId(),
						propertyId = self.productProperty1.getPropertyId(),
						objectId   = 'kaputtesdepot.dom.local'
						)
			self.backend.productPropertyState_insertObject(pps0)

	def test_getProductPropertyStatesFromBackend(self):
		productPropertyStates = self.backend.productPropertyState_getObjects()
		self.assertEqual(len(productPropertyStates), len(self.productPropertyStates), u"Expected %s product property states, but got %s from backend." % (len(self.productPropertyStates), len(productPropertyStates)))
		
	def test_deleteProductPropertyState(self):
		self.backend.productPropertyState_deleteObjects(self.productPropertyState2)
		productPropertyStates = self.backend.productPropertyState_getObjects()
		self.assertEqual(len(productPropertyStates), len(self.productPropertyStates) - 1, u"Expected %s product property states, but got %s from backend." % (len(self.productPropertyStates)-1, len(productPropertyStates)))
		
	def test_insertProductPropertyState(self):
		self.backend.productPropertyState_deleteObjects(self.productPropertyState2)
		
		self.backend.productPropertyState_insertObject(self.productPropertyState2)
		productPropertyStates = self.backend.productPropertyState_getObjects()
		self.assertEqual(len(productPropertyStates), len(self.productPropertyStates), u"Expected %s product property states, but got %s from backend." % (len(self.productPropertyStates), len(productPropertyStates)))
		
	def test_getGroupsFromBackend(self):
		groups = self.backend.group_getObjects()
		self.assertEqual(len(groups), len(self.groups), u"Expected %s groups, but found '%s' on backend" % (len(self.groups), len(groups)))
		
	def test_selectGroupByDescrition(self):
		groups = self.backend.group_getObjects(description = self.groups[0].description)
		self.assertEqual(len(groups), 1, u"Expected one group, but got '%s' from backend" % len(groups))
		self.assertEqual(groups[0].getId(), self.groups[0].id, u"Expected group to be %s, but got '%s' from backend" % (self.groups[0].id, groups[0].getId()))
		
	def test_updateGroup(self):
		self.group1.setDescription(u'new description')
		self.backend.group_updateObject(self.group1)
		
		groups = self.backend.group_getObjects(description = self.group1.description)
		self.assertEqual(len(groups), 1, u"Expected one group, but got '%s' from backend" % len(groups))
		self.assertEqual(groups[0].getDescription(), u'new description', u"Expected description of group %s to be %s, got %s" % (self.group1.id, 'new description', groups[0].getDescription()))
		
	def test_deleteGroup(self):
		self.backend.group_deleteObjects(self.group1)
		groups = self.backend.group_getObjects()
		self.assertEqual(len(groups), len(self.groups)-1, u"Expected %s groups, but found '%s' on backend" % (len(self.groups)-1, len(groups)))
		
	def test_createDuplicateGroup(self):
		self.backend.group_createObjects(self.group1)
		groups = self.backend.group_getObjects()
		self.assertEqual(len(groups), len(self.groups), u"Expected %s groups, but found '%s' on backend" % (len(self.groups), len(groups)))
		
	def test_getObjectsToGroupFromBackend(self):
		objectToGroups = self.backend.objectToGroup_getObjects()
		self.assertEqual(len(objectToGroups), len(self.objectToGroups), u"Expected %s objects to group, but found '%s' on backend" % (len(self.objectToGroups), len(objectToGroups)))
		
	def test_selectObjectToGroupById(self):
		client1ObjectToGroups = []
		client2ObjectToGroups = []
		for objectToGroup in self.objectToGroups:
			if (objectToGroup.objectId == self.client1.getId()):
				client1ObjectToGroups.append(objectToGroup)
			if (objectToGroup.objectId == self.client2.getId()):
				client2ObjectToGroups.append(objectToGroup)
		objectToGroups = self.backend.objectToGroup_getObjects(objectId = self.client1.getId())
		self.assertEqual(len(objectToGroups), len(client1ObjectToGroups), u"Expected %s objects to group %s, but found %s on backend." % (len(client1ObjectToGroups), self.client1.getId(), len(objectToGroups)))
		for objectToGroup in objectToGroups:
			self.assertEqual(objectToGroup.objectId, self.client1.id, u"Expected object to be '%s', got: '%s'" % (self.client1.id, objectToGroup.objectId))
		
		objectToGroups = self.backend.objectToGroup_getObjects(objectId = self.client2.getId())
		self.assertEqual(len(objectToGroups), len(client2ObjectToGroups), u"Expected %s objects to group %s, but found %s on backend." % (len(client2ObjectToGroups), self.client2.getId(), len(objectToGroups)))
		for objectToGroup in objectToGroups:
			self.assertEqual(objectToGroup.objectId, self.client2.id, u"Expected object to be '%s', got: '%s'" % (self.client2.id, objectToGroup.objectId))
		

	def test_deleteObjectToGroup(self):
		self.backend.objectToGroup_deleteObjects(self.objectToGroup3)
		objectToGroups = self.backend.objectToGroup_getObjects()
		self.assertEqual(len(objectToGroups), len(self.objectToGroups)-1, u"Expected %s objects to group, but found '%s' on backend" % (len(self.objectToGroups)-1, len(objectToGroups)))
		
	def test_createDuplicateObjectToGroup(self):
		self.backend.objectToGroup_createObjects(self.objectToGroup3)
		objectToGroups = self.backend.objectToGroup_getObjects()
		self.assertEqual(len(objectToGroups), len(self.objectToGroups), u"Expected %s objects to group, but found '%s' on backend" % (len(self.objectToGroups), len(objectToGroups)))


		
		
		



######################### OLD STUFF ##########################################
		
#		print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
#		configs = self.backend.config_getObjects()
#		print "#######################"
#		for config in configs:
#			if config.id == u'opsi-linux-bootimage.cmdline.bool': #config2
#				print config
#		print "#######################"
#		print self.config2.getDefaultValues(), "getDefaultValues()" #[True]
#		print self.config2.defaultValues, "defaultValues" #[True]
#		print "#######################"
#		
#		configs = self.backend.config_getObjects(defaultValues = self.config2.defaultValues)
#		
#		print "#######################"
#		print self.config2.getDefaultValues(), "getDefaultValues()" #[u'True']
#		print self.config2.defaultValues, "defaultValues" #[u'True']
#		
#		print "#######################"
#		configs = self.backend.config_getObjects()
#		for config in configs:
#			if config.id == u'opsi-linux-bootimage.cmdline.bool': #config2
#				print config
#		print "#######################"
#		print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
#		
#----------

		

#		
#		#cannot be updated ...
#		groups = self.backend.group_getObjects(description = self.group1.description)
#		assert len(groups) == 1
#		assert groups[0].getDescription() == 'new description'
		