# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

from opsi.process import run_command


def set_system_datetime(new_datetime: datetime, *, update_hardware_clock: bool = False) -> None:
	"""
	Set the system date and time.

	Requires root privileges (CAP_SYS_TIME).

	Parameters
	----------
	new_datetime : datetime
		The new date and time. Timezone aware values are converted to UTC,
		naive values are interpreted as UTC.

	update_hardware_clock : bool, default: False
		If True, also write the new system time to the hardware clock (RTC) using `hwclock --systohc`.

	Raises
	------
	RuntimeError
		If the system time or the hardware clock could not be set.
	"""
	if new_datetime.tzinfo is None:
		new_datetime = new_datetime.replace(tzinfo=UTC)

	try:
		time.clock_settime(time.CLOCK_REALTIME, new_datetime.timestamp())
	except Exception as err:
		raise RuntimeError(f"Failed to set system time as uid {os.geteuid()}: {err}") from err

	if not update_hardware_clock:
		return

	try:
		run_command(["hwclock", "--systohc"], timeout=10.0)
	except Exception as err:
		raise RuntimeError(f"Failed to update hardware clock as uid {os.geteuid()}: {err}") from err
