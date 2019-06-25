# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2019 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded extension `20_easy.conf`.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/20_easy.conf``.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import random

import pytest

from OPSI.Object import UnicodeConfig

from .test_hosts import getConfigServer, getDepotServers, getClients


@pytest.fixture
def clients():
    return getClients()


@pytest.fixture
def depots():
    return getDepotServers()


@pytest.fixture
def configServer():
    return getConfigServer()


@pytest.fixture
def hosts(clients, depots, configServer):
    hosts = [getConfigServer()]
    hosts.extend(depots)
    hosts.extend(clients)

    return hosts


def testGetClients(backendManager, hosts, clients):
    for host in hosts:
        backendManager.host_insertObject(host)

    newClients = backendManager.getClients()

    assert len(newClients) == len(clients)
    clientIds = [client.id for client in clients]

    for client in newClients:
        assert isinstance(client, dict)

        assert 'type' not in client
        assert 'id' not in client
        assert 'depotId' in client

        for key, value in client.items():
            assert value is not None, 'Key {} has a None value'.format(key)

        clientIds.remove(client['hostId'])

    assert not clientIds, 'possibly duplicate clients'


def testGetClientIDs(backendManager, hosts, clients):
    for host in hosts:
        backendManager.host_insertObject(host)

    originalClientIDs = [client.id for client in clients]
    clientIDs = backendManager.getClientIDs()

    assert len(originalClientIDs) == len(clientIDs)

    diff = set(originalClientIDs) ^ set(clientIDs)
    assert not diff


def testGetClientsOnDepot(backendManager, hosts, clients, configServer):
    for host in hosts:
        backendManager.host_insertObject(host)

    clientIds = backendManager.getClientsOnDepot(configServer.id)
    assert not clientIds, 'Default mapping appeared somewhere'

    clientConfigDepotId = UnicodeConfig(
        id=u'clientconfig.depot.id',
        description=u'Depotserver to use',
        possibleValues=[],
        defaultValues=[configServer.id]
    )
    backendManager.config_createObjects(clientConfigDepotId)
    clientIds = backendManager.getClientsOnDepot(configServer.id)
    assert len(clientIds) == len(clients)
    diff = set(clientIds) ^ set([client.id for client in clients])
    assert not diff


@pytest.mark.parametrize("value", [1, 'justahostname'])
def testGetClientsOnDepotExpectsValidIDs(backendManager, value):
    with pytest.raises(ValueError):
        backendManager.getClientsOnDepot(value)


def testGetClientsOnDepotWithDifferentDepot(backendManager, hosts, clients, depots, configServer):
    for host in hosts:
        backendManager.host_insertObject(host)

    clientConfigDepotId = UnicodeConfig(
        id=u'clientconfig.depot.id',
        description=u'Depotserver to use',
        possibleValues=[],
        defaultValues=[configServer.id]
    )
    backendManager.config_createObjects(clientConfigDepotId)

    depot = random.choice(depots)
    clientIds = backendManager.getClientsOnDepot(depot.id)
    assert len(clientIds) == 0

    client = random.choice(clients)
    backendManager.configState_create(clientConfigDepotId.id, client.id, values=[depot.id])

    clientIds = backendManager.getClientsOnDepot(depot.id)
    assert len(clientIds) == 1
    assert clientIds[0] == client.id

    assert len(backendManager.getClientsOnDepot(configServer.id)) == len(clients) - 1


@pytest.mark.parametrize("productIds, installationStatus", [
    ([], None),
    ([''], None),
    (['myproduct'], 1),
    (['myproduct'], 'not_a_valid_status'),
])
def testGetClientsWithProductsWithInvalidParameters(backendManager, productIds, installationStatus):
    with pytest.raises(ValueError):
        backendManager.getClientsWithProducts(productIds, installationStatus)
