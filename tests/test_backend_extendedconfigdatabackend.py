#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing extended backends features

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

from contextlib import contextmanager
from itertools import izip

from OPSI.Object import (LocalbootProduct, OpsiClient, OpsiDepotserver,
    ProductOnClient, ProductOnDepot, UnicodeConfig)

from .test_configs import getConfigs, getConfigStates
from .test_hosts import getClients, getDepotServers
from .test_products import (getLocalbootProducts, getNetbootProduct,
    getProductsOnClients, getProductsOnDepot)

import pytest


@contextmanager
def temporaryBackendOptions(backend, **config):
    oldkeys = backend.backend_getOptions()

    try:
        print("Setting backend option {0!r}".format(config))
        backend.backend_setOptions(config)
        yield
    finally:
        backend.backend_setOptions(oldkeys)


# TODO: provide tests for these backend options:
#     extendedConfigDataBackend.backend_setOptions({
#     'addProductPropertyStateDefaults':     True,
#     'addConfigStateDefaults':              True,
#     'deleteConfigStateIfDefault':          True,
#     'returnObjectsOnUpdateAndCreate':      False
# })

@pytest.mark.requiresModulesFile
def test_configState_getClientToDepotserver(extendedConfigDataBackend):
    originalClients = getClients()
    depotservers = getDepotServers()
    depot1 = depotservers[0]
    extendedConfigDataBackend.host_createObjects(depotservers)
    extendedConfigDataBackend.host_createObjects(originalClients)

    clientConfigDepotId = UnicodeConfig(
        id=u'clientconfig.depot.id',
        description=u'Depotserver to use',
        possibleValues=[],
        defaultValues=[depot1.id]
    )
    extendedConfigDataBackend.config_createObjects(clientConfigDepotId)

    products = list(getLocalbootProducts()) + [getNetbootProduct()]
    extendedConfigDataBackend.product_createObjects(products)
    originalProductsOnDepots = getProductsOnDepot(products, depot1, depotservers)
    extendedConfigDataBackend.productOnDepot_createObjects(originalProductsOnDepots)

    clients = extendedConfigDataBackend.host_getObjects(type='OpsiClient')
    with temporaryBackendOptions(extendedConfigDataBackend, addConfigStateDefaults=True):
        clientToDepots = extendedConfigDataBackend.configState_getClientToDepotserver()

    assert len(clientToDepots) == len(clients)

    for depotserver in getDepotServers():
        productOnDepots = extendedConfigDataBackend.productOnDepot_getObjects(depotId=depotserver.id)
        expectedProducts = [x for x in originalProductsOnDepots if x.depotId == depotserver.id]
        for productOnDepot in productOnDepots:
            assert productOnDepot in expectedProducts

    depotServerIDs = set(ds.id for ds in depotservers)

    for clientToDepot in clientToDepots:
        assert clientToDepot['depotId'] in depotServerIDs


@pytest.mark.requiresModulesFile
def test_createProductOnClient(extendedConfigDataBackend):
    client = OpsiClient(id='client.test.invalid')
    extendedConfigDataBackend.host_createObjects(client)

    originalPoc = ProductOnClient(
        productId='product6',
        productType='LocalbootProduct',
        clientId=client.id,
        installationStatus='not_installed',
        actionRequest='setup'
    )
    extendedConfigDataBackend.productOnClient_createObjects(originalPoc)

    productOnClients = [poc for poc in
                        extendedConfigDataBackend.productOnClient_getObjects(clientId=client.id)
                        if poc.actionRequest == 'setup']

    assert [originalPoc] == productOnClients


@pytest.mark.requiresModulesFile
def test_selectProductOnClientWithDefault(extendedConfigDataBackend):
    client = OpsiClient(id='client.test.invalid')
    depot = OpsiDepotserver(id='depotserver1.test.invalid')
    extendedConfigDataBackend.host_createObjects([client, depot])

    poc = ProductOnClient(
        productId='product6',
        productType='LocalbootProduct',
        clientId=client.id,
        installationStatus='not_installed',
        actionRequest='setup'
    )
    extendedConfigDataBackend.productOnClient_createObjects(poc)

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
    extendedConfigDataBackend.product_createObjects([prod6, prod7])

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
    extendedConfigDataBackend.productOnDepot_createObjects([
        installedProductOnDepot6,
        installedProductOnDepot7
    ])

    clientConfigDepotId = UnicodeConfig(
        id=u'clientconfig.depot.id',
        description=u'Depotserver to use',
        possibleValues=[],
        defaultValues=[depot.id]
    )
    extendedConfigDataBackend.config_createObjects(clientConfigDepotId)

    with temporaryBackendOptions(extendedConfigDataBackend, addProductOnClientDefaults=True):
        productOnClients = [pocc.productId for pocc in
                            extendedConfigDataBackend.productOnClient_getObjects(
                                clientId=client.id,
                                productId=['product6', 'product7'])]

    productOnClients.sort()
    assert productOnClients == [u'product6', u'product7']


