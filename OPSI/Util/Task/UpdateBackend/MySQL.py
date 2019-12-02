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
Functionality to update an MySQL backend.

This module handles the database migrations for opsi.
Usually the function :py:func:updateMySQLBackend: is called from opsi-setup

.. versionadded:: 4.0.6.1

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime

from OPSI.Backend.SQL import DATABASE_SCHEMA_VERSION, createSchemaVersionTable
from OPSI.Backend.MySQL import MySQL, MySQLBackend
from OPSI.Logger import Logger
from OPSI.Types import (
	forceHardwareDeviceId, forceHardwareVendorId, forceLicenseContractId,
	forceSoftwareLicenseId, forceLicensePoolId
)
from OPSI.Util.Task.ConfigureBackend import getBackendConfiguration

from . import BackendUpdateError

__all__ = (
	'DatabaseMigrationUnfinishedError',
	'disableForeignKeyChecks', 'getTableColumns', 'updateMySQLBackend'
)

LOGGER = Logger()


class DatabaseMigrationUnfinishedError(BackendUpdateError):
	"""
	This error indicates an unfinished database migration.
	"""


def updateMySQLBackend(
		backendConfigFile=u'/etc/opsi/backends/mysql.conf',
		additionalBackendConfiguration={}):
	"""
	Applies migrations to the MySQL backend.

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
	LOGGER.info(u"Current mysql backend config: %s" % config)

	LOGGER.notice(u"Connection to database '%s' on '%s' as user '%s'" % (config['database'], config['address'], config['username']))
	mysql = MySQL(**config)

	schemaVersion = readSchemaVersion(mysql)
	LOGGER.debug("Found database schema version {0}", schemaVersion)

	if schemaVersion is None:
		LOGGER.notice("Missing information about database schema. Creating...")
		createSchemaVersionTable(mysql)
		with updateSchemaVersion(mysql, version=0):
			_processOpsi40migrations(mysql)

		schemaVersion = readSchemaVersion(mysql)

	# The migrations that follow are each a function that will take the
	# established database connection as first parameter.
	# Do not change the order of the migrations once released, because
	# this may lead to hard-to-debug inconsistent version numbers.
	migrations = [
		_dropTableBootconfiguration,
		_addIndexOnProductPropertyValues,
		_addWorkbenchAttributesToHosts,
		_adjustLengthOfGroupId,
		_increaseInventoryNumberLength,
		_changeSoftwareConfigConfigIdToBigInt,
	]

	for newSchemaVersion, migration in enumerate(migrations, start=1):
		if schemaVersion < newSchemaVersion:
			with updateSchemaVersion(mysql, version=newSchemaVersion):
				migration(mysql)

	LOGGER.debug("Expected database schema version: {0}", DATABASE_SCHEMA_VERSION)
	if not readSchemaVersion(mysql) == DATABASE_SCHEMA_VERSION:
		raise BackendUpdateError("Not all migrations have been run!")

	with MySQLBackend(**config) as mysqlBackend:
		# We do this to make sure all tables that are currently
		# non-existing will be created. That creation will give them
		# the currently wanted schema.
		mysqlBackend.backend_createBase()


def readSchemaVersion(database):
	"""
	Read the version of the schema from the database.

	:raises DatabaseMigrationNotFinishedError: In case a migration was \
