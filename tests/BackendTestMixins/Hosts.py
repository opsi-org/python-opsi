#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Backend mixin for testing the functionality of working with hosts.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import socket
from OPSI.Object import OpsiConfigserver, OpsiDepotserver


def getConfigServer():
    serverId = socket.getfqdn()
    if serverId.count('.') < 2:
        raise Exception(u"Failed to get fqdn: %s" % serverId)

    return OpsiConfigserver(
            id=serverId,
            opsiHostKey='71234545689056789012123678901234',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl=u'smb://%s/opt_pcbin/install' % serverId.split(
                '.')[0],
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl=u'webdavs://%s:4447/repository' % serverId,
            description='The configserver',
            notes='Config 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000001',
            networkAddress='192.168.1.0/24',
            maxBandwidth=10000
        )


def getDepotServers():
    depotserver1 = OpsiDepotserver(
        id='depotserver1.uib.local',
        opsiHostKey='19012334567845645678901232789012',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl='smb://depotserver1.test.invalid/opt_pcbin/install',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl='webdavs://depotserver1.test.invalid:4447/repository',
        description='A depot',
        notes='D€pot 1',
        hardwareAddress=None,
        ipAddress=None,
        inventoryNumber='00000000002',
        networkAddress='192.168.2.0/24',
        maxBandwidth=10000
    )

    depotserver2 = OpsiDepotserver(
        id='depotserver2.test.invalid',
        opsiHostKey='93aa22f38a678c64ef678a012d2e82f2',
        depotLocalUrl='file:///opt/pcbin/install',
        depotRemoteUrl='smb://depotserver2.test.invalid/opt_pcbin',
        repositoryLocalUrl='file:///var/lib/opsi/repository',
        repositoryRemoteUrl='webdavs://depotserver2.test.invalid:4447/repository',
        description='Second depot',
        notes='no notes here',
        hardwareAddress='00:01:09:07:11:aa',
        ipAddress='192.168.10.1',
        inventoryNumber='',
        networkAddress='192.168.10.0/24',
        maxBandwidth=240000
    )

    return depotserver1, depotserver2
