#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

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
Tests for easy configuration of WAN clients.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/70_wan.conf``.

.. versionadded:: 4.0.6.3

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import unittest

from OPSI.Object import OpsiClient
from OPSI.Util.Task.ConfigureBackend.ConfigurationData import createWANconfigs

from .Backends.File import FileBackendBackendManagerMixin


class SimpleWanConfigTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
    """
    Testing the group actions.
    """
    def setUp(self):
        self.setUpBackend()
        createWANconfigs(self.backend)

    def tearDown(self):
        self.tearDownBackend()

    def testEnablingSettingForOneHost(self):
        clientId = 'testclient.test.invalid'
        self.backend.host_createObjects(OpsiClient(id=clientId))

        self.backend.changeWANConfig(True, clientId)
        self.assertTrue(self.clientHasWANEnabled(clientId))

        self.backend.changeWANConfig(False, clientId)
        self.assertFalse(self.clientHasWANEnabled(clientId))

    def clientHasWANEnabled(self, clientId):
        configsToCheck = set([
            "opsiclientd.event_gui_startup.active",
            "opsiclientd.event_gui_startup{user_logged_in}.active",
            "opsiclientd.event_net_connection.active",
            "opsiclientd.event_timer.active"
        ])

        for configState in self.backend.configState_getObjects(objectId=clientId):
            if configState.configId == u"opsiclientd.event_gui_startup.active":
                if configState.values[0]:
                    return False
                configsToCheck.remove(u"opsiclientd.event_gui_startup.active")
            elif configState.configId == u"opsiclientd.event_gui_startup{user_logged_in}.active":
                if configState.values[0]:
                    return False
                configsToCheck.remove(u"opsiclientd.event_gui_startup{user_logged_in}.active")
            elif configState.configId == u"opsiclientd.event_net_connection.active":
                if not configState.values[0]:
                    return False
                configsToCheck.remove(u"opsiclientd.event_net_connection.active")
            elif configState.configId == u"opsiclientd.event_timer.active":
                if not configState.values[0]:
                    return False
                configsToCheck.remove(u"opsiclientd.event_timer.active")

        if configsToCheck:
            print("The following configs were not set: {0}".format(configsToCheck))
            return False

        return True

    def testEnablingSettingForMultipleHosts(self):
        clientIds = ['testclient{0}.test.invalid'.format(num) for num in range(10)]
        self.backend.host_createObjects([OpsiClient(id=clientId) for clientId in clientIds])

        self.backend.changeWANConfig(True, clientIds)

        for clientId in clientIds:
            self.assertTrue(self.clientHasWANEnabled(clientId))

    def testNotProcessingEmptyList(self):
        self.backend.changeWANConfig(True, [])

    def testNotChangingUnreferencedClient(self):
        clientIds = ['testclient{0}.test.invalid'.format(num) for num in range(10)]
        singleClient = 'testclient99.test.invalid'
        self.backend.host_createObjects([OpsiClient(id=clientId) for clientId in clientIds])
        self.backend.host_createObjects([OpsiClient(id=singleClient)])

        self.backend.changeWANConfig(True, clientIds)
        self.backend.changeWANConfig(True, [])

        for clientId in clientIds:
            self.assertTrue(self.clientHasWANEnabled(clientId))

        self.assertFalse(self.clientHasWANEnabled(singleClient))

    def testUsingNonBooleanParameters(self):
        client = OpsiClient(id='testclient101.test.invalid')

        self.backend.host_createObjects([client])

        self.backend.changeWANConfig(False, client.id)
        for term in ("on", "1", "true"):
            self.backend.changeWANConfig(term, client.id)
            self.assertTrue(self.clientHasWANEnabled(client.id))
            self.backend.changeWANConfig(False, client.id)

        self.backend.changeWANConfig(True, client.id)
        for term in ("off", "false", "0"):
            self.backend.changeWANConfig(term, client.id)
            self.assertFalse(self.clientHasWANEnabled(client.id))
            self.backend.changeWANConfig(True, client.id)


if __name__ == '__main__':
    unittest.main()
