#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Testing the patching of the sudoers file.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import os

from .helpers import mock, unittest, createTemporaryTestfile, workInTemporaryDirectory

from OPSI.System import which
from OPSI.Util.Task.Sudoers import (_NO_TTY_FOR_SERVICE_REQUIRED,
    _NO_TTY_REQUIRED_DEFAULT, FILE_ADMIN_GROUP, patchSudoersFileForOpsi,
    patchSudoersFileToAllowRestartingDHCPD)


SUDOERS_WITHOUT_ENTRIES = os.path.join(
    os.path.dirname(__file__),
    'testdata', 'util', 'task', 'sudoers', 'sudoers_without_entries'
)

class PatchSudoersFileForOpsiTestCase(unittest.TestCase):
    def testDoNotAlterFileIfEntryAlreadyExisting(self):
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as first:
                contentAfterFirstPatch = first.readlines()

            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as second:
                contentAfterSecondPatch = second.readlines()

        self.assertEqual(contentAfterFirstPatch, contentAfterSecondPatch)

    def testAlterFileIfPartOfPreviousPatchWasMissing(self):
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as before:
                lines = before.readlines()

            lines = [line for line in lines if not line.startswith('opsiconfd')]
            with open(fileName, 'w') as before:
                before.writelines(lines)

            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as after:
                for line in after:
                    if line.startswith('opsiconfd'):
                        self.assertTrue(True)
                        return

            self.fail(u"Missing line starting with 'opsiconfd'")

    def testFileEndsWithNewline(self):
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            patchSudoersFileForOpsi(sudoersFile=fileName)

            with open(fileName) as changedFile:
                for line in changedFile:
                    lastLine = line

                self.assertTrue('\n' == lastLine)

    def testBackupIsCreated(self):
        def showFolderInfo():
            print(u'Files in {0}: {1}'.format(tempFolder, filesInTemporaryFolder))

        with workInTemporaryDirectory() as tempFolder:
            with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES, tempDir=tempFolder) as fileName:
                filesInTemporaryFolder = os.listdir(tempFolder)

                showFolderInfo()
                self.assertEqual(1, len(filesInTemporaryFolder))

                patchSudoersFileForOpsi(sudoersFile=fileName)

                filesInTemporaryFolder = os.listdir(tempFolder)
                showFolderInfo()
                self.assertEqual(2, len(filesInTemporaryFolder))

    def testOpsiconfdDoesNotRequireTTY(self):
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            with open(fileName) as pre:
                for line in pre:
                    if _NO_TTY_REQUIRED_DEFAULT in line:
                        self.fail(u'Command already existing. Can\'t check.')

            with mock.patch('OPSI.Util.Task.Sudoers.distributionRequiresNoTtyPatch', lambda: True):
                patchSudoersFileForOpsi(fileName)

            entryFound = False
            with open(fileName) as post:
                for line in post:
                    if _NO_TTY_REQUIRED_DEFAULT in line:
                        entryFound = True

        self.assertTrue(
            entryFound,
            u"Expected {0} in patched file.".format(_NO_TTY_REQUIRED_DEFAULT)
        )

    def testExecutingServiceDoesNotRequireTTY(self):
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            with open(fileName) as pre:
                for line in pre:
                    if _NO_TTY_FOR_SERVICE_REQUIRED in line:
                        self.fail(u'Command already existing. Can\'t check.')

            patchSudoersFileForOpsi(fileName)

            entryFound = False
            with open(fileName) as post:
                for line in post:
                    if _NO_TTY_FOR_SERVICE_REQUIRED in line:
                        entryFound = True

        self.assertTrue(
            entryFound,
            u"Expected {0} in patched file.".format(_NO_TTY_FOR_SERVICE_REQUIRED)
        )

    def testServiceLineHasRightPathToService(self):
        try:
            path = which('service')
            self.assertTrue(path in _NO_TTY_FOR_SERVICE_REQUIRED)
        except Exception:
            self.skipTest(u"Cant't find 'service' in path.")

    def testPatchingToAllowRestartingDHCPD(self):
        serviceCommand = u"service dhcpd restart"

        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            with open(fileName) as pre:
                for line in pre:
                    if serviceCommand in line:
                        self.fail(u"Restart command already existing.")

            patchSudoersFileToAllowRestartingDHCPD(serviceCommand, fileName)

            entryFound = False
            with open(fileName) as post:
                for line in post:
                    if serviceCommand in line:
                        entryFound = True

        self.assertTrue(entryFound)

    def testDoNotAddDuplicates(self):
        adminGroup = u'%{0}'.format(FILE_ADMIN_GROUP)

        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as before:
                lines = before.readlines()

            lines = [line for line in lines if not line.startswith('opsiconfd')]
            self.assertEquals(len([line for line in lines if line.startswith(adminGroup)]), 1)

            with open(fileName, 'w') as before:
                before.writelines(lines)

            patchSudoersFileForOpsi(sudoersFile=fileName)
            with open(fileName) as after:
                afterLines = after.readlines()

        self.assertEquals(len([line for line in afterLines if line.startswith(adminGroup)]), 1)


if __name__ == '__main__':
    unittest.main()
