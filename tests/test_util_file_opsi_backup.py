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
import pytest
import shutil
from contextlib import closing, contextmanager

from OPSI.Exceptions import OpsiBackupBackendNotFound
from OPSI.System import which
from OPSI.Util.File.Opsi import OpsiBackupFileError, OpsiBackupArchive
from OPSI.Util import md5sum, randomString

from .helpers import mock, workInTemporaryDirectory

try:
    import MySQLdb
except ImportError as ierr:
    print(ierr)
    MySQLdb = None

try:
    which('mysqldump')
    mysqldump = True
except Exception as error:
    mysqldump = False


def createArchive(tempDir, **kwargs):
    """
    Creates an archive with the given keyword arguments.
    """
    kwargs['tempdir'] = tempDir
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

        with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive.getSysInfo', returnExampleSysconfig):
            with mock.patch('OPSI.Util.File.Opsi.OpsiBackupArchive._readBackendConfiguration', returnExampleBackendConfiguration):
                print('Detected missing version file. Patchiiiing.')
                archive = OpsiBackupArchive(**kwargs)
    else:
        archive = OpsiBackupArchive(**kwargs)

    return archive, kwargs


def testArchiveGetsCreated(tempDir):
    archive, _ = createArchive(tempDir)
    assert os.path.exists(archive.name)


def testArchiveCanBeNamed(tempDir):
    randomName = os.path.join(tempDir, '{0}.tar'.format(randomString(16)))
    archive, _ = createArchive(tempDir, name=randomName, mode="w")

    assert os.path.exists(archive.name)


def testExistingArchiveIsImmutable(tempDir):
    randomName = os.path.join(tempDir, '{0}.tar'.format(randomString(16)))
    _, options = createArchive(tempDir, name=randomName, mode="w")

    with pytest.raises(OpsiBackupFileError):
        OpsiBackupArchive(**options)


def testFilesCanBeAdded(tempDir):
    archive, _ = createArchive(tempDir)

    # TODO: check if file exists
    # TODO: reuse fixture?
    exampleFile = os.path.join(
        os.path.dirname(__file__),
        'testdata', 'util', 'fake_global.conf'
    )

    with closing(archive):
        archive._addContent(exampleFile)


@pytest.mark.skipif(not os.path.exists('/var/lib/opsi/config'),
                    reason='Missing directory "/var/lib/opsi/config" on testmachine.')
def testVerifyingBackup(tempDir):
    archive, options = createArchive(tempDir, mode="w")

    # TODO: Fix for computers without /var/lib/opsi/config
    with closing(archive):
        archive.backupFileBackend()

    newArguments = options
    newArguments['mode'] = 'r'
    newArguments['name'] = archive.name

    with closing(OpsiBackupArchive(**newArguments)) as backup:
        assert backup.verify()


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
            with open(targetFile, 'x'):
                pass
        except IOError as error:
            if error.errno != 17:  # 17 is File exists
                raise error


def fakeMySQLBackend(backendDir):
    try:
        from .Backends.config import MySQLconfiguration
    except ImportError:
        pytest.skip(
            u"Missing MySQLconfiguration - "
            u"please check your config.py in tests/Backends. "
            u"See config.py.example for example data."
        )

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
        if operror.errno != 1050:  # "Table 'CONFIG' already exists"
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
        with open(dispatchConfig, 'x') as dispatchFile:
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


def testCreatingConfigurationBackup(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        archive.backupConfiguration()
        oldContent = getFolderContent(archive.CONF_DIR)
        shutil.rmtree(archive.CONF_DIR, ignore_errors="True")

    assert oldContent

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

    assert newContent
    assert oldContent == newContent


def testBackupHasConfiguration(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        assert not archive.hasConfiguration()
        archiveName = archive.name
        archive.backupConfiguration()

    with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
        assert backup.hasConfiguration()


def testCreatingFileBackendBackup(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        assert list(archive._getBackends("file")), "Missing file backend!"
        assert 1 == len(list(archive._getBackends("file")))

        with pytest.raises(OpsiBackupBackendNotFound):
            archive.restoreFileBackend()

        for backend in archive._getBackends("file"):
            baseDir = backend["config"]["baseDir"]
            oldContent = getFolderContent(baseDir)

            keyFile = backend["config"]["hostKeyFile"]
            assert os.path.exists(keyFile)

            archive.backupFileBackend()
            archive.close()

            shutil.rmtree(baseDir, ignore_errors=True)
            if baseDir not in keyFile:
                os.remove(keyFile)
            assert not os.path.exists(keyFile)
            os.mkdir(baseDir)

        with getOpsiBackupArchive(name=archive.name, mode="r", tempdir=tempDir) as backup:
            backup.restoreFileBackend()
            newContent = getFolderContent(baseDir)

            newKeyFile = backend["config"]["hostKeyFile"]
            assert os.path.exists(newKeyFile)

        assert oldContent == newContent


def testBackupHasFileBackend(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        assert not archive.hasFileBackend()
        archiveName = archive.name
        archive.backupFileBackend()

    with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
        assert backup.hasFileBackend()


@pytest.mark.endless
def testBackupDHCPBackend(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        with pytest.raises(OpsiBackupBackendNotFound):
            archive.restoreDHCPBackend()

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

    assert md5OfOriginalFile == md5OfRestoredFile


def testBackupDHCPBackendDoesNotFailIfConfigFileIsMissing(tempDir):
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

        with pytest.raises(OpsiBackupBackendNotFound):
            backup.restoreDHCPBackend()


def testBackupHasDHCPDBackend(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        assert not archive.hasDHCPBackend()
        archiveName = archive.name
        archive.backupDHCPBackend()

    with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
        assert backup.hasDHCPBackend()


@pytest.mark.skipif(not MySQLdb, reason="Missing MySQLdb.")
@pytest.mark.skipif(not mysqldump, reason="Missing mysqldump.")
def test_backupMySQLBackend(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True, dataBackend="mysql") as archive:
        with pytest.raises(OpsiBackupBackendNotFound):
            archive.restoreMySQLBackend()

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

    assert orig
    for backendName, values in orig.items():
        print("Checking for content in {0!r}...".format(backendName))
        assert values

    with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir, dataBackend="mysql") as backup:
        backup.restoreMySQLBackend()

        new = {}
        for backend in archive._getBackends("mysql"):
            con = MySQLdb.connect(
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

    assert orig == new


def testBackupHasMySQLBackend(tempDir):
    with getOpsiBackupArchive(tempdir=tempDir, keepArchive=True) as archive:
        assert not archive.hasMySQLBackend()
        archiveName = archive.name

        with mock.patch('OPSI.System.which', lambda x: 'echo'):
            archive.backupMySQLBackend()

    with getOpsiBackupArchive(name=archiveName, mode="r", tempdir=tempDir) as backup:
        assert backup.hasMySQLBackend()

