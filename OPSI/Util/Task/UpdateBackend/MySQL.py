# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Functionality to update an MySQL backend.

This module handles the database migrations for opsi.
Usually the function :py:func:updateMySQLBackend: is called from opsi-setup

.. versionadded:: 4.0.6.1
"""

from __future__ import absolute_import

from collections import namedtuple
from contextlib import contextmanager

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

logger = Logger()


class DatabaseMigrationUnfinishedError(BackendUpdateError):
	"""
	This error indicates an unfinished database migration.
	"""


def updateMySQLBackend(
	backendConfigFile='/etc/opsi/backends/mysql.conf',
	additionalBackendConfiguration=None
):
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
	additionalBackendConfiguration = additionalBackendConfiguration or {}

	config = getBackendConfiguration(backendConfigFile)
	config.update(additionalBackendConfiguration)
	logger.info("Current mysql backend config: %s", config)

	logger.notice(
		"Connection to database '%s' on '%s' as user '%s'",
		config['database'], config['address'], config['username']
	)
	mysql = MySQL(**config)

	schemaVersion = readSchemaVersion(mysql)
	logger.debug("Found database schema version %s", schemaVersion)

	if schemaVersion is None:
		logger.notice("Missing information about database schema. Creating...")
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
		_addIndexProductIdOnProductAndWindowsSoftwareIDToProduct
	]

	for newSchemaVersion, migration in enumerate(migrations, start=1):
		if schemaVersion < newSchemaVersion:
			with updateSchemaVersion(mysql, version=newSchemaVersion):
				migration(mysql)

	logger.debug("Expected database schema version: %s", DATABASE_SCHEMA_VERSION)
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
		for result in database.getSet("SELECT `version`, `updateStarted`, `updateEnded` FROM OPSI_SCHEMA ORDER BY `version` DESC;"):
			version = result['version']
			start = result['updateStarted']
			assert start

			try:
				end = result['updateEnded']
				assert end
			except (AssertionError, ValueError) as err:
				raise DatabaseMigrationUnfinishedError(
					"Migration to version {version} started at {start} "
					"but no end time found.".format(version=version, start=start)
				) from err

			break
		else:
			raise RuntimeError("No schema version read!")
	except DatabaseMigrationUnfinishedError as err:
		logger.warning("Migration probably gone wrong: %s", err)
		raise err
	except Exception as err:  # pylint: disable=broad-except
		logger.warning("Reading database schema version failed: %s", err)
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
	logger.notice("Migrating to schema version %s...", version)
	query = "INSERT INTO OPSI_SCHEMA(`version`) VALUES({version});".format(version=version)
	database.execute(query)
	yield
	_finishSchemaVersionUpdate(database, version)
	logger.notice("Migration to schema version %s successful", version)


def _finishSchemaVersionUpdate(database, version):
	query = "UPDATE OPSI_SCHEMA SET `updateEnded` = CURRENT_TIMESTAMP WHERE VERSION = {version};".format(version=version)
	database.execute(query)


def _processOpsi40migrations(mysql):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
	"""
	Process migrations done before opsi 4.1.

	Some of these migrations are used to update an opsi 3 database to
	opsi 4 while some other adjust existing tables to what was required
	during that time.
	"""
	tables = {}
	logger.debug("Current tables:")
	for i in mysql.getSet('SHOW TABLES;'):
		for tableName in i.values():
			logger.debug(" [ %s ]", tableName)
			tables[tableName] = []
			mysql.execute("alter table `%s` convert to charset utf8 collate utf8_general_ci;" % tableName)
			for row in mysql.getSet('SHOW COLUMNS FROM `%s`' % tableName):
				logger.debug("      %s", row)
				tables[tableName].append(row['Field'])

	if 'HOST' in tables and 'host_id' in tables['HOST']:
		logger.info("Updating database table HOST from opsi 3.3 to 3.4")
		# SOFTWARE_CONFIG
		logger.info("Updating table SOFTWARE_CONFIG")
		mysql.execute("alter table SOFTWARE_CONFIG add `hostId` varchar(50) NOT NULL;")
		mysql.execute("alter table SOFTWARE_CONFIG add `softwareId` varchar(100) NOT NULL;")
		for res in mysql.getSet("SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
			mysql.execute(
				"update SOFTWARE_CONFIG set `hostId`='%s' where `host_id`=%s;" % \
				(res['hostId'].replace("'", "\\'"), res['host_id'])
			)
		for res in mysql.getSet("SELECT softwareId,software_id FROM `SOFTWARE` WHERE `softwareId` != ''"):
			mysql.execute(
				"update SOFTWARE_CONFIG set `softwareId`='%s' where `software_id`=%s;" % \
				(res['softwareId'].replace("'", "\\'"), res['software_id'])
			)
		mysql.execute("alter table SOFTWARE_CONFIG drop `host_id`;")
		mysql.execute("alter table SOFTWARE_CONFIG drop `software_id`;")
		mysql.execute("alter table SOFTWARE_CONFIG DEFAULT CHARACTER set utf8;")
		mysql.execute("alter table SOFTWARE_CONFIG ENGINE = InnoDB;")

	for key in tables:
		# HARDWARE_CONFIG
		if key.startswith('HARDWARE_CONFIG') and 'host_id' in tables[key]:
			logger.info("Updating database table %s from opsi 3.3 to 3.4", key)
			mysql.execute("alter table %s add `hostId` varchar(50) NOT NULL;" % key)
			for res in mysql.getSet("SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
				mysql.execute("update %s set `hostId` = '%s' where `host_id` = %s;" % (key, res['hostId'].replace("'", "\\'"), res['host_id']))
			mysql.execute("alter table %s drop `host_id`;" % key)
			mysql.execute("alter table %s DEFAULT CHARACTER set utf8;" % key)
			mysql.execute("alter table %s ENGINE = InnoDB;" % key)

	if 'HARDWARE_INFO' in tables and 'host_id' in tables['HARDWARE_INFO']:
		logger.info("Updating database table HARDWARE_INFO from opsi 3.3 to 3.4")
		# HARDWARE_INFO
		logger.info("Updating table HARDWARE_INFO")
		mysql.execute("alter table HARDWARE_INFO add `hostId` varchar(50) NOT NULL;")
		for res in mysql.getSet("SELECT hostId,host_id FROM `HOST` WHERE `hostId` != ''"):
			mysql.execute("update HARDWARE_INFO set `hostId` = '%s' where `host_id` = %s;" % (res['hostId'].replace("'", "\\'"), res['host_id']))
		mysql.execute("alter table HARDWARE_INFO drop `host_id`;")
		mysql.execute("alter table HARDWARE_INFO DEFAULT CHARACTER set utf8;")
		mysql.execute("alter table HARDWARE_INFO ENGINE = InnoDB;")

	if 'SOFTWARE' in tables and 'software_id' in tables['SOFTWARE']:
		logger.info("Updating database table SOFTWARE from opsi 3.3 to 3.4")
		# SOFTWARE
		logger.info("Updating table SOFTWARE")
		# remove duplicates
		mysql.execute("delete S1 from SOFTWARE S1, SOFTWARE S2 where S1.softwareId=S2.softwareId and S1.software_id > S2.software_id")
		mysql.execute("alter table SOFTWARE drop `software_id`;")
		mysql.execute("alter table SOFTWARE add primary key (`softwareId`);")

	if 'HOST' in tables and 'host_id' in tables['HOST']:
		logger.info("Updating database table HOST from opsi 3.3 to 3.4")
		# HOST
		logger.info("Updating table HOST")
		# remove duplicates
		mysql.execute("delete H1 from HOST H1, HOST H2 where H1.hostId=H2.hostId and H1.host_id > H2.host_id")
		mysql.execute("alter table HOST drop `host_id`;")
		mysql.execute("alter table HOST add primary key (`hostId`);")
		mysql.execute("alter table HOST add `type` varchar(20);")
		mysql.execute("alter table HOST add `description` varchar(100);")
		mysql.execute("alter table HOST add `notes` varchar(500);")
		mysql.execute("alter table HOST add `hardwareAddress` varchar(17);")
		mysql.execute("alter table HOST add `lastSeen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;")
		mysql.execute("alter table HOST DEFAULT CHARACTER set utf8;")
		mysql.execute("alter table HOST ENGINE = InnoDB;")

		mysql.execute("update HOST set `type` = 'OPSI_CLIENT' where `hostId` != '';")

	tables = {}
	logger.debug("Current tables:")
	for i in mysql.getSet('SHOW TABLES;'):
		for tableName in i.values():
			logger.debug(" [ %s ]", tableName)
			tables[tableName] = []
			for row in mysql.getSet('SHOW COLUMNS FROM `%s`' % tableName):
				logger.debug("      %s", row)
				tables[tableName].append(row['Field'])

	if 'HOST' in tables and 'depotLocalUrl' not in tables['HOST']:
		logger.info("Updating database table HOST from opsi 3.4 to 4.0")
		# HOST
		logger.info("Updating table HOST")
		mysql.execute("alter table HOST modify `hostId` varchar(255) NOT NULL;")
		mysql.execute("alter table HOST modify `type` varchar(30);")

		mysql.execute("alter table HOST add `ipAddress` varchar(15);")
		mysql.execute("alter table HOST add `inventoryNumber` varchar(30);")
		mysql.execute("alter table HOST add `created` TIMESTAMP;")
		mysql.execute("alter table HOST add `opsiHostKey` varchar(32);")
		mysql.execute("alter table HOST add `oneTimePassword` varchar(32);")
		mysql.execute("alter table HOST add `maxBandwidth` int;")
		mysql.execute("alter table HOST add `depotLocalUrl` varchar(128);")
		mysql.execute("alter table HOST add `depotRemoteUrl` varchar(255);")
		mysql.execute("alter table HOST add `depotWebdavUrl` varchar(255);")
		mysql.execute("alter table HOST add `repositoryLocalUrl` varchar(128);")
		mysql.execute("alter table HOST add `repositoryRemoteUrl` varchar(255);")
		mysql.execute("alter table HOST add `networkAddress` varchar(31);")
		mysql.execute("alter table HOST add `isMasterDepot` bool;")
		mysql.execute("alter table HOST add `masterDepotId` varchar(255);")

		mysql.execute("update HOST set `type`='OpsiClient' where `type`='OPSI_CLIENT';")
		mysql.execute("update HOST set `description`=NULL where `description`='None';")
		mysql.execute("update HOST set `notes`=NULL where `notes`='None';")
		mysql.execute("update HOST set `hardwareAddress`=NULL where `hardwareAddress`='None';")

		mysql.execute("alter table HOST add INDEX(`type`);")

	for key in tables:
		if key.startswith('HARDWARE_DEVICE'):
			if 'vendorId' not in tables[key]:
				continue

			logger.info("Updating database table %s", key)
			for vendorId in ('NDIS', 'SSTP', 'AGIL', 'L2TP', 'PPTP', 'PPPO', 'PTIM'):
				mysql.execute("update %s set `vendorId`=NULL where `vendorId`='%s';" % (key, vendorId))

			for attr in ('vendorId', 'deviceId', 'subsystemVendorId', 'subsystemDeviceId'):
				if attr not in tables[key]:
					continue
				mysql.execute("update %s set `%s`=NULL where `%s`='';" % (key, attr, attr))
				mysql.execute("update %s set `%s`=NULL where `%s`='None';" % (key, attr, attr))

			for res in mysql.getSet("SELECT * FROM %s" % key):
				if res.get('vendorId'):
					try:
						forceHardwareVendorId(res['vendorId'])
					except Exception:  # pylint: disable=broad-except
						logger.warning("Dropping bad vendorId '%s'", res['vendorId'])
						mysql.execute("update %s set `vendorId`=NULL where `vendorId`='%s';" % (key, res['vendorId']))

				if res.get('subsystemVendorId'):
					try:
						forceHardwareVendorId(res['subsystemVendorId'])
					except Exception:  # pylint: disable=broad-except
						logger.warning("Dropping bad subsystemVendorId id '%s'", res['subsystemVendorId'])
						mysql.execute("update %s set `subsystemVendorId`=NULL where `subsystemVendorId`='%s';" % (key, res['subsystemVendorId']))

				if res.get('deviceId'):
					try:
						forceHardwareDeviceId(res['deviceId'])
					except Exception:  # pylint: disable=broad-except
						logger.warning("Dropping bad deviceId '%s'", res['deviceId'])
						mysql.execute("update %s set `deviceId`=NULL where `deviceId`='%s';" % (key, res['deviceId']))

				if res.get('subsystemDeviceId'):
					try:
						forceHardwareDeviceId(res['subsystemDeviceId'])
					except Exception:  # pylint: disable=broad-except
						logger.warning("Dropping bad subsystemDeviceId '%s'", res['subsystemDeviceId'])
						mysql.execute("update %s set `subsystemDeviceId`=NULL where `subsystemDeviceId`='%s';" % (key, res['subsystemDeviceId']))

		# HARDWARE_CONFIG
		if key.startswith('HARDWARE_CONFIG') and 'audit_lastseen' in tables[key]:
			logger.info("Updating database table %s from opsi 3.4 to 4.0", key)

			mysql.execute("alter table %s change `audit_firstseen` `firstseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;" % key)
			mysql.execute("alter table %s change `audit_lastseen` `lastseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;" % key)
			mysql.execute("alter table %s change `audit_state` `state` TINYINT NOT NULL;" % key)

	if 'LICENSE_USED_BY_HOST' in tables:
		# LICENSE_ON_CLIENT
		logger.info("Updating table LICENSE_USED_BY_HOST to LICENSE_ON_CLIENT")
		mysql.execute('''CREATE TABLE `LICENSE_ON_CLIENT` (
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

		mysql.execute('''
			insert into LICENSE_ON_CLIENT (`softwareLicenseId`, `licensePoolId`, `clientId`, `licenseKey`, `notes`)
			select `softwareLicenseId`, `licensePoolId`, `hostId`, `licenseKey`, `notes`
			from LICENSE_USED_BY_HOST where `softwareLicenseId` != ''
		''')
		mysql.execute("drop table LICENSE_USED_BY_HOST")

	if 'SOFTWARE' in tables and 'name' not in tables['SOFTWARE']:
		logger.info("Updating database table SOFTWARE from opsi 3.4 to 4.0")
		# SOFTWARE
		logger.info("Updating table SOFTWARE")
		mysql.execute("alter table SOFTWARE add `name` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `version` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `subVersion` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `language` varchar(10) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `architecture` varchar(3) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `windowsSoftwareId` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `windowsDisplayName` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `windowsDisplayVersion` varchar(100) NOT NULL;")
		mysql.execute("alter table SOFTWARE add `type` varchar(30) NOT NULL;")
		for res in mysql.getSet("SELECT * FROM `SOFTWARE`"):
			name = res['displayName']
			if not name:
				name = res['softwareId']
			name = name.replace("'", "\\'")

			version = ''
			if res['displayVersion']:
				version = res['displayVersion'].replace("'", "\\'")

			res2 = mysql.getSet("SELECT * FROM `SOFTWARE` where `name` = '%s' and version ='%s'" % (name, version))
			if res2:
				logger.warning("Skipping duplicate: %s", res2)
				mysql.execute("DELETE FROM `SOFTWARE` where `softwareId` = '%s'" % res['softwareId'].replace("'", "\\'"))
				continue

			update = "update SOFTWARE set"
			update += "  `type`='AuditSoftware'"
			update += ", `windowsSoftwareId`='%s'" % res['softwareId'].replace("'", "\\'")
			if res['displayName'] is not None:
				update += ", `windowsDisplayName`='%s'" % res['displayName'].replace("'", "\\'")
			if res['displayVersion'] is not None:
				update += ", `windowsDisplayVersion`='%s'" % res['displayVersion'].replace("'", "\\'")
			update += ", `architecture`='x86'"
			update += ", `language`=''"
			update += ", `name`='%s'" % name
			update += ", `version`='%s'" % version
			update += ", `subVersion`=''"
			update += " where `softwareId`='%s';" % res['softwareId'].replace("'", "\\'")
			mysql.execute(update)

		mysql.execute("alter table SOFTWARE drop PRIMARY KEY;")
		mysql.execute("alter table SOFTWARE add PRIMARY KEY ( `name`, `version`, `subVersion`, `language`, `architecture` );")
		mysql.execute("alter table SOFTWARE drop `softwareId`;")
		mysql.execute("alter table SOFTWARE drop `displayName`;")
		mysql.execute("alter table SOFTWARE drop `displayVersion`;")
		mysql.execute("alter table SOFTWARE drop `uninstallString`;")
		mysql.execute("alter table SOFTWARE drop `binaryName`;")

		mysql.execute("alter table SOFTWARE add INDEX( `windowsSoftwareId` );")
		mysql.execute("alter table SOFTWARE add INDEX( `type` );")

	if 'SOFTWARE_CONFIG' in tables and 'clientId' not in tables['SOFTWARE_CONFIG']:
		logger.info("Updating database table SOFTWARE_CONFIG from opsi 3.4 to 4.0")
		# SOFTWARE_CONFIG
		logger.info("Updating table SOFTWARE_CONFIG")

		mysql.execute("alter table SOFTWARE_CONFIG 	change `hostId` `clientId` varchar(255) NOT NULL, \
				add `name` varchar(100) NOT NULL, \
				add `version` varchar(100) NOT NULL, \
				add `subVersion` varchar(100) NOT NULL, \
				add `language` varchar(10) NOT NULL, \
				add `architecture` varchar(3) NOT NULL, \
				add `uninstallString` varchar(200), \
				add `binaryName` varchar(100), \
				change `audit_firstseen` `firstseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, \
				change `audit_lastseen` `lastseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, \
				change `audit_state` `state` TINYINT NOT NULL, \
				add `licenseKey` varchar(100), \
				add INDEX( `clientId` ), \
				add INDEX( `name`, `version`, `subVersion`, `language`, `architecture` );")

		mysql.execute("UPDATE SOFTWARE_CONFIG as sc \
				LEFT JOIN (select windowsSoftwareId, name, version, subVersion, language, architecture from SOFTWARE group by windowsSoftwareId) \
				as s on s.windowsSoftwareId = sc.softwareId \
				set sc.name = s.name, sc.version = s.version, sc.subVersion = s.subVersion, sc.architecture = s.architecture \
				where s.windowsSoftwareId is not null;")

		mysql.execute("delete from SOFTWARE_CONFIG where `name` = '';")
		mysql.execute("alter table SOFTWARE_CONFIG drop `softwareId`;")

	if 'LICENSE_CONTRACT' in tables and 'type' not in tables['LICENSE_CONTRACT']:
		logger.info("Updating database table LICENSE_CONTRACT from opsi 3.4 to 4.0")
		# LICENSE_CONTRACT
		mysql.execute("alter table LICENSE_CONTRACT add `type` varchar(30) NOT NULL;")
		mysql.execute("alter table LICENSE_CONTRACT add `description` varchar(100) NOT NULL;")
		mysql.execute("alter table LICENSE_CONTRACT modify `conclusionDate` TIMESTAMP NULL DEFAULT NULL;")
		mysql.execute("alter table LICENSE_CONTRACT modify `notificationDate` TIMESTAMP NULL DEFAULT NULL;")
		mysql.execute("alter table LICENSE_CONTRACT modify `expirationDate` TIMESTAMP NULL DEFAULT NULL;")
		mysql.execute("update LICENSE_CONTRACT set `type`='LicenseContract' where 1=1")

		mysql.execute("alter table LICENSE_CONTRACT add INDEX( `type` );")

	if 'SOFTWARE_LICENSE' in tables and 'type' not in tables['SOFTWARE_LICENSE']:
		logger.info("Updating database table SOFTWARE_LICENSE from opsi 3.4 to 4.0")
		# SOFTWARE_LICENSE
		mysql.execute("alter table SOFTWARE_LICENSE add `type` varchar(30) NOT NULL;")
		mysql.execute("alter table SOFTWARE_LICENSE modify `expirationDate` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01';")
		mysql.execute("alter table SOFTWARE_LICENSE modify `boundToHost` varchar(255);")
		mysql.execute("update SOFTWARE_LICENSE set `type`='RetailSoftwareLicense' where `licenseType`='RETAIL'")
		mysql.execute("update SOFTWARE_LICENSE set `type`='OEMSoftwareLicense' where `licenseType`='OEM'")
		mysql.execute("update SOFTWARE_LICENSE set `type`='VolumeSoftwareLicense' where `licenseType`='VOLUME'")
		mysql.execute("update SOFTWARE_LICENSE set `type`='ConcurrentSoftwareLicense' where `licenseType`='CONCURRENT'")
		mysql.execute("alter table SOFTWARE_LICENSE drop `licenseType`;")

		mysql.execute("alter table SOFTWARE_LICENSE add INDEX( `type` );")
		mysql.execute("alter table SOFTWARE_LICENSE add INDEX( `boundToHost` );")

	if 'LICENSE_POOL' in tables and 'type' not in tables['LICENSE_POOL']:
		logger.info("Updating database table LICENSE_POOL from opsi 3.4 to 4.0")
		# LICENSE_POOL
		mysql.execute("alter table LICENSE_POOL add `type` varchar(30) NOT NULL;")
		mysql.execute("update LICENSE_POOL set `type`='LicensePool' where 1=1")

		mysql.execute("alter table LICENSE_POOL add INDEX( `type` );")

	if 'WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL' in tables:
		# AUDIT_SOFTWARE_TO_LICENSE_POOL
		logger.info("Updating table WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL to AUDIT_SOFTWARE_TO_LICENSE_POOL")

		mysql.execute('''CREATE TABLE `AUDIT_SOFTWARE_TO_LICENSE_POOL` (
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

		for res in mysql.getSet("SELECT * FROM `WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL`"):
			res2 = mysql.getSet("SELECT * FROM `SOFTWARE` where `windowsSoftwareId` = '%s'" % res['windowsSoftwareId'].replace("'", "\\'"))
			if not res2:
				continue
			res2 = res2[0]
			mysql.execute(
				"""
				insert into AUDIT_SOFTWARE_TO_LICENSE_POOL (`licensePoolId`, `name`, `version`, `subVersion`, `language`, `architecture`)
				VALUES ('%s', '%s', '%s', '%s', '%s', '%s');
				""" % (
					res['licensePoolId'], res2['name'].replace("'", "\\'"), res2['version'].replace("'", "\\'"),
					res2['subVersion'].replace("'", "\\'"), res2['language'], res2['architecture']
				)
			)

		mysql.execute("drop table WINDOWS_SOFTWARE_ID_TO_LICENSE_POOL;")

	for res in mysql.getSet("SELECT * FROM `LICENSE_CONTRACT`"):
		if res['licenseContractId'] != forceLicenseContractId(res['licenseContractId']):
			deleteLicenseContractId = res['licenseContractId']
			res['licenseContractId'] = forceLicenseContractId(res['licenseContractId'])
			logger.warning("Changing license contract id '%s' to '%s'", deleteLicenseContractId, res['licenseContractId'])

			data = {
				'SOFTWARE_LICENSE': [],
				'LICENSE_ON_CLIENT': [],
				'SOFTWARE_LICENSE_TO_LICENSE_POOL': []
			}
			for res2 in mysql.getSet("SELECT * FROM `SOFTWARE_LICENSE` where licenseContractId = '%s'" % deleteLicenseContractId):
				res2['licenseContractId'] = res['licenseContractId']
				data['SOFTWARE_LICENSE'].append(res2)
				for tab in ('LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
					for res3 in mysql.getSet("SELECT * FROM `%s` where softwareLicenseId = '%s'" % (tab, res2['softwareLicenseId'])):
						data[tab].append(res3)
					mysql.delete(tab, "softwareLicenseId = '%s'" % res2['softwareLicenseId'])
			mysql.delete('SOFTWARE_LICENSE', "licenseContractId = '%s'" % deleteLicenseContractId)
			mysql.delete('LICENSE_CONTRACT', "licenseContractId = '%s'" % deleteLicenseContractId)
			mysql.insert('LICENSE_CONTRACT', res)
			for tab in ('SOFTWARE_LICENSE', 'SOFTWARE_LICENSE_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT'):
				for i in data[tab]:
					mysql.insert(tab, i)

	for res in mysql.getSet("SELECT * FROM `LICENSE_POOL`"):
		if (res['licensePoolId'] != res['licensePoolId'].strip()) or (res['licensePoolId'] != forceLicensePoolId(res['licensePoolId'])):
			deleteLicensePoolId = res['licensePoolId']
			res['licensePoolId'] = forceLicensePoolId(res['licensePoolId'].strip())
			logger.warning("Changing license pool id '%s' to '%s'", deleteLicensePoolId, res['licensePoolId'])

			data = {}
			for tab in ('AUDIT_SOFTWARE_TO_LICENSE_POOL', 'PRODUCT_ID_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
				data[tab] = []
				for res2 in mysql.getSet("SELECT * FROM `%s` where licensePoolId = '%s'" % (tab, deleteLicensePoolId)):
					res2['licensePoolId'] = res['licensePoolId']
					data[tab].append(res2)
				mysql.delete(tab, "licensePoolId = '%s'" % deleteLicensePoolId)

			mysql.delete('LICENSE_POOL', "licensePoolId = '%s'" % deleteLicensePoolId)
			mysql.insert('LICENSE_POOL', res)
			for tab in ('AUDIT_SOFTWARE_TO_LICENSE_POOL', 'PRODUCT_ID_TO_LICENSE_POOL', 'SOFTWARE_LICENSE_TO_LICENSE_POOL', 'LICENSE_ON_CLIENT'):
				for i in data[tab]:
					mysql.insert(tab, i)

	for res in mysql.getSet("SELECT * FROM `SOFTWARE_LICENSE`"):
		if (
			res['softwareLicenseId'] != res['softwareLicenseId'].strip() or
			res['softwareLicenseId'] != forceSoftwareLicenseId(res['softwareLicenseId'])
		):
			deleteSoftwareLicenseId = res['softwareLicenseId']
			res['softwareLicenseId'] = forceSoftwareLicenseId(res['softwareLicenseId'].strip())
			logger.warning("Changing software license id '%s' to '%s'", deleteSoftwareLicenseId, res['softwareLicenseId'])

			data = {}
			for tab in ('LICENSE_ON_CLIENT', 'SOFTWARE_LICENSE_TO_LICENSE_POOL'):
				data[tab] = []
				for res2 in mysql.getSet("SELECT * FROM `%s` where softwareLicenseId = '%s'" % (tab, deleteSoftwareLicenseId)):
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
		logger.info("Updating productId Columns")
		for line in mysql.getSet("SHOW TABLES;"):
			for tableName in line.values():
				logger.debug(" [ %s ]", tableName)
				for column in mysql.getSet('SHOW COLUMNS FROM `%s`;' % tableName):
					fieldName = column['Field']
					fieldType = column['Type']
					if "productid" in fieldName.lower() and fieldType != "varchar(255)":
						logger.debug("ALTER TABLE for Table: '%s' and Column: '%s'", tableName, fieldName)
						mysql.execute("alter table %s MODIFY COLUMN `%s` VARCHAR(255);" % (tableName, fieldName))

	# Changing description fields to type TEXT
	for tableName in ("PRODUCT_PROPERTY", ):
		logger.info("Updating field 'description' on table %s", tableName)
		fieldName = "description"
		mysql.execute(
			"alter table {name} MODIFY COLUMN `{column}` TEXT;".format(
				name=tableName,
				column=fieldName
			)
		)

	# Fixing unwanted MySQL defaults:
	if 'HOST' in tables:
		logger.info("Fixing DEFAULT for colum 'created' on table HOST")
		mysql.execute("alter table HOST modify `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

	# Changing the length of too small hostId / depotId column
	def tableNeedsHostIDLengthFix(table, columnName="hostId"):
		for column in mysql.getSet('SHOW COLUMNS FROM `{0}`;'.format(table)):
			if column['Field'] != columnName:
				continue

			if column['Type'].lower() != "varchar(255)":
				return True

		return False

	with disableForeignKeyChecks(mysql):
		for tablename in tables:
			if tablename == 'PRODUCT_ON_DEPOT' and tableNeedsHostIDLengthFix(tablename, columnName="depotId"):
				logger.info("Fixing length of 'depotId' column on %s", tablename)
				mysql.execute("ALTER TABLE `PRODUCT_ON_DEPOT` MODIFY COLUMN `depotId` VARCHAR(255) NOT NULL;")
			elif tablename.startswith('HARDWARE_CONFIG') and tableNeedsHostIDLengthFix(tablename):
				logger.info("Fixing length of 'hostId' column on %s", tablename)
				mysql.execute("ALTER TABLE `{table}` MODIFY COLUMN `hostId` VARCHAR(255) NOT NULL;".format(table=tablename))

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
	logger.debug("Disabled FOREIGN_KEY_CHECKS for session.")
	try:
		yield
	finally:
		database.execute('SET FOREIGN_KEY_CHECKS=1;')
		logger.debug("Enabled FOREIGN_KEY_CHECKS for session.")


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
					logger.info("Fixing length of 'licenseKey' column on table '%s'", table)
					database.execute("ALTER TABLE `{0}` MODIFY COLUMN `licenseKey` VARCHAR(1024);".format(table))


def getTableColumns(database, tableName):
	TableColumn = namedtuple("TableColumn", ["name", "type"])
	return [TableColumn(column['Field'], column['Type']) for column
			in database.getSet('SHOW COLUMNS FROM `{0}`;'.format(tableName))]


def _dropTableBootconfiguration(database):
	logger.info("Dropping table BOOT_CONFIGURATION.")
	database.execute("drop table BOOT_CONFIGURATION;")


def _addIndexOnProductPropertyValues(database):
	logger.info("Adding index on table PRODUCT_PROPERTY_VALUE.")
	database.execute('''
		CREATE INDEX `index_product_property_value` on
		`PRODUCT_PROPERTY_VALUE`
		(`productId`, `propertyId`, `productVersion`, `packageVersion`);''')


def _addWorkbenchAttributesToHosts(database):
	logger.info("Adding column 'workbenchLocalUrl' on table HOST.")
	database.execute('ALTER TABLE `HOST` add `workbenchLocalUrl` varchar(128);')

	logger.info("Adding column 'workbenchRemoteUrl' on table HOST.")
	database.execute('ALTER TABLE `HOST` add `workbenchRemoteUrl` varchar(255);')


def _adjustLengthOfGroupId(database):
	logger.info("Correcting length of column 'groupId' on table OBJECT_TO_GROUP")
	database.execute(
		'ALTER TABLE `OBJECT_TO_GROUP` '
		'MODIFY COLUMN `groupId` varchar(255) NOT NULL;'
	)


def _increaseInventoryNumberLength(database):
	logger.info("Correcting length of column 'groupId' on table OBJECT_TO_GROUP")
	database.execute(
		'ALTER TABLE `HOST` '
		'MODIFY COLUMN `inventoryNumber` varchar(64) NOT NULL;'
	)


def _changeSoftwareConfigConfigIdToBigInt(database):
	logger.info("Changing the type of SOFTWARE_CONFIG.config_id to bigint")
	database.execute("ALTER TABLE `SOFTWARE_CONFIG` MODIFY COLUMN `config_id` bigint auto_increment;")

def _addIndexProductIdOnProductAndWindowsSoftwareIDToProduct(database):
	logger.info("Adding productId index on PRODUCT and WINDOWS_SOFTWARE_ID_TO_PRODUCT")
	database.execute('CREATE INDEX `index_productId` on `WINDOWS_SOFTWARE_ID_TO_PRODUCT` (`productId`);')
	database.execute('CREATE INDEX `index_productId` on `PRODUCT` (`productId`);')
