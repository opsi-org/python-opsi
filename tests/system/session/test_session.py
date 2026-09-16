# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import os
import socket
import stat
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import psutil
import pytest

if TYPE_CHECKING:
	from collections.abc import Callable, Iterator
	from typing import Any

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
			id="x11::0",
			user="user1",
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="wayland:/run/user/1000/wayland-0",
			user="user1",
			linux_session_type=LinuxDisplaySessionType.WAYLAND,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="x11::1",
			user="user2",
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="wayland:/run/user/1001/wayland-0",
			user="user2",
			linux_session_type=LinuxDisplaySessionType.WAYLAND,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="x11::4",
			user=None,
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
		DisplaySession(
			id="x11::5",
			user=None,
			linux_session_type=LinuxDisplaySessionType.X11,
			linux_session_class=LinuxDisplaySessionClass.USER,
		),
	]
	sessions = sorted(_one_session_per_user(sessions), key=lambda x: x.id)
	assert len(sessions) == 4
	assert sessions[0].id == "wayland:/run/user/1000/wayland-0"
	assert sessions[1].id == "wayland:/run/user/1001/wayland-0"
	assert sessions[2].id == "x11::4"
	assert sessions[3].id == "x11::5"


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
				assert session.id.startswith("x11:")
				assert session.environment["DISPLAY"]
			elif session.linux_session_type == LinuxDisplaySessionType.WAYLAND:
				assert session.id.startswith("wayland:/")
				assert session.environment["WAYLAND_DISPLAY"]
				if not Path(session.environment["WAYLAND_DISPLAY"]).is_absolute():
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
		assert int(session.id) >= 1


@pytest.fixture
def linux_display_processes(tmp_path: Path) -> Iterator[Callable[..., Mock]]:
	"""Supply isolated process environments and account records without inspecting the host."""
	if not is_linux():
		pytest.skip("Linux session discovery")
	processes: list[Mock] = []

	def add_process(env: dict[str, str], uid: int = 1000, pid: int | None = None) -> Mock:
		"""Add a process with independently controlled environment and effective credentials."""
		process = Mock(pid=pid if pid is not None else len(processes) + 1)
		process.environ.return_value = env.copy()
		process.uids.return_value = SimpleNamespace(effective=uid)
		processes.append(process)
		return process

	def get_account(uid: int) -> SimpleNamespace:
		"""Return a predictable account with a temporary home directory."""
		return SimpleNamespace(pw_name=f"user{uid}", pw_dir=str(tmp_path / f"user{uid}"))

	with (
		patch("opsi.system.session._linux.psutil.process_iter", side_effect=lambda: iter(processes)),
		patch("opsi.system.session._linux.pwd.getpwuid", side_effect=get_account),
		patch("opsi.system.session._linux._Logind", side_effect=OSError("not installed")),
	):
		yield add_process


@pytest.mark.linux
@pytest.mark.parametrize(
	"env",
	[
		{"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"},
		{"XDG_SESSION_TYPE": "x11", "WAYLAND_DISPLAY": "wayland-0"},
		{"WAYLAND_DISPLAY": "wayland-0"},
		{"WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": "relative"},
		{},
	],
)
def test_linux_discovery_skips_incomplete_environments(linux_display_processes: Callable[..., Mock], env: dict[str, str]) -> None:
	"""An invalid environment does not abort discovery of subsequent valid processes."""
	linux_display_processes(env)
	linux_display_processes({"DISPLAY": "remote:0"})
	assert [s.id for s in get_display_sessions()] == ["x11:remote:0"]


@pytest.mark.linux
def test_linux_wayland_ids_are_scoped_and_absolute(linux_display_processes: Callable[..., Mock]) -> None:
	"""Relative and absolute names for one socket deduplicate, but users' sockets do not."""
	for uid in (1000, 1001):
		linux_display_processes({"WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": f"/run/user/{uid}"}, uid=uid)
	linux_display_processes({"WAYLAND_DISPLAY": "/run/user/1000/wayland-0"})
	with patch("opsi.system.session._linux._is_usable", return_value=True):
		sessions = get_display_sessions(one_session_per_user=False)
	assert [s.id for s in sessions] == ["wayland:/run/user/1000/wayland-0", "wayland:/run/user/1001/wayland-0"]
	assert [s.user for s in sessions] == ["user1000", "user1001"]
	assert sessions[0].environment["WAYLAND_DISPLAY"] == "wayland-0"
	assert not any(s.is_current_console_session for s in sessions)


