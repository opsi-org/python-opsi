#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016 uib GmbH <info@uib.de>

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
Testing of a JSONRPCBackend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import json
from contextlib import contextmanager

from . import getTestBackend
from ..helpers import patchAddress, mock

from OPSI.Backend.JSONRPC import JSONRPCBackend
from OPSI.Util import toJson
from OPSI.Util.HTTP import deflateEncode, gzipDecode


import OPSI.Util.HTTP


class MockResponse(object):

	def __init__(self, data):
		self.data = data

	def getheader(self, header, default=''):
		return default

	def setheader(self, header, value):
		pass


class JSONRPCTestCase(object):

	def _mock_urlopen(self, method, url, body=None, headers=None, retry=True, redirect=True, assert_same_host=True, firstTryTime=None):
		if headers is None:
			headers = {}
		if 'gzip' in headers['content-type']:
			body = gzipDecode(body)
		d = json.JSONDecoder().decode(body)

		# TODO: improve current implementation
		# The current implementation fails to hand over the reference
		# to self on methods that require it.
		# This leads to a TypeError saying that insufficent arguments
		# were given to the function.
		params = d["params"]
		args = []
		kwargs = {}

		if len(params) == 2:
			args.append(params[0])
			kwargs.update(params[1])
		elif len(params) == 1:
			if params[0].__class__ == "dict":
				kwargs.update(params[0])
			else:
				args.append(params[0])

		try:
			method = getattr(self._dataBackend, d['method'])
			if method:
				data = method(*args, **kwargs)
				result = {
					"id": 1,
					"result": [],
					"error": None
				}

				if data is not None:
					result["result"] = data

				jsonstr = toJson(result)
				return MockResponse(jsonstr)
			else:
				raise RuntimeError("Missing method {0!r} on Fake-Backend.".format(d['method']))
		except Exception as err:
			print("Problem in mock_urlopen: {0}".format(err))
			raise err

	def setUpBackend(self):
		self._address_patch = patchAddress()
		self._address_patch.__enter__()

		self._http_pool_patch = mock.patch('OPSI.Util.HTTP.HTTPConnectionPool.urlopen', self._mock_urlopen)
		self._https_pool_patch = mock.patch('OPSI.Util.HTTP.HTTPSConnectionPool.urlopen', self._mock_urlopen)
		self._http_pool_patch.start()
		self._https_pool_patch.start()

		self._backend_context = getTestBackend(extended=True)
		self._dataBackend = self._backend_context.__enter__()

		self.backend = JSONRPCBackend(
			username='testUser',
			password='h1ddenpw',
			address='localhost',
		)

	def tearDownBackend(self):
		try:
			self._backend_context.__exit__(None, None, None)
		except Exception:
			pass

		try:
			self._address_patch.__exit__(None, None, None)
		except Exception:
			pass

		try:
			self._http_pool_patch.stop()
		except Exception:
			pass

		try:
			self._https_pool_patch.stop()
		except Exception:
			pass

		try:
			self.backend.backend_exit()
		finally:
			del self._dataBackend


@contextmanager
def getJSONRPCBackend():
	with patchAddress():
		with getTestBackend(extended=True) as dataBackend:

			def mock_urlopen(self, method, url, body=None, headers=None, retry=True, redirect=True, assert_same_host=True, firstTryTime=None):
				headers = headers or {}
				if 'gzip' in headers['content-type']:
					body = gzipDecode(body)
				d = json.JSONDecoder().decode(body)

				params = d["params"]
				args = []
				kwargs = {}

				if len(params) == 2:
					args.append(params[0])
					kwargs.update(params[1])
				elif len(params) == 1:
					if params[0].__class__ == "dict":
						kwargs.update(params[0])
					else:
						args.append(params[0])

				method = getattr(dataBackend, d['method'])
				print("Method: {0}".format(method))

				if method:
					data = method(*args, **kwargs)
					result = {"id": 1, "result": [], "error": None}
					if data is not None:
						result["result"] = data

					jsonstr = toJson(result)
					return MockResponse(jsonstr)

			with mock.patch.object(OPSI.Util.HTTP.HTTPConnectionPool, "urlopen", mock_urlopen):
				with mock.patch.object(OPSI.Util.HTTP.HTTPSConnectionPool, "urlopen", mock_urlopen):
					try:
						backend = JSONRPCBackend(username='root', password='linux123', address='localhost', connectoninit=False)
						yield backend
					finally:
						try:
							backend.backend_exit()
						except NameError:
							pass
