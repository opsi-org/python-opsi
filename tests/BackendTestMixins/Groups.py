#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Backend for testing group functionality of an backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Object import HostGroup, ProductGroup, ObjectToGroup


class GroupsMixin(object):
    def setUpGroups(self):
            self.group1 = HostGroup(
                id='host_group_1',
                description='Group 1',
                notes='First group',
                parentGroupId=None
            )

            # TODO: test?
            self.group2 = HostGroup(
                id=u'host group 2',
                description='Group 2',
                notes='Test\nTest\nTest',
                parentGroupId='host_group_1'
            )

            self.group3 = HostGroup(
                id=u'host group 3',
                description='Group 3',
                notes='',
                parentGroupId=None
            )
            self.group4 = ProductGroup(
                id=u'products group 4',
                description='Group 4',
                notes='',
                parentGroupId=None
            )
            self.groups = [self.group1, self.group2, self.group3, self.group4]

    def createGroupsOnBackend(self):
        self.backend.group_createObjects(self.groups)


class GroupTestsMixin(GroupsMixin):
    def testGroupMethods(self):
        self.setUpGroups()
        self.createGroupsOnBackend()

        groups = self.backend.group_getObjects()
        assert len(groups) == len(
            self.groups), u"got: '%s', expected: '%s'" % (groups, self.groups)

        groups = self.backend.group_getObjects(
            description=self.groups[0].description)
        assert len(groups) == 1, u"got: '%s', expected: '%s'" % (groups, 1)
        assert groups[0].getId() == self.groups[
            0].id, u"got: '%s', expected: '%s'" % (groups[0].getId(), self.groups[0].id)

        self.group1.setDescription(u'new description')
        self.backend.group_updateObject(self.group1)

        groups = self.backend.group_getObjects(
            description=self.group1.description)
        assert len(groups) == 1, u"got: '%s', expected: '%s'" % (groups, 1)
        assert groups[0].getDescription() == 'new description', u"got: '%s', expected: '%s'" % (
            groups[0].getDescription(), 'new description')

        self.backend.group_deleteObjects(self.group1)
        groups = self.backend.group_getObjects()
        assert len(groups) == len(self.groups) - \
            1, u"got: '%s', expected: '%s'" % (
                groups, len(self.groups) - 1)

        self.backend.group_createObjects(self.group1)
        groups = self.backend.group_getObjects()
        assert len(groups) == len(
            self.groups), u"got: '%s', expected: '%s'" % (groups, len(self.groups))


class ObjectToGroupsMixin(GroupsMixin):
    def setUpObjectToGroups(self):
        self.setUpClients()
        self.setUpGroups()

        self.objectToGroup1 = ObjectToGroup(
            groupType=self.group1.getType(),
            groupId=self.group1.getId(),
            objectId=self.client1.getId()
        )

        self.objectToGroup2 = ObjectToGroup(
            groupType=self.group1.getType(),
            groupId=self.group1.getId(),
            objectId=self.client2.getId()
        )

        self.objectToGroup3 = ObjectToGroup(
            groupType=self.group2.getType(),
            groupId=self.group2.getId(),
            objectId=self.client2.getId()
        )
        self.objectToGroups = [
            self.objectToGroup1, self.objectToGroup2, self.objectToGroup3
        ]


class ObjectToGroupTestsMixin(ObjectToGroupsMixin):
        def testObjectToGroupMethods(self):
            self.setUpObjectToGroups()
            self.createHostsOnBackend()
            self.createGroupsOnBackend()

            self.backend.objectToGroup_createObjects(self.objectToGroups)

            objectToGroups = self.backend.objectToGroup_getObjects()
            assert len(objectToGroups) == len(self.objectToGroups)

            client1ObjectToGroups = []
            client2ObjectToGroups = []
            for objectToGroup in self.objectToGroups:
                if (objectToGroup.objectId == self.client1.getId()):
                    client1ObjectToGroups.append(objectToGroup)
                if (objectToGroup.objectId == self.client2.getId()):
                    client2ObjectToGroups.append(objectToGroup)
            objectToGroups = self.backend.objectToGroup_getObjects(
                objectId=self.client1.getId())
            assert len(objectToGroups) == len(client1ObjectToGroups), u"got: '%s', expected: '%s'" % (
                objectToGroups, client1ObjectToGroups)
            for objectToGroup in objectToGroups:
                assert objectToGroup.objectId == self.client1.id, u"got: '%s', expected: '%s'" % (
                    objectToGroup.objectId, self.client1.id)

            objectToGroups = self.backend.objectToGroup_getObjects(
                objectId=self.client2.getId())
            assert len(objectToGroups) == len(client2ObjectToGroups), u"got: '%s', expected: '%s'" % (
                objectToGroups, client2ObjectToGroups)
            for objectToGroup in objectToGroups:
                assert objectToGroup.objectId == self.client2.id, u"got: '%s', expected: '%s'" % (
                    objectToGroup.objectId, self.client2.id)

            objectToGroup3update = ObjectToGroup(
                groupType=self.group2.getType(),
                groupId=self.group2.getId(),
                objectId=self.client2.getId()
            )
            self.backend.objectToGroup_updateObject(objectToGroup3update)
    #
            # cannot be updated ...
    #       groups = self.backend.group_getObjects(description = self.group1.description)
    #       assert len(groups) == 1
    #       assert groups[0].getDescription() == 'new description'

            self.backend.objectToGroup_deleteObjects(objectToGroup3update)
            objectToGroups = self.backend.objectToGroup_getObjects()
            assert len(objectToGroups) == len(self.objectToGroups) - \
                1, u"got: '%s', expected: '%s'" % (
                    objectToGroups, len(self.objectToGroups) - 1)

            self.backend.objectToGroup_createObjects(objectToGroup3update)
            objectToGroups = self.backend.objectToGroup_getObjects()
            assert len(objectToGroups) == len(self.objectToGroups), u"got: '%s', expected: '%s'" % (
                objectToGroups, self.objectToGroups)
