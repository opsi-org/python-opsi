# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0

from contextlib import contextmanager

import pytest

from OPSI.Backend.MySQL import (
	MySQL, MySQLBackend, MySQLBackendObjectModificationTracker
)
from OPSI.Util.Task.UpdateBackend.MySQL import disableForeignKeyChecks

try:
	from .config import MySQLconfiguration
except ImportError:
	MySQLconfiguration = None

UNKNOWN_TABLE_ERROR_CODE = 1051


@contextmanager
def getMySQLBackend(**backendOptions):
	if not MySQLconfiguration:
		pytest.skip('no MySQL backend configuration given.')

	optionsForBackend = MySQLconfiguration
	optionsForBackend.update(backendOptions)

	with cleanDatabase(MySQL(**optionsForBackend)):
		yield MySQLBackend(**optionsForBackend)


@contextmanager
def getMySQLModificationTracker():
	if not MySQLconfiguration:
		pytest.skip('no MySQL backend configuration given.')

	yield MySQLBackendObjectModificationTracker(**MySQLconfiguration)


@contextmanager
def cleanDatabase(database):
	def dropAllTables(database):
		with database.session() as session:
			with disableForeignKeyChecks(database, session):
				tablesToDropAgain = set()
				for tableName in getTableNames(database, session):
					try:
						database.execute(session, 'DROP TABLE `{0}`;'.format(tableName))
					except Exception as error:
						print("Failed to drop {0}: {1}".format(tableName, error))
						tablesToDropAgain.add(tableName)

				for tableName in tablesToDropAgain:
					try:
						database.execute(session, 'DROP TABLE `{0}`;'.format(tableName))
					except Exception as error:
						errorCode = error.args[0]
						if errorCode == UNKNOWN_TABLE_ERROR_CODE:
							continue

						print("Failed to drop {0} a second time: {1}".format(tableName, error))
						raise error

	dropAllTables(database)
	try:
		yield database
	finally:
		dropAllTables(database)


def getTableNames(database, session):
	return set(tuple(i.values())[0] for i in database.getSet(session, u'SHOW TABLES;'))
