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
Testing the update of the MySQL backend from an older version.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import json
import os.path

from .Backends.File import getFileBackend

import pytest
from OPSI.Util.Task.UpdateBackend.File import (
    FileBackendUpdateError,
    getVersionFilePath, readBackendVersion, _readVersionFile,
    updateBackendVersion, updateFileBackend
)


@pytest.fixture
def fileBackend(tempDir):
    with getFileBackend(path=tempDir) as backend:
        yield backend


def testUpdatingFileBackend(fileBackend, tempDir):
    config = os.path.join(tempDir, 'etc', 'opsi', 'backends', 'file.conf')

    updateFileBackend(config)


def testReadingSchemaVersionFromMissingFile(tempDir):
    assert readBackendVersion(os.path.join(tempDir, 'missingbasedir')) is None


@pytest.fixture
def baseDirectory(tempDir):
    newDir = os.path.join(tempDir, 'config')
    os.makedirs(newDir)
    yield newDir


@pytest.fixture
def writtenConfig(baseDirectory):
    configFile = getVersionFilePath(baseDirectory)
    config = {
        0:
            {
                "start": 1495529319.022833,
                "end": 1495529341.870662,
            },
        1:
            {
                "start": 1495539432.271123,
                "end": 1495539478.045244
            },
    }
    with open(configFile, 'w') as f:
        json.dump(config, f)

    yield config


def testReadingSchemaVersionLowLevel(baseDirectory, writtenConfig):
    assert writtenConfig == _readVersionFile(baseDirectory)


def testReadingSchemaVersion(baseDirectory, writtenConfig):
    version = readBackendVersion(baseDirectory)
    assert version is not None
    assert version == max(writtenConfig.keys())
    assert version > 0


@pytest.mark.parametrize("config", [
    {0: {"start": 1495529319.022833}},  # missing end
    {0: {}}  # missing start
])
def testRaisingExceptionOnUnfinishedUpdate(baseDirectory, config):
    configFile = getVersionFilePath(baseDirectory)

    with open(configFile, 'w') as f:
        json.dump(config, f)

    with pytest.raises(FileBackendUpdateError):
        readBackendVersion(baseDirectory)


def testApplyingTheSameUpdateMultipleTimesFails(baseDirectory):
    with updateBackendVersion(baseDirectory, 1):
        pass

    with pytest.raises(FileBackendUpdateError):
        with updateBackendVersion(baseDirectory, 1):
            pass
