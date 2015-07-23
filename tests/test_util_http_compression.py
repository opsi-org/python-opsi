#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015 uib GmbH <info@uib.de>

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
Testing functionality for compression in an HTTP context.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Util.HTTP import deflateEncode, deflateDecode
from OPSI.Util.HTTP import gzipEncode, gzipDecode


class DeflateCompressionTestCase(unittest.TestCase):
    def testDeflating(self):
        text = "Das ist ein Test und so."

        deflated = deflateEncode(text)

        self.assertNotEquals(text, deflated)

        newText = deflateDecode(deflated)

        self.assertEquals(text, newText)

    def testDeflatingUnicode(self):
        text = u"Mötörheäd!"

        deflated = deflateEncode(text)
        self.assertNotEquals(text, deflated)

        newText = deflateDecode(deflated)
        self.assertEquals(text, newText)

    def testHandingOverDifferentCompressionLevel(self):
        text = "Das ist ein Test und so."

        for level in range(1, 10):
            deflated = deflateEncode(text, level)
            self.assertEquals(text, deflateDecode(deflated))


class GzipCompressionTestCase(unittest.TestCase):
    def testEncodedObjectIsNotCleartext(self):
        text = "Das ist ein Test und so."

        gzipped = gzipEncode(text)

        self.assertNotEquals(text, gzipped)

        newText = gzipDecode(gzipped)

        self.assertEquals(text, newText)

    def testDecodingUnicode(self):
        text = u"Mötörheäd!"

        gzipped = gzipEncode(text)
        self.assertNotEquals(text, gzipped)

        newText = gzipDecode(gzipped)
        self.assertEquals(text, newText)


    def testWorkingWithDifferentCompressionLevel(self):
        text = "Das ist ein Test und so."

        for level in range(1, 10):
            gzipped = deflateEncode(text, level)
            self.assertEquals(text, deflateDecode(gzipped))


if __name__ == '__main__':
    unittest.main()
