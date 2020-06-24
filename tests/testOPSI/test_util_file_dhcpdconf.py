# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

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
Testing the work with the DHCPD configuration files.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os

import pytest

from OPSI.Util.File import DHCPDConfFile

from .helpers import createTemporaryTestfile


def testParsingExampleDHCPDConf():
	testExample = os.path.join(
		os.path.dirname(__file__), 'testdata',
		'util', 'dhcpd', 'dhcpd_1.conf'
	)

	with createTemporaryTestfile(testExample) as fileName:
		confFile = DHCPDConfFile(fileName)
		confFile.parse()


@pytest.fixture
def dhcpdConf(tempDir):
	"""Mixin for an DHCPD backend.
	Manages a subnet 192.168.99.0/24"""

	testData = '''
ddns-update-style none;
default-lease-time 68400;
# max-lease-time 68400;
max-lease-time 68400;
authoritative ;
log-facility local7;
use-host-decl-names on;
option domain-name "domain.local";
option domain-name-servers ns.domain.local;
option routers 192.168.99.254;

# Comment netbios name servers
option netbios-name-servers 192.168.99.2;

subnet 192.168.99.0 netmask 255.255.255.0 {
	group {
		#  Opsi hosts
		next-server 192.168.99.2;
		filename "linux/pxelinux.0/xxx?{}";
		host opsi-test {
			hardware ethernet 9a:e5:3c:10:22:22;
			fixed-address opsi-test.domain.local;
		}
	}
	host out-of-group {
		hardware ethernet 9a:e5:3c:10:22:22;
		fixed-address out-of-group.domain.local;
	}
}
host out-of-subnet {
	hardware ethernet 1a:25:31:11:23:21;
	fixed-address out-of-subnet.domain.local;
}
'''

	dhcpdConfFile = os.path.join(tempDir, 'dhcpd.conf')

	with codecs.open(dhcpdConfFile, 'w', 'utf-8') as f:
		f.write(testData)

	yield DHCPDConfFile(dhcpdConfFile)


def testAddingHostsToConfig(dhcpdConf):
	"""
	Adding hosts to a DHCPDConf.

	If this fails on your machine with a message that 127.x.x.x is refused
	as network address please correct your hostname settings.
	"""
	dhcpdConf.parse()

	dhcpdConf.addHost('TestclienT', '0001-21-21:00:00', '192.168.99.112', '192.168.99.112', None)
	dhcpdConf.addHost('TestclienT2', '00:01:09:08:99:11', '192.168.99.113', '192.168.99.113', {"next-server": "192.168.99.2", "filename": "linux/pxelinux.0/xxx?{}"})

	assert dhcpdConf.getHost('TestclienT2') is not None
	assert dhcpdConf.getHost('notthere') is None


def testGeneratingConfig(dhcpdConf):
	dhcpdConf.parse()

	dhcpdConf.addHost('TestclienT', '0001-21-21:00:00', '192.168.99.112', '192.168.99.112', None)
	dhcpdConf.addHost('TestclienT2', '00:01:09:08:99:11', '192.168.99.113', '192.168.99.113', {"next-server": "192.168.99.2", "filename": "linux/pxelinux.0/xxx?{}"})

	dhcpdConf.generate()
	# TODO: check generated file
