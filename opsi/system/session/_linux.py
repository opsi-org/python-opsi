# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import psutil

from opsi.logging import get_logger

from ._common import DisplaySession

logger = get_logger("opsi")


def get_display_sessions(*, one_session_per_user: bool = True) -> list[DisplaySession]:
	sessions: list[DisplaySession] = []
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			session_class = env.get("XDG_SESSION_CLASS")
			if env.get("USER") and env.get("DISPLAY") and session_class:
				if env.get("DISPLAY") == ":1024":
					continue  # never try to use :1024 session as it seems to break gdm!
				if not any((session.id == int(env["DISPLAY"][1:]) for session in sessions)):
					sessions.append(DisplaySession(id=int(env["DISPLAY"][1:]), desktop=session_class, user=env["USER"]))
		except (psutil.AccessDenied, psutil.NoSuchProcess) as err:
			logger.debug(err)

	if one_session_per_user:
		relevant_sessions: list[DisplaySession] = []
		for user in {entry.user for entry in sessions}:
			relevant_sessions.append(min([user_session for user_session in sessions if user_session.user == user], key=lambda x: x.id))
		sessions = relevant_sessions

	return sessions
