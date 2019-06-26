# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2019 uib GmbH <info@uib.de>

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
from collections import defaultdict

import pytest

from OPSI.Util.Task.Rights import (
    chown, getDepotDirectory, getDirectoriesAndExpectedRights,
    getWebserverRepositoryPath, getWebserverUsernameAndGroupname,
    filterDirsAndRights, setRightsOnSSHDirectory, setRightsOnFile)

from .helpers import mock


OS_CHECK_FUNCTIONS = ['isRHEL', 'isCentOS', 'isSLES', 'isOpenSUSE', 'isUbuntu', 'isDebian', 'isUCS']


@pytest.fixture
def depotDirectory():
    'Returning a fixed address when checking for a depotUrl'
    depotUrl = u'file:///var/lib/opsi/depot'
    with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', lambda: depotUrl):
        yield depotUrl


@pytest.fixture
def emptyDepotDirectoryCache():
    'Making sure that no depotUrl is cached.'
    with mock.patch('OPSI.Util.Task.Rights._CACHED_DEPOT_DIRECTORY', None):
        yield


@pytest.fixture
def patchUserInfo():
    'Calls to find uid / gid will always succeed.'
    uid = 1234
    gid = 5678
    with mock.patch('OPSI.Util.Task.Rights.pwd.getpwnam', return_value=(None, None, uid)):
        with mock.patch('OPSI.Util.Task.Rights.grp.getgrnam', return_value=(None, None, gid)):
            yield uid, gid


@pytest.mark.parametrize("slesSupport, tftpdir", [
    (False, u'/tftpboot/linux'),
    (True, u'/var/lib/tftpboot/opsi')
], ids=["sles", "non-sles"])
def testGetDirectoriesToProcess(depotDirectory, patchUserInfo, slesSupport, tftpdir):
    with mock.patch('OPSI.Util.Task.Rights.getWebserverRepositoryPath', lambda: '/path/to/apache'):
        with mock.patch('OPSI.Util.Task.Rights.isSLES', lambda: slesSupport):
            directories = [d for d, _ in getDirectoriesAndExpectedRights('/')]

    assert u'/etc/opsi' in directories
    assert u'/var/lib/opsi' in directories
    assert u'/var/log/opsi' in directories
    assert tftpdir in directories
    assert '/path/to/apache' in directories


@pytest.mark.parametrize("slesSupport, tftpdir", [
    (False, u'/tftpboot/linux'),
    (True, u'/var/lib/tftpboot/opsi')
], ids=["opensuse", "non-opensuse"])
def testGetDirectoriesToProcessOpenSUSE(depotDirectory, patchUserInfo, slesSupport, tftpdir):
    with mock.patch('OPSI.Util.Task.Rights.getWebserverRepositoryPath', lambda: '/path/to/apache'):
        with mock.patch('OPSI.Util.Task.Rights.isOpenSUSE', lambda: slesSupport):
            directories = [d for d, _ in getDirectoriesAndExpectedRights('/')]

    assert u'/etc/opsi' in directories
    assert u'/var/lib/opsi' in directories
    assert u'/var/log/opsi' in directories
    assert tftpdir in directories
    assert '/path/to/apache' in directories


def testGettingDirectories(patchUserInfo, depotDirectory):
    directories = [d for d, _ in getDirectoriesAndExpectedRights('/tmp')]
    assert len(directories) > 2


@pytest.mark.parametrize("testDir", [
    '/opt/pcbin/install/foo',
    pytest.param('/tmp', marks=pytest.mark.xfail),
])
def testOptPcbinGetRelevantIfInParameter(emptyDepotDirectoryCache, depotDirectory, testDir):
    directories = getDepotDirectory(testDir)
    assert '/opt/pcbin/install' in directories


def testReturningEmptyPathIfLookupFailed(emptyDepotDirectoryCache, depotDirectory):
    with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', mock.Mock(side_effect=Exception)):
        assert not getDepotDirectory('/')

    with mock.patch('OPSI.Util.Task.Rights.getDepotUrl', lambda: 'invalid:/x'):
        assert not getDepotDirectory('/')


def testDepotPathMayWillBeReturned(depotDirectory):
    depotDirToCheck = depotDirectory.split('file://', 1)[1]

    depotDir = getDepotDirectory(depotDirToCheck)

    assert depotDir == '/var/lib/opsi/depot'


@pytest.fixture(scope="session")
def currentUserId():
    yield os.getuid()


@pytest.fixture
def nonRootUserId():
    userId = os.getuid()
    isRoot = os.geteuid() == 0

    if isRoot:
        for uid in range(2, 60000):
            try:
                pwd.getpwuid(uid)
                changedUid = uid
                break
            except KeyError:
                pass
        else:
            pytest.skip("No userId for test found. Aborting.")

        if userId == changedUid:
            pytest.skip("Could not find another user.")

        return changedUid
    else:
        return -1


@pytest.fixture(scope="session")
def currentGroupId():
    yield os.getgid()


@pytest.fixture
def nonRootGroupId(currentGroupId):
    for gid in range(2, 60000):
        try:
            grp.getgrgid(gid)
            if currentGroupId == gid:
                # We do not want to use the same group ID.
                continue

            return gid
        except KeyError:
            pass
    else:
        pytest.skip("No group for test found. Aborting.")


