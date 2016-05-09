#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Mixin for testing an extended backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from contextlib import contextmanager

from OPSI.Object import (LocalbootProduct, OpsiClient, OpsiDepotserver,
    ProductOnClient, ProductOnDepot, UnicodeConfig)

from .Clients import getClients
from .Configs import getConfigs, getConfigStates
from .Hosts import getDepotServers
from .Products import getLocalbootProducts, getNetbootProduct, getProductsOnClients, getProductsOnDepot


@contextmanager
def temporaryBackendOptions(backend, **config):
    oldkeys = backend.backend_getOptions()

    try:
        print("Setting backend option {0!r}".format(config))
        backend.backend_setOptions(config)
        yield
    finally:
        backend.backend_setOptions(oldkeys)


class ExtendedBackendTestsMixin(object):
    # TODO: provide tests for these backend options:
    #     self.backend.backend_setOptions({
    #     'addProductPropertyStateDefaults':     True,
    #     'addConfigStateDefaults':              True,
    #     'deleteConfigStateIfDefault':          True,
    #     'returnObjectsOnUpdateAndCreate':      False
    # })

    def test_configState_getClientToDepotserver(self):
        originalClients = getClients()
        depotservers = getDepotServers()
        depot1 = depotservers[0]
        self.backend.host_createObjects(depotservers)
        self.backend.host_createObjects(originalClients)

        clientConfigDepotId = UnicodeConfig(
            id=u'clientconfig.depot.id',
            description=u'Depotserver to use',
            possibleValues=[],
            defaultValues=[depot1.id]
        )
        self.backend.config_createObjects(clientConfigDepotId)

        products = list(getLocalbootProducts()) + [getNetbootProduct()]
        self.backend.product_createObjects(products)
        originalProductsOnDepots = getProductsOnDepot(products, depot1, depotservers)
        self.backend.productOnDepot_createObjects(originalProductsOnDepots)

        clients = self.backend.host_getObjects(type='OpsiClient')
        with temporaryBackendOptions(self.backend, addConfigStateDefaults=True):
            clientToDepots = self.backend.configState_getClientToDepotserver()

        self.assertEqual(len(clientToDepots), len(clients), u"Expected %s clients, but got %s from backend." % (len(clientToDepots), len(clients)))

        for depotserver in getDepotServers():
            productOnDepots = self.backend.productOnDepot_getObjects(depotId=depotserver.id)
            expectedProducts = [x for x in originalProductsOnDepots if x.depotId == depotserver.id]
            for productOnDepot in productOnDepots:
                self.assertTrue(productOnDepot in expectedProducts, u"Expected products %s do be on depotserver %s, but depotserver found %s." % (expectedProducts, depotserver.id, productOnDepot.productId))

        for clientToDepot in clientToDepots:
           self.assertTrue(clientToDepot['depotId'] in [ds.id for ds in depotservers])

    def test_createProductOnClient(self):
        client = OpsiClient(id='client.test.invalid')
        self.backend.host_createObjects(client)

        originalPoc = ProductOnClient(
            productId='product6',
            productType='LocalbootProduct',
            clientId=client.id,
            installationStatus='not_installed',
            actionRequest='setup'
        )
        self.backend.productOnClient_createObjects(originalPoc)

        productOnClients = [poc for poc in
                            self.backend.productOnClient_getObjects(clientId=client.id)
                            if poc.actionRequest == 'setup']

        self.assertEqual([originalPoc], productOnClients)

    def test_selectProductOnClientWithDefault(self):
        client = OpsiClient(id='client.test.invalid')
        depot = OpsiDepotserver(id='depotserver1.test.invalid')
        self.backend.host_createObjects([client, depot])

        poc = ProductOnClient(
            productId='product6',
            productType='LocalbootProduct',
            clientId=client.id,
            installationStatus='not_installed',
            actionRequest='setup'
        )
        self.backend.productOnClient_createObjects(poc)

        prod6 = LocalbootProduct(
            id="product6",
            productVersion="1.0",
            packageVersion=1,
        )
        prod7 = LocalbootProduct(
            id='product7',
            name=u'Product 7',
            productVersion="1.0",
            packageVersion=1,
        )
        self.backend.product_createObjects([prod6, prod7])

        installedProductOnDepot6 = ProductOnDepot(
            productId=prod6.id,
            productType=prod6.getType(),
            productVersion=prod6.productVersion,
            packageVersion=prod6.packageVersion,
            depotId=depot.getId(),
            locked=False
        )
        installedProductOnDepot7 = ProductOnDepot(
            productId=prod7.id,
            productType=prod7.getType(),
            productVersion=prod7.productVersion,
            packageVersion=prod7.packageVersion,
            depotId=depot.getId(),
            locked=False
        )
        self.backend.productOnDepot_createObjects([installedProductOnDepot6,
                                                   installedProductOnDepot7])

        clientConfigDepotId = UnicodeConfig(
            id=u'clientconfig.depot.id',
            description=u'Depotserver to use',
            possibleValues=[],
            defaultValues=[depot.id]
        )
        self.backend.config_createObjects(clientConfigDepotId)

        with temporaryBackendOptions(self.backend, addProductOnClientDefaults=True):
            productOnClients = [pocc.productId for pocc in
                                self.backend.productOnClient_getObjects(
                                    clientId=client.id,
                                    productId=['product6', 'product7'])]

        productOnClients.sort()
        self.assertEqual(productOnClients, [u'product6',u'product7'])

    def test_selectProductOnClientsByWildcard(self):
        client = OpsiClient(id='client.test.invalid')
        self.backend.host_createObjects(client)

        poc = ProductOnClient(
            productId='product6',
            productType='LocalbootProduct',
            clientId=client.id,
            installationStatus='not_installed',
            actionRequest='setup'
        )
        self.backend.productOnClient_createObjects(poc)

        productOnClients = self.backend.productOnClient_getObjects(
            clientId=client.id,
            productId='*6*'
        )
        self.assertEqual(productOnClients, [poc])

    def test_createDepotServer(self):
        self.backend.host_createOpsiDepotserver(
                id='depot100.test.invalid',
                opsiHostKey='123456789012345678901234567890aa',
                depotLocalUrl='file:///opt/pcbin/install',
                depotRemoteUrl='smb://depot3.uib.local/opt_pcbin/install',
                repositoryLocalUrl='file:///var/lib/opsi/products',
                repositoryRemoteUrl='webdavs://depot3.uib.local:4447/products',
                description='A depot',
                notes='Depot 100',
                hardwareAddress=None,
                ipAddress=None,
                networkAddress='192.168.100.0/24',
                maxBandwidth=0)


        hosts = self.backend.host_getObjects(id='depot100.test.invalid')
        self.assertEqual(len(hosts), 1, u"Expected one depotserver with id '%s', but found '%s' on backend." % ('depot100.uib.local', len(hosts)))

    def test_createClient(self):
        self.backend.host_createOpsiClient(
                id='client100.uib.local',
                opsiHostKey=None,
                description='Client 100',
                notes='No notes',
                hardwareAddress='00:00:01:01:02:02',
                ipAddress='192.168.0.200',
                created=None,
                lastSeen=None)

        hosts = self.backend.host_getObjects(id = 'client100.uib.local')
        self.assertEqual(len(hosts), 1, u"Expected one client with id '%s', but found '%s' on backend." % ('client100.uib.local', len(hosts)))

    def test_hostIdents(self):
        self.backend.host_createOpsiDepotserver(
            id='depot100.test.invalid',
            opsiHostKey='123456789012345678901234567890aa',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depot3.uib.local/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/products',
            repositoryRemoteUrl='webdavs://depot3.uib.local:4447/products',
            description='A depot',
            notes='Depot 100',
            hardwareAddress=None,
            ipAddress=None,
            networkAddress='192.168.100.0/24',
            maxBandwidth=0)
        self.backend.host_createOpsiClient(
            id='client100.test.invalid',
            opsiHostKey=None,
            description='Client 100',
            notes='No notes',
            hardwareAddress='00:00:01:01:02:02',
            ipAddress='192.168.0.200',
            created=None,
            lastSeen=None)
        clients = getClients()
        self.backend.host_createObjects(clients)

        numHosts = len(clients) + 2

        selfIdents = [
            {'id': 'depot100.test.invalid'},
            {'id': 'client100.test.invalid'}
        ]
        for host in clients:
            selfIdents.append(host.getIdent(returnType = 'dict'))

        selfIds = [d['id'] for d in selfIdents]

        ids = self.backend.host_getIdents()
        self.assertEqual(len(ids), len(selfIdents))

        for ident in ids:
            self.assertIn(ident, selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        ids = self.backend.host_getIdents(id='*100*')
        self.assertEqual(len(ids), 2, u"Expected %s idents, but found '%s' on backend." % (2, len(ids)))
        for ident in ids:
            self.assertIn(ident, selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        ids = self.backend.host_getIdents(returnType = 'tuple')
        self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))
        for ident in ids:
            self.assertIn(ident[0], selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        ids = self.backend.host_getIdents(returnType = 'list')
        self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))
        for ident in ids:
            self.assertIn(ident[0], selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        ids = self.backend.host_getIdents(returnType = 'dict')
        self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))
        for ident in ids:
            self.assertIn(ident['id'], selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        configs = getConfigs()
        self.backend.config_createObjects(configs)
        selfIdents = []
        for config in configs:
            selfIdents.append(config.getIdent(returnType='dict'))
        selfIds = [d['id'] for d in selfIdents]

        ids = self.backend.config_getIdents()
        self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))
        for ident in ids:
            self.assertIn(ident, selfIds, u"'%s' not in '%s'" % (ident, selfIds))

        depotServer = self.backend.host_getObjects(id='depot100.test.invalid')[0]
        configStates = getConfigStates(configs, clients, [None, depotServer])
        self.backend.configState_createObjects(configStates)
        selfIdents = []
        for configState in configStates:
            selfIdents.append(configState.getIdent(returnType='dict'))

        with temporaryBackendOptions(self.backend, addConfigStateDefaults=False):
            ids = self.backend.configState_getIdents()

        self.assertEqual(len(ids), len(selfIdents), u"Expected %s idents, but found '%s' on backend." % (len(selfIdents), len(ids)))
        for ident in ids:
            id = dict(zip(('configId', 'objectId'), tuple(ident.split(";"))))
            self.assertIn(id, selfIdents, u"'%s' not in '%s'" % (ident, selfIdents))

        expect = len(self.backend.host_getObjects()) * len(configs)
        with temporaryBackendOptions(self.backend, addConfigStateDefaults=True):
            ids = self.backend.configState_getIdents()
        self.assertEqual(expect, len(ids), u"Expected %s idents, but found '%s' on backend." % (expect, len(ids)))

    def test_gettingIdentsDoesNotRaiseAnException(self):
        # TODO: create objects and check if something is returned.

        self.backend.product_getIdents()
        self.backend.productProperty_getIdents()
        self.backend.productOnDepot_getIdents()
        self.backend.productOnDepot_getIdents()
        self.backend.productPropertyState_getIdents()
        self.backend.productPropertyState_getIdents(returnType='tuple')
        self.backend.productPropertyState_getIdents(returnType='list')
        self.backend.productPropertyState_getIdents(returnType='dict')
        self.backend.group_getIdents()
        self.backend.objectToGroup_getIdents()
        self.backend.product_getIdents(id='*product*')

    def test_ldapSearchFilter(self):
        depotServer = getDepotServers()
        self.backend.host_createObjects(depotServer)

        result = self.backend.backend_searchIdents('(&(objectClass=Host)(type=OpsiDepotserver))')
        expected = self.backend.host_getIdents(type="OpsiDepotserver")
        result.sort()
        expected.sort()
        assert expected  # If this fails there are no objects.
        self.assertEqual(expected, result)

        result = self.backend.backend_searchIdents('(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
        expected = self.backend.host_getIdents(type="OpsiDepotserver")
        result.sort()
        expected.sort()
        assert expected  # If this fails there are no objects.
        self.assertEqual(expected, result)
        depotIdents = [d.getIdent() for d in depotServer]
        depotIdents.sort()
        self.assertEqual(result, depotIdents)

        clients = getClients()
        self.backend.host_createObjects(clients)
        result = self.backend.backend_searchIdents('(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
        expected = self.backend.host_getIdents(type="OpsiClient", id=["client1*", "client2*"])
        result.sort()
        expected.sort()
        assert expected  # If this fails there are no objects.
        self.assertEqual(expected, result)
        clientIdents = [c.getIdent() for c in clients if c.id.startswith('client1.') or c.id.startswith('client2.')]
        clientIdents.sort()
        self.assertEqual(result, clientIdents)

        products = getLocalbootProducts()
        product1 = products[0]
        pocs = getProductsOnClients(products, clients)
        assert products
        assert pocs
        self.backend.product_createObjects(products)
        self.backend.productOnClient_createObjects(pocs)
        result = self.backend.backend_searchIdents('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId={0})))'.format(product1.id))
        expected = [x["clientId"] for x in self.backend.productOnClient_getIdents(returnType="dict", installationStatus="installed", productId=product1.id)]
        print(self.backend.productOnClient_getIdents(returnType="dict"))
        result.sort()
        expected.sort()
        assert expected  # If this fails there are no objects.
        self.assertEqual(expected, result)

        result = self.backend.backend_searchIdents('(&(objectClass=Host)(description=T*))')
        expected = self.backend.host_getIdents(description="T*")
        result.sort()
        expected.sort()
        assert expected  # If this fails there are no objects.
        self.assertEqual(expected, result)
