#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
Tests for the dynamically loaded group actions extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/40_groupActions.conf``.

.. versionadded:: 4.0.5.4

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import random
import unittest

from OPSI.Object import HostGroup, OpsiClient, LocalbootProduct, ObjectToGroup, ProductOnDepot, OpsiDepotserver
from .Backends.File import ExtendedFileBackendMixin


class GroupActionsTestCase(unittest.TestCase, ExtendedFileBackendMixin):
    """
    Testing the group actions.
    """
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testSetProductActionRequestForHostGroup(self):
        testGroup = HostGroup(
            id='host_group_1',
            description='Group 1',
            notes='First group',
            parentGroupId=None
        )

        client1 = OpsiClient(
            id='client1.uib.local',
        )

        client2 = OpsiClient(
            id='client2.uib.local',
        )

        product2 = LocalbootProduct(
            id='product2',
            name=u'Product 2',
            productVersion='2.0',
            packageVersion='test',
            setupScript="setup.ins",
        )

        client1ToGroup = ObjectToGroup(testGroup.getType(), testGroup.id, client1.id)
        client2ToGroup = ObjectToGroup(testGroup.getType(), testGroup.id, client2.id)

        depot = OpsiDepotserver(
            id='depotserver1.uib.local',
            opsiHostKey='19012334567845645678901232789012',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depotserver1.uib.local/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl='webdavs://depotserver1.uib.local:4447/repository',
            description='A depot',
            notes='D€pot 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000002',
            networkAddress='192.168.2.0/24',
            maxBandwidth=10000
        )

        prodOnDepot = ProductOnDepot(
            productId=product2.getId(),
            productType=product2.getType(),
            productVersion=product2.getProductVersion(),
            packageVersion=product2.getPackageVersion(),
            depotId=depot.getId(),
            locked=False
        )


        self.backend.host_insertObject(client1)
        self.backend.host_insertObject(client2)
        self.backend.host_insertObject(depot)
        self.backend.group_insertObject(testGroup)
        self.backend.objectToGroup_createObjects([client1ToGroup, client2ToGroup])
        self.backend.config_create(u'clientconfig.depot.id')
        self.backend.configState_create(u'clientconfig.depot.id', client1.getId(), values=[depot.getId()])
        self.backend.configState_create(u'clientconfig.depot.id', client2.getId(), values=[depot.getId()])
        self.backend.product_insertObject(product2)
        self.backend.productOnDepot_insertObject(prodOnDepot)

        self.assertFalse(self.backend.productOnClient_getObjects())
        self.assertTrue(self.backend.objectToGroup_getObjects(groupType="HostGroup"))

        self.backend.setProductActionRequestForHostGroup('host_group_1', 'product2', 'setup')

        print(self.backend.productOnClient_getObjects())
        self.assertTrue(self.backend.productOnClient_getObjects())

        self.assertEquals(2, len(self.backend.productOnClient_getObjects()))

        for poc in self.backend.productOnClient_getObjects():
            self.assertEquals(poc.productId, product2.getId())
            self.assertTrue(poc.clientId in (client1.id, client2.id))


if __name__ == '__main__':
    unittest.main()
