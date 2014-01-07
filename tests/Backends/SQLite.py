#-*- coding: utf-8 -*-
#
# Copyright (C) 2013 uib GmbH
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

from OPSI.Backend.SQLite import SQLiteBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from . import BackendMixin

try:
    from .config import SQLiteconfiguration
except ImportError:
    SQLiteconfiguration = {}


class SQLiteBackendMixin(BackendMixin):

    CREATES_INVENTORY_HISTORY = True

    def setUpBackend(self):
        self.backend = ExtendedConfigDataBackend(SQLiteBackend(**SQLiteconfiguration))
        self.backend.backend_createBase()

    def tearDownBackend(self):
        self.backend.backend_deleteBase()
