# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH

   http://www.uib.de/

   All rights reserved.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.

   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

import os, pwd, grp, socket, MySQLdb, random, time

from fixtures import TempDir

from OPSI.tests.helper.fixture import Fixture, FQDNFixture, HwAuditConfigFixture
from OPSI.tests.helper.testcase import TestCase

from OPSI.Backend.File import FileBackend
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.SQLite import SQLiteBackend, SQLiteObjectBackendModificationTracker
from OPSI.Backend.LDAP import LDAPBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend

from OPSI.Object import *


class _BackendFixture(Fixture):

	defaultOptions = {
			'processProductPriorities':            False,
			'processProductDependencies':          False,
			'addProductOnClientDefaults':          False,
			'addProductPropertyStateDefaults':     False,
			'addConfigStateDefaults':              False,
			'deleteConfigStateIfDefault':          False,
			'returnObjectsOnUpdateAndCreate':      False
	}
	licenseManagement = False

	def __init__(self):
		super(_BackendFixture, self).__init__()
		self.options = self.defaultOptions.copy()

	def extend(self):
		self.backend = ExtendedConfigDataBackend(self.backend)

	def setUp(self):
		super(_BackendFixture, self).setUp()

		self.setupBackend()

		self.addCleanup(self.backend.backend_exit)
		self.backend.backend_setOptions(self.options)

		self.backend.backend_createBase()

	def setupBackend(self):
		raise NotImplementedError()