def test_selectProductOnClientsByWildcard(extendedConfigDataBackend):
    client = OpsiClient(id='client.test.invalid')
    extendedConfigDataBackend.host_createObjects(client)

    poc = ProductOnClient(
        productId='product6',
        productType='LocalbootProduct',
        clientId=client.id,
        installationStatus='not_installed',
        actionRequest='setup'
    )
    extendedConfigDataBackend.productOnClient_createObjects(poc)

    productOnClients = extendedConfigDataBackend.productOnClient_getObjects(
        clientId=client.id,
        productId='*6*'
    )
    assert productOnClients == [poc]


def test_createDepotServer(extendedConfigDataBackend):
    extendedConfigDataBackend.host_createOpsiDepotserver(
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
        maxBandwidth=0
    )

    hosts = extendedConfigDataBackend.host_getObjects(id='depot100.test.invalid')
    assert len(hosts) == 1
    # TODO: check host!


@pytest.mark.requiresModulesFile
def test_createClient(extendedConfigDataBackend):
    extendedConfigDataBackend.host_createOpsiClient(
        id='client100.test.invalid',
        opsiHostKey=None,
        description='Client 100',
        notes='No notes',
        hardwareAddress='00:00:01:01:02:02',
        ipAddress='192.168.0.200',
        created=None,
        lastSeen=None
    )

    hosts = extendedConfigDataBackend.host_getObjects(id='client100.test.invalid')
    assert len(hosts) == 1
    # TODO: check Host


def test_hostIdents(extendedConfigDataBackend):
    extendedConfigDataBackend.host_createOpsiDepotserver(
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
    extendedConfigDataBackend.host_createOpsiClient(
        id='client100.test.invalid',
        opsiHostKey=None,
        description='Client 100',
        notes='No notes',
        hardwareAddress='00:00:01:01:02:02',
        ipAddress='192.168.0.200',
        created=None,
        lastSeen=None)
    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)

    selfIdents = [
        {'id': 'depot100.test.invalid'},
        {'id': 'client100.test.invalid'}
    ]
    for host in clients:
        selfIdents.append(host.getIdent(returnType='dict'))

    selfIds = [d['id'] for d in selfIdents]

    ids = extendedConfigDataBackend.host_getIdents()
    assert len(ids) == len(selfIdents)

    for ident in ids:
        assert ident in selfIds

    ids = extendedConfigDataBackend.host_getIdents(id='*100*')
    assert 2 == len(ids)
    for ident in ids:
        assert ident in selfIds

    ids = extendedConfigDataBackend.host_getIdents(returnType='tuple')
    assert len(ids) == len(selfIdents)
    for ident in ids:
        assert ident[0] in selfIds

    ids = extendedConfigDataBackend.host_getIdents(returnType='list')
    assert len(ids) == len(selfIdents)
    for ident in ids:
        assert ident[0] in selfIds

    ids = extendedConfigDataBackend.host_getIdents(returnType='dict')
    assert len(ids) == len(selfIdents)
    for ident in ids:
        assert ident['id'] in selfIds

    configs = getConfigs()
    extendedConfigDataBackend.config_createObjects(configs)
    selfIdents = []
    for config in configs:
        selfIdents.append(config.getIdent(returnType='dict'))
    selfIds = [d['id'] for d in selfIdents]

    ids = extendedConfigDataBackend.config_getIdents()
    assert len(ids) == len(selfIdents)
    for ident in ids:
        assert ident in selfIds

    depotServer = extendedConfigDataBackend.host_getObjects(id='depot100.test.invalid')[0]
    configStates = getConfigStates(configs, clients, [None, depotServer])
    extendedConfigDataBackend.configState_createObjects(configStates)
    selfIdents = []
    for configState in configStates:
        selfIdents.append(configState.getIdent(returnType='dict'))

    with temporaryBackendOptions(extendedConfigDataBackend, addConfigStateDefaults=False):
        ids = extendedConfigDataBackend.configState_getIdents()

    assert len(ids) == len(selfIdents)
    for ident in ids:
        id = dict(zip(('configId', 'objectId'), tuple(ident.split(";"))))
        assert id in selfIdents

    expect = len(extendedConfigDataBackend.host_getObjects()) * len(configs)
    with temporaryBackendOptions(extendedConfigDataBackend, addConfigStateDefaults=True):
        ids = extendedConfigDataBackend.configState_getIdents()
    assert expect == len(ids)


