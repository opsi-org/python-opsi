#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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

import pytest

from OPSI.Object import (HostGroup, ObjectToGroup, OpsiClient, OpsiConfigserver,
    OpsiDepotserver)
from OPSI.Types import BackendError, BackendMissingDataError


def getClients():
    client1 = OpsiClient(
        id='client1.test.invalid',
        description='Test client 1',
        notes='Notes ...',
        hardwareAddress='00:01:02:03:04:05',
        ipAddress='192.168.1.100',
        lastSeen='2009-01-01 00:00:00',
        opsiHostKey='45656789789012789012345612340123',
        inventoryNumber=None
    )

    client2 = OpsiClient(
        id='client2.test.invalid',
        description='Test client 2',
        notes=';;;;;;;;;;;;;;',
        hardwareAddress='00-ff0aa3:0b-B5',
        opsiHostKey='59051234345678890121678901223467',
        inventoryNumber='00000000003',
        oneTimePassword='logmein'
    )

    client3 = OpsiClient(
        id='client3.test.invalid',
        description='Test client 3',
        notes='#############',
        inventoryNumber='XYZABC_1200292'
    )

    client4 = OpsiClient(
        id='client4.test.invalid',
        description='Test client 4',
    )

    client5 = OpsiClient(
        id='client5.test.invalid',
        description='Test client 5',
        oneTimePassword='abe8327kjdsfda'
    )

    client6 = OpsiClient(
        id='client6.test.invalid',
        description='Test client 6',
    )

    client7 = OpsiClient(
        id='client7.test.invalid',
        description='Test client 7',
    )

    return client1, client2, client3, client4, client5, client6, client7


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


def testDeletingAllHosts(extendedConfigDataBackend):
    extendedConfigDataBackend.host_createObjects(getClients())

    hosts = extendedConfigDataBackend.host_getObjects()
    assert len(hosts) > 1
    extendedConfigDataBackend.host_delete(id=[])  # Deletes all clients
    hosts = extendedConfigDataBackend.host_getObjects()

    # This is special for the file backend: there the ConfigServer
    # will stay in the backend and does not get deleted.
    assert len(hosts) <= 1


def testGettingHostIdents(extendedConfigDataBackend):
    clients = getClients()
    configserver1 = getConfigServer()
    depots = getDepotServers()

    extendedConfigDataBackend.host_createObjects(clients)
    extendedConfigDataBackend.host_createObjects(depots)
    extendedConfigDataBackend.host_createObjects(configserver1)
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

    selfIdents = []
    for host in clients:
        selfIdents.append(host.getIdent(returnType='dict'))
    for host in depots:
        selfIdents.append(host.getIdent(returnType='dict'))
    selfIdents.append(configserver1.getIdent(returnType='dict'))

    selfIdents.append({'id': 'depot100.test.invalid'})
    selfIdents.append({'id': 'client100.test.invalid'})

    # TODO: split this into multiple tests

    ids = extendedConfigDataBackend.host_getIdents()
    assert len(ids) == len(
        selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
    for ident in ids:
        found = False
        for selfIdent in selfIdents:
            if (ident == selfIdent['id']):
                found = True
                break
        assert found, u"'%s' not in '%s'" % (ident, selfIdents)

    ids = extendedConfigDataBackend.host_getIdents(id='*100*')
    assert len(ids) == 2, u"got: '%s', expected: '%s'" % (ids, 2)
    for ident in ids:
        found = False
        for selfIdent in selfIdents:
            if (ident == selfIdent['id']):
                found = True
                break
        assert found, u"'%s' not in '%s'" % (ident, selfIdents)

    ids = extendedConfigDataBackend.host_getIdents(returnType='tuple')
    assert len(ids) == len(
        selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
    for ident in ids:
        found = False
        for selfIdent in selfIdents:
            if (ident[0] == selfIdent['id']):
                found = True
                break
        assert found, u"'%s' not in '%s'" % (ident, selfIdents)

    ids = extendedConfigDataBackend.host_getIdents(returnType='list')
    assert len(ids) == len(
        selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
    for ident in ids:
        found = False
        for selfIdent in selfIdents:
            if (ident[0] == selfIdent['id']):
                found = True
                break
        assert found, u"'%s' not in '%s'" % (ident, selfIdents)

    ids = extendedConfigDataBackend.host_getIdents(returnType='dict')
    assert len(ids) == len(
        selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
    for ident in ids:
        found = False
        for selfIdent in selfIdents:
            if (ident['id'] == selfIdent['id']):
                found = True
                break
        assert found, u"'%s' not in '%s'" % (ident, selfIdents)


def testRenamingOpsiClientFailsIfNewIdAlreadyExisting(extendedConfigDataBackend):
    backend = extendedConfigDataBackend

    host = OpsiClient(id='old.test.invalid')
    anotherHost = OpsiClient(id='new.test.invalid')

    backend.host_insertObject(host)
    backend.host_insertObject(anotherHost)

    with pytest.raises(BackendError):
        backend.host_renameOpsiClient(host.id, anotherHost.id)


def testRenamingOpsiClientFailsIfOldClientMissing(extendedConfigDataBackend):
    with pytest.raises(BackendMissingDataError):
        extendedConfigDataBackend.host_renameOpsiClient('nonexisting.test.invalid', 'new.test.invalid')


def testRenamingOpsiClient(extendedConfigDataBackend):
    backend = extendedConfigDataBackend

    host = OpsiClient(id='jacket.test.invalid')
    backend.host_insertObject(host)

    protagonists = HostGroup("protagonists")
    backend.group_insertObject(protagonists)

    backend.objectToGroup_insertObject(ObjectToGroup(protagonists.getType(), protagonists.id, host.id))

    oldId = host.id
    newId = 'richard.test.invalid'

    backend.host_renameOpsiClient(oldId, newId)

    assert not backend.host_getObjects(id=oldId)
    assert backend.host_getObjects(id=newId)

    # We want to make sure that the membership of groups does get
    # changed aswell.
    assert not backend.objectToGroup_getObjects(objectId=oldId)
    memberships = backend.objectToGroup_getObjects(objectId=newId)
    assert memberships
    membership = memberships[0]
    assert membership.objectId == newId
    assert membership.groupId == protagonists.id
