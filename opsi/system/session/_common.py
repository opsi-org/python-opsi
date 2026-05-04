# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from opsi.system.info import is_windows


class DisplaySessionWindowsState(StrEnum):
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
	def _missing_(cls, value: object) -> DisplaySessionWindowsState:
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


class DisplaySessionWindowsProtocol(StrEnum):
	RDP = "rdp"
	ICA = "ica"
	CONSOLE = "console"

	@classmethod
	def _missing_(cls, value: object) -> DisplaySessionWindowsProtocol:
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


@dataclass
class DisplaySession:
	id: int
	desktop: str
	user: str
	windows_state: DisplaySessionWindowsState | None = None
	windows_protocol: str | None = None