@pytest.mark.requiresModulesFile
def test_ldapSearchFilter(extendedConfigDataBackend):
    depotServer = getDepotServers()
    extendedConfigDataBackend.host_createObjects(depotServer)

    result = extendedConfigDataBackend.backend_searchIdents('(&(objectClass=Host)(type=OpsiDepotserver))')
    expected = extendedConfigDataBackend.host_getIdents(type="OpsiDepotserver")
    result.sort()
    expected.sort()
    assert expected  # If this fails there are no objects.
    assert expected == result

    result = extendedConfigDataBackend.backend_searchIdents('(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
    expected = extendedConfigDataBackend.host_getIdents(type="OpsiDepotserver")
    result.sort()
    expected.sort()
    assert expected  # If this fails there are no objects.
    assert expected == result
    depotIdents = [d.getIdent() for d in depotServer]
    depotIdents.sort()
    assert result == depotIdents

    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)
    result = extendedConfigDataBackend.backend_searchIdents('(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
    expected = extendedConfigDataBackend.host_getIdents(type="OpsiClient", id=["client1*", "client2*"])
    result.sort()
    expected.sort()
    assert expected  # If this fails there are no objects.
    assert expected == result
    clientIdents = [c.getIdent() for c in clients if c.id.startswith('client1.') or c.id.startswith('client2.')]
    clientIdents.sort()
    assert result == clientIdents

    products = getLocalbootProducts()
    product1 = products[0]
    pocs = getProductsOnClients(products, clients)
    assert products
    assert pocs
    extendedConfigDataBackend.product_createObjects(products)
    extendedConfigDataBackend.productOnClient_createObjects(pocs)
    result = extendedConfigDataBackend.backend_searchIdents('(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId={0})))'.format(product1.id))
    expected = [x["clientId"] for x in extendedConfigDataBackend.productOnClient_getIdents(returnType="dict", installationStatus="installed", productId=product1.id)]
    result.sort()
    expected.sort()
    assert expected  # If this fails there are no objects.
    assert expected == result

    result = extendedConfigDataBackend.backend_searchIdents('(&(objectClass=Host)(description=T*))')
    expected = extendedConfigDataBackend.host_getIdents(description="T*")
    result.sort()
    expected.sort()
    assert expected  # If this fails there are no objects.
    assert expected == result

    pocIdents = extendedConfigDataBackend.productOnClient_getIdents(returnType="dict")
    assert pocIdents


def test_gettingIdentsDoesNotRaiseAnException(extendedConfigDataBackend):
    # TODO: create objects and check if something is returned.

    extendedConfigDataBackend.product_getIdents()
    extendedConfigDataBackend.productProperty_getIdents()
    extendedConfigDataBackend.productOnDepot_getIdents()
    extendedConfigDataBackend.productOnDepot_getIdents()
    extendedConfigDataBackend.productPropertyState_getIdents()
    extendedConfigDataBackend.productPropertyState_getIdents(returnType='tuple')
    extendedConfigDataBackend.productPropertyState_getIdents(returnType='list')
    extendedConfigDataBackend.productPropertyState_getIdents(returnType='dict')
    extendedConfigDataBackend.group_getIdents()
    extendedConfigDataBackend.objectToGroup_getIdents()
    extendedConfigDataBackend.product_getIdents(id='*product*')


def testBackend_getInterface(extendedConfigDataBackend):
    """
    Testing the behaviour of backend_getInterface.

    The method descriptions in `expected` may vary and should be
    reduced if problems because of missing methods occur.
    """
    print("Base backend {0!r}".format(extendedConfigDataBackend))
    try:
        print("Checking with backend {0!r}".format(extendedConfigDataBackend._backend._backend))
    except AttributeError:
        try:
            print("Checking with backend {0!r}".format(extendedConfigDataBackend._backend))
        except AttributeError:
            pass

    expected = [
        {'name': 'backend_getInterface', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'backend_getOptions', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'backend_info', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'configState_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'config_getIdents', 'args': ['self', 'returnType'], 'params': ['*returnType', '**filter'], 'defaults': ('unicode',), 'varargs': None, 'keywords': 'filter'},
        {'name': 'host_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'productOnClient_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'productPropertyState_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
    ]

    results = extendedConfigDataBackend.backend_getInterface()
    for selection in expected:
        for result in results:
            if result['name'] == selection['name']:
                print('Checking {0}'.format(selection['name']))
                for parameter in ('args', 'params', 'defaults', 'varargs', 'keywords'):
                    print('Now checking parameter {0!r}, expecting {1!r}'.format(parameter, selection[parameter]))
                    singleResult = result[parameter]
                    if isinstance(singleResult, (list, tuple)):
                        # We do check the content of the result
                        # because JSONRPC-Backends can only work
                        # with JSON and therefore not with tuples
                        assert len(singleResult) == len(selection[parameter])

                        for exp, res in izip(singleResult, selection[parameter]):
                            assert exp == res
                    else:
                        assert singleResult == selection[parameter]

                break  # We found what we are looking for.
        else:
            pytest.fail("Expected method {0!r} not found".format(selection['name']))


def testSearchingForIdents(extendedConfigDataBackend):
    # TODO: fill the backend with data!
    # TODO: assertions
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(objectClass=Host)(type=OpsiDepotserver))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(|(&(objectClass=ProductOnClient)(productId=product1))(&(objectClass=ProductOnClient)(productId=product2))))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(objectClass=OpsiClient)(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(objectClass=Host)(description=T*))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(objectClass=Host)(description=*))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(&(objectClass=OpsiClient)(ipAddress=192*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
    print(result)
    result = extendedConfigDataBackend.backend_searchIdents(
        '(&(&(objectClass=Product)(description=*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
    print(result)
