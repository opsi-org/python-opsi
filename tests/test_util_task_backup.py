#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Util.Task.Backup import OpsiBackup


class BackupTestCase(unittest.TestCase):
    def testVerifySysConfigDoesNotFailBecauseWhitespaceAtEnd(self):
        class FakeSysInfo(object):
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        backup = OpsiBackup()

        archive = {
            'distribution': 'SUSE Linux Enterprise Server'
        }
        system = FakeSysInfo(
            distribution='SUSE Linux Enterprise Server '
        )

        self.assertEquals(
            {},
            backup._getDifferencesInSysConfig(
                archive,
                sysInfo=system
            )
        )


if __name__ == '__main__':
    unittest.main()
