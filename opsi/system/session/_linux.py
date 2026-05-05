# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only
from pathlib import Path

import psutil

from opsi.logging import get_logger

from ._common import DisplaySession, LinuxDisplaySessionClass, LinuxDisplaySessionType

logger = get_logger("opsi")


def get_display_sessions(*, one_session_per_user: bool = True) -> list[DisplaySession]:
	sessions_by_id: dict[str, DisplaySession] = {}
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			user = env.get("USER")
			if not user:
				continue

			display = env.get("DISPLAY")
			wayland_display = env.get("WAYLAND_DISPLAY")
			if not display and not wayland_display:
				continue

			if display == ":1024":
				# Never try to use :1024 session as it seems to break gdm!
				# TODO: Check if this is still the case
				logger.trace("Process %d has DISPLAY=:1024, skipping", proc.pid)
				continue

			try:
				linux_session_type = LinuxDisplaySessionType(env.get("XDG_SESSION_TYPE"))
			except ValueError:
				logger.trace("Process %d has unknown session type %r, skipping", proc.pid, env.get("XDG_SESSION_TYPE"))
				continue

			session_id = wayland_display if linux_session_type == LinuxDisplaySessionType.WAYLAND else display
			assert session_id

			if session_id in sessions_by_id:
				continue

			try:
				session_class = LinuxDisplaySessionClass(env.get("XDG_SESSION_CLASS"))
			except ValueError:
				logger.trace("Process %d has unknown session class %r, skipping", proc.pid, env.get("XDG_SESSION_CLASS"))
				continue

			xauthority = env.get("XAUTHORITY") or None
			xdg_runtime_dir = env.get("XDG_RUNTIME_DIR") or None
			if linux_session_type == LinuxDisplaySessionType.WAYLAND:
				if not wayland_display:
					logger.trace("Process %d has session type Wayland but no WAYLAND_DISPLAY, skipping", proc.pid)
					continue
				if not xdg_runtime_dir:
					logger.trace("Process %d has session type Wayland but no XDG_RUNTIME_DIR, skipping", proc.pid)
					continue

			elif linux_session_type == LinuxDisplaySessionType.X11:
				if not display:
					logger.trace("Process %d has session type X11 but no DISPLAY, skipping", proc.pid)
					continue
				if not xauthority:
					logger.trace("Process %d has session type X11 but no XAUTHORITY, skipping", proc.pid)
					continue

			display_session = DisplaySession(
				id=session_id,
				desktop=session_class.value.lower(),
				user=user,
				linux_session_type=linux_session_type,
				linux_session_class=session_class,
				linux_display=display,
				linux_wayland_display=wayland_display,
				linux_xauthority=Path(xauthority) if xauthority else None,
				linux_xdg_runtime_dir=Path(xdg_runtime_dir) if xdg_runtime_dir else None,
			)
			sessions_by_id[session_id] = display_session
		except (psutil.AccessDenied, psutil.NoSuchProcess) as err:
			logger.debug(err)

	sessions = list(sessions_by_id.values())
	if one_session_per_user:
		relevant_sessions: list[DisplaySession] = []
		for user in {entry.user for entry in sessions}:
			relevant_sessions.append(min([user_session for user_session in sessions if user_session.user == user], key=lambda x: x.id))
		sessions = relevant_sessions

	return sessions


def get_console_session() -> DisplaySession | None:
	sessions = get_display_sessions(one_session_per_user=False)
	if not sessions:
		return None
	return min(sessions, key=lambda x: x.id)