@pytest.mark.linux
def test_linux_x11_screen_normalization_preserves_environment(linux_display_processes: Callable[..., Mock]) -> None:
	"""An X server has one endpoint ID even when processes reference different screens."""
	for display in ("remote:0.0", "remote:0", "remote:0.1"):
		linux_display_processes({"DISPLAY": display})
	sessions = get_display_sessions(one_session_per_user=False)
	assert len(sessions) == 1
	assert sessions[0].id == "x11:remote:0"
	assert sessions[0].environment["DISPLAY"] == "remote:0.0"


@pytest.mark.linux
@pytest.mark.parametrize("claimed_user", [None, "root", "someone_else"])
def test_linux_identity_uses_credentials(linux_display_processes: Callable[..., Mock], tmp_path: Path, claimed_user: str | None) -> None:
	"""Environment-supplied account data must not control the launch identity."""
	env = {"DISPLAY": "remote:0", "HOME": "/root", "LOGNAME": "root"}
	if claimed_user is not None:
		env["USER"] = claimed_user
	process = linux_display_processes(env)
	session = get_display_sessions()[0]
	assert session.user == session.environment["USER"] == session.environment["LOGNAME"] == "user1000"
	assert session.environment["HOME"] == str(tmp_path / "user1000")
	assert process.environ.return_value == env


@pytest.mark.linux
def test_linux_x11_uses_default_authority(linux_display_processes: Callable[..., Mock], tmp_path: Path) -> None:
	"""Missing XAUTHORITY uses the verified account's default file when present."""
	authority = tmp_path / "user1000" / ".Xauthority"
	authority.parent.mkdir()
	authority.write_bytes(b"test authority")
	linux_display_processes({"DISPLAY": "remote:0"})
	session = get_display_sessions()[0]
	assert session.environment["XAUTHORITY"] == str(authority)
	assert session.is_usable


@pytest.mark.linux
def test_linux_usable_candidate_replaces_stale_environment(linux_display_processes: Callable[..., Mock], tmp_path: Path) -> None:
	"""A lower PID must not make a stale authority file win over a usable environment."""
	linux_display_processes({"DISPLAY": "remote:0", "XAUTHORITY": str(tmp_path / "missing")})
	linux_display_processes({"DISPLAY": "remote:0", "LANG": "de_DE.UTF-8"})
	sessions = get_display_sessions(one_session_per_user=False)
	assert len(sessions) == 1
	assert sessions[0].environment["LANG"] == "de_DE.UTF-8"


@pytest.mark.linux
@pytest.mark.parametrize("only_usable", [False, True])
def test_linux_only_usable_filters_missing_endpoints(
	linux_display_processes: Callable[..., Mock], tmp_path: Path, only_usable: bool
) -> None:
	"""Unusable but identifiable endpoints remain visible when explicitly requested."""
	linux_display_processes({"WAYLAND_DISPLAY": str(tmp_path / "missing-socket")})
	linux_display_processes({"DISPLAY": "remote:0", "XAUTHORITY": str(tmp_path / "missing-authority")})
	sessions = get_display_sessions(one_session_per_user=False, only_usable=only_usable)
	assert len(sessions) == (0 if only_usable else 2)
	assert not any(s.is_usable for s in sessions)


@pytest.mark.linux
@pytest.mark.parametrize("owner, mode, expected", [(1000, stat.S_IFSOCK, True), (1001, stat.S_IFSOCK, False), (1000, stat.S_IFREG, False)])
def test_linux_wayland_requires_owned_socket(linux_display_processes: Callable[..., Mock], owner: int, mode: int, expected: bool) -> None:
	"""Wayland candidates must reference a socket owned by the process user."""
	linux_display_processes({"WAYLAND_DISPLAY": "/run/user/1000/wayland-0"})
	with patch("opsi.system.session._linux.Path.stat", return_value=SimpleNamespace(st_uid=owner, st_mode=mode)):
		sessions = get_display_sessions(only_usable=False)
	assert sessions[0].is_usable is expected


