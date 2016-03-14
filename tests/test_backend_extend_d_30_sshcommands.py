#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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
Testing CRUD Methods for sshcommands (read from / write to jsonfile).

:author: Anna Sucher <a.sucher@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import unittest


# from OPSI.Backend.DHCPD import DHCPDBackend
# from OPSI.Object import OpsiClient
# from OPSI.Types import BackendIOError
from .Backends.File import FileBackendBackendManagerMixin
import JSON
class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
    """
    Testing the group actions.
    """
    def setUp(self):
        self.setUpBackend()
        # self.testGroup = HostGroup(
        #     id='host_group_1',
        #     description='Group 1',
        #     notes='First group',
        #     parentGroupId=None
        # )
        # self.testGroup2 = HostGroup(
        #     id='new_group_1',
        #     description='Group 1',
        #     notes='First group',
        #     parentGroupId=None
        # )

        # self.client1 = OpsiClient(
        #     id='client1.test.invalid',
        # )

        # self.client2 = OpsiClient(
        #     id='client2.test.invalid',
        # )

        # client1ToGroup = ObjectToGroup(self.testGroup.getType(),self.testGroup.id, self.client1.id)
        # client2ToGroup = ObjectToGroup(self.testGroup.getType(),self.testGroup.id, self.client2.id)

        # self.backend.host_insertObject(self.client1)
        # self.backend.host_insertObject(self.client2)
        # self.backend.group_insertObject(self.testGroup)
        # self.backend.objectToGroup_createObjects([client1ToGroup, client2ToGroup])

    def tearDown(self):
        self.tearDownBackend()

    # def testGroupnameExists(self):
    #     self.assertTrue(self.backend.groupname_exists(self.testGroup.id))
    #     self.assertFalse(self.backend.groupname_exists(u'testgruppe'))

    # def testAlreadyExistingGroup(self):
    #     self.assertRaises(Exception, self.backend.group_rename, self.testGroup.id, self.testGroup.id)
    #     self.assertRaises(Exception, self.backend.group_rename, u'notExisting', self.testGroup.id)

    # def testCreateNewDeleteOldGroup(self):
    #     self.backend.group_rename(self.testGroup.id, self.testGroup2.id)

    #     group = self.backend.group_getObjects(id=self.testGroup2.id) [0]
    #     self.assertEquals(group.description, self.testGroup.description)
    #     self.assertEquals(group.notes, self.testGroup.notes)
    #     self.assertEquals(group.parentGroupId, self.testGroup.parentGroupId)

    #     self.assertFalse(self.backend.groupname_exists(self.testGroup.id))

    # def testObjectToGroupsHaveNewGroupIds(self):
    #     self.backend.group_rename(self.testGroup.id, self.testGroup2.id)

    #     objTpGrp_client1 = self.backend.objectToGroup_getObjects(objectId=self.client1.id) [0]
    #     self.assertTrue(objTpGrp_client1.groupId, self.testGroup2.id )

    #     objTpGrp_client2 = self.backend.objectToGroup_getObjects(objectId=self.client2.id) [0]
    #     self.assertTrue(objTpGrp_client2.groupId, self.testGroup2.id )

    # def testObjectToGroupsHaveNotOldGroupIds(self):
    #     self.backend.group_rename(self.testGroup.id, self.testGroup2.id)

    #     objsToGrp = self.backend.objectToGroup_getObjects()
    #     for obj in objsToGrp:
    #         self.assertNotEqual(obj.groupId, self.testGroup.id)


if __name__ == '__main__':
    unittest.main()
