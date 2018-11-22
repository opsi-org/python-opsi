# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2018 uib GmbH <info@uib.de>

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
Testing the work with archives.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os

import pytest

from OPSI.Util.File.Archive import getFileType, Archive, PigzMixin, TarArchive

from .helpers import mock


def testArchiveFactoryRaisesExceptionOnUnknownFormat():
    with pytest.raises(Exception):
        Archive('no_filename', format='unknown')


@pytest.mark.parametrize("fileFormat", ["tar", "cpio"])
def testCreatingArchive(fileFormat):
    Archive('no_file', format=fileFormat)


def testRaisingExceptionIfFiletypeCanNotBeDetermined():
    with pytest.raises(Exception):
        Archive(__file__)


def testPigzDetectionOnTarArchive():
    assert PigzMixin.is_pigz_available() == TarArchive.is_pigz_available()


@pytest.fixture
def dumbArchive():
    class DumbArchive(PigzMixin):
        pass

    yield DumbArchive()


def testPigzMixinProvidesMethods(dumbArchive):
    assert hasattr(dumbArchive, 'pigz_detected')
    assert hasattr(dumbArchive, 'is_pigz_available')


def testPigzMixinMethods(dumbArchive):
    assert PigzMixin.is_pigz_available() == dumbArchive.pigz_detected
    assert PigzMixin.is_pigz_available() == dumbArchive.is_pigz_available()


def testDisablingPigz(dumbArchive):
    """
    Disabling the usage of pigz by setting PIGZ_ENABLED to False.
    """
    with mock.patch('OPSI.Util.File.Archive.PIGZ_ENABLED', False):
        assert dumbArchive.is_pigz_available() is False


@pytest.fixture(params=[('Python', __file__)])
# TODO: enhance this with more files...
def filenameAndExpectedType(request):
    yield request.param


def testGetFileType(filenameAndExpectedType):
    expectedType, filename = filenameAndExpectedType
    assert expectedType.lower() in getFileType(filename).lower()


def testGetFileTypeFollowsSymlink(filenameAndExpectedType, tempDir):
    expectedType, filename = filenameAndExpectedType

    linkFile = os.path.join(tempDir, 'mylink')
    os.symlink(filename, linkFile)

    assert expectedType.lower() in getFileType(linkFile).lower()
