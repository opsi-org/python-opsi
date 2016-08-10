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
Mixin for testing various backend methods.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import random
import threading
import time

from ..test_configs import getConfigs, getConfigStates
from ..test_groups import fillBackendWithObjectToGroups
from ..test_hosts import getClients, getConfigServer, getDepotServers
from ..test_products import getProducts

from ..helpers import unittest


try:
    from MySQLdb.constants.ER import DUP_ENTRY
    from MySQLdb import IntegrityError
except ImportError as imperr:
    print(imperr)
    DUP_ENTRY = None
    IntegrityError = None

try:
    from apsw import ConstraintError
except ImportError:
    class ConstraintError(BaseException):
        result = 0


class BackendTestsMixin(object):
    def testObjectMethods(self):
        self.backend.backend_createBase()

        (self.client1, self.client2, self.client3, self.client4,
         self.client5, self.client6, self.client7) = getClients()

        self.clients = [self.client1, self.client2, self.client3,
                        self.client4, self.client5, self.client6, self.client7]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.clients)

        self.configserver1 = getConfigServer()
        self.configservers = [self.configserver1]

        self.depotserver1, self.depotserver2 = getDepotServers()
        self.depotservers = [self.depotserver1, self.depotserver2]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.configservers)
        self.hosts.extend(self.depotservers)

        for host in self.hosts:
            host.setDefaults()
        self.backend.host_createObjects(self.hosts)

        hosts = self.backend.host_getObjects()
        self.assertEqual(len(hosts), len(self.hosts))
        for host in hosts:
            assert host.getOpsiHostKey(), u"Host key for host '%s': %s" % (
                host.getId(), host.getOpsiHostKey())
            for h in self.hosts:
                if (host.id == h.id):
                    h1 = h.toHash()
                    h2 = host.toHash()
                    h1['lastSeen'] = None
                    h2['lastSeen'] = None
                    assert h1 == h2, u"got: '%s', expected: '%s'" % (h1, h2)

        self.backend.host_createObjects(self.depotservers)
        hosts = self.backend.host_getObjects()
        assert len(hosts) == len(
            self.hosts), u"got: '%s', expected: '%s'" % (hosts, len(self.hosts))

        hosts = self.backend.host_getObjects(type='OpsiConfigserver')
        assert len(hosts) == len(self.configservers), u"got: '%s', expected: '%s'" % (
            hosts, len(self.configservers))

        hosts = self.backend.host_getObjects(
            id=[self.client1.getId(), self.client2.getId()])
        assert len(hosts) == 2, u"got: '%s', expected: '%s'" % (hosts, 2)
        ids = []
        for host in hosts:
            ids.append(host.getId())
        assert self.client1.getId() in ids, u"'%s' not in '%s'" % (
            self.client1.getId(), ids)
        assert self.client2.getId() in ids, u"'%s' not in '%s'" % (
            self.client2.getId(), ids)

        hosts = self.backend.host_getObjects(
            attributes=['description', 'notes'], ipAddress=[None])
        count = 0
        for host in self.hosts:
            if host.getIpAddress() is None:
                count += 1

        assert len(hosts) == count
        for host in hosts:
            assert host.getIpAddress() is None, u"got: '%s', expected: '%s'" % (
                host.getIpAddress(), None)
            assert host.getInventoryNumber() is None, u"got: '%s', expected: '%s'" % (
                host.getInventoryNumber(), None)
            assert host.getNotes() is not None, u"got: '%s', expected: '%s'" % (
                host.getNotes(), not None)
            assert host.getDescription() is not None, u"got: '%s', expected: '%s'" % (
                host.getDescription(), not None)

        hosts = self.backend.host_getObjects(
            attributes=['description', 'notes'], ipAddress=None)
        assert len(hosts) == len(
            self.hosts), u"got: '%s', expected: '%s'" % (hosts, len(self.hosts))
        for host in hosts:
            assert host.getIpAddress() is None, u"got: '%s', expected: '%s'" % (
                host.getIpAddress(), None)
            assert host.getInventoryNumber() is None, u"got: '%s', expected: '%s'" % (
                host.getInventoryNumber(), None)

        hosts = self.backend.host_getObjects(
            type=[self.clients[0].getType()])
        assert len(hosts) == len(
            self.clients), u"got: '%s', expected: '%s'" % (hosts, len(self.clients))
        ids = []
        for host in hosts:
            ids.append(host.getId())
        for client in self.clients:
            assert client.getId() in ids, u"'%s' not in '%s'" % (
                client.getId(), ids)

        hosts = self.backend.host_getObjects(
            id=[self.client1.getId(), self.client2.getId()], description=self.client2.getDescription())
        assert len(hosts) == 1, u"got: '%s', expected: '%s'" % (hosts, 1)
        assert hosts[0].description == self.client2.getDescription(), u"got: '%s', expected: '%s'" % (
            hosts[0].description, self.client2.getDescription())
        assert hosts[0].id == self.client2.getId(), u"got: '%s', expected: '%s'" % (
            hosts[0].id, self.client2.getId())

        hosts = self.backend.host_getObjects(
            attributes=['id', 'description'], id=self.client1.getId())
        assert len(hosts) == 1, u"got: '%s', expected: '%s'" % (hosts, 1)
        assert hosts[0].getId() == self.client1.getId(), u"got: '%s', expected: '%s'" % (
            hosts[0].getId(), self.client1.getId())
        assert hosts[0].getDescription() == self.client1.getDescription(), u"got: '%s', expected: '%s'" % (
            hosts[0].getDescription(), self.client1.getDescription())

        self.backend.host_deleteObjects(self.client2)
        hosts = self.backend.host_getObjects(type=[self.client1.getType()])
        assert len(hosts) == len(self.clients) - \
            1, u"got: '%s', expected: '%s'" % (
                hosts, len(self.clients) - 1)
        ids = []
        for host in hosts:
            ids.append(host.getId())

        for client in self.clients:
            if (client.getId() == self.client2.getId()):
                continue
            assert client.getId() in ids, u"'%s' not in '%s'" % (
                client.getId(), ids)

        self.backend.host_createObjects(self.client2)
        self.client2.setDescription('Updated')
        self.backend.host_updateObject(self.client2)
        hosts = self.backend.host_getObjects(description='Updated')
        assert len(hosts) == 1, u"got: '%s', expected: '%s'" % (hosts, 1)
        assert hosts[0].getId() == self.client2.getId(), u"got: '%s', expected: '%s'" % (
            hosts[0].getId(), self.client2.getId())

        self.client2.setDescription(u'Test client 2')
        self.backend.host_createObjects(self.client2)
        hosts = self.backend.host_getObjects(
            attributes=['id', 'description'], id=self.client2.getId())
        assert len(hosts) == 1, u"got: '%s', expected: '%s'" % (hosts, 1)
        assert hosts[0].getId() == self.client2.getId(), u"got: '%s', expected: '%s'" % (
            hosts[0].getId(), self.client2.getId())
        assert hosts[0].getDescription() == 'Test client 2', u"got: '%s', expected: '%s'" % (
            hosts[0].getDescription(), 'Test client 2')

    def testNonObjectMethods(self):
        if 'jsonrpc' in str(self.backend).lower():  # TODO: improve test implementation
            self.skipTest('Unable to run these tests with the current '
                          'implementation of a fake JSONRPC-Backend.')

        # Hosts
        self.backend.host_createOpsiDepotserver(
            id='depot100.test.invalid',
            opsiHostKey='123456789012345678901234567890aa',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depot3.test.invalid/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/products',
            repositoryRemoteUrl='webdavs://depot3.test.invalid:4447/products',
            description='A depot',
            notes='Depot 100',
            hardwareAddress=None,
            ipAddress=None,
            networkAddress='192.168.100.0/24',
            maxBandwidth=0)

        self.products = getProducts()
        self.backend.product_createObjects(self.products)

        self.product4 = self.products[3]
        self.backend.productOnDepot_create(
            productId=self.product4.getId(),
            productType=self.product4.getType(),
            productVersion=self.product4.getProductVersion(),
            packageVersion=self.product4.getPackageVersion(),
            depotId='depot100.test.invalid',
            locked=False
        )

        self.backend.host_createOpsiClient(
            id='client100.test.invalid',
            opsiHostKey=None,
            description='Client 100',
            notes='No notes',
            hardwareAddress='00:00:01:01:02:02',
            ipAddress='192.168.0.200',
            created=None,
            lastSeen=None)

        hosts = self.backend.host_getObjects(id='client100.test.invalid')
        assert len(hosts) == 1, u"got: '%s', expected: '%s'" % (hosts, 1)

        (self.client1, self.client2, self.client3, self.client4,
         self.client5, self.client6, self.client7) = getClients()

        self.clients = [self.client1, self.client2, self.client3,
                        self.client4, self.client5, self.client6, self.client7]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.clients)

        self.configserver1 = getConfigServer()
        self.configservers = [self.configserver1]

        self.depotserver1, self.depotserver2 = getDepotServers()
        self.depotservers = [self.depotserver1, self.depotserver2]

        if not hasattr(self, 'hosts'):
            self.hosts = []
        self.hosts.extend(self.configservers)
        self.hosts.extend(self.depotservers)

        selfIdents = []
        for host in self.hosts:
            selfIdents.append(host.getIdent(returnType='dict'))

        selfIdents.append({'id': 'depot100.test.invalid'})
        selfIdents.append({'id': 'client100.test.invalid'})

        for host in self.hosts:
            host.setDefaults()
        self.backend.host_createObjects(self.hosts)

        ids = self.backend.host_getIdents()
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        ids = self.backend.host_getIdents(id='*100*')
        assert len(ids) == 2, u"got: '%s', expected: '%s'" % (ids, 2)
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        ids = self.backend.host_getIdents(returnType='tuple')
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident[0] == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        ids = self.backend.host_getIdents(returnType='list')
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident[0] == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        ids = self.backend.host_getIdents(returnType='dict')
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident['id'] == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        (self.config1, self.config2, self.config3, self.config4,
         self.config5, self.config6) = getConfigs(self.depotserver1.id)

        self.configs = [
            self.config1, self.config2, self.config3, self.config4,
            self.config5, self.config6
        ]

        selfIdents = []
        for config in self.configs:
            selfIdents.append(config.getIdent(returnType='dict'))

        for config in self.configs:
            config.setDefaults()
        self.backend.config_createObjects(self.configs)

        ids = self.backend.config_getIdents()
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            found = False
            for selfIdent in selfIdents:
                if (ident == selfIdent['id']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        (self.configState1, self.configState2, self.configState3,
         self.configState4, self.configState5, self.configState6,
         self.configState7) = getConfigStates(self.configs, self.clients, self.depotservers)

        self.configStates = [
            self.configState1, self.configState2, self.configState3,
            self.configState4, self.configState5, self.configState6,
            self.configState7
        ]
        # some deleted?
        self.backend.configState_createObjects(self.configStates)

        selfIdents = []
        for configState in self.configStates:
            selfIdents.append(configState.getIdent(returnType='dict'))

        ids = self.backend.configState_getIdents()
        assert len(ids) == len(
            selfIdents), u"got: '%s', expected: '%s'" % (ids, len(selfIdents))
        for ident in ids:
            i = ident.split(';')
            found = False
            for selfIdent in selfIdents:
                if (i[0] == selfIdent['configId']) and (i[1] == selfIdent['objectId']):
                    found = True
                    break
            assert found, u"'%s' not in '%s'" % (ident, selfIdents)

        # TODO: assertions
        result = self.backend.backend_searchIdents(
            '(&(objectClass=Host)(type=OpsiDepotserver))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(&(objectClass=Host)(type=OpsiDepotserver))(objectClass=Host))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(|(&(objectClass=OpsiClient)(id=client1*))(&(objectClass=OpsiClient)(id=client2*)))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(&(objectClass=OpsiClient))(&(objectClass=ProductOnClient)(installationStatus=installed))(|(&(objectClass=ProductOnClient)(productId=product1))(&(objectClass=ProductOnClient)(productId=product2))))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(objectClass=OpsiClient)(&(objectClass=ProductOnClient)(installationStatus=installed))(&(objectClass=ProductOnClient)(productId=product1)))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(objectClass=Host)(description=T*))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(objectClass=Host)(description=*))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(&(objectClass=OpsiClient)(ipAddress=192*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
        print(result)
        result = self.backend.backend_searchIdents(
            '(&(&(objectClass=Product)(description=*))(&(objectClass=ProductOnClient)(installationStatus=installed)))')
        print(result)

        hosts = self.backend.host_getObjects()
        assert len(hosts) > 1
        self.backend.host_delete(id=[])  # Deletes all clients
        hosts = self.backend.host_getObjects()

        # This is special for the file backend: there the ConfigServer
        # will stay in the backend and does not get deleted.
        assert len(hosts) <= 1

class BackendPerformanceTestMixin(object):
    def testBackendPerformance(self, clientCount=500, productCount=50):
        return # TODO: make real test

        start = time.time()
        for i in range(clientCount):
            ip = i
            while (ip > 255):
                ip -= 255
            self.backend.host_createOpsiClient(
                id='client%d.test.invalid' % i,
                opsiHostKey='01234567890123456789012345678912',
                description='Client %d' % i,
                notes='No notes',
                hardwareAddress='',
                ipAddress='192.168.0.%d' % ip,
                created=None,
                lastSeen=None
            )
        print(u"Took %.2f seconds to create %d clients" %
                      ((time.time() - start), clientCount))

        start = time.time()
        self.backend.host_getObjects(
            attributes=['id'], ipAddress='192.168.0.100')
        print(u"Took %.2f seconds to search ip address in %d clients" %
                      ((time.time() - start), clientCount))

        #start = time.time()
        #self.backend.host_delete(id = [])
        #logger.notice(u"Took %.2f seconds to delete %d clients" % ((time.time()-start), clientCount))

        start = time.time()
        for i in range(productCount):
            method = random.choice(
                (self.backend.product_createLocalboot, self.backend.product_createNetboot))
            method(
                id='product%d' % i,
                productVersion=random.choice(
                    ('1.0', '2', 'xxx', '3.1', '4')),
                packageVersion=random.choice(
                    ('1', '2', 'y', '3', '10', 11, 22)),
                name='Product %d' % i,
                licenseRequired=random.choice((None, True, False)),
                setupScript=random.choice(('setup.ins', None)),
                uninstallScript=random.choice(('uninstall.ins', None)),
                updateScript=random.choice(('update.ins', None)),
                alwaysScript=random.choice(('always.ins', None)),
                onceScript=random.choice(('once.ins', None)),
                priority=random.choice((-100, -90, -30, 0, 30, 40, 60, 99)),
                description=random.choice(
                    ('Test product %d' % i, 'Some product', '--------', '', None)),
                advice=random.choice(
                    ('Nothing', 'Be careful', '--------', '', None)),
                changelog=None,
                windowsSoftwareIds=None
            )

        print(u"Took %.2f seconds to create %d products" %
                      ((time.time() - start), productCount))

        #start = time.time()
        #self.backend.product_getObjects(attributes = ['id'], uninstallScript = 'uninstall.ins')
        #logger.notice(u"Took %.2f seconds to search uninstall script in %d products" % ((time.time()-start), productCount))

        start = time.time()
        nrOfproductOnDepots = 0
        for product in self.backend.product_getObjects():
            for depotId in self.backend.host_getIdents(type='OpsiDepotserver'):
                nrOfproductOnDepots += 1
                self.backend.productOnDepot_create(
                    productId=product.id,
                    productType=product.getType(),
                    productVersion=product.productVersion,
                    packageVersion=product.packageVersion,
                    depotId=depotId
                )
        print(u"Took %.2f seconds to create %d productsOnDepot" %
                      ((time.time() - start), nrOfproductOnDepots))

        start = time.time()
        nrOfproductOnClients = 0
        for product in self.backend.product_getObjects():
            actions = ['none', None]
            if product.setupScript:
                actions.append('setup')
            if product.uninstallScript:
                actions.append('uninstall')
            if product.onceScript:
                actions.append('once')
            if product.alwaysScript:
                actions.append('always')
            if product.updateScript:
                actions.append('update')
            for clientId in self.backend.host_getIdents(type='OpsiClient'):
                if random.choice((True, False, False, False)):
                    nrOfproductOnClients += 1
                    self.backend.productOnClient_create(
                        productId=product.id,
                        productType=product.getType(),
                        clientId=clientId,
                        installationStatus=random.choice(
                            ('installed', 'not_installed')),
                        actionRequest=random.choice(actions),
                        actionProgress=random.choice(
                            ('installing 30%', 'uninstalling 30%', 'syncing 60%', None, '', 'failed')),
                        productVersion=product.productVersion,
                        packageVersion=product.packageVersion,
                        modificationTime=None
                    )
        print(
            u"Took %.2f seconds to create %d random productsOnClient" %
            ((time.time() - start), nrOfproductOnClients))


class MultiThreadingTestMixin(object):
    NUMBER_OF_THREADS = 50

    @unittest.skipIf(DUP_ENTRY is None or IntegrityError is None,
                     'Missing imports from MySQLdb-module.')
    def testMultithreading(self):
        o2g, _, clients = fillBackendWithObjectToGroups(self.backend)
        self.client1 = clients[0]
        self.client2 = clients[1]
        self.objectToGroup1 = o2g[0]
        self.objectToGroup2 = o2g[0]

        class MultiThreadTest(threading.Thread):
            def __init__(self, backendTest):
                threading.Thread.__init__(self)
                self._backendTest = backendTest
                self.exitCode = 0
                self.errorMessage = None

            def run(self):
                try:
                    print(u"Thread %s started" % self)
                    time.sleep(1)
                    self._backendTest.backend.host_getObjects()
                    self._backendTest.backend.host_deleteObjects(self._backendTest.client1)

                    self._backendTest.backend.host_getObjects()
                    self._backendTest.backend.host_deleteObjects(self._backendTest.client2)

                    self._backendTest.backend.host_createObjects(self._backendTest.client2)
                    self._backendTest.backend.host_createObjects(self._backendTest.client1)
                    self._backendTest.backend.objectToGroup_createObjects(self._backendTest.objectToGroup1)
                    self._backendTest.backend.objectToGroup_createObjects(self._backendTest.objectToGroup2)

                    self._backendTest.backend.host_getObjects()
                    self._backendTest.backend.host_createObjects(self._backendTest.client1)
                    self._backendTest.backend.host_deleteObjects(self._backendTest.client2)
                    self._backendTest.backend.host_createObjects(self._backendTest.client1)
                    self._backendTest.backend.host_getObjects()
                    print(u"Thread %s done" % self)
                except IntegrityError as e:
                    if e[0] != DUP_ENTRY:
                        self.errorMessage = e
                        self.exitCode = 1
                except ConstraintError as e:
                    if e.result != 19:  # column is not unique
                        self.errorMessage = e
                        self.exitCode = 1
                except Exception as e:
                    self.errorMessage = e
                    self.exitCode = 1

        mtts = [MultiThreadTest(self) for _ in range(self.NUMBER_OF_THREADS)]
        for mtt in mtts:
            mtt.start()

        for mtt in mtts:
            mtt.join()

        try:
            self.backend.host_createObjects(self.client1)

            while len(mtts) > 0:
                mtt = mtts.pop(0)
                if not mtt.isAlive():
                    self.assertEqual(mtt.exitCode, 0, u"Mutlithreading test failed: Exit Code %s: %s"% (mtt.exitCode, mtt.errorMessage))
                else:
                    mtts.append(mtt)
        except Exception as e:
            self.fail(u"Creating object on backend failed: {0}".format(e))
