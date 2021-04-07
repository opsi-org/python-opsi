# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0

from contextlib import contextmanager

import pytest

try:
	from .config import SQLiteconfiguration
except ImportError:
	SQLiteconfiguration = {}


@contextmanager
def getSQLiteBackend(**backendOptions):
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

	optionsForBackend = SQLiteconfiguration
	optionsForBackend.update(backendOptions)

	yield SQLiteBackend(**optionsForBackend)


@contextmanager
def getSQLiteModificationTracker():
	sqliteModule = pytest.importorskip("OPSI.Backend.SQLite")
	trackerClass = sqliteModule.SQLiteObjectBackendModificationTracker

	yield trackerClass(database=":memory:")
