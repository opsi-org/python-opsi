#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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

from __future__ import absolute_import, print_function

import os

from OPSI.Backend.BackendManager import BackendManager, ConfigDataBackend

from .Backends.File import FileBackendMixin

from .helpers import getLocalFQDN, unittest, workInTemporaryDirectory
from .Backends.File import getFileBackend
from .test_configs import getConfigs
from .test_groups import fillBackendWithGroups
from .test_hosts import getClients, getConfigServer, getDepotServers
from .test_products import getProducts, getProductsOnDepot


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


class ExtendedBackendManagerTestCase(unittest.TestCase, FileBackendMixin):
    """
    This tests an extended BackendManager that makes use of the extensions.
    """
    # TODO: we may want to extend the backend fixtures to make use of a backendmanager aswell.

    def setUp(self):
        self.setUpBackend()
        self.backend = BackendManager(
            backend=self.backend,
            extensionconfigdir=os.path.join(self._fileTempDir, self.BACKEND_SUBFOLDER, 'backendManager', 'extend.d')
        )

    def tearDown(self):
        self.tearDownBackend()

    def testBackendManager(self):
        # TODO: use fixtures!
        bm = self.backend

        self.clients = getClients()
        self.configserver1 = getConfigServer()
        self.depotservers = getDepotServers()
        self.hosts = list(self.clients) + list(self.depotservers) + [self.configserver1]

        bm.host_createObjects(self.clients)
        bm.host_createObjects(self.depotservers)
        bm.host_createObjects(self.configserver1)

        hostIds = bm.host_getIdents()
        for host in self.hosts:
            self.assertTrue(host.id in hostIds)

        # No configs set - should be equal now
        self.client1 = self.clients[0]
        self.assertEquals(bm.getGeneralConfig_hash(), bm.getGeneralConfig_hash(objectId=self.client1.id))

        self.depotserver1 = self.depotservers[0]
        (self.config1, self.config2, self.config3, self.config4,
         self.config5, self.config6) = getConfigs(self.depotserver1.id)

        self.configs = [
            self.config1, self.config2, self.config3, self.config4,
            self.config5, self.config6
        ]
        for config in self.configs:
            config.setDefaults()
        self.backend.config_createObjects(self.configs)

        self.assertEquals(self.config1.defaultValues[0], bm.getGeneralConfigValue(key=self.config1.id, objectId=None))

        generalConfig = {
            'test-key-1': 'test-value-1',
            'test-key-2': 'test-value-2',
            'opsiclientd.depot_server.depot_id': self.depotserver1.id
        }
        bm.setGeneralConfig(config=generalConfig, objectId=None)

        key = generalConfig.keys()[0]
        value = bm.getGeneralConfigValue(key=key, objectId=self.client1.id)
        self.assertEquals(value, generalConfig[key])

        anotherKey = generalConfig.keys()[1]
        bm.setGeneralConfigValue(anotherKey, self.client1.id, objectId=self.client1.id)
        bm.setGeneralConfigValue(anotherKey, 'changed', objectId=None)
        self.assertEquals('changed', bm.getGeneralConfigValue(key=anotherKey, objectId=None))

        value = bm.getGeneralConfigValue(key=anotherKey, objectId=self.client1.id)
        self.assertEquals(value, self.client1.id)

        bm.deleteGeneralConfig(self.client1.id)
        self.assertEquals('changed', bm.getGeneralConfigValue(key=anotherKey, objectId=self.client1.id))

        self.groups = fillBackendWithGroups(self.backend)

        groupIds = bm.getGroupIds_list()
        for group in self.groups:
            self.assertTrue(group.id in groupIds)

        self.client2 = self.clients[1]
        clients = [self.client1.id, self.client2.id]
        groupId = 'a test group'
        bm.createGroup(
            groupId,
            members=clients,
            description="A test group",
            parentGroupId=""
        )

        self.assertEquals(1, len(bm.group_getObjects(id=groupId)))

        objectToGroups = bm.objectToGroup_getObjects(groupId=groupId)
        self.assertEquals(2, len(objectToGroups))
        for objectToGroup in objectToGroups:
            self.assertTrue(objectToGroup.objectId in clients)

        bm.deleteGroup(groupId=groupId)
        self.assertEquals(0, len(bm.group_getObjects(id=groupId)))

        ipAddress = bm.getIpAddress(hostId=self.client1.id)
        self.assertEquals(ipAddress, self.client1.ipAddress)

        serverName, domain = getLocalFQDN().split('.', 1)
        serverId = bm.createServer(
            serverName=serverName,
            domain=domain,
            description='Some description',
            notes=None
        )
        self.assertEquals(serverId, serverName + '.' + domain)

        serverIds = bm.host_getIdents(type='OpsiConfigserver')
        self.assertTrue(serverId in serverIds)

        clientName = 'test-client'
        clientId = bm.createClient(
            clientName=clientName,
            domain=domain,
            description='a description',
            notes='notes...',
            ipAddress='192.168.1.91',
            hardwareAddress='00:01:02:03:01:aa'
        )
        self.assertEquals(clientId, clientName + '.' + domain)

        clientIds = bm.host_getIdents(type='OpsiClient')
        self.assertTrue(clientId, clientIds)

        # This will not work with the file backend because it will not
        # delete any host with the id == local FQDN.
        # TODO: if running with different backend, please enable
        # bm.deleteServer(serverId)
        # serverIds = bm.host_getIdents(type='OpsiConfigserver')
        # self.assertTrue(serverId not in serverIds)

        bm.deleteClient(clientId)
        self.assertTrue(clientId not in bm.host_getIdents(type='OpsiClient'))

        lastSeen = '2009-01-01 00:00:00'
        description = 'Updated description'
        notes = 'Updated notes'
        opsiHostKey = '00000000001111111111222222222233'
        mac = '00:01:02:03:40:12'
        bm.setHostLastSeen(hostId=self.client1.id, timestamp=lastSeen)
        bm.setHostDescription(hostId=self.client1.id, description=description)
        bm.setHostNotes(hostId=self.client1.id, notes=notes)
        bm.setOpsiHostKey(hostId=self.client1.id, opsiHostKey=opsiHostKey)
        bm.setMacAddress(hostId=self.client1.id, mac=mac)

        host = bm.host_getObjects(id=self.client1.id)[0]

        self.assertEquals(lastSeen, host.lastSeen)
        self.assertEquals(description, host.description)
        self.assertEquals(notes, host.notes)
        self.assertEquals(opsiHostKey, host.opsiHostKey)
        self.assertEquals(mac, host.hardwareAddress)

        self.assertEquals(opsiHostKey, bm.getOpsiHostKey(hostId=self.client1.id))
        self.assertEquals(mac, bm.getMacAddress(hostId=self.client1.id))

        host = bm.getHost_hash(hostId=self.client1.id)
        serverIds = bm.getServerIds_list()
        serverId = bm.getServerId(clientId=self.client1.id)

        depotName = self.depotserver1.id.split('.', 1)[0]
        depotRemoteUrl = 'smb://{0}/xyz'.format(depotName)
        depotId = bm.createDepot(
            depotName=depotName,
            domain=domain,
            depotLocalUrl='file:///xyz',
            depotRemoteUrl=depotRemoteUrl,
            repositoryLocalUrl='file:///abc',
            repositoryRemoteUrl='webdavs://{0}:4447/products'.format(depotName),
            network='0.0.0.0/0',
            description='Some description',
            notes='Some notes',
            maxBandwidth=100000
        )
        self.assertEquals(depotId, depotName + '.' + domain)

        depotIds = bm.getDepotIds_list()
        depot = bm.getDepot_hash(depotId)
        self.assertEquals(depot['depotRemoteUrl'], depotRemoteUrl)

        bm.deleteDepot(depotId)
        depotIds = bm.getDepotIds_list()
        self.assertTrue(depotId not in depotIds)

        self.products = getProducts()
        self.backend.product_createObjects(self.products)

        depotserver1 = {
            "isMasterDepot": True,
            "type": "OpsiDepotserver",
            "id": self.depotserver1.id,
        }
        self.backend.host_createObjects(depotserver1)

        self.productOnDepots = getProductsOnDepot(self.products, self.configserver1, self.depotservers)
        self.backend.productOnDepot_createObjects(self.productOnDepots)

        self.product1 = self.products[0]
        bm.lockProduct(productId=self.product1.id, depotIds=[self.depotserver1.id])
        productLocks = bm.getProductLocks_hash(depotIds=[])
        for (prductId, depotIds) in productLocks.items():
            self.assertEquals(prductId, self.product1.id)
            self.assertEquals(1, len(depotIds))
            self.assertEquals(depotIds[0], self.depotserver1.id)

        bm.unlockProduct(productId=self.product1.id, depotIds=[])
        self.assertFalse(bm.getProductLocks_hash(depotIds=[]))

        productId1 = 'test-localboot-1'
        bm.createLocalBootProduct(
            productId=productId1,
            name='Some localboot product',
            productVersion='1.0',
            packageVersion='1',
            licenseRequired=0,
            setupScript="",
            uninstallScript="",
            updateScript="",
            alwaysScript="",
            onceScript="",
            priority=0,
            description="",
            advice="",
            windowsSoftwareIds=[],
            depotIds=[]
        )

        productId2 = 'test-netboot-1'
        bm.createNetBootProduct(
            productId=productId2,
            name='Some localboot product',
            productVersion='1.0',
            packageVersion='1',
            licenseRequired=0,
            setupScript="",
            uninstallScript="",
            updateScript="",
            alwaysScript="",
            onceScript="",
            priority=0,
            description="",
            advice="",
            pxeConfigTemplate='some_template',
            windowsSoftwareIds=[],
            depotIds=[]
        )

        productIdents = bm.product_getIdents(returnType='tuple')
        self.assertTrue((productId1, '1.0', '1') in productIdents)
        self.assertTrue((productId2, '1.0', '1') in productIdents)

        product = bm.getProduct_hash(productId=productId1, depotId=self.depotserver1.id)
        products = bm.getProducts_hash()
        products = bm.getProducts_listOfHashes()
        products = bm.getProducts_listOfHashes(depotId=self.depotserver1.id)

        for client in self.clients:
            allProductIds = bm.getInstalledProductIds_list(objectId = client.id)

            productIds = bm.getInstalledLocalBootProductIds_list(objectId=client.id)
            for product in productIds:
                self.assertTrue(product in allProductIds)

            productIds = bm.getInstalledNetBootProductIds_list(objectId=client.id)
            for product in productIds:
                self.assertTrue(product in allProductIds)

        productIds = bm.getProvidedLocalBootProductIds_list(depotId=self.depotserver1.id)
        productIds = bm.getProvidedNetBootProductIds_list(depotId=self.depotserver1.id)

        for client in self.clients:
            status = bm.getProductInstallationStatus_hash(productId=self.product1.id, objectId=client.id)

        self.backend.config_createObjects([{
            "id": u'clientconfig.depot.id',
            "type": "UnicodeConfig",
        }])
        self.backend.configState_create(u'clientconfig.depot.id', client.id, values=[depotId])

        bm.setProductState(productId=self.product1.id, objectId=client.id, installationStatus="not_installed", actionRequest="setup")
        bm.setProductInstallationStatus(productId=self.product1.id, objectId=client.id, installationStatus="installed")
        bm.setProductActionProgress(productId=self.product1.id, hostId=client.id, productActionProgress="something 90%")
        bm.setProductActionRequest(productId=self.product1.id, clientId=client.id, actionRequest='uninstall')

        for product in self.products:
            actions = bm.getPossibleProductActions_list(productId=product.id)

        actions = bm.getPossibleProductActions_hash()
        depotId = bm.getDepotId(clientId=client.id)
        self.assertEquals(depotId, self.depotserver1.id)

        clientId = bm.getClientIdByMac(mac=self.client2.hardwareAddress)
        self.assertEquals(clientId, self.client2.id)

        productIds = bm.getInstallableProductIds_list(clientId=client.id)
        productIds = bm.getInstallableLocalBootProductIds_list(clientId=client.id)
        productIds = bm.getInstallableNetBootProductIds_list(clientId=client.id)
        # TODO: assertions!
        status = bm.getProductInstallationStatus_listOfHashes(objectId=client.id)
        actions = bm.getProductActionRequests_listOfHashes(clientId=client.id)
        states = bm.getLocalBootProductStates_hash()


