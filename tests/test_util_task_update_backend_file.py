# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017 uib GmbH <info@uib.de>

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
Testing the update of the MySQL backend from an older version.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path

from OPSI.Util.Task.UpdateBackend.File import updateFileBackend

from .Backends.File import getFileBackend

import pytest


@pytest.fixture
def fileBackend(tempDir):
    with getFileBackend(path=tempDir) as backend:
        yield backend


def testUpdatingFileBackend(fileBackend, tempDir):
    config = os.path.join(tempDir, 'etc', 'opsi', 'backends', 'file.conf')

    updateFileBackend(config)
