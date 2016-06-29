#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016 uib GmbH <info@uib.de>

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
Fixtures for tests.

These will replace the mixins in the future and should be preferred when
writing new tests.

To use any of these fixtures use their name as a parameter when
creating a test function. No rurther imports are needed.

    def testSomething(fixtureName):
        pass


:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import shutil
from contextlib import contextmanager

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.BackendManager import BackendManager

from .Backends.File import getFileBackend, _getOriginalBackendLocation
from .Backends.SQLite import getSQLiteBackend
from .Backends.MySQL import getMySQLBackend
from .helpers import workInTemporaryDirectory

import pytest


@pytest.yield_fixture(
    params=[getFileBackend, getSQLiteBackend, getMySQLBackend],
    ids=['file', 'sqlite', 'mysql']
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


@pytest.yield_fixture
def extendedConfigDataBackend(configDataBackend):
    """
    Returns an `OPSI.Backend.ExtendedConfigDataBackend` for testing.

    This will return multiple backends but some of these may lead to
    skips if required libraries are missing or conditions for the
    execution are not met.
    """
    yield ExtendedConfigDataBackend(configDataBackend)


@pytest.yield_fixture
def cleanableDataBackend(_serverBackend):
    """
    Returns an backend that can be cleaned.
    """
    yield ExtendedConfigDataBackend(_serverBackend)


@pytest.yield_fixture(
    params=[getFileBackend, getMySQLBackend],
    ids=['file', 'mysql']
)
def _serverBackend(request):
    "Shortcut to specify backends used on an opsi server."

    with request.param() as backend:
        with _backendBase(backend):
            yield backend


@pytest.yield_fixture
def backendManager(_serverBackend):
    """
    Returns an `OPSI.Backend.BackendManager.BackendManager` for testing.

    The returned instance is set up to have access to backend extensions.
    """
    defaultConfigDir = _getOriginalBackendLocation()

    with workInTemporaryDirectory() as tempDir:
        shutil.copytree(defaultConfigDir, os.path.join(tempDir, 'etc', 'opsi'))

        yield BackendManager(
            backend=_serverBackend,
            extensionconfigdir=os.path.join(tempDir, 'etc', 'opsi', 'backendManager', 'extend.d')
        )


@pytest.yield_fixture
def licenseManagementBackend(_sqlBackend):
    '''Returns a backend that can handle License Management.'''
    yield ExtendedConfigDataBackend(_sqlBackend)


@pytest.yield_fixture(
    params=[getSQLiteBackend, getMySQLBackend],
    ids=['sqlite', 'mysql']
)
def _sqlBackend(request):
    '''Backends that make use of SQL.'''

    with request.param() as backend:
        with _backendBase(backend):
            yield backend


def pytest_runtest_setup(item):
    envmarker = item.get_marker("requiresModulesFile")
    if envmarker is not None:
        if not os.path.exists(os.path.join('/etc', 'opsi', 'modules')):
            pytest.skip("{0} requires a modules file!".format(item.name))

    envmarker = item.get_marker("requiresHwauditConfigFile")
    if envmarker is not None:
        if not os.path.exists(os.path.join('/etc', 'opsi', 'hwaudit', 'opsihwaudit.conf')):
            pytest.skip("{0} requires a opsihwaudit.conf in /etc/opsi/hwaudit!".format(item.name))
