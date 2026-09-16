# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import ctypes
import os
import pwd
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
	from collections.abc import Callable

from opsi.logging import get_logger

from ._common import DisplaySession, LinuxDisplaySessionClass, LinuxDisplaySessionType

logger = get_logger("opsi")


@dataclass(frozen=True)
class _LoginSession:
	uid: int
	session_type: str
	session_class: str
	display: str
	is_console: bool


class _Logind:
	"""Read trusted process/session metadata through the optional libsystemd API."""

	def __init__(self) -> None:
		self._lib = ctypes.CDLL("libsystemd.so.0")
		self._free = ctypes.CDLL(None).free
		self._free.argtypes = [ctypes.c_void_p]
		self._free.restype = None
		for name in ("type", "class", "seat", "display"):
			function = getattr(self._lib, f"sd_session_get_{name}")
			function.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p)]
			function.restype = ctypes.c_int
		self._lib.sd_pid_get_session.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
		self._lib.sd_pid_get_session.restype = ctypes.c_int
		self._lib.sd_pid_get_owner_uid.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
		self._lib.sd_pid_get_owner_uid.restype = ctypes.c_int
		self._lib.sd_uid_get_display.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_char_p)]
		self._lib.sd_uid_get_display.restype = ctypes.c_int
		self._lib.sd_session_get_uid.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint)]
		self._lib.sd_session_get_uid.restype = ctypes.c_int
		self._lib.sd_session_is_active.argtypes = [ctypes.c_char_p]
		self._lib.sd_session_is_active.restype = ctypes.c_int
		self._sessions: dict[str, _LoginSession | None] = {}
		self._user_display_sessions: dict[int, str] = {}

	def _string(self, function: Callable[..., int], argument: bytes | int) -> str:
		value = ctypes.c_char_p()
		try:
			if function(argument, ctypes.byref(value)) < 0 or not value.value:
				return ""
			return os.fsdecode(value.value)
		finally:
			if value:
				self._free(value)

	def session_for_pid(self, pid: int) -> _LoginSession | None:
		"""Resolve a process's session, falling back to its systemd owner's primary display session."""
		session_id = self._string(self._lib.sd_pid_get_session, pid)
		owner_uid: int | None = None
		if not session_id:
			# GNOME services run under user@UID.service, outside session-N.scope.
			# Use logind ownership, never USER/XDG_SESSION_ID or the calling SSH session.
			owner = ctypes.c_uint()
			if self._lib.sd_pid_get_owner_uid(pid, ctypes.byref(owner)) < 0:
				return None
			owner_uid = owner.value
			if owner_uid not in self._user_display_sessions:
				self._user_display_sessions[owner_uid] = self._string(self._lib.sd_uid_get_display, owner_uid)
			session_id = self._user_display_sessions[owner_uid]
			if not session_id:
				return None
		if session_id not in self._sessions:
			encoded_id = os.fsencode(session_id)
			uid = ctypes.c_uint()
			if self._lib.sd_session_get_uid(encoded_id, ctypes.byref(uid)) < 0:
				self._sessions[session_id] = None
			else:
				self._sessions[session_id] = _LoginSession(
					uid=uid.value,
					session_type=self._string(self._lib.sd_session_get_type, encoded_id),
					session_class=self._string(self._lib.sd_session_get_class, encoded_id),
					display=self._string(self._lib.sd_session_get_display, encoded_id),
					is_console=self._string(self._lib.sd_session_get_seat, encoded_id) == "seat0"
					and self._lib.sd_session_is_active(encoded_id) > 0,
				)
		session = self._sessions[session_id]
		if session and owner_uid is not None and session.uid != owner_uid:
			return None
		return session


def _x11_display(display: str) -> str:
	# Screens share an X server and must not create duplicate display sessions.
	return re.sub(r"(?<=\d)\.\d+$", "", display)


def _session_priority(session: DisplaySession) -> tuple[bool, bool, str, str]:
	return (not session.is_usable, not session.is_current_console_session, session.id, session.user or "")


def _one_session_per_user(sessions: list[DisplaySession]) -> list[DisplaySession]:
	relevant_sessions: list[DisplaySession] = []
	seen_users: set[str] = set()
	for session in sorted(sessions, key=_session_priority):
		if session.user and session.user in seen_users:
			continue
		relevant_sessions.append(session)
		if session.user:
			seen_users.add(session.user)
	return sorted(relevant_sessions, key=lambda session: session.id)


def _is_usable(session: DisplaySession, uid: int) -> bool:
	"""Check local prerequisites without connecting to or authenticating with a display."""
	env = session.environment
	try:
		if session.linux_session_type == LinuxDisplaySessionType.WAYLAND:
			socket_path = Path(session.id.removeprefix("wayland:"))
			socket_stat = socket_path.stat()
			if not stat.S_ISSOCK(socket_stat.st_mode) or socket_stat.st_uid != uid:
				return False
			# An absolute WAYLAND_DISPLAY need not be below a per-user runtime directory.
			if not Path(env["WAYLAND_DISPLAY"]).is_absolute():
				runtime_stat = Path(env["XDG_RUNTIME_DIR"]).stat()
				return stat.S_ISDIR(runtime_stat.st_mode) and runtime_stat.st_uid == uid
			return True

		display = session.id.removeprefix("x11:")
		if display in (":1024", "unix:1024", "unix/:1024"):
			# Retain the legacy GDM safety exclusion, but only for X11 endpoints.
			return False
		local_display = re.fullmatch(r"(?:unix/|unix)?:([0-9]+)", display)
		if local_display and not Path(f"/tmp/.X11-unix/X{local_display[1]}").is_socket():
			return False
		if xauthority := env.get("XAUTHORITY"):
			path = Path(xauthority)
			return path.is_absolute() and path.is_file() and bool(path.stat().st_mode & 0o444)
		# X11 can also use host/local-user access control without an authority file.
		return True
	except (OSError, ValueError):
		return False


