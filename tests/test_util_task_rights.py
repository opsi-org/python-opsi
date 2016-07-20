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
    getDirectoriesAndExpectedRights,
    filterDirsAndRights, setRightsOnSSHDirectory, _getDepotDirectory)

from .helpers import mock, unittest, workInTemporaryDirectory

import pytest


@pytest.yield_fixture
def depotDirectory():
    'Returning a fixed address when checking for a depotUrl'
    depotUrl = u'file:///var/lib/opsi/depot'
    with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', lambda: depotUrl):
        yield depotUrl


@pytest.yield_fixture
def resetDepotDirectoryCache():
    'Making sure that no depotUrl is cached.'
    with mock.patch('OPSI.Util.Task.Rights._DEPOT_DIRECTORY', None):
        yield


@pytest.yield_fixture
def patchUserInfo():
    'Calls to find uid / gid will always succeed.'
    uid = 1234
    gid = 5678
    with mock.patch('OPSI.Util.Task.Rights.pwd.getpwnam', return_value=(None, None, uid)):
        with mock.patch('OPSI.Util.Task.Rights.grp.getgrnam', return_value=(None, None, gid)):
            yield uid, gid


@pytest.mark.parametrize("sles_support, workbench, tftpdir", [
    (False, u'/home/opsiproducts', u'/tftpboot/linux'),
    (True, u'/var/lib/opsi/workbench', u'/var/lib/tftpboot/opsi')
], ids=["sles", "non-sles"])
def testGetDirectoriesToProcess(patchUserInfo, sles_support, workbench, tftpdir):
    with mock.patch('OPSI.Util.Task.Rights.getApacheRepositoryPath', lambda: '/path/to/apache'):
        with mock.patch('OPSI.Util.Task.Rights.isSLES', lambda: sles_support):
            directories = [d for d, _ in filterDirsAndRights('/')]

    assert u'/etc/opsi' in directories
    assert u'/var/lib/opsi' in directories
    assert u'/var/log/opsi' in directories
    assert workbench in directories
    assert tftpdir in directories
    assert '/path/to/apache' in directories


def testGettingDirectories(patchUserInfo, depotDirectory):
    directories = [d for d, _ in getDirectoriesAndExpectedRights('/tmp')]
    assert len(directories) > 2


@pytest.mark.parametrize("testDir", [
    '/opt/pcbin/install/foo',
    pytest.mark.xfail('/tmp'),
])
def testOptPcbinGetRelevantIfInParameter(resetDepotDirectoryCache, depotDirectory, testDir):
    directories = _getDepotDirectory(testDir)
    assert '/opt/pcbin/install' in directories


def testDepotPathMayWillBeReturned(depotDirectory):
    depotDirToCheck = depotDirectory.split('file://', 1)[1]

    depotDir = _getDepotDirectory(depotDirToCheck)

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
    pytest.mark.xfail(('/var/www/html/opsi', 'forceHostId')),
    (None, 'forceHostId'),
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


def testFilterDirsAndRights(patchUserInfo):
    dar = list(filterDirsAndRights('/'))

    assert len(dar) > 4

    dirsReturned = set()

    for dirname, rights in dar:
        assert dirname
        assert rights

        dirsReturned.add(dirname)

    assert len(dirsReturned) == len(dar), "Duplicate entry returned"


def testLimitingFilterDirsAndRights(patchUserInfo):
    depotDir = '/var/lib/opsi/depot'
    depotDirExists = os.path.exists(depotDir)

    dar = list(filterDirsAndRights(depotDir))

    assert 3 > len(dar) >= 1

    for dirname, _ in dar:
        if depotDirExists and dirname == '/var/lib/opsi/depot':
            break
        elif not depotDirExists and dirname == '/var/lib/opsi':
            break
    else:
        print("Dar is: {0}".format(dar))
        print("Exists directory? {0}".format(depotDirExists))
        raise RuntimeError("Missing path to workbench!")


def testSetRightsOnSSHDirectory():
    groupId = os.getgid()
    userId = os.getuid()

    with workInTemporaryDirectory() as sshDir:
        expectedFilemod = {
            os.path.join(sshDir, u'id_rsa'): 0o640,
            os.path.join(sshDir, u'id_rsa.pub'): 0o644,
            os.path.join(sshDir, u'authorized_keys'): 0o600,
        }

        for filename in expectedFilemod:
            with open(filename, 'w'):
                pass

            os.chmod(filename, 0o400)

        setRightsOnSSHDirectory(userId, groupId, path=sshDir)

        for filename, mod in expectedFilemod.items():
            print("Checking {0} with expected mod {1}".format(filename, mod))
            assert os.path.exists(filename)

            stats = os.stat(filename)

            # As the returned value has many more information but we
            # only require the last 3 digits we apply a logical AND
            # with 777 to it. It's 777 because we have octal values...
            filemod = os.stat(filename).st_mode & 0o777
            assert filemod == mod

            # The following checks are not that good yet...
            # ... but make sure the files are still accessible.
            assert stats.st_gid == groupId
            assert stats.st_uid == userId
