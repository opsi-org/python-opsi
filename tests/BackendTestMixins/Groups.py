#!/usr/bin/env python
#-*- coding: utf-8 -*-

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


class GroupTestsMixin(GroupsMixin):
    def testGroupMethods(self):
        self.setUpObjectToGroups()

        self.backend.group_createObjects(self.groups)

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