class GettingBackendManagerTestCase(unittest.TestCase):
    def testGettingBackendManagerWithDefaultConfig(self):
        requiredPaths = (
            u'/etc/opsi/backendManager/dispatch.conf',
            u'/etc/opsi/backends',
            u'/etc/opsi/backendManager/extend.d',
            u'/var/lib/opsi/config/depots',
        )

        for path in requiredPaths:
            if not os.path.exists(path):
                self.skipTest("Missing {0}".format(path))

        backend = BackendManager()
        print(backend.backend_info())

    def testGettingBackendManagerWithCustomConfig(self):
        with workInTemporaryDirectory() as tempDir:
            backendsDir = os.path.join(tempDir, 'backendsss')
            bmDir = os.path.join(tempDir, 'bm')
            dispatchConfig = os.path.join(bmDir, 'dispatch.conf')
            extensionDir = os.path.join(bmDir, 'extension')

            os.mkdir(bmDir)
            os.mkdir(extensionDir)
            os.mkdir(backendsDir)

            with open(dispatchConfig, 'w') as dpconf:
                dpconf.write("""
.* : file
""")

            kwargs = {
                "dispatchConfigFile": dispatchConfig,
                "backendConfigDir": backendsDir,
                "extensionConfigDir": extensionDir,
            }

            with getFileBackend(path=tempDir):
                # We need to make sure there is a file.conf for the backend.
                os.link(
                    os.path.join(tempDir, 'etc', 'opsi', 'backends', 'file.conf'),
                    os.path.join(backendsDir, 'file.conf')
                )

            backend = BackendManager(**kwargs)
            print(backend.backend_info())


def testBackendManagerCanAccessExtensions(backendManager):
    print(backendManager)
    print(backendManager.backend_info())

    print(backendManager.getServerIds_list())