class BackendContentFixture(Fixture):

	def __init__(self, backend, licenseManagement=False):

		self.backend = backend
		self.licenseManagement = licenseManagement


	def setUp(self):
		super(BackendContentFixture, self).setUp()
		self.addCleanup(self.backend.backend_deleteBase)
		self.serverId = socket.getfqdn('')

		self.hwconf = self.backend.auditHardware_getConfig()
		AuditHardware.setHardwareConfig(self.hwconf)
		AuditHardwareOnHost.setHardwareConfig(self.hwconf)


		self.hosts = []
		self.configserver1 = OpsiConfigserver(
			id                  = self.serverId,
			opsiHostKey         = '71234545689056789012123678901234',
			depotLocalUrl       = 'file:///opt/pcbin/install',
			depotRemoteUrl      = u'smb://%s/opt_pcbin/install' % self.serverId.split('.')[0],
			repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
			repositoryRemoteUrl = u'webdavs://%s:4447/repository' % self.serverId,
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
			depotRemoteUrl      = 'smb://depotserver1.uib.local/opt_pcbin/install',
			repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
			repositoryRemoteUrl = 'webdavs://depotserver1.uib.local:4447/repository',
			description         = 'A depot',
			notes               = u'D€pot 1',
			hardwareAddress     = None,
			ipAddress           = None,
			inventoryNumber     = '00000000002',
			networkAddress      = '192.168.2.0/24',
			maxBandwidth        = 10000,
			isMasterDepot       = True
		)

		self.depotserver2 = OpsiDepotserver(
			id                  = 'depotserver2.uib.local',
			opsiHostKey         = '93aa22f38a678c64ef678a012d2e82f2',
			depotLocalUrl       = 'file:///opt/pcbin/install',
			depotRemoteUrl      = 'smb://depotserver2.uib.local/opt_pcbin',
			repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
			repositoryRemoteUrl = 'webdavs://depotserver2.uib.local:4447/repository',
			description         = 'Second depot',
			notes               = 'no notes here',
			hardwareAddress     = '00:01:09:07:11:aa',
			ipAddress           = '192.168.10.1',
			inventoryNumber     = '',
			networkAddress      = '192.168.10.0/24',
			maxBandwidth        = 240000,
			isMasterDepot       = True
		)

		self.depotservers = [ self.depotserver1, self.depotserver2]
		self.hosts.extend(self.depotservers)

		self.client1 = OpsiClient(
			id              = 'client1.uib.local',
			description     = 'Test client 1',
			notes           = 'Notes ...',
			hardwareAddress = '00:01:02:03:04:05',
			ipAddress       = '192.168.1.100',
			lastSeen        = '2009-01-01 00:00:00',
			opsiHostKey     = '45656789789012789012345612340123',
			inventoryNumber = "$$4"
		)

		self.client2 = OpsiClient(
			id              = 'client2.uib.local',
			description     = 'Test client 2',
			notes           = ';;;;;;;;;;;;;;',
			hardwareAddress = '00-ff0aa3:0b-B5',
			opsiHostKey     = '59051234345678890121678901223467',
			inventoryNumber = '00000000003',
			oneTimePassword = 'logmein'
		)

		self.client3 = OpsiClient(
			id              = 'client3.uib.local',
			description     = 'Test client 3',
			notes           = '#############',
			inventoryNumber = 'XYZABC_1200292'
		)

		self.client4 = OpsiClient(
			id              = 'client4.uib.local',
			description     = 'Test client 4',
		)

		self.client5 = OpsiClient(
			id              = 'client5.uib.local',
			description     = 'Test client 5',
			oneTimePassword = 'abe8327kjdsfda'
		)

		self.client6 = OpsiClient(
			id              = 'client6.uib.local',
			description     = 'Test client 6',
		)

		self.client7 = OpsiClient(
			id              = 'client7.uib.local',
			description     = 'Test client 7',
		)

		self.clients = [ self.client1, self.client2, self.client3, self.client4, self.client5, self.client6, self.client7 ]
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
			id             = u'clientconfig.depot.id',
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

		self.config6 = UnicodeConfig(
			id             = u'%username%',
			description    = u'username',
			possibleValues = None,
			defaultValues  = ['opsi']
		)

		self.config7 = UnicodeConfig(
			id             = u'product_sort_algorithm',
			description    = u'product_sort_algorithm',
			possibleValues = ["algorithm1", "algorithm2"],
			defaultValues  = ['algorithm1'],
			editable       = False
		)
		self.configs = [ self.config1, self.config2, self.config3, self.config4, self.config5, self.config6, self.config7 ]

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

		self.configState4 = ConfigState(
			configId = self.config6.getId(),
			objectId = self.client2.getId(),
			values   = ["-------- test --------\n4: %4\n1: %1\n2: %2\n5: %5"]
		)

		self.configState5 = ConfigState(
			configId = self.config4.getId(),
			objectId = self.client5.getId(),
			values   = self.depotserver2.id
		)

		self.configState6 = ConfigState(
			configId = self.config4.getId(),
			objectId = self.client6.getId(),
			values   = self.depotserver2.id
		)

		self.configState7 = ConfigState(
			configId = self.config4.getId(),
			objectId = self.client7.getId(),
			values   = self.depotserver2.id
		)

		self.configStates = [ self.configState1, self.configState2, self.configState3, self.configState4, self.configState5, self.configState6, self.configState7 ]

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
			productClassIds    = [],
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
			productClassIds    = [],
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
			productClassIds    = [],
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
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.product5 = LocalbootProduct(
			id                 = 'product5',
			name               = u'Product 5',
			productVersion     = "3.0",
			packageVersion     = 25,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			priority           = 0,
			description        = "",
			advice             = "",
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.product6 = LocalbootProduct(
			id                 = 'product6',
			name               = u'Product 6',
			productVersion     = "1.0",
			packageVersion     = 1,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			priority           = 0,
			description        = "",
			advice             = "",
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.product7 = LocalbootProduct(
			id                 = 'product7',
			name               = u'Product 7',
			productVersion     = "1.0",
			packageVersion     = 1,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			priority           = 0,
			description        = "",
			advice             = "",
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.product8 = LocalbootProduct(
			id                 = 'product7',
			name               = u'Product 7',
			productVersion     = "1.0",
			packageVersion     = 2,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			customScript       = "custom.ins",
			priority           = 0,
			description        = "",
			advice             = "",
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.product9 = LocalbootProduct(
			id                 = 'product9',
			name               = u'Product 9',
			productVersion     = "1.0",
			packageVersion     = 2,
			licenseRequired    = False,
			setupScript        = "setup.ins",
			uninstallScript    = "uninstall.ins",
			updateScript       = None,
			alwaysScript       = None,
			onceScript         = None,
			customScript       = "custom.ins",
			priority           = 0,
			description        = "",
			advice             = "",
			productClassIds    = [],
			windowsSoftwareIds = []
		)

		self.localbootProducts = [ self.product2, self.product3, self.product4, self.product5, self.product6, self.product7, self.product8, self.product9 ]
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

		self.productProperty4 = UnicodeProductProperty(
			productId      = self.product1.id,
			productVersion = self.product1.productVersion,
			packageVersion = self.product1.packageVersion,
			propertyId     = u"i386_dir",
			description    = u'i386 dir to use as installation source',
			possibleValues = ["i386"],
			defaultValues  = ["i386"],
			editable       = True,
			multiValue     = False
		)

		self.productProperties = [ self.productProperty1, self.productProperty2, self.productProperty3, self.productProperty4 ]

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
			requirementType            = 'before'
		)

		self.productDependency3 = ProductDependency(
			productId                  = self.product4.id,
			productVersion             = self.product4.productVersion,
			packageVersion             = self.product4.packageVersion,
			productAction              = 'setup',
			requiredProductId          = self.product5.id,
			requiredProductVersion     = None,
			requiredPackageVersion     = None,
			requiredAction             = None,
			requiredInstallationStatus = 'installed',
			requirementType            = 'before'
		)

		self.productDependency4 = ProductDependency(
			productId                  = self.product6.id,
			productVersion             = self.product6.productVersion,
			packageVersion             = self.product6.packageVersion,
			productAction              = 'setup',
			requiredProductId          = self.product7.id,
			requiredProductVersion     = self.product7.productVersion,
			requiredPackageVersion     = self.product7.packageVersion,
			requiredAction             = None,
			requiredInstallationStatus = 'installed',
			requirementType            = 'after'
		)

		self.productDependency5 = ProductDependency(
			productId                  = self.product7.id,
			productVersion             = self.product7.productVersion,
			packageVersion             = self.product7.packageVersion,
			productAction              = 'setup',
			requiredProductId          = self.product9.id,
			requiredProductVersion     = None,
			requiredPackageVersion     = None,
			requiredAction             = None,
			requiredInstallationStatus = 'installed',
			requirementType            = 'after'
		)

		self.productDependencies = [ self.productDependency1, self.productDependency2, self.productDependency3, self.productDependency4, self.productDependency5 ]

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

		self.productOnDepot4 = ProductOnDepot(
			productId      = self.product3.getId(),
			productType    = self.product3.getType(),
			productVersion = self.product3.getProductVersion(),
			packageVersion = self.product3.getPackageVersion(),
			depotId        = self.configserver1.getId(),
			locked         = False
		)

		self.productOnDepot4 = ProductOnDepot(
			productId      = self.product3.getId(),
			productType    = self.product3.getType(),
			productVersion = self.product3.getProductVersion(),
			packageVersion = self.product3.getPackageVersion(),
			depotId        = self.configserver1.getId(),
			locked         = False
		)
		self.productOnDepot5 = ProductOnDepot(
			productId      = self.product5.getId(),
			productType    = self.product5.getType(),
			productVersion = self.product5.getProductVersion(),
			packageVersion = self.product5.getPackageVersion(),
			depotId        = self.configserver1.getId(),
			locked         = False
		)

		self.productOnDepot6 = ProductOnDepot(
			productId      = self.product6.getId(),
			productType    = self.product6.getType(),
			productVersion = self.product6.getProductVersion(),
			packageVersion = self.product6.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)

		self.productOnDepot7 = ProductOnDepot(
			productId      = self.product6.getId(),
			productType    = self.product6.getType(),
			productVersion = self.product6.getProductVersion(),
			packageVersion = self.product6.getPackageVersion(),
			depotId        = self.depotserver2.getId(),
			locked         = False
		)

		self.productOnDepot8 = ProductOnDepot(
			productId      = self.product7.getId(),
			productType    = self.product7.getType(),
			productVersion = self.product7.getProductVersion(),
			packageVersion = self.product7.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)

		self.productOnDepot9 = ProductOnDepot(
			productId      = self.product8.getId(),
			productType    = self.product8.getType(),
			productVersion = self.product8.getProductVersion(),
			packageVersion = self.product8.getPackageVersion(),
			depotId        = self.depotserver2.getId(),
			locked         = False
		)

		self.productOnDepot10 = ProductOnDepot(
			productId      = self.product9.getId(),
			productType    = self.product9.getType(),
			productVersion = self.product9.getProductVersion(),
			packageVersion = self.product9.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)

		self.productOnDepot11 = ProductOnDepot(
			productId      = self.product9.getId(),
			productType    = self.product9.getType(),
			productVersion = self.product9.getProductVersion(),
			packageVersion = self.product9.getPackageVersion(),
			depotId        = self.depotserver2.getId(),
			locked         = False
		)

		self.productOnDepot12 = ProductOnDepot(
			productId      = self.product4.getId(),
			productType    = self.product4.getType(),
			productVersion = self.product4.getProductVersion(),
			packageVersion = self.product4.getPackageVersion(),
			depotId        = self.configserver1.getId(),
			locked         = False
		)

		self.productOnDepot13 = ProductOnDepot(
			productId      = self.product4.getId(),
			productType    = self.product4.getType(),
			productVersion = self.product4.getProductVersion(),
			packageVersion = self.product4.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)

		self.productOnDepot14 = ProductOnDepot(
			productId      = self.product4.getId(),
			productType    = self.product4.getType(),
			productVersion = self.product4.getProductVersion(),
			packageVersion = self.product4.getPackageVersion(),
			depotId        = self.depotserver2.getId(),
			locked         = False
		)

		self.productOnDepot15 = ProductOnDepot(
			productId      = self.product5.getId(),
			productType    = self.product5.getType(),
			productVersion = self.product5.getProductVersion(),
			packageVersion = self.product5.getPackageVersion(),
			depotId        = self.depotserver1.getId(),
			locked         = False
		)

		self.productOnDepots = [ self.productOnDepot1, self.productOnDepot2, self.productOnDepot3, self.productOnDepot4, self.productOnDepot5,
					 self.productOnDepot6, self.productOnDepot7, self.productOnDepot8, self.productOnDepot9, self.productOnDepot10,
					 self.productOnDepot11, self.productOnDepot12, self.productOnDepot13, self.productOnDepot14, self.productOnDepot15 ]

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
			modificationTime   = '2009-07-01 12:00:00'
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
			actionProgress     = 'running',
			productVersion     = self.product2.getProductVersion(),
			packageVersion     = self.product2.getPackageVersion()
		)

		self.productOnClient4 = ProductOnClient(
			productId           = self.product1.getId(),
			productType         = self.product1.getType(),
			clientId            = self.client3.getId(),
			targetConfiguration = 'installed',
			installationStatus  = 'installed',
			actionRequest       = 'none',
			lastAction          = 'setup',
			actionProgress      = '',
			actionResult        = 'successful',
			productVersion      = self.product1.getProductVersion(),
			packageVersion      = self.product1.getPackageVersion()
		)

		self.productOnClients = [ self.productOnClient1, self.productOnClient2, self.productOnClient3, self.productOnClient4 ]

		# ProductPropertyStates
		self.productPropertyState1 = ProductPropertyState(
			productId  = self.productProperty1.getProductId(),
			propertyId = self.productProperty1.getPropertyId(),
			objectId   = self.depotserver1.getId(),
			values     = 'unicode-depot-default'
		)

		self.productPropertyState2 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.depotserver1.getId(),
			values     = [ True ]
		)

		self.productPropertyState3 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.depotserver2.getId(),
			values     = False
		)

		self.productPropertyState4 = ProductPropertyState(
			productId  = self.productProperty1.getProductId(),
			propertyId = self.productProperty1.getPropertyId(),
			objectId   = self.client1.getId(),
			values     = 'unicode1'
		)

		self.productPropertyState5 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.client1.getId(),
			values     = [ False ]
		)

		self.productPropertyState6 = ProductPropertyState(
			productId  = self.productProperty2.getProductId(),
			propertyId = self.productProperty2.getPropertyId(),
			objectId   = self.client2.getId(),
			values     = True
		)

		self.productPropertyStates = [ self.productPropertyState1, self.productPropertyState2, self.productPropertyState3, self.productPropertyState4, self.productPropertyState5, self.productPropertyState6 ]

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
			id            = u'group xxxxxx',
			description   = 'HostGroup xxxxxx',
			notes         = '',
			parentGroupId = None
		)

		self.group4 = ProductGroup(
			id            = u'product group 1',
			description   = 'Product Group 1',
			notes         = '----------- notes --------------',
			parentGroupId = None
		)

		self.group5 = ProductGroup(
			id            = u'product group 2',
			description   = 'Product Group 2',
			notes         = None,
			parentGroupId = u'product group 1',
		)

		self.group6 = ProductGroup(
			id            = u'group xxxxxx',
			description   = 'ProductGroup xxxxxx',
			notes         = '',
			parentGroupId = None
		)

		self.groups = [ self.group1, self.group2, self.group3, self.group4, self.group5, self.group6 ]

		# ObjectToGroups
		self.objectToGroup1 = ObjectToGroup(
			groupType = self.group1.getType(),
			groupId   = self.group1.getId(),
			objectId  = self.client1.getId()
		)

		self.objectToGroup2 = ObjectToGroup(
			groupType = self.group1.getType(),
			groupId   = self.group1.getId(),
			objectId  = self.client2.getId()
		)

		self.objectToGroup3 = ObjectToGroup(
			groupType = self.group2.getType(),
			groupId   = self.group2.getId(),
			objectId  = self.client2.getId()
		)

		self.objectToGroup4 = ObjectToGroup(
			groupType = self.group4.getType(),
			groupId   = self.group4.getId(),
			objectId  = self.product1.getId()
		)

		self.objectToGroup5 = ObjectToGroup(
			groupType = self.group4.getType(),
			groupId   = self.group4.getId(),
			objectId  = self.product2.getId()
		)

		self.objectToGroup6 = ObjectToGroup(
			groupType = self.group6.getType(),
			groupId   = self.group6.getId(),
			objectId  = self.product3.getId()
		)

		self.objectToGroups = [ self.objectToGroup1, self.objectToGroup2, self.objectToGroup3, self.objectToGroup4, self.objectToGroup5, self.objectToGroup6 ]

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
			productIds         = self.product1.getId()
		)

		self.licensePool2 = LicensePool(
			id                 = u'license_pool_2',
			description        = u'licenses for product2',
			productIds         = self.product2.getId()
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

		# AuditSoftwares
		self.auditSoftware1 = AuditSoftware(
			name                  = 'A software',
			version               = '1.0.21',
			subVersion            = '',
			language              = '',
			architecture          = '',
			windowsSoftwareId     = '{480aa013-93a7-488c-89c3-b985b6c8440a}',
			windowsDisplayName    = 'A Software',
			windowsDisplayVersion = '1.0.21',
			installSize           = 129012992
		)

		self.auditSoftware2 = AuditSoftware(
			name                  = self.product2.getName(),
			version               = self.product2.getProductVersion(),
			subVersion            = '',
			language              = 'de',
			architecture          = 'x64',
			windowsSoftwareId     = self.product2.getWindowsSoftwareIds()[0],
			windowsDisplayName    = self.product2.getName(),
			windowsDisplayVersion = self.product2.getProductVersion(),
			installSize           = 217365267
		)

		self.auditSoftware3 = AuditSoftware(
			name                  = 'my software',
			version               = '',
			subVersion            = '12;00;01',
			language              = '',
			architecture          = '',
			windowsSoftwareId     = 'my software',
			windowsDisplayName    = '',
			windowsDisplayVersion = '',
			installSize           = -1
		)

		self.auditSoftware4 = AuditSoftware(
			name                  = 'söftwäre\n;?&%$$$§$§§$$$§$',
			version               = u'\\0012',
			subVersion            = '\n',
			language              = 'de',
			architecture          = '',
			windowsSoftwareId     = 'söftwäre\n;?&%$$$§$§§$$$§$',
			windowsDisplayName    = 'söftwäre\n;?&%$$$§$§§$$$§$',
			windowsDisplayVersion = '\n\r',
			installSize           = -1
		)

		self.auditSoftwares = [self.auditSoftware1, self.auditSoftware2, self.auditSoftware3, self.auditSoftware4]

		# AuditSoftwareToLicensePools
		self.auditSoftwareToLicensePool1 = AuditSoftwareToLicensePool(
			name          = self.auditSoftware1.name,
			version       = self.auditSoftware1.version,
			subVersion    = self.auditSoftware1.subVersion,
			language      = self.auditSoftware1.language,
			architecture  = self.auditSoftware1.architecture,
			licensePoolId = self.licensePool1.id
		)

		self.auditSoftwareToLicensePool2 = AuditSoftwareToLicensePool(
			name          = self.auditSoftware2.name,
			version       = self.auditSoftware2.version,
			subVersion    = self.auditSoftware2.subVersion,
			language      = self.auditSoftware2.language,
			architecture  = self.auditSoftware2.architecture,
			licensePoolId = self.licensePool2.id
		)

		self.auditSoftwareToLicensePools = [self.auditSoftwareToLicensePool1, self.auditSoftwareToLicensePool2]

		# AuditSoftwareOnClients
		self.auditSoftwareOnClient1 = AuditSoftwareOnClient(
			name            = self.auditSoftware1.getName(),
			version         = self.auditSoftware1.getVersion(),
			subVersion      = self.auditSoftware1.getSubVersion(),
			language        = self.auditSoftware1.getLanguage(),
			architecture    = self.auditSoftware1.getArchitecture(),
			clientId        = self.client1.getId(),
			uninstallString = 'c:\\programme\\a software\\unistall.exe /S',
			binaryName      = u'',
			firstseen       = None,
			lastseen        = None,
			state           = None,
			usageFrequency  = 2,
			lastUsed        = '2009-02-12 09:48:22'
		)

		self.auditSoftwareOnClient2 = AuditSoftwareOnClient(
			name            = self.auditSoftware2.getName(),
			version         = self.auditSoftware2.getVersion(),
			subVersion      = self.auditSoftware2.getSubVersion(),
			language        = self.auditSoftware2.getLanguage(),
			architecture    = self.auditSoftware2.getArchitecture(),
			clientId        = self.client1.getId(),
			uninstallString = 'msiexec /x %s' % self.auditSoftware2.getWindowsSoftwareId(),
			binaryName      = u'',
			firstseen       = None,
			lastseen        = None,
			state           = None,
			usageFrequency  = None,
			lastUsed        = None
		)

		self.auditSoftwareOnClient3 = AuditSoftwareOnClient(
			name            = self.auditSoftware3.getName(),
			version         = self.auditSoftware3.getVersion(),
			subVersion      = self.auditSoftware3.getSubVersion(),
			language        = self.auditSoftware3.getLanguage(),
			architecture    = self.auditSoftware3.getArchitecture(),
			clientId        = self.client1.getId(),
			uninstallString = None,
			firstseen       = None,
			lastseen        = None,
			state           = None,
			usageFrequency  = 0,
			lastUsed        = '2009-08-01 14:11:00'
		)

		self.auditSoftwareOnClient4 = AuditSoftwareOnClient(
			name            = self.auditSoftware2.getName(),
			version         = self.auditSoftware2.getVersion(),
			subVersion      = self.auditSoftware2.getSubVersion(),
			language        = self.auditSoftware2.getLanguage(),
			architecture    = self.auditSoftware2.getArchitecture(),
			clientId        = self.client2.getId(),
			firstseen       = None,
			lastseen        = None,
			state           = None,
			usageFrequency  = 0,
			lastUsed        = None
		)
		self.auditSoftwareOnClients = [self.auditSoftwareOnClient1, self.auditSoftwareOnClient2, self.auditSoftwareOnClient3, self.auditSoftwareOnClient4]


		# AuditHardwares
		self.auditHardware1 = AuditHardware(
			hardwareClass       = 'COMPUTER_SYSTEM',
			description         = 'a pc',
			vendor              = 'Dell',
			model               = 'xyz',
		)

		self.auditHardware2 = AuditHardware(
			hardwareClass       = 'COMPUTER_SYSTEM',
			description         =  None,
			vendor              = 'HP',
			model               = '0815',
		)

		self.auditHardware3 = AuditHardware(
			hardwareClass       = 'BASE_BOARD',
			name                = 'MSI 2442',
			description         = 'AMD motherboard',
			vendor              = 'MSI',
			model               = 'äüöüöäüöüäüööüö11',
			product             = None
		)

		self.auditHardware4 = AuditHardware(
			hardwareClass       = 'CHASSIS',
			name                = 'Manufacturer XX-112',
			description         = 'A chassis',
			chassisType         = 'Desktop'
		)

		self.auditHardware5 = AuditHardware(
			hardwareClass       = 'PROCESSOR',
			name                = '0',
			description         = 'processor long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long long'
		)

		self.auditHardware6 = AuditHardware(
			hardwareClass       = 'PROCESSOR',
			name                = '0',
			description         = None
		)

		self.auditHardwares = [ self.auditHardware1, self.auditHardware2, self.auditHardware3, self.auditHardware4, self.auditHardware5, self.auditHardware6 ]

		# AuditHardwareOnHosts
		self.auditHardwareOnHost1 = AuditHardwareOnHost(
			hostId              = self.client1.getId(),
			hardwareClass       = 'COMPUTER_SYSTEM',
			description         = self.auditHardware1.description,
			vendor              = self.auditHardware1.vendor,
			model               = self.auditHardware1.model,

			serialNumber        = '843391034-2192',
			systemType          = 'Desktop',
			totalPhysicalMemory = 1073741824
		)

		self.auditHardwareOnHost2 = AuditHardwareOnHost(
			hostId              = self.client2.getId(),
			hardwareClass       = 'COMPUTER_SYSTEM',
			description         = self.auditHardware1.description,
			vendor              = self.auditHardware1.vendor,
			model               = self.auditHardware1.model,

			serialNumber        = '142343234-9571',
			systemType          = 'Desktop',
			totalPhysicalMemory = 1073741824
		)

		self.auditHardwareOnHost3 = AuditHardwareOnHost(
			hostId              = self.client3.getId(),
			hardwareClass       = 'COMPUTER_SYSTEM',
			description         = self.auditHardware2.description,
			vendor              = self.auditHardware2.vendor,
			model               = self.auditHardware2.model,

			serialNumber        = 'a63c09dd234a213',
			systemType          = None,
			totalPhysicalMemory = 536870912
		)

		self.auditHardwareOnHost4 = AuditHardwareOnHost(
			hostId              = self.client1.getId(),
			hardwareClass       = 'BASE_BOARD',
			name                = self.auditHardware3.name,
			description         = self.auditHardware3.description,
			vendor              = self.auditHardware3.vendor,
			model               = self.auditHardware3.model,
			product             = self.auditHardware3.product,

			serialNumber        = 'xxxx-asjdks-sll3kf03-828112'
		)

		self.auditHardwareOnHost5 = AuditHardwareOnHost(
			hostId              = self.client2.getId(),
			hardwareClass       = 'BASE_BOARD',
			name                = self.auditHardware3.name,
			description         = self.auditHardware3.description,
			vendor              = self.auditHardware3.vendor,
			model               = self.auditHardware3.model,
			product             = self.auditHardware3.product,

			serialNumber        = 'xxxx-asjdks-sll3kf03-213791'
		)

		self.auditHardwareOnHost6 = AuditHardwareOnHost(
			hostId              = self.client3.getId(),
			hardwareClass       = 'BASE_BOARD',
			name                = self.auditHardware3.name,
			description         = self.auditHardware3.description,
			vendor              = self.auditHardware3.vendor,
			model               = self.auditHardware3.model,
			product             = self.auditHardware3.product,

			serialNumber        = 'xxxx-asjdks-sll3kf03-132290'
		)

		self.auditHardwareOnHost7 = AuditHardwareOnHost(
			hostId              = self.client3.getId(),
			hardwareClass       = 'PROCESSOR',
			name                = self.auditHardware5.name,
			description         = self.auditHardware5.description,

			serialNumber        = '4325345325132290'
		)

		self.auditHardwareOnHosts = [ self.auditHardwareOnHost1, self.auditHardwareOnHost2, self.auditHardwareOnHost3,
						self.auditHardwareOnHost4, self.auditHardwareOnHost5, self.auditHardwareOnHost6, self.auditHardwareOnHost7 ]
		self.backend.host_createObjects( self.hosts )
		self.backend.host_createObjects( self.depotservers )
		self.backend.config_createObjects( self.configs )
		self.backend.configState_createObjects( self.configStates )
		self.backend.product_createObjects( self.products )
		self.backend.productProperty_createObjects(self.productProperties)
		self.backend.productDependency_createObjects(self.productDependencies)
		self.backend.productOnDepot_createObjects(self.productOnDepots)
		self.backend.productOnClient_createObjects(self.productOnClients)
		self.backend.productPropertyState_createObjects(self.productPropertyStates)
		self.backend.group_createObjects(self.groups)
		self.backend.objectToGroup_createObjects(self.objectToGroups)
		self.backend.auditSoftware_createObjects(self.auditSoftwares)
		self.backend.auditSoftwareOnClient_createObjects(self.auditSoftwareOnClients)
		self.backend.auditHardware_createObjects(self.auditHardwares)
		self.backend.auditHardwareOnHost_createObjects(self.auditHardwareOnHosts)
		if self.licenseManagement:
			self.backend.licenseContract_createObjects(self.licenseContracts)
			self.backend.softwareLicense_createObjects(self.softwareLicenses)
			self.backend.licensePool_createObjects(self.licensePools)
			self.backend.softwareLicenseToLicensePool_createObjects(self.softwareLicenseToLicensePools)
			self.backend.licenseOnClient_createObjects(self.licenseOnClients)

class FileBackendConfigFixtire(Fixture):

	template = None


class FileBackendFixture(_BackendFixture):

	def __init__(self, baseDir=None, hostKeyFile=None):

		super(FileBackendFixture, self).__init__()

		self.env = os.environ.copy()
		self.uid = self.gid = self.env["USER"]

		self.baseDir = baseDir
		self.hostKeyFile = hostKeyFile

	def setupBackend(self):

		hw = HwAuditConfigFixture()

		self.useFixture(hw)

		if self.baseDir is None:
			bd = self.useFixture(TempDir())
			self.baseDir = bd.path
		if self.hostKeyFile is None:
			hkf = self.useFixture(TempDir())
			self.hostKeyFile = os.path.join(hkf.path, "pckeys")


		self.backend = FileBackend(baseDir=self.baseDir, hostKeyFile=self.hostKeyFile, audithardwareconfigfile=hw.path)

		self.test.patch(self.backend, "__fileUid", pwd.getpwnam(self.uid)[2])
		self.test.patch(self.backend, "__fileGid", grp.getgrnam(self.gid)[2])
		self.test.patch(self.backend, "__dirUid", pwd.getpwnam(self.uid)[2])
		self.test.patch(self.backend, "__dirGid", grp.getgrnam(self.gid)[2])

		self.test.patch(self.backend, "__fileUser", self.uid)
		self.test.patch(self.backend, "__fileGroup", self.gid)
		self.test.patch(self.backend, "__dirUser", self.uid)
		self.test.patch(self.backend, "__dirGroup", self.gid)

		self.extend()

	def setOptions(self, options):
		self.options.update(options)
		self.backend.backend_setOptions(self.options)


class MySQLBackendFixture(_BackendFixture):

	defaultOptions = {
			'processProductPriorities':            True,
			'processProductDependencies':          True,
			'addProductOnClientDefaults':          True,
			'addProductPropertyStateDefaults':     True,
			'addConfigStateDefaults':              True,
			'deleteConfigStateIfDefault':          True,
			'returnObjectsOnUpdateAndCreate':      False
	}
	licenseManagement = True

	def __init__(self, username, password, database=None, hostname="localhost"):
		super(MySQLBackendFixture, self).__init__()
		self.username = username
		self.password = password
		self.database = database
		self.hostname = hostname


	def setupBackend(self):

		hw = HwAuditConfigFixture()

		self.useFixture(hw)

		if not self.database:
			random.SystemRandom(time.clock()*1234567)
			self.database = "opsitest%s" % str(random.randint(1000000, 10000000))
		con = MySQLdb.connect(user=self.username, passwd=self.password)
		c = con.cursor()
		c.execute("CREATE DATABASE %s" % self.database)

		c.close()
		con.close()
		self.addCleanup(self._dropDatabase)

		self.backend = self.mb = MySQLBackend(
						username = self.username,
						password = self.password,
						database = self.database,
						address = self.hostname,
						audithardwareconfigfile=hw.path
						)
		self.extend()

	def _dropDatabase(self):
		con = MySQLdb.connect(user=self.username, passwd=self.password)
		c = con.cursor()
		c.execute("DROP DATABASE IF EXISTS %s" % self.database)
		c.close()
		con.close()
		self.database = None
		self.mb._sql._pool.destroy()
		del self.mb._sql._pool


class BackendTestCase(TestCase):

	inventoryHistory = False

	def setUp(self):
		super(TestCase, self).setUp()

		self.useFixture(FQDNFixture('opsi-test-server.uib.local'))
