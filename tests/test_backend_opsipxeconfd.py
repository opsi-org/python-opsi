# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2018 uib GmbH <info@uib.de>

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
Testing opsipxeconfd backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import pytest

from OPSI.Backend.OpsiPXEConfd import OpsiPXEConfdBackend, getClientCacheFilePath
from OPSI.Object import (NetbootProduct, OpsiClient, OpsiDepotserver,
    ProductOnClient, ProductOnDepot, UnicodeConfig)

from .helpers import patchAddress


@pytest.fixture()
def client():
    return OpsiClient(id='foo.test.invalid')


@pytest.fixture()
def depot():
    return OpsiDepotserver(id='depotserver1.test.invalid')


def testInitialisation():
    with patchAddress():
        OpsiPXEConfdBackend()


def testGetClientCachePath():
    clientId = 'foo.bar.baz'

    path = getClientCacheFilePath(clientId)

    assert clientId in path
    assert path.endswith('.json')


def testCacheDataCollectionWithPxeConfigTemplate(backendManager, client, depot):
    """
    Collection of caching data with a product with pxeConfigTemplate.
    """
    backendManager.host_createObjects([client, depot])

    backendManager.config_createObjects([
        UnicodeConfig(
            id=u'opsi-linux-bootimage.append',
            possibleValues=[
                u'acpi=off', u'irqpoll', u'noapic', u'pci=nomsi',
                u'vga=normal', u'reboot=b'
            ],
            defaultValues=[u''],
        ),
        UnicodeConfig(
            id=u'clientconfig.configserver.url',
            description=u'URL(s) of opsi config service(s) to use',
            possibleValues=[u'https://%s:4447/rpc' % depot.id],
            defaultValues=[u'https://%s:4447/rpc' % depot.id],
        ),
        UnicodeConfig(
            id=u'clientconfig.depot.id',
            description=u'Depotserver to use',
            possibleValues=[],
            defaultValues=[depot.id]
        )
    ])

    product = NetbootProduct(
        'mytest86',
        productVersion=1,
        packageVersion=1,
        pxeConfigTemplate='scaredOfNothing'
    )
    backendManager.product_insertObject(product)

    productOnDepot = ProductOnDepot(
        productId=product.getId(),
        productType=product.getType(),
        productVersion=product.getProductVersion(),
        packageVersion=product.getPackageVersion(),
        depotId=depot.id
    )
    backendManager.productOnDepot_createObjects([productOnDepot])

    poc = ProductOnClient(
        product.id,
        product.getType(),
        client.id,
        actionRequest="setup"
    )
    backendManager.productOnClient_insertObject(poc)

    with patchAddress(fqdn=depot.id):
        backend = OpsiPXEConfdBackend(context=backendManager)

        data = backend._collectDataForUpdate(poc, depot.id)

        assert data
        assert data['product']['pxeConfigTemplate'] == product.pxeConfigTemplate
