# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2019 uib GmbH <info@uib.de>

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
Testing the backend initialisation.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import OPSI.Util.Task.InitializeBackend as initBackend

import pytest
from .helpers import mock


@pytest.mark.parametrize("onUCS", [True, False])
def testGettingServerConfig(onUCS):
	networkConfig = {
		"ipAddress": "192.168.12.34",
		"hardwareAddress": "acabacab",
		"subnet": "192.168.12.0",
		"netmask": "255.255.255.0"
	}
	fqdn = "blackwidow.test.invalid"

	with mock.patch('OPSI.Util.Task.InitializeBackend.isUCS', lambda: onUCS):
		config = initBackend._getServerConfig(fqdn, networkConfig)

	assert config['id'] == fqdn
	for key in ('opsiHostKey', 'description', 'notes', 'inventoryNumber', 'masterDepotId'):
		assert config[key] is None

	assert config['ipAddress'] == networkConfig['ipAddress']
	assert config['hardwareAddress'] == networkConfig['hardwareAddress']
	assert config['maxBandwidth'] == 0
	assert config['isMasterDepot'] is True

	if onUCS:
		address = fqdn
	else:
		address = networkConfig['ipAddress']

	assert config['depotLocalUrl'] == u'file:///var/lib/opsi/depot'
	assert config['depotRemoteUrl'] == u'smb://%s/opsi_depot' % address
	assert config['depotWebdavUrl'] == u'webdavs://%s:4447/depot' % address
	assert config['repositoryLocalUrl'] == u'file:///var/lib/opsi/repository'
	assert config['repositoryRemoteUrl'] == u'webdavs://%s:4447/repository' % address
	assert config['workbenchLocalUrl'] == u'file:///var/lib/opsi/workbench'
	assert config['workbenchRemoteUrl'] == u'smb://{}/opsi_workbench'.format(address)
	assert config['networkAddress'] == u'{subnet}/{netmask}'.format(**networkConfig)
