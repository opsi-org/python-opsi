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
Testing ConfigDataBackend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os

import OPSI.Backend.Backend
from OPSI.Types import BackendBadValueError

from .helpers import mock, workInTemporaryDirectory

import pytest


@pytest.yield_fixture
def logBackend(patchLogDir):
	yield OPSI.Backend.Backend.ConfigDataBackend()


@pytest.yield_fixture
def patchLogDir():
	with workInTemporaryDirectory() as tempDir:
		with mock.patch('OPSI.Backend.Backend.LOG_DIR', tempDir):
			yield tempDir


def testReadingLogFailsIfTypeUnknown(logBackend):
	with pytest.raises(BackendBadValueError):
		logBackend.log_read('unknowntype')


@pytest.mark.parametrize("logType", ['bootimage', 'clientconnect', 'instlog', 'userlogin'])
def testReadingLogRequiresObjectId(logBackend, logType):
	with pytest.raises(BackendBadValueError):
		logBackend.log_read(logType)


def testReadingOpsiconfdLogDoesNotRequireObjectId(logBackend):
	logBackend.log_read('opsiconfd')


@pytest.mark.parametrize("objectId", [None, 'unknown_object'])
def testReadingNonExistingLogReturnsEmptyString(logBackend, objectId):
	"""
	Valid calls to read logs should return empty strings if no file
	does exist.
	"""
	assert '' == logBackend.log_read('opsiconfd', objectId)


def testOnlyValidLogTypesAreWritten(logBackend):
	with pytest.raises(BackendBadValueError):
		logBackend.log_write('foobar', '')


@pytest.mark.parametrize("objectId", [
	'foo.bar.baz',
	'opsiconfd',
	pytest.mark.xfail(''),
	pytest.mark.xfail(None),
])
@pytest.mark.parametrize("logType", [
	'bootimage',
	'clientconnect',
	'instlog',
	'opsiconfd',
	'userlogin'
])
def testWritingLogRequiresValidObjectId(logBackend, logType, objectId):
	logBackend.log_write(logType, 'logdata', objectId)


def testWritingAndThenReadingDataFromLog(logBackend):
	logBackend.log_write('opsiconfd', 'data', objectId='foo.bar.baz')

	assert 'data' == logBackend.log_read('opsiconfd', 'foo.bar.baz')


@pytest.mark.parametrize("logType", [
	'bootimage', 'clientconnect', 'instlog', 'opsiconfd', 'userlogin'
])
def testWritingLogCreatesFile(patchLogDir, logType):
	cdb = OPSI.Backend.Backend.ConfigDataBackend()
	cdb.log_write(logType, 'logdata', objectId='foo.bar.baz')

	expectedLogDir = os.path.join(patchLogDir, logType)
	assert os.path.exists(expectedLogDir)

	expectedLogPath = os.path.join(expectedLogDir, 'foo.bar.baz.log')
	assert os.path.exists(expectedLogPath)


@pytest.mark.parametrize("expected, text, length", [
		('', 'hallo\nwelt', 0),
		('o', 'hallo', 1),
		('llo', 'hallo', 3),
		('elt', 'hallo\nwelt', 3),
		('welt', 'hallo\nwelt', 4),
		('welt', 'hallo\nwelt', 5),
		('hallo\nwelt', 'hallo\nwelt', 10),
		('welt\n', 'hallo\nwelt\n', 10),
		('hallo\nwelt', 'hallo\nwelt', 15),
	])
def testTruncatingLogData(logBackend, text, length, expected):
	assert expected == logBackend._truncateLogData(text, length)


def testWritingAndThenReadingDataFromLogWithLimitedWrite(patchLogDir):
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=10)

	longData = 'data1\ndata2\ndata3\ndata4\n'
	cdb.log_write('opsiconfd', longData, objectId='foo.bar.baz')

	assert 'data4\n' == cdb.log_read('opsiconfd', 'foo.bar.baz')


def testWritingAndThenReadingDataFromLogWithLimitedRead(logBackend):
	objId = 'foo.bar.baz'
	longData = 'data1\ndata2\ndata3\ndata4\n'
	logBackend.log_write('opsiconfd', longData, objectId=objId)

	assert 'data4\n' == logBackend.log_read('opsiconfd', objId, maxSize=10)


def testAppendingLog(patchLogDir):
	data1 = 'data1\ndata2\ndata3\ndata4\n'
	data2 = "data5\n"

	maxLogSize = len(data1 + data2)
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=maxLogSize)

	cdb.log_write('opsiconfd', data1, objectId='foo.bar.baz')
	cdb.log_write('opsiconfd', data2, objectId='foo.bar.baz', append=True)

	logData = cdb.log_read('opsiconfd', 'foo.bar.baz', maxSize=maxLogSize)
	assert data1 + data2 == logData


def testWritingAndReadingLogWithoutLimits(patchLogDir):
	# 0 means no limit.
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=0)

	# The magic 218454 are meant to be more than:
	# MAX_LOG_SIZE / len('data1\ndata2\ndata3\ndata4\n')
	longData = 'data1\ndata2\ndata3\ndata4\n' * 218454
	cdb.log_write('opsiconfd', longData, objectId='foo.bar.baz')

	assert longData == cdb.log_read('opsiconfd', 'foo.bar.baz', maxSize=0)


def testTruncatingOldDataWhenAppending(patchLogDir):
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=15)

	objId = 'foo.bar.baz'
	cdb.log_write('opsiconfd', u'data1data2data3data4data5', objectId=objId)
	cdb.log_write('opsiconfd', u'data6', objectId=objId, append=True)

	assert 'data4data5data6' == cdb.log_read('opsiconfd', objectId=objId)


def testOverwritingOldDataInAppendMode(patchLogDir):
	"""
	With size limits in place old data should be overwritten.

	Each write operation submits data that is as long as our limit.
	So every write operation should override the previously written
	data.
	"""
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=5)

	objId = 'foo.bar.baz'
	cdb.log_write('opsiconfd', u'data1', objectId=objId, append=True)
	cdb.log_write('opsiconfd', u'data2', objectId=objId, append=True)
	cdb.log_write('opsiconfd', u'data3', objectId=objId, append=True)

	assert 'data3' == cdb.log_read('opsiconfd', objectId=objId, maxSize=0)


def testTruncatingOldDataWhenAppendingWithNewlines(patchLogDir):
	"If we append data we want to truncate the data at a newline."

	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=15)

	objId = 'foo.bar.baz'
	cdb.log_write('opsiconfd', u'data1data2data3data4data5\n', objectId=objId, append=True)
	cdb.log_write('opsiconfd', u'data6', objectId=objId, append=True)

	assert 'data6' == cdb.log_read('opsiconfd', objectId=objId)


def testOverwritingOldDataInAppendModeWithNewlines(patchLogDir):
	"""
	With size limits in place old data should be overwritten - even with newlines.

	Each write operation submits data that is as long as our limit.
	So every write operation should override the previously written
	data.
	"""
	cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=7)

	objId = 'foo.bar.baz'
	cdb.log_write('opsiconfd', u'data3\ndata4\n', objectId=objId)
	cdb.log_write('opsiconfd', u'data4\ndata5\n', objectId=objId, append=True)

	assert 'data5\n' == cdb.log_read('opsiconfd', objectId=objId)
	assert 'data5\n' == cdb.log_read('opsiconfd', objectId=objId, maxSize=0)
