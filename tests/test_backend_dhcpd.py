# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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

from collections import namedtuple

import pytest

from OPSI.Backend.DHCPD import DHCPDBackend
from OPSI.Object import OpsiClient
from OPSI.Types import BackendIOError

from .helpers import mock
from .test_util_file_dhcpdconf import dhcpdConf  # test fixture


ClientConfig = namedtuple("ClientConfig", "hostname oldMAC newMAC additionalConfig")


def testAddingHostsToBackend(dhcpBackendWithoutLookup):
    dhcpBackendWithoutLookup.host_insertObject(
        OpsiClient(
            id='client1.test.invalid',
            hardwareAddress='00:01:02:03:04:05',
            ipAddress='192.168.1.101',
        )
    )
    dhcpBackendWithoutLookup.host_insertObject(
        OpsiClient(
            id='client2.test.invalid',
            hardwareAddress='00:01:02:03:11:22',
            ipAddress='192.168.1.102',
        )
    )
    dhcpBackendWithoutLookup.host_insertObject(
        OpsiClient(
            id='client3.test.invalid',
            hardwareAddress='1101:02:03-83:22',
            ipAddress='192.168.1.103',
        )
    )
    dhcpBackendWithoutLookup.host_insertObject(
        OpsiClient(
            id='client4.test.invalid',
            hardwareAddress='00:99:88:77:77:11',
            ipAddress='192.168.1.104',
        )
    )


def testUpdatingHostWhereAddressCantBeResolvedFails(dhcpBackendWithoutLookup):
    client = OpsiClient(
        id='unknown-client.test.invalid',
        hardwareAddress='00:99:88:77:77:21'
    )

    with pytest.raises(BackendIOError):
        dhcpBackendWithoutLookup.host_insertObject(client)


@pytest.fixture
def dhcpBackendWithoutLookup(dhcpdBackend):
    def failingLookup(_):
        raise Exception("Lookup disabled")

    with mock.patch('socket.gethostbyname', failingLookup):
        yield dhcpdBackend


@pytest.fixture
def dhcpdBackend(dhcpdConf):
    yield DHCPDBackend(
        dhcpdConfigFile=dhcpdConf._filename,
        reloadConfigCommand=u'/bin/echo "Reloading dhcpd.conf"'
    )


def testUpdatingHostTriggersChangeInDHCPDConfiguration(dhcpBackendWithoutLookup):
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

        if caseInSensitive:
            lineConversion = lambda line: line.lower()
        else:
            lineConversion = lambda line: line

        with open(backend._dhcpdConfFile._filename) as config:
            return any(elem in lineConversion(line) for line in config)

    backend = dhcpBackendWithoutLookup

    configs = (
        ClientConfig('client4hostFile', '00:99:88:77:77:11', '00:99:88:77:77:12', {'ipAddress': '192.168.99.104'}),
        ClientConfig('client4hostFile', '00:99:88:77:77:21', '00:99:88:77:77:22', {})
    )

    def getMissingInfo(term):
        return "Expected {term!r} to be in DHCPD config {file}".format(
            term=term,
            file=backend._dhcpdConfFile._filename
        )

    for clientConfig in configs:
        # (hostname, oldMAC, newMAC, additionalClientConfig)
        clientParameters = {
            'id': '{0}.somenetwork.test'.format(clientConfig.hostname),
            'hardwareAddress': clientConfig.oldMAC,
        }
        clientParameters.update(clientConfig.additionalConfig)

        client = OpsiClient(**clientParameters)
        backend.host_insertObject(client)

        assert isElementInConfigFile(clientConfig.hostname.lower()), getMissingInfo(client.id)
        assert isMacAddressInConfigFile(clientConfig.oldMAC), getMissingInfo(clientConfig.oldMAC)

        client.hardwareAddress = clientConfig.newMAC
        backend.host_updateObject(client)

        assert isMacAddressInConfigFile(clientConfig.newMAC), getMissingInfo(clientConfig.newMAC)
        assert not isMacAddressInConfigFile(clientConfig.oldMAC)
