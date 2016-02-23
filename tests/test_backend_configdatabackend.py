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

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import OPSI.Backend.Backend
from OPSI.Types import BackendBadValueError

from .helpers import mock, unittest


class ConfigDataBackendLogTestCase(unittest.TestCase):
	def setUp(self):
		self.logDirectory = tempfile.mkdtemp()
		self.logDirectoryPatch = mock.patch('OPSI.Backend.Backend.LOG_DIR', self.logDirectory)
		self.logDirectoryPatch.start()

	def tearDown(self):
		if os.path.exists(self.logDirectory):
			shutil.rmtree(self.logDirectory)

		self.logDirectoryPatch.stop()

	def testReadingLogFailsIfTypeUnknown(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		self.assertRaises(BackendBadValueError, cdb.log_read, 'blablabla')

	def testReadingLogRequiresObjectId(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		for logType in ('bootimage', 'clientconnect', 'userlogin', 'instlog'):
			print("Logtype: {0}".format(logType))
			self.assertRaises(BackendBadValueError, cdb.log_read, logType)

	def testReadingOpsiconfdLogDoesNotRequireObjectId(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		cdb.log_read('opsiconfd')

	def testReadingNonExistingLogReturnsEmptyString(self):
		"""
		Valid calls to read logs should return empty strings if no file
		does exist.
		"""
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		self.assertEquals("", cdb.log_read('opsiconfd'))
		self.assertEquals("", cdb.log_read('opsiconfd', 'unknown_object'))

	def testOnlyValidLogTypesAreWritten(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		self.assertRaises(BackendBadValueError, cdb.log_write, 'foobar', '')

	def testWritingLogRequiresObjectId(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		self.assertRaises(BackendBadValueError, cdb.log_write, 'opsiconfd', None)

	def testWritingLogCreatesFile(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		cdb.log_write('opsiconfd', 'data', objectId='foo.bar.baz')

		expectedLogPath = os.path.join(self.logDirectory, 'opsiconfd', 'foo.bar.baz.log')
		self.assertTrue(os.path.exists(expectedLogPath),
						"Log path {0} should exist.".format(expectedLogPath))

	def testWritingAndThenReadingDataFromLog(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		cdb.log_write('opsiconfd', 'data', objectId='foo.bar.baz')

		self.assertEquals('data', cdb.log_read('opsiconfd', 'foo.bar.baz'))

	def testWritingAndThenReadingDataFromLogWithLimitedWrite(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=10)

		longData = 'data1\ndata2\ndata3\ndata4\n'
		cdb.log_write('opsiconfd', longData, objectId='foo.bar.baz')

		self.assertEquals('data4\n', cdb.log_read('opsiconfd', 'foo.bar.baz'))

	def testWritingAndThenReadingDataFromLogWithLimitedRead(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		longData = 'data1\ndata2\ndata3\ndata4\n'
		cdb.log_write('opsiconfd', longData, objectId='foo.bar.baz')

		self.assertEquals('data4\n', cdb.log_read('opsiconfd', 'foo.bar.baz', maxSize=10))

	def testAppendingLog(self):
		data1 = 'data1\ndata2\ndata3\ndata4\n'
		data2 = "data5\n"

		maxLogSize = len(data1 + data2)
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=maxLogSize)

		cdb.log_write('opsiconfd', data1, objectId='foo.bar.baz')
		cdb.log_write('opsiconfd', data2, objectId='foo.bar.baz', append=True)

		self.assertEquals(
			data1 + data2,
			cdb.log_read('opsiconfd', 'foo.bar.baz', maxSize=maxLogSize)
		)

	def testWritingAndReadingLogWithoutLimits(self):
		# Not even the sky is the limit!
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=0)

		# The magic 218454 are meant to be more than:
		# MAX_LOG_SIZE / len('data1\ndata2\ndata3\ndata4\n')
		longData = 'data1\ndata2\ndata3\ndata4\n' * 218454
		cdb.log_write('opsiconfd', longData, objectId='foo.bar.baz')

		self.assertEquals(longData, cdb.log_read('opsiconfd', 'foo.bar.baz', maxSize=0))

	def testTruncatingData(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		self.assertEquals('', cdb._truncateLogData('hallo\nwelt', 0))

		self.assertEquals('o', cdb._truncateLogData('hallo', 1))
		self.assertEquals('llo', cdb._truncateLogData('hallo', 3))

		self.assertEquals('elt', cdb._truncateLogData('hallo\nwelt', 3))
		self.assertEquals('welt', cdb._truncateLogData('hallo\nwelt', 4))
		self.assertEquals('welt', cdb._truncateLogData('hallo\nwelt', 5))

		self.assertEquals('hallo\nwelt', cdb._truncateLogData('hallo\nwelt', 10))
		self.assertEquals('welt\n', cdb._truncateLogData('hallo\nwelt\n', 10))
		self.assertEquals('hallo\nwelt', cdb._truncateLogData('hallo\nwelt', 15))

	def testTruncatingOldDataWhenAppending(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=15)

		cdb.log_write('opsiconfd', u'data1data2data3data4data5', objectId='foo.bar.baz')
		cdb.log_write('opsiconfd', u'data6', objectId='foo.bar.baz', append=True)

		self.assertEquals(
			'data4data5data6',
			cdb.log_read('opsiconfd', objectId='foo.bar.baz')
		)

	def testOverwritingOldDataInAppendMode(self):
		"""
		With size limits in place old data should be overwritten.

		Each write operation submits data that is as long as our limit.
		So every write operation should override the previously written
		data.
		"""
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=5)

		cdb.log_write('opsiconfd', u'data1', objectId='foo.bar.baz', append=True)
		cdb.log_write('opsiconfd', u'data2', objectId='foo.bar.baz', append=True)
		cdb.log_write('opsiconfd', u'data3', objectId='foo.bar.baz', append=True)

		self.assertEquals(
			'data3',
			cdb.log_read('opsiconfd', objectId='foo.bar.baz', maxSize=0)
		)

	def testTruncatingOldDataWhenAppendingWithNewlines(self):
		"If we append data we want to truncate the data at a newline."

		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=15)

		cdb.log_write('opsiconfd', u'data1data2data3data4data5\n', objectId='foo.bar.baz', append=True)
		cdb.log_write('opsiconfd', u'data6', objectId='foo.bar.baz', append=True)

		self.assertEquals('data6', cdb.log_read('opsiconfd', objectId='foo.bar.baz'))

	def testOverwritingOldDataInAppendModeWithNewlines(self):
		"""
		With size limits in place old data should be overwritten - even with newlines.

		Each write operation submits data that is as long as our limit.
		So every write operation should override the previously written
		data.
		"""
		cdb = OPSI.Backend.Backend.ConfigDataBackend(maxLogSize=7)

		cdb.log_write('opsiconfd', u'data3\ndata4\n', objectId='foo.bar.baz')
		cdb.log_write('opsiconfd', u'data4\ndata5\n', objectId='foo.bar.baz', append=True)

		self.assertEquals(
			'data5\n',
			cdb.log_read('opsiconfd', objectId='foo.bar.baz')
		)
		self.assertEquals(
			'data5\n',
			cdb.log_read('opsiconfd', objectId='foo.bar.baz', maxSize=0)
		)

if __name__ == '__main__':
	unittest.main()
