# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
Testing the work with repositories.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import pytest

from OPSI.Exceptions import RepositoryError
from OPSI.Util.Repository import FileRepository, getRepository


def testGettingFileRepository():
    repo = getRepository("file:///not-here")
    assert isinstance(repo, FileRepository)


def testGettingRepositoryFailsOnUnsupportedURL():
    with pytest.raises(RepositoryError):
        getRepository("lolnope:///asdf")


def testListingRepository(tempDir):
    repo = FileRepository(url=u'file://{path}'.format(path=tempDir))
    assert not repo.content('', recursive=True)

    os.mkdir(os.path.join(tempDir, "foobar"))

    assert 1 == len(repo.content('', recursive=True))
    for content in repo.content('', recursive=True):
        assert content == {'path': u'foobar', 'type': 'dir', 'name': u'foobar', 'size': 0}

    with open(os.path.join(tempDir, "bar"), "w"):
        pass

    assert 2 == len(repo.content('', recursive=True))
    assert 2 == len(repo.listdir())
    assert "bar" in repo.listdir()

    # TODO: list subdir tempDir and check if file is shown


def testFileRepositoryFailsWithWrongURL():
    with pytest.raises(RepositoryError):
        FileRepository(u'nofile://nada')
