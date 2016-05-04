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
Testing ACL on the backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import unittest

import OPSI.Types
import OPSI.Object
from OPSI.Util import getfqdn
from OPSI.Util.File.Opsi import BackendACLFile
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.BackendManager import BackendAccessControl

from .BackendTestMixins.Products import ProductsOnClientsMixin, ProductPropertyStatesMixin
from .Backends.File import FileBackendMixin
from .Backends.SQLite import getSQLiteBackend
from .BackendTestMixins.Hosts import HostsMixin
from .helpers import workInTemporaryDirectory, requiresModulesFile
from .test_backend_replicator import (fillBackendWithHosts,
    fillBackendWithProducts, fillBackendWithProductOnClients)

import pytest


def testParsingBackendACLFile():
    with workInTemporaryDirectory() as tempDir:
        aclFile = os.path.join(tempDir, 'acl.conf')
        with open(aclFile, 'w') as exampleConfig:
            exampleConfig.write(
'''
host_.*: opsi_depotserver(depot1.test.invalid, depot2.test.invalid); opsi_client(self,  attributes (attr1, attr2)); sys_user(some user, some other user); sys_group(a_group, group2)
'''
        )

        expectedACL = [
            [u'host_.*', [
                {'denyAttributes': [], 'type': u'opsi_depotserver', 'ids': [u'depot1.test.invalid', u'depot2.test.invalid'], 'allowAttributes': []},
                {'denyAttributes': [], 'type': u'opsi_client', 'ids': [u'self'], 'allowAttributes': [u'attr1', u'attr2']},
                {'denyAttributes': [], 'type': u'sys_user', 'ids': [u'some user', u'some other user'], 'allowAttributes': []},
                {'denyAttributes': [], 'type': u'sys_group', 'ids': [u'a_group', u'group2'], 'allowAttributes': []}
                ]
            ]
        ]

        assert expectedACL == BackendACLFile(aclFile).parse()


