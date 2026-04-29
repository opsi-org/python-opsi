# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import re

from opsi.process import run_command


def get_system_uuid() -> str:
	regex = re.compile(r'"IOPlatformUUID"\s*=\s*"([a-zA-Z0-9\-]+)"')
	proc = run_command(["ioreg", "-d", "2", "-c", "IOPlatformExpertDevice"], timeout=10)
	for line in proc.get_output_lines():
		if match := regex.search(line):
			return match.group(1).lower()
	raise RuntimeError(f"Failed to find IOPlatformUUID in ioreg output: {proc.get_output_text()}")
