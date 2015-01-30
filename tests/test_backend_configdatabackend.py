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
Testing ConfigDataBackend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import mock
import os
import shutil
import tempfile
import unittest

import OPSI.Backend.Backend
from OPSI.Types import BackendBadValueError


class ConfigDataBackendTestCase(unittest.TestCase):
	def setUp(self):
		self.logDirectory = tempfile.mkdtemp()
		self.logDirectoryPatch = mock.patch('OPSI.Backend.Backend.LOG_DIR', self.logDirectory)
		self.logDirectoryPatch.start()

	def tearDown(self):
		if os.path.exists(self.logDirectory):
			shutil.rmtree(self.logDirectory)

		self.logDirectoryPatch.stop()

	def test_reading_log_fails_if_type_unknown(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		self.assertRaises(BackendBadValueError, cdb.log_read, 'blablabla')

	def test_reading_log_requires_objectId(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()

		for logType in ('bootimage', 'clientconnect', 'userlogin', 'instlog', 'opsiconfd'):
			self.assertRaises(BackendBadValueError, cdb.log_read, logType)

	def test_reading_opsiconfd_log_does_not_require_objectId(self):
		cdb = OPSI.Backend.Backend.ConfigDataBackend()
		cdb.log_read('opsiconfd')


if __name__ == '__main__':
	unittest.main()
