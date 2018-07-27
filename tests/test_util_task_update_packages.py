

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
            'thingy_1.2-3.opsi', 'thingy_1.2-3.opsi.md5'
        ]

        with open(os.path.join(filenames), 'w'):
            pass

        config = DEFAULT_CONFIG.copy()
        config['packageDir'] = tempDir
        config['configFile'] = configFile

        packageUpdater = packageUpdaterClass(config)
        localPackages = packageUpdater.getLocalPackages()
        print(localPackages)
        assert len(localPackages) == 1

        # TODO: check for local packages
