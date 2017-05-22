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

from contextlib import contextmanager

from OPSI.Logger import Logger
from OPSI.Util.Task.ConfigureBackend import getBackendConfiguration

__all__ = ('updateFileBackend', )

logger = Logger()


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


def readSchemaVersion():
    """
    Read the version of the schema from the database.

    :raises DatabaseMigrationNotFinishedError: In case a migration was \
started but never ended.
    :returns: The version of the schema. `None` if no info is found.
    :returntype: int or None
    """
    raise NotImplementedError("WIP")


@contextmanager
def updateSchemaVersion(version):
    """
    Update the schema information to the given version.

    This is to be used as a context manager and will mark the start
    time of the update aswell as the end time.
    If during the operation something happens there will be no
    information about the end time written to the database.
    """
    raise NotImplementedError("WIP")
