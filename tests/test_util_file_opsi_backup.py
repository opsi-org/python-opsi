#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import tempfile

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

from OPSI.Util.File.Opsi import OpsiBackupFileError, OpsiBackupArchive
from OPSI.Util import randomString


class BackendArchiveTestCase(unittest.TestCase):
    def setUp(self):
        self._tempDir = tempfile.gettempdir()

    def tearDown(self):
        try:
            if os.path.exists(self.archive.name):
                os.remove(self.archive.name)
        except AttributeError:
            pass

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
                    'domainname': u'uib.local',
                    'distributionId': '',
                    'fqdn': u'debian6.uib.local',
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

if __name__ == '__main__':
    unittest.main()
