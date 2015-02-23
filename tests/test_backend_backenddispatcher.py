#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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
Testing BackendDispatcher.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import grp
import os
import pwd
import shutil
import tempfile
import unittest

from OPSI.Backend.BackendManager import BackendDispatcher
from OPSI.Types import BackendConfigurationError


class BackendDispatcherTestCase(unittest.TestCase):
    def testBackendCreationFailsIfConfigMissing(self):
        self.assertRaises(BackendConfigurationError, BackendDispatcher)

        self.assertRaises(BackendConfigurationError, BackendDispatcher, dispatchConfigfile='')
        self.assertRaises(BackendConfigurationError, BackendDispatcher, dispatchConfigfile='nope')

        self.assertRaises(BackendConfigurationError, BackendDispatcher, dispatchConfig='')

        self.assertRaises(BackendConfigurationError, BackendDispatcher, dispatchConfig=[[u'.*', [u'file']]])


class BackendDispatcherWithFilesTestCase(unittest.TestCase):
    """
    Testing the BackendDispatcher with files on the disk.

    This will create files that look like an actual backend to simulate
    correct loading of backend information.
    """
    def setUp(self):
        self.testDir = tempfile.mkdtemp()
        self.backendDir = os.path.join(self.testDir, 'backends')

    def tearDown(self):
        if os.path.exists(self.testDir):
            shutil.rmtree(self.testDir)

    def testLoadingDispatchConfigFailsIfBackendConfigMissing(self):
        self.assertRaises(
            BackendConfigurationError,
            BackendDispatcher,
            dispatchConfig=[[u'.*', [u'file']]],
            backendConfigDir=self.backendDir
        )

        os.mkdir(self.backendDir)
        self.assertRaises(
            BackendConfigurationError,
            BackendDispatcher,
            dispatchConfig=[[u'.*', [u'file']]],
            backendConfigDir=self.backendDir
        )

    def testLoadingDispatchConfig(self):
        self.createTestBackendConfiguration()

        dispatcher = BackendDispatcher(dispatchConfig=[[u'.*', [u'file']]],
                                        backendConfigDir=self.backendDir)

    def createTestBackendConfiguration(self):
        os.mkdir(self.backendDir)

        currentGroupId = os.getgid()
        groupName = grp.getgrgid(currentGroupId)[0]
        userName = pwd.getpwuid(os.getuid())[0]

        with open(os.path.join(self.backendDir, 'file.conf'), 'w') as config:
            new_configuration = """
# -*- coding: utf-8 -*-

module = 'File'
config = {{
    "fileGroupName": u"{groupName}",
    "fileUserName": u"{userName}",
}}
""".format(groupName=groupName, userName=userName)

            config.write(new_configuration)


if __name__ == '__main__':
    unittest.main()
