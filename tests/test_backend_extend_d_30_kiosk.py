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
Tests for the kiosk client method.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import pytest

from OPSI.Object import ConfigState, OpsiClient, OpsiDepotserver, UnicodeConfig
from OPSI.Types import BackendMissingDataError


def testGettingInfoForNonExistingClient(backendManager):
    with pytest.raises(BackendMissingDataError):
        backendManager.getKioskProductInfosForClient('foo.bar.baz')

# TODO: set custom configState for the client with different products in group.
# TODO: check what happens if client is on different depot.
def testGettingEmptyInfo(backendManager):
    client = OpsiClient(id='foo.test.invalid')
    depot = OpsiDepotserver(id='depotserver1.test.invalid')
    backendManager.host_createObjects([client, depot])

    basicConfigs = [
        UnicodeConfig(
            id=u'software-on-demand.product-group-ids',
            defaultValues=["software-on-demand"],
            multiValue=True,
        ),
        UnicodeConfig(
            id=u'clientconfig.depot.id',
            description=u'Depotserver to use',
            possibleValues=[],
            defaultValues=[depot.id]
        ),
    ]
    backendManager.config_createObjects(basicConfigs)

    clientDepotMappingConfigState = ConfigState(
        configId=u'clientconfig.depot.id',
        objectId=client.id,
        values=depot.id
    )

    backendManager.configState_createObjects(clientDepotMappingConfigState)

    assert [] == backendManager.getKioskProductInfosForClient(client.id)
