#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
Backend mixin for testing the functionality of working with hosts.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import socket
from OPSI.Object import OpsiConfigserver, OpsiDepotserver

from .Clients import getClients


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


class HostsMixin(object):
    def setUpHosts(self):
        self.configserver1 = getConfigServer()
        self.configservers = [self.configserver1]

        self.depotserver1, self.depotserver2 = getDepotServers()
        self.depotservers = [self.depotserver1, self.depotserver2]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.configservers)
        self.hosts.extend(self.depotservers)

    def createHostsOnBackend(self):
        for host in self.hosts:
            host.setDefaults()
        self.backend.host_createObjects(self.hosts)


class HostsTestMixin(object):
    # TODO: this should be inside the general backend test but then JSONRPC-Backend would fail!

    def test_getHostsHostOnBackend(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()

        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        hosts = self.backend.host_getObjects()
        assert hosts
        self.assertEqual(len(hosts), len(hostsOriginal))

    def test_verifyHosts(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        hosts = self.backend.host_getObjects()
        assert hosts
        for host in hosts:
            self.assertIsNotNone(host.getOpsiHostKey())
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
                    self.assertEqual(h1, h2)

    def test_createDepotserverOnBackend(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        hosts = self.backend.host_getObjects(type='OpsiConfigserver')
        self.assertEqual(len(hosts), 1)

    def test_clientsOnBackend(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        hosts = self.backend.host_getObjects(type=[clients[0].getType()])
        self.assertEqual(len(hosts), len(clients))
        ids = [host.getId() for host in hosts]

        for client in clients:
            self.assertIn(client.getId(), ids)

    def test_selectClientsOnBackend(self):
        clients = getClients()
        self.backend.host_createObjects(clients)

        client1, client2 = clients[:2]

        hosts = self.backend.host_getObjects(id=[client1.getId(), client2.getId()])
        self.assertEqual(len(hosts), 2)

        ids = [host.getId() for host in hosts]
        self.assertIn(client1.getId(), ids)
        self.assertIn(client2.getId(), ids)

    def test_hostAttributes(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        hosts = self.backend.host_getObjects(attributes=['description', 'notes'], ipAddress=[None])
        count = sum(1 for host in hostsOriginal if host.getIpAddress() is None)

        self.assertEqual(len(hosts), count)
        for host in hosts:
            self.assertIsNone(host.getIpAddress())
            self.assertIsNone(host.getInventoryNumber())
            self.assertIsNotNone(host.getNotes())
            self.assertIsNotNone(host.getDescription())

        hosts = self.backend.host_getObjects(attributes=['description', 'notes'], ipAddress=None)
        self.assertEqual(len(hosts), len(hostsOriginal))

        for host in hosts:
            self.assertIsNone(host.getIpAddress())
            self.assertIsNone(host.getInventoryNumber())

    def test_selectClientsByDescription(self):
        clients = getClients()
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        client2 = clients[1]

        hosts = self.backend.host_getObjects(type=["OpsiClient"], description=client2.getDescription())

        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].id, client2.getId())
        self.assertEqual(hosts[0].description, client2.getDescription())

    def test_selectClientById(self):
        clients = getClients()
        self.backend.host_createObjects(clients)
        client1 = clients[0]

        hosts = self.backend.host_getObjects(attributes=['id', 'description'], id=client1.getId())

        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].id, client1.getId())
        self.assertEqual(hosts[0].description, client1.getDescription())

    def test_deleteClientFromBackend(self):
        clients = list(getClients())
        configServer = getConfigServer()
        depots = getDepotServers()
        hostsOriginal = list(clients) + [configServer] + list(depots)
        self.backend.host_createObjects(hostsOriginal)

        client2 = clients[1]
        self.backend.host_deleteObjects(client2)

        hosts = self.backend.host_getObjects(type=["OpsiClient"])
        self.assertEqual(len(hosts), len(clients) - 1)

        ids = [host.getId() for host in hosts]
        self.assertNotIn(client2.getId(), ids)

        del clients[clients.index(client2)]
        for client in clients:
            self.assertIn(client.getId(), ids)

    def test_updateObjectOnBackend(self):
        clients = getClients()
        self.backend.host_createObjects(clients)

        client2 = clients[1]
        client2.setDescription('Updated')
        self.backend.host_updateObject(client2)
        hosts = self.backend.host_getObjects(description='Updated')
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].getId(), client2.getId())

    def test_createObjectOnBackend(self):
        clients = getClients()
        self.backend.host_createObjects(clients)

        client2 = clients[1]
        self.backend.host_deleteObjects(client2)

        client2.setDescription(u'Test client 2')
        self.backend.host_createObjects(client2)
        hosts = self.backend.host_getObjects(attributes=['id', 'description'], id=client2.getId())
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].getId(), client2.getId())
        self.assertEqual(hosts[0].getDescription(), u'Test client 2')
