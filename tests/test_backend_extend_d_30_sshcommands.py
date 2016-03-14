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
from .Backends.File import FileBackendBackendManagerMixin
import unittest


class SSHCommandsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
    """
    Testing the crud methods for json commands .
    """
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testCreateCommand(self):
        name=u'testname'
        menuText=u'Test Menu'
        commands=[u'test1', u'test2']
        needSudo=True
        priority=1
        # tooltip=
        parentMenu=None
        self.backend.createCommand(name, menuText, commands, needSudo, priority )
        # command={u'name':name}
        command={u'name':name,
            u'menuText':menuText,
            u'tooltip':u'""',
            u'commands':commands,
            u'needSudo':needSudo,
            u'priority':priority,
            u'parentMenu':parentMenu
            }
        # self.assertEquals(self.backend.readCommands() , command)
        self.assertNotEquals(self.backend.readCommands() , {u'name':u'bla'})

    # def testCreateCommand(self):
        # self.assertTrueS(self.backend.createCommand("name1"))
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
