#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time

from OPSI.Logger import *
from OPSI.Backend.Object import *

logger = Logger()

someTypes = (
	1,
	None,
	True,
	time.localtime(),
	u'unicode string',
	u'utf-8 string: äöüß€®'.encode('utf-8'),
	u'windows-1258 string: äöüß€'.encode('windows-1258'),
	u'utf-16 string: äöüß€'.encode('utf-16'),
	u'latin1 string: äöüß'.encode('latin-1')
)

class BackendTest(object):
	def __init__(self, backend):
		self.backend = backend
		
		# Hosts
		self.hosts = []
		
		self.configserver1 = OpsiConfigserver(
			id                  = 'config1.uib.local',
			opsiHostKey         = '71234545689056789012123678901234',
			depotLocalUrl       = 'file:///opt/pcbin/install',
			depotRemoteUrl      = 'smb://config1/opt_pcbin',
			repositoryLocalUrl  = 'file:///var/lib/opsi/products',
			repositoryRemoteUrl = 'webdavs://config1.uib.local:4447/products',
			description         = 'The configserver',
			notes               = 'Config 1',
			hardwareAddress     = None,
			ipAddress           = None,
			inventoryNumber     = '00000000001',
			network             = '192.168.1.0/24',
			maxBandwidth        = 10000
		)
		self.configservers = [ self.configserver1 ]
		self.hosts.extend(self.configservers)
		
		self.depotserver1 = OpsiDepotserver(
			id                  = 'depotserver1.uib.local',
			opsiHostKey         = '19012334567845645678901232789012',
			depotLocalUrl       = 'file:///opt/pcbin/install',
			depotRemoteUrl      = 'smb://depotserver1.uib.local/opt_pcbin',
			repositoryLocalUrl  = 'file:///var/lib/opsi/products',
			repositoryRemoteUrl = 'webdavs://depotserver1.uib.local:4447/products',
			description         = 'A depot',
			notes               = 'D€pot 1',
			hardwareAddress     = None,
			ipAddress           = None,
			network             = '192.168.2.0/24',
			maxBandwidth        = 10000
		)
		self.depotservers = [ self.depotserver1 ]
		self.hosts.extend(self.depotservers)
		
		self.client1 = OpsiClient(
			id              = 'client1.uib.local',
			description     = 'Test client 1',
			notes           = 'Notes ...',
			hardwareAddress = '00:01:02:03:04:05',
			ipAddress       = '192.168.1.100',
			lastSeen        = '2009-01-01 00:00:00',
			opsiHostKey     = '45656789789012789012345612340123',
			inventoryNumber = None
		)
		
		self.client2 = OpsiClient(
			id              = 'client2.uib.local',
			description     = 'Test client 2',
			hardwareAddress = '00-ff0aa3:0b-B5',
			opsiHostKey     = '59051234345678890121678901223467',
			inventoryNumber = '00000000002'
		)
		
		self.client3 = OpsiClient(
			id              = 'client3.uib.local',
			description     = 'Test client 3',
			inventoryNumber = 'XYZABC_1200292'
		)
		self.clients = [ self.client1, self.client2, self.client3 ]
		self.hosts.extend(self.clients)
		
		# Configs
		self.config1 = UnicodeConfig(
			id             = u'opsi-linux-bootimage.cmdline.reboot',
			description    = (u'Some sting üöä?').encode('latin-1'),
			possibleValues = ['w', 'c', 'b', 'h', 'b,c'],
			defaultValues  = ['b,c']
		)
		
		self.config2 = BoolConfig(
			id            = u'opsi-linux-bootimage.cmdline.bool',
			description   = 'Bool?',
			defaultValues = 'on'
		)
		
		self.config3 = UnicodeConfig(
			id             = u'some.products',
			description    = u'Install this products',
			possibleValues = ['product1', 'product2', 'product3', 'product4'],
			defaultValues  = ['product1', 'product3']
		)
		
		self.config4 = UnicodeConfig(
			id             = u'network.depot_server.depot_id',
			description    = u'Depotserver to use',
			possibleValues = [],
			defaultValues  = [ self.depotserver1.id ]
		)
		
		self.configs = [ self.config1, self.config2, self.config3, self.config4 ]
		
		# ConfigStates
		self.configState1 = ConfigState(
			configId = self.config1.getId(),
			objectId = self.client1.getId(),
			values   = ['w']
		)
		
		self.configState2 = ConfigState(
			configId = self.config2.getId(),
			objectId = self.client1.getId(),
			values   = [False]
		)
		
		self.configState3 = ConfigState(
			configId = self.config2.getId(),
			objectId = self.client2.getId(),
			values   = [False]
		)
		self.configStates = [ self.configState1, self.configState2, self.configState3 ]
		
		# Products
		self.products = []
		self.product1 = NetbootProduct(
			id                 = 'product1',
			name               = u'Product 1',
			productVersion     = '1.0',
			packageVersion     = 1,
			licenseRequired    = True,
			setupScript        = "setup.py",
			uninstallScript    = None,
			updateScript       = "update.py",
			alwaysScript       = None,
			onceScript         = None,
			priority           = '100',
			description        = "Nothing",
			advice             = u"No advice",
			productClassNames  = ['class1'],
			windowsSoftwareIds = ['{be21bd07-eb19-44e4-893a-fa4e44e5f806}', 'product1'],
			pxeConfigTemplate  = 'special'
		)
		self.netbootProducts = [ self.product1 ]
		self.products.extend(self.netbootProducts)
		
		self.product2 = LocalbootProduct(
			id                 = 'product2',
			name               = u'Product 2',
			productVersion     = '2.0',
			packageVersion     = 'test',
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = u"uninstall.ins",
			updateScript       = "update.ins",
			alwaysScript       = None,
			onceScript         = None,
			priority           = 0,
			description        = None,
			advice             = "",
			productClassNames  = ['localboot-products'],
			windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx']
		)
		
		self.product3 = LocalbootProduct(
			id                 = 'product3',
			name               = u'Product 3',
			productVersion     = 3,
			packageVersion     = 1,
			licenseRequired    = True,
			setupScript        = "setup.ins",
			uninstallScript    = None,
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			priority           = 100,
			description        = "---",
			advice             = "---",
			productClassNames  = ['localboot-products'],
			windowsSoftwareIds = []
		)
		self.localbootProducts = [ self.product2, self.product3 ]
		self.products.extend(self.localbootProducts)
		
		# ProductProperties
		self.productProperty1 = UnicodeProductProperty(
			productId      = self.product1.id,
			productVersion = self.product1.productVersion,
			packageVersion = self.product1.packageVersion,
			propertyId     = "productProperty1",
			description    = 'Test product property (unicode)',
			possibleValues = ['unicode1', 'unicode2', 'unicode3'],
			defaultValues  = [ 'unicode1', 'unicode3' ],
			editable       = True,
			multiValue     = True
		)
		
		self.productProperty2 = BoolProductProperty(
			productId      = self.product1.id,
			productVersion = self.product1.productVersion,
			packageVersion = self.product1.packageVersion,
			propertyId     = "productProperty2",
			description    = 'Test product property 2 (bool)',
			defaultValues  = True
		)
		
		self.productProperty3 = BoolProductProperty(
			productId      = self.product3.id,
			productVersion = self.product3.productVersion,
			packageVersion = self.product3.packageVersion,
			propertyId     = u"productProperty3",
			description    = u'Test product property 3 (bool)',
			defaultValues  = False
		)
		self.productProperties = [ self.productProperty1, self.productProperty2, self.productProperty3 ]
		
		# ProductOnDepots
		self.productOnDepot1 = ProductOnDepot(
			productId      = self.product1.getId(),
			productType    = self.product1.getType(),
			productVersion = self.product1.getProductVersion(),
			packageVersion = self.product1.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)
		
		self.productOnDepot2 = ProductOnDepot(
			productId      = self.product2.getId(),
			productType    = self.product2.getType(),
			productVersion = self.product2.getProductVersion(),
			packageVersion = self.product2.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)
		
		self.productOnDepot3 = ProductOnDepot(
			productId      = self.product3.getId(),
			productType    = self.product3.getType(),
			productVersion = self.product3.getProductVersion(),
			packageVersion = self.product3.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)
		self.productOnDepots = [ self.productOnDepot1, self.productOnDepot2, self.productOnDepot3 ]
		
		# ProductOnClients
		self.productOnClient1 = ProductOnClient(
			productId          = self.product1.getId(),
			productType        = self.product1.getType(),
			clientId           = self.client1.getId(),
			installationStatus = 'installed',
			actionRequest      = 'setup',
			actionProgress     = '',
			productVersion     = self.product1.getProductVersion(),
			packageVersion     = self.product1.getPackageVersion(),
			lastStateChange    = '2009-07-01 12:00:00'
		)
		
		self.productOnClient2 = ProductOnClient(
			productId          = self.product2.getId(),
			productType        = self.product2.getType(),
			clientId           = self.client1.getId(),
			installationStatus = 'installed',
			actionRequest      = 'uninstall',
			actionProgress     = '',
			productVersion     = self.product2.getProductVersion(),
			packageVersion     = self.product2.getPackageVersion()
		)
		
		self.productOnClient3 = ProductOnClient(
			productId          = self.product2.getId(),
			productType        = self.product2.getType(),
			clientId           = self.client3.getId(),
			installationStatus = 'installed',
			actionRequest      = 'setup',
			actionProgress     = '',
			productVersion     = self.product2.getProductVersion(),
			packageVersion     = self.product2.getPackageVersion()
		)
		self.productOnClients = [ self.productOnClient1, self.productOnClient2, self.productOnClient3 ]
		
		# ProductPropertyStates
		self.productPropertyState1 = ProductPropertyState(
			productId  = self.productProperty1.getProductId(),
			propertyId = self.productProperty1.getPropertyId(),
			objectId   = self.client1.getId(),
			values     = 'unicode1'
		)
		
		self.productPropertyState2 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.client1.getId(),
			values     = [ False ]
		)
		
		self.productPropertyState3 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.client2.getId(),
			values     = True
		)
		self.productPropertyStates = [ self.productPropertyState1, self.productPropertyState2, self.productPropertyState3 ]
		
		# Groups
		self.group1 = HostGroup(
			id            = 'host_group_1',
			description   = 'Group 1',
			notes         = 'First group',
			parentGroupId = None
		)
		
		self.group2 = HostGroup(
			id            = u'host group 2',
			description   = 'Group 2',
			notes         = 'Test\nTest\nTest',
			parentGroupId = 'host_group_1'
		)
		
		self.group3 = HostGroup(
			id            = u'host group 3',
			description   = 'Group 3',
			notes         = '',
			parentGroupId = None
		)
		self.groups = [ self.group1, self.group2, self.group3 ]
		
		# ObjectToGroups
		self.objectToGroup1 = ObjectToGroup(
			groupId =  self.group1.getId(),
			objectId = self.client1.getId()
		)
		
		self.objectToGroup2 = ObjectToGroup(
			groupId =  self.group1.getId(),
			objectId = self.client2.getId()
		)
		
		self.objectToGroup3 = ObjectToGroup(
			groupId  = self.group2.getId(),
			objectId = self.client2.getId()
		)
		self.objectToGroups = [ self.objectToGroup1, self.objectToGroup2, self.objectToGroup3 ]
		
	def cleanupBackend(self):
		logger.notice(u"Deleting base")
		self.backend.base_delete()
	
	def testObjectMethods(self):
		logger.notice(u"Creating base")
		self.backend.base_create()
		
		# Hosts
		logger.notice(u"Testing host methods")
		
		self.backend.host_createObjects( self.hosts )
		
		hosts = self.backend.host_getObjects()
		assert len(hosts) == len(self.hosts)
		for host in hosts:
			assert host.getOpsiHostKey()
		
		hosts = self.backend.host_getObjects( id = [ self.client1.getId(), self.client2.getId() ] )
		assert len(hosts) == 2
		ids = []
		for host in hosts:
			ids.append(host.getId())
		assert self.client1.getId() in ids
		assert self.client2.getId() in ids
		
		hosts = self.backend.host_getObjects( type = [ self.clients[0].getType() ] )
		assert len(hosts) == len(self.clients)
		ids = []
		for host in hosts:
			ids.append(host.getId())
		for client in self.clients:
			assert client.getId() in ids
		
		hosts = self.backend.host_getObjects( id = [ self.client1.getId(), self.client2.getId() ], description = self.client2.getDescription() )
		assert len(hosts) == 1
		assert hosts[0].description == self.client2.getDescription()
		assert hosts[0].id == self.client2.getId()
		
		hosts = self.backend.host_getObjects(attributes=['id', 'description'], id = self.client1.getId())
		assert len(hosts) == 1
		assert hosts[0].getId() == self.client1.getId()
		assert hosts[0].getDescription() == self.client1.getDescription()
		
		self.backend.host_deleteObjects(self.client2)
		hosts = self.backend.host_getObjects( type = [ self.client1.getType() ] )
		assert len(hosts) == len(self.clients)-1
		ids = []
		for host in hosts:
			ids.append(host.getId())
		
		for client in self.clients:
			if (client.getId() == self.client2.getId()):
				continue
			assert client.getId() in ids
		
		self.backend.host_createObjects(self.client2)
		self.client2.setDescription('Updated')
		self.backend.host_updateObject(self.client2)
		hosts = self.backend.host_getObjects( description = 'Updated' )
		assert len(hosts) == 1
		assert hosts[0].getId() == self.client2.getId()
		
		self.client2.setDescription(u'Test client 2')
		self.backend.host_createObjects(self.client2)
		hosts = self.backend.host_getObjects( attributes = ['id', 'description'], id = self.client2.getId() )
		assert len(hosts) == 1
		assert hosts[0].getId() == self.client2.getId()
		assert hosts[0].getDescription() == 'Test client 2'
		
		
		# Configs
		logger.notice(u"Testing config methods")
		
		self.backend.config_createObjects( self.configs )
		
		configs = self.backend.config_getObjects()
		assert len(configs) == len(self.configs)
		ids = []
		for config in configs:
			ids.append(config.id)
		for config in self.configs:
			assert config.id in ids
		
		multiValueConfigNames = []
		for config in self.configs:
			if config.getMultiValue():
				multiValueConfigNames.append(config.name)
		configs = self.backend.config_getObjects( attributes = [], multiValue = True )
		assert len(configs) == len(multiValueConfigNames)
		for config in configs:
			assert config.name in multiValueConfigNames
		
		self.backend.config_deleteObjects(self.config1)
		configs = self.backend.config_getObjects()
		assert len(configs) == len(self.configs)-1
		
		self.backend.config_createObjects(self.config1)
		
		self.config3.setDescription(u'Updated')
		self.config3.setDefaultValues(['1', '2'])
		self.config3.setPossibleValues(['1', '2', '3'])
		self.backend.config_updateObject(self.config3)
		
		configs = self.backend.config_getObjects(description = u'Updated')
		assert len(configs) == 1
		assert configs[0].getPossibleValues() == ['1', '2', '3']
		assert configs[0].getDefaultValues() == ['1', '2']
		
		
		# ConfigStates
		logger.notice(u"Testing configState methods")
		
		self.backend.configState_createObjects( self.configStates )
		
		configStates = self.backend.configState_getObjects()
		assert len(configStates) == len(self.configStates)
		
		client1ConfigStates = []
		for configState in self.configStates:
			if configState.getObjectId() == self.client1.getId():
				client1ConfigStates.append(configState)
		configStates = self.backend.configState_getObjects( attributes = [], objectId = self.client1.getId() )
		assert len(configStates) == len(client1ConfigStates)
		for configState in configStates:
			assert configState.objectId == self.client1.getId()
		
		self.backend.configState_deleteObjects(self.configState2)
		configStates = self.backend.configState_getObjects()
		assert len(configStates) == len(self.configStates)-1
		for configState in configStates:
			assert not (configState.objectId == self.configState2.objectId and configState.configId == self.configState2.configId)
		
		self.configState3.setValues([True])
		self.backend.configState_updateObject(self.configState3)
		configStates = self.backend.configState_getObjects(objectId = self.configState3.getObjectId(), configId = self.configState3.getConfigId())
		assert len(configStates) == 1
		assert configStates[0].getValues() == [True]
		
		# Products
		logger.notice(u"Testing product methods")
		
		self.backend.product_createObjects( self.products )
		
		products = self.backend.product_getObjects()
		assert len(products) == len(self.products)
		
		products = self.backend.product_getObjects(type = self.localbootProducts[0].getType())
		assert len(products) == len(self.localbootProducts)
		ids = []
		for product in products:
			ids.append(product.getId())
		for product in self.localbootProducts:
			assert product.id in ids
		
		self.product2.setName(u'Product 2 updated')
		products = self.backend.product_updateObject(self.product2)
		products = self.backend.product_getObjects( attributes = ['name'], id = 'product2' )
		assert len(products) == 1
		assert products[0].getName() == u'Product 2 updated'
		
		
		# ProductProperties
		logger.notice(u"Testing productProperty methods")
		
		self.backend.productProperty_createObjects(self.productProperties)
		productProperties = self.backend.productProperty_getObjects()
		assert len(productProperties) == len(self.productProperties)
		
		
		# ProductOnDepots
		logger.notice(u"Testing productOnDepot methods")
		
		self.backend.productOnDepot_createObjects(self.productOnDepots)
		productOnDepots = self.backend.productOnDepot_getObjects( attributes = ['productId'] )
		assert len(productOnDepots) == len(self.productOnDepots)
		
		
		# ProductOnClients
		logger.notice(u"Testing productOnClient methods")
		
		self.backend.productOnClient_createObjects(self.productOnClients)
		productOnClients = self.backend.productOnClient_getObjects()
		assert len(productOnClients) == len(self.productOnClients)
		
		client1ProductOnClients = []
		for productOnClient in self.productOnClients:
			if (productOnClient.getClientId() == self.client1.id):
				client1ProductOnClients.append(productOnClient)
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.client1.getId())
		assert len(productOnClients) == len(client1ProductOnClients)
		
		
		# ProductPropertyStates
		logger.notice(u"Testing productPropertyState methods")
		
		self.backend.productPropertyState_createObjects(self.productPropertyStates)
		productPropertyStates = self.backend.productPropertyState_getObjects()
		assert len(productPropertyStates) == len(self.productPropertyStates)
		
		
		# Groups
		logger.notice(u"Testing group methods")
		self.backend.group_createObjects(self.groups)
		
		groups = self.backend.group_getObjects()
		assert len(groups) == len((self.groups))
		
		groups = self.backend.group_getObjects(description = self.groups[0].description)
		assert len(groups) == 1
		assert groups[0].getId() == self.groups[0].id
		
		self.group1.setDescription(u'new description')
		self.backend.group_createObjects(self.group1)
		
		groups = self.backend.group_getObjects(description = self.group1.description)
		assert len(groups) == 1
		assert groups[0].getDescription() == 'new description'
		
		self.backend.group_deleteObjects(self.group1)
		groups = self.backend.group_getObjects()
		assert len(groups) == len(self.groups)-1
		
		self.backend.group_createObjects(self.group1)
		groups = self.backend.group_getObjects()
		assert len(groups) == len(self.groups)
		
		
		# ObjectToGroups
		logger.notice(u"Testing objectToGroup methods")
		
		self.backend.objectToGroup_createObjects(self.objectToGroups)
		
		objectToGroups = self.backend.objectToGroup_getObjects()
		assert len(objectToGroups) == len(self.objectToGroups)
		
		client1ObjectToGroups = []
		client2ObjectToGroups = []
		for objectToGroup in self.objectToGroups:
			if (objectToGroup.objectId == self.client1.getId()):
				client1ObjectToGroups.append(objectToGroup)
			if (objectToGroup.objectId == self.client2.getId()):
				client2ObjectToGroups.append(objectToGroup)
		objectToGroups = self.backend.objectToGroup_getObjects(objectId = self.client1.getId())
		assert len(objectToGroups) == len(client1ObjectToGroups)
		for objectToGroup in objectToGroups:
			assert objectToGroup.objectId == self.client1.id
		objectToGroups = self.backend.objectToGroup_getObjects(objectId = self.client2.getId())
		assert len(objectToGroups) == len(client2ObjectToGroups)
		for objectToGroup in objectToGroups:
			assert objectToGroup.objectId == self.client2.id
		
	def testNonObjectMethods(self):
		# Hosts
		self.backend.host_createOpsiConfigserver(
				id = 'config100.uib.local',
				opsiHostKey = '123456789012345678901234567890bb',
				depotLocalUrl = 'file:///opt/pcbin/install',
				depotRemoteUrl = 'smb://config1.uib.local/opt_pcbin',
				repositoryLocalUrl = 'file:///var/lib/opsi/products',
				repositoryRemoteUrl = 'webdavs://config1.uib.local:4447/products',
				description = 'config server',
				notes = 'config 100',
				hardwareAddress = None,
				ipAddress = None,
				network = '192.168.100.0/24',
				maxBandwidth = 200000)
		
		hosts = self.backend.host_getObjects(id = 'config100.uib.local')
		assert len(hosts) == 1
		
		self.backend.host_createOpsiDepotserver(
				id = 'depot100.uib.local',
				opsiHostKey = '123456789012345678901234567890aa',
				depotLocalUrl = 'file:///opt/pcbin/install',
				depotRemoteUrl = 'smb://depot3.uib.local/opt_pcbin',
				repositoryLocalUrl = 'file:///var/lib/opsi/products',
				repositoryRemoteUrl = 'webdavs://depot3.uib.local:4447/products',
				description = 'A depot',
				notes = 'Depot 100',
				hardwareAddress = None,
				ipAddress = None,
				network = '192.168.100.0/24',
				maxBandwidth = 0)
		
		hosts = self.backend.host_getObjects(id = 'depot100.uib.local')
		assert len(hosts) == 1
		
		self.backend.host_createOpsiClient(
				id = 'client100.uib.local',
				opsiHostKey = None,
				description = 'Client 100',
				notes = 'No notes',
				hardwareAddress = '00:00:01:01:02:02',
				ipAddress = '192.168.0.200',
				created = None,
				lastSeen = None)
		
		hosts = self.backend.host_getObjects(id = 'config100.uib.local')
		assert len(hosts) == 1
		
		# TODO: assertions
		ids = self.backend.host_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.host_getIdents(id = '*100*')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.host_getIdents(returnType = 'tuple')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.host_getIdents(returnType = 'list')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.host_getIdents(returnType = 'dict')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.config_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.configState_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.product_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productProperty_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productOnDepot_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productOnDepot_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productPropertyState_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productPropertyState_getIdents(returnType = 'tuple')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productPropertyState_getIdents(returnType = 'list')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.productPropertyState_getIdents(returnType = 'dict')
		logger.notice("Idents: %s" % ids)
		ids = self.backend.group_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.objectToGroup_getIdents()
		logger.notice("Idents: %s" % ids)
		ids = self.backend.product_getIdents(id = '*product*')
		logger.notice("Idents: %s" % ids)
		
		# TODO: assertions
		result = self.backend.searchObjects('(&(objectClass=Host)(type=OpsiDepotserver))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
		logger.notice(result)
		result = self.backend.searchObjects('(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(|(&(objectClass=ProductOnClient)(productId=product1))(&(objectClass=ProductOnClient)(productId=product2))))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(objectClass=OpsiClient)(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(objectClass=Host)(description=T*))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(objectClass=Host)(description=*))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(&(objectClass=OpsiClient)(ipAddress=192*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
		logger.notice(result)
		result = self.backend.searchObjects('(&(&(objectClass=Product)(description=*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
		logger.notice(result)
		
		self.backend.host_delete(id = [])
		hosts = self.backend.host_getObjects()
		assert len(hosts) == 0
		
	def testPerformance(self):
		consoleLevel = logger.getConsoleLevel()
		if (consoleLevel > LOG_NOTICE):
			logger.setConsoleLevel(LOG_NOTICE)
		logger.notice("Testing backend performance...")
		
		num = 1000
		start = time.time()
		for i in range(num):
			ip = num
			while (ip > 255):
				ip -= 255
			self.backend.host_createOpsiClient(
				id = 'client%d.uib.local' % i,
				opsiHostKey = None,
				description = 'Client %d' % i,
				notes = 'No notes',
				hardwareAddress = '',
				ipAddress = '192.168.0.%d' % ip,
				created = None,
				lastSeen = None)
		logger.notice(u"Took %.2f seconds to create %d clients" % ((time.time()-start), num))
		
		start = time.time()
		self.backend.host_getObjects(attributes = ['id'], ipAddress = '192.168.0.100')
		logger.notice(u"Took %.2f seconds to search ip address in %d clients" % ((time.time()-start), num))
		
		start = time.time()
		self.backend.host_delete(id = [])
		logger.notice(u"Took %.2f seconds to delete %d clients" % ((time.time()-start), num))
		
		logger.setConsoleLevel(consoleLevel)

class BackendManagerTest(BackendTest):
	def __init__(self, backendManager):
		BackendTest.__init__(self, backendManager)
	
	

















