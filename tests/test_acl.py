#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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

import os
import shutil
import tempfile
import unittest

import OPSI.Types
import OPSI.Object
from OPSI.Util.File.Opsi import BackendACLFile
from OPSI.Backend.BackendManager import BackendAccessControl

from BackendTestMixins.Products import ProductsOnClientsMixin, ProductPropertyStatesMixin
from Backends.File import FileBackendMixin
from BackendTestMixins.Hosts import HostsMixin


class BackendACLFileTestCase(unittest.TestCase):
    def setUp(self):
        self._temp_config_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self._temp_config_dir):
            shutil.rmtree(self._temp_config_dir)

    def testParsingFile(self):
        aclFile = os.path.join(self._temp_config_dir, 'acl.conf')
        with open(aclFile, 'w') as exampleConfig:
            exampleConfig.write(
'''
host_.*: opsi_depotserver(depot1.uib.local, depot2.uib.local); opsi_client(self,  attributes (attr1, attr2)); sys_user(some user, some other user); sys_group(a_group, group2)
'''
        )

        expectedACL = [
            [u'host_.*', [
                {'denyAttributes': [], 'type': u'opsi_depotserver', 'ids': [u'depot1.uib.local', u'depot2.uib.local'], 'allowAttributes': []},
                {'denyAttributes': [], 'type': u'opsi_client', 'ids': [u'self'], 'allowAttributes': [u'attr1', u'attr2']},
                {'denyAttributes': [], 'type': u'sys_user', 'ids': [u'some user', u'some other user'], 'allowAttributes': []},
                {'denyAttributes': [], 'type': u'sys_group', 'ids': [u'a_group', u'group2'], 'allowAttributes': []}
                ]
            ]
        ]

        self.assertEquals(expectedACL, BackendACLFile(aclFile).parse())


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


if __name__ == '__main__':
    unittest.main()
