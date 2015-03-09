#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2015 uib GmbH <info@uib.de>

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
Testing the setting of rights.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import unittest

from OPSI.Util.Task.Rights import getDirectoriesToProcess, removeDuplicatesFromDirectories


class SetRightsTestCase(unittest.TestCase):
    def testGetDirectoriesToProcess(self):
        directories = getDirectoriesToProcess()

        self.assertTrue(u'/var/log/opsi' in directories)
        self.assertTrue(u'/etc/opsi' in directories)
        self.assertTrue(u'/var/lib/opsi' in directories)

        # TODO: make a test for that patches reading the distribution and pretend to be SLES
        # if 'suse linux enterprise server' in distribution.lower():
        #     return [u'/var/lib/tftpboot/opsi', u'/var/lib/opsi/workbench']
        # else:
        #     return [u'/tftpboot/linux', u'/home/opsiproducts', ]

    def testCleaningDirectoryList(self):
        self.assertEquals(
            set(['/home', '/etc']),
            removeDuplicatesFromDirectories(['/home/', '/etc'])
        )

        self.assertEquals(
            set(['/home']),
            removeDuplicatesFromDirectories(['/home/', '/home/'])
        )

        self.assertEquals(
            set(['/home']),
            removeDuplicatesFromDirectories(['/home/', '/home/abc'])
        )

        self.assertEquals(
            set(['/home']),
            removeDuplicatesFromDirectories(['/home/abc/', '/home/', '/home/def/ghi'])
        )


if __name__ == '__main__':
    unittest.main()
