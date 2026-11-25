# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import os
from datetime import UTC, datetime

from opsi.process import run_command


def set_system_datetime(new_datetime: datetime, *, update_hardware_clock: bool = False) -> None:
	"""
	Set the system date and time.

	Requires root privileges.

	Parameters
	----------
	new_datetime : datetime
		The new date and time. Timezone aware values are converted to UTC,
		naive values are interpreted as UTC.
		The time is set with a resolution of one second.

	update_hardware_clock : bool, default: False
		Ignored on macOS, because the hardware clock is managed by the operating system.

	Raises
	------
	RuntimeError
		If the system time could not be set.
	"""
	if new_datetime.tzinfo is None:
		new_datetime = new_datetime.replace(tzinfo=UTC)
	new_datetime = new_datetime.astimezone(UTC)

	try:
		# macOS date format: [[[mm]dd]HH]MM[[cc]yy][.ss]
		run_command(["date", "-u", new_datetime.strftime("%m%d%H%M%Y.%S")], timeout=10.0)
	except Exception as err:
		raise RuntimeError(f"Failed to set system time as uid {os.geteuid()}: {err}") from err