@pytest.mark.linux
def test_linux_x11_missing_socket_is_unusable(linux_display_processes: Callable[..., Mock]) -> None:
	"""A local X11 endpoint needs its Unix socket even without an authority file."""
	linux_display_processes({"DISPLAY": ":7"})
	with patch("opsi.system.session._linux.Path.is_socket", return_value=False):
		assert not get_display_sessions()
		assert not get_display_sessions(only_usable=False)[0].is_usable


@pytest.mark.linux
def test_linux_gdm_exclusion_does_not_hide_wayland(linux_display_processes: Callable[..., Mock]) -> None:
	"""The legacy safety rule is restricted to the X11 endpoint, not its Wayland session."""
	linux_display_processes({"DISPLAY": ":1024"})
	linux_display_processes({"DISPLAY": ":1024", "WAYLAND_DISPLAY": "/run/user/1000/wayland-0"})
	with patch("opsi.system.session._linux.Path.stat", return_value=SimpleNamespace(st_uid=1000, st_mode=stat.S_IFSOCK)):
		sessions = get_display_sessions(one_session_per_user=False, only_usable=False)
	assert len(sessions) == 2
	assert sessions[0].id.startswith("wayland:") and sessions[0].is_usable
	assert sessions[1].id == "x11::1024" and not sessions[1].is_usable


@pytest.mark.linux
def test_linux_logind_selects_active_console_and_checks_uid(linux_display_processes: Callable[..., Mock]) -> None:
	"""Trusted logind metadata beats forged environment variables and lexical display order."""
	from opsi.system.session._linux import _LoginSession

	linux_display_processes({"DISPLAY": ":0", "XDG_SESSION_ID": "forged", "XDG_SEAT": "seat0"})
	linux_display_processes({"DISPLAY": ":10"})
	linux_display_processes({"DISPLAY": ":11"}, uid=0)
	metadata = [
		_LoginSession(1000, "x11", "user", ":0", False),
		_LoginSession(1000, "x11", "user", ":10", True),
		_LoginSession(1000, "x11", "user", ":11", True),
	]
	with (
		patch("opsi.system.session._linux._Logind") as logind,
		patch("opsi.system.session._linux._is_usable", return_value=True),
	):
		logind.return_value.session_for_pid.side_effect = lambda pid: metadata[pid - 1]
		sessions = get_display_sessions(one_session_per_user=False)
		preferred = get_display_sessions()
	assert [s.id for s in sessions] == ["x11::0", "x11::10"]
	assert [s.is_current_console_session for s in sessions] == [False, True]
	assert [s.id for s in preferred] == ["x11::10"]


@pytest.mark.linux
def test_linux_remote_display_in_active_session_is_not_console(linux_display_processes: Callable[..., Mock]) -> None:
	"""An SSH-forwarded or overridden DISPLAY is not the console's X server."""
	from opsi.system.session._linux import _LoginSession

	linux_display_processes({"DISPLAY": "localhost:10"})
	with patch("opsi.system.session._linux._Logind") as logind:
		logind.return_value.session_for_pid.return_value = _LoginSession(1000, "x11", "user", ":0", True)
		assert not get_display_sessions()[0].is_current_console_session


@pytest.mark.linux
@pytest.mark.parametrize("error", [psutil.AccessDenied(1), psutil.NoSuchProcess(1), psutil.ZombieProcess(1), OSError("gone")])
def test_linux_process_errors_do_not_abort_scan(linux_display_processes: Callable[..., Mock], error: Exception) -> None:
	"""Inaccessible and disappearing processes do not hide the remaining endpoints."""
	process = linux_display_processes({"DISPLAY": "remote:0"})
	process.environ.side_effect = error
	linux_display_processes({"DISPLAY": "remote:1"})
	assert [s.id for s in get_display_sessions()] == ["x11:remote:1"]


