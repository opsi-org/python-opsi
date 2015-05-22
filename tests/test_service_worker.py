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


class WorkerOpsiJsonRpcTestCase(unittest.TestCase):

	def setUp(self):
		r = FakeRequest()
		self.worker = WorkerOpsiJsonRpc(service=None, request=r, resource=None)

	def tearDown(self):
		del self.worker

	def testReturningCorrectEncoding(self):
		# TODO: this is work in progress
		result = self.worker._generateResponse(None)
		self.assertTrue(200, result.code)


if __name__ == '__main__':
	unittest.main()
