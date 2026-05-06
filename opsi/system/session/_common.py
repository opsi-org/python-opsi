# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from opsi.system.info import is_windows


class WindowsDisplaySessionState(StrEnum):
	"""Windows display session states.

	ACTIVE: A user is logged on to the WinStation.
		This state occurs when a user is signed in and actively connected to the device.
	CONNECTED: The WinStation is connected to the client.
	CONNECT_QUERY: The WinStation is in the process of connecting to the client.
	SHADOW: The WinStation is shadowing another WinStation.
	DISCONNECTED: The WinStation is active but the client is disconnected.
		This state occurs when a user is signed in but not actively connected to the device,
		such as when the user has chosen to exit to the lock screen.
	IDLE: The WinStation is waiting for a client to connect.
	LISTEN: The WinStation is listening for a connection.
		A listener session waits for requests for new client connections.
		No user is logged on a listener session.
		A listener session cannot be reset, shadowed, or changed to a regular client session.
	RESET: The WinStation is being reset.
	DOWN: The WinStation is down due to an error.
	INIT: The WinStation is initializing.
	"""

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

	USER: A regular interactive user session. This is the default class for sessions
		for which a TTY or X display is known at session registration time.
	USER_EARLY: Similar to USER but sessions of this class are not ordered after
		systemd-user-sessions.service(8), i.e. may be started before regular sessions
		are allowed to be established. (Added in v256.)
	USER_LIGHT: Similar to USER, but sessions of this class will not pull in the
		user@.service(5) of the user. (Added in v258.)
	USER_EARLY_LIGHT: Similar to USER_EARLY, but sessions of this class will not
		pull in the user@.service(5) of the user. (Added in v258.)
	USER_INCOMPLETE: Similar to USER but for sessions which are not fully set up yet.
		Used by systemd-homed.service(8) to allow users to log in via ssh(1) before
		their home directory is mounted.
	GREETER: Similar to USER but for sessions spawned by a display manager ephemerally
		which prompt the user for login credentials.
	LOCK_SCREEN: Similar to USER but for sessions spawned by a display manager
		ephemerally which show a lock screen.
	BACKGROUND: Used for background sessions, such as those invoked by cron(8).
		This is the default class for sessions with no TTY or X display.
	BACKGROUND_LIGHT: Similar to BACKGROUND, but sessions of this class will not
		pull in the user@.service(5) of the user. (Added in v256.)
	MANAGER: The user@.service(5) service of the user is registered under this
		session class. (Added in v256.)
	MANAGER_EARLY: Similar to MANAGER, but for the root user. (Added in v256.)
	NONE: Skips registering this session with systemd-logind. No session scope will
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
	"""
	Represents a display session on the system.

	Parameters:
	id: The session ID. On Windows, this is the session ID returned by WTSEnumerateSessions.
		On Linux, this is the value of the DISPLAY or WAYLAND_DISPLAY environment variable.
	is_current_console_session: Whether this session is the current console session.
	is_usable: Whether the session is usable for running applications.
	user: The user associated with the session, or None if no user is associated.
	domain: The domain of the user associated with the session, or None if no domain is associated or applicable.
	environment: The environment variables associated with the session.
	windows_state: The Windows display session state, or None if not applicable.
	windows_protocol: The Windows display session protocol, or None if not applicable.
	linux_session_type: The Linux display session type, or None if not applicable.
	linux_session_class: The Linux display session class, or None if not applicable.
	"""

	id: str
	is_current_console_session: bool = False
	is_usable: bool = True
	user: str | None = None
	domain: str | None = None
	environment: dict[str, str] = field(default_factory=dict)
	windows_state: WindowsDisplaySessionState | None = None
	windows_protocol: WindowsDisplaySessionProtocol | None = None
	linux_session_type: LinuxDisplaySessionType | None = None
	linux_session_class: LinuxDisplaySessionClass | None = None
