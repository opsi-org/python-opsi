# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import subprocess
from datetime import datetime

from opsi.logging import get_logger

logger = get_logger("opsi")


def set_system_datetime(utc_datetime: datetime) -> None:
	try:
		subprocess.run(["date", "--utc", "--set", utc_datetime.strftime("%Y-%m-%d %H:%M:%S")], capture_output=True, check=True)
	except subprocess.CalledProcessError as err:
		raise RuntimeError(
			f"Failed to set system time as uid {os.geteuid()}: {err.returncode} - {err.stderr.decode(errors='replace')}"
		) from err
