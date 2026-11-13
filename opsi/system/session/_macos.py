# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import psutil

from ._common import DisplaySession


def get_display_sessions(
	*, one_session_per_user: bool = True, only_usable: bool = True, only_user_sessions: bool = False
) -> list[DisplaySession]:
	for proc in psutil.process_iter():
		try:
			if proc.name() == "loginwindow":
				user = proc.username()
				sessions = [
					DisplaySession(
						id="1",
						is_current_console_session=True,
						is_usable=True,
						is_user_session=user != "root",
						user=user,
						environment=proc.environ(),
					)
				]
				return [s for s in sessions if s.is_user_session or not only_user_sessions]
		except (psutil.AccessDenied, psutil.NoSuchProcess):
			pass
	if only_user_sessions:
		return []
	return [DisplaySession(id="1", is_current_console_session=True, is_usable=True, is_user_session=False, user="root")]