@pytest.mark.linux
def test_linux_one_per_user_is_deterministic_and_prefers_usable() -> None:
	"""Selection is stable across input ordering and does not prefer an unusable console."""
	from opsi.system.session._linux import _one_session_per_user

	sessions = [
		DisplaySession(id="x11::0", user="user", is_usable=False, is_current_console_session=True),
		DisplaySession(id="x11::1", user="user"),
		DisplaySession(id="x11::2", user=None),
		DisplaySession(id="x11::3", user=None),
	]
	assert _one_session_per_user(sessions) == _one_session_per_user(list(reversed(sessions))) == sessions[1:]


@pytest.mark.linux
@pytest.mark.parametrize("absolute", [True, False])
def test_linux_wayland_real_socket(linux_display_processes: Callable[..., Mock], tmp_path: Path, absolute: bool) -> None:
	"""Socket prerequisites work for both absolute names and runtime-relative names."""
	socket_path = tmp_path / "wayland-0"
	env = {"WAYLAND_DISPLAY": str(socket_path)} if absolute else {"WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": str(tmp_path)}
	linux_display_processes(env, uid=os.geteuid())
	with socket.socket(socket.AF_UNIX) as server:
		server.bind(str(socket_path))
		sessions = get_display_sessions()
	assert len(sessions) == 1
	assert sessions[0].id == f"wayland:{socket_path}"
	assert sessions[0].is_usable


@pytest.mark.linux
@pytest.mark.parametrize("user_manager", [False, True])
@pytest.mark.parametrize("session_type", ["x11", "wayland"])
@pytest.mark.parametrize("seat, active, expected", [(b"seat0", 1, True), (b"seat0", 0, False), (b"seat1", 1, False), (b"", 1, False)])
def test_linux_logind_reads_trusted_metadata_and_frees_strings(
	seat: bytes, active: int, expected: bool, user_manager: bool, session_type: str
) -> None:
	"""Native lookups recognize session-scope and GNOME user-manager processes alike."""
	from opsi.system.session._linux import _Logind

	process = Mock(pid=125)
	process.environ.return_value = {
		"DISPLAY": ":0",
		"WAYLAND_DISPLAY": "/run/user/1000/wayland-0",
		"XDG_SESSION_TYPE": session_type,
		"XDG_SESSION_ID": "forged",
		"XAUTHORITY": "/mock/authority",
	}
	process.uids.return_value = SimpleNamespace(effective=1000)
	library = Mock()
	libc = Mock()
	# Keep the backing bytes alive while the fake native API exposes their pointers.
	values = {
		"sd_pid_get_session": b"c1",
		"sd_uid_get_display": b"c1",
		"sd_session_get_type": session_type.encode(),
		"sd_session_get_class": b"user",
		"sd_session_get_display": b":0",
		"sd_session_get_seat": seat,
	}

	def set_string(value: bytes, _argument: object, output: Any) -> int:
		"""Emulate a libsystemd out-parameter without allocating native memory."""
		ctypes.cast(output, ctypes.POINTER(ctypes.c_char_p))[0] = value
		return 0

	def set_uid(_argument: object, output: Any) -> int:
		"""Emulate the uid_t out-parameter."""
		ctypes.cast(output, ctypes.POINTER(ctypes.c_uint))[0] = 1000
		return 0

	for name, value in values.items():
		getattr(library, name).side_effect = partial(set_string, value)
	if user_manager:
		library.sd_pid_get_session.side_effect = None
		library.sd_pid_get_session.return_value = -61
	library.sd_pid_get_owner_uid.side_effect = set_uid
	library.sd_session_get_uid.side_effect = set_uid
	library.sd_session_is_active.return_value = active
	with patch("opsi.system.session._linux.ctypes.CDLL", side_effect=[library, libc]):
		logind = _Logind()
		session = logind.session_for_pid(123)
		assert session is not None
		assert (session.uid, session.session_type, session.session_class, session.display) == (1000, session_type, "user", ":0")
		assert session.is_console is expected
		assert logind.session_for_pid(124) is session
		with (
			patch("opsi.system.session._linux._Logind", return_value=logind),
			patch("opsi.system.session._linux._is_usable", return_value=True),
			patch("opsi.system.session._linux.psutil.process_iter", return_value=[process]),
			patch("opsi.system.session._linux.pwd.getpwuid", return_value=SimpleNamespace(pw_name="user", pw_dir="/home/user")),
		):
			displays = get_display_sessions()
		assert len(displays) == 1
		assert displays[0].is_current_console_session is expected
	library.sd_session_get_uid.assert_called_once()
	if user_manager:
		library.sd_uid_get_display.assert_called_once()
		assert library.sd_uid_get_display.call_args.args[0] == 1000
		assert libc.free.call_count == 5
	else:
		library.sd_pid_get_owner_uid.assert_not_called()
		library.sd_uid_get_display.assert_not_called()
		assert libc.free.call_count == 7


