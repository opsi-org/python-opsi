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
Functionality to update a file-based backend.

This module handles the database migrations for opsi.
Usually the function :py:func:updateFileBackend: is called from opsi-setup

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import json
import os.path
import time
from contextlib import contextmanager

from OPSI.Logger import Logger
from OPSI.Util.Task.ConfigureBackend import getBackendConfiguration

from . import BackendUpdateError

__all__ = ('FileBackendUpdateError', 'updateFileBackend')

LOGGER = Logger()


class FileBackendUpdateError(BackendUpdateError):
	"""
	Something went wrong during the update of the file-based backend.
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
	LOGGER.info(u"Current file backend config: {0}", config)

	baseDirectory = config['baseDir']
	schemaVersion = readBackendVersion(baseDirectory)

	if schemaVersion is None:
		LOGGER.notice("Missing information about file backend version. Creating...")
		with updateBackendVersion(baseDirectory, 0):
			LOGGER.info("Creating...")
		LOGGER.notice("Created information about file backend version.")

		schemaVersion = readBackendVersion(baseDirectory)
		assert schemaVersion == 0

	# Placeholder to see the usage for the first update :)
	# if schemaVersion < 1:
	#     print("Update goes here")


def readBackendVersion(baseDirectory):
	"""
	Read the backend version from `baseDirectory`.

	:param baseDirectory: The base directory of the backend.
	:type baseDirectory: str
	:raises FileBackendUpdateError: In case a migration was \
started but never ended.
	:returns: The version of the schema. `None` if no info is found.
	:rtype: int or None
	"""
	schemaConfig = _readVersionFile(baseDirectory)
	if not schemaConfig:
		# We got an empty version -> no version read.
		return None

	for version, info in schemaConfig.items():
		if 'start' not in info:
			raise FileBackendUpdateError("Update {0} gone wrong: start time missing.".format(version))

		if 'end' not in info:
			raise FileBackendUpdateError("Update {0} gone wrong: end time missing.".format(version))

	maximumVersion = max(schemaConfig)

	return maximumVersion


@contextmanager
def updateBackendVersion(baseDirectory, version):
	"""
	Update the backend version to the given `version`

	This is to be used as a context manager and will mark the start
	time of the update aswell as the end time.
	If during the operation something happens there will be no
	information about the end time written to the database.
	:param baseDirectory: The base directory of the backend.
	:type baseDirectory: str
	:param version: The version to update to.
	:type version: int
	"""
	versionInfo = _readVersionFile(baseDirectory)

	if version in versionInfo:
		raise FileBackendUpdateError("Update for {0} already applied!.".format(version))

	versionInfo[version] = {"start": time.time()}
	_writeVersionFile(baseDirectory, versionInfo)
	yield
	versionInfo[version]["end"] = time.time()
	_writeVersionFile(baseDirectory, versionInfo)


def _readVersionFile(baseDirectory):
	"""
	Read the version information from the file in `baseDirectory`.

	:param baseDirectory: The base directory of the backend.
	:type baseDirectory: str
	:return: The complete backend information. The key is the version,
the value is a dict with two keys: `start` holds information about the
time the update was started and `end` about the time the update finished.
	:rtype: {int: {str: float}}
	"""
	schemaConfigFile = getVersionFilePath(baseDirectory)

	try:
		with open(schemaConfigFile) as source:
			versionInfo = json.load(source)
	except IOError:
		return {}

	for key, value in versionInfo.items():
		versionInfo[int(key)] = value
		del versionInfo[key]

	return versionInfo


def getVersionFilePath(baseDirectory):
	"""
	Returns the path to the file containing version information.

	:param baseDirectory: The base directory of the backend.
	:type baseDirectory: str
	:rtype: str
	"""
	return os.path.join(os.path.dirname(baseDirectory), u'config', u'schema.json')


def _writeVersionFile(baseDirectory, versionInfo):
	"""
	Write the version information to the file in `baseDirectory`.

	:param baseDirectory: The base directory of the backend.
	:type baseDirectory: str
	:param versionInfo: Versioning information.
	:type versionInfo: {int: {str: float}}
	"""
	schemaConfigFile = getVersionFilePath(baseDirectory)

	with open(schemaConfigFile, 'w') as destination:
		json.dump(versionInfo, destination)
