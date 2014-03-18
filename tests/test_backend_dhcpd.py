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
Testing DHCPD Backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Object import OpsiClient
from OPSI.Backend.DHCPD import DHCPDBackend

from Backends.DHCPD import DHCPDConfMixin


class DHCPDConfFileTestCase(unittest.TestCase, DHCPDConfMixin):
    def setUp(self):
        self.setUpDHCPDConf()

    def tearDown(self):
        self.tearDownDHCPDConf()

    def testAddingHostsToConfig(self):
        """
        Adding hosts to a DHCPDConf.

        If this fails on your machine with a message that 127.x.x.x is refused
        as network address please correct your hostname settings.
        """
        dhcpdConf = self.dhcpdConf
        dhcpdConf.parse()

        dhcpdConf.addHost('TestclienT', '0001-21-21:00:00', '192.168.99.112', '192.168.99.112', None)
        dhcpdConf.addHost('TestclienT2', '00:01:09:08:99:11', '192.168.99.113', '192.168.99.113', {"next-server": "192.168.99.2", "filename": "linux/pxelinux.0/xxx?{}"})

        self.assertNotEqual(None, dhcpdConf.getHost('TestclienT2'))
        self.assertEqual(None, dhcpdConf.getHost('notthere'))

    def testGeneratingConfig(self):
        dhcpdConf = self.dhcpdConf
        dhcpdConf.parse()

        dhcpdConf.addHost('TestclienT', '0001-21-21:00:00', '192.168.99.112', '192.168.99.112', None)
        dhcpdConf.addHost('TestclienT2', '00:01:09:08:99:11', '192.168.99.113', '192.168.99.113', {"next-server": "192.168.99.2", "filename": "linux/pxelinux.0/xxx?{}"})

        dhcpdConf.generate()


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
                id='client1.uib.local',
                hardwareAddress='00:01:02:03:04:05',
                ipAddress='192.168.1.101',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client2.uib.local',
                hardwareAddress='00:01:02:03:11:22',
                ipAddress='192.168.1.102',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client3.uib.local',
                hardwareAddress='1101:02:03-83:22',
                ipAddress='192.168.1.103',
            )
        )
        self.backend.host_insertObject(
            OpsiClient(
                id='client4.uib.local',
                hardwareAddress='00:99:88:77:77:11',
                ipAddress='192.168.1.104',
            )
        )
