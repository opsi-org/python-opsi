# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the opsi SQLite backend.
"""

import pytest


def testInitialisationOfSQLiteBackendWithoutParametersDoesNotFail():
	sqlModule = pytest.importorskip("OPSI.Backend.SQLite")
	SQLiteBackend = sqlModule.SQLiteBackend

	backend = SQLiteBackend()
	backend.backend_createBase()
