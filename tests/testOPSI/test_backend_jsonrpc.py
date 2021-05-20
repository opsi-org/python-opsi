# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the JSON-RPC backend.
"""
import pytest

from OPSI.Backend.JSONRPC import _GZIP_COMPRESSION
from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Util.HTTP import HTTPHeaders, deflateEncode, gzipEncode
from OPSI.Util import randomString


class FakeResponse:
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
		header={'Content-Encoding': contentEncoding}
	)

	assert text.encode() == jsonRpcBackend._processResponse(response)


@pytest.mark.parametrize("compressionOptions, expectedCompression", [
	({"deflate": False}, False),
	({"deflate": True}, False),  # not supported anymore.
	({"compression": False}, False),
	({"compression": True}, True),
	({"compression": 'deflate'}, False),
	({"compression": 'DEFLATE'}, False),
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
	('deflate', False),  # deprecated
	('  DEFLATE  ', False),  # deprecated
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
