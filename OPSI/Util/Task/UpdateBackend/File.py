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
Functionality to update a file-based backend.

This module handles the database migrations for opsi.
Usually the function :py:func:updateFileBackend: is called from opsi-setup

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import json
import os.path
import time
from contextlib import contextmanager

from OPSI.Logger import Logger
from OPSI.Util.Task.ConfigureBackend import getBackendConfiguration

__all__ = ('updateFileBackend', )

logger = Logger()


class BackendUpdateUnfinishedError(ValueError):
    """
    This error indicates an unfinished file backend migration.
    """
    pass


def updateFileBackend(
        backendConfigFile=u'/etc/opsi/backends/file.conf',
        additionalBackendConfiguration={}):
    """
    Applies migrations to the file-based backend.

    :param backendConfigFile: Path to the file where the backend \
configuration is read from.
    :type backendConfigFile: str
    :param additionalBackendConfiguration: Additional / different \
settings for the backend that will extend / override the configuration \
read from `backendConfigFile`.
    :type additionalBackendConfiguration: dict
    """

    config = getBackendConfiguration(backendConfigFile)
    config.update(additionalBackendConfiguration)
    logger.info(u"Current file backend config: {0}", config)

    baseDirectory = config['baseDir']
    schemaVersion = readBackendVersion(baseDirectory)

    if schemaVersion is None:
        logger.notice("Missing information about file backend version. Creating...")
        with updateBackendVersion(baseDirectory, 0):
            logger.info("Creating...")
        logger.notice("Created information about file backend version.")

        schemaVersion = readBackendVersion(baseDirectory)
        assert schemaVersion == 0

    # Placeholder to see the usage for the first update :)
    # if schemaVersion < 1:
    #     print("Update goes here")


def readBackendVersion(baseDirectory):
    """
    Read the version of the schema from the database.

    :raises DatabaseMigrationNotFinishedError: In case a migration was \
started but never ended.
    :returns: The version of the schema. `None` if no info is found.
    :returntype: int or None
    """
    schemaConfig = _readVersionFile(baseDirectory)
    if not schemaConfig:
        # We got an empty version -> no version read.
        return None

    for version, info in schemaConfig.items():
        if 'start' not in info:
            raise BackendUpdateUnfinishedError("Update {0} gone wrong: start time missing.".format(version))

        if 'end' not in info:
            raise BackendUpdateUnfinishedError("Update {0} gone wrong: end time missing.".format(version))

    maximumVersion = max(schemaConfig)

    return maximumVersion


def getVersionFilePath(baseDirectory):
    return os.path.join(os.path.dirname(baseDirectory), u'config', u'schema.json')


@contextmanager
def updateBackendVersion(baseDirectory, version):
    """
    Update the schema information to the given version.

    This is to be used as a context manager and will mark the start
    time of the update aswell as the end time.
    If during the operation something happens there will be no
    information about the end time written to the database.
    """
    versionInfo = _readVersionFile(baseDirectory)

    assert version not in versionInfo
    if version in versionInfo:
        raise RuntimeError("Update for {0} already applied!.".format(version))

    versionInfo[version] = {"start": time.time()}
    _writeVersionFile(baseDirectory, versionInfo)
    yield
    versionInfo[version]["end"] = time.time()
    _writeVersionFile(baseDirectory, versionInfo)


def _readVersionFile(baseDirectory):
    schemaConfigFile = getVersionFilePath(baseDirectory)

    try:
        with open(schemaConfigFile) as f:
            versionInfo = json.load(f)
    except IOError:
        return {}

    for key, value in versionInfo.items():
        versionInfo[int(key)] = value
        del versionInfo[key]

    return versionInfo


def _writeVersionFile(baseDirectory, versionInfo):
    schemaConfigFile = getVersionFilePath(baseDirectory)

    with open(schemaConfigFile, 'w') as f:
        json.dump(versionInfo, f)
