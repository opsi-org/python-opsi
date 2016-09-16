#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2016 uib GmbH
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

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from . import BackendMixin

import pytest

try:
	from .config import SQLiteconfiguration
except ImportError:
	SQLiteconfiguration = {}


class SQLiteBackendMixin(BackendMixin):

	CREATES_INVENTORY_HISTORY = True

	def setUpBackend(self):
		sqliteModule = pytest.importorskip("OPSI.Backend.SQLite")
		SQLiteBackend = sqliteModule.SQLiteBackend

		self.backend = ExtendedConfigDataBackend(SQLiteBackend(**SQLiteconfiguration))
		self.backend.backend_createBase()

	def tearDownBackend(self):
		self.backend.backend_deleteBase()


@contextmanager
def getSQLiteBackend(configuration=None):
	sqliteModule = pytest.importorskip("OPSI.Backend.SQLite")
	SQLiteBackend = sqliteModule.SQLiteBackend

	# Defaults and settings from the old fixture.
	# defaultOptions = {
	# 	'processProductPriorities':            True,
	# 	'processProductDependencies':          True,
	# 	'addProductOnClientDefaults':          True,
	# 	'addProductPropertyStateDefaults':     True,
	# 	'addConfigStateDefaults':              True,
	# 	'deleteConfigStateIfDefault':          True,
	# 	'returnObjectsOnUpdateAndCreate':      False
	# }
	# licenseManagement = True
	if configuration is None:
		configuration = SQLiteconfiguration

	backend = SQLiteBackend(**SQLiteconfiguration)
	backend.backend_createBase()
	yield backend
	backend.backend_deleteBase()


@contextmanager
def getSQLiteModificationTracker():
	sqliteModule = pytest.importorskip("OPSI.Backend.SQLite")
	trackerClass = sqliteModule.SQLiteObjectBackendModificationTracker

	yield trackerClass(database=":memory:")
