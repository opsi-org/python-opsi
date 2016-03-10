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

from OPSI.Object import (ConfigState, LocalbootProduct, OpsiClient,
    OpsiDepotserver, ProductOnClient, ProductOnDepot, UnicodeConfig)


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
    def testExtendedBackend(self):
        self.backend.backend_setOptions({
            'addProductOnClientDefaults':          True,
            'addProductPropertyStateDefaults':     True,
            'addConfigStateDefaults':              True,
            'deleteConfigStateIfDefault':          True,
            'returnObjectsOnUpdateAndCreate':      False
        })

        self.setUpClients()
        self.setUpHosts()
        self.createHostsOnBackend()

        self.setUpConfigStates()
        self.createConfigOnBackend()
        self.createConfigStatesOnBackend()

        clients = self.backend.host_getObjects(type='OpsiClient')
        clientToDepots = self.backend.configState_getClientToDepotserver()
        self.assertEquals(len(clientToDepots), len(clients))

        for depotserver in self.depotservers:
            productOnDepots = self.backend.productOnDepot_getObjects(depotId=depotserver.id)

            # TODO: richtige Tests
            # for productOnDepot in productOnDepots:
            #     logger.info(u"Got productOnDepot: %s" % productOnDepot)

            # for clientToDepot in clientToDepots:
            #     if (clientToDepot['depotId'] == depotserver.id):
            #         # TODO: richtige Tests
            #         logger.info(u"Got client to depot: %s" % clientToDepot)

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

        clientDepotMappingConfigState = ConfigState(
            configId=u'clientconfig.depot.id',
            objectId=client.id,
            values=depot.id,
        )

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
