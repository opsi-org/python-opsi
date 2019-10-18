# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util.Task.Samba

:author: Mathias Radtke <m.radtke@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os.path
import pytest

import OPSI.Util.Task.Samba as Samba

from .helpers import mock


@pytest.fixture(params=[True, False], ids=['Samba-4', 'Samba-3'])
def isSamba4(request):
	with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: request.param):
		yield request.param


@pytest.fixture
def pathToSmbConf(tempDir):
	"""
	Path to an empty file serving as possible smb.conf.
	"""
	pathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
	with open(pathToSmbConf, 'w'):
		pass

	return pathToSmbConf


@pytest.fixture
def disableDirCreation():
	def printMessage(path, *_unused):
		print("Would create {0!r}".format(path))

	with mock.patch('OPSI.Util.Task.Samba.os.mkdir', printMessage):
		yield


@pytest.fixture(params=['/home/opsiproducts', '/var/lib/opsi/workbench/'])
def workbenchPath(request):
	path = request.param
	with mock.patch('OPSI.Util.Task.Samba.getWorkbenchDirectory', lambda: path):
		yield path


@pytest.mark.parametrize("emptyoutput", [None, []])
def testCheckForSambaVersionWithoutSMBD(emptyoutput):
	with mock.patch('OPSI.Util.Task.Samba.execute', lambda cmd: emptyoutput):
		with mock.patch('OPSI.Util.Task.Samba.which', lambda cmd: None):
			assert not Samba.isSamba4()


@pytest.mark.parametrize("versionString, expectedSamba4", [
	('version 4.0.3', True),
	('version 3.1', False)
])
def testCheckForSamba4DependsOnVersion(versionString, expectedSamba4):
	with mock.patch('OPSI.Util.Task.Samba.execute', lambda cmd: [versionString]):
		with mock.patch('OPSI.Util.Task.Samba.which', lambda cmd: cmd):
			assert Samba.isSamba4() == expectedSamba4


def testReadingEmptySambaConfig(pathToSmbConf):
	assert [] == Samba._readConfig(pathToSmbConf)


def testReadingSambaConfig(pathToSmbConf):
	config = [
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_repository]\n",
		u"[opsi_logs]\n",
	]

	with open(pathToSmbConf, 'w') as fakeSambaConfig:
		for line in config:
			fakeSambaConfig.write(line)

	assert config == Samba._readConfig(pathToSmbConf)


def testConfigureSambaOnUbuntu(isSamba4, workbenchPath, disableDirCreation):
	result = Samba._processConfig([])

	if workbenchPath.endswith('/'):
		workbenchPath = workbenchPath[:-1]

	assert any('path = {}'.format(workbenchPath) in line for line in result)


def testSambaConfigureSamba4Share(isSamba4, workbenchPath, disableDirCreation):
	config = [
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_repository]\n",
		u"[opsi_logs]\n",
	]

	result = Samba._processConfig(config)

	assert any(line.strip() for line in result)


def testAdminUsersAreAddedToExistingOpsiDepotShare(isSamba4, disableDirCreation):
	config = [
		u"[opsi_depot]\n",
		u"   available = yes\n",
		u"   comment = opsi depot share (ro)\n",
		u"   path = /var/lib/opsi/depot\n",
		u"   oplocks = no\n",
		u"   follow symlinks = yes\n",
		u"   level2 oplocks = no\n",
		u"   writeable = no\n",
		u"   invalid users = root\n",
	]

	if not isSamba4:
		pytest.skip("Requires Samba 4.")

	result = Samba._processConfig(config)

	assert any('admin users' in line for line in result), 'Missing Admin Users in Share opsi_depot'


def testCorrectOpsiDepotShareWithoutFixForSamba4(isSamba4, disableDirCreation):
	config = [
		u"[opsi_depot]\n",
		u"   available = yes\n",
		u"   comment = opsi depot share (ro)\n",
		u"   path = /var/lib/opsi/depot\n",
		u"   oplocks = no\n",
		u"   follow symlinks = yes\n",
		u"   level2 oplocks = no\n",
		u"   writeable = no\n",
		u"   invalid users = root\n",
	]

	if not isSamba4:
		pytest.skip("Requires Samba 4.")

	result = Samba._processConfig(config)

	opsiDepotFound = False
	for line in result:
		if line.strip():
			if '[opsi_depot]' in line:
				opsiDepotFound = True
			elif opsiDepotFound and 'admin users' in line:
				break
			elif opsiDepotFound and line.startswith('['):
				opsiDepotFound = False
				break
	else:
		raise RuntimeError('Did not find "admin users" in opsi_depot share')


def testCorrectOpsiDepotShareWithSamba4Fix(isSamba4, disableDirCreation):
	config = [
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"   available = yes\n",
		u"   comment = opsi depot share (ro)\n",
		u"   path = /var/lib/opsi/depot\n",
		u"   oplocks = no\n",
		u"   follow symlinks = yes\n",
		u"   level2 oplocks = no\n",
		u"   writeable = no\n",
		u"   invalid users = root\n",
		u"   admin users = @%s\n" % Samba.FILE_ADMIN_GROUP,
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_repository]\n",
		u"[opsi_logs]\n",
	]

	if not isSamba4:
		pytest.skip("Requires Samba 4.")

	assert config == Samba._processConfig(config)


def testProcessConfigDoesNotRemoveComment(isSamba4, disableDirCreation):
	config = [
		u"; load opsi shares\n",
		u"include = /etc/samba/share.conf\n",
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_repository]\n",
		u"[opsi_logs]\n",
	]

	result = Samba._processConfig(config)

	assert any('; load opsi shares' in line for line in result)


def testProcessConfigAddsMissingRepositoryShare(isSamba4, disableDirCreation):
	config = [
		u"; load opsi shares\n",
		u"include = /etc/samba/share.conf\n",
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_logs]\n",
	]

	result = Samba._processConfig(config)

	repository = False
	pathFound = False
	for line in result:
		if '[opsi_repository]' in line:
			repository = True
		elif repository:
			if line.strip().startswith('['):
				# next section
				break
			elif line.strip().startswith('path'):
				assert '/var/lib/opsi/repository' in line
				pathFound = True
				break

	assert repository, "Missing entry 'opsi_repository'"
	assert pathFound, "Missing 'path' in 'opsi_repository'"


def testWritingEmptySambaConfig(pathToSmbConf):
	Samba._writeConfig([], pathToSmbConf)

	with open(pathToSmbConf, 'r') as readConfig:
		assert [] == readConfig.readlines()


def testWritingSambaConfig(pathToSmbConf):
	config = [
		u"[opt_pcbin]\n",
		u"[opsi_depot]\n",
		u"[opsi_depot_rw]\n",
		u"[opsi_images]\n",
		u"[opsi_workbench]\n",
		u"[opsi_repository]\n",
		u"[opsi_logs]\n",

	]

	Samba._writeConfig(config, pathToSmbConf)

	with open(pathToSmbConf, 'r') as readConfig:
		assert config == readConfig.readlines()
