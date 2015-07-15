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
Testing functionality of OPSI.Util.Task.Samba

:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3
"""

import random
import re
import os
import mock
import unittest
import OPSI.Util.Task.Samba as Samba
from collections import defaultdict

class SambaTest(unittest.TestCase):

	def testNoSmbd(self):

		def fakeWhich(command):
			return None

		def fakeExecute(command):
			return None

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertFalse(Samba.isSamba4())

	def testIsSamba4(self):

		def fakeExecute(command):
			return ['version 4.0.3']

		def fakeWhich(command):
			return command

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertTrue(Samba.isSamba4())

		def fakeExecute(command):
			return ['version ']

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertFalse(Samba.isSamba4())

	def testSambaConfigure(self):

		def fakeSambaServiceName(command):
			return None

		with mock.patch('OPSI.Util.Task.Samba.Posix.getSambaServiceName', fakeSambaServiceName):
			self.assertFalse(Samba.configureSamba())


def main():
	unittest.main()

if __name__ == '__main__':
	main()
