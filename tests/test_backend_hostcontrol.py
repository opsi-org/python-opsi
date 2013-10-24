#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from Backends.HostControl import HostControlBackendMixin
from BackendTestMixins.Clients import ClientsMixin


class FileBackendTestCase(unittest.TestCase, HostControlBackendMixin, ClientsMixin):
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testCallingStartAndStopMethod(self):
        """
        Test if calling the methods works.

        This test does not check if WOL on these clients work nor that
        they do exist.
        """
        self.setUpClients()
        self.createHostsOnBackend()

        self.backend.hostControl_start([u'client1.uib.local'])
        self.backend.hostControl_shutdown([u'client1.uib.local'])


if __name__ == '__main__':
    unittest.main()