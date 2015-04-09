#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing our logger.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import mock
import sys
import warnings

import OPSI.Logger
from OPSI.Types import forceUnicode

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
	from io import BytesIO as StringIO
except ImportError:
	from StringIO import StringIO


class LoggerTestCase(unittest.TestCase):
	def setUp(self):
		self.logger = OPSI.Logger.LoggerImplementation()

	def tearDown(self):
		self.logger.setConsoleLevel(OPSI.Logger.LOG_NONE)
		self.logger.setFileLevel(OPSI.Logger.LOG_NONE)

		# Making sure that a possible switched function is resetted to
		# it's default.
		warnings.showwarning = OPSI.Logger._showwarning

	def testChangingConsoleLogLevel(self):
		logLevel = (OPSI.Logger.LOG_CONFIDENTIAL,
					OPSI.Logger.LOG_DEBUG2,
					OPSI.Logger.LOG_DEBUG,
					OPSI.Logger.LOG_INFO,
					OPSI.Logger.LOG_NOTICE,
					OPSI.Logger.LOG_WARNING,
					OPSI.Logger.LOG_ERROR,
					OPSI.Logger.LOG_CRITICAL,
					OPSI.Logger.LOG_ESSENTIAL,
					OPSI.Logger.LOG_COMMENT,
					OPSI.Logger.LOG_NONE)

		for level in logLevel:
			self.logger.setConsoleLevel(level)
			self.assertEquals(level, self.logger.getConsoleLevel())

		for level in reversed(logLevel):
			self.logger.setConsoleLevel(level)
			self.assertEquals(level, self.logger.getConsoleLevel())

	def testLoggingMessage(self):
		level = OPSI.Logger.LOG_CONFIDENTIAL
		self.logger.setConsoleLevel(level)

		messageBuffer = StringIO()
		with mock.patch('OPSI.Logger.sys.stdin', messageBuffer):
			with mock.patch('OPSI.Logger.sys.stderr', messageBuffer):
				self.logger.log(level, "This is not a test!",
								raiseException=True)

		self.assertTrue("This is not a test!" in messageBuffer.getvalue())

	def testLoggingUnicode(self):
		level = OPSI.Logger.LOG_CONFIDENTIAL
		self.logger.setConsoleLevel(level)

		messageBuffer = StringIO()
		with mock.patch('OPSI.Logger.sys.stdin', messageBuffer):
			with mock.patch('OPSI.Logger.sys.stderr', messageBuffer):
				self.logger.log(level, u"Heävy Metäl Ümläüts! Öy!",
								raiseException=True)

		# Currently this has to be suffice
		# TODO: better check for logged string.
		self.assertTrue(messageBuffer.getvalue())

	def test_logTwisted(self):
		try:
			from twisted.python import log
		except ImportError:
			self.skipTest("Could not import twisted log module.")

		self.logger.setConsoleLevel(OPSI.Logger.LOG_DEBUG)
		self.logger.setLogFormat('[%l] %M')

		err = StringIO()

		with mock.patch('OPSI.Logger.sys.stdin', err):
			with mock.patch('OPSI.Logger.sys.stderr', err):
				self.logger.startTwistedLogging()

				value = err.getvalue()
				self.assertNotEquals("", value)
				self.assertEquals("[{0:d}] [twisted] Log opened.\n".format(OPSI.Logger.LOG_DEBUG), value)
				err.seek(0)
				err.truncate(0)

				log.msg("message")
				value = err.getvalue()
				self.assertNotEquals("", value)
				self.assertEquals("[{0:d}] [twisted] message\n".format(OPSI.Logger.LOG_DEBUG), value)
				err.seek(0)
				err.truncate(0)

				log.err("message")
				value = err.getvalue()
				self.assertEquals("[{0:d}] [twisted] 'message'\n".format(OPSI.Logger.LOG_ERROR), value)

	def testPatchingShowwarnings(self):
		originalWarningFunction = warnings.showwarning
		self.assertTrue(originalWarningFunction is warnings.showwarning)

		self.logger.logWarnings()
		self.assertFalse(originalWarningFunction is warnings.showwarning)

		warnings.showwarning = originalWarningFunction

	def testLoggingFromWarningsModule(self):
		self.logger.setConsoleLevel(OPSI.Logger.LOG_WARNING)
		self.logger.setLogFormat('[%l] %M')

		messageBuffer = StringIO()

		with mock.patch('OPSI.Logger.sys.stdin', messageBuffer):
			with mock.patch('OPSI.Logger.sys.stderr', messageBuffer):
				self.logger.logWarnings()

				warnings.warn("usermessage")
				warnings.warn("another message", DeprecationWarning)
				warnings.warn("message", DeprecationWarning, stacklevel=2)

		value = messageBuffer.getvalue()

		self.assertTrue(value.startswith("[{0:d}]".format(OPSI.Logger.LOG_WARNING)))
		self.assertTrue("UserWarning: usermessage" in value)

		if sys.version_info < (2, 7):
			# Changed in version 2.7: DeprecationWarning is ignored by default.
			# Source: https://docs.python.org/2.7/library/warnings.html#warning-categories
			self.assertTrue("DeprecationWarning: message" in value)
			self.assertTrue("DeprecationWarning: another message" in value)
