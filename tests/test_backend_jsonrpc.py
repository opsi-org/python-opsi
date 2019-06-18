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

from OPSI.Backend.JSONRPC import JSONRPCBackend, _DEFLATE_COMPRESSION
from OPSI.Util.HTTP import deflateEncode, gzipEncode
from OPSI.Util import randomString


class FakeResponse(object):
    def __init__(self, header=None, data=None):
        self._header = header or {}
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
])
def testParsingCompressionValue(value, expectedResult):
    assert JSONRPCBackend._parseCompressionValue(value) == expectedResult
