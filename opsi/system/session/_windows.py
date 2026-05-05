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

from ._common import DisplaySession, DisplaySessionWindowsState

logger = get_logger("opsi")


def get_display_sessions(*, one_session_per_user: bool = True) -> list[DisplaySession]:
	server = win32ts.WTS_CURRENT_SERVER_HANDLE
	sessions: list[DisplaySession] = []
	for session in win32ts.WTSEnumerateSessions(server):
		session_id = int(session["SessionId"])

		windows_state = None
		try:
			windows_state = DisplaySessionWindowsState(session.get("State"))
		except ValueError:
			logger.warning("Unknown session state %r for session %d", session.get("State"), session_id)
			continue

		windows_protocol = None
		try:
			windows_protocol = win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSClientProtocolType)
		except ValueError:
			logger.warning("Unknown session protocol %r for session %d", windows_protocol, session_id)
			continue

		session_user = win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSUserName)
		if not session_user:
			logger.debug("Session %d has no user, skipping", session_id)
			continue

		sessions.append(
			DisplaySession(
				id=session_id,
				desktop=str(win32ts.WTSQuerySessionInformation(server, session_id, win32ts.WTSWorkingDirectory)).lower() or "default",
				user=session_user or "",
				windows_state=windows_state,
				windows_protocol=windows_protocol,
			)
		)

	if one_session_per_user:
		# Prefer active sessions over inactive ones, and if there are multiple active sessions for a user, prefer the one with the lowest session ID.
		relevant_sessions: list[DisplaySession] = []
		for user in {entry.user for entry in sessions}:
			relevant_sessions.append(
				min(
					[user_session for user_session in sessions if user_session.user == user],
					key=lambda x: (0 if x.windows_state == DisplaySessionWindowsState.ACTIVE else 1, x.id),
				)
			)
		sessions = relevant_sessions

	return sessions


def get_console_session() -> DisplaySession | None:
	session_id = int(win32ts.WTSGetActiveConsoleSessionId())
	for session in get_display_sessions(one_session_per_user=False):
		if session.id == session_id:
			return session
	return None
