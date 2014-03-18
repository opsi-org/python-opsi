#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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
Testing the backend configuration.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import unittest

import OPSI.Util.Task.ConfigureBackend as backendConfigUtils

from .helpers import copyTestfileToTemporaryFolder


class ConfigFileManagementTestCase(unittest.TestCase):

    def setUp(self):
        self.fileName = copyTestfileToTemporaryFolder(
                            os.path.join(
                                os.path.dirname(__file__), '..',
                                'data', 'backends', 'mysql.conf'
                            )
                        )

    def tearDown(self):
        if os.path.exists(self.fileName):
            os.remove(self.fileName)

        del self.fileName

    def testReadingMySQLConfigFile(self):
        config = backendConfigUtils.getBackendConfiguration(self.fileName)

        defaultMySQLConfig = {
            "address": u"localhost",
            "database": u"opsi",
            "username": u"opsi",
            "password": u"opsi",
            "databaseCharset": "utf8",
            "connectionPoolSize": 20,
            "connectionPoolMaxOverflow": 10,
            "connectionPoolTimeout": 30
        }

        self.assertEqual(config, defaultMySQLConfig)

    def testUpdatingTestConfigFile(self):
        config = backendConfigUtils.getBackendConfiguration(self.fileName)

        self.assertNotEqual('notYourCurrentPassword', config['password'])
        config['password'] = 'notYourCurrentPassword'
        backendConfigUtils.updateConfigFile(self.fileName, config)
        self.assertEqual('notYourCurrentPassword', config['password'])

        del config['address']
        del config['database']
        del config['password']

        backendConfigUtils.updateConfigFile(self.fileName, config)

        config = backendConfigUtils.getBackendConfiguration(self.fileName)
        for key in ('address', 'database', 'password'):
            self.assertTrue(
                key not in config,
                '{0} should not be in {1}'.format(key, config)
            )

        for key in ('username', 'connectionPoolMaxOverflow'):
            self.assertTrue(
                key in config,
                '{0} should be in {1}'.format(key, config)
            )


if __name__ == '__main__':
    unittest.main()