def testChangingOwnershipWithOurChown(currentUserId, nonRootUserId, currentGroupId, nonRootGroupId, tempDir):
    isRoot = os.geteuid() == 0
    original = os.path.join(tempDir, 'original')
    with open(original, 'w'):
        pass

    linkfile = os.path.join(tempDir, 'linkfile')
    os.symlink(original, linkfile)
    assert os.path.islink(linkfile)

    # Changing the uid/gid to something different
    os.chown(original, nonRootUserId, nonRootGroupId)
    os.lchown(linkfile, nonRootUserId, nonRootGroupId)

    for filename in (original, linkfile):
        if os.path.islink(filename):
            stat = os.lstat(filename)
        else:
            stat = os.stat(linkfile)

        assert nonRootGroupId == stat.st_gid
        if not isRoot:
            assert nonRootUserId == stat.st_uid

    # Correcting the uid/gid
    chown(linkfile, currentUserId, currentGroupId)
    chown(original, currentUserId, currentGroupId)

    for filename in (original, linkfile):
        if os.path.islink(filename):
            stat = os.lstat(filename)
        else:
            stat = os.stat(linkfile)

        assert currentGroupId == stat.st_gid
        if not isRoot:
            assert currentUserId == stat.st_uid


def testGettingDirectoriesAndRights(patchUserInfo):
    dm = dict(getDirectoriesAndExpectedRights('/'))

    for rights in dm.values():
        # For now we just want to make sure these fields are filled.
        assert rights.uid
        assert rights.gid

    rights = dm[u'/etc/opsi']
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert rights.correctLinks

    rights = dm[u'/var/lib/opsi']
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert not rights.correctLinks

    rights = dm[u'/var/log/opsi']
    assert rights.files == 0o660
    assert rights.directories == 0o770
    assert rights.correctLinks


@pytest.mark.parametrize("directoryExists", [True, pytest.param(False, marks=pytest.mark.xfail)])
@pytest.mark.parametrize("dir, function", [
    ('/var/www/html/opsi', 'isCentOS'),
    ('/var/www/html/opsi', 'isDebian'),
    ('/srv/www/htdocs/opsi', 'isOpenSUSE'),
    ('/srv/www/htdocs/opsi', 'isSLES'),
    ('/var/www/html/opsi', 'isRHEL'),
    ('/var/www/html/opsi', 'isUbuntu'),
    ('/var/www/opsi', 'isUCS'),
])
def testGettingWebserverRepositoryPath(dir, function, directoryExists):
    with disableOSChecks(OS_CHECK_FUNCTIONS[:]):
        with mock.patch('OPSI.Util.Task.Rights.{0}'.format(function), lambda: True):
            with mock.patch('OPSI.Util.Task.Rights.os.path.exists', lambda x: directoryExists):
                assert dir == getWebserverRepositoryPath()


@pytest.mark.parametrize("function, username, groupname", [
    ('isCentOS', 'apache', 'apache'),
    ('isDebian', 'www-data', 'www-data'),
    ('isOpenSUSE', 'wwwrun', 'www'),
    ('isRHEL', 'apache', 'apache'),
    ('isSLES', 'wwwrun', 'www'),
    ('isUbuntu', 'www-data', 'www-data'),
    ('isUCS', 'www-data', 'www-data'),
    pytest.param('forceHostId', '', '', marks=pytest.mark.xfail),
])
def testGettingWebserverUsernameAndGroupname(function, username, groupname):
    with disableOSChecks(OS_CHECK_FUNCTIONS[:]):
        with mock.patch('OPSI.Util.Task.Rights.{0}'.format(function), lambda: True):
            user, group = getWebserverUsernameAndGroupname()
            assert user == username
            assert group == groupname


@contextmanager
def disableOSChecks(functions):
    try:
        func = functions.pop()
        with mock.patch('OPSI.Util.Task.Rights.{0}'.format(func), return_value=False):
            with disableOSChecks(functions):
                yield
    except IndexError:
        yield


def testFilterDirsAndRightsReturnsAllWhenRootIsGiven(patchUserInfo):
    defaultDirGenerator = getDirectoriesAndExpectedRights('/')
    dar = list(filterDirsAndRights('/', defaultDirGenerator))

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

    defaultDirGenerator = getDirectoriesAndExpectedRights(depotDir)
    dar = list(filterDirsAndRights(depotDir, defaultDirGenerator))

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


def testFilteringOutDuplicateDirectories():
    def duplicatingGenerator():
        for i, x in enumerate(('/etc/opsi', '/var/lib/opsi/', '/unrelated/')):
            for _ in range(i):
                yield x, None

    counts = defaultdict(lambda: 0)
    for d, _ in filterDirsAndRights('/', duplicatingGenerator()):
        counts[d] += 1

    for d, count in counts.items():
        assert count == 1, "{0} was returned more than once!".format(d)


def testSetRightsOnSSHDirectory(tempDir):
    groupId = os.getgid()
    userId = os.getuid()

    sshDir = tempDir
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
        assert os.path.exists(filename)

        assert getMod(filename) == mod

        stats = os.stat(filename)
        # The following checks are not that good yet...
        # ... but make sure the files are still accessible.
        assert stats.st_gid == groupId
        assert stats.st_uid == userId


def getMod(path):
    """
    Return the octal representation of rights for a `path`.

    Will only return the last three values, i.e. 664.
    """
    # As the returned value has many more information but we
    # only require the last 3 digits we apply a logical AND
    # with 777 to it. It's 777 because we have octal values...
    return os.stat(path).st_mode & 0o777


def testSettingRightsOnFile(tempDir):
    filePath = os.path.join(tempDir, 'foobar')
    with open(filePath, 'w'):
        pass

    os.chmod(filePath, 0o000)
    assert getMod(filePath) == 0o000

    setRightsOnFile(filePath, 0o777)

    assert getMod(filePath) == 0o777
