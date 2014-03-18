#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
