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

from functools import wraps
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from . import BackendMixin

try:
    from unittest import SkipTest
except ImportError:
    # Running Python < 2.7
    SkipTest = None

try:
    from .config import MySQLconfiguration
except ImportError:
    MySQLconfiguration = None


def skipTest(condition, reason):
    def skipWrapper(function):
        @wraps(function)
        def returnedWrapper(*args, **kwargs):
            if not condition:
                return function(*args, **kwargs)

            if SkipTest is not None:
                raise SkipTest(reason)
            else:
                # def nothingFunc(*args, **kwargs):
                print('Skipping test: {0}'.format(function.func_name))

                # return nothingFunc(*args, **kwargs)

        return  returnedWrapper

    return skipWrapper

# self.backendFixture.licenseManagement # war das True?
#     inventoryHistory = True


class MySQLBackendMixin(BackendMixin):

    CREATES_INVENTORY_HISTORY = True

    @skipTest(not MySQLconfiguration, "No MySQL configuration given.")
    def setUpBackend(self):
        self.backend = ExtendedConfigDataBackend(MySQLBackend(**MySQLconfiguration))
        self.backend.backend_createBase()

    def tearDownBackend(self):
        self.backend.backend_deleteBase()
