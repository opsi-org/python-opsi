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

from __future__ import absolute_import, print_function

import grp
import os
import os.path
import pwd

from OPSI.Util.Task.Rights import (getDirectoriesManagedByOpsi, getDirectoriesForProcessing,
    removeDuplicatesFromDirectories, chown)

from .helpers import mock, unittest, workInTemporaryDirectory


class SetRightsTestCase(unittest.TestCase):
    def testGetDirectoriesToProcess(self):
        with mock.patch('OPSI.Util.Task.Rights.isSLES', mock.Mock(return_value=False)):
            directories = getDirectoriesManagedByOpsi()

        self.assertTrue(u'/home/opsiproducts' in directories)
        self.assertTrue(u'/etc/opsi' in directories)
        self.assertTrue(u'/tftpboot/linux' in directories)
        self.assertTrue(u'/var/lib/opsi' in directories)
        self.assertTrue(u'/var/log/opsi' in directories)

    def testGetDirectoriesToProcessOnSLES(self):
        with mock.patch('OPSI.Util.Task.Rights.isSLES', mock.Mock(return_value=True)):
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

    def testDepotPathMayAlsoExistInDirectories(self):
        with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', lambda: u'file:///var/lib/opsi/depot'):
            directories, depotDir = getDirectoriesForProcessing('/var/lib/opsi/depot/')

        print("Directories: {0}".format(directories))
        assert '/var/lib/opsi' in directories
        print("depotDir: {0}".format(depotDir))
        assert depotDir == '/var/lib/opsi/depot'


class ChownTestCase(unittest.TestCase):

    def testChangingOwnership(self):
        try:
            groupId = os.getgid()
            userId = os.getuid()
        except Exception as exc:
            print("Could not get uid/guid: {0}".format(exc))
            self.skipTest("Could not get uid/guid: {0}".format(exc))

        print("Current group ID: {0}".format(groupId))
        print("Current user ID: {0}".format(userId))
        isRoot = os.geteuid() == 0

        for gid in range(2, 60000):
            try:
                grp.getgrgid(gid)
                changedGid = gid
                break
            except KeyError:
                pass
        else:
            self.skipTest("No group for test found. Aborting.")

        if groupId == changedGid:
            self.skipTest("Could not find another group.")

        if isRoot:
            for uid in range(2, 60000):
                try:
                    pwd.getpwuid(uid)
                    changedUid = uid
                    break
                except KeyError:
                    pass
            else:
                self.skipTest("No userId for test found. Aborting.")

            if userId == changedUid:
                self.skipTest("Could not find another user.")
        else:
            changedUid = -1

        with workInTemporaryDirectory() as tempDir:
            original = os.path.join(tempDir, 'original')
            with open(original, 'w'):
                pass

            linkfile = os.path.join(tempDir, 'linkfile')
            os.symlink(original, linkfile)
            self.assertTrue(os.path.islink(linkfile))

            # Changing the uid/gid to something different
            os.chown(original, changedUid, changedGid)
            os.lchown(linkfile, changedUid, changedGid)

            for filename in (original, linkfile):
                if os.path.islink(filename):
                    stat = os.lstat(filename)
                else:
                    stat = os.stat(linkfile)

                self.assertEquals(changedGid, stat.st_gid)
                if not isRoot:
                    self.assertEquals(changedUid, stat.st_uid)

            # Correcting the uid/gid
            chown(linkfile, userId, groupId)
            chown(original, userId, groupId)

            for filename in (original, linkfile):
                if os.path.islink(filename):
                    stat = os.lstat(filename)
                else:
                    stat = os.stat(linkfile)

                self.assertEquals(groupId, stat.st_gid)
                if not isRoot:
                    self.assertEquals(userId, stat.st_uid)


if __name__ == '__main__':
    unittest.main()
