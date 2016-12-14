#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015 uib GmbH <info@uib.de>

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

from __future__ import absolute_import

import os
import unittest

from OPSI.Types import RepositoryError
from OPSI.Util.Repository import FileRepository, getRepository

from .helpers import workInTemporaryDirectory


class GetRepositoryTestCase(unittest.TestCase):
    def testGettingFileRepository(self):
        repo = getRepository("file:///not-here")
        self.assertTrue(isinstance(repo, FileRepository))

    def testFailingOnUnsupportedURL(self):
        self.assertRaises(RepositoryError, getRepository, "lolnope:///asdf")


class FileRepositoryTestCase(unittest.TestCase):
    def testListingRepository(self):
        with workInTemporaryDirectory() as tempDir:
            repo = FileRepository(url=u'file://{path}'.format(path=tempDir))
            for content in repo.content('', recursive=True):
                self.fail("Should be empty.")

            os.mkdir(os.path.join(tempDir, "foobar"))

            self.assertEquals(1, len(repo.content('', recursive=True)))
            for content in repo.content('', recursive=True):
                self.assertEquals({'path': u'foobar', 'type': 'dir', 'name': u'foobar', 'size': 0}, content)

            with open(os.path.join(tempDir, "bar"), "w"):
                pass

            self.assertEquals(2, len(repo.content('', recursive=True)))
            self.assertEquals(2, len(repo.listdir()))
            self.assertTrue("bar" in repo.listdir())

    def testFailWithWrongURL(self):
        self.assertRaises(RepositoryError, FileRepository, u'nofile://nada')


if __name__ == '__main__':
    unittest.main()
