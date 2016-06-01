#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Testing behaviour of exceptions.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import print_function

import time
import unittest

from OPSI.Types import BackendError, OpsiError, OpsiProductOrderingError


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

    def test__repr__(self):
        r = repr(self.error)

        self.assertTrue(r.startswith('<'))
        self.assertTrue(r.endswith('>'))

        if not self.ERROR_ARGUMENT:
            print(r)
            self.assertTrue('()' in r)


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


class OpsiProductOrderingErrorTestCase(OpsiErrorTestCase):
    def setUp(self):
        self.error = OpsiProductOrderingError(self.ERROR_ARGUMENT, [3, 4, 5])

    def testOrderingIsAccessible(self):
        self.assertEquals([3, 4, 5], self.error.problematicRequirements)


class BackendErrorTest(unittest.TestCase):
    def testIsSubClassOfOpsiError(self):
        def raiseError():
            raise BackendError('Test')

        self.assertRaises(OpsiError, raiseError)


if __name__ == '__main__':
    unittest.main()
