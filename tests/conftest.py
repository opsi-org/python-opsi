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

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os

from OPSI.Backend.Backend import ExtendedConfigDataBackend

from .Backends.File import getFileBackend
from .Backends.SQLite import getSQLiteBackend

import pytest


@pytest.yield_fixture(
    params=[getFileBackend, getSQLiteBackend],
    ids=['file backend', 'SQLite backend']
)
def configDataBackend(request):
    """
    Returns an `OPSI.Backend.ConfigDataBackend` for testing.

    This will return multiple backends but some of these may lead to
    skips if required libraries are missing or conditions for the
    execution are not met.
    """
    with request.param() as backend:
        yield backend


@pytest.yield_fixture
def extendedConfigDataBackend(configDataBackend):
    """
    Returns an `OPSI.Backend.ExtendedConfigDataBackend` for testing.

    This will return multiple backends but some of these may lead to
    skips if required libraries are missing or conditions for the
    execution are not met.
    """
    yield ExtendedConfigDataBackend(configDataBackend)


def pytest_runtest_setup(item):
    envmarker = item.get_marker("requiresModulesFile")
    if envmarker is not None:
        if not os.path.exists(os.path.join('/etc', 'opsi', 'modules')):
            raise pytest.skip("This test requires a modules file!")
