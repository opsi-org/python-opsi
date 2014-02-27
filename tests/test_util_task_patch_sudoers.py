#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013 uib GmbH <info@uib.de>

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

from __future__ import unicode_literals

import os
import shutil
import unittest

import helpers

from OPSI.Util.Task.Sudoers import (_NO_TTY_REQUIRED_DEFAULT,
    patchSudoersFileForOpsi, distributionRequiresNoTtyPatch)


class PatchSudoersFileForOpsiTestCase(unittest.TestCase):
    def setUp(self):
        emptyExampleFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'task', 'sudoers','sudoers_without_entries'
        )

        self.fileName = helpers.copyTestfileToTemporaryFolder(emptyExampleFile)

    def tearDown(self):
        tempDirectory = os.path.dirname(self.fileName)
        if os.path.exists(tempDirectory):
            shutil.rmtree(tempDirectory)

        del self.fileName

    def testDoNotAlterFileIfEntryAlreadyExisting(self):
        patchSudoersFileForOpsi(sudoersFile=self.fileName)
        with open(self.fileName) as first:
            contentAfterFirstPatch = first.readlines()

        patchSudoersFileForOpsi(sudoersFile=self.fileName)
        with open(self.fileName) as second:
            contentAfterSecondPatch = second.readlines()

        self.assertEqual(contentAfterFirstPatch, contentAfterSecondPatch)

    def testFileEndsWithNewline(self):
        patchSudoersFileForOpsi(sudoersFile=self.fileName)

        with open(self.fileName) as changedFile:
            for line in changedFile:
                lastLine = line

            self.assertTrue('\n' == lastLine)

    def testBackupIsCreated(self):
        def showFolderInfo():
            print('Files in {0}: {1}'.format(tempFolder, filesInTemporaryFolder))

        tempFolder = os.path.dirname(self.fileName)
        filesInTemporaryFolder = os.listdir(tempFolder)

        showFolderInfo()
        self.assertEqual(1, len(filesInTemporaryFolder))

        patchSudoersFileForOpsi(sudoersFile=self.fileName)

        filesInTemporaryFolder = os.listdir(tempFolder)
        showFolderInfo()
        self.assertEqual(2, len(filesInTemporaryFolder))

    @unittest.skipIf(not distributionRequiresNoTtyPatch(), 'Distribution not affected.')
    def testOpsiconfdDoesNotRequireTTY(self):
        # TODO: patch the distributionCheckFunction so this works with all OS
        with open(self.fileName) as pre:
            for line in pre:
                if _NO_TTY_REQUIRED_DEFAULT in line:
                    self.fail()

        patchSudoersFileForOpsi(self.fileName)

        entryFound = False
        with open(self.fileName) as post:
            for line in post:
                if _NO_TTY_REQUIRED_DEFAULT in line:
                    entryFound = True

        self.assertTrue(
            entryFound,
            "Expected {0} in patched file.".format(_NO_TTY_REQUIRED_DEFAULT)
        )

if __name__ == '__main__':
    unittest.main()
