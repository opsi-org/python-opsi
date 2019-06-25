# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2019 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded extension `20_easy.conf`.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/20_easy.conf``.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .test_hosts import getConfigServer, getDepotServers, getClients


def testGetClients(backendManager):
    clients = getClients()
    hosts = [getConfigServer()]
    hosts.extend(getDepotServers())
    hosts.extend(clients)
    for host in hosts:
        backendManager.host_insertObject(host)

    newClients = backendManager.getClients()

    assert len(newClients) == len(clients)

    for client in newClients:
        assert isinstance(client, dict)

        assert 'type' not in client
        assert 'id' not in client
        assert 'depotId' in client

        for key, value in client.items():
            assert value is not None, 'Key {} has a None value'.format(key)
