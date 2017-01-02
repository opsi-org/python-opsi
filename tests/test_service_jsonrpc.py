#! /usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2017 uib GmbH <info@uib.de>

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
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
from __future__ import absolute_import, print_function

import pytest

from OPSI.Service.JsonRpc import JsonRpc

from .helpers import mock


@pytest.mark.parametrize("invalidRpcInfo", [
	None,
    {},
    {"id": 0},
    {"tid": 0},
    {"id": 1},
    {"id": 1, "method": ""},
    {"id": 1, "method": None},
    {"id": 1, "method": 0},
    {"id": 1, "method": False},
])
def testJsonRpcRequiresTransactionId(invalidRpcInfo):
	with pytest.raises(Exception):  # TODO: better Exception class
		JsonRpc(None, None, invalidRpcInfo)


def testLoggingTracebackMayFail():
	j = JsonRpc(None, interface=[], rpc={"id": 1, "method": "foo"})

	with mock.patch('OPSI.Service.JsonRpc.sys.exc_info', return_value=[None, None, object()]):
		j.execute()

	assert j.ended
	assert j.exception
	assert j.traceback

	print("Collected traceback: {0!r}".format(j.traceback))
	print("Collected Exception: {0!r}".format(j.exception))

	assert 'Failed to collect traceback' in j.traceback[-1]


def testLoggingTraceback():
	j = JsonRpc(None, interface=[], rpc={"id": 1, "method": "foo"})
	j.execute()

	assert j.ended
	assert j.exception
	assert j.traceback

	print("Old traceback was something like this: {0!r}".format(
		[u"     line 105 in 'execute' in file '/root/python-opsi/OPSI/Service/JsonRpc.py'"]
	))
	print("Collected traceback: {0!r}".format(j.traceback))
	print("Collected Exception: {0!r}".format(j.exception))

	assert 'line' in ''.join(j.traceback).lower()
	assert 'file' in ''.join(j.traceback).lower()
	assert 'jsonrpc' in ''.join(j.traceback).lower()  # Module name
	assert 'execute' in ''.join(j.traceback).lower()  # Function name


def testExecutingMethodOnInstance():
	class TestInstance:
		def testMethod(self):
			return ["yeah it works!"]

	j = JsonRpc(
		instance=TestInstance(),
		interface=[{"name": "testMethod", "keywords": []}],
		rpc={"id": 42, "method": "testMethod"}
	)
	j.execute()

	assert j.ended
	assert not j.traceback
	assert not j.exception

	response = j.getResponse()
	assert response

	assert response['id'] == 42
	assert response['result'] == ["yeah it works!"]
	assert not response['error']


def testRequiringValidMethod():
	j = JsonRpc(None, [], {"id": 1, "method": "foo"})
	j.execute()

	assert j.ended
	assert j.traceback
	assert j.exception

	print("Collected Exception: {0!r}".format(j.exception))

	assert "Method 'foo' is not valid" in str(j.exception)


def testGettingMetainformation():
	j = JsonRpc(None, None, {"id": 1, "method": "foo"})

	assert not j.isStarted()
	assert not j.hasEnded()
	assert j.getMethodName() == "foo"

	assert j.getDuration() == None

	j.execute()

	assert j.isStarted()
	assert j.hasEnded()
	assert j.getDuration() != None
