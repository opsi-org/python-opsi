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

from OPSI.Backend.Backend import OPSI_GLOBAL_CONF
from OPSI.Logger import Logger
from OPSI.System import getEthernetDevices, getNetworkDeviceConfig
from OPSI.Types import forceHostId
from OPSI.Util import getfqdn, objectToBeautifiedText

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
	sysConfig = {
		'hardwareAddress': None,
	}

	try:
		fqdn = getfqdn(conf=OPSI_GLOBAL_CONF)
		sysConfig['fqdn'] = forceHostId(fqdn)
	except Exception as exc:
		raise RuntimeError(
			u"Failed to get fully qualified domain name: {0}".format(exc)
		)

	sysConfig['hostname'] = fqdn.split(u'.')[0]
	sysConfig['ipAddress'] = socket.gethostbyname(fqdn)

	if sysConfig['ipAddress'].split(u'.')[0] in ('127', '169'):
		sysConfig['ipAddress'] = None

	for device in getEthernetDevices():
		devconf = getNetworkDeviceConfig(device)
		if devconf['ipAddress'] and devconf['ipAddress'].split(u'.')[0] not in ('127', '169'):
			if not sysConfig['ipAddress']:
				sysConfig['ipAddress'] = devconf['ipAddress']

			if sysConfig['ipAddress'] == devconf['ipAddress']:
				sysConfig['netmask'] = devconf['netmask']
				sysConfig['hardwareAddress'] = devconf['hardwareAddress']
				break

	if not sysConfig['ipAddress']:
		raise RuntimeError(
			u"Failed to get a valid ip address for fqdn '{0}'".format(fqdn)
		)

	if not sysConfig.get('netmask'):
		sysConfig['netmask'] = u'255.255.255.0'

	sysConfig['broadcast'] = u''
	sysConfig['subnet'] = u''
	for i in range(4):
		if sysConfig['broadcast']:
			sysConfig['broadcast'] += u'.'
		if sysConfig['subnet']:
			sysConfig['subnet'] += u'.'

		sysConfig['subnet'] += u'%d' % (int(sysConfig['ipAddress'].split(u'.')[i]) & int(sysConfig['netmask'].split(u'.')[i]))
		sysConfig['broadcast'] += u'%d' % (int(sysConfig['ipAddress'].split(u'.')[i]) | int(sysConfig['netmask'].split(u'.')[i]) ^ 255)

	LOGGER.notice(u"System information:")
	LOGGER.notice(u"   ip address   : %s" % sysConfig['ipAddress'])
	LOGGER.notice(u"   netmask      : %s" % sysConfig['netmask'])
	LOGGER.notice(u"   subnet       : %s" % sysConfig['subnet'])
	LOGGER.notice(u"   broadcast    : %s" % sysConfig['broadcast'])
	LOGGER.notice(u"   fqdn         : %s" % sysConfig['fqdn'])
	LOGGER.notice(u"   hostname     : %s" % sysConfig['hostname'])

	return sysConfig
