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

from OPSI.Backend.DHCPD import DHCPDBackend
from OPSI.Object import OpsiClient
from OPSI.Types import BackendIOError

from .test_util_file_dhcpdconf import dhcpdConf

import pytest


@pytest.fixture
def dhcpdBackend(dhcpdConf):
    yield DHCPDBackend(
        dhcpdConfigFile=dhcpdConf._filename,
        reloadConfigCommand=u'/bin/echo "Reloading dhcpd.conf"'
    )


def testAddingHostsToBackend(dhcpdBackend):
    dhcpdBackend.host_insertObject(
        OpsiClient(
            id='client1.test.invalid',
            hardwareAddress='00:01:02:03:04:05',
            ipAddress='192.168.1.101',
        )
    )
    dhcpdBackend.host_insertObject(
        OpsiClient(
            id='client2.test.invalid',
            hardwareAddress='00:01:02:03:11:22',
            ipAddress='192.168.1.102',
        )
    )
    dhcpdBackend.host_insertObject(
        OpsiClient(
            id='client3.test.invalid',
            hardwareAddress='1101:02:03-83:22',
            ipAddress='192.168.1.103',
        )
    )
    dhcpdBackend.host_insertObject(
        OpsiClient(
            id='client4.test.invalid',
            hardwareAddress='00:99:88:77:77:11',
            ipAddress='192.168.1.104',
        )
    )


def testUpdatingHostWhereAddressCantBeResolvedFails(dhcpdBackend):
    client = OpsiClient(
        id='unknown-client.test.invalid',
        hardwareAddress='00:99:88:77:77:21'
    )

    with pytest.raises(BackendIOError):
        dhcpdBackend.host_insertObject(client)


def testUpdatingHostTriggersChangeInDHCPDConfiguration(dhcpdBackend):
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

        with open(dhcpdBackend._dhcpdConfFile._filename) as config:
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
        file=dhcpdBackend._dhcpdConfFile._filename
    )

    for (hostname, oldMAC, newMAC, additionalClientConfig) in configs:
        clientConfig = {
            'id': '{0}.some.network'.format(hostname),
            'hardwareAddress': oldMAC,
        }
        clientConfig.update(additionalClientConfig)

        client = OpsiClient(**clientConfig)
        dhcpdBackend.host_insertObject(client)

        assert isElementInConfigFile(hostname.lower()), showMissingInfo(client.id)
        assert isMacAddressInConfigFile(oldMAC), showMissingInfo(oldMAC)

        client.hardwareAddress = newMAC
        dhcpdBackend.host_updateObject(client)

        assert isMacAddressInConfigFile(newMAC), showMissingInfo(newMAC)
        assert not isMacAddressInConfigFile(oldMAC)
