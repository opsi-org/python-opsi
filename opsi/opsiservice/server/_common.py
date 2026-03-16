# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import json
from functools import lru_cache
from typing import Any

from opsi.logging import get_logger, secret_filter
from opsi.process import run_command

logger = get_logger("opsi")

OPSICONFD_GET_CONFIG_COMMAND = ["opsiconfd", "get-config"]


@lru_cache
def _opsiconfd_get_config() -> dict[str, Any]:
	return json.loads(run_command(OPSICONFD_GET_CONFIG_COMMAND, timeout=10.0).get_stdout_text())


def get_opsiconfd_config(template: dict[str, Any] | None = None, ignore_error: bool = True) -> dict[str, str]:
	config = dict(template) if template else {}
	try:
		for attribute, value in _opsiconfd_get_config().items():
			if "passphrase" in attribute or "password" in attribute or "private_key" in attribute:
				secret_filter.add_secrets(value)
			if not template or attribute in template:
				config[attribute] = value
	except Exception as err:
		if not ignore_error:
			raise
		logger.debug("Failed to get opsiconfd config %s", err)
	return config
