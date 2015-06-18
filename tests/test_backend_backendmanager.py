#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing BackendManager.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import shutil
import unittest

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.BackendManager import BackendManager, ConfigDataBackend
from OPSI.Util import objectToBeautifiedText

from .Backends.File import FileBackendMixin
from .BackendTestMixins.Backend import BackendTestsMixin
from .BackendTestMixins.Configs import ConfigTestsMixin, ConfigStateTestsMixin
from .BackendTestMixins.Groups import GroupTestsMixin
from .BackendTestMixins.Products import ProductsTestMixin, ProductsOnDepotMixin

from .helpers import getLocalFQDN


class BackendExtensionTestCase(unittest.TestCase):
    def testBackendManagerDispatchesCallsToExtensionClass(self):
        """
        Make sure that calls are dispatched to the extension class.
        These calls should not fail.
        """
        class TestClass(object):
            def testMethod(self, y):
                print("Working test.")
                print('Argument: {0}'.format(y))
                print('This is me: {0}'.format(self))

            def testMethod2(self):
                print('Getting all that shiny options...')
                print(self.backend_getOptions())

        cdb = ConfigDataBackend()
        bm = BackendManager(backend=cdb, extensionClass=TestClass)
        bm.testMethod('yyyyyyyy')
        bm.testMethod2()


