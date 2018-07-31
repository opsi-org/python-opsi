# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2018 uib GmbH <info@uib.de>

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
Testing the opsi-package-updater functionality.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path
import pytest

from OPSI.Util.Task.UpdatePackages import OpsiPackageUpdater
from OPSI.Util.Task.UpdatePackages.Config import DEFAULT_CONFIG

from .helpers import mock, workInTemporaryDirectory
from .test_hosts import getConfigServer


@pytest.fixture
def packageUpdaterClass(backendManager):
	configServer = getConfigServer()
	backendManager.host_insertObject(configServer)

	klass = OpsiPackageUpdater
	with mock.patch.object(klass, 'getConfigBackend', return_value=backendManager):
		yield klass


def testListingLocalPackages(packageUpdaterClass):
	with workInTemporaryDirectory() as tempDir:
		configFile = os.path.join(tempDir, 'emptyconfig.conf')
		with open(configFile, 'w'):
			pass

		filenames = [
			'not.tobefound.opsi.nono',
			'thingy_1.2-3.opsi', 'thingy_1.2-3.opsi.no'
		]

		for filename in filenames:
			with open(os.path.join(tempDir, filename), 'w'):
				pass

		config = DEFAULT_CONFIG.copy()
		config['packageDir'] = tempDir
		config['configFile'] = configFile

		packageUpdater = packageUpdaterClass(config)
		localPackages = packageUpdater.getLocalPackages()
		packageInfo = localPackages.pop()
		assert not localPackages, "There should only be one package!"

		expectedInfo = {
			"productId": "thingy",
			"version": "1.2-3",
			"packageFile": os.path.join(tempDir, 'thingy_1.2-3.opsi'),
			"filename": "thingy_1.2-3.opsi",
			"md5sum": None
		}

		assert set(packageInfo.keys()) == set(expectedInfo.keys())
		assert packageInfo['md5sum']  # We want any value

		del expectedInfo['md5sum']  # Not comparing this
		for key, expectedValue in expectedInfo.items():
			assert packageInfo[key] == expectedValue


@pytest.fixture
def exampleConfigPath():
	return os.path.join(
		os.path.dirname(__file__), 'testdata', 'util', 'task',
		'updatePackages', 'example_updater.conf'
	)


def patchConfigFile(filename, **values):
	with open(filename) as configFile:
		lines = configFile.readlines()

	newLines = []
	for line in lines:
		for key, value in values.items():
			if line.startswith(key):
				newLines.append('{} = {}\n'.format(key, value))
				break
		else:
			newLines.append(line)

	with open(filename, 'w') as configFile:
		for line in newLines:
			configFile.write(line)


def testParsingConfigFile(exampleConfigPath, packageUpdaterClass):
	with workInTemporaryDirectory() as tempDir:
		preparedConfig = DEFAULT_CONFIG.copy()
		preparedConfig['packageDir'] = tempDir
		preparedConfig['configFile'] = exampleConfigPath

		repoPath = os.path.join(tempDir, 'repos.d')
		os.mkdir(repoPath)

		patchConfigFile(filename, packageDir=tempDir, repositoryConfigDir=repoPath)

		packageUpdater = packageUpdaterClass(preparedConfig)
		config = packageUpdater.config

		assert config
		assert not config['repositories']

		assert config['packageDir'] == '/var/lib/opsi/repository'
		assert config['tempdir'] == '/tmp'
		assert config['repositoryConfigDir'] = '/etc/opsi/package-updater.repos.d/'

		# e-mail notification settings
		assert config['notification'] == False
		assert config['smtphost'] == 'smtp'
		assert config['smtpport'] == 25
		assert config['smtpuser'] == DEFAULT_CONFIG['smtpuser']
		assert config['smtppassword'] == DEFAULT_CONFIG['smtppassword']
		assert config['use_starttls'] == False
		assert config['sender'] == 'opsi-package-updater@localhost'
		assert config['receivers'] == ['root@localhost', 'anotheruser@localhost']
		assert config['subject'] == 'opsi-package-updater example config'

		# Automatic installation settings
		assert config['installationWindowStartTime'] == '01:23'
		assert config['installationWindowEndTime'] == '04:56'
		assert config['installationWindowExceptions'] == ['firstProduct', 'second-product']

		# Wake-On-LAN settings
		assert config['wolAction'] == False
		assert config['wolActionExcludeProductIds'] == ['this', 'that']
		assert config['wolShutdownWanted'] == True
		assert config['wolStartGap'] == 10
