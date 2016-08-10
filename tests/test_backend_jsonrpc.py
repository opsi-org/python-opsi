#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

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
from __future__ import absolute_import

from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Util.HTTP import deflateEncode, gzipEncode

from .helpers import unittest
from .Backends.JSONRPC import JSONRPCTestCase


class FakeResponse(object):
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
        JSONRPCBackend("localhost", connectoninit=False)

    def testProcessingEmptyResponse(self):
        """
        Test processing an empty response
        """
        backend = JSONRPCBackend("localhost", connectoninit=False)
        result = backend._processResponse(FakeResponse())

        self.assertEquals(None, result)


class JSONRPCBackendCompressionTestCase(unittest.TestCase):
    def testProcessingGzippedResponse(self):
        backend = JSONRPCBackend("localhost", connectoninit=False)

        response = FakeResponse(
            data=gzipEncode("This is gzipped"),
            header={'content-encoding': 'gzip'}
        )

        self.assertEquals("This is gzipped", backend._processResponse(response))

    def testProcessingDeflatedResponse(self):
        backend = JSONRPCBackend("localhost", connectoninit=False)

        response = FakeResponse(
            data=deflateEncode("This is deflated"),
            header={'content-encoding': 'deflate'}
        )

        self.assertEquals("This is deflated", backend._processResponse(response))

    def testProcessingResponseBackwardsCompatible(self):
        backend = JSONRPCBackend("localhost", connectoninit=False)

        response = FakeResponse(
            data=deflateEncode("This is deflated"),
            header={'content-type': 'gzip-application/json'}
        )

        self.assertEquals("This is deflated", backend._processResponse(response))


class JSONRPCBackendUsingTestCase(unittest.TestCase, JSONRPCTestCase):
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()


if __name__ == '__main__':
    unittest.main()
