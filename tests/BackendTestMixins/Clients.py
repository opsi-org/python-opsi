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
Backend mixin for testing client functionality.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Object import OpsiClient


def getClients():
    client1 = OpsiClient(
        id='client1.test.invalid',
        description='Test client 1',
        notes='Notes ...',
        hardwareAddress='00:01:02:03:04:05',
        ipAddress='192.168.1.100',
        lastSeen='2009-01-01 00:00:00',
        opsiHostKey='45656789789012789012345612340123',
        inventoryNumber=None
    )

    client2 = OpsiClient(
        id='client2.test.invalid',
        description='Test client 2',
        notes=';;;;;;;;;;;;;;',
        hardwareAddress='00-ff0aa3:0b-B5',
        opsiHostKey='59051234345678890121678901223467',
        inventoryNumber='00000000003',
        oneTimePassword='logmein'
    )

    client3 = OpsiClient(
        id='client3.test.invalid',
        description='Test client 3',
        notes='#############',
        inventoryNumber='XYZABC_1200292'
    )

    client4 = OpsiClient(
        id='client4.test.invalid',
        description='Test client 4',
    )

    client5 = OpsiClient(
        id='client5.test.invalid',
        description='Test client 5',
        oneTimePassword='abe8327kjdsfda'
    )

    client6 = OpsiClient(
        id='client6.test.invalid',
        description='Test client 6',
    )

    client7 = OpsiClient(
        id='client7.test.invalid',
        description='Test client 7',
    )

    return client1, client2, client3, client4, client5, client6, client7
