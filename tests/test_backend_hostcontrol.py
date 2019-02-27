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
Testing the Host Control backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Backend.HostControl import HostControlBackend
from .test_hosts import getClients

import pytest


def testCallingStartAndStopMethod(hostControlBackend):
    """
    Test if calling the methods works.

    This test does not check if WOL on these clients work nor that
    they do exist.
    """
    clients = getClients()
    hostControlBackend.host_createObjects(clients)

    hostControlBackend._hostRpcTimeout = 1  # for faster finishing of the test

    hostControlBackend.hostControl_start([u'client1.test.invalid'])
    hostControlBackend.hostControl_shutdown([u'client1.test.invalid'])


@pytest.fixture
def hostControlBackend(extendedConfigDataBackend):
    yield HostControlBackend(extendedConfigDataBackend)
