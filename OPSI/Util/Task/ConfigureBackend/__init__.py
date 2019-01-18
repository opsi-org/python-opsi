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
Functionality to automatically configure an OPSI backend.

.. versionadded:: 4.0.4.6

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os
import re
import socket
import sys

from OPSI.Logger import Logger
from OPSI.System.Posix import getNetworkConfiguration, getLocalFqdn
from OPSI.Util import objectToBeautifiedText

__all__ = ('getBackendConfiguration', 'updateConfigFile')

LOGGER = Logger()


def getBackendConfiguration(backendConfigFile, customGlobals=None):
	"""
	Reads the backend configuration from the given file.

	:param backendConfigFile: Path to the backend configuration file.
	:param customGlobals: If special locals are needed for the config file \
please pass them here. If this is None defaults will be used.
	:type customGlobals: dict
	"""
	if customGlobals is None:
		customGlobals = {
			'config': {},  # Will be filled after loading
			'module': '',  # Will be filled after loading
			'os': os,
			'socket': socket,
			'sys': sys,
		}

	LOGGER.info(u"Loading backend config '{0}'", backendConfigFile)
	execfile(backendConfigFile, customGlobals)
	config = customGlobals['config']
	LOGGER.debug(u"Current backend config: {!r}", config)

	return config


def updateConfigFile(backendConfigFile, newConfig, notificationFunction=None):
	"""
	Updates a config file with the corresponding new configuration.

	:param backendConfigFile: path to the backend configuration
	:param newConfig: the new configuration.
	:param notificationFunction: A function that log messages will be passed \
on to. Defaults to logger.notice
	:type notificationFunction: func
	"""
	def correctBooleans(text):
		"""
		Creating correct JSON booleans - they are all lowercase.
		"""
		return text.replace("true", "True").replace("false", "False")

	if notificationFunction is None:
		notificationFunction = LOGGER.notice

	notificationFunction(u"Updating backend config '%s'" % backendConfigFile)

	lines = []
	with codecs.open(backendConfigFile, 'r', 'utf-8') as backendFile:
		for line in backendFile.readlines():
			if re.search(r'^\s*config\s*\=', line):
				break
			lines.append(line)

	with codecs.open(backendConfigFile, 'w', 'utf-8') as backendFile:
		backendFile.writelines(lines)
		backendConfigData = correctBooleans(objectToBeautifiedText(newConfig))
		backendFile.write("config = %s\n" % backendConfigData)

	notificationFunction(u"Backend config '%s' updated" % backendConfigFile)


def _getSysConfig():
	"""
	Skinned down version of getSysConfig from ``opsi-setup``.

	Should be used as **fallback only**!
	"""
	LOGGER.notice(u"Getting current system config")
	fqdn = getLocalFqdn()
	sysConfig = {
		'fqdn': fqdn,
		'hostname': fqdn.split(u'.')[0]
	}

	sysConfig.update(getNetworkConfiguration())

	LOGGER.notice(u"System information:")
	LOGGER.notice(u"   ip address   : %s" % sysConfig['ipAddress'])
	LOGGER.notice(u"   netmask      : %s" % sysConfig['netmask'])
	LOGGER.notice(u"   subnet       : %s" % sysConfig['subnet'])
	LOGGER.notice(u"   broadcast    : %s" % sysConfig['broadcast'])
	LOGGER.notice(u"   fqdn         : %s" % sysConfig['fqdn'])
	LOGGER.notice(u"   hostname     : %s" % sysConfig['hostname'])

	return sysConfig
