#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util.HTTP

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import random
import string
import unittest

from OPSI.Util.HTTP import hybi10Decode, hybi10Encode


class Hybi10EncodeTestCase(unittest.TestCase):
    def testEncodingAndDecodingDoNotAlterString(self):
        randstring = (
            u'[{"operations": ["created", "deleted", "updated"], '
            u'message_type": "register_for_object_events", '
            u'"client_id": "nJ87nTA7Fph8n29C", '
            u'"object_types": ["OpsiClient", "ProductOnClient", '
            u'"BootConfiguration", "ProductOnDepot", "ConfigState"]}]'
        )
        randstring = randstring.encode('utf-8')
        encoded = hybi10Encode(randstring)
        decoded = hybi10Decode(encoded)

        self.assertEquals(randstring, decoded)

    def testEncodingAndDecodingDoNotAlterStringWithRandomInputs(self):
        valid_digits = ''.join((string.ascii_uppercase, string.digits))
        def string_generator(size):
            return ''.join(random.choice(valid_digits) for x in range(size))

        # Here comes masked data with no length of 126 or 127
        for _ in range(50):
            randstring = string_generator(random.randint(3, 125))
            encoded = hybi10Encode(randstring)
            decoded = hybi10Decode(encoded)

            self.assertEquals(randstring, decoded)

        # Here comes masked data with length 126
        for _ in range(50):
            randstring = string_generator(random.randint(126, 65535))
            encoded = hybi10Encode(randstring)
            decoded = hybi10Decode(encoded)

            self.assertEquals(randstring, decoded)

    def testDecodingTooSmallStrings(self):
        self.assertEquals('', hybi10Decode(''))
        self.assertEquals('', hybi10Decode('a'))
        self.assertEquals('', hybi10Decode('    a    '))


if __name__ == '__main__':
    unittest.main()
