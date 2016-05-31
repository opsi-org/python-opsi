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
Testing the update of the MySQL backend from an older version.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os

from OPSI.Util.Task.UpdateBackend.MySQL import updateMySQLBackend
from OPSI.Util.Task.ConfigureBackend import updateConfigFile

from .Backends.MySQL import MySQLconfiguration
from .helpers import workInTemporaryDirectory

import pytest


def testCorrectingLicenseOnClientLicenseKeyLength():
    """
    Test if the license key length is correctly set.

    An backend updated from an older version has the field 'licenseKey'
    on the LICENSE_ON_CLIENT table as VARCHAR(100).
    A fresh backend has the length of 1024.
    The size should be the same.
    """
    if not MySQLconfiguration:
        pytest.skip("Missing configuration for MySQL.")

    with workInTemporaryDirectory() as tempDir:
        configFile = os.path.join(tempDir, 'asdf')
        with open(configFile, 'w'):
            pass

        updateConfigFile(configFile, MySQLconfiguration)

        # TODO: prepare the table the have a column length of just 100.

        updateMySQLBackend(backendConfigFile=configFile)

        # TODO: add
