#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import unittest

from OPSI.Util.File import DHCPDConfFile

from helpers import copyTestfileToTemporaryFolder


class DHCPDConfFileTestCase(unittest.TestCase):

    def setUp(self):
        self.fileName = copyTestfileToTemporaryFolder(
                            os.path.join(
                                os.path.dirname(__file__), 'testdata',
                                'util', 'dhcpd', 'dhcpd_1.conf'
                            )
                        )

        self.confFile = DHCPDConfFile(self.fileName)

    def tearDown(self):
        del self.confFile

        if os.path.exists(self.fileName):
            os.remove(self.fileName)

    def testParsingFile(self):
        self.confFile.parse()


if __name__ == '__main__':
    unittest.main()
