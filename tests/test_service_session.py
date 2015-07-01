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
Testing session and sessionhandler.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest
from contextlib import contextmanager

from OPSI.Service.Session import Session


@contextmanager
def getTestSession(sessionHandler=None, **kwargs):
	session = Session(sessionHandler or FakeSessionHandler(), **kwargs)
	yield session

	# This may leave a thread running afterwards
	if session.sessionTimer:
		session.sessionTimer.cancel()
		session.sessionTimer.join(1)

	session.sessionTimer = None


class FakeSessionHandler:
	def sessionExpired(self, session):
		pass


class SessionTestCase(unittest.TestCase):
	def testUsageCount(self):
		with getTestSession() as session:
			self.assertEquals(0, session.usageCount)

			session.increaseUsageCount()
			self.assertEquals(1, session.usageCount)

			session.decreaseUsageCount()
			self.assertEquals(0, session.usageCount)

	def testUsageCountDoesNothingOnExpiredSession(self):
		with getTestSession() as session:
			self.assertEquals(0, session.usageCount)

			session.delete()

			session.increaseUsageCount()
			self.assertEquals(0, session.usageCount)

			session.decreaseUsageCount()
			self.assertEquals(0, session.usageCount)

	def testMarkingForDeletion(self):
		with getTestSession() as session:
			self.assertFalse(session.getMarkedForDeletion(),
				"New session should not be marked for deletion."
			)

			self.assertFalse(session.getMarkedForDeletion())

			session.setMarkedForDeletion()

			self.assertTrue(session.getMarkedForDeletion())

	def testValidity(self):
		with getTestSession() as session:
			self.assertTrue(session.getValidity())

	def testDeletedSessionsAreInvalid(self):
		with getTestSession() as session:
			session.delete()
			self.assertFalse(session.getValidity())


if __name__ == '__main__':
	unittest.main()
