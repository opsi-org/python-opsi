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
Testing session and sessionhandler.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import time

from OPSI.Service.Session import Session, SessionHandler

import pytest


@pytest.fixture
def session():
	testSession = Session(FakeSessionHandler())
	try:
		yield testSession
	finally:
		# This may leave a thread running afterwards
		# if testSession and testSession.sessionTimer:
		try:
			testSession.sessionTimer.cancel()
			testSession.sessionTimer.join(1)
		except AttributeError:
			pass

		testSession.sessionTimer = None


class FakeSessionHandler(object):
	def sessionExpired(self, session):
		pass


def testSessionUsageCount(session):
	assert 0 == session.usageCount

	session.increaseUsageCount()
	assert 1 == session.usageCount

	session.decreaseUsageCount()
	assert 0 == session.usageCount


def testUsageCountDoesNothingOnExpiredSession(session):
	assert 0 == session.usageCount

	session.delete()

	session.increaseUsageCount()
	assert 0 == session.usageCount

	session.decreaseUsageCount()
	assert 0 == session.usageCount


def testMarkingSessionForDeletion(session):
	assert not session.getMarkedForDeletion(), "New session should not be marked for deletion."

	session.setMarkedForDeletion()

	assert session.getMarkedForDeletion()


def testSessionValidity(session):
	assert session.getValidity()


def testDeletedSessionsAreMadeInvalid(session):
	session.delete()
	assert not session.getValidity()


def testSessionHandlerInitialisation():
	handler = SessionHandler("testapp", 10, maxSessionsPerIp=4, sessionDeletionTimeout=23)
	assert "testapp" == handler.sessionName
	assert 10 == handler.sessionMaxInactiveInterval
	assert 4 == handler.maxSessionsPerIp
	assert 23 == handler.sessionDeletionTimeout

	assert not handler.sessions


def testHandlerCreatesAndExpiresSessions():
	handler = SessionHandler()
	assert not handler.sessions

	session = handler.createSession()
	assert 1 == len(handler.sessions)
	assert handler == session.sessionHandler

	session.expire()
	assert 0 == len(handler.sessions)


def testDeletingAllSessions():
	handler = SessionHandler()
	assert not handler.sessions

	for _ in range(10):
		handler.createSession()

	assert 10 == len(handler.sessions)

	handler.deleteAllSessions()
	assert 0 == len(handler.sessions)


def testSessionHandlerDeletingSessionInUse():
	handler = SessionHandler()
	assert not handler.sessions

	session = handler.createSession()
	assert 1 == len(handler.sessions)

	session.increaseUsageCount()
	session.increaseUsageCount()
	session.expire()

	assert 0 == len(handler.sessions)


def testDeletingNonExistingSessionMustNotFail():
	handler = SessionHandler()
	handler.deleteSession('iAmNotHere')


@pytest.mark.parametrize("sessionCount", [256])
def testCreatingAndExpiringManySessions(sessionCount):
	"Creating a lot of sessions and wait for them to expire."

	deletion_time_in_sec = 2

	handler = SessionHandler(
		"testapp",
		maxSessionsPerIp=4,
		sessionMaxInactiveInterval=deletion_time_in_sec,
		sessionDeletionTimeout=23
	)

	for _ in range(sessionCount):
		handler.createSession()

	for _ in range(deletion_time_in_sec + 1):
		time.sleep(1)

	assert {} == handler.getSessions()


def testGettingSession():
	handler = SessionHandler()
	session = handler.getSession()

	assert session.usageCount == 1


def testGettingSessionByUID():
	handler = SessionHandler()
	session = handler.getSession(uid='testUID12345')

	assert session.usageCount == 1


def testGettingSessionByUIDAndReuse():
	handler = SessionHandler()
	firstSession = handler.getSession(uid='testUID12345')

	assert firstSession.usageCount == 1

	secondSession = handler.getSession(uid=firstSession.uid)
	assert secondSession.usageCount == 2

	assert firstSession == secondSession


def testGettingNewSessionDoesNotSetUid():
	handler = SessionHandler()
	session = handler.getSession(uid='testUID12345')

	assert session.uid != 'testUID12345'


def testGettingNewSessionDoesIgnoreSessionMarkedForDeletion():
	handler = SessionHandler()
	session = handler.getSession()
	session.setMarkedForDeletion()

	secondSession = handler.getSession(uid=session.uid)
	assert secondSession != session