def get_display_sessions(*, one_session_per_user: bool = True, only_usable: bool = True) -> list[DisplaySession]:
	"""
	Discover Linux display endpoints from accessible process environments.

	Parameters
	----------
	one_session_per_user : bool, default: True
		Keep the best session per user, preferring usable and current console sessions.
	only_usable : bool, default: True
		Exclude endpoints with missing local sockets or invalid explicit authority files.

	Returns
	-------
	list[DisplaySession]
		Sessions sorted by opaque, host-local endpoint IDs: ``x11:<display>`` or
		``wayland:<absolute socket path>``. X11 screen suffixes are omitted from IDs.
		Original display environment values are preserved. User identity comes from
		process credentials, checked against logind when available.

	Notes
	-----
	Console detection uses logind's active session on seat0. Processes outside a
	login session scope (e.g. GNOME user services) use their systemd owner's primary
	display session. Without that metadata no session is guessed to be the console.
	Usability is advisory: socket liveness, X11 authentication and remote display
	connectivity are not probed. Discovery cannot see processes whose environments
	are inaccessible and is not a security boundary for the contents of those
	environments. IDs may be reused after logout.
	"""
	try:
		logind: _Logind | None = _Logind()
	except (OSError, AttributeError) as err:
		logger.debug("logind session metadata unavailable: %s", err)
		logind = None

	sessions_by_id: dict[str, DisplaySession] = {}
	candidate_priorities: dict[str, tuple[bool, bool, bool, int]] = {}
	users: dict[int, pwd.struct_passwd] = {}
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			display = env.get("DISPLAY")
			wayland_display = env.get("WAYLAND_DISPLAY")
			if not display and not wayland_display:
				continue

			uid = proc.uids().effective
			login_session = logind.session_for_pid(proc.pid) if logind else None
			if login_session and login_session.uid != uid:
				# Do not attribute a sudo/su helper's environment to its login-session user.
				continue
			if uid not in users:
				users[uid] = pwd.getpwuid(uid)
			user = users[uid]
			env = dict(env)
			env["USER"] = env["LOGNAME"] = user.pw_name
			env["HOME"] = user.pw_dir

			try:
				linux_session_type = LinuxDisplaySessionType(env.get("XDG_SESSION_TYPE"))
			except ValueError:
				linux_session_type = LinuxDisplaySessionType.WAYLAND if wayland_display else LinuxDisplaySessionType.X11

			try:
				session_class = LinuxDisplaySessionClass(login_session.session_class if login_session else env.get("XDG_SESSION_CLASS"))
			except ValueError:
				session_class = LinuxDisplaySessionClass.USER

			if linux_session_type == LinuxDisplaySessionType.WAYLAND:
				if not wayland_display:
					continue
				socket_path = Path(wayland_display)
				if not socket_path.is_absolute():
					runtime_dir = env.get("XDG_RUNTIME_DIR", "")
					if not runtime_dir or not Path(runtime_dir).is_absolute():
						continue
					socket_path = Path(runtime_dir) / socket_path
				session_id = f"wayland:{os.path.normpath(socket_path)}"
			else:
				if not display:
					continue
				if not re.fullmatch(r"[^\s]*:[0-9]+(?:\.[0-9]+)?", display):
					continue
				session_id = f"x11:{_x11_display(display)}"
				if not env.get("XAUTHORITY"):
					authority = Path(user.pw_dir) / ".Xauthority"
					if authority.is_file():
						env["XAUTHORITY"] = str(authority)

			display_session = DisplaySession(
				id=session_id,
				user=user.pw_name,
				environment=env,
				linux_session_type=linux_session_type,
				linux_session_class=session_class,
			)
			display_session.is_usable = _is_usable(display_session, uid)
			display_session.is_current_console_session = bool(
				login_session
				and login_session.is_console
				and login_session.session_type == linux_session_type
				and (
					linux_session_type == LinuxDisplaySessionType.WAYLAND
					or (login_session.display and _x11_display(login_session.display) == _x11_display(display or ""))
				)
			)
			# A usable, session-associated environment beats stale/background candidates.
			priority = (
				not display_session.is_usable,
				not display_session.is_current_console_session,
				login_session is None,
				proc.pid,
			)
			if session_id not in candidate_priorities or priority < candidate_priorities[session_id]:
				sessions_by_id[session_id] = display_session
				candidate_priorities[session_id] = priority
		except (psutil.AccessDenied, psutil.NoSuchProcess, OSError, KeyError, ValueError) as err:
			logger.debug(err)

	sessions = sorted((s for s in sessions_by_id.values() if s.is_usable or not only_usable), key=lambda session: session.id)
	console_sessions = sorted((s for s in sessions if s.is_current_console_session), key=_session_priority)
	for session in console_sessions[1:]:
		session.is_current_console_session = False

	if one_session_per_user:
		sessions = _one_session_per_user(sessions)

	return sessions
