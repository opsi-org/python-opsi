#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time, random, socket

from OPSI.Logger import *
from OPSI.Object import *

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
		serverId = socket.getfqdn()
		if (serverId.count('.') < 2):
			raise Exception(u"Failed to get fqdn: %s" % serverId)
		
		self.hosts = []
		self.configserver1 = OpsiConfigserver(
			id                  = serverId,
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
			networkAddress      = '192.168.1.0/24',
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
			inventoryNumber     = '00000000002',
			networkAddress      = '192.168.2.0/24',
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
			inventoryNumber = '00000000003'
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
		
		self.config5 = UnicodeConfig(
			id             = u'some.other.products',
			description    = u'Some other product ids',
			possibleValues = ['product3', 'product4', 'product5'],
			defaultValues  = ['product3']
		)
		
		self.configs = [ self.config1, self.config2, self.config3, self.config4, self.config5 ]
		
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
		
		self.product4 = LocalbootProduct(
			id                 = 'product4',
			name               = u'Product 4',
			productVersion     = "3.0",
			packageVersion     = 24,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			priority           = 0,
			description        = "",
			advice             = "",
			productClassNames  = [],
			windowsSoftwareIds = []
		)
		
		self.localbootProducts = [ self.product2, self.product3, self.product4 ]
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
		
		# ProductDependencies
		self.productDependency1 = ProductDependency(
			productId                  = self.product2.id,
			productVersion             = self.product2.productVersion,
			packageVersion             = self.product2.packageVersion,
			productAction              = 'setup',
			requiredProductId          = self.product3.id,
			requiredProductVersion     = self.product3.productVersion,
			requiredPackageVersion     = self.product3.packageVersion,
			requiredAction             = 'setup',
			requiredInstallationStatus = None,
			requirementType            = 'before'
		)
		self.productDependency2 = ProductDependency(
			productId                  = self.product2.id,
			productVersion             = self.product2.productVersion,
			packageVersion             = self.product2.packageVersion,
			productAction              = 'setup',
			requiredProductId          = self.product4.id,
			requiredProductVersion     = None,
			requiredPackageVersion     = None,
			requiredAction             = None,
			requiredInstallationStatus = 'installed',
			requirementType            = 'after'
		)
		self.productDependencies = [ self.productDependency1, self.productDependency2 ]
		
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
			groupId  = self.group1.getId(),
			objectId = self.client1.getId()
		)
		
		self.objectToGroup2 = ObjectToGroup(
			groupId  = self.group1.getId(),
			objectId = self.client2.getId()
		)
		
		self.objectToGroup3 = ObjectToGroup(
			groupId  = self.group2.getId(),
			objectId = self.client2.getId()
		)
		self.objectToGroups = [ self.objectToGroup1, self.objectToGroup2, self.objectToGroup3 ]
		
		# LicenseContracts
		self.licenseContract1 = LicenseContract(
			id               = u'license contract 1',
			description      = u'a license contract',
			notes            = None,
			partner          = u'',
			conclusionDate   = None,
			notificationDate = None,
			expirationDate   = None
		)
		
		self.licenseContract2 = LicenseContract(
			id               = u'license contract 2',
			description      = u'license contract with company x',
			notes            = u'Contract notes',
			partner          = u'company x',
			conclusionDate   = '2009-01-01 00:00:00',
			notificationDate = '2010-12-01 00:00:00',
			expirationDate   = '2011-01-01 00:00:00',
		)
		self.licenseContracts = [ self.licenseContract1, self.licenseContract2 ]
		
		# SoftwareLicenses
		self.softwareLicense1 = RetailSoftwareLicense(
			id                = u'software license 1',
			licenseContractId = self.licenseContract1.getId(),
			maxInstallations  = 2,
			boundToHost       = None,
			expirationDate    = self.licenseContract1.getExpirationDate()
		)
		
		self.softwareLicense2 = OEMSoftwareLicense(
			id                = u'software license 2',
			licenseContractId = self.licenseContract1.getId(),
			maxInstallations  = None,
			boundToHost       = self.client1.getId(),
			expirationDate    = self.licenseContract1.getExpirationDate()
		)
		
		self.softwareLicense3 = VolumeSoftwareLicense(
			id                = u'software license 3',
			licenseContractId = self.licenseContract2.getId(),
			maxInstallations  = 100,
			boundToHost       = None,
			expirationDate    = self.licenseContract2.getExpirationDate()
		)
		
		self.softwareLicense4 = ConcurrentSoftwareLicense(
			id                = u'software license 4',
			licenseContractId = self.licenseContract2.getId(),
			maxInstallations  = 10,
			boundToHost       = None,
			expirationDate    = self.licenseContract2.getExpirationDate()
		)
		self.softwareLicenses = [ self.softwareLicense1, self.softwareLicense2, self.softwareLicense3, self.softwareLicense4 ]
		
		# LicensePools
		self.licensePool1 = LicensePool(
			id                 = u'license_pool_1',
			description        = u'licenses for product1',
			productIds         = self.product1.getId(),
			windowsSoftwareIds = self.product1.windowsSoftwareIds
		)
		
		self.licensePool2 = LicensePool(
			id                 = u'license_pool_2',
			description        = u'licenses for product2',
			productIds         = self.product2.getId(),
			windowsSoftwareIds = None
		)
		self.licensePools = [ self.licensePool1, self.licensePool2 ]
		
		# SoftwareLicenseToLicensePools
		self.softwareLicenseToLicensePool1 = SoftwareLicenseToLicensePool(
			softwareLicenseId  = self.softwareLicense1.getId(),
			licensePoolId      = self.licensePool1.getId(),
			licenseKey         = 'xxxxx-yyyyy-zzzzz-aaaaa-bbbbb'
		)
		
		self.softwareLicenseToLicensePool2 = SoftwareLicenseToLicensePool(
			softwareLicenseId  = self.softwareLicense2.getId(),
			licensePoolId      = self.licensePool1.getId(),
			licenseKey         = ''
		)
		
		self.softwareLicenseToLicensePool3 = SoftwareLicenseToLicensePool(
			softwareLicenseId  = self.softwareLicense3.getId(),
			licensePoolId      = self.licensePool2.getId(),
			licenseKey         = '12345-56789-00000-11111-aaaaa'
		)
		
		self.softwareLicenseToLicensePool4 = SoftwareLicenseToLicensePool(
			softwareLicenseId  = self.softwareLicense4.getId(),
			licensePoolId      = self.licensePool2.getId(),
			licenseKey         = None
		)
		self.softwareLicenseToLicensePools = [ self.softwareLicenseToLicensePool1, self.softwareLicenseToLicensePool2, self.softwareLicenseToLicensePool3, self.softwareLicenseToLicensePool4 ]
		
		# LicenseOnClients
		self.licenseOnClient1 = LicenseOnClient(
			softwareLicenseId  = self.softwareLicenseToLicensePool1.getSoftwareLicenseId(),
			licensePoolId      = self.softwareLicenseToLicensePool1.getLicensePoolId(),
			clientId           = self.client1.getId(),
			licenseKey         = self.softwareLicenseToLicensePool1.getLicenseKey(),
			notes              = None
		)
		
		self.licenseOnClient2 = LicenseOnClient(
			softwareLicenseId  = self.softwareLicenseToLicensePool1.getSoftwareLicenseId(),
			licensePoolId      = self.softwareLicenseToLicensePool1.getLicensePoolId(),
			clientId           = self.client2.getId(),
			licenseKey         = self.softwareLicenseToLicensePool1.getLicenseKey(),
			notes              = u'Installed manually'
		)
		self.licenseOnClients = [self.licenseOnClient1, self.licenseOnClient2]
		
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
		
		# AuditSoftwares
		self.auditSoftware1 = AuditSoftware(
			softwareId      = '{480aa013-93a7-488c-89c3-b985b6c8440a}',
			displayName     = 'A Software',
			displayVersion  = '1.0.21',
			uninstallString = 'c:\\programme\\a software\\unistall.exe /S',
			binaryName      = u'',
			installSize     = 129012992
		)
		
		self.auditSoftware2 = AuditSoftware(
			softwareId      = self.product2.getWindowsSoftwareIds()[0],
			displayName     = self.product2.getName(),
			displayVersion  = self.product2.getProductVersion(),
			uninstallString = 'msiexec /x %s' % self.product2.getWindowsSoftwareIds()[0],
			binaryName      = u'',
			installSize     = 217365267
		)
		
		self.auditSoftware3 = AuditSoftware(
			softwareId      = 'my software',
			displayName     = '',
			displayVersion  = '',
			uninstallString = None,
			binaryName      = None,
			installSize     = -1
		)
		self.auditSoftwares = [self.auditSoftware1, self.auditSoftware2, self.auditSoftware3]
		
		# AuditSoftwareOnClients
		self.auditSoftwareOnClient1 = AuditSoftwareOnClient(
			softwareId     = self.auditSoftware1.getSoftwareId(),
			displayName    = self.auditSoftware1.getDisplayName(),
			displayVersion = self.auditSoftware1.getDisplayVersion(),
			clientId       = self.client1.getId(),
			firstseen      = None,
			lastseen       = None,
			state          = None,
			usageFrequency = 2,
			lastUsed       = '2009-02-12 09:48:22'
		)
		
		self.auditSoftwareOnClient2 = AuditSoftwareOnClient(
			softwareId     = self.auditSoftware2.getSoftwareId(),
			displayName    = self.auditSoftware2.getDisplayName(),
			displayVersion = self.auditSoftware2.getDisplayVersion(),
			clientId       = self.client1.getId(),
			firstseen      = None,
			lastseen       = None,
			state          = None,
			usageFrequency = None,
			lastUsed       = None
		)
		
		self.auditSoftwareOnClient3 = AuditSoftwareOnClient(
			softwareId     = self.auditSoftware3.getSoftwareId(),
			displayName    = self.auditSoftware3.getDisplayName(),
			displayVersion = self.auditSoftware3.getDisplayVersion(),
			clientId       = self.client1.getId(),
			firstseen      = None,
			lastseen       = None,
			state          = None,
			usageFrequency = 0,
			lastUsed       = '2009-08-01 14:11:00'
		)
		
		self.auditSoftwareOnClient4 = AuditSoftwareOnClient(
			softwareId     = self.auditSoftware2.getSoftwareId(),
			displayName    = self.auditSoftware2.getDisplayName(),
			displayVersion = self.auditSoftware2.getDisplayVersion(),
			clientId       = self.client2.getId(),
			firstseen      = None,
			lastseen       = None,
			state          = None,
			usageFrequency = 0,
			lastUsed       = None
		)
		self.auditSoftwareOnClients = [self.auditSoftwareOnClient1, self.auditSoftwareOnClient2, self.auditSoftwareOnClient3, self.auditSoftwareOnClient4]
		
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
		logger.info(u"Got hosts: %s" % hosts)
		assert len(hosts) == len(self.hosts)
		for host in hosts:
			logger.debug(host)
			logger.info(u"Host key for host '%s': %s" % (host.getId(), host.getOpsiHostKey()))
			assert host.getOpsiHostKey()
			for h in self.hosts:
				if (host.id == h.id):
					host = host.toHash()
					h = h.toHash()
					for (attribute, value) in h.items():
						if not value is None:
							logger.debug(u"%s: expected(%s) == got(%s) in host: '%s'" % (attribute, value, host[attribute], host['id']))
							if type(value) is list:
								for v in value:
									assert v in host[attribute]
							else:
								assert value == host[attribute]
					break
		
		hosts = self.backend.host_getObjects( id = [ self.client1.getId(), self.client2.getId() ] )
		assert len(hosts) == 2
		ids = []
		for host in hosts:
			ids.append(host.getId())
		assert self.client1.getId() in ids
		assert self.client2.getId() in ids
		
		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = [ None ] )
		count = 0
		for host in self.hosts:
			if host.getIpAddress() is None:
				count += 1
		
		assert len(hosts) == count
		for host in hosts:
			assert host.getIpAddress() is None
			assert host.getInventoryNumber() is None
			assert not host.getNotes() is None
			assert not host.getDescription() is None
		
		hosts = self.backend.host_getObjects( attributes = ['description', 'notes'], ipAddress = None )
		assert len(hosts) == len(self.hosts)
		for host in hosts:
			assert host.getIpAddress() is None
			assert host.getInventoryNumber() is None
		
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
		
		for config in configs:
			logger.debug(config)
			for c in self.configs:
				if (config.id == c.id):
					config = config.toHash()
					c = c.toHash()
					for (attribute, value) in c.items():
						if not value is None:
							logger.debug(u"%s: expected(%s) == got(%s)" % (attribute, value, config[attribute]))
							if type(value) is list:
								for v in value:
									assert v in config[attribute]
							else:
								assert value == config[attribute]
					break
		
		configs = self.backend.config_getObjects(defaultValues = [ self.config2.defaultValues ])
		logger.debug(u"expected(%s), got(%s)" % (self.config2, configs))
		assert len(configs) == 1
		assert configs[0].getId() == self.config2.getId()
		
		configs = self.backend.config_getObjects(possibleValues = [])
		assert len(configs) == len(self.configs)
		
		configs = self.backend.config_getObjects(possibleValues = [ self.config1.possibleValues ], defaultValues = [ self.config1.defaultValues ])
		logger.debug(u"expected(%s), got(%s)" % (self.config1, configs))
		assert len(configs) == 1
		assert configs[0].getId() == self.config1.getId()
		
		configs = self.backend.config_getObjects(possibleValues = self.config5.possibleValues, defaultValues = self.config5.defaultValues)
		logger.debug(u"expected(%s), got(%s)" % (self.config5, configs))
		assert len(configs) == 2
		for config in configs:
			assert config.getId() in (self.config3.id, self.config5.id)
		
		multiValueConfigNames = []
		for config in self.configs:
			if config.getMultiValue():
				multiValueConfigNames.append(config.id)
		configs = self.backend.config_getObjects( attributes = [], multiValue = True )
		logger.debug(u"expected(%s), got(%s)" % (multiValueConfigNames, configs))
		assert len(configs) == len(multiValueConfigNames)
		for config in configs:
			assert config.id in multiValueConfigNames
		
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
		#assert len(configStates) == len(self.configStates)
		
		client1ConfigStates = []
		for configState in self.configStates:
			if configState.getObjectId() == self.client1.getId():
				client1ConfigStates.append(configState)
		configStates = self.backend.configState_getObjects( attributes = [], objectId = self.client1.getId() )
		#assert len(configStates) == len(client1ConfigStates)
		for configState in configStates:
			assert configState.objectId == self.client1.getId()
		
		self.backend.configState_deleteObjects(self.configState2)
		configStates = self.backend.configState_getObjects()
		#assert len(configStates) == len(self.configStates)-1
		#for configState in configStates:
		#	assert not (configState.objectId == self.configState2.objectId and configState.configId == self.configState2.configId)
		
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
		
		for product in products:
			logger.debug(product)
			for p in self.products:
				if (product.id == p.id):
					product = product.toHash()
					p = p.toHash()
					for (attribute, value) in p.items():
						if (attribute == 'productClassIds'):
							logger.warning(u"Skipping productClassIds attribute test!!!")
							continue
						if not value is None:
							logger.debug(u"%s: expected(%s) == got(%s)" % (attribute, value, product[attribute]))
							if type(value) is list:
								for v in value:
									assert v in product[attribute]
							else:
								assert value == product[attribute]
					break
		
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
		
		# ProductDependencies
		logger.notice(u"Testing ProductDependency methods")
		
		self.backend.productDependency_createObjects(self.productDependencies)
		productDependencies = self.backend.productDependency_getObjects()
		assert len(productDependencies) == len(self.productDependencies)
		
		# ProductOnDepots
		logger.notice(u"Testing productOnDepot methods")
		
		self.backend.productOnDepot_createObjects(self.productOnDepots)
		productOnDepots = self.backend.productOnDepot_getObjects( attributes = ['productId'] )
		assert len(productOnDepots) == len(self.productOnDepots)
		
		
		# ProductOnClients
		logger.notice(u"Testing productOnClient methods")
		
		self.backend.productOnClient_createObjects(self.productOnClients)
		productOnClients = self.backend.productOnClient_getObjects()
		
		client1ProductOnClients = []
		for productOnClient in self.productOnClients:
			if (productOnClient.getClientId() == self.client1.id):
				client1ProductOnClients.append(productOnClient)
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.client1.getId())
		for productOnClient in productOnClients:
			assert productOnClient.getClientId() == self.client1.getId()
		
		productOnClients = self.backend.productOnClient_getObjects(clientId = self.client1.getId(), productId = self.product2.getId())
		assert len(productOnClients) == 1
		assert productOnClients[0].getProductId() == self.product2.getId()
		assert productOnClients[0].getClientId() == self.client1.getId()
		
		# ProductPropertyStates
		logger.notice(u"Testing productPropertyState methods")
		
		self.backend.productPropertyState_createObjects(self.productPropertyStates)
		productPropertyStates = self.backend.productPropertyState_getObjects()
		#assert len(productPropertyStates) == len(self.productPropertyStates)
		
		
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
		
		# LicenseContracts
		logger.notice(u"Testing licenseContract methods")
		
		self.backend.licenseContract_createObjects(self.licenseContracts)
		
		licenseContracts = self.backend.licenseContract_getObjects()
		assert len(licenseContracts) == len(self.licenseContracts)
		
		# SoftwareLicenses
		logger.notice(u"Testing softwareLicense methods")
		
		self.backend.softwareLicense_createObjects(self.softwareLicenses)
		
		softwareLicenses = self.backend.softwareLicense_getObjects()
		assert len(softwareLicenses) == len(self.softwareLicenses)
		
		# LicensePools
		logger.notice(u"Testing licensePool methods")
		
		self.backend.licensePool_createObjects(self.licensePools)
		
		licensePools = self.backend.licensePool_getObjects()
		assert len(licensePools) == len(self.licensePools)
		for licensePool in licensePools:
			if (licensePool.getId() == self.licensePool1.getId()):
				for windowsSoftwareId in licensePool.getWindowsSoftwareIds():
					assert windowsSoftwareId in self.licensePool1.getWindowsSoftwareIds()
				for productId in licensePool.getProductIds():
					assert productId in self.licensePool1.getProductIds()
		
		licensePools = self.backend.licensePool_getObjects(windowsSoftwareIds = self.licensePool1.windowsSoftwareIds)
		assert len(licensePools) == 1
		assert licensePools[0].getId() == self.licensePool1.getId()
		
		licensePools = self.backend.licensePool_getObjects(productIds = self.licensePool1.productIds)
		assert len(licensePools) == 1
		assert licensePools[0].getId() == self.licensePool1.getId()
		
		licensePools = self.backend.licensePool_getObjects(productIds = self.licensePool1.productIds, windowsSoftwareIds = self.licensePool1.windowsSoftwareIds)
		assert len(licensePools) == 1
		assert licensePools[0].getId() == self.licensePool1.getId()
		
		licensePools = self.backend.licensePool_getObjects(productIds = self.licensePool1.productIds, windowsSoftwareIds = self.licensePool1.windowsSoftwareIds[0])
		assert len(licensePools) == 1
		assert licensePools[0].getId() == self.licensePool1.getId()
		
		licensePools = self.backend.licensePool_getObjects(id = self.licensePool1.id, productIds = self.licensePool1.productIds, windowsSoftwareIds = self.licensePool1.windowsSoftwareIds)
		assert len(licensePools) == 1
		assert licensePools[0].getId() == self.licensePool1.getId()
		
		licensePools = self.backend.licensePool_getObjects(id = self.licensePool2.id, productIds = self.licensePool1.productIds)
		assert len(licensePools) == 0
		
		licensePools = self.backend.licensePool_getObjects(productIds = None, windowsSoftwareIds = [])
		assert len(licensePools) == len(self.licensePools)
		
		licensePools = self.backend.licensePool_getObjects(productIds = ['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'])
		assert len(licensePools) == 0
		
		# SoftwareLicenseToLicensePools
		logger.notice(u"Testing softwareLicenseToLicensePool methods")
		
		self.backend.softwareLicenseToLicensePool_createObjects(self.softwareLicenseToLicensePools)
		
		softwareLicenseToLicensePools = self.backend.softwareLicenseToLicensePool_getObjects()
		assert len(softwareLicenseToLicensePools) == len(self.softwareLicenseToLicensePools)
		
		# LicenseOnClients
		logger.notice(u"Testing licenseOnClient methods")
		
		self.backend.licenseOnClient_createObjects(self.licenseOnClients)
		
		licenseOnClients = self.backend.licenseOnClient_getObjects()
		assert len(licenseOnClients) == len(self.licenseOnClients)
		
		# AuditSoftwares
		logger.notice(u"Testing auditSoftware methods")
		
		self.backend.auditSoftware_createObjects(self.auditSoftwares)
		
		auditSoftwares = self.backend.auditSoftware_getObjects()
		assert len(auditSoftwares) == len(self.auditSoftwares)
		
		# AuditSoftwareOnClients
		logger.notice(u"Testing auditSoftwareOnClient methods")
		
		self.backend.auditSoftwareOnClient_createObjects(self.auditSoftwareOnClients)
		
		auditSoftwareOnClients = self.backend.auditSoftwareOnClient_getObjects()
		assert len(auditSoftwareOnClients) == len(self.auditSoftwareOnClients)
		
		
		
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
				networkAddress = '192.168.100.0/24',
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
				networkAddress = '192.168.100.0/24',
				maxBandwidth = 0)
		
		hosts = self.backend.host_getObjects(id = 'depot100.uib.local')
		assert len(hosts) == 1
		
		self.backend.productOnDepot_create(
			productId      = self.product4.getId(),
			productType    = self.product4.getType(),
			productVersion = self.product4.getProductVersion(),
			packageVersion = self.product4.getPackageVersion(),
			depotId        = 'depot100.uib.local',
			locked         = False
		)
		
		self.backend.host_createOpsiClient(
				id = 'client100.uib.local',
				opsiHostKey = None,
				description = 'Client 100',
				notes = 'No notes',
				hardwareAddress = '00:00:01:01:02:02',
				ipAddress = '192.168.0.200',
				created = None,
				lastSeen = None)
		
		hosts = self.backend.host_getObjects(id = 'client100.uib.local')
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
		
		#self.backend.host_delete(id = [])
		#hosts = self.backend.host_getObjects()
		#assert len(hosts) == 0
		
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
				lastSeen = None
			)
		logger.notice(u"Took %.2f seconds to create %d clients" % ((time.time()-start), num))
		
		start = time.time()
		self.backend.host_getObjects(attributes = ['id'], ipAddress = '192.168.0.100')
		logger.notice(u"Took %.2f seconds to search ip address in %d clients" % ((time.time()-start), num))
		
		#start = time.time()
		#self.backend.host_delete(id = [])
		#logger.notice(u"Took %.2f seconds to delete %d clients" % ((time.time()-start), num))
		
		
		num = 100
		start = time.time()
		for i in range(num):
			method = random.choice((self.backend.product_createLocalboot, self.backend.product_createNetboot))
			method(
				id = 'product-%d' % i,
				productVersion = random.choice(('1.0', '2', 'xxx', '3.1', '4')),
				packageVersion = random.choice(('1', '2', 'y', '3', '10', 11, 22)),
				name = 'Product %d' % i,
				licenseRequired = random.choice((None, True, False)),
				setupScript = random.choice(('setup.ins', None)),
				uninstallScript = random.choice(('uninstall.ins', None)),
				updateScript = random.choice(('update.ins', None)),
				alwaysScript = random.choice(('always.ins', None)),
				onceScript = random.choice(('once.ins', None)),
				priority = random.choice((-100, -90, -30, 0, 30, 40, 60, 99)),
				description = random.choice(('Test product %d' % i, 'Some product', '--------', '', None)),
				advice = random.choice(('Nothing', 'Be careful', '--------', '', None)),
				changelog = None,
				productClassNames = None,
				windowsSoftwareIds = None
			)
		
		logger.notice(u"Took %.2f seconds to create %d products" % ((time.time()-start), num))
		
		#start = time.time()
		#self.backend.product_getObjects(attributes = ['id'], uninstallScript = 'uninstall.ins')
		#logger.notice(u"Took %.2f seconds to search uninstall script in %d products" % ((time.time()-start), num))
		
		for product in self.backend.product_getObjects():
			for depotId in self.backend.host_getIdents(type = 'OpsiDepotserver'):
				self.backend.productOnDepot_create(
					productId = product.id,
					productType = product.getType(),
					productVersion = product.productVersion,
					packageVersion = product.packageVersion,
					depotId = depotId
				)
		
		
		for product in self.backend.product_getObjects():
			for clientId in self.backend.host_getIdents(type = 'OpsiClient'):
				actions = ['none', None]
				if product.setupScript:     actions.append('setup')
				if product.uninstallScript: actions.append('uninstall')
				if product.onceScript:      actions.append('once')
				if product.alwaysScript:    actions.append('always')
				if product.updateScript:    actions.append('update')
				self.backend.productOnClient_create(
					productId = product.id,
					productType = product.getType(),
					clientId = clientId,
					installationStatus = random.choice(('installed', 'not_installed', None)),
					actionRequest = random.choice(actions),
					actionProgress = random.choice(('installing 100%', 'uninstalling 56%', 'something', None)),
					productVersion = product.productVersion,
					packageVersion = product.packageVersion,
					lastStateChange = None
				)
		
		logger.setConsoleLevel(consoleLevel)
	
	def testMultithreading(self):
		logger.notice(u"Starting multithreading tests")
		import threading
		
		class MultiThreadTest(threading.Thread):
			def __init__(self, backend):
				threading.Thread.__init__(self)
				self._backend = backend
				
			def run(self):
				logger.info(u"Thread %s started" % self)
				self._backend.host_getObjects()
				logger.info(u"Thread %s done" % self)
				
		for i in range(50):
			mtt = MultiThreadTest(self.backend)
			mtt.start()
			time.sleep(0.05)
		
class BackendManagerTest(BackendTest):
	def __init__(self, backendManager):
		BackendTest.__init__(self, backendManager)
	
	

















