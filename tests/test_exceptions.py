#!/usr/bin/env python
#-*- coding: utf-8 -*-

import time
import unittest


from OPSI.Types import OpsiError, BackendError


class OpsiErrorTestCase(unittest.TestCase):
    ERROR_ARGUMENT = None

    def setUp(self):
        self.error = OpsiError(self.ERROR_ARGUMENT)

    def tearDown(self):
        del self.error

    def testCanBePrinted(self):
        print(self.error)

    def testCanBeCaught(self):
        def raiseError():
            raise self.error

        self.assertRaises(OpsiError, raiseError)


class OpsiErrorWithIntTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = 1


class OpsiErrorWithBoolTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = True


class OpsiErrorWithTimeTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = time.localtime()


class OpsiErrorWithUnicodeStringTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = u'unicode string'


class OpsiErrorWithUTF8StringTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = u'utf-8 string: äöüß€'.encode('utf-8')


class OpsiErrorWithWindowsEncodedStringTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = u'windows-1258 string: äöüß€'.encode('windows-1258')


class OpsiErrorWithUTF16StringTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = u'utf-16 string: äöüß€'.encode('utf-16'),


class OpsiErrorWithLatin1StringTestCase(OpsiErrorTestCase):
    ERROR_ARGUMENT = u'latin1 string: äöüß'.encode('latin-1')


class BackendErrorTest(unittest.TestCase):
    def testIsSubClassOfOpsiError(self):
        def raiseError():
            raise BackendError('Test')

        self.assertRaises(OpsiError, raiseError)


if __name__ == '__main__':
    unittest.main()
