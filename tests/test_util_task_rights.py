#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
from contextlib import contextmanager

from OPSI.Util.Task.Rights import (chown, getApacheRepositoryPath,
    getDirectoriesManagedByOpsi, getDirectoriesForProcessing,
    getDirectoriesAndExpectedRights)

from .helpers import mock, unittest, workInTemporaryDirectory

import pytest


@pytest.mark.parametrize("sles_support, workbench, tftpdir", [
    (False, u'/home/opsiproducts', u'/tftpboot/linux'),
    (True, u'/var/lib/opsi/workbench', u'/var/lib/tftpboot/opsi')
], ids=["sles", "non-sles"])
def testGetDirectoriesToProcess(sles_support, workbench, tftpdir):
    with mock.patch('OPSI.Util.Task.Rights.isSLES', mock.Mock(return_value=sles_support)):
        directories = getDirectoriesManagedByOpsi()

    assert u'/etc/opsi' in directories
    assert u'/var/lib/opsi' in directories
    assert u'/var/log/opsi' in directories
    assert workbench in directories
    assert tftpdir in directories


@pytest.yield_fixture
def depotDirectory():
    depotUrl = u'file:///var/lib/opsi/depot'
    with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', lambda: depotUrl):
        yield depotUrl


def testGettingDirectories(depotDirectory):
    directories, _ = getDirectoriesForProcessing('/tmp')
    assert len(directories) > 2


@pytest.mark.parametrize("testDir", [
    '/opt/pcbin/install/foo',
    pytest.mark.xfail('/tmp'),
])
def testOptPcbinGetRelevantIfInParameter(depotDirectory, testDir):
    directories, _ = getDirectoriesForProcessing(testDir)
    assert '/opt/pcbin/install' in directories


def testDepotPathMayAlsoExistInDirectories(depotDirectory):
    depotDirToCheck = depotDirectory.split('file://', 1)[1]

    directories, depotDir = getDirectoriesForProcessing(depotDirToCheck)

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


@pytest.yield_fixture
def patchUserInfo():
    with mock.patch('OPSI.Util.Task.Rights.pwd.getpwnam', return_value=(None, None, 1234)):
        with mock.patch('OPSI.Util.Task.Rights.grp.getgrnam', return_value=(None, None, 5678)):
            yield


def testGettingDirectoriesAndRights(patchUserInfo):
    dm = dict(getDirectoriesAndExpectedRights('/'))
    print(dm)

    for rights in dm.values():
        # For now we just want to make sure these fields are filled.
        assert rights.uid
        assert rights.gid

    rights = dm[u'/etc/opsi']
    print(rights)
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert rights.correctLinks

    rights = dm[u'/var/lib/opsi']
    print(rights)
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert not rights.correctLinks

    rights = dm[u'/var/log/opsi']
    print(rights)
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert rights.correctLinks


@pytest.mark.parametrize("dir, function", [
    ('/var/www/html/opsi', 'isCentOS'),
    ('/var/www/html/opsi', 'isDebian'),
    ('/srv/www/htdocs/opsi', 'isOpenSUSE'),
    ('/var/www/html/opsi', 'isRHEL'),
    ('/var/www/html/opsi', 'isSLES'),
    ('/var/www/html/opsi', 'isUbuntu'),
    ('/var/www/html/opsi', 'isUCS'),
    pytest.mark.xfail(('/var/www/html/opsi', 'getDirectoriesManagedByOpsi')),
    (None, 'getDirectoriesManagedByOpsi'),
])
def testGettingApacheRepositoryPath(dir, function):
    functions = ['isRHEL', 'isCentOS', 'isSLES', 'isOpenSUSE', 'isUbuntu', 'isDebian', 'isUCS']

    with disableOSChecks(functions):
        with mock.patch('OPSI.Util.Task.Rights.{0}'.format(function), lambda: True):
            assert dir == getApacheRepositoryPath()


@contextmanager
def disableOSChecks(functions):
    try:
        func = functions.pop()
        with mock.patch('OPSI.Util.Task.Rights.{0}'.format(func), return_value=False):
            with disableOSChecks(functions):
                yield
    except IndexError:
        yield
