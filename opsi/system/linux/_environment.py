# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import platform
from pathlib import Path

from opsi.logging import get_logger

logger = get_logger(__name__)


def update_environment_from_config_files(files: list[Path] | None = None) -> None:
	"""
	Updates the environment variables from the config files.
	"""
	if not platform.system().lower() == "linux":
		return

	if files is None:  # allow empty list
		files = [Path("/etc/environment"), Path("/etc/sysconfig/proxy"), Path("/etc/default")]
	# debian/ubuntu, suse, redhat/centos
	for path in files:
		if not path.exists() or not path.is_file():
			continue
		logger.debug("Updating environment from %s", path)
		with path.open("r", encoding="utf-8") as file:
			for line in file:
				line = line.strip()
				if not line or line.startswith("#") or "=" not in line:
					continue
				key, value = line.split("=", 1)
				key = key.lstrip("export").strip().lower()
				value = value.strip(" '\"\t")
				if value and key in ("http_proxy", "https_proxy", "no_proxy") and not os.environ.get(key):
					os.environ[key] = value.strip()
