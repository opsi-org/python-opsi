#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2018 uib GmbH <info@uib.de>

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

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile
from contextlib import contextmanager

import mock
try:
    import MySQLdb
except ImportError as ierr:
    print(ierr)
    MySQLdb = None

from .helpers import unittest, workInTemporaryDirectory

from OPSI.System import which
from OPSI.Types import OpsiBackupBackendNotFound
from OPSI.Util.File.Opsi import OpsiBackupFileError, OpsiBackupArchive
from OPSI.Util import md5sum, randomString


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


@contextmanager
def getOpsiBackupArchive(name=None, mode=None, tempdir=None, keepArchive=False, dataBackend="file"):
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
                fakeDHCPDBackendConfig(baseDir, backendDir)
                if dataBackend == 'file':
                    backendDataDir, hostKeyFile = fakeFileBackendConfig(baseDir, backendDir)
                    fillFileBackendWithFakeFiles(backendDataDir, hostKeyFile)
                elif "mysql" == dataBackend:
                    mySQLConnectionConfig = fakeMySQLBackend(backendDir)
                    fillMySQLBackend(mySQLConnectionConfig)
                else:
                    raise RuntimeError("Unsupported backend: {0!r}".format(dataBackend))
                dispatchConfig = fakeDispatchConfig(baseDir, dataBackend)

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


def fakeDHCPDBackendConfig(baseDir, backendDir):
    dhcpdConfig = os.path.join(baseDir, "dhcpd_for_test.conf")
    dhcpdBackendConfig = os.path.join(backendDir, "dhcpd.conf")
    if not os.path.exists(dhcpdBackendConfig):
        raise RuntimeError("Missing dhcpd backend config {0!r}".format(dhcpdBackendConfig))

    with open(dhcpdBackendConfig, "w") as fileConfig:
        fileConfig.write("""
# -*- coding: utf-8 -*-

module = 'DHCPD'

localip = socket.gethostbyname(socket.getfqdn())

config = {{
"dhcpdOnDepot":            False,
"dhcpdConfigFile":         u"{0}",
"reloadConfigCommand":     u"sudo service dhcp3-server restart",
"fixedAddressFormat":      u"IP", # or FQDN
"defaultClientParameters": {{ "next-server": localip, "filename": u"linux/pxelinux.0" }}
}}
""".format(dhcpdConfig))

    with open(dhcpdConfig, "w") as config:
        config.write("""
# Just some testdata so this is not empty.
# Since this is not a test this can be some useless text.
""")


def fakeFileBackendConfig(baseDir, backendDir):
    fileBackendConfig = os.path.join(backendDir, "file.conf")
    if not os.path.exists(fileBackendConfig):
        raise RuntimeError("Missing file backend config {0!r}".format(fileBackendConfig))

    keyFile = os.path.join(baseDir, "pckeys")
    # TODO: refactor for some code-sharing with the test-setup
    # from the file backend.
    configDataFolder = os.path.join(backendDir, 'fileBackendData')
    try:
        os.mkdir(configDataFolder)
    except OSError as oserr:
        if oserr.errno != 17:  # 17 is File exists
            raise oserr

    with open(fileBackendConfig, "w") as fileConfig:
        fileConfig.write("""
# -*- coding: utf-8 -*-

module = 'File'
config = {{
    "baseDir":     u"{0}",
    "hostKeyFile": u"{1}",
}}
""".format(configDataFolder, keyFile))

    return configDataFolder, keyFile


def fillFileBackendWithFakeFiles(backendDir, hostKeyFile):
    with open(hostKeyFile, 'w') as keyFile:
        keyFile.write('abc:123\n')

    requiredFolders = (u'clients', u'depots', u'products', u'audit', u'templates')
    for folder in requiredFolders:
        try:
            os.mkdir(os.path.join(backendDir, folder))
        except OSError as error:
            if error.errno != 17:  # 17 is File exists
                raise error

    exampleFiles = (
        os.path.join(backendDir, 'config.ini'),
        os.path.join(backendDir, 'clientgroups.ini'),
        os.path.join(backendDir, 'productgroups.ini'),
    )
    for targetFile in exampleFiles:
        try:
            with open(targetFile, 'wx') as dispatchFile:
                pass
        except IOError as error:
            if error.errno != 17:  # 17 is File exists
                raise error


