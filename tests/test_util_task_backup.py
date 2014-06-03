#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing the task to backup opsi.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import mock
import sys
import unittest

from OPSI.Util.Task.Backup import OpsiBackup


class BackupTestCase(unittest.TestCase):
    def testVerifySysConfigDoesNotFailBecauseWhitespaceAtEnd(self):
        class FakeSysInfo(object):
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        backup = OpsiBackup()

        archive = {
            'distribution': 'SUSE Linux Enterprise Server'
        }
        system = FakeSysInfo(
            distribution='SUSE Linux Enterprise Server '
        )

        self.assertEquals(
            {},
            backup._getDifferencesInSysConfig(
                archive,
                sysInfo=system
            )
        )

    def testPatchingStdout(self):
        fake = 'fake'
        backup = OpsiBackup(stdout=fake)
        self.assertEquals(fake, backup.stdout)

        newBackup = OpsiBackup()
        self.assertEquals(sys.stdout, newBackup.stdout)

    def testGettingArchive(self):
        fakeBackendDir = os.path.join(os.path.dirname(__file__), '..', 'data', 'backends')
        fakeBackendDir = os.path.normpath(fakeBackendDir)

        with mock.patch('OPSI.System.Posix.SysInfo.opsiVersion'):
            with mock.patch('OPSI.Util.Task.Backup.OpsiBackupArchive.BACKEND_CONF_DIR', fakeBackendDir):
                backup = OpsiBackup()
                archive = backup._getArchive('r')

if __name__ == '__main__':
    unittest.main()
