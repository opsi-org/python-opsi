# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>
# All rights reserved.

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
MySQL-Backend

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero GPL version 3
"""

import base64
import time
from contextlib import contextmanager
from hashlib import md5
try:
	# pyright: reportMissingImports=false
	# python3-pycryptodome installs into Cryptodome
	from Cryptodome.Hash import MD5
	from Cryptodome.Signature import pkcs1_15
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Hash import MD5
	from Crypto.Signature import pkcs1_15

from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.orm import scoped_session, sessionmaker

from OPSI.Backend.Base import ConfigDataBackend
from OPSI.Backend.SQL import (
	onlyAllowSelect, SQL, SQLBackend, SQLBackendObjectModificationTracker
)
from OPSI.Exceptions import BackendBadValueError
from OPSI.Logger import Logger
from OPSI.Types import forceInt, forceUnicode
from OPSI.Util import getPublicKey
from OPSI.Object import Product, ProductProperty

__all__ = (
	'MySQL', 'MySQLBackend', 'MySQLBackendObjectModificationTracker'
)

logger = Logger()


def retry_on_deadlock(func):
	def wrapper(*args, **kwargs):
		trynum = 0
		while True:
			trynum += 1
			try:
				return func(*args, **kwargs)
			except Exception as err:  # pylint: disable=broad-except
				if trynum >= 3 or "deadlock" not in str(err).lower():
					raise
				time.sleep(0.1)
	return wrapper


class MySQL(SQL):  # pylint: disable=too-many-instance-attributes

	AUTOINCREMENT = 'AUTO_INCREMENT'
	ALTER_TABLE_CHANGE_SUPPORTED = True
	ESCAPED_BACKSLASH = "\\\\"
	ESCAPED_APOSTROPHE = "\\\'"
	ESCAPED_ASTERISK = "\\*"

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._address = 'localhost'
		self._username = 'opsi'
		self._password = 'opsi'
		self._database = 'opsi'
		self._databaseCharset = 'utf8'
		self._connectionPoolSize = 20
		self._connectionPoolMaxOverflow = 10
		self._connectionPoolTimeout = 30
		self._connectionPoolRecyclingSeconds = -1

		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'address':
				self._address = forceUnicode(value)
				if self._address == "::1":
					self._address = "[::1]"
			elif option == 'username':
				self._username = forceUnicode(value)
			elif option == 'password':
				self._password = forceUnicode(value)
			elif option == 'database':
				self._database = forceUnicode(value)
			elif option == 'databasecharset':
				self._databaseCharset = str(value)
			elif option == 'connectionpoolsize':
				self._connectionPoolSize = forceInt(value)
			elif option == 'connectionpoolmaxoverflow':
				self._connectionPoolMaxOverflow = forceInt(value)
			#elif option == 'connectionpooltimeout':
			#	self._connectionPoolTimeout = forceInt(value)
			elif option == 'connectionpoolrecycling':
				self._connectionPoolRecyclingSeconds = forceInt(value)

		try:
			self.init_connection()
		except Exception as err:  # pylint: disable=broad-except
			if self._address != "localhost":
				raise
			logger.info("Failed to connect to socket (%s), retrying with tcp/ip", err)
			self._address = "127.0.0.1"
			self.init_connection()

	@staticmethod
	def on_engine_connect(conn, branch):  # pylint: disable=unused-argument
		conn.execute("""
			SET SESSION sql_mode=(SELECT
				REPLACE(
					REPLACE(
						REPLACE(@@sql_mode,
							'ONLY_FULL_GROUP_BY', ''
						),
						'NO_ZERO_IN_DATE', ''
					),
					'NO_ZERO_DATE', ''
				)
			);
		""")
		#conn.execute("SHOW VARIABLES LIKE 'sql_mode';").fetchone()

	def init_connection(self):
		uri = f'mysql://{self._username}:{self._password}@{self._address}/{self._database}'
		logger.info("Connecting to %s", uri)

		self.engine = create_engine(
			uri,
			pool_pre_ping=True, # auto reconnect
			encoding=self._databaseCharset,
			pool_size=self._connectionPoolSize,
			max_overflow=self._connectionPoolMaxOverflow,
			pool_recycle=self._connectionPoolRecyclingSeconds
		)

		listen(self.engine, 'engine_connect', self.on_engine_connect)

		self.session_factory = sessionmaker(
			bind=self.engine,
			autocommit=False,
			autoflush=False
		)
		self.Session = scoped_session(self.session_factory)  # pylint: disable=invalid-name

		# Test connection
		self.getSet("SELECT 1")
		logger.debug('MySQL connected: %s', self)


	def __repr__(self):
		return f"<{self.__class__.__name__}(address={self._address})>"

	@contextmanager
	def session(self):
		try:
			yield self.Session()
		finally:
			self.Session.remove()

	def connect(self, cursorType=None):
		pass

	def close(self, conn, cursor):
		pass

	def getSet(self, query):
		"""
		Return a list of rows, every row is a dict of key / values pairs
		"""
		logger.trace("getSet: %s", query)
		onlyAllowSelect(query)
		with self.session() as session:
			result = session.execute(query).fetchall()  # pylint: disable=no-member
			if not result:
				return []
			return [ dict(row.items()) for row in result if row is not None ]

	def getRows(self, query):
		"""
		Return a list of rows, every row is a list of values
		"""
		logger.trace("getRows: %s", query)
		onlyAllowSelect(query)
		with self.session() as session:
			result = session.execute(query).fetchall()  # pylint: disable=no-member
			if not result:
				return []
			return [ list(row) for row in result if row is not None ]

	def getRow(self, query, conn=None, cursor=None):
		"""
		Return one row as value list
		"""
		logger.trace("getRow: %s", query)
		onlyAllowSelect(query)
		with self.session() as session:
			result = session.execute(query).fetchone()  # pylint: disable=no-member
			if not result:
				return []
			return list(result)

	@retry_on_deadlock
	def insert(self, table, valueHash, conn=None, cursor=None):  # pylint: disable=too-many-branches
		if not valueHash:
			raise BackendBadValueError("No values given")

		col_names = [ f"`{col_name}`" for col_name in list(valueHash) ]
		bind_names = [ f":{col_name}" for col_name in list(valueHash) ]
		query = f"INSERT INTO `{table}` ({','.join(col_names)}) VALUES ({','.join(bind_names)})"
		logger.trace("insert: %s - %s", query, valueHash)
		with self.session() as session:
			result = session.execute(query, valueHash)  # pylint: disable=no-member
			session.commit()  # pylint: disable=no-member
			return result.lastrowid

	@retry_on_deadlock
	def update(self, table, where, valueHash, updateWhereNone=False):  # pylint: disable=too-many-branches
		if not valueHash:
			raise BackendBadValueError("No values given")

		updates = []
		for (key, value) in valueHash.items():
			if value is None and not updateWhereNone:
				continue
			updates.append(f"`{key}` = :{key}")

		query = f"UPDATE `{table}` SET {','.join(updates)} WHERE {where}"

		logger.trace("update: %s - %s", query, valueHash)
		with self.session() as session:
			result = session.execute(query, valueHash)  # pylint: disable=no-member
			session.commit()  # pylint: disable=no-member
			return result.rowcount

	@retry_on_deadlock
	def delete(self, table, where, conn=None, cursor=None):
		query = f"DELETE FROM `{table}` WHERE {where}"
		logger.trace("delete: %s", query)
		with self.session() as session:
			result = session.execute(query)  # pylint: disable=no-member
			session.commit()  # pylint: disable=no-member
			return result.rowcount

	def execute(self, query, conn=None, cursor=None):
		with self.session() as session:
			session.execute(query)  # pylint: disable=no-member
			session.commit()  # pylint: disable=no-member

	def getTables(self):
		"""
		Get what tables are present in the database.

		Table names will always be uppercased.

		:returns: A dict with the tablename as key and the field names as value.
		:rtype: dict
		"""
		tables = {}
		logger.trace("Current tables:")
		for i in self.getSet('SHOW TABLES;'):
			for tableName in i.values():
				tableName = tableName.upper()
				logger.trace(" [ %s ]", tableName)
				fields = [j['Field'] for j in self.getSet('SHOW COLUMNS FROM `%s`' % tableName)]
				tables[tableName] = fields
				logger.trace("Fields in %s: %s", tableName, fields)

		return tables

	def getTableCreationOptions(self, table):
		if table in ('SOFTWARE', 'SOFTWARE_CONFIG') or table.startswith(('HARDWARE_DEVICE_', 'HARDWARE_CONFIG_')):
			return 'ENGINE=MyISAM DEFAULT CHARSET utf8 COLLATE utf8_general_ci;'
		return 'ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci'


class MySQLBackend(SQLBackend):

	def __init__(self, **kwargs):  # pylint: disable=too-many-branches, too-many-statements
		self._name = 'mysql'

		SQLBackend.__init__(self, **kwargs)

		self._sql = MySQL(**kwargs)

		backendinfo = self._context.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']

		if not all(key in modules for key in ('expires', 'customer')):
			logger.info(
				"Missing important information about modules. "
				"Probably no modules file installed."
			)
		elif not modules.get('customer'):
			logger.error("Disabling mysql backend and license management module: no customer in modules file")
		elif not modules.get('valid'):
			logger.error("Disabling mysql backend and license management module: modules file invalid")
		elif (
			modules.get('expires', '') != 'never' and
			time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0
		):
			logger.error("Disabling mysql backend and license management module: modules file expired")
		else:
			logger.info("Verifying modules file signature")
			publicKey = getPublicKey(
				data=base64.decodebytes(
					b"AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDo"
					b"jY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8"
					b"S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDU"
					b"lk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP"
				)
			)
			data = ""
			mks = list(modules.keys())
			mks.sort()
			for module in mks:
				if module in ("valid", "signature"):
					continue
				if module in helpermodules:
					val = helpermodules[module]
					if int(val) > 0:
						modules[module] = True
				else:
					val = modules[module]
					if isinstance(val, bool):
						val = "yes" if val else "no"
				data += "%s = %s\r\n" % (module.lower().strip(), val)

			verified = False
			if modules["signature"].startswith("{"):
				s_bytes = int(modules['signature'].split("}", 1)[-1]).to_bytes(256, "big")
				try:
					pkcs1_15.new(publicKey).verify(MD5.new(data.encode()), s_bytes)
					verified = True
				except ValueError:
					# Invalid signature
					pass
			else:
				h_int = int.from_bytes(md5(data.encode()).digest(), "big")
				s_int = publicKey._encrypt(int(modules["signature"]))
				verified = h_int == s_int

			if not verified:
				logger.error("Disabling mysql backend and license management module: modules file invalid")
			else:
				logger.debug("Modules file signature verified (customer: %s)", modules.get('customer'))

				if modules.get("license_management"):
					self._licenseManagementModule = True

				if modules.get("mysql_backend"):
					self._sqlBackendModule = True

		logger.debug('MySQLBackend created: %s', self)

	def _createTableHost(self):
		logger.debug('Creating table HOST')
		# MySQL uses some defaults for a row that specifies TIMESTAMP as
		# type without giving DEFAULT or ON UPDATE constraints that
		# result in hosts always having the current time in created and
		# lastSeen. We do not want this behaviour, so we need to specify
		# our DEFAULT.
		# More information about the defaults can be found in the MySQL
		# handbook:
		#   https://dev.mysql.com/doc/refman/5.1/de/timestamp-4-1.html
		table = '''CREATE TABLE `HOST` (
				`hostId` varchar(255) NOT NULL,
				`type` varchar(30),
				`description` varchar(100),
				`notes` varchar(500),
				`hardwareAddress` varchar(17),
				`ipAddress` varchar(15),
				`inventoryNumber` varchar(64),
				`created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				`lastSeen` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				`opsiHostKey` varchar(32),
				`oneTimePassword` varchar(32),
				`maxBandwidth` integer,
				`depotLocalUrl` varchar(128),
				`depotRemoteUrl` varchar(255),
				`depotWebdavUrl` varchar(255),
				`repositoryLocalUrl` varchar(128),
				`repositoryRemoteUrl` varchar(255),
				`networkAddress` varchar(31),
				`isMasterDepot` bool,
				`masterDepotId` varchar(255),
				`workbenchLocalUrl` varchar(128),
				`workbenchRemoteUrl` varchar(255),
				PRIMARY KEY (`hostId`)
			) %s;''' % self._sql.getTableCreationOptions('HOST')
		logger.debug(table)
		self._sql.execute(table)
		self._sql.execute('CREATE INDEX `index_host_type` on `HOST` (`type`);')

	def _createTableSoftwareConfig(self):
		logger.debug('Creating table SOFTWARE_CONFIG')
		# We want the primary key config_id to be of a bigint as
		# regular int has been proven to be too small on some
		# installations.
		table = '''CREATE TABLE `SOFTWARE_CONFIG` (
				`config_id` bigint NOT NULL ''' + self._sql.AUTOINCREMENT + ''',
				`clientId` varchar(255) NOT NULL,
				`name` varchar(100) NOT NULL,
				`version` varchar(100) NOT NULL,
				`subVersion` varchar(100) NOT NULL,
				`language` varchar(10) NOT NULL,
				`architecture` varchar(3) NOT NULL,
				`uninstallString` varchar(200),
				`binaryName` varchar(100),
				`firstseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
				`lastseen` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
				`state` TINYINT NOT NULL,
				`usageFrequency` integer NOT NULL DEFAULT -1,
				`lastUsed` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
				`licenseKey` VARCHAR(1024),
				PRIMARY KEY (`config_id`)
			) %s;
			''' % self._sql.getTableCreationOptions('SOFTWARE_CONFIG')
		logger.debug(table)
		self._sql.execute(table)
		self._sql.execute('CREATE INDEX `index_software_config_clientId` on `SOFTWARE_CONFIG` (`clientId`);')
		self._sql.execute(
			'CREATE INDEX `index_software_config_nvsla` on `SOFTWARE_CONFIG` (`name`, `version`, `subVersion`, `language`, `architecture`);'
		)

	# Overwriting product_getObjects to use JOIN for speedup
	def product_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.product_getObjects(self, attributes=[], **filter)
		logger.info("Getting products, filter: %s", filter)

		(attributes, filter) = self._adjustAttributes(Product, attributes, filter)
		readWindowsSoftwareIDs = not attributes or 'windowsSoftwareIds' in attributes

		select = ','.join(f'p.`{attribute}`' for attribute in attributes) or 'p.*'
		where = self._filterToSql(filter, table="p") or '1=1'
		query = f'''
			SELECT
				{select},
				GROUP_CONCAT(wp.windowsSoftwareId SEPARATOR "\n") AS windowsSoftwareIds
			FROM
				PRODUCT AS p
			LEFT JOIN
				WINDOWS_SOFTWARE_ID_TO_PRODUCT AS wp ON p.productId = wp.productId
			WHERE
				{where}
			GROUP BY
				p.productId,
				p.productVersion,
				p.packageVersion
		'''

		products = []
		for product in self._sql.getSet(query):
			product['productClassIds'] = []
			if readWindowsSoftwareIDs and product['windowsSoftwareIds']:
				product['windowsSoftwareIds'] = product['windowsSoftwareIds'].split("\n")
			else:
				product['windowsSoftwareIds'] = []

			if not attributes or 'productClassIds' in attributes:
				pass

			self._adjustResult(Product, product)
			products.append(Product.fromHash(product))
		return products

	# Overwriting productProperty_getObjects to use JOIN for speedup
	def productProperty_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._requiresEnabledSQLBackendModule()
		ConfigDataBackend.productProperty_getObjects(self, attributes=[], **filter)
		logger.info("Getting product properties, filter: %s", filter)

		(attributes, filter) = self._adjustAttributes(ProductProperty, attributes, filter)
		readValues = not attributes or 'possibleValues' in attributes or 'defaultValues' in attributes

		select = ','.join(f'pp.`{attribute}`' for attribute in attributes) or 'pp.*'
		where = self._filterToSql(filter, table="pp") or '1=1'
		query = f'''
			SELECT
				{select},
				-- JSON_ARRAYAGG(ppv.value) AS possibleValues,
				-- JSON_ARRAYAGG(IF(ppv.isDefault, ppv.value, NULL)) AS defaultValues,
				GROUP_CONCAT(ppv.value SEPARATOR "\n") AS possibleValues,
				GROUP_CONCAT(IF(ppv.isDefault, ppv.value, NULL) SEPARATOR "\n") AS defaultValues
			FROM
				PRODUCT_PROPERTY AS pp
			LEFT JOIN
				PRODUCT_PROPERTY_VALUE AS ppv ON
					ppv.productId = pp.productId AND
					ppv.productVersion = pp.productVersion AND
					ppv.packageVersion = pp.packageVersion AND
					ppv.propertyId = pp.propertyId
			WHERE
				{where}
			GROUP BY
				pp.productId,
				pp.productVersion,
				pp.packageVersion,
				pp.propertyId
		'''
		productProperties = []
		for productProperty in self._sql.getSet(query):
			if readValues and productProperty['possibleValues']:
				productProperty['possibleValues'] = productProperty['possibleValues'].split("\n")
			else:
				productProperty['possibleValues'] = []

			if readValues and productProperty['defaultValues']:
				productProperty['defaultValues'] = productProperty['defaultValues'].split("\n")
			else:
				productProperty['defaultValues'] = []
			productProperties.append(ProductProperty.fromHash(productProperty))
		return productProperties


class MySQLBackendObjectModificationTracker(SQLBackendObjectModificationTracker):
	def __init__(self, **kwargs):
		SQLBackendObjectModificationTracker.__init__(self, **kwargs)
		self._sql = MySQL(**kwargs)
		self._createTables()
