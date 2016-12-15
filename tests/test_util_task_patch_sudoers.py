# -*- coding: utf-8 -*-

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
import pytest

from .helpers import mock, createTemporaryTestfile, workInTemporaryDirectory

from OPSI.System import which
from OPSI.Util.Task.Sudoers import (_NO_TTY_FOR_SERVICE_REQUIRED,
    _NO_TTY_REQUIRED_DEFAULT, FILE_ADMIN_GROUP, patchSudoersFileForOpsi,
    patchSudoersFileToAllowRestartingDHCPD)


SUDOERS_WITHOUT_ENTRIES = os.path.join(
    os.path.dirname(__file__),
    'testdata', 'util', 'task', 'sudoers', 'sudoers_without_entries'
)


@pytest.fixture
def temporarySudoersFile():
    with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES) as fileName:
        yield fileName


def testDoNotAlterFileIfEntryAlreadyExisting(temporarySudoersFile):
    fileName = temporarySudoersFile
    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as first:
        contentAfterFirstPatch = first.readlines()

    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as second:
        contentAfterSecondPatch = second.readlines()

    assert contentAfterFirstPatch == contentAfterSecondPatch


def testAlterFileIfPartOfPreviousPatchWasMissing(temporarySudoersFile):
    fileName = temporarySudoersFile
    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as before:
        lines = before.readlines()

    lines = [line for line in lines if not line.startswith('opsiconfd')]
    with open(fileName, 'w') as before:
        before.writelines(lines)

    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as after:
        assert any(line.startswith('opsiconfd') for line in after)


def testFileEndsWithNewline(temporarySudoersFile):
    patchSudoersFileForOpsi(sudoersFile=temporarySudoersFile)

    with open(temporarySudoersFile) as changedFile:
        for line in changedFile:
            lastLine = line

        assert '\n' == lastLine


def testBackupIsCreated():
    def showFolderInfo():
        print(u'Files in {0}: {1}'.format(tempFolder, filesInTemporaryFolder))

    with workInTemporaryDirectory() as tempFolder:
        with createTemporaryTestfile(SUDOERS_WITHOUT_ENTRIES, tempDir=tempFolder) as fileName:
            filesInTemporaryFolder = os.listdir(tempFolder)

            showFolderInfo()
            assert 1 == len(filesInTemporaryFolder)

            patchSudoersFileForOpsi(sudoersFile=fileName)

            filesInTemporaryFolder = os.listdir(tempFolder)
            showFolderInfo()
            assert 2 == len(filesInTemporaryFolder)


def testOpsiconfdDoesNotRequireTTY(temporarySudoersFile):
    fileName = temporarySudoersFile

    with open(fileName) as pre:
        for line in pre:
            if _NO_TTY_REQUIRED_DEFAULT in line:
                pytest.skip(u'Command already existing. Can\'t check.')

    with mock.patch('OPSI.Util.Task.Sudoers.distributionRequiresNoTtyPatch', lambda: True):
        patchSudoersFileForOpsi(fileName)

    with open(fileName) as post:
        assert any(_NO_TTY_REQUIRED_DEFAULT in line for line in post), u"Expected {0} in patched file.".format(_NO_TTY_REQUIRED_DEFAULT)


def testExecutingServiceDoesNotRequireTTY(temporarySudoersFile):
    fileName = temporarySudoersFile
    with open(fileName) as pre:
        for line in pre:
            if _NO_TTY_FOR_SERVICE_REQUIRED in line:
                pytest.skip(u'Command already existing. Can\'t check.')

    patchSudoersFileForOpsi(fileName)

    with open(fileName) as post:
        assert any(_NO_TTY_FOR_SERVICE_REQUIRED in line for line in post), u"Expected {0} in patched file.".format(_NO_TTY_FOR_SERVICE_REQUIRED)


def testServiceLineHasRightPathToService():
    try:
        path = which('service')
        assert path in _NO_TTY_FOR_SERVICE_REQUIRED
    except Exception:
        pytest.skip(u"Cant't find 'service' in path.")


@pytest.mark.parametrize("command", [
    u"service dhcpd restart",
    ])
def testPatchingToAllowRestartingDHCPD(temporarySudoersFile, command):
    fileName = temporarySudoersFile
    with open(fileName) as pre:
        for line in pre:
            if command in line:
                pytest.skip(u"Command {0!r} already existing.".format(command))

    patchSudoersFileToAllowRestartingDHCPD(command, fileName)

    with open(fileName) as post:
        assert any(command in line for line in post)


def testDoNotAddDuplicates(temporarySudoersFile):
    adminGroup = u'%{0}'.format(FILE_ADMIN_GROUP)

    fileName = temporarySudoersFile
    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as before:
        lines = before.readlines()

    lines = [line for line in lines if not line.startswith('opsiconfd')]
    assert 1 == len([line for line in lines if line.startswith(adminGroup)])

    with open(fileName, 'w') as before:
        before.writelines(lines)

    patchSudoersFileForOpsi(sudoersFile=fileName)
    with open(fileName) as after:
        afterLines = after.readlines()

    assert 1 == len([line for line in afterLines if line.startswith(adminGroup)])
