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
Testing the functionality of working with hosts.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import socket
from OPSI.Object import OpsiConfigserver, OpsiDepotserver

from .BackendTestMixins.Clients import getClients


def getConfigServer():
    serverId = socket.getfqdn()
    if serverId.count('.') < 2:
        raise Exception(u"Failed to get fqdn: %s" % serverId)

    return OpsiConfigserver(
            id=serverId,
            opsiHostKey='71234545689056789012123678901234',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl=u'smb://%s/opt_pcbin/install' % serverId.split(
                '.')[0],
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl=u'webdavs://%s:4447/repository' % serverId,
            description='The configserver',
            notes='Config 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000001',
            networkAddress='192.168.1.0/24',
            maxBandwidth=10000
        )


def getDepotServers():
    depotserver1 = OpsiDepotserver(
        id='depotserver1.uib.local',
        opsiHostKey='19012334567845645678901232789012',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl='smb://depotserver1.test.invalid/opt_pcbin/install',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl='webdavs://depotserver1.test.invalid:4447/repository',
        description='A depot',
        notes='D€pot 1',
        hardwareAddress=None,
        ipAddress=None,
        inventoryNumber='00000000002',
        networkAddress='192.168.2.0/24',
        maxBandwidth=10000
    )

    depotserver2 = OpsiDepotserver(
        id='depotserver2.test.invalid',
        opsiHostKey='93aa22f38a678c64ef678a012d2e82f2',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl='smb://depotserver2.test.invalid/opt_pcbin',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl='webdavs://depotserver2.test.invalid:4447/repository',
        description='Second depot',
        notes='no notes here',
        hardwareAddress='00:01:09:07:11:aa',
        ipAddress='192.168.10.1',
        inventoryNumber='',
        networkAddress='192.168.10.0/24',
        maxBandwidth=240000
    )

    return depotserver1, depotserver2


def test_getHostsHostOnBackend(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()

    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    hosts = extendedConfigDataBackend.host_getObjects()
    assert hosts
    assert len(hosts) == len(hostsOriginal)


def test_verifyHosts(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    hosts = extendedConfigDataBackend.host_getObjects()
    assert hosts
    for host in hosts:
        assert host.getOpsiHostKey() is not None

        for h in hostsOriginal:
            if host.id == h.id:
                h1 = h.toHash()
                h2 = host.toHash()
                h1['lastSeen'] = None
                h2['lastSeen'] = None
                h1['created'] = None
                h2['created'] = None
                h1['inventoryNumber'] = None
                h2['inventoryNumber'] = None
                h1['notes'] = None
                h2['notes'] = None
                h1['opsiHostKey'] = None
                h2['opsiHostKey'] = None
                h1['isMasterDepot'] = None
                h2['isMasterDepot'] = None
                assert h1 == h2


def test_createDepotserverOnBackend(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    hosts = extendedConfigDataBackend.host_getObjects(type='OpsiConfigserver')
    assert len(hosts) == 1


def test_clientsOnBackend(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    hosts = extendedConfigDataBackend.host_getObjects(type=[clients[0].getType()])
    assert len(hosts) == len(clients)
    ids = [host.getId() for host in hosts]

    for client in clients:
        assert client.getId() in ids


def test_selectClientsOnBackend(extendedConfigDataBackend):
    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)

    client1, client2 = clients[:2]

    hosts = extendedConfigDataBackend.host_getObjects(id=[client1.getId(), client2.getId()])
    assert len(hosts) == 2

    ids = [host.getId() for host in hosts]
    assert client1.getId() in ids
    assert client2.getId() in ids


def test_hostAttributes(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    hosts = extendedConfigDataBackend.host_getObjects(attributes=['description', 'notes'], ipAddress=[None])
    count = sum(1 for host in hostsOriginal if host.getIpAddress() is None)

    assert len(hosts) == count
    for host in hosts:
        assert host.getIpAddress() is None
        assert host.getInventoryNumber() is None
        assert host.getNotes() is not None
        assert host.getDescription() is not None

    hosts = extendedConfigDataBackend.host_getObjects(attributes=['description', 'notes'], ipAddress=None)
    assert len(hosts) == len(hostsOriginal)

    for host in hosts:
        assert host.getIpAddress() is None
        assert host.getInventoryNumber() is None


def test_selectClientsByDescription(extendedConfigDataBackend):
    clients = getClients()
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    client2 = clients[1]

    hosts = extendedConfigDataBackend.host_getObjects(type=["OpsiClient"], description=client2.getDescription())

    assert len(hosts) == 1
    assert hosts[0].id == client2.getId()
    assert hosts[0].description == client2.getDescription()


def test_selectClientById(extendedConfigDataBackend):
    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)
    client1 = clients[0]

    hosts = extendedConfigDataBackend.host_getObjects(attributes=['id', 'description'], id=client1.getId())

    assert len(hosts) == 1
    assert hosts[0].id == client1.getId()
    assert hosts[0].description == client1.getDescription()


def test_deleteClientFromBackend(extendedConfigDataBackend):
    clients = list(getClients())
    configServer = getConfigServer()
    depots = getDepotServers()
    hostsOriginal = list(clients) + [configServer] + list(depots)
    extendedConfigDataBackend.host_createObjects(hostsOriginal)

    client2 = clients[1]
    extendedConfigDataBackend.host_deleteObjects(client2)

    hosts = extendedConfigDataBackend.host_getObjects(type=["OpsiClient"])
    assert len(hosts) == len(clients) - 1

    ids = [host.getId() for host in hosts]
    assert client2.getId() not in ids

    del clients[clients.index(client2)]
    for client in clients:
        assert client.getId() in ids


def test_updateObjectOnBackend(extendedConfigDataBackend):
    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)

    client2 = clients[1]
    client2.setDescription('Updated')
    extendedConfigDataBackend.host_updateObject(client2)
    hosts = extendedConfigDataBackend.host_getObjects(description='Updated')
    assert len(hosts) == 1
    assert hosts[0].getId() == client2.getId()


def test_createObjectOnBackend(extendedConfigDataBackend):
    clients = getClients()
    extendedConfigDataBackend.host_createObjects(clients)

    client2 = clients[1]
    extendedConfigDataBackend.host_deleteObjects(client2)

    client2.setDescription(u'Test client 2')
    extendedConfigDataBackend.host_createObjects(client2)
    hosts = extendedConfigDataBackend.host_getObjects(attributes=['id', 'description'], id=client2.getId())
    assert len(hosts) == 1
    assert hosts[0].getId() == client2.getId()
    assert hosts[0].getDescription() == u'Test client 2'
