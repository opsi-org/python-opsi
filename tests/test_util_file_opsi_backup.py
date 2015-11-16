#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing opsis backup functionality.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import shutil
import tempfile
from contextlib import contextmanager

import mock

from .helpers import unittest, workInTemporaryDirectory

from OPSI.Util.File.Opsi import OpsiBackupFileError, OpsiBackupArchive
from OPSI.Util import randomString


class BackendArchiveTestCase(unittest.TestCase):
    def setUp(self):
        self._tempDir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            if os.path.exists(self.archive.name):
                os.remove(self.archive.name)
        except AttributeError:
            pass

        if os.path.exists(self._tempDir):
            shutil.rmtree(self._tempDir)

    def createArchive(self, **kwargs):
        """
        Creates an archive with the given keyword arguments.
        """
        kwargs['tempdir'] = self._tempDir
        self._kwargs = kwargs
        print('Creating archive with the fowlling settings: {0}'.format(kwargs))

        if not os.path.exists('/etc/opsi/version'):
            def returnExampleSysconfig(unused):
                exampleSysConfig = {
                    'hostname': u'debian6',
                    'sysVersion': (6, 0, 9),
                    'domainname': u'test.invalid',
                    'distributionId': '',
                    'fqdn': u'debian6.test.invalid',
                    'opsiVersion': '4.0.4.5',
                    'distribution': 'debian'
                }
                return exampleSysConfig

            # TODO: rather setup an fake environment.
            def returnExampleBackendConfiguration(unused):
                return {
                    'file': {
                        'config': {
                            'baseDir': u'/var/lib/opsi/config',
                            'hostKeyFile': u'/etc/opsi/pckeys'
                        },
                        'dispatch': True,
                        'module': 'File',
                        'name': 'file'
                    },
                    'hostcontrol': {
                        'config': {
                            'broadcastAddresses': ['255.255.255.255'],
                            'hostRpcTimeout': 15,
                            'maxConnections': 50,
                            'opsiclientdPort': 4441,
                            'resolveHostAddress': False
                        },
                        'dispatch': False,
                        'module': 'HostControl',
                        'name': 'hostcontrol'
                    },
                    'mysql': {
                        'config': {
                            'address': u'localhost',
                            'connectionPoolMaxOverflow': 10,
                            'connectionPoolSize': 20,
                            'connectionPoolTimeout': 30,
                            'database': u'opsi',
                            'databaseCharset': 'utf8',
                            'password': u'opsi',
                            'username': u'opsi'
                        },
                        'dispatch': False,
                        'module': 'MySQL',
                        'name': 'mysql'
                    },
                }

            with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive._probeSysInfo', returnExampleSysconfig):
                with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive._readBackendConfiguration', returnExampleBackendConfiguration):
                    print('Detected missing version file. Patchiiiing.')
                    self.archive = OpsiBackupArchive(**kwargs)
        else:
            self.archive = OpsiBackupArchive(**kwargs)

    def testArchiveGetsCreated(self):
        self.createArchive()
        self.assertTrue(os.path.exists(self.archive.name))

    def testArchiveCanBeNamed(self):
        randomName = os.path.join(self._tempDir, '{0}.tar'.format(randomString(16)))
        self.createArchive(name=randomName, mode="w")

        self.assertTrue(os.path.exists(self.archive.name))

    def testExistingArchiveIsImmutable(self):
        randomName = os.path.join(self._tempDir, '{0}.tar'.format(randomString(16)))
        self.createArchive(name=randomName, mode="w")

        self.assertRaises(OpsiBackupFileError, OpsiBackupArchive, **self._kwargs)

    def testFilesCanBeAdded(self):
        self.createArchive()
        exampleFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'fake_global.conf'
        )

        self.archive._addContent(exampleFile)

        self.archive.close()

    def testVerifyingBackup(self):
        requiredDirectory = '/var/lib/opsi/config'
        if not os.path.exists(requiredDirectory):
            self.skipTest('Missing directory "{0}" on testmachine.'.format(requiredDirectory))

        self.createArchive(mode="w")
        # TODO: Fix for computers without /var/lib/opsi/config
        self.archive.backupFileBackend()
        self.archive.close()

        newArguments = self._kwargs
        newArguments['mode'] = 'r'
        newArguments['name'] = self.archive.name

        backup = OpsiBackupArchive(**newArguments)
        self.assertTrue(backup.verify())
        backup.close()

    @unittest.skip("TODO: test corrupted Image")
    def test_backupVerifyCorrupted(self):
        # TODO: test corrupted Image
        pass


