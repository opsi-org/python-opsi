#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing the JSON-RPC backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
import unittest

from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Util.HTTP import deflateEncode, gzipEncode


class FakeResponse:
    def __init__(self, header=None, data=None):
        self._header = header or {}
        self.data = data

    def getheader(self, field, default=None):
        return self._header.get(field, default)


class JSONRPCBackendTestCase(unittest.TestCase):
    def testCreatingInstance(self):
        """
        Testing the creation of an instance.

        We connect to localhost without making a connection right from
        the start on.
        """
        backend = JSONRPCBackend("localhost", connectoninit=False)

    def testProcessingEmptyResponse(self):
        """
        Test processing an empty response
        """
        backend = JSONRPCBackend("localhost", connectoninit=False)
        result = backend._processResponse(FakeResponse())

        self.assertEquals(None, result)

    def testProcessingGzippedResponse(self):
        backend = JSONRPCBackend("localhost", connectoninit=False)

        response = FakeResponse(
            data=gzipEncode("This is a test"),
            header={'content-encoding': 'gzip'}
        )

        self.assertEquals("This is a test", backend._processResponse(response))

    def testProcessingDeflatedResponse(self):
        backend = JSONRPCBackend("localhost", connectoninit=False)

        response = FakeResponse(
            data=deflateEncode("This is a test"),
            header={'content-encoding': 'deflate'}
        )

        self.assertEquals("This is a test", backend._processResponse(response))


if __name__ == '__main__':
    unittest.main()
