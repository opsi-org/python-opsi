# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2018 uib GmbH
#
# http://www.uib.de/
#
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import

from contextlib import contextmanager

import pytest

from OPSI.Backend.MySQL import (
    MySQL, MySQLBackend, MySQLBackendObjectModificationTracker)
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
        with disableForeignKeyChecks(database):
            tablesToDropAgain = set()
            for tableName in getTableNames(database):
                try:
                    database.execute(u'DROP TABLE `{0}`;'.format(tableName))
                except Exception as error:
                    print("Failed to drop {0}: {1}".format(tableName, error))
                    tablesToDropAgain.add(tableName)

            for tableName in tablesToDropAgain:
                try:
                    database.execute(u'DROP TABLE `{0}`;'.format(tableName))
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


def getTableNames(database):
    return set(tuple(i.values())[0] for i in database.getSet(u'SHOW TABLES;'))
