# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the backend initialisation.
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
