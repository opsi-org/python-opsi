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

from OPSI.Service.Session import Session, SessionHandler


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


class SessionHandlerTestCase(unittest.TestCase):
	def testInitialisation(self):
		handler = SessionHandler("testapp", 10, maxSessionsPerIp=4, sessionDeletionTimeout=23)
		self.assertEquals("testapp", handler.sessionName)
		self.assertEquals(10, handler.sessionMaxInactiveInterval)
		self.assertEquals(4, handler.maxSessionsPerIp)
		self.assertEquals(23, handler.sessionDeletionTimeout)

		self.assertFalse(handler.sessions)

	def testSessionCreationAndExpiration(self):
		handler = SessionHandler()
		self.assertFalse(handler.sessions)

		session = handler.createSession()
		self.assertEquals(1, len(handler.sessions))
		self.assertEquals(handler, session.sessionHandler)

		session.expire()
		self.assertEquals(0, len(handler.sessions))

	def testDeletingAllSessions(self):
		handler = SessionHandler()
		self.assertEquals(0, len(handler.sessions))

		for _ in range(10):
			handler.createSession()

		self.assertEquals(10, len(handler.sessions))

		handler.deleteAllSessions()
		self.assertEquals(0, len(handler.sessions))

	def testDeletingSessionInUse(self):
		handler = SessionHandler(sessionDeletionTimeout=2)
		self.assertEquals(0, len(handler.sessions))

		session = handler.createSession()
		self.assertEquals(1, len(handler.sessions))

		session.increaseUsageCount()
		session.increaseUsageCount()
		session.expire()

		self.assertEquals(0, len(handler.sessions))


if __name__ == '__main__':
	unittest.main()
