#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013 uib GmbH <info@uib.de>

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
from OPSI.Util import objectToBeautifiedText

LOGGER = Logger()


def getBackendConfiguration(backendConfigFile, customLocals=None):
	"""
	Reads the backend configuration from the given file.

	:param backendConfigFile: Path to the backend configuration file.
	:param customLocals: If special locals are needed for the config file \
please pass them here. If this is None defaults will be used.
	:type customLocals: dict
	"""
	if customLocals is None:
		customLocals = {
			'socket': socket,
			'os': os,
			'sys': sys,
			'module': '',
			'config': {}
		}

	LOGGER.info(u"Loading backend config '{0}'".format(backendConfigFile))
	execfile(backendConfigFile, customLocals)
	config = customLocals['config']
	LOGGER.debug(u"Current backend config: %s" % config)

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
