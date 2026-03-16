# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
from datetime import datetime

from opsi.process import run_command


def set_system_datetime(utc_datetime: datetime) -> None:
	try:
		run_command(["date", "-f", "%Y-%m-%d %H:%M:%S %Z", "-u", utc_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")], timeout=10.0)
	except Exception as err:
		raise RuntimeError(f"Failed to set system time as uid {os.geteuid()}: {err}") from err
