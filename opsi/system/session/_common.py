# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from opsi.system.info import is_windows


class WindowsDisplaySessionState(StrEnum):
	ACTIVE = "active"
	CONNECTED = "connected"
	CONNECT_QUERY = "connect_query"
	SHADOW = "shadow"
	DISCONNECTED = "disconnected"
	IDLE = "idle"
	LISTEN = "listen"
	RESET = "reset"
	DOWN = "down"
	INIT = "init"

	@classmethod
	def _missing_(cls, value: object) -> WindowsDisplaySessionState:
		if isinstance(value, str):
			value = value.lower()
			for member in cls:
				if member.value == value:
					return member

		if isinstance(value, int) and is_windows():
			import win32ts  # ty: ignore[unresolved-import]

			int_to_state = {
				win32ts.WTSActive: cls.ACTIVE,
				win32ts.WTSConnected: cls.CONNECTED,
				win32ts.WTSConnectQuery: cls.CONNECT_QUERY,
				win32ts.WTSShadow: cls.SHADOW,
				win32ts.WTSDisconnected: cls.DISCONNECTED,
				win32ts.WTSIdle: cls.IDLE,
				win32ts.WTSListen: cls.LISTEN,
				win32ts.WTSReset: cls.RESET,
				win32ts.WTSDown: cls.DOWN,
				win32ts.WTSInit: cls.INIT,
			}
			if value in int_to_state:
				return int_to_state[value]

		raise ValueError(f"{value!r} is not a valid {cls.__name__}")


class WindowsDisplaySessionProtocol(StrEnum):
	RDP = "rdp"
	ICA = "ica"
	CONSOLE = "console"

	@classmethod
	def _missing_(cls, value: object) -> WindowsDisplaySessionProtocol:
		if isinstance(value, str):
			value = value.lower()
			for member in cls:
				if member.value == value:
					return member

		if isinstance(value, int) and is_windows():
			import win32ts  # ty: ignore[unresolved-import]

			int_to_protocol = {
				win32ts.WTS_PROTOCOL_TYPE_RDP: cls.RDP,
				win32ts.WTS_PROTOCOL_TYPE_ICA: cls.ICA,
				win32ts.WTS_PROTOCOL_TYPE_CONSOLE: cls.CONSOLE,
			}
			if value in int_to_protocol:
				return int_to_protocol[value]

		raise ValueError(f"{value!r} is not a valid {cls.__name__}")


class LinuxDisplaySessionType(StrEnum):
	X11 = "x11"
	WAYLAND = "wayland"


class LinuxDisplaySessionClass(StrEnum):
	"""Display session Linux class types.

	user: A regular interactive user session. This is the default class for sessions
		for which a TTY or X display is known at session registration time.
	user-early: Similar to user but sessions of this class are not ordered after
		systemd-user-sessions.service(8), i.e. may be started before regular sessions
		are allowed to be established. (Added in v256.)
	user-light: Similar to user, but sessions of this class will not pull in the
		user@.service(5) of the user. (Added in v258.)
	user-early-light: Similar to user-early, but sessions of this class will not
		pull in the user@.service(5) of the user. (Added in v258.)
	user-incomplete: Similar to user but for sessions which are not fully set up yet.
		Used by systemd-homed.service(8) to allow users to log in via ssh(1) before
		their home directory is mounted.
	greeter: Similar to user but for sessions spawned by a display manager ephemerally
		which prompt the user for login credentials.
	lock-screen: Similar to user but for sessions spawned by a display manager
		ephemerally which show a lock screen.
	background: Used for background sessions, such as those invoked by cron(8).
		This is the default class for sessions with no TTY or X display.
	background-light: Similar to background, but sessions of this class will not
		pull in the user@.service(5) of the user. (Added in v256.)
	manager: The user@.service(5) service of the user is registered under this
		session class. (Added in v256.)
	manager-early: Similar to manager, but for the root user. (Added in v256.)
	none: Skips registering this session with systemd-logind. No session scope will
		be created. (Added in v258.)
	"""

	USER = "user"
	USER_EARLY = "user-early"
	USER_LIGHT = "user-light"
	USER_EARLY_LIGHT = "user-early-light"
	USER_INCOMPLETE = "user-incomplete"
	GREETER = "greeter"
	LOCK_SCREEN = "lock-screen"
	BACKGROUND = "background"
	BACKGROUND_LIGHT = "background-light"
	MANAGER = "manager"
	MANAGER_EARLY = "manager-early"
	NONE = "none"


@dataclass(kw_only=True)
class DisplaySession:
	id: str
	console: bool = False
	user: str | None = None
	windows_state: WindowsDisplaySessionState | None = None
	windows_protocol: WindowsDisplaySessionProtocol | None = None
	linux_session_type: LinuxDisplaySessionType | None = None
	linux_session_class: LinuxDisplaySessionClass | None = None
	linux_display: str | None = None
	linux_wayland_display: str | None = None
	linux_xauthority: Path | None = None
	linux_xdg_runtime_dir: Path | None = None