@pytest.mark.linux
def test_linux_logind_missing_session_does_not_free_null() -> None:
	"""A process outside logind has no allocated session string to release."""
	from opsi.system.session._linux import _Logind

	library = Mock()
	library.sd_pid_get_session.return_value = -61
	library.sd_pid_get_owner_uid.return_value = -61
	libc = Mock()
	with patch("opsi.system.session._linux.ctypes.CDLL", side_effect=[library, libc]):
		assert _Logind().session_for_pid(123) is None
	libc.free.assert_not_called()
	library.sd_uid_get_display.assert_not_called()


@pytest.mark.linux
@pytest.mark.parametrize("display_found, session_uid", [(False, 1000), (True, 1001)])
def test_linux_logind_user_manager_rejects_missing_or_mismatched_session(display_found: bool, session_uid: int) -> None:
	"""Fallbacks must not invent a session or associate another user's login session."""
	from opsi.system.session._linux import _Logind, _LoginSession

	library = Mock()
	library.sd_pid_get_session.return_value = -61
	library.sd_uid_get_display.return_value = -61
	libc = Mock()

	def set_owner(_pid: int, output: Any) -> int:
		"""Provide trusted systemd user-manager ownership."""
		ctypes.cast(output, ctypes.POINTER(ctypes.c_uint))[0] = 1000
		return 0

	def set_display(_uid: int, output: Any) -> int:
		"""Return a primary session whose metadata will fail the owner check."""
		ctypes.cast(output, ctypes.POINTER(ctypes.c_char_p))[0] = b"c1"
		return 0

	library.sd_pid_get_owner_uid.side_effect = set_owner
	if display_found:
		library.sd_uid_get_display.side_effect = set_display
	with patch("opsi.system.session._linux.ctypes.CDLL", side_effect=[library, libc]):
		logind = _Logind()
		logind._sessions["c1"] = _LoginSession(session_uid, "wayland", "user", "", True)
		assert logind.session_for_pid(123) is None
		assert logind.session_for_pid(124) is None
	library.sd_uid_get_display.assert_called_once()


@pytest.mark.linux
def test_linux_logind_preserves_direct_ssh_session() -> None:
	"""A direct SSH session must not be replaced by the user's primary desktop session."""
	from opsi.system.session._linux import _Logind, _LoginSession

	library = Mock()
	libc = Mock()

	def set_session(_pid: int, output: Any) -> int:
		"""Return the existing SSH session from the PID lookup."""
		ctypes.cast(output, ctypes.POINTER(ctypes.c_char_p))[0] = b"ssh-session"
		return 0

	library.sd_pid_get_session.side_effect = set_session
	with patch("opsi.system.session._linux.ctypes.CDLL", side_effect=[library, libc]):
		logind = _Logind()
		ssh_session = _LoginSession(1000, "tty", "user", "", False)
		logind._sessions["ssh-session"] = ssh_session
		assert logind.session_for_pid(123) is ssh_session
	library.sd_pid_get_owner_uid.assert_not_called()
	library.sd_uid_get_display.assert_not_called()