started but never ended.
	:returns: The version of the schema. `None` if no info is found.
	:rtype: int or None
	"""
	try:
		for result in database.getSet(u"SELECT `version`, `updateStarted`, `updateEnded` FROM OPSI_SCHEMA ORDER BY `version` DESC;"):
			version = result['version']
			start = datetime.strptime(result['updateStarted'], '%Y-%m-%d %H:%M:%S')
			assert start

			try:
				end = datetime.strptime(result['updateEnded'], '%Y-%m-%d %H:%M:%S')
				assert end
			except (AssertionError, ValueError):
				raise DatabaseMigrationUnfinishedError(
					"Migration to version {version} started at {start} "
					"but no end time found.".format(version=version, start=start)
				)

			break
		else:
			raise RuntimeError("No schema version read!")
	except DatabaseMigrationUnfinishedError as dbmnfe:
		LOGGER.warning("Migration probably gone wrong: {0}", dbmnfe)
		raise dbmnfe
	except Exception as versionLookupError:
		LOGGER.warning("Reading database schema version failed: {0}", versionLookupError)
		version = None

	return version


@contextmanager
def updateSchemaVersion(database, version):
	"""
	Update the schema information to the given version.

	This is to be used as a context manager and will mark the start
	time of the update aswell as the end time.
	If during the operation something happens there will be no
	information about the end time written to the database.
	"""
	LOGGER.notice("Migrating to schema version {}...", version)
	query = "INSERT INTO OPSI_SCHEMA(`version`) VALUES({version});".format(version=version)
	database.execute(query)
	yield
	_finishSchemaVersionUpdate(database, version)
	LOGGER.notice("Migration to schema version {} successful", version)


def _finishSchemaVersionUpdate(database, version):
	query = "UPDATE OPSI_SCHEMA SET `updateEnded` = CURRENT_TIMESTAMP WHERE VERSION = {version};".format(version=version)
	database.execute(query)


def _processOpsi40migrations(mysql):
	"""
	Process migrations done before opsi 4.1.

	Some of these migrations are used to update an opsi 3 database to
	opsi 4 while some other adjust existing tables to what was required
	during that time.
	"""
	tables = {}
	LOGGER.debug(u"Current tables:")
	for i in mysql.getSet(u'SHOW TABLES;'):
		for tableName in i.values():
			LOGGER.debug(u" [ %s ]" % tableName)
			tables[tableName] = []
			mysql.execute("alter table `%s` convert to charset utf8 collate utf8_general_ci;" % tableName)
			for j in mysql.getSet(u'SHOW COLUMNS FROM `%s`' % tableName):
				LOGGER.debug(u"      %s" % j)
				tables[tableName].append(j['Field'])

	if 'HOST' in tables and 'host_id' in tables['HOST']:
		LOGGER.info(u"Updating database table HOST from opsi 3.3 to 3.4")
		# SOFTWARE_CONFIG
		LOGGER.info(u"Updating table SOFTWARE_CONFIG")
		mysql.execute(u"alter table SOFTWARE_CONFIG add `hostId` varchar(50) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE_CONFIG add `softwareId` varchar(100) NOT NULL;")
		for res in mysql.getSet(u"SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
			mysql.execute(u"update SOFTWARE_CONFIG set `hostId`='%s' where `host_id`=%s;" % (res['hostId'].replace("'", "\\'"), res['host_id']))
		for res in mysql.getSet(u"SELECT softwareId,software_id FROM `SOFTWARE` WHERE `softwareId` != ''"):
			mysql.execute(u"update SOFTWARE_CONFIG set `softwareId`='%s' where `software_id`=%s;" % (res['softwareId'].replace("'", "\\'"), res['software_id']))
		mysql.execute(u"alter table SOFTWARE_CONFIG drop `host_id`;")
		mysql.execute(u"alter table SOFTWARE_CONFIG drop `software_id`;")
		mysql.execute(u"alter table SOFTWARE_CONFIG DEFAULT CHARACTER set utf8;")
		mysql.execute(u"alter table SOFTWARE_CONFIG ENGINE = InnoDB;")

	for key in tables:
		# HARDWARE_CONFIG
		if key.startswith(u'HARDWARE_CONFIG') and 'host_id' in tables[key]:
			LOGGER.info(u"Updating database table %s from opsi 3.3 to 3.4" % key)
			mysql.execute(u"alter table %s add `hostId` varchar(50) NOT NULL;" % key)
			for res in mysql.getSet(u"SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
				mysql.execute(u"update %s set `hostId` = '%s' where `host_id` = %s;" % (key, res['hostId'].replace("'", "\\'"), res['host_id']))
			mysql.execute(u"alter table %s drop `host_id`;" % key)
			mysql.execute(u"alter table %s DEFAULT CHARACTER set utf8;" % key)
			mysql.execute(u"alter table %s ENGINE = InnoDB;" % key)

	if 'HARDWARE_INFO' in tables and 'host_id' in tables['HARDWARE_INFO']:
		LOGGER.info(u"Updating database table HARDWARE_INFO from opsi 3.3 to 3.4")
		# HARDWARE_INFO
		LOGGER.info(u"Updating table HARDWARE_INFO")
		mysql.execute(u"alter table HARDWARE_INFO add `hostId` varchar(50) NOT NULL;")
		for res in mysql.getSet(u"SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
			mysql.execute(u"update HARDWARE_INFO set `hostId` = '%s' where `host_id` = %s;" % (res['hostId'].replace("'", "\\'"), res['host_id']))
		mysql.execute(u"alter table HARDWARE_INFO drop `host_id`;")
		mysql.execute(u"alter table HARDWARE_INFO DEFAULT CHARACTER set utf8;")
		mysql.execute(u"alter table HARDWARE_INFO ENGINE = InnoDB;")

	if 'SOFTWARE' in tables and 'software_id' in tables['SOFTWARE']:
		LOGGER.info(u"Updating database table SOFTWARE from opsi 3.3 to 3.4")
		# SOFTWARE
		LOGGER.info(u"Updating table SOFTWARE")
		# remove duplicates
		mysql.execute("delete S1 from SOFTWARE S1, SOFTWARE S2 where S1.softwareId=S2.softwareId and S1.software_id > S2.software_id")
		mysql.execute(u"alter table SOFTWARE drop `software_id`;")
		mysql.execute(u"alter table SOFTWARE add primary key (`softwareId`);")

	if 'HOST' in tables and 'host_id' in tables['HOST']:
		LOGGER.info(u"Updating database table HOST from opsi 3.3 to 3.4")
		# HOST
		LOGGER.info(u"Updating table HOST")
		# remove duplicates
		mysql.execute("delete H1 from HOST H1, HOST H2 where H1.hostId=H2.hostId and H1.host_id > H2.host_id")
		mysql.execute(u"alter table HOST drop `host_id`;")
		mysql.execute(u"alter table HOST add primary key (`hostId`);")
		mysql.execute(u"alter table HOST add `type` varchar(20);")
		mysql.execute(u"alter table HOST add `description` varchar(100);")
		mysql.execute(u"alter table HOST add `notes` varchar(500);")
		mysql.execute(u"alter table HOST add `hardwareAddress` varchar(17);")
		mysql.execute(u"alter table HOST add `lastSeen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';")
		mysql.execute(u"alter table HOST DEFAULT CHARACTER set utf8;")
		mysql.execute(u"alter table HOST ENGINE = InnoDB;")

		mysql.execute(u"update HOST set `type` = 'OPSI_CLIENT' where `hostId` != '';")

	tables = {}
	LOGGER.debug(u"Current tables:")
	for i in mysql.getSet(u'SHOW TABLES;'):
		for tableName in i.values():
			LOGGER.debug(u" [ %s ]" % tableName)
			tables[tableName] = []
			for j in mysql.getSet(u'SHOW COLUMNS FROM `%s`' % tableName):
				LOGGER.debug(u"      %s" % j)
				tables[tableName].append(j['Field'])

	if 'HOST' in tables and 'depotLocalUrl' not in tables['HOST']:
		LOGGER.info(u"Updating database table HOST from opsi 3.4 to 4.0")
		# HOST
		LOGGER.info(u"Updating table HOST")
		mysql.execute(u"alter table HOST modify `hostId` varchar(255) NOT NULL;")
		mysql.execute(u"alter table HOST modify `type` varchar(30);")

		mysql.execute(u"alter table HOST add `ipAddress` varchar(15);")
		mysql.execute(u"alter table HOST add `inventoryNumber` varchar(30);")
		mysql.execute(u"alter table HOST add `created` TIMESTAMP;")
		mysql.execute(u"alter table HOST add `opsiHostKey` varchar(32);")
		mysql.execute(u"alter table HOST add `oneTimePassword` varchar(32);")
		mysql.execute(u"alter table HOST add `maxBandwidth` int;")
		mysql.execute(u"alter table HOST add `depotLocalUrl` varchar(128);")
		mysql.execute(u"alter table HOST add `depotRemoteUrl` varchar(255);")
		mysql.execute(u"alter table HOST add `depotWebdavUrl` varchar(255);")
		mysql.execute(u"alter table HOST add `repositoryLocalUrl` varchar(128);")
		mysql.execute(u"alter table HOST add `repositoryRemoteUrl` varchar(255);")
		mysql.execute(u"alter table HOST add `networkAddress` varchar(31);")
		mysql.execute(u"alter table HOST add `isMasterDepot` bool;")
		mysql.execute(u"alter table HOST add `masterDepotId` varchar(255);")

		mysql.execute(u"update HOST set `type`='OpsiClient' where `type`='OPSI_CLIENT';")
		mysql.execute(u"update HOST set `description`=NULL where `description`='None';")
		mysql.execute(u"update HOST set `notes`=NULL where `notes`='None';")
		mysql.execute(u"update HOST set `hardwareAddress`=NULL where `hardwareAddress`='None';")

		mysql.execute(u"alter table HOST add INDEX(`type`);")

	for key in tables:
		if key.startswith(u'HARDWARE_DEVICE'):
			if 'vendorId' not in tables[key]:
				continue

			LOGGER.info(u"Updating database table %s" % key)
			for vendorId in ('NDIS', 'SSTP', 'AGIL', 'L2TP', 'PPTP', 'PPPO', 'PTIM'):
				mysql.execute(u"update %s set `vendorId`=NULL where `vendorId`='%s';" % (key, vendorId))

			for attr in ('vendorId', 'deviceId', 'subsystemVendorId', 'subsystemDeviceId'):
				if attr not in tables[key]:
					continue
				mysql.execute(u"update %s set `%s`=NULL where `%s`='';" % (key, attr, attr))
				mysql.execute(u"update %s set `%s`=NULL where `%s`='None';" % (key, attr, attr))

			for res in mysql.getSet(u"SELECT * FROM %s" % key):
				if res.get('vendorId'):
					try:
						forceHardwareVendorId(res['vendorId'])
					except Exception:
						LOGGER.warning(u"Dropping bad vendorId '%s'" % res['vendorId'])
						mysql.execute(u"update %s set `vendorId`=NULL where `vendorId`='%s';" % (key, res['vendorId']))

				if res.get('subsystemVendorId'):
					try:
						forceHardwareVendorId(res['subsystemVendorId'])
					except Exception:
						LOGGER.warning(u"Dropping bad subsystemVendorId id '%s'" % res['subsystemVendorId'])
						mysql.execute(u"update %s set `subsystemVendorId`=NULL where `subsystemVendorId`='%s';" % (key, res['subsystemVendorId']))

				if res.get('deviceId'):
					try:
						forceHardwareDeviceId(res['deviceId'])
					except Exception:
						LOGGER.warning(u"Dropping bad deviceId '%s'" % res['deviceId'])
						mysql.execute(u"update %s set `deviceId`=NULL where `deviceId`='%s';" % (key, res['deviceId']))

				if res.get('subsystemDeviceId'):
					try:
						forceHardwareDeviceId(res['subsystemDeviceId'])
					except Exception:
						LOGGER.warning(u"Dropping bad subsystemDeviceId '%s'" % res['subsystemDeviceId'])
						mysql.execute(u"update %s set `subsystemDeviceId`=NULL where `subsystemDeviceId`='%s';" % (key, res['subsystemDeviceId']))

		# HARDWARE_CONFIG
		if key.startswith(u'HARDWARE_CONFIG') and 'audit_lastseen' in tables[key]:
			LOGGER.info(u"Updating database table %s from opsi 3.4 to 4.0" % key)

			mysql.execute(u"alter table %s change `audit_firstseen` `firstseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';" % key)
			mysql.execute(u"alter table %s change `audit_lastseen` `lastseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';" % key)
			mysql.execute(u"alter table %s change `audit_state` `state` TINYINT NOT NULL;" % key)

	if 'LICENSE_USED_BY_HOST' in tables:
		# LICENSE_ON_CLIENT
		LOGGER.info(u"Updating table LICENSE_USED_BY_HOST to LICENSE_ON_CLIENT")
		mysql.execute(u'''CREATE TABLE `LICENSE_ON_CLIENT` (
					`license_on_client_id` int NOT NULL AUTO_INCREMENT,
					PRIMARY KEY( `license_on_client_id` ),
					`softwareLicenseId` VARCHAR(100) NOT NULL,
					`licensePoolId` VARCHAR(100) NOT NULL,
					`clientId` varchar(255),
					FOREIGN KEY( `softwareLicenseId`, `licensePoolId` ) REFERENCES SOFTWARE_LICENSE_TO_LICENSE_POOL( `softwareLicenseId`, `licensePoolId` ),
					INDEX( `clientId` ),
					`licenseKey` VARCHAR(100),
					`notes` VARCHAR(1024)
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				''')

		mysql.execute(u"insert into LICENSE_ON_CLIENT (`softwareLicenseId`, `licensePoolId`, `clientId`, `licenseKey`, `notes`) select `softwareLicenseId`, `licensePoolId`, `hostId`, `licenseKey`, `notes` from LICENSE_USED_BY_HOST where `softwareLicenseId` != ''")
		mysql.execute(u"drop table LICENSE_USED_BY_HOST")

	if 'SOFTWARE' in tables and 'name' not in tables['SOFTWARE']:
		LOGGER.info(u"Updating database table SOFTWARE from opsi 3.4 to 4.0")
		# SOFTWARE
		LOGGER.info(u"Updating table SOFTWARE")
		mysql.execute(u"alter table SOFTWARE add `name` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `version` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `subVersion` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `language` varchar(10) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `architecture` varchar(3) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `windowsSoftwareId` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `windowsDisplayName` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `windowsDisplayVersion` varchar(100) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE add `type` varchar(30) NOT NULL;")
		for res in mysql.getSet(u"SELECT * FROM `SOFTWARE`"):
			name = res['displayName']
			if not name:
				name = res['softwareId']
			name = name.replace("'", "\\'")

			version = u''
			if res['displayVersion']:
				version = res['displayVersion'].replace("'", "\\'")

			res2 = mysql.getSet(u"SELECT * FROM `SOFTWARE` where `name` = '%s' and version ='%s'" % (name, version))
			if res2:
				LOGGER.warning(u"Skipping duplicate: %s" % res2)
				mysql.execute(u"DELETE FROM `SOFTWARE` where `softwareId` = '%s'" % res['softwareId'].replace("'", "\\'"))
				continue

			update = u"update SOFTWARE set"
			update += u"  `type`='AuditSoftware'"
			update += u", `windowsSoftwareId`='%s'" % res['softwareId'].replace("'", "\\'")
			if res['displayName'] is not None:
				update += u", `windowsDisplayName`='%s'" % res['displayName'].replace("'", "\\'")
			if res['displayVersion'] is not None:
				update += u", `windowsDisplayVersion`='%s'" % res['displayVersion'].replace("'", "\\'")
			update += u", `architecture`='x86'"
			update += u", `language`=''"
			update += u", `name`='%s'" % name
			update += u", `version`='%s'" % version
			update += u", `subVersion`=''"
			update += u" where `softwareId`='%s';" % res['softwareId'].replace("'", "\\'")
			mysql.execute(update)

		mysql.execute(u"alter table SOFTWARE drop PRIMARY KEY;")
		mysql.execute(u"alter table SOFTWARE add PRIMARY KEY ( `name`, `version`, `subVersion`, `language`, `architecture` );")
		mysql.execute(u"alter table SOFTWARE drop `softwareId`;")
		mysql.execute(u"alter table SOFTWARE drop `displayName`;")
		mysql.execute(u"alter table SOFTWARE drop `displayVersion`;")
		mysql.execute(u"alter table SOFTWARE drop `uninstallString`;")
		mysql.execute(u"alter table SOFTWARE drop `binaryName`;")

		mysql.execute(u"alter table SOFTWARE add INDEX( `windowsSoftwareId` );")
		mysql.execute(u"alter table SOFTWARE add INDEX( `type` );")

	if 'SOFTWARE_CONFIG' in tables and 'clientId' not in tables['SOFTWARE_CONFIG']:
		LOGGER.info(u"Updating database table SOFTWARE_CONFIG from opsi 3.4 to 4.0")
		# SOFTWARE_CONFIG
		LOGGER.info(u"Updating table SOFTWARE_CONFIG")

		mysql.execute(u"alter table SOFTWARE_CONFIG 	change `hostId` `clientId` varchar(255) NOT NULL, \
				add `name` varchar(100) NOT NULL, \
				add `version` varchar(100) NOT NULL, \
				add `subVersion` varchar(100) NOT NULL, \
				add `language` varchar(10) NOT NULL, \
				add `architecture` varchar(3) NOT NULL, \
				add `uninstallString` varchar(200), \
				add `binaryName` varchar(100), \
				change `audit_firstseen` `firstseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', \
				change `audit_lastseen` `lastseen` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00', \
				change `audit_state` `state` TINYINT NOT NULL, \
				add `licenseKey` varchar(100), \
				add INDEX( `clientId` ), \
				add INDEX( `name`, `version`, `subVersion`, `language`, `architecture` );")

		mysql.execute(u"UPDATE SOFTWARE_CONFIG as sc \
				LEFT JOIN (select windowsSoftwareId, name, version, subVersion, language, architecture from SOFTWARE group by windowsSoftwareId) \
				as s on s.windowsSoftwareId = sc.softwareId \
				set sc.name = s.name, sc.version = s.version, sc.subVersion = s.subVersion, sc.architecture = s.architecture \
				where s.windowsSoftwareId is not null;")

		mysql.execute(u"delete from SOFTWARE_CONFIG where `name` = '';")
		mysql.execute(u"alter table SOFTWARE_CONFIG drop `softwareId`;")

	if 'LICENSE_CONTRACT' in tables and 'type' not in tables['LICENSE_CONTRACT']:
		LOGGER.info(u"Updating database table LICENSE_CONTRACT from opsi 3.4 to 4.0")
		# LICENSE_CONTRACT
		mysql.execute(u"alter table LICENSE_CONTRACT add `type` varchar(30) NOT NULL;")
		mysql.execute(u"alter table LICENSE_CONTRACT add `description` varchar(100) NOT NULL;")
		mysql.execute(u"alter table LICENSE_CONTRACT modify `conclusionDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';")
		mysql.execute(u"alter table LICENSE_CONTRACT modify `notificationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';")
		mysql.execute(u"alter table LICENSE_CONTRACT modify `expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';")
		mysql.execute(u"update LICENSE_CONTRACT set `type`='LicenseContract' where 1=1")

		mysql.execute(u"alter table LICENSE_CONTRACT add INDEX( `type` );")

	if 'SOFTWARE_LICENSE' in tables and 'type' not in tables['SOFTWARE_LICENSE']:
		LOGGER.info(u"Updating database table SOFTWARE_LICENSE from opsi 3.4 to 4.0")
		# SOFTWARE_LICENSE
		mysql.execute(u"alter table SOFTWARE_LICENSE add `type` varchar(30) NOT NULL;")
		mysql.execute(u"alter table SOFTWARE_LICENSE modify `expirationDate` TIMESTAMP NOT NULL DEFAULT '0000-00-00 00:00:00';")
		mysql.execute(u"alter table SOFTWARE_LICENSE modify `boundToHost` varchar(255);")
		mysql.execute(u"update SOFTWARE_LICENSE set `type`='RetailSoftwareLicense' where `licenseType`='RETAIL'")
		mysql.execute(u"update SOFTWARE_LICENSE set `type`='OEMSoftwareLicense' where `licenseType`='OEM'")
		mysql.execute(u"update SOFTWARE_LICENSE set `type`='VolumeSoftwareLicense' where `licenseType`='VOLUME'")
		mysql.execute(u"update SOFTWARE_LICENSE set `type`='ConcurrentSoftwareLicense' where `licenseType`='CONCURRENT'")
		mysql.execute(u"alter table SOFTWARE_LICENSE drop `licenseType`;")

		mysql.execute(u"alter table SOFTWARE_LICENSE add INDEX( `type` );")
		mysql.execute(u"alter table SOFTWARE_LICENSE add INDEX( `boundToHost` );")

	if 'LICENSE_POOL' in tables and 'type' not in tables['LICENSE_POOL']:
		LOGGER.info(u"Updating database table LICENSE_POOL from opsi 3.4 to 4.0")
		# LICENSE_POOL
		mysql.execute(u"alter table LICENSE_POOL add `type` varchar(30) NOT NULL;")
		mysql.execute(u"update LICENSE_POOL set `type`='LicensePool' where 1=1")

		mysql.execute(u"alter table LICENSE_POOL add INDEX( `type` );")

	if 'WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL' in tables:
		# AUDIT_SOFTWARE_TO_LICENSE_POOL
		LOGGER.info(u"Updating table WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL to AUDIT_SOFTWARE_TO_LICENSE_POOL")

		mysql.execute(u'''CREATE TABLE `AUDIT_SOFTWARE_TO_LICENSE_POOL` (
					`licensePoolId` VARCHAR(100) NOT NULL,
					FOREIGN KEY ( `licensePoolId` ) REFERENCES LICENSE_POOL( `licensePoolId` ),
					`name` varchar(100) NOT NULL,
					`version` varchar(100) NOT NULL,
					`subVersion` varchar(100) NOT NULL,
					`language` varchar(10) NOT NULL,
					`architecture` varchar(3) NOT NULL,
					PRIMARY KEY( `name`, `version`, `subVersion`, `language`, `architecture` )
				) ENGINE=InnoDB DEFAULT CHARSET=utf8;
				''')

		for res in mysql.getSet(u"SELECT * FROM `WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL`"):
			res2 = mysql.getSet(u"SELECT * FROM `SOFTWARE` where `windowsSoftwareId` = '%s'" % res['windowsSoftwareId'].replace("'", "\\'"))
			if not res2:
				continue
			res2 = res2[0]
			mysql.execute(u"insert into AUDIT_SOFTWARE_TO_LICENSE_POOL (`licensePoolId`, `name`, `version`, `subVersion`, `language`, `architecture`) VALUES ('%s', '%s', '%s', '%s', '%s', '%s');"
				% (res['licensePoolId'], res2['name'].replace("'", "\\'"), res2['version'].replace("'", "\\'"), res2['subVersion'].replace("'", "\\'"), res2['language'], res2['architecture']))

		mysql.execute(u"drop table WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL;")

	for res in mysql.getSet(u"SELECT * FROM `LICENSE_CONTRACT`"):
		if res['licenseContractId'] != forceLicenseContractId(res['licenseContractId']):
			deleteLicenseContractId = res['licenseContractId']
			res['licenseContractId'] = forceLicenseContractId(res['licenseContractId'])
			LOGGER.warning(u"Changing license contract id '%s' to '%s'" % (deleteLicenseContractId, res['licenseContractId']))

			data = {
				'SOFTWARE_LICENSE': [],
				'LICENSE_ON_CLIENT': [],
				'SOFTWARE_LICENSE_TO_LICENSE_POOL': []
			}
			for res2 in mysql.getSet(u"SELECT * FROM `SOFTWARE_LICENSE` where licenseContractId = '%s'" % deleteLicenseContractId):
				res2['licenseContractId'] = res['licenseContractId']
				data['SOFTWARE_LICENSE'].append(res2)
				for tab in ('LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
					for res3 in mysql.getSet(u"SELECT * FROM `%s` where softwareLicenseId = '%s'" % (tab, res2['softwareLicenseId'])):
						data[tab].append(res3)
					mysql.delete(tab, "softwareLicenseId = '%s'" % res2['softwareLicenseId'])
			mysql.delete('SOFTWARE_LICENSE', "licenseContractId = '%s'" % deleteLicenseContractId)
			mysql.delete('LICENSE_CONTRACT', "licenseContractId = '%s'" % deleteLicenseContractId)
			mysql.insert('LICENSE_CONTRACT', res)
			for tab in ('SOFTWARE_LICENSE', 'SOFTWARE_LICENSE_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT'):
				for i in data[tab]:
					mysql.insert(tab, i)

	for res in mysql.getSet(u"SELECT * FROM `LICENSE_POOL`"):
		if (res['licensePoolId'] != res['licensePoolId'].strip()) or (res['licensePoolId'] != forceLicensePoolId(res['licensePoolId'])):
			deleteLicensePoolId = res['licensePoolId']
			res['licensePoolId'] = forceLicensePoolId(res['licensePoolId'].strip())
			LOGGER.warning(u"Changing license pool id '%s' to '%s'" % (deleteLicensePoolId, res['licensePoolId']))

			data = {}
			for tab in ('AUDIT_SOFTWARE_TO_LICENSE_POOL', 'PRODUCT_ID_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
				data[tab] = []
				for res2 in mysql.getSet(u"SELECT * FROM `%s` where licensePoolId = '%s'" % (tab, deleteLicensePoolId)):
					res2['licensePoolId'] = res['licensePoolId']
					data[tab].append(res2)
				mysql.delete(tab, "licensePoolId = '%s'" % deleteLicensePoolId)

			mysql.delete('LICENSE_POOL', "licensePoolId = '%s'" % deleteLicensePoolId)
			mysql.insert('LICENSE_POOL', res)
			for tab in ('AUDIT_SOFTWARE_TO_LICENSE_POOL', 'PRODUCT_ID_TO_LICENSE_POOL', 'SOFTWARE_LICENSE_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT'):
				for i in data[tab]:
					mysql.insert(tab, i)

	for res in mysql.getSet(u"SELECT * FROM `SOFTWARE_LICENSE`"):
		if (res['softwareLicenseId'] != res['softwareLicenseId'].strip()) or (res['softwareLicenseId'] != forceSoftwareLicenseId(res['softwareLicenseId'])):
			deleteSoftwareLicenseId = res['softwareLicenseId']
			res['softwareLicenseId'] = forceSoftwareLicenseId(res['softwareLicenseId'].strip())
			LOGGER.warning(u"Changing software license id '%s' to '%s'" % (deleteSoftwareLicenseId, res['softwareLicenseId']))

			data = {}
			for tab in ('LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
				data[tab] = []
				for res2 in mysql.getSet(u"SELECT * FROM `%s` where softwareLicenseId = '%s'" % (tab, deleteSoftwareLicenseId)):
					res2['softwareLicenseId'] = res['softwareLicenseId']
					data[tab].append(res2)
				mysql.delete(tab, "softwareLicenseId = '%s'" % deleteSoftwareLicenseId)

			mysql.delete('SOFTWARE_LICENSE', "softwareLicenseId = '%s'" % deleteSoftwareLicenseId)
			mysql.insert('SOFTWARE_LICENSE', res)
			for tab in ('SOFTWARE_LICENSE_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT'):
				for i in data[tab]:
					mysql.insert(tab, i)

	# Increase productId Fields on existing database:
	with disableForeignKeyChecks(mysql):
		LOGGER.info(u"Updating productId Columns")
		for line in mysql.getSet(u"SHOW TABLES;"):
			for tableName in line.values():
				LOGGER.debug(u" [ %s ]" % tableName)
				for column in mysql.getSet(u'SHOW COLUMNS FROM `%s`;' % tableName):
					fieldName = column['Field']
					fieldType = column['Type']
					if "productid" in fieldName.lower() and fieldType != "varchar(255)":
						LOGGER.debug("ALTER TABLE for Table: '%s' and Column: '%s'" % (tableName, fieldName))
						mysql.execute(u"alter table %s MODIFY COLUMN `%s` VARCHAR(255);" % (tableName, fieldName))

	# Changing description fields to type TEXT
	for tableName in (u"PRODUCT_PROPERTY", ):
		LOGGER.info(u"Updating field 'description' on table {name}".format(name=tableName))
		fieldName = u"description"
		mysql.execute(
			u"alter table {name} MODIFY COLUMN `{column}` TEXT;".format(
				name=tableName,
				column=fieldName
			)
		)

	# Fixing unwanted MySQL defaults:
	if 'HOST' in tables:
		LOGGER.info(u"Fixing DEFAULT for colum 'created' on table HOST")
		mysql.execute(u"alter table HOST modify `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

	# Changing the length of too small hostId / depotId column
	def tableNeedsHostIDLengthFix(table, columnName="hostId"):
		for column in mysql.getSet(u'SHOW COLUMNS FROM `{0}`;'.format(table)):
			if column['Field'] != columnName:
				continue

			if column['Type'].lower() != "varchar(255)":
				return True

		return False

	with disableForeignKeyChecks(mysql):
		for tablename in tables:
			if tablename == 'PRODUCT_ON_DEPOT' and tableNeedsHostIDLengthFix(tablename, columnName="depotId"):
				LOGGER.info(u"Fixing length of 'depotId' column on {table}".format(table=tablename))
				mysql.execute(u"ALTER TABLE `PRODUCT_ON_DEPOT` MODIFY COLUMN `depotId` VARCHAR(255) NOT NULL;")
			elif tablename.startswith(u'HARDWARE_CONFIG') and tableNeedsHostIDLengthFix(tablename):
				LOGGER.info(u"Fixing length of 'hostId' column on {table}".format(table=tablename))
				mysql.execute(u"ALTER TABLE `{table}` MODIFY COLUMN `hostId` VARCHAR(255) NOT NULL;".format(table=tablename))

	_fixLengthOfLicenseKeys(mysql)


@contextmanager
def disableForeignKeyChecks(database):
	"""
	Disable checks for foreign keys in context and enable afterwards.

	This will disable FOREIGN_KEY_CHECKS for the context and enable
	them afterwards.
	It will set this per session, not global.
	"""
	database.execute('SET FOREIGN_KEY_CHECKS=0;')
	LOGGER.debug("Disabled FOREIGN_KEY_CHECKS for session.")
	try:
		yield
	finally:
		database.execute('SET FOREIGN_KEY_CHECKS=1;')
		LOGGER.debug("Enabled FOREIGN_KEY_CHECKS for session.")


def _fixLengthOfLicenseKeys(database):
	"Correct the length of license key columns to be consistent."

	relevantTables = (
		'LICENSE_ON_CLIENT', 'SOFTWARE_CONFIG',
		'SOFTWARE_LICENSE_TO_LICENSE_POOL'
	)

	for table in relevantTables:
		for column in getTableColumns(database, table):
			if column.name == 'licenseKey':
				assert column.type.lower().startswith('varchar(')

				_, length = column.type.split('(')
				length = int(length[:-1])

				if length != 1024:
					LOGGER.info(u"Fixing length of 'licenseKey' column on table {0!r}".format(table))
					database.execute(u"ALTER TABLE `{0}` MODIFY COLUMN `licenseKey` VARCHAR(1024);".format(table))


def getTableColumns(database, tableName):
	TableColumn = namedtuple("TableColumn", ["name", "type"])
	return [TableColumn(column['Field'], column['Type']) for column
			in database.getSet(u'SHOW COLUMNS FROM `{0}`;'.format(tableName))]


def _dropTableBootconfiguration(database):
	LOGGER.info(u"Dropping table BOOT_CONFIGURATION.")
	database.execute(u"drop table BOOT_CONFIGURATION;")


def _addIndexOnProductPropertyValues(database):
	LOGGER.info("Adding index on table PRODUCT_PROPERTY_VALUE.")
	database.execute('''
		CREATE INDEX `index_product_property_value` on
		`PRODUCT_PROPERTY_VALUE`
		(`productId`, `propertyId`, `productVersion`, `packageVersion`);''')


def _addWorkbenchAttributesToHosts(database):
	LOGGER.info("Adding column 'workbenchLocalUrl' on table HOST.")
	database.execute('ALTER TABLE `HOST` add `workbenchLocalUrl` varchar(128);')

	LOGGER.info("Adding column 'workbenchRemoteUrl' on table HOST.")
	database.execute('ALTER TABLE `HOST` add `workbenchRemoteUrl` varchar(255);')


def _adjustLengthOfGroupId(database):
	LOGGER.info("Correcting length of column 'groupId' on table OBJECT_TO_GROUP")
	database.execute(
		'ALTER TABLE `OBJECT_TO_GROUP` '
		'MODIFY COLUMN `groupId` varchar(255) NOT NULL;'
	)


def _increaseInventoryNumberLength(database):
	LOGGER.info("Correcting length of column 'groupId' on table OBJECT_TO_GROUP")
	database.execute(
		'ALTER TABLE `HOST` '
		'MODIFY COLUMN `inventoryNumber` varchar(64) NOT NULL;'
	)


def _changeSoftwareConfigConfigIdToBigInt(database):
	LOGGER.info("Changing the type of SOFTWARE_CONFIG.config_id to bigint")
	database.execute("ALTER TABLE `SOFTWARE_CONFIG` MODIFY COLUMN `config_id` bigint auto_increment;")
