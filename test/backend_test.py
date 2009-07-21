#!/usr/bin/python
# -*- coding: utf-8 -*-

from OPSI.Logger import *
from OPSI.Backend.Object import *
from OPSI.Backend.MySQL import MySQLBackend

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
	
	logger.notice(u"Testing host methods")
	client1 = OpsiClient(
		id = 'test1.uib.local',
		description = 'Test client 1',
		notes = 'Notes ...',
		hardwareAddress = '00:01:02:03:04:05',
		ipAddress = '192.168.1.100',
		lastSeen = '2009-01-01 00:00:00',
		opsiHostKey = '12345678901234567890123456789012'
	)
	
	client2 = OpsiClient(
		id = 'test2.uib.local',
		description = 'Test client 2',
		hardwareAddress = '00-ff0aa3:0b-B5',
		opsiHostKey = '12345678901234567890123456789012'
	)
	
	depot1 = OpsiDepot(
		id = 'depot1.uib.local',
		opsiHostKey ='12345678901234567890123456789012',
		depotLocalUrl = 'file:///opt/pcbin/install',
		depotRemoteUrl = 'smb://depot1.uib.local/opt_pcbin',
		repositoryLocalUrl = 'file:///var/lib/opsi/products',
		repositoryRemoteUrl = 'webdavs://depot1.uib.local:4447/products',
		description = 'A depot',
		notes = 'Däpöt 1',
		hardwareAddress = '',
		ipAddress = '',
		network = '192.168.1.0/24',
		maxBandwidth = 10000)
	
	backend.host_create(client1)
	backend.host_create(client2)
	backend.host_create(depot1)
	
	hosts = backend.host_get()
	assert len(hosts) == 3
	
	hosts = backend.host_get(attributes=['id', 'description'], id = client1.id)
	assert len(hosts) == 1
	assert hosts[0].id == client1.id
	assert hosts[0].description == client1.description
	
	backend.host_delete(client2)
	hosts = backend.host_get()
	assert len(hosts) == 2
	
	
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
		setupScript = "setup.py",
		uninstallScript = u"uninstall.ins",
		updateScript = "update.py",
		alwaysScript = u"",
		onceScript = "",
		priority = 0,
		description = None,
		advice = "",
		productClassNames = ['localboot-products'],
		windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx'])
	
	
	backend.product_create(products = [ product1, product2 ])
	
	products = backend.product_get()
	assert len(products) == 2
	
	products = backend.product_get(type = 'LocalbootProduct')
	assert len(products) == 1
	
	
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
	
	logger.notice(u"Testing productOnDepot methods")
	
	productOnDepot1 = ProductOnDepot(
		productId = product1.id,
		productVersion = product1.productVersion,
		packageVersion = product1.packageVersion,
		depotId = depot1.id,
		locked = False)
	
	return
	# ==========================================================================
	group1 = HostGroup(
		id = 'test group',
		description = 'A group',
		notes = '',
		parentGroupId = '',
		memberIds = [ client1.id, client2.id ]
	)

	
	
	backend.productOnDepot_create(productOnDepots = [productOnDepot1])
	print backend.productOnDepot_get()
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	


testBackend( MySQLBackend(username = 'opsi', password = 'opsi', args = {'database': 'opsi'}) )


