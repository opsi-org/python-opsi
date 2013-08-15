#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Backend.SQLite import SQLiteBackend

class BackendSQLiteTestCase(unittest.TestCase):
    def testInitialisationDoesNotFail(self):
        backend = SQLiteBackend()
        backend.backend_createBase()


if __name__ == '__main__':
    unittest.main()