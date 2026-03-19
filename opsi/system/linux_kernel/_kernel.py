# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path

from opsi.logging import get_logger

CMDLINE_PATH = "/proc/cmdline"

logger = get_logger("opsi")


def get_kernel_params() -> dict[str, str]:
	"""
	Reads the kernel cmdline and returns a dict containing all key=value pairs.
	Keys are converted to lower case.
	"""
	cmdline_path = Path(CMDLINE_PATH)
	logger.debug("Reading %s", cmdline_path)
	cmdline = cmdline_path.read_text(encoding="utf-8").strip()

	params: dict[str, str] = {}
	for option in cmdline.split():
		key_value = option.split("=", 1)
		params[key_value[0].strip().lower()] = "" if len(key_value) == 1 else key_value[1].strip()
	return params