class ExtendedBackendManagerTestCase(unittest.TestCase, FileBackendMixin,
        BackendTestsMixin, ProductsTestMixin, ProductsOnDepotMixin, ConfigTestsMixin,
        ConfigStateTestsMixin, GroupTestsMixin):

    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testBackendManager(self):
        bm = BackendManager(
            backend=self.backend,
            extensionconfigdir=os.path.join(self._fileTempDir, self.BACKEND_SUBFOLDER, 'backendManager', 'extend.d')
        )

        self.testObjectMethods()

        if False:

            with open(aclFile, 'w') as f:
                f.write('''
        .*: opsi_depotserver
''')

            bm = BackendManager(
                dispatchConfigFile = dispatchConfigFile,
                backendConfigDir   = backendConfigDir,
                username           = self.configserver1.getId(),
                password           = self.configserver1.getOpsiHostKey(),
                aclFile            = aclFile)

        # def testComposition():
        # bm = BackendManager(
        #     dispatchConfigFile = dispatchConfigFile,
        #     backendConfigDir   = backendConfigDir,
        #     extensionconfigdir = extensionConfigDir,
        #     username           = self.configserver1.getId(),
        #     password           = self.configserver1.getOpsiHostKey(),
        #     aclFile            = aclFile)

        hostIds = bm.host_getIdents()
        print(hostIds)
        for host in self.hosts:
            assert host.id in hostIds

        generalConfig = bm.getGeneralConfig_hash()
        print(generalConfig)

        generalConfig = bm.getGeneralConfig_hash(objectId = self.client1.id)
        print(generalConfig)

        self.setUpConfigs()
        self.createConfigOnBackend()
        value = bm.getGeneralConfigValue(key = self.config1.id, objectId = None)
        print(value)
        assert value == self.config1.defaultValues[0]

        generalConfig = {'test-key-1': 'test-value-1', 'test-key-2': 'test-value-2', 'opsiclientd.depot_server.depot_id': self.depotserver1.id}
        bm.setGeneralConfig(config = generalConfig, objectId = None)

        value = bm.getGeneralConfigValue(key = generalConfig.keys()[0], objectId = self.client1.id)
        print(value)
        assert value == generalConfig[generalConfig.keys()[0]]

        bm.setGeneralConfigValue(generalConfig.keys()[1], self.client1.id, objectId = self.client1.id)
        bm.setGeneralConfigValue(generalConfig.keys()[1], 'changed', objectId = None)
        value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = None)
        print(value)
        assert value == 'changed'
        value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = self.client1.id)
        print(value)
        assert value == self.client1.id

        bm.deleteGeneralConfig(self.client1.id)
        value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = self.client1.id)
        print(value)
        assert value == 'changed'

        self.setUpGroups()
        self.createGroupsOnBackend()

        groupIds = bm.getGroupIds_list()
        print(groupIds)
        for group in self.groups:
            assert group.id in groupIds

        groupId = 'a test group'
        bm.createGroup(groupId, members = [ self.client1.id, self.client2.id ], description = "A test group", parentGroupId="")
        groups = bm.group_getObjects(id = groupId)
        print(groups)
        assert len(groups) == 1

        objectToGroups = bm.objectToGroup_getObjects(groupId = groupId)
        print(objectToGroups)
        assert len(objectToGroups) == 2
        for objectToGroup in objectToGroups:
            assert objectToGroup.objectId in [ self.client1.id, self.client2.id ]

        bm.deleteGroup(groupId = groupId)
        groups = bm.group_getObjects(id = groupId)
        assert len(groups) == 0

        ipAddress = bm.getIpAddress(hostId = self.client1.id)
        print(ipAddress)
        assert ipAddress == self.client1.ipAddress

        serverName, domain = getLocalFQDN().split('.', 1)
        serverId = bm.createServer(serverName = serverName, domain = domain, description = 'Some description', notes=None)
        print(serverId)
        assert serverId == serverName + '.' + domain

        serverIds = bm.host_getIdents(type = 'OpsiConfigserver')
        print(serverIds)
        assert serverId in serverIds

        clientName = 'test-client'
        clientId = bm.createClient(clientName = clientName, domain = domain, description = 'a description', notes = 'notes...', ipAddress = '192.168.1.91', hardwareAddress = '00:01:02:03:01:aa')
        print(clientId)
        assert clientId == clientName + '.' + domain

        clientIds = bm.host_getIdents(type = 'OpsiClient')
        print(clientIds)
        assert clientId in clientIds

        # TODO: check what is wrong here
        # bm.deleteServer(serverId)
        # serverIds = bm.host_getIdents(type = 'OpsiConfigserver')
        # print(serverIds)
        # assert serverId not in serverIds

        bm.deleteClient(clientId)
        clientIds = bm.host_getIdents(type = 'OpsiClient')
        print(clientIds)
        assert clientId not in clientIds

        lastSeen = '2009-01-01 00:00:00'
        description = 'Updated description'
        notes = 'Updated notes'
        opsiHostKey = '00000000001111111111222222222233'
        mac = '00:01:02:03:40:12'
        bm.setHostLastSeen(hostId = self.client1.id, timestamp = lastSeen)
        bm.setHostDescription(hostId = self.client1.id, description = description)
        bm.setHostNotes(hostId = self.client1.id, notes = notes)
        bm.setOpsiHostKey(hostId = self.client1.id, opsiHostKey = opsiHostKey)
        bm.setMacAddress(hostId = self.client1.id, mac = mac)

        host = bm.host_getObjects(id = self.client1.id)[0]
        print(host.lastSeen)
        print(host.description)
        print(host.notes)
        print(host.opsiHostKey)
        print(host.hardwareAddress)

        assert lastSeen == host.lastSeen
        assert description == host.description
        assert notes == host.notes
        assert opsiHostKey == host.opsiHostKey
        assert mac == host.hardwareAddress

        res = bm.getOpsiHostKey(hostId = self.client1.id)
        print(res)
        assert opsiHostKey == res

        res = bm.getMacAddress(hostId = self.client1.id)
        print(res)
        assert mac == res

        host = bm.getHost_hash(hostId = self.client1.id)
        print(host)

        serverIds = bm.getServerIds_list()
        print(serverIds)

        serverId = bm.getServerId(clientId = self.client1.id)
        print(serverId)

        depotName = 'test-depot'
        depotName = self.depotserver1.id.split('.', 1)[0]

        depotRemoteUrl = 'smb://{0}/xyz'.format(depotName)
        depotId = bm.createDepot(
            depotName = depotName,
            domain = domain,
            depotLocalUrl = 'file:///xyz',
            depotRemoteUrl = depotRemoteUrl,
            repositoryLocalUrl = 'file:///abc',
            repositoryRemoteUrl = 'webdavs://{0}:4447/products'.format(depotName),
            network = '0.0.0.0/0',
            description = 'Some description',
            notes = 'Some notes',
            maxBandwidth = 100000
        )
        print(depotId)
        assert depotId == depotName + '.' + domain

        depotIds = bm.getDepotIds_list()
        print(depotIds)

        depot = bm.getDepot_hash(depotId)
        print(depot)
        assert depot['depotRemoteUrl'] == depotRemoteUrl

        bm.deleteDepot(depotId)
        depotIds = bm.getDepotIds_list()
        print(depotIds)
        assert not depotId in depotIds

        self.setUpProducts()
        self.createProductsOnBackend()

        depotserver1 = {
            "isMasterDepot" : True,
            "type" : "OpsiDepotserver",
            "id" : self.depotserver1.id,
        }
        self.backend.host_createObjects(depotserver1)

        self.setUpProductOnDepots()
        self.backend.productOnDepot_createObjects(self.productOnDepots)

        bm.lockProduct(productId = self.product1.id, depotIds = [ self.depotserver1.id ])
        productLocks = bm.getProductLocks_hash(depotIds = [])
        print(productLocks)
        for (prductId, depotIds) in productLocks.items():
            assert prductId == self.product1.id
            assert len(depotIds) == 1
            assert depotIds[0] == self.depotserver1.id

        bm.unlockProduct(productId = self.product1.id, depotIds = [])
        productLocks = bm.getProductLocks_hash(depotIds = [])
        print(productLocks)
        assert not productLocks

        productId1 = 'test-localboot-1'
        bm.createLocalBootProduct(productId = productId1, name = 'Some localboot product', productVersion = '1.0', packageVersion = '1', licenseRequired=0,
               setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
               priority=0, description="", advice="", windowsSoftwareIds=[], depotIds=[])

        productId2 = 'test-netboot-1'
        bm.createNetBootProduct(productId = productId2, name = 'Some localboot product', productVersion = '1.0', packageVersion = '1', licenseRequired=0,
               setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
               priority=0, description="", advice="", pxeConfigTemplate = 'some_template', windowsSoftwareIds=[], depotIds=[])

        productIdents = bm.product_getIdents(returnType = 'tuple')
        print(productIdents)
        assert (productId1,'1.0','1') in productIdents
        assert (productId2,'1.0','1') in productIdents

        product = bm.getProduct_hash(productId = productId1, depotId = self.depotserver1.id)
        print(product)

        products = bm.getProducts_hash()
        print(objectToBeautifiedText(products))

        products = bm.getProducts_listOfHashes()
        print(objectToBeautifiedText(products))

        products = bm.getProducts_listOfHashes(depotId = self.depotserver1.id)
        print(objectToBeautifiedText(products))

        for client in self.clients:
            productIds = bm.getInstalledProductIds_list(objectId = client.id)
            print(productIds)

            productIds = bm.getInstalledLocalBootProductIds_list(objectId = client.id)
            print(productIds)

            productIds = bm.getInstalledNetBootProductIds_list(objectId = client.id)
            print(productIds)

        productIds = bm.getProvidedLocalBootProductIds_list(depotId = self.depotserver1.id)
        print(productIds)

        productIds = bm.getProvidedNetBootProductIds_list(depotId = self.depotserver1.id)
        print(productIds)

        for client in self.clients:
            status = bm.getProductInstallationStatus_hash(productId = self.product1.id, objectId = client.id)
            print(status)

        self.backend.config_createObjects([{
            "id": u'clientconfig.depot.id',
            "type": "UnicodeConfig",
        }])
        self.backend.configState_create(u'clientconfig.depot.id', client.id, values=[depotId])
        print("asdasda {0}".format(self.backend.configState_getObjects()))

        bm.setProductState(productId = self.product1.id, objectId = client.id, installationStatus = "not_installed", actionRequest = "setup")
        bm.setProductInstallationStatus(productId = self.product1.id, objectId = client.id, installationStatus = "installed")
        bm.setProductActionProgress(productId = self.product1.id, hostId = client.id, productActionProgress = "something 90%")
        bm.setProductActionRequest(productId = self.product1.id, clientId = client.id, actionRequest = 'uninstall')

        print("asdasda {0}".format(self.backend.configState_getObjects()))

        for product in self.products:
            actions = bm.getPossibleProductActions_list(productId = product.id)
            print(actions)

        actions = bm.getPossibleProductActions_hash()
        print(actions)

        depotId = bm.getDepotId(clientId = client.id)
        print(depotId)
        assert depotId == self.depotserver1.id

        clientId = bm.getClientIdByMac(mac = self.client2.hardwareAddress)
        print(self.client2.id)
        assert clientId == self.client2.id

        productIds = bm.getInstallableProductIds_list(clientId = client.id)
        print(productIds)

        productIds = bm.getInstallableLocalBootProductIds_list(clientId = client.id)
        print(productIds)

        productIds = bm.getInstallableNetBootProductIds_list(clientId = client.id)
        print(productIds)

        status = bm.getProductInstallationStatus_listOfHashes(objectId = client.id)
        print(status)

        actions = bm.getProductActionRequests_listOfHashes(clientId = client.id)
        print(actions)

        states = bm.getLocalBootProductStates_hash()
        print(objectToBeautifiedText(states))


if __name__ == '__main__':
    unittest.main()
