# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Fixtures for tests.

To use any of these fixtures use their name as a parameter when
creating a test function. No rurther imports are needed.

	def testSomething(fixtureName):
		pass


Backends with MySQL / SQLite sometimes require a modules file and may
be skipped if it does not exist.
"""

import os
import shutil
import urllib3
from contextlib import contextmanager

import pytest
from _pytest.logging import LogCaptureHandler

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.BackendManager import BackendManager

from .Backends.File import getFileBackend, _getOriginalBackendLocation
from .Backends.SQLite import getSQLiteBackend
from .Backends.MySQL import getMySQLBackend
from .helpers import workInTemporaryDirectory, createTemporaryTestfile


_MODULES_FILE = os.path.exists(os.path.join('/etc', 'opsi', 'modules'))

urllib3.disable_warnings()

def emit(*args, **kwargs) -> None:  # pylint: disable=unused-argument
	pass
LogCaptureHandler.emit = emit


@pytest.fixture(
	params=[
		getFileBackend,
		pytest.param(getMySQLBackend, marks=pytest.mark.requiresModulesFile),
		pytest.param(getSQLiteBackend, marks=pytest.mark.requiresModulesFile),
	],
	ids=['file', 'mysql', 'sqlite']
)
def configDataBackend(request):
	"""
	Returns an `OPSI.Backend.ConfigDataBackend` for testing.

	This will return multiple backends but some of these may lead to
	skips if required libraries are missing or conditions for the
	execution are not met.
	"""
	with request.param() as backend:
		with _backendBase(backend):
			yield backend


@contextmanager
def _backendBase(backend):
	"Creates the backend base before and deletes it after use."

	backend.backend_createBase()
	try:
		yield
	finally:
		backend.backend_deleteBase()


@pytest.fixture
def extendedConfigDataBackend(configDataBackend):
	"""
	Returns an `OPSI.Backend.ExtendedConfigDataBackend` for testing.

	This will return multiple backends but some of these may lead to
	skips if required libraries are missing or conditions for the
	execution are not met.
	"""
	yield ExtendedConfigDataBackend(configDataBackend)


@pytest.fixture
def cleanableDataBackend(_serverBackend):
	"""
	Returns an backend that can be cleaned.
	"""
	yield ExtendedConfigDataBackend(_serverBackend)


@pytest.fixture(
	params=[
		getFileBackend,
		pytest.param(getMySQLBackend, marks=pytest.mark.requiresModulesFile),
	],
	ids=['file', 'mysql']
)
def _serverBackend(request):
	"Shortcut to specify backends used on an opsi server."

	with request.param() as backend:
		with _backendBase(backend):
			yield backend


@pytest.fixture(
	params=[
		getFileBackend,
		pytest.param(getMySQLBackend, marks=pytest.mark.requiresModulesFile),
	],
	ids=['destination:file', 'destination:mysql']
)
def replicationDestinationBackend(request):
	# This is the same as _serverBackend, but has custom id's set.
	with request.param() as backend:
		with _backendBase(backend):
			yield backend


@pytest.fixture
def backendManager(_serverBackend, tempDir):
	"""
	Returns an `OPSI.Backend.BackendManager.BackendManager` for testing.

	The returned instance is set up to have access to backend extensions.
	"""
	defaultConfigDir = _getOriginalBackendLocation()

	shutil.copytree(defaultConfigDir, os.path.join(tempDir, 'etc', 'opsi'))

	yield BackendManager(
		backend=_serverBackend,
		extensionconfigdir=os.path.join(tempDir, 'etc', 'opsi', 'backendManager', 'extend.d')
	)


@pytest.fixture
def tempDir():
	'''
	Switch to a temporary directory.
	'''
	with workInTemporaryDirectory() as tDir:
		yield tDir


@pytest.fixture
def licenseManagementBackend(sqlBackendCreationContextManager):
	'''Returns a backend that can handle License Management.'''
	with sqlBackendCreationContextManager() as backend:
		with _backendBase(backend):
			yield ExtendedConfigDataBackend(backend)


@pytest.fixture(
	params=[
		getMySQLBackend,
		pytest.param(getSQLiteBackend, marks=pytest.mark.requiresModulesFile),
	],
	ids=['mysql', 'sqlite']
)
def sqlBackendCreationContextManager(request):
	yield request.param


@pytest.fixture(
	params=[getMySQLBackend],
	ids=['mysql']
)
def multithreadingBackend(request):
	with request.param() as backend:
		with _backendBase(backend):
			yield backend


@pytest.fixture(
	params=[getMySQLBackend, getSQLiteBackend],
	ids=['mysql', 'sqlite']
)
def hardwareAuditBackendWithHistory(request, hardwareAuditConfigPath):
	with request.param(auditHardwareConfigFile=hardwareAuditConfigPath) as backend:
		with _backendBase(backend):
			yield ExtendedConfigDataBackend(backend)


@pytest.fixture
def hardwareAuditConfigPath():
	'''
	Copies the opsihwaudit.conf that is usually distributed for
	installation to a temporary folder and then returns the new absolute
	path of the config file.
	'''
	pathToOriginalConfig = os.path.join(os.path.dirname(__file__), '..', '..',
										'data', 'hwaudit', 'opsihwaudit.conf')

	with createTemporaryTestfile(pathToOriginalConfig) as fileCopy:
		yield fileCopy


@pytest.fixture(
	params=[getFileBackend, getMySQLBackend, getSQLiteBackend],
	ids=['file', 'mysql', 'sqlite']
)
def auditDataBackend(request, hardwareAuditConfigPath):
	with request.param(auditHardwareConfigFile=hardwareAuditConfigPath) as backend:
		with _backendBase(backend):
			yield ExtendedConfigDataBackend(backend)


@pytest.fixture(
	params=[
		getMySQLBackend,
		pytest.param(getSQLiteBackend, marks=pytest.mark.requiresModulesFile),
	],
	ids=['mysql', 'sqlite']
)
def licenseManagentAndAuditBackend(request):
	with request.param() as backend:
		with _backendBase(backend):
			yield ExtendedConfigDataBackend(backend)


def pytest_configure(config):
	config.addinivalue_line(
		"markers", "obsolete: mark test that are obsolete for 4.2 development"
	)


def pytest_runtest_setup(item):
	envmarker = item.get_closest_marker("requiresModulesFile")
	if envmarker is not None:
		if not _MODULES_FILE:
			pytest.skip("{0} requires a modules file!".format(item.name))

	envmarker = item.get_closest_marker("obsolete")
	if envmarker is not None:
		pytest.skip("{0} uses tech that will likely be obsolete in the future".format(item.name))
