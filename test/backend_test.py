#!/usr/bin/python
# -*- coding: utf-8 -*-

from OPSI.Logger import *
from OPSI.Backend.Object import *
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.BackendManager import BackendManager

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)

someTypes = (
	1,
	None,
	True,
	time.localtime(),
	u'unicode string',
	u'utf-8 string: äöüß€'.encode('utf-8'),
	u'windows-1258 string: äöüß€'.encode('windows-1258'),
	u'utf-16 string: äöüß€'.encode('utf-16'),
	u'latin1 string: äöüß'.encode('latin-1')
)

# ----------------------------------------------------------------------- #
def testBackend(backend):
	logger.notice(u"Testing backend %s" % backend)
	
	logger.notice(u"Deleting base")
	backend.base_delete()
	
	logger.notice(u"Creating base")
	backend.base_create()
	
	# --- Host --- #
	logger.notice(u"Testing host methods")
	client1 = OpsiClient(
		id = 'test1.uib.local',
		description = 'Test client 1',
		notes = 'Notes ...',
		hardwareAddress = '00:01:02:03:04:05',
		ipAddress = '192.168.1.100',
		lastSeen = '2009-01-01 00:00:00',
		opsiHostKey = '45656789789012789012345612340123'
	)
	
	client2 = OpsiClient(
		id = 'test2.uib.local',
		description = 'Test client 2',
		hardwareAddress = '00-ff0aa3:0b-B5',
		opsiHostKey = '59051234345678890121678901223467'
	)
	
	configserver1 = OpsiConfigserver(
		id = 'config1.uib.local',
		opsiHostKey ='71234545689056789012123678901234',
		depotLocalUrl = 'file:///opt/pcbin/install',
		depotRemoteUrl = 'smb://config1/opt_pcbin',
		repositoryLocalUrl = 'file:///var/lib/opsi/products',
		repositoryRemoteUrl = 'webdavs://config1.uib.local:4447/products',
		description = 'The configserver',
		notes = 'Config 1',
		hardwareAddress = '',
		ipAddress = '',
		network = '192.168.1.0/24',
		maxBandwidth = 10000)
	
	depot1 = OpsiDepot(
		id = 'depot1.uib.local',
		opsiHostKey ='19012334567845645678901232789012',
		depotLocalUrl = 'file:///opt/pcbin/install',
		depotRemoteUrl = 'smb://depot1.uib.local/opt_pcbin',
		repositoryLocalUrl = 'file:///var/lib/opsi/products',
		repositoryRemoteUrl = 'webdavs://depot1.uib.local:4447/products',
		description = 'A depot',
		notes = 'Däpöt 1',
		hardwareAddress = '',
		ipAddress = '',
		network = '192.168.2.0/24',
		maxBandwidth = 10000)
	
	backend.host_create(configserver1)
	backend.host_create(depot1)
	backend.host_create(client1)
	backend.host_create(client2)
	
	
	hosts = backend.host_get()
	assert len(hosts) == 4
	
	hosts = backend.host_get(attributes=['id', 'description'], id = client1.id)
	assert len(hosts) == 1
	assert hosts[0].id == client1.id
	assert hosts[0].description == client1.description
	
	backend.host_delete(client2)
	hosts = backend.host_get()
	assert len(hosts) == 3
	
	backend.host_create(client2)
	client2.description = 'Updated'
	backend.host_update(client2)
	hosts = backend.host_get(description = 'Updated')
	assert len(hosts) == 1
	
	
	# --- Config --- #
	logger.notice(u"Testing config methods")
	config1 = UnicodeConfig(
		name = u'opsi-linux-bootimage.cmdline.reboot',
		description = (u'Some sting üöä?').encode('latin-1'),
		possibleValues = ['w', 'c', 'b', 'h', 'b,c'],
		defaultValues = ['b,c']
	)
	
	config2 = BoolConfig(
		name = u'opsi-linux-bootimage.cmdline.bool',
		description = 'Bool?',
		defaultValues = 'on'
	)
	
	config3 = UnicodeConfig(
		name = u'some.products',
		description = u'Install this products',
		possibleValues = ['product1', 'product2', 'product3', 'product4'],
		defaultValues = ['product1', 'product3']
	)
	
	backend.config_create([config1, config2, config3])
	
	configs = backend.config_get()
	assert len(configs) == 3
	
	configs = backend.config_get(attributes=[], multiValue = True)
	assert len(configs) == 1
	
	backend.config_delete(config1)
	configs = backend.config_get()
	assert len(configs) == 2
	
	config3.description = u'Updated'
	config3.possibleValues = ['1', '2', '3']
	config3.defaultValues = ['1', '2']
	backend.config_update(config3)
	
	configs = backend.config_get(description = u'Updated')
	assert len(configs) == 1
	assert configs[0].possibleValues == ['1', '2', '3']
	assert configs[0].defaultValues == ['1', '2']
	
	# --- Product --- #
	logger.notice(u"Testing product methods")
	
	product1 = NetbootProduct(
		id = 'product1',
		name = u'Product 1',
		productVersion = '1.0',
		packageVersion = 1,
		licenseRequired = True,
		setupScript = None,
		uninstallScript = None,
		updateScript = "update.py",
		alwaysScript = u"",
		onceScript = "",
		priority = '100',
		description = "Nothing",
		advice = u"No advice",
		productClassNames = ['class1'],
		windowsSoftwareIds = ['{be21bd07-eb19-44e4-893a-fa4e44e5f806}', 'product1'],
		pxeConfigTemplate = 'special')
	
	product2 = LocalbootProduct(
		id = 'product2',
		name = u'Product 2',
		productVersion = '2.0',
		packageVersion = 'test',
		licenseRequired = False,
		setupScript = "setup.ins",
		uninstallScript = u"uninstall.ins",
		updateScript = "update.ins",
		alwaysScript = u"",
		onceScript = "",
		priority = 0,
		description = None,
		advice = "",
		productClassNames = ['localboot-products'],
		windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx'])
	
	product3 = LocalbootProduct(
		id = 'product3',
		name = u'Product 3',
		productVersion = 3,
		packageVersion = 1,
		licenseRequired = True,
		setupScript = "setup.ins",
		uninstallScript = None,
		updateScript = '',
		alwaysScript = "",
		onceScript = "",
		priority = 100,
		description = "---",
		advice = "---",
		productClassNames = ['localboot-products'],
		windowsSoftwareIds = [])
	
	
	
	backend.product_create(products = [ product1, product2, product3 ])
	
	products = backend.product_get()
	assert len(products) == 3
	
	products = backend.product_get(type = 'LocalbootProduct')
	assert len(products) == 2
	
	product2.name = u'Product 2 updated'
	products = backend.product_update(product2)
	products = backend.product_get(id = 'product2')
	assert len(products) == 1
	assert products[0].name == u'Product 2 updated'
	
	
	# --- ProductProperty --- #
	logger.notice(u"Testing productProperty methods")
	
	productProperty1 = UnicodeProductProperty(
		productId = product1.id,
		productVersion = product1.productVersion,
		packageVersion = product1.packageVersion,
		name = "test_pp",
		description = 'Test product property (unicode)',
		possibleValues = ['unicode1', 'unicode2', 'unicode3'],
		defaultValues = [ 'unicode1', 'unicode3' ],
		editable = False,
		multiValue = True)
	
	productProperty2 = BoolProductProperty(
		productId = product1.id,
		productVersion = product1.productVersion,
		packageVersion = product1.packageVersion,
		name = "test_pp_2",
		description = 'Test product property 2 (bool)',
		defaultValues = True)
	
	backend.productProperty_create(productProperties = [ productProperty1, productProperty2 ])
	
	productProperties = backend.productProperty_get()
	assert len(productProperties) == 2
	
	
	# --- ProductOnDepot --- #
	logger.notice(u"Testing productOnDepot methods")
	
	productOnDepot1 = ProductOnDepot(
		productId = product1.id,
		productVersion = product1.productVersion,
		packageVersion = product1.packageVersion,
		depotId = depot1.id,
		locked = False)
	
	productOnDepot2 = ProductOnDepot(
		productId = product2.id,
		productVersion = product2.productVersion,
		packageVersion = product2.packageVersion,
		depotId = depot1.id,
		locked = False)
	
	backend.productOnDepot_create([productOnDepot1, productOnDepot2])
	
	productOnDepots = backend.productOnDepot_get()
	assert len(productProperties) == 2
	
	
	logger.notice(u"Testing productState methods")
	
	productState1 = ProductState(
		productId = product1.id,
		hostId = client1.id,
		installationStatus = 'installed',
		actionRequest = 'setup',
		actionProgress = '',
		productVersion = product1.productVersion,
		packageVersion = product1.packageVersion,
		lastStateChange = '2009-07-01 12:00:00')
	
	productState2 = ProductState(
		productId = product2.id,
		hostId = client1.id,
		installationStatus = 'installed',
		actionRequest = 'uninstall',
		actionProgress = '',
		productVersion = product2.productVersion,
		packageVersion = product2.packageVersion)
	
	backend.productState_create([productState1, productState2])
	
	productStates = backend.productState_get(hostId = client1.id)
	assert len(productStates) == 2
	
	
	logger.notice(u"Testing productPropertyState methods")
	
	productPropertyState1 = ProductPropertyState(
		productId = product1.id,
		name = 'test_pp',
		hostId = client1.id,
		values = 'unicode1')
	
	productPropertyState2 = ProductPropertyState(
		productId = product1.id,
		name = 'test_pp_2',
		hostId = client1.id,
		values = [ False ])
	
	productPropertyState3 = ProductPropertyState(
		productId = product1.id,
		name = 'test_pp_2',
		hostId = client2.id,
		values = True)
	
	backend.productPropertyState_create(productPropertyStates = [ productPropertyState1, productPropertyState2, productPropertyState3 ])
	
	productPropertyStates = backend.productPropertyState_get()
	assert len(productPropertyStates) == 3
	
	
	# --- Group --- #
	logger.notice(u"Testing group methods")
	
	group1 = HostGroup(
		id = 'host_group_1',
		description = 'Group 1',
		notes = 'First group',
		parentGroupId = ''
	)
	
	group2 = HostGroup(
		id = u'host group 2',
		description = 'Group 2',
		notes = 'Test\nTest\nTest',
		parentGroupId = 'host_group_1'
	)
	
	group3 = HostGroup(
		id = u'host group 3',
		description = 'Group 3',
		notes = '',
		parentGroupId = ''
	)
	
	backend.group_create(groups = [ group1, group2, group3 ])
	
	groups = backend.group_get()
	assert len(groups) == 3
	
	groups = backend.group_get(description = u'Group 3')
	assert len(groups) == 1
	assert groups[0].id == u'host group 3'
	
	groups[0].description = u'new description'
	backend.group_update(groups[0])
	
	groups = backend.group_get(id = u'host group 3')
	assert len(groups) == 1
	assert groups[0].description == u'new description'
	
	backend.group_delete(groups[0])
	groups = backend.group_get()
	assert len(groups) == 2
	
	# --- ObjectToGroup --- #
	logger.notice(u"Testing objectToGroup methods")
	
	objectToGroup1 = ObjectToGroup(
		groupId = group1.id,
		objectId = client1.id
	)
	objectToGroup2 = ObjectToGroup(
		groupId = group1.id,
		objectId = client2.id
	)
	objectToGroup3 = ObjectToGroup(
		groupId = group2.id,
		objectId = client2.id
	)
	
	backend.objectToGroup_create(objectToGroups = [objectToGroup1, objectToGroup2, objectToGroup3])
	
	objectToGroups = backend.objectToGroup_get()
	assert len(objectToGroups) == 3
	
	objectToGroups = backend.objectToGroup_get(objectId = client2.id)
	assert len(objectToGroups) == 2
	
	objectToGroups = backend.objectToGroup_get(objectId = client1.id)
	assert len(objectToGroups) == 1
	assert objectToGroups[0].objectId == client1.id
	
	
	
	
	
	
	
	
	
	


#testBackend( MySQLBackend(username = 'opsi', password = 'opsi', args = {'database': 'opsi'}) )
testBackend( BackendManager(username = 'opsi', password = 'opsi', args = {'database': 'opsi'}) )






























