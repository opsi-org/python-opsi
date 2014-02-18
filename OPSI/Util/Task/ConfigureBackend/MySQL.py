#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
opsi python library - Util - Task - Configure Backend - MySQL

Functionality to automatically configure an OPSI MySQL backend.

.. versionadded:: 4.0.4.6

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""


import codecs
import MySQLdb
import os
import re
import socket

import OPSI.Util.Task.ConfigureBackend as backendUtils
from OPSI.Logger import Logger
from OPSI.Backend.MySQL import MySQLBackend


OPSI_GLOBAL_CONF = u'/etc/opsi/global.conf'

logger = Logger()
sysConfig = {}


class DatabaseConnectionFailedException(Exception):
	pass


def getSysConfig():
	global sysConfig
	if sysConfig:
		return sysConfig

	logger.notice(u"Getting current system config")
	if ipAddress:
		sysConfig['ipAddress'] = ipAddress
	try:
		sysConfig['fqdn'] = forceHostId(getfqdn(conf=OPSI_GLOBAL_CONF))
	except:
		raise Exception(u"Failed to get fully qualified domain name, got '%s'" % getfqdn(conf=OPSI_GLOBAL_CONF))

	sysConfig['hostname'] = sysConfig['fqdn'].split(u'.')[0]
	if 'ipAddress' not in sysConfig:
		sysConfig['ipAddress'] = socket.gethostbyname(sysConfig['fqdn'])
		if sysConfig['ipAddress'].split(u'.')[0] in ('127', '169'):
			sysConfig['ipAddress'] = None
	sysConfig['hardwareAddress'] = None

	for device in getEthernetDevices():
		devconf = getNetworkDeviceConfig(device)
		if devconf['ipAddress'] and devconf['ipAddress'].split(u'.')[0] not in ('127', '169'):
			if not sysConfig['ipAddress']:
				sysConfig['ipAddress'] = devconf['ipAddress']
			if (sysConfig['ipAddress'] == devconf['ipAddress']):
				sysConfig['netmask'] = devconf['netmask']
				sysConfig['hardwareAddress'] = devconf['hardwareAddress']
				break

	if not sysConfig['ipAddress']:
		raise Exception(u"Failed to get a valid ip address for fqdn '%s'" % sysConfig['fqdn'])

	logger.notice(u"System information:")
	logger.notice(u"   ip address   : %s" % sysConfig['ipAddress'])
	logger.notice(u"   fqdn         : %s" % sysConfig['fqdn'])
	logger.notice(u"   hostname     : %s" % sysConfig['hostname'])

	return sysConfig


def configureMySQLBackend(dbAdminUser, dbAdminPass,
	systemConfiguration=None,
	backendConfigFile=u'/etc/opsi/backends/mysql.conf',
	config=None,
	additionalBackendConfig=None,
	notificationFunction=None,
	errorFunction=None):

	if notificationFunction is None:
		notificationFunction = logger.notice

	if errorFunction is None:
		errorFunction = logger.error

	if config is None:
		config = backendUtils.getBackendConfiguration(backendConfigFile)

	if additionalBackendConfig is not None:
		# TODO: in opsi-setup additionalBackendConfig is a global
		# that has some additional backend configuration in it.
		# Check what is needed of it
		config.update(additionalBackendConfig)

	try:
		initializeDatabase(dbAdminUser, dbAdminPass, config, notificationFunction=notificationFunction)
	except DatabaseConnectionFailedException as e:
		errorFunction(u"Failed to connect to host '%s' as user '%s': %s" % (config['address'], dbAdminUser, e))
		raise e
	except Exception as exc:
		errorFunction(exc)
		raise e

	backendUtils.updateConfigFile(backendConfigFile, config, notificationFunction)

	notificationFunction(u"Initializing mysql backend")
	backend = MySQLBackend(**config)
	backend.backend_createBase()


def initializeDatabase(dbAdminUser, dbAdminPass, config, notificationFunction=None, errorFunction=None):

	def createUser(host):
		notificationFunction(u"Creating user '%s' and granting all rights on '%s'" % (config['username'], config['database']))
		db.query(u'USE %s;' % config['database'])
		db.query(u'GRANT ALL ON %s .* TO %s@%s IDENTIFIED BY \'%s\'' \
			% (config['database'], config['username'], host, config['password']))
		db.query(u'FLUSH PRIVILEGES;')
		notificationFunction(u"User '%s' created and privileges set" % config['username'])

	if notificationFunction is None:
		notificationFunction = logger.notice

	if errorFunction is None:
		errorFunction = logger.error

	# Connect to database host
	notificationFunction(u"Connecting to host '%s' as user '%s'" % (config['address'], dbAdminUser))

	try:
		db = MySQLdb.connect(host=config['address'], user=dbAdminUser, passwd=dbAdminPass)
	except Exception as e:
		raise DatabaseConnectionFailedException(e)

	notificationFunction(u"Successfully connected to host '%s' as user '%s'" % (config['address'], dbAdminUser))

	# Create opsi database and user
	notificationFunction(u"Creating database '%s'" % config['database'])
	try:
		db.query(u'CREATE DATABASE %s DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_bin;' % config['database'])
	except MySQLdb.ProgrammingError as e:
		if e[0] != 1007:
			# 1007: database exists
			raise

	notificationFunction(u"Database '%s' created" % config['database'])

	sysconf = getSysConfig()
	if config['address'] in ("localhost", "127.0.0.1", sysconf['hostname'], sysconf['fqdn']):
		createUser("localhost")
		if config['address'] not in ("localhost", "127.0.0.1"):
			createUser(config['address'])
	else:
		createUser(sysConfig['ipAddress'])
		createUser(sysConfig['fqdn'])
		createUser(sysConfig['hostname'])

	# Disconnect from database
	db.close()

	# Test connection / credentials
	notificationFunction(u"Testing connection to database '%s' as user '%s'" % (config['database'], config['username']))

	try:
		db = MySQLdb.connect(host = config['address'], user = config['username'], passwd = config['password'], db = config['database'])
		db.close()
	except Exception as e:
		raise DatabaseConnectionFailedException(e)

	notificationFunction(u"Successfully connected to host '%s' as user '%s'" % (config['address'], config['username']))
