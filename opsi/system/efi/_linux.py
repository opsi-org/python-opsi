# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path

from opsi.logging import get_logger
from opsi.process import ProcessError, run_command

logger = get_logger("opsi")


def get_system_uuid() -> str:
	uuid_path = Path("/sys/class/dmi/id/product_uuid")
	if uuid_path.exists():
		return uuid_path.read_text(encoding="utf-8").strip().lower()

	logger.debug("'%s' not available, trying dmidecode", uuid_path)
	try:
		run_command(["dmidecode", "-s", "system-uuid"], timeout=10)
		system_uuid = run_command(["dmidecode", "-s", "system-uuid"], timeout=10).get_output_text().strip().lower()
		if not system_uuid:
			raise ValueError("dmidecode did not return a system uuid")
	except (ProcessError, ValueError) as err:
		logger.error("Failed to get system uuid from dmidecode: %s", err)
		raise RuntimeError("Failed to get system uuid from dmidecode") from err
	return system_uuid