def fakeMySQLBackend(backendDir):
    try:
        from .Backends.config import MySQLconfiguration
    except ImportError as ierr:
        raise unittest.SkipTest(u"Missing MySQLconfiguration - "
            u"please check your config.py in tests/Backends. "
            u"See config.py.example for example data.")

    mysqlConfigFile = os.path.join(backendDir, "mysql.conf")
    with open(mysqlConfigFile, 'w') as mySQLConf:
        mySQLConf.write("""
# -*- coding: utf-8 -*-

module = 'MySQL'
config = {{
    "address":                   u"{address}",
    "database":                  u"{database}",
    "username":                  u"{username}",
    "password":                  u"{password}",
    "databaseCharset":           "{databaseCharset}",
    "connectionPoolSize":        {connectionPoolSize},
    "connectionPoolMaxOverflow": {connectionPoolMaxOverflow},
    "connectionPoolTimeout":     {connectionPoolTimeout}
}}
""".format(**MySQLconfiguration))

    return MySQLconfiguration


def fillMySQLBackend(connectionConfig):
    con = MySQLdb.connect(
        host=connectionConfig["address"],
        user=connectionConfig["username"],
        passwd=connectionConfig["password"],
        db=connectionConfig["database"]
    )

    table = u'''CREATE TABLE `CONFIG` (
            `configId` varchar(200) NOT NULL,
            `type` varchar(30) NOT NULL,
            `description` varchar(256),
            `multiValue` bool NOT NULL,
            `editable` bool NOT NULL,
            PRIMARY KEY (`configId`)
        ) ENGINE=InnoDB DEFAULT CHARSET utf8 COLLATE utf8_general_ci;'''

    try:
        cursor = con.cursor()
        cursor.execute(table)
    except MySQLdb.OperationalError as operror:
        if operror.args[0] != 1050:  # "Table 'CONFIG' already exists"
            raise operror
    finally:
        con.close()


