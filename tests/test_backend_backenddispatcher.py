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
Testing BackendDispatcher.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os

import pytest

from OPSI.Backend.BackendManager import BackendDispatcher
from OPSI.Exceptions import BackendConfigurationError

from .Backends.File import getFileBackend
from .conftest import _backendBase


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


def testDispatchingMethodAndReceivingResults(dispatcher):
    assert [] == dispatcher.host_getObjects()


def testLoadingDispatchConfig(dispatcher):
    assert 'file' in dispatcher.dispatcher_getBackendNames()
    assert [(u'.*', (u'file', ))] == dispatcher.dispatcher_getConfig()


@pytest.fixture
def dispatcherBackend(tempDir):
    "A file backend for dispatching"
    with getFileBackend(tempDir) as backend:
        with _backendBase(backend):
            yield backend


@pytest.fixture
def dispatcher(dispatcherBackend, tempDir):
    "a BackendDispatcher running on a file backend."

    dispatchConfigPath = _patchDispatchConfigForFileBackend(tempDir)

    yield BackendDispatcher(
        dispatchConfigFile=dispatchConfigPath,
        backendConfigDir=os.path.join(tempDir, 'etc', 'opsi', 'backends')
    )


def _patchDispatchConfigForFileBackend(targetDirectory):
    configDir = os.path.join(targetDirectory, 'etc', 'opsi', 'backendManager')
    dispatchConfigPath = os.path.join(configDir, 'dispatch.conf')

    with open(dispatchConfigPath, 'w') as dpconf:
        dpconf.write("""
.* : file
""")

    return dispatchConfigPath
