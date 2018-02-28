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
Testing the update of configuration data.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import pytest

from OPSI.Object import OpsiClient, OpsiDepotserver, OpsiConfigserver
from OPSI.Util.Task.UpdateBackend.ConfigurationData import updateBackendData

from .test_hosts import getLocalHostFqdn
from .helpers import mock


@pytest.mark.parametrize("onSuse, expectedLocalPath", (
	(True, 'file:///var/lib/opsi/workbench'),
	(False, 'file:///home/opsiproducts'),
))
def testUpdateBackendData(backendManager, onSuse, expectedLocalPath):
	def getDepotAddress(address):
		_, addressAndPath = address.split(':')
		return addressAndPath.split('/')[2]

	addServers(backendManager)
	with mock.patch('OPSI.Util.Task.UpdateBackend.ConfigurationData.isOpenSUSE', lambda: onSuse):
		with mock.patch('OPSI.Util.Task.UpdateBackend.ConfigurationData.isSLES', lambda: onSuse):
			updateBackendData(backendManager)

	servers = backendManager.host_getObjects(type=["OpsiDepotserver", "OpsiConfigserver"])
	assert servers, "No servers found in backend."

	for server in servers:
		assert server.workbenchLocalUrl == expectedLocalPath

		depotAddress = getDepotAddress(server.depotRemoteUrl)
		expectedAddress = 'smb://' + depotAddress + '/opsi_workbench'
		assert expectedAddress == server.workbenchRemoteUrl


def addServers(backend):
	localHostFqdn = getLocalHostFqdn()
	configServer = OpsiConfigserver(
		id=localHostFqdn,
		depotRemoteUrl='smb://192.168.123.1/opsi_depot'
	)
	backend.host_createObjects([configServer])

	_, domain = localHostFqdn.split('.', 1)

	def getDepotRemoteUrl(index):
		if index % 2 == 0:
			return 'smb://192.168.123.{}/opsi_depot'.format(index)
		else:
			return 'smb://somename/opsi_depot'

	depots = [
		OpsiDepotserver(
			id='depot{n}.{domain}'.format(n=index, domain=domain),
			depotRemoteUrl=getDepotRemoteUrl(index)
		)
		for index in range(10)
	]
	backend.host_createObjects(depots)

	clients = [
		OpsiClient(id='client{n}.{domain}'.format(n=index, domain=domain))
		for index in range(10)
	]
	backend.host_createObjects(clients)
