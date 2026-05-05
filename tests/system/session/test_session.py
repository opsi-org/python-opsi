# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import pytest

from opsi.system.info import is_linux, is_windows
from opsi.system.session import (
	LinuxDisplaySessionClass,
	LinuxDisplaySessionType,
	WindowsDisplaySessionProtocol,
	WindowsDisplaySessionState,
	get_console_session,
	get_display_sessions,
)


@pytest.mark.parametrize("one_session_per_user", [True, False])
def test_get_display_sessions(one_session_per_user: bool) -> None:
	sessions = get_display_sessions(one_session_per_user=one_session_per_user)
	assert isinstance(sessions, list)
	if not sessions and is_linux():
		pytest.skip("No display sessions found, might be running in a headless Linux environment")

	assert sessions
	users = set()
	active_console_session_id = None
	for session in sessions:
		assert session.id

		if is_windows():
			assert isinstance(session.windows_state, WindowsDisplaySessionState)
			assert isinstance(session.windows_protocol, WindowsDisplaySessionProtocol)
			if session.is_current_console_session:
				if active_console_session_id is not None:
					raise AssertionError(f"Multiple active console sessions found: {active_console_session_id} and {session.id}")
				active_console_session_id = session.id
			if session.windows_protocol != WindowsDisplaySessionProtocol.CONSOLE:
				assert session.user
		if is_linux():
			assert isinstance(session.linux_session_type, LinuxDisplaySessionType)
			assert isinstance(session.linux_session_class, LinuxDisplaySessionClass)
			if session.linux_session_type == LinuxDisplaySessionType.X11:
				assert session.environment["DISPLAY"]
				assert session.environment["XAUTHORITY"]
			elif session.linux_session_type == LinuxDisplaySessionType.WAYLAND:
				assert session.environment["WAYLAND_DISPLAY"]
				assert session.environment["XDG_RUNTIME_DIR"]
			assert session.user

		if one_session_per_user:
			assert session.user not in users
		users.add(session.user)

	if is_windows():
		assert active_console_session_id is not None


def test_get_console_session() -> None:
	session = get_console_session()
	print(session)
	if not session and is_linux():
		pytest.skip("No console session found, might be running in a headless Linux environment")

	assert session
	assert session.id
	assert session.is_current_console_session
