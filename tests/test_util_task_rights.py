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

import mock
import unittest

from OPSI.Util.Task.Rights import (getDirectoriesManagedByOpsi, getDirectoriesForProcessing,
    removeDuplicatesFromDirectories)


class SetRightsTestCase(unittest.TestCase):
    def testGetDirectoriesToProcess(self):
        with mock.patch('OPSI.Util.Task.Rights._isSLES', mock.Mock(return_value=False)):
            directories = getDirectoriesManagedByOpsi()

        self.assertTrue(u'/home/opsiproducts' in directories)
        self.assertTrue(u'/etc/opsi' in directories)
        self.assertTrue(u'/tftpboot/linux' in directories)
        self.assertTrue(u'/var/lib/opsi' in directories)
        self.assertTrue(u'/var/log/opsi' in directories)

    def testGetDirectoriesToProcessOnSLES(self):
        with mock.patch('OPSI.Util.Task.Rights._isSLES', mock.Mock(return_value=True)):
            directories = getDirectoriesManagedByOpsi()

        self.assertTrue(u'/var/log/opsi' in directories)
        self.assertTrue(u'/etc/opsi' in directories)
        self.assertTrue(u'/var/lib/opsi' in directories)
        self.assertTrue(u'/var/lib/tftpboot/opsi' in directories)
        self.assertTrue(u'/var/lib/opsi/workbench' in directories)

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

        self.assertEquals(
            set(['/']),
            removeDuplicatesFromDirectories(['/home/', '/etc', '/'])
        )

        self.assertEquals(
            set(['/a/bc/de', '/ab/c', '/bc/de']),
            removeDuplicatesFromDirectories(['/a/bc/de', '/ab/c', '/bc/de'])
        )

    def testIgnoringSubfolders(self):
        """
        Subfolder should be ignored - real world testcase.

        Running this on old opsi servers might cause problems if
        they link /opt/pcbin/install to /var/lib/opsi/depot.
        That's the reason for the patch.
        """
        def fakeRealpath(path):
            return path

        with mock.patch('OPSI.Util.Task.Rights.os.path.realpath', fakeRealpath):
            self.assertEquals(
                set([u'/var/log/opsi', u'/tftpboot/linux', u'/home/opsiproducts', u'/etc/opsi', u'/var/lib/opsi']),
                removeDuplicatesFromDirectories([u'/var/log/opsi', u'/var/lib/opsi/depot', u'/tftpboot/linux', u'/var/lib/opsi/depot', u'/home/opsiproducts', u'/etc/opsi', u'/var/lib/opsi'])
            )


class GetDirectoriesForProcessingTestCase(unittest.TestCase):
    def testGettingDirectories(self):
        directories, _ = getDirectoriesForProcessing('/tmp')

        self.assertTrue(len(directories) > 2)

    def testOptPcbinGetRelevantIfInParameter(self):
        directories, _ = getDirectoriesForProcessing('/opt/pcbin/install/foo')
        self.assertTrue('/opt/pcbin/install' in directories)

        directories, _ = getDirectoriesForProcessing('/tmp')
        self.assertTrue('/opt/pcbin/install' not in directories)


if __name__ == '__main__':
    unittest.main()
