# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2017 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded group actions extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/40_groupActions.conf``.

.. versionadded:: 4.0.5.4

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import pytest

from OPSI.Object import (HostGroup, LocalbootProduct, ProductOnDepot,
    ObjectToGroup, OpsiClient, OpsiDepotserver)
from OPSI.Types import BackendMissingDataError


def testSetProductActionRequestForHostGroup(backendManager):
    testGroup = HostGroup(id='host_group_1')

    client1 = OpsiClient(id='client1.test.invalid')
    client2 = OpsiClient(id='client2.test.invalid')

    client1ToGroup = ObjectToGroup(testGroup.getType(), testGroup.id, client1.id)
    client2ToGroup = ObjectToGroup(testGroup.getType(), testGroup.id, client2.id)

    depot = OpsiDepotserver(id='depotserver1.test.invalid')

    product2 = LocalbootProduct(
        id='product2',
        name=u'Product 2',
        productVersion='2.0',
        packageVersion='test',
        setupScript="setup.ins",
    )

    prodOnDepot = ProductOnDepot(
        productId=product2.getId(),
        productType=product2.getType(),
        productVersion=product2.getProductVersion(),
        packageVersion=product2.getPackageVersion(),
        depotId=depot.getId()
    )

    backendManager.host_insertObject(client1)
    backendManager.host_insertObject(client2)
    backendManager.host_insertObject(depot)
    backendManager.group_insertObject(testGroup)
    backendManager.objectToGroup_createObjects([client1ToGroup, client2ToGroup])
    backendManager.config_create(u'clientconfig.depot.id')
    backendManager.configState_create(u'clientconfig.depot.id', client1.getId(), values=[depot.getId()])
    backendManager.configState_create(u'clientconfig.depot.id', client2.getId(), values=[depot.getId()])
    backendManager.product_insertObject(product2)
    backendManager.productOnDepot_insertObject(prodOnDepot)

    backendManager.setProductActionRequestForHostGroup('host_group_1', 'product2', 'setup')

    pocs = backendManager.productOnClient_getObjects()
    assert pocs
    assert len(pocs) == 2

    for poc in backendManager.productOnClient_getObjects():
        assert poc.productId == product2.getId()
        assert poc.clientId in (client1.id, client2.id)


def testGroupnameExists(backendManager):
    testGroup, _ = fillBackendForRenaming(backendManager)

    assert backendManager.groupname_exists(testGroup.id)
    assert not backendManager.groupname_exists(u'testgruppe')


def testRenamingGroupToAlreadyExistingGroupFails(backendManager):
    testGroup, _ = fillBackendForRenaming(backendManager)

    newGroup = HostGroup(
        id='new_group_1',
        description='Group 1',
        notes='First group',
        parentGroupId=None
    )
    backendManager.group_insertObject(newGroup)

    with pytest.raises(Exception):
        backendManager.group_rename(testGroup.id, newGroup.id)


def testRenamingNonexistingGroupFails(backendManager):
    with pytest.raises(BackendMissingDataError):
        backendManager.group_rename(u'notExisting', 'newGroupId')


def testRenamingKeepsSettingsOfOldGroup(backendManager):
    """
    After a rename non-key attributes of the new object must be the same.
    """
    testGroup, _ = fillBackendForRenaming(backendManager)
    newGroupId = 'new_group_1'

    backendManager.group_rename(testGroup.id, newGroupId)

    group = backendManager.group_getObjects(id=newGroupId)[0]
    assert group.id == 'new_group_1'
    assert group.description == testGroup.description
    assert group.notes == testGroup.notes
    assert group.parentGroupId == testGroup.parentGroupId

    assert not backendManager.groupname_exists(testGroup.id)


def testGroupRenameUpdatesObjectToGroups(backendManager):
    testGroup, clients = fillBackendForRenaming(backendManager)
    client1, client2 = clients[:2]
    newGroupId = 'new_group_1'

    backendManager.group_rename(testGroup.id, newGroupId)

    objTpGrp_client1 = backendManager.objectToGroup_getObjects(objectId=client1.id)[0]
    assert objTpGrp_client1.groupId == newGroupId

    objTpGrp_client2 = backendManager.objectToGroup_getObjects(objectId=client2.id)[0]
    assert objTpGrp_client2.groupId == newGroupId

    objsToGrp = backendManager.objectToGroup_getObjects()
    # Removal of old group ID
    assert not any(obj.groupId == testGroup.id for obj in objsToGrp)
    # Existance of new group ID
    assert any(obj.groupId == newGroupId for obj in objsToGrp)


def fillBackendForRenaming(backend):
    group = HostGroup(
        id='host_group_1',
        description='Group 1',
        notes='First group',
        parentGroupId=None
    )

    client1 = OpsiClient(id='client1.test.invalid')
    client2 = OpsiClient(id='client2.test.invalid')

    client1ToGroup = ObjectToGroup(group.getType(), group.id, client1.id)
    client2ToGroup = ObjectToGroup(group.getType(), group.id, client2.id)

    backend.host_insertObject(client1)
    backend.host_insertObject(client2)
    backend.group_insertObject(group)
    backend.objectToGroup_createObjects([client1ToGroup, client2ToGroup])

    return (
        group,
        (client1, client2)
    )
