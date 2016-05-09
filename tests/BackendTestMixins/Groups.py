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
Backend for testing group functionality of an backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from OPSI.Object import HostGroup, ProductGroup, ObjectToGroup

from .Clients import getClients


def getGroups():
    return list(getHostGroups()) + [getProductGroup()]


def getHostGroups():
    group1 = HostGroup(
        id='host_group_1',
        description='Group 1',
        notes='First group',
        parentGroupId=None
    )

    group2 = HostGroup(
        id=u'host group 2',
        description='Group 2',
        notes='Test\nTest\nTest',
        parentGroupId=group1.id
    )

    group3 = HostGroup(
        id=u'host group 3',
        description='Group 3',
        notes='',
        parentGroupId=None
    )

    return group1, group2, group3


def getProductGroup():
    return ProductGroup(
        id=u'products group 4',
        description='Group 4',
        notes='',
        parentGroupId=None
    )


def getObjectToGroups(groups, clients):
    group1, group2 = groups[:2]
    client1, client2 = clients[:2]

    objectToGroup1 = ObjectToGroup(
        groupType=group1.getType(),
        groupId=group1.getId(),
        objectId=client1.getId()
    )

    objectToGroup2 = ObjectToGroup(
        groupType=group1.getType(),
        groupId=group1.getId(),
        objectId=client2.getId()
    )

    objectToGroup3 = ObjectToGroup(
        groupType=group2.getType(),
        groupId=group2.getId(),
        objectId=client2.getId()
    )

    return objectToGroup1, objectToGroup2, objectToGroup3


class GroupsMixin(object):
    def setUpGroups(self):
        self.group1, self.group2, self.group3 = getHostGroups()
        self.group4 = getProductGroup()

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

    def test_selectGroupByDescrition(self):
        groupsIn = getGroups()
        self.backend.group_createObjects(groupsIn)

        group1 = groupsIn[0]

        groups = self.backend.group_getObjects(description=group1.description)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].getId(), group1.id)

    def test_updateGroup(self):
        groupsIn = getGroups()
        self.backend.group_createObjects(groupsIn)

        group1 = groupsIn[0]
        group1.setDescription(u'new description')
        self.backend.group_updateObject(group1)

        groups = self.backend.group_getObjects(description=group1.description)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].getDescription(), u'new description')

    def test_deleteGroup(self):
        groupsIn = getGroups()
        self.backend.group_createObjects(groupsIn)

        group1 = groupsIn[0]
        self.backend.group_deleteObjects(group1)
        groups = self.backend.group_getObjects()
        self.assertEqual(len(groups), len(groupsIn) - 1)

    def test_createGroup(self):
        groupsIn = getGroups()
        self.backend.group_createObjects(groupsIn)

        groupsOut = self.backend.group_getObjects()
        self.assertEqual(len(groupsOut), len(groupsIn))
        # TODO: check contents

    def test_createDuplicateGroup(self):
        groups = getGroups()
        self.backend.group_createObjects(groups)

        group1 = groups[0]
        self.backend.group_createObjects(group1)
        groupsFromBackend = self.backend.group_getObjects()
        self.assertEqual(len(groupsFromBackend), len(groups))


class ObjectToGroupsMixin(GroupsMixin):
    def setUpObjectToGroups(self):
        self.setUpClients()
        self.setUpGroups()

        self.objectToGroup1, self.objectToGroup2, self.objectToGroup3 = getObjectToGroups(self.groups, self.clients)

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

        # TODO: cannot be updated ...?
        # groups = self.backend.group_getObjects(description=self.group1.description)
        # assert len(groups) == 1
        # assert groups[0].getDescription() == 'new description'

        self.backend.objectToGroup_deleteObjects(objectToGroup3update)
        objectToGroups = self.backend.objectToGroup_getObjects()
        assert len(objectToGroups) == len(self.objectToGroups) - \
            1, u"got: '%s', expected: '%s'" % (
                objectToGroups, len(self.objectToGroups) - 1)

        self.backend.objectToGroup_createObjects(objectToGroup3update)
        objectToGroups = self.backend.objectToGroup_getObjects()
        assert len(objectToGroups) == len(self.objectToGroups), u"got: '%s', expected: '%s'" % (
            objectToGroups, self.objectToGroups)

    def test_getObjectsToGroupFromBackend(self):
        clients = getClients()
        groups = getHostGroups()
        o2g = getObjectToGroups(groups, clients)
        self.backend.host_createObjects(clients)
        self.backend.group_createObjects(groups)
        self.backend.objectToGroup_createObjects(o2g)

        objectToGroups = self.backend.objectToGroup_getObjects()
        self.assertEqual(len(objectToGroups), len(o2g))
        # TODO: check contents

    def test_selectObjectToGroupById(self):
        clients = getClients()
        groups = getHostGroups()
        o2g = getObjectToGroups(groups, clients)
        client1 = clients[0]
        client2 = clients[1]

        client1ObjectToGroups = [objectToGroup for objectToGroup in o2g if objectToGroup.objectId == client1.id]
        client2ObjectToGroups = [objectToGroup for objectToGroup in o2g if objectToGroup.objectId == client2.id]

        self.backend.host_createObjects(clients)
        self.backend.group_createObjects(groups)
        self.backend.objectToGroup_createObjects(o2g)
        objectToGroups = self.backend.objectToGroup_getObjects(objectId=client1.getId())
        self.assertEqual(len(objectToGroups), len(client1ObjectToGroups))
        for objectToGroup in objectToGroups:
            self.assertEqual(objectToGroup.objectId, client1.id)

        objectToGroups = self.backend.objectToGroup_getObjects(objectId=client2.getId())
        self.assertEqual(len(objectToGroups), len(client2ObjectToGroups))
        for objectToGroup in objectToGroups:
            self.assertEqual(objectToGroup.objectId, client2.id)

    def test_deleteObjectToGroup(self):
        clients = getClients()
        groups = getHostGroups()
        o2g = getObjectToGroups(groups, clients)
        self.backend.host_createObjects(clients)
        self.backend.group_createObjects(groups)
        self.backend.objectToGroup_createObjects(o2g)

        objectToGroup3 = o2g[2]
        self.backend.objectToGroup_deleteObjects(objectToGroup3)
        objectToGroups = self.backend.objectToGroup_getObjects()
        self.assertEqual(len(objectToGroups), len(o2g) - 1)

    def test_createDuplicateObjectToGroup(self):
        clients = getClients()
        groups = getHostGroups()
        o2g = getObjectToGroups(groups, clients)
        self.backend.host_createObjects(clients)
        self.backend.group_createObjects(groups)
        self.backend.objectToGroup_createObjects(o2g)

        objectToGroup3 = o2g[2]
        self.backend.objectToGroup_createObjects(objectToGroup3)
        objectToGroups = self.backend.objectToGroup_getObjects()
        self.assertEqual(len(objectToGroups), len(o2g))
