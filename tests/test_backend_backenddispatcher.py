# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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
Testing BackendDispatcher.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import unittest

from OPSI.Backend.BackendManager import BackendDispatcher
from OPSI.Types import BackendConfigurationError

from .Backends.File import FileBackendMixin

import pytest


@pytest.mark.parametrize("kwargs", [
    {},
    {'dispatchConfigfile': ''},
    {'dispatchConfigfile': 'nope'},
    {'dispatchConfig': ''},
    {'dispatchConfig': [(u'.*', (u'file',))]},
])
def testBackendCreationFailsIfConfigMissing(kwargs):
    with pytest.raises(BackendConfigurationError):
        BackendDispatcher(**kwargs)


@pytest.mark.parametrize("create_folder", [True, False], ids=["existing folder", "nonexisting folder"])
def testLoadingDispatchConfigFailsIfBackendConfigWithoutConfigs(create_folder, tempDir):
    backendDir = os.path.join(tempDir, 'backends')

    if create_folder:
        os.mkdir(backendDir)
        print("Created folder: {0}".format(backendDir))

    with pytest.raises(BackendConfigurationError):
        BackendDispatcher(
            dispatchConfig=[[u'.*', [u'file']]],
            backendConfigDir=backendDir
        )


class BackendDispatcherWithBackendTestCase(unittest.TestCase, FileBackendMixin):
    """
    Testing the BackendDispatcher with files on the disk.

    This will create files that look like an actual backend to simulate
    correct loading of backend information.
    """
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testLoadingDispatchConfig(self):
        dispatchConfig = [(u'.*', (u'file', ))]

        dispatcher = BackendDispatcher(
            dispatchConfigFile=self._fileBackendConfig['dispatchConfig'],
            backendConfigDir=os.path.join(self._fileTempDir, 'etc', 'opsi', 'backends')
        )

        assert 'file' in dispatcher.dispatcher_getBackendNames()
        assert dispatchConfig == dispatcher.dispatcher_getConfig()

    def testDispatchingMethodAndReceivingResults(self):
        dispatcher = BackendDispatcher(
            dispatchConfigFile=self._fileBackendConfig['dispatchConfig'],
            backendConfigDir=os.path.join(self._fileTempDir, 'etc', 'opsi', 'backends')
        )

        assert [] == dispatcher.host_getObjects()