class ACLEnforcingTestCase(unittest.TestCase, FileBackendMixin,
    ProductsOnClientsMixin, ProductPropertyStatesMixin, HostsMixin):

    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testAllowingMethodsForSpecificClient(self):
        """
        Access to methods can be limited to specific clients.

        In this example client1 can access host_getObjects but not
        config_getObjects.
        """
        self.setUpClients()
        self.createHostsOnBackend()

        backendAccessControl = BackendAccessControl(
            username=self.client1.id,
            password=self.client1.opsiHostKey,
            backend=self.backend,
            acl=[
                ['host_getObjects',   [{'type': u'opsi_client', 'ids':[self.client1.id], 'denyAttributes': [], 'allowAttributes': []}]],
                ['config_getObjects', [{'type': u'opsi_client', 'ids':[self.client2.id], 'denyAttributes': [], 'allowAttributes': []}]],
            ]
        )

        backendAccessControl.host_getObjects()
        self.assertRaises(OPSI.Types.BackendPermissionDeniedError, backendAccessControl.config_getObjects)

    def testDenyingAttributes(self):
        """
        Access to attributes can be denied.

        In this case the backend can only access its own opsiHostKey and
        for other clients no value is given.
        """
        self.setUpClients()
        self.createHostsOnBackend()

        backendAccessControl = BackendAccessControl(
            username=self.client1.id,
            password=self.client1.opsiHostKey,
            backend=self.backend,
            acl=[
                ['host_getObjects', [{'type': u'self',        'ids': [], 'denyAttributes': [],              'allowAttributes': []}]],
                ['host_getObjects', [{'type': u'opsi_client', 'ids': [], 'denyAttributes': ['opsiHostKey'], 'allowAttributes': []}]],
            ]
        )

        for host in backendAccessControl.host_getObjects():
            if host.id == self.client1.id:
                self.assertEquals(host.opsiHostKey, self.client1.opsiHostKey)
            else:
                self.assertEquals(host.opsiHostKey, None)

    # def testAllowingOnlyUpdatesOfSpecificAttributes(self):
    #     self.setUpClients()
    #     self.createHostsOnBackend()

    #     backendAccessControl = BackendAccessControl(
    #         username=self.client1.id,
    #         password=self.client1.opsiHostKey,
    #         backend=self.backend,
    #         acl=[
    #             ['host_.*',       [{'type': u'self',        'ids': [], 'denyAttributes': [],              'allowAttributes': []}]],
    #             ['host_get.*',    [{'type': u'opsi_client', 'ids': [], 'denyAttributes': ['opsiHostKey'], 'allowAttributes': []}]],
    #             ['host_update.*', [{'type': u'opsi_client', 'ids': [], 'denyAttributes': [],              'allowAttributes': ['notes']}]]
    #         ]
    #     )

    #     self.assertTrue(
    #         len(backendAccessControl.host_getObjects()) > 1,
    #         msg="Backend must be able to access all objects not only itself!"
    #     )
    #     self.client1.setDescription("Access to self is allowed.")
    #     self.client1.setNotes("Access to self is allowed.")
    #     backendAccessControl.host_updateObject(self.client1)

    #     self.client2.setDescription("Only updating notes is allowed.")
    #     self.assertRaises(OPSI.Types.BackendPermissionDeniedError, backendAccessControl.host_updateObject, self.client2)

    #     self.assertFalse(backendAccessControl.host_getObjects())
    #     newClient3 = OPSI.Object.OpsiClient(
    #         id=self.client3.id,
    #         notes="New notes are okay"
    #     )
    #     # backendAccessControl.host_updateObject(newClient3)
    #     self.assertFalse(backendAccessControl.host_getObjects(id=self.client3.id))
    #     client3FromBackend = backendAccessControl.host_getObjects(id=self.client3.id)[0]
    #     self.assertEquals(client3FromBackend.notes, newClient3.notes)

    def testDenyingAccessToOtherObjects(self):
        """
        It must be possible to deny access to foreign objects.

        In this test we first make sure that the access to productOnClient_create
        is possible for the object accessing the backend.
        After that we test the same referencing another object which we
        want to fail.
        """
        serverFqdn = OPSI.Types.forceHostId(getfqdn())  # using local FQDN
        depotserver1 = {
            "isMasterDepot" : True,
            "type" : "OpsiConfigserver",
            "id" : serverFqdn,
        }

        self.backend.host_createObjects(depotserver1)

        self.setUpClients()
        self.setUpProducts()

        self.createHostsOnBackend()
        self.createProductsOnBackend()

        self.backend.config_createObjects([{
            "id": u'clientconfig.depot.id',
            "type": "UnicodeConfig",
        }])
        self.backend.configState_create(u'clientconfig.depot.id', self.client1.getId(), values=[depotserver1['id']])

        productOnDepot1 = OPSI.Object.ProductOnDepot(
            productId=self.product1.getId(),
            productType=self.product1.getType(),
            productVersion=self.product1.getProductVersion(),
            packageVersion=self.product1.getPackageVersion(),
            depotId=depotserver1['id'],
            locked=False
        )

        self.backend.productOnDepot_createObjects([productOnDepot1])


        backendAccessControl = BackendAccessControl(
            username=self.client1.id,
            password=self.client1.opsiHostKey,
            backend=self.backend,
            acl=[
                ['productOnClient_create', [{'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}]],
            ]
        )

        backendAccessControl.productOnClient_create(
            productId=self.product1.id,
            productType=self.product1.getType(),
            clientId=self.client1.id,
            installationStatus='installed'
        )

        self.assertRaises(
            Exception,
            backendAccessControl.productOnClient_create,
            productId=self.product1.id,
            productType=self.product1.getType(),
            clientId=self.client2.id,  # here is the difference
            installationStatus='installed'
        )


class ACLTestCase(unittest.TestCase, HostsMixin, ProductsOnClientsMixin):

    # TODO: implement this with various backends

    def test_get_access_full(self):
        with getSQLiteBackend() as backend:
            self.backend = ExtendedConfigDataBackend(backend)
            self.setUpHosts()
            self.createHostsOnBackend()

            backend = BackendAccessControl(
                backend=self.backend,
                username=self.configserver1.id,
                password=self.configserver1.opsiHostKey,
                acl=[
                        ['.*',
                            [
                                {'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
                        ]
                    ]
                ]
            )

            hosts = backend.host_getObjects()
            self.assertEqual(len(self.hosts), len(hosts),
                u"Expected %s hosts, but got '%s' from backend" % (len(self.hosts), len(hosts))
            )

            for host in hosts:
                for h in self.hosts:
                    if h.id != host.id:
                        continue
                    self.assertEqual(h.opsiHostKey, host.opsiHostKey,
                        u"Expected opsi host key %s, but got '%s' from backend" % (h.opsiHostKey, host.opsiHostKey)
                    )

    def testOnlyAccessingSelfIsPossible(self):
        with getSQLiteBackend() as backend:
            self.backend = ExtendedConfigDataBackend(backend)
            self.setUpHosts()
            self.createHostsOnBackend()

            backend = BackendAccessControl(
                backend=self.backend,
                username=self.configserver1.id,
                password=self.configserver1.opsiHostKey,
                acl=[
                        ['.*',
                            [
                                {'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
                        ]
                    ]
                ]
            )

            hosts = backend.host_getObjects()
            self.assertEqual(1, len(hosts),
                u"Expected %s hosts, but found '%s' on backend" % (1, len(hosts))
            )

    def testDenyingAccessToSpecifiedAttributes(self):
        with getSQLiteBackend() as backend:
            self.backend = ExtendedConfigDataBackend(backend)
            self.setUpHosts()
            self.createHostsOnBackend()

            denyAttributes = set(['opsiHostKey', 'description'])
            backend = BackendAccessControl(
                backend=self.backend,
                username=self.configserver1.id,
                password=self.configserver1.opsiHostKey,
                acl=[
                        ['.*',
                            [
                                {'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': denyAttributes, 'allowAttributes': []}
                        ]
                    ]
                ]
            )

            hosts = backend.host_getObjects()
            self.assertEqual(len(self.hosts), len(hosts),
                u"Expected %s hosts, but got '%s' from backend" % (len(self.hosts), len(hosts))
            )

            for host in hosts:
                for attribute, value in host.toHash().items():
                    if attribute in denyAttributes:
                        self.assertEqual(value, None,
                            u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value)
                        )

    def test_get_access_allow_attributes(self):
        with getSQLiteBackend() as backend:
            self.backend = ExtendedConfigDataBackend(backend)
            self.setUpHosts()
            self.createHostsOnBackend()

            allowAttributes = set(['type', 'id', 'description', 'notes'])
            backend = BackendAccessControl(
                backend=self.backend,
                username=self.configserver1.id,
                password=self.configserver1.opsiHostKey,
                acl=[
                        ['.*',
                            [
                                {'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': [], 'allowAttributes': allowAttributes}
                        ]
                    ]
                ]
            )

            hosts = backend.host_getObjects()
            self.assertEqual(len(self.hosts), len(hosts),
                u"Expected %s hosts, but got '%s' from backend" % (len(self.hosts), len(hosts))
            )

            for host in hosts:
                for attribute, value in host.toHash().items():
                    if attribute not in allowAttributes:
                        self.assertEqual(value, None,
                            u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value)
                        )

    def test_get_access_deny_attributes_and_self(self):
        with getSQLiteBackend() as backend:
            self.backend = ExtendedConfigDataBackend(backend)
            self.setUpHosts()
            self.createHostsOnBackend()

            denyAttributes = set(['opsiHostKey', 'description'])
            backend = BackendAccessControl(
                backend=self.backend,
                username=self.configserver1.id,
                password=self.configserver1.opsiHostKey,
                acl=[
                        ['.*',
                            [
                                {'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': denyAttributes, 'allowAttributes': []},
                                {'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
                        ]
                    ]
                ]
            )

            hosts = backend.host_getObjects()
            self.assertEqual(len(self.hosts), len(hosts),
                u"Expected %s hosts, but got '%s' from backend" % (len(self.hosts), len(hosts))
            )

            for host in hosts:
                if host.id == self.configserver1.id:
                    self.assertEqual(self.configserver1.opsiHostKey, host.opsiHostKey,
                        u"Expected opsi host key %s, but got '%s' from backend" % (self.configserver1.opsiHostKey, host.opsiHostKey)
                    )
                else:
                    for attribute, value in host.toHash().items():
                        if attribute in denyAttributes:
                            self.assertEqual(value, None,
                                u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value)
                            )

# @requiresModulesFile  # Until this is implemented without SQL
# TODO: fix the usage of requiresModulesFile!
def testAccessingSelfProductOnClients(extendedConfigDataBackend):
    dataBackend = extendedConfigDataBackend

    configServer, depotServer, clients = fillBackendWithHosts(dataBackend)
    products = fillBackendWithProducts(dataBackend)
    productOnClients = fillBackendWithProductOnClients(dataBackend, products, clients)

    for client in clients:
        if client.id == productOnClients[0].clientId:
            break
    else:
        raise RuntimeError("Missing client!")

    backend = BackendAccessControl(
        backend=dataBackend,
        username=client.id,
        password=client.opsiHostKey,
        acl=[
                ['.*',
                    [
                        {'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
                ]
            ]
        ]
    )

    productOnClients = backend.productOnClient_getObjects()
    for productOnClient in productOnClients:
        assert client.id == productOnClient.clientId, u"Expected client id %s in productOnClient, but got client id '%s'" % (client.id, productOnClient.clientId)

    for c in clients:
        if client.id != c.id:
            otherClientId = c.id
            break
    else:
        raise RuntimeError("Failed to get different clientID.")

    productOnClient = productOnClients[0].clone()
    productOnClient.clientId = otherClientId

    with pytest.raises(Exception):
        backend.productOnClient_updateObjects(productOnClient)


if __name__ == '__main__':
    unittest.main()
