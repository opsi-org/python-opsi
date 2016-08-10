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
Mixin for testing various backend methods.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import random
import threading
import time

from ..test_groups import fillBackendWithObjectToGroups
from ..test_hosts import getClients, getConfigServer, getDepotServers

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
