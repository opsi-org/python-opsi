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

import pytest

from OPSI.Backend.MySQL import MySQLBackend, MySQLBackendObjectModificationTracker

try:
    from .config import MySQLconfiguration
except ImportError:
    MySQLconfiguration = None


@contextmanager
def getMySQLBackend():
    if not MySQLconfiguration:
        pytest.skip('no MySQL backend configuration given.')

    yield MySQLBackend(**MySQLconfiguration)


@contextmanager
def getMySQLModificationTracker():
    if not MySQLconfiguration:
        pytest.skip('no MySQL backend configuration given.')

    yield MySQLBackendObjectModificationTracker(**MySQLconfiguration)
