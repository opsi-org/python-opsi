# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Functionality to automatically configure an OPSI backend.

.. versionadded:: 4.0.4.6
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

	LOGGER.info(u"Loading backend config '%s'", backendConfigFile)
	with open(backendConfigFile) as configFile:
		exec(configFile.read(), customGlobals)

	config = customGlobals['config']
	LOGGER.debug(u"Current backend config: %s", config)

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
