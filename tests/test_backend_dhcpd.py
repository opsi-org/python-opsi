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
Testing DHCPD Backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import unittest

from OPSI.Backend.DHCPD import DHCPDBackend
from OPSI.Object import OpsiClient
from OPSI.Types import BackendIOError

from .Backends.DHCPD import DHCPDConfMixin


class DHCPBackendTestCase(unittest.TestCase, DHCPDConfMixin):
    def setUp(self):
        self.setUpDHCPDConf()

        self.backend = DHCPDBackend(
            dhcpdConfigFile=self.dhcpdConfFile,
            reloadConfigCommand=u'/bin/echo "Reloading dhcpd.conf"'
        )

    def tearDown(self):
        del self.backend

        self.tearDownDHCPDConf()

    def testAddingHostsToBackend(self):
        self.backend.host_insertObject(
            OpsiClient(
                id='client1.test.invalid',
                hardwareAddress='00:01:02:03:04:05',
                ipAddress='192.168.1.101',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client2.test.invalid',
                hardwareAddress='00:01:02:03:11:22',
                ipAddress='192.168.1.102',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client3.test.invalid',
                hardwareAddress='1101:02:03-83:22',
                ipAddress='192.168.1.103',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client4.test.invalid',
                hardwareAddress='00:99:88:77:77:11',
                ipAddress='192.168.1.104',
            )
        )

    def testUpdatingHostWhereAddressCantBeResolvedFails(self):
        client = OpsiClient(
            id='unknown-client.test.invalid',
            hardwareAddress='00:99:88:77:77:21'
        )

        self.assertRaises(BackendIOError, self.backend.host_insertObject, client)

    def testUpdatingHostTriggersChangeInDHCPDConfiguration(self):
        """
        Updating hosts should trigger an update in the DHCP config.

        Currently there are the two cases that the updated objects
        differ in the fact that one brings it's ip with it and the other
        does not.

        If the IP is not found the backend will try to get it from DNS.
        If this fails it should get the information from the DHCP
        config file.
        """
        def isMacAddressInConfigFile(mac):
            return isElementInConfigFile(mac, caseInSensitive=True)

        def isElementInConfigFile(elem, caseInSensitive=False):
            if caseInSensitive:
                elem = elem.lower()

            with open(self.dhcpdConfFile) as config:
                for line in config:
                    if caseInSensitive:
                        line = line.lower()

                    if elem in line:
                        return True

            return False

        configs = (
            ('client4hostFile', '00:99:88:77:77:11', '00:99:88:77:77:12', {'ipAddress': '192.168.99.104'}),
            ('client4hostFile', '00:99:88:77:77:21', '00:99:88:77:77:22', {})
        )

        showMissingInfo = lambda x: "Expected {term} to be in DHCPD config {file}".format(
            term=x,
            file=self.dhcpdConfFile
        )

        for (hostname, oldMAC, newMAC, additionalClientConfig) in configs:
            clientConfig = {
                'id': '{0}.some.network'.format(hostname),
                'hardwareAddress': oldMAC,
            }
            clientConfig.update(additionalClientConfig)

            client = OpsiClient(**clientConfig)
            self.backend.host_insertObject(client)

            self.assertTrue(
                isElementInConfigFile(hostname.lower()),
                showMissingInfo(client.id)
            )
            self.assertTrue(
                isMacAddressInConfigFile(oldMAC),
                showMissingInfo(oldMAC)
            )


            client.hardwareAddress = newMAC
            self.backend.host_updateObject(client)

            self.assertTrue(
                isMacAddressInConfigFile(newMAC),
                showMissingInfo(newMAC)
            )
            self.assertFalse(isMacAddressInConfigFile(oldMAC))


if __name__ == '__main__':
    unittest.main()
