# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import sys

from opsi.exception import OperatingSystemUnsupportedError

if sys.platform != "win32":
	raise OperatingSystemUnsupportedError("This module is only supported on Windows")

import win32ts

from opsi.logging import get_logger

from ._common import DisplaySession, WindowsDisplaySessionProtocol, WindowsDisplaySessionState

logger = get_logger("opsi")


def _one_session_per_user(sessions: list[DisplaySession]) -> list[DisplaySession]:
	# Prefer active sessions over inactive ones, and if there are multiple active sessions for a user, prefer the one with the lowest session ID.
	relevant_sessions: list[DisplaySession] = []
	for user in {entry.user for entry in sessions}:
		user_sessions = [s for s in sessions if s.user == user]
		if user:
			relevant_sessions.append(
				min(user_sessions, key=lambda s: (0 if s.windows_state == WindowsDisplaySessionState.ACTIVE else 1, int(s.id)))
			)
		else:
			relevant_sessions.extend(user_sessions)

	return relevant_sessions


def get_display_sessions(*, one_session_per_user: bool = True, only_usable: bool = True) -> list[DisplaySession]:
	server = win32ts.WTS_CURRENT_SERVER_HANDLE
	sessions: list[DisplaySession] = []
	for session in win32ts.WTSEnumerateSessions(server):
		session_id = session["SessionId"]

		try:
			windows_state = WindowsDisplaySessionState(session.get("State"))
		except ValueError:
			logger.warning("Invalid session state %r for session %r", session.get("State"), session_id)
			continue

		try:
			windows_protocol = WindowsDisplaySessionProtocol(
				win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSClientProtocolType)
			)
		except ValueError:
			logger.warning("Invalid session protocol %r for session %r", windows_protocol, session_id)
			continue

		# Session ID 0 is the "services" session
		is_usable = session_id > 0 and windows_state in (
			WindowsDisplaySessionState.ACTIVE,
			WindowsDisplaySessionState.CONNECTED,
			WindowsDisplaySessionState.DISCONNECTED,
		)
		if only_usable and not is_usable:
			continue

		session_user = win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSUserName) or None
		# TODO: Get environment if needed
		sessions.append(
			DisplaySession(
				id=str(session_id),
				is_usable=is_usable,
				user=session_user,
				windows_state=windows_state,
				windows_protocol=windows_protocol,
			)
		)

	console_sessions = [s for s in sessions if s.windows_protocol == WindowsDisplaySessionProtocol.CONSOLE and s.is_usable]
	if console_sessions:
		min(
			console_sessions, key=lambda x: (0 if x.windows_state == WindowsDisplaySessionState.ACTIVE else 1, int(x.id))
		).is_current_console_session = True

	if one_session_per_user:
		sessions = _one_session_per_user(sessions)

	return sessions
