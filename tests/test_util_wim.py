# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2018 uib GmbH <info@uib.de>

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
Testing working with WIM files.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path
from contextlib import contextmanager

import pytest

from OPSI.Util.WIM import getImageInformation, parseWIM

from .helpers import workInTemporaryDirectory, mock


@contextmanager
def fakeWIMEnvironment(tempDir=None):
    with workInTemporaryDirectory(tempDir) as temporaryDir:
        fakeWimPath = os.path.join(temporaryDir, 'fake.wim')
        with open(fakeWimPath, 'w'):
            pass

        exampleData = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'testdata', 'wimlib.example')

        def fakeReturningOutput(_unused):
            with open(exampleData, 'r', 'utf-8') as f:
                return f.readlines()

        with mock.patch('OPSI.Util.WIM.which', lambda x: '/usr/bin/echo'):
            with mock.patch('OPSI.Util.WIM.execute', fakeReturningOutput):
                yield fakeWimPath


@pytest.fixture
def fakeWimPath():
    with fakeWIMEnvironment() as fakeWimPath:
        yield fakeWimPath


def testParsingNonExistingWimFileFails():
    with pytest.raises(OSError):
        parseWIM('not_here.wim')


def testParsingWIMReturnNoInformationFails(fakeWimPath):
    with mock.patch('OPSI.Util.WIM.execute', lambda x: ['']):
        with pytest.raises(ValueError):
            parseWIM(fakeWimPath)


def testParsingWIM(fakeWimPath):
    imageData = {
        'Windows 7 STARTERN': (set(['de-DE']), 'de-DE'),
        'Windows 7 HOMEBASICN': (set(['de-DE']), 'de-DE'),
        'Windows 7 HOMEPREMIUMN': (set(['de-DE']), 'de-DE'),
        'Windows 7 PROFESSIONALN': (set(['de-DE']), 'de-DE'),
        'Windows 7 ULTIMATEN': (set(['de-DE']), 'de-DE'),
    }

    for image in parseWIM(fakeWimPath):
        assert image.name in imageData

        assert image.languages == imageData[image.name][0]
        assert image.default_language == imageData[image.name][1]

        del imageData[image.name]

    assert not imageData, "Missed reading info for {0}".format(imageData.keys())


def testReadingImageInformationFromWim(fakeWimPath):
    infos = getImageInformation(fakeWimPath)

    for _ in range(5):
        info = next(infos)
        assert info

    with pytest.raises(StopIteration):  # Only five infos in example.
        next(infos)
