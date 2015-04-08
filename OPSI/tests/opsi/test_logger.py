# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH

   http://www.uib.de/

   All rights reserved.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.

   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

from testtools import TestCase

import sys
import warnings
try:
	from io import BytesIO as StringIO
except ImportError:
	from StringIO import StringIO

from OPSI.Logger import LoggerImplementation, LOG_WARNING


class LoggerTestCase(TestCase):
	def setUp(self):
		super(LoggerTestCase, self).setUp()
		self.logger = LoggerImplementation()

	def test_logWarningsModule(self):
		buffer = StringIO()

		self.patch(sys, "stdout", buffer)
		self.patch(sys, "stderr", buffer)

		self.logger.setConsoleLevel(LOG_WARNING)
		self.logger.setLogFormat('[%l] %M')
		self.logger.logWarnings()
		warnings.warn("message", DeprecationWarning, stacklevel=2)

		value = buffer.getvalue()
		self.assertNotEquals("", value)
		self.assertTrue(value.startswith("[%d]" % LOG_WARNING))
		self.assertTrue(value.find("DeprecationWarning: message"))

	def tearDown(self):
		super(LoggerTestCase, self).tearDown()
		self.logger.setConsoleLevel(0)
		self.logger.setFileLevel(0)


def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)
