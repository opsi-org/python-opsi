# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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

import pytest

from OPSI.Backend.JSONRPC import _DEFLATE_COMPRESSION, _GZIP_COMPRESSION
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Util.HTTP import HTTPHeaders, deflateEncode, gzipEncode
from OPSI.Util import randomString


class FakeResponse(object):
    def __init__(self, header=None, data=None):
        self._header = HTTPHeaders(header or {})
        self.data = data

    def getheader(self, field, default=None):
        return self._header.get(field, default)


@pytest.fixture
def jsonRpcBackend():
    yield JSONRPCBackend("localhost", connectoninit=False)


def testProcessingEmptyResponse(jsonRpcBackend):
    """
    Test processing an empty response
    """
    result = jsonRpcBackend._processResponse(FakeResponse())

    assert result is None


@pytest.fixture
def text():
    return randomString(24)


@pytest.mark.parametrize("contentEncoding, encodingFunction", [
    ('deflate', deflateEncode),
    ('gzip', gzipEncode),
])
def testProcessingResponseWithEncodedContent(jsonRpcBackend, encodingFunction, contentEncoding, text):
    response = FakeResponse(
        data=encodingFunction(text),
        header={'content-encoding': contentEncoding}
    )

    assert text == jsonRpcBackend._processResponse(response)


@pytest.mark.parametrize("compressionOptions, expectedCompression", [
    ({"deflate": False}, False),
    ({"deflate": True}, True),
    ({"compression": False}, False),
    ({"compression": True}, True),
    ({"compression": 'deflate'}, True),
    ({"compression": 'DEFLATE'}, True),
    ({"compression": 'gzip'}, True),
])
def testCreatinBackendWithCompression(compressionOptions, expectedCompression):
    backend = JSONRPCBackend("localhost", connectoninit=False, **compressionOptions)

    assert backend.isCompressionUsed() == expectedCompression


@pytest.mark.parametrize("value, expectedResult", [
    (False, False),
    (True, True),
    ("no", False),
    ("true", True),
    ('deflate', _DEFLATE_COMPRESSION),
    ('  DEFLATE  ', _DEFLATE_COMPRESSION),
    ('GZIP   ', _GZIP_COMPRESSION),
    ('gzip', _GZIP_COMPRESSION),
])
def testParsingCompressionValue(value, expectedResult):
    assert JSONRPCBackend._parseCompressionValue(value) == expectedResult


@pytest.mark.parametrize("header, expectedSessionID", [
    ({}, None),
    ({'set-cookie': "OPSISID=d395e2f8-9409-4876-bea9-cc621b829998; Path=/"}, "OPSISID=d395e2f8-9409-4876-bea9-cc621b829998"),
    ({'Set-Cookie': "SID=abc-def-12-345; Path=/"}, "SID=abc-def-12-345"),
    ({'SET-COOKIE': "weltunter"}, "weltunter"),
    ({'FAT-NOOKIE': "foo"}, None),
])
def testReadingSessionID(jsonRpcBackend, header, expectedSessionID):
    response = FakeResponse(
        data='randomtext',
        header=header
    )

    jsonRpcBackend._processResponse(response)

    assert jsonRpcBackend._sessionId == expectedSessionID
