# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import pytest

from opsi.system.info import is_linux, is_windows
from opsi.system.session import (
	DisplaySession,
	LinuxDisplaySessionClass,
	LinuxDisplaySessionType,
	WindowsDisplaySessionProtocol,
	WindowsDisplaySessionState,
	get_console_session,
	get_display_sessions,
)


@pytest.mark.windows
def test_one_session_per_user_windows() -> None:
	from opsi.system.session._windows import _one_session_per_user

	sessions = [
		DisplaySession(
			id="1", user="user1", windows_state=WindowsDisplaySessionState.ACTIVE, windows_protocol=WindowsDisplaySessionProtocol.RDP
		),
		DisplaySession(
			id="2", user="user1", windows_state=WindowsDisplaySessionState.DISCONNECTED, windows_protocol=WindowsDisplaySessionProtocol.RDP
		),
		DisplaySession(
			id="3", user="user2", windows_state=WindowsDisplaySessionState.ACTIVE, windows_protocol=WindowsDisplaySessionProtocol.CONSOLE
		),
		DisplaySession(
			id="4", user="user2", windows_state=WindowsDisplaySessionState.ACTIVE, windows_protocol=WindowsDisplaySessionProtocol.RDP
		),
		DisplaySession(
			id="5", user=None, windows_state=WindowsDisplaySessionState.DISCONNECTED, windows_protocol=WindowsDisplaySessionProtocol.CONSOLE
		),
		DisplaySession(
			id="6", user=None, windows_state=WindowsDisplaySessionState.DISCONNECTED, windows_protocol=WindowsDisplaySessionProtocol.CONSOLE
		),
	]

	sessions = sorted(_one_session_per_user(sessions), key=lambda x: x.id)
	assert len(sessions) == 4
	assert sessions[0].id == "1"
	assert sessions[1].id == "3"
	assert sessions[2].id == "5"
	assert sessions[3].id == "6"


@pytest.mark.linux
def test_one_session_per_user_linux() -> None:
	from opsi.system.session._linux import _one_session_per_user

	sessions = [
		DisplaySession(
			id=":0",
			user="user1",
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="wayland-0",
			user="user1",
			linux_session_type=LinuxDisplaySessionType.WAYLAND,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id=":1",
			user="user2",
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="wayland-1",
			user="user2",
			linux_session_type=LinuxDisplaySessionType.WAYLAND,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id=":4",
			user=None,
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id=":5",
			user=None,
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
	]
	sessions = sorted(_one_session_per_user(sessions), key=lambda x: x.id)
	assert len(sessions) == 4
	assert sessions[0].id == ":0"
	assert sessions[1].id == ":1"
	assert sessions[2].id == ":4"
	assert sessions[3].id == ":5"


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
	assert session.is_usable

	if is_windows():
		assert int(session.id) > 1
