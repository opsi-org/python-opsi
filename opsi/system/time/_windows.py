# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from datetime import UTC, datetime

import win32api  # ty: ignore[import-not-found]
import win32con  # ty: ignore[import-not-found]
import win32security  # ty: ignore[import-not-found]


def _enable_system_time_privilege() -> None:
	"""Enable the SeSystemtimePrivilege for the current process."""
	token = win32security.OpenProcessToken(
		win32api.GetCurrentProcess(),
		win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY,
	)
	luid = win32security.LookupPrivilegeValue(None, win32security.SE_SYSTEMTIME_NAME)
	win32security.AdjustTokenPrivileges(token, False, [(luid, win32security.SE_PRIVILEGE_ENABLED)])


def set_system_datetime(new_datetime: datetime, *, update_hardware_clock: bool = False) -> None:
	"""
	Set the system date and time.

	Requires administrative privileges.

	Parameters
	----------
	new_datetime : datetime
		The new date and time. Timezone aware values are converted to UTC,
		naive values are interpreted as UTC.

	update_hardware_clock : bool, default: False
		Ignored on Windows, because the operating system writes the system time to the hardware clock itself.

	Raises
	------
	RuntimeError
		If the system time could not be set.
	"""
	if new_datetime.tzinfo is None:
		new_datetime = new_datetime.replace(tzinfo=UTC)
	new_datetime = new_datetime.astimezone(UTC)

	try:
		_enable_system_time_privilege()
		win32api.SetSystemTime(
			new_datetime.year,
			new_datetime.month,
			# Windows counts Sunday as 0
			new_datetime.isoweekday() % 7,
			new_datetime.day,
			new_datetime.hour,
			new_datetime.minute,
			new_datetime.second,
			new_datetime.microsecond // 1000,
		)
	except Exception as err:
		raise RuntimeError(f"Failed to set system time: {err}") from err