@contextmanager
def getOpsiBackupArchive(name=None, mode=None, tempdir=None, keepArchive=False):
    with workInTemporaryDirectory(tempdir) as tempDir:
        baseDir = os.path.join(tempDir, 'base')
        backendDir = os.path.join(baseDir, 'backends')

        baseDataDir = os.path.join(os.path.dirname(__file__), '..', 'data', 'backends')
        baseDataDir = os.path.normpath(baseDataDir)
        try:
            shutil.copytree(baseDataDir, backendDir)
        except OSError as error:
            print(u"Failed to copy {0!r} to {1!r}: {2}".format(baseDataDir, backendDir, error))

        with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive.CONF_DIR', baseDir):
            with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive.BACKEND_CONF_DIR', backendDir):

                fileBackendConfig = os.path.join(backendDir, "file.conf")
                if not os.path.exists(fileBackendConfig):
                    raise RuntimeError("Missing file backend config {0!r}".format(fileBackendConfig))

                # TODO: refactor for some code-sharing with the test-setup
                # from the file backend.
                with open(fileBackendConfig, "w") as fileConfig:
                    fileConfig.write("""
                # -*- coding: utf-8 -*-

module = 'File'
config = {{
    "baseDir":     u"{0}",
    "hostKeyFile": u"/etc/opsi/pckeys",
}}
""".format(baseDir))

                try:
                    os.mkdir(os.path.join(baseDir, "backendManager"))
                except OSError as oserr:
                    if oserr.errno != 17:  # 17 is File exists
                        raise oserr

                dispatchConfig = os.path.join(baseDir, "backendManager", "dispatch.conf")

                try:
                    with open(dispatchConfig, 'wx') as dispatchFile:
                        dispatchFile.write("""
backend_.*         : file, opsipxeconfd, dhcpd
host_.*            : file, opsipxeconfd, dhcpd
productOnClient_.* : file, opsipxeconfd
configState_.*     : file, opsipxeconfd
.*                 : file
""")
                except IOError as error:
                    if error.errno != 17:  # 17 is File exists
                        raise oserr

                with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive.DISPATCH_CONF', dispatchConfig):
                    with mock.patch('OPSI.System.Posix.SysInfo.opsiVersion', '1.2.3'):
                        archive = OpsiBackupArchive(name=name, mode=mode, tempdir=tempDir)
                        try:
                            yield archive
                        finally:
                            try:
                                archive.close()
                            except IOError:
                                # Archive is probably already closed
                                pass

                            if not keepArchive:
                                try:
                                    os.remove(archive.name)
                                except OSError:
                                    pass


def getFolderContent(path):
    content = []
    for root, directories, files in os.walk(path):
        for oldDir in directories:
            content.append(os.path.join(root, oldDir))

        for filename in files:
            content.append(os.path.join(root, filename))

    return content


class BackupArchiveTest(unittest.TestCase):
    def testCreatingConfigurationBackup(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                archive.backupConfiguration()
                oldContent = getFolderContent(archive.CONF_DIR)
                shutil.rmtree(archive.CONF_DIR, ignore_errors="True")

            self.assertTrue(oldContent, "No data found!")

            with getOpsiBackupArchive(name=archive.name, mode="r", tempdir=tempDir) as backup:
                backup.restoreConfiguration()
                newContent = getFolderContent(backup.CONF_DIR)

            self.assertTrue(newContent, "No data found!")
            self.assertEquals(oldContent, newContent)

    def testBackupHasConfiguration(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertFalse(archive.hasConfiguration())
                archiveName = archive.name
                archive.backupConfiguration()

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                self.assertTrue(backup.hasConfiguration())

    def testCreatingFileBackendBackup(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertTrue(list(archive._getBackends("file")), "Missing file backend!")

                self.assertTrue(1, len(list(archive._getBackends("file"))))

                for backend in archive._getBackends("file"):
                    baseDir = backend["config"]["baseDir"]

                    oldContent = getFolderContent(baseDir)

                    archive.backupFileBackend()
                    archive.close()

                    shutil.rmtree(baseDir, ignore_errors=True)
                    os.mkdir(baseDir)

                with getOpsiBackupArchive(name=archive.name, mode="r", tempdir=tempDir) as backup:
                    backup.restoreFileBackend()
                    newContent = getFolderContent(baseDir)

                self.assertEquals(oldContent, newContent)

    def testBackupHasFileBackend(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertFalse(archive.hasFileBackend())
                archiveName = archive.name
                archive.backupFileBackend()

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                self.assertTrue(backup.hasFileBackend())

if __name__ == '__main__':
    unittest.main()
