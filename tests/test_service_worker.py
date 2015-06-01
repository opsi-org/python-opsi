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
Testing the workers.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Service.Worker import WorkerOpsiJsonRpc


class FakeHeader(object):
	def __init__(self, headers=None):
		self.headers = headers or {}

	def hasHeader(self, header):
		return header in self.headers

	def getHeader(self, header):
		return self.headers[header]


class FakeRequest(object):
	def __init__(self, headers=None):
		self.headers = headers or FakeHeader()


class FakeRPC(object):
			def __init__(self, result=None):
				self.result = result or None

			def getResponse(self):
				return self.result


class WorkerOpsiJsonRpcTestCase(unittest.TestCase):

	def setUp(self):
		r = FakeRequest()
		self.worker = WorkerOpsiJsonRpc(service=None, request=r, resource=None)

	def tearDown(self):
		del self.worker

	def testReturningEmptyResponse(self):
		"""
		Making sure that an empty uncompressed response is returned.

		We check the headers of the request and also make sure that
		the content is "null".
		"""
		result = self.worker._generateResponse(None)
		self.assertTrue(200, result.code)
		self.assertTrue(result.headers.hasHeader('content-type'))
		self.assertFalse(result.headers.hasHeader('content-encoding'))
		self.assertEquals(['application/json;charset=utf-8'], result.headers.getRawHeaders('content-type'))
		self.assertEquals('null', str(result.stream.read()))

	def testHandlingMultipleRPCs(self):
		"""
		With multiple RPCs the results are returned in a list.

		We do not use any compression in this testcase.
		"""
		class FakeRPC(object):
			def __init__(self, result=None):
				self.result = result or None

			def getResponse(self):
				return self.result

		self.worker._rpcs = [FakeRPC(), FakeRPC(1), FakeRPC(u"FÄKE!"),
							FakeRPC({"Narziss": "Morgen Nicht Geboren"})]

		result = self.worker._generateResponse(None)
		self.assertTrue(200, result.code)
		self.assertTrue(result.headers.hasHeader('content-type'))
		self.assertFalse(result.headers.hasHeader('content-encoding'))
		self.assertEquals(['application/json;charset=utf-8'], result.headers.getRawHeaders('content-type'))
		self.assertEquals('[null, 1, "F\xc3\x84KE!", {"Narziss": "Morgen Nicht Geboren"}]', str(result.stream.read()))

	def testHandlingSingleResult(self):
		"""
		A single RPC result must not be returned in a list.
		"""
		self.worker._rpcs = [FakeRPC("Hallo Welt")]
		result = self.worker._generateResponse(None)
		self.assertTrue(200, result.code)
		self.assertTrue(result.headers.hasHeader('content-type'))
		self.assertFalse(result.headers.hasHeader('content-encoding'))
		self.assertEquals(['application/json;charset=utf-8'], result.headers.getRawHeaders('content-type'))
		self.assertEquals('"Hallo Welt"', str(result.stream.read()))

	def testHandlingSingleResultConsistingOfList(self):
		"""
		If a single result is made the result is a list this list must not be unpacked.
		"""
		self.worker._rpcs = [FakeRPC(["Eins", "Zwei", "Drei"])]
		result = self.worker._generateResponse(None)
		self.assertTrue(200, result.code)
		self.assertTrue(result.headers.hasHeader('content-type'))
		self.assertFalse(result.headers.hasHeader('content-encoding'))
		self.assertEquals(['application/json;charset=utf-8'], result.headers.getRawHeaders('content-type'))
		self.assertEquals('["Eins", "Zwei", "Drei"]', str(result.stream.read()))


if __name__ == '__main__':
	unittest.main()