def fakeDispatchConfig(baseDir, dataBackend="file"):
    try:
        os.mkdir(os.path.join(baseDir, "backendManager"))
    except OSError as oserr:
        if oserr.errno != 17:  # 17 is File exists
            raise oserr

    dispatchConfig = os.path.join(baseDir, "backendManager", "dispatch.conf")

    try:
        with open(dispatchConfig, 'wx') as dispatchFile:
            dispatchFile.write("""
backend_.*         : {0}, opsipxeconfd, dhcpd
host_.*            : {0}, opsipxeconfd, dhcpd
productOnClient_.* : {0}, opsipxeconfd
configState_.*     : {0}, opsipxeconfd
.*                 : {0}
""".format(dataBackend))
    except IOError as error:
        if error.errno != 17:  # 17 is File exists
            raise oserr

    return dispatchConfig


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

            expectedFiles = (
                '/backends/sqlite.conf', '/backends/jsonrpc.conf',
                '/backends/mysql.conf', '/backends/opsipxeconfd.conf',
                '/backends/file.conf', '/backends/hostcontrol.conf',
                '/backends/dhcpd.conf', '/backendManager/dispatch.conf',
            )
            for expectedFile in expectedFiles:
                print("Checking for {0!r}".format(expectedFile))
                assert any(entry.endswith(expectedFile) for entry in oldContent)

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

                self.assertRaises(OpsiBackupBackendNotFound, archive.restoreFileBackend)

                for backend in archive._getBackends("file"):
                    baseDir = backend["config"]["baseDir"]

                    oldContent = getFolderContent(baseDir)

                    archive.backupFileBackend()
                    archive.close()

                    shutil.rmtree(baseDir, ignore_errors=True)
                    os.mkdir(baseDir)

                self.assertTrue(oldContent)

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

    def test_backupDHCPBackend(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertRaises(OpsiBackupBackendNotFound, archive.restoreDHCPBackend)

                archiveName = archive.name

                for backend in archive._getBackends("dhcpd"):
                    dhcpConfigFile = backend['config']['dhcpdConfigFile']

                    md5OfOriginalFile = md5sum(dhcpConfigFile)

                    archive.backupDHCPBackend()
                    archive.close()

                    os.remove(dhcpConfigFile)
                    break
                else:
                    raise RuntimeError("No DHCPD backend configured!")

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                backup.restoreDHCPBackend()
                md5OfRestoredFile = md5sum(dhcpConfigFile)

            self.assertEqual(md5OfOriginalFile, md5OfRestoredFile)

    def testBackupDHCPBackendDoesNotFailIfConfigFileIsMissing(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:

                archiveName = archive.name

                for backend in archive._getBackends("dhcpd"):
                    dhcpConfigFile = backend['config']['dhcpdConfigFile']
                    os.remove(dhcpConfigFile)
                    break
                else:
                    raise RuntimeError("No DHCPD backend configured!")

                archive.backupDHCPBackend()
                archive.close()

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                assert not backup.hasDHCPBackend()
                self.assertRaises(OpsiBackupBackendNotFound, backup.restoreDHCPBackend)

    def testBackupHasDHCPDBackend(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertFalse(archive.hasDHCPBackend())
                archiveName = archive.name
                archive.backupDHCPBackend()

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                self.assertTrue(backup.hasDHCPBackend())

    def test_backupMySQLBackend(self):
        if not MySQLdb:
            raise unittest.SkipTest("Could not import MySQLdb: {0}".format(ierr))

        try:
            which('mysqldump')
        except Exception as error:
            raise unittest.SkipTest("Missing mysqldump: {0}".format(error))

        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True, dataBackend="mysql") as archive:
                self.assertRaises(OpsiBackupBackendNotFound, archive.restoreMySQLBackend)

                archiveName = archive.name
                archive.backupMySQLBackend()
                archive.close()

                orig = {}
                for backend in archive._getBackends("mysql"):
                    con = MySQLdb.connect(
                        host=backend["config"]["address"],
                        user=backend["config"]["username"],
                        passwd=backend["config"]["password"],
                        db=backend["config"]["database"]
                    )

                    cursor = con.cursor()
                    cursor.execute("SHOW TABLES;")
                    orig[backend["name"]] = dict.fromkeys([r[0] for r in cursor.fetchall()])
                    for entry in orig[backend["name"]].keys():
                        cursor.execute("SELECT COUNT(*) FROM `%s`" % entry)
                        count = cursor.fetchone()
                        orig[backend["name"]][entry] = count[0]
                        cursor.execute("DROP TABLE `%s`" % entry)

            self.assertTrue(orig)
            for backendName, values in orig.items():
                print("Checking for content in {0!r}...".format(backendName))
                self.assertTrue(values)

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir, dataBackend="mysql") as backup:
                backup.restoreMySQLBackend()

                new = {}
                for backend in archive._getBackends("mysql"):
                    con = MySQLdb.connect (
                        host=backend["config"]["address"],
                        user=backend["config"]["username"],
                        passwd=backend["config"]["password"],
                        db=backend["config"]["database"]
                    )
                    cursor = con.cursor()
                    cursor.execute("SHOW TABLES;")
                    new[backend["name"]] = dict.fromkeys([r[0] for r in cursor.fetchall()])
                    for entry in new[backend["name"]].keys():
                        cursor.execute("SELECT COUNT(*) FROM `%s`" % entry)
                        count = cursor.fetchone()
                        new[backend["name"]][entry] = count[0]

            self.assertEqual(orig, new)

    def testBackupHasMySQLBackend(self):
        with workInTemporaryDirectory() as tempDir:
            with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
                self.assertFalse(archive.hasMySQLBackend())
                archiveName = archive.name

                with mock.patch('OPSI.System.which', lambda x: 'echo'):
                    archive.backupMySQLBackend()

            with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
                self.assertTrue(backup.hasMySQLBackend())


if __name__ == '__main__':
    unittest.main()
