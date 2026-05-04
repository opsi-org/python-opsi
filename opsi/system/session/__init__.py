# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows

from ._common import DisplaySession, DisplaySessionWindowsProtocol, DisplaySessionWindowsState

if is_linux():
	from ._linux import get_console_session, get_display_sessions
elif is_macos():
	from ._macos import get_console_session, get_display_sessions
elif is_windows():
	from ._windows import get_console_session, get_display_sessions
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")

__all__ = ["get_display_sessions", "get_console_session", "DisplaySession", "DisplaySessionWindowsState", "DisplaySessionWindowsProtocol"]
