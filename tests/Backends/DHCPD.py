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
Mixin that provides an ready to use DHCPD backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import codecs
import os
import tempfile

from OPSI.Util.File import DHCPDConfFile
from . import BackendMixin


class DHCPDConfMixin(BackendMixin):
    """Mixin for an DHCPD backend.
    Manages a subnet 192.168.99.0/24"""

    def setUpDHCPDConf(self):
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

        self.dhcpdConfFile = tempfile.mkstemp()[1]

        with codecs.open(self.dhcpdConfFile, 'w', 'utf-8') as f:
            f.write(testData)

        self.dhcpdConf = DHCPDConfFile(self.dhcpdConfFile)

    def tearDownDHCPDConf(self):
        del self.dhcpdConf

        try:
            os.remove(self.dhcpdConfFile)
        except OSError:
            pass

        del self.dhcpdConfFile
