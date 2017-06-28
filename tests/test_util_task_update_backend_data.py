# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017 uib GmbH <info@uib.de>

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
Testing the update of the MySQL backend from an older version.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from OPSI.Object import OpsiClient, OpsiDepotserver, OpsiConfigserver
from OPSI.Util.Task.UpdateBackend.ConfigurationData import updateBackendData

from .test_hosts import getLocalHostFqdn


def testUpdateBackendData(backendManager):
    addServers(backendManager)
    updateBackendData(backendManager)

    servers = backendManager.host_getObjects(type=["OpsiDepotserver", "OpsiConfigserver"])
    assert servers, "No servers found in backend."

    for server in servers:
        assert server.workbenchLocalUrl
        assert server.workbenchRemoteUrl

        # TODO: check if the right value for each distribution is inserted


def addServers(backend):
    localHostFqdn = getLocalHostFqdn()
    configServer = OpsiConfigserver(id=localHostFqdn)
    backend.host_createObjects([configServer])

    _, domain = localHostFqdn.split('.', 1)

    depots = [
        OpsiDepotserver(id='depot{n}.{domain}'.format(n=index, domain=domain))
        for index in range(10)
    ]
    backend.host_createObjects(depots)

    clients = [
        OpsiClient(id='client{n}.{domain}'.format(n=index, domain=domain))
        for index in range(10)
    ]
    backend.host_createObjects(clients)
