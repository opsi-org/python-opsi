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
Testing the workers.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import gzip
import pytest
import zlib
from contextlib import closing  # Needed for Python 2.6

try:
	from cStringIO import StringIO
except ImportError:
	from io import StringIO

from .helpers import mock

from OPSI.Service.Worker import WorkerOpsi, WorkerOpsiJsonRpc


@pytest.fixture
def enableRFCConformHeaders():
	with mock.patch.object(WorkerOpsiJsonRpc, 'RFC_CONFORM_HEADERS', True):
		yield


class FakeHeader(object):
	def __init__(self, headers=None):
		self.headers = headers or {}

	def hasHeader(self, header):
		return header in self.headers

	def getHeader(self, header):
		return self.headers[header]


class FakeDictHeader(FakeHeader):
	def getHeader(self, header):
		class ReturnWithMediaType:
			def __init__(self, key):
				self.mediaType = key

		return dict((ReturnWithMediaType(self.headers[key]), self.headers[key]) for key in self.headers if key.startswith(header))


class FakeMediaType(object):
	def __init__(self, type):
		self.mediaType = type


class FakeRequest(object):
	def __init__(self, headers=None):
		self.headers = headers or FakeHeader()
		self.method = 'POST'


class FakeRPC(object):
	def __init__(self, result=None):
		self.result = result or None

	def getResponse(self):
		return self.result


def testReturningEmptyResponse(enableRFCConformHeaders):
	"""
	Making sure that an empty uncompressed response is returned.

	We check the headers of the request and also make sure that
	the content is "null".
	"""
	worker = WorkerOpsiJsonRpc(service=None, request=FakeRequest(), resource=None)

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert not result.headers.hasHeader('content-encoding')
	assert 'null' == str(result.stream.read())


def testHandlingMultipleRPCs(enableRFCConformHeaders):
	"""
	With multiple RPCs the results are returned in a list.

	We do not use any compression in this testcase.
	"""
	worker = WorkerOpsiJsonRpc(service=None, request=FakeRequest(), resource=None)
	worker._rpcs = [
		FakeRPC(), FakeRPC(1), FakeRPC(u"FÄKE!"),
		FakeRPC({"Narziss": "Morgen Nicht Geboren"})
	]

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert not result.headers.hasHeader('content-encoding')
	assert '[null, 1, "F\xc3\x84KE!", {"Narziss": "Morgen Nicht Geboren"}]' == str(result.stream.read())


def testHandlingSingleResult(enableRFCConformHeaders):
	"""
	A single RPC result must not be returned in a list.
	"""
	worker = WorkerOpsiJsonRpc(service=None, request=FakeRequest(), resource=None)
	worker._rpcs = [FakeRPC("Hallo Welt")]

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert not result.headers.hasHeader('content-encoding')
	assert '"Hallo Welt"' == str(result.stream.read())


def testHandlingSingleResultConsistingOfList(enableRFCConformHeaders):
	"""
	If a single result is made the result is a list this list must not be unpacked.
	"""
	worker = WorkerOpsiJsonRpc(service=None, request=FakeRequest(), resource=None)
	worker._rpcs = [FakeRPC(["Eins", "Zwei", "Drei"])]

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert not result.headers.hasHeader('content-encoding')
	assert '["Eins", "Zwei", "Drei"]' == str(result.stream.read())


def testCompressingResponseDataWithGzip(enableRFCConformHeaders):
	"""
	Responding with data compressed by gzip.
	"""
	testHeader = FakeHeader({"Accept-Encoding": "gzip"})
	request = FakeRequest(testHeader)
	worker = WorkerOpsiJsonRpc(service=None, request=request, resource=None)

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert ['gzip'] == result.headers.getRawHeaders('content-encoding')

	sdata = result.stream.read()

	with closing(gzip.GzipFile(fileobj=StringIO(sdata), mode="r")) as gzipfile:
		data = gzipfile.read()

	assert 'null' == data


def testCompressingResponseDataWithDeflate(enableRFCConformHeaders):
	"""
	Responding with data compressed by deflate.
	"""
	testHeader = FakeHeader({"Accept-Encoding": "deflate"})
	request = FakeRequest(testHeader)
	worker = WorkerOpsiJsonRpc(service=None, request=request, resource=None)

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert ['deflate'] == result.headers.getRawHeaders('content-encoding')

	sdata = result.stream.read()
	data = zlib.decompress(sdata)
	assert 'null' == data


def testCompressingResponseIfInvalidMimetype(enableRFCConformHeaders):
	"""
	Staying backwards compatible.

	Old clients connect to the server and send an "Accept" with
	the invalid mimetype "gzip-application/json-rpc".
	We must respond to these clients because not doing so could
	result in rendering an opsi landscape unresponding.

	The returned "content-type" is invalid and makes no sense.
	Correct would be "application/json".
	The returned content-encoding is "gzip" but the content
	is acutally compressed with deflate.
	"""
	testHeader = FakeDictHeader({
		"Accept": "gzip-application/json-rpc",
		"invalid": "ignoreme"
	})
	request = FakeRequest(testHeader)
	worker = WorkerOpsiJsonRpc(service=None, request=request, resource=None)

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['gzip'] == result.headers.getRawHeaders('content-encoding')
	assert ['gzip-application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')

	sdata = result.stream.read()
	data = zlib.decompress(sdata)
	assert 'null' == data


def testReturningPlainCalls(enableRFCConformHeaders):
	testHeader = FakeDictHeader({"Accept": "text/plain"})
	request = FakeRequest(testHeader)
	worker = WorkerOpsiJsonRpc(service=None, request=request, resource=None)

	result = worker._generateResponse(None)
	assert 200 == result.code
	assert result.headers.hasHeader('content-type')
	assert ['application/json;charset=utf-8'] == result.headers.getRawHeaders('content-type')
	assert not result.headers.hasHeader('content-encoding')

	data = result.stream.read()
	assert 'null' == str(data)


def testDecodingOldCallQuery():
	r = FakeRequest(headers=FakeHeader(
		{
			"content-encoding": "gzip",
			"content-type": FakeMediaType("gzip-application/json-rpc"),
		}
	))

	worker = WorkerOpsi(service=None, request=r, resource=None)
	worker.query = zlib.compress("Test 1234")
	worker._decodeQuery(None)
	assert u'Test 1234' == worker.query
