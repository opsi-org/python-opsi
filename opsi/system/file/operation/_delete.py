# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import shutil
from pathlib import Path

from opsi.retry import Retry, RetryConfig, RetryConfigType, get_retry_config


def _delete_attempt(path: Path) -> None:
	from opsi.system.file.operation import get_link_target

	if get_link_target(path) or path.is_file():
		path.unlink()
	else:
		shutil.rmtree(path)


def delete(path: Path | str, *, missing_ok: bool = False, retry_config: RetryConfig | None = None) -> None:
	"""
	Delete a file, link, or directory recursively if it exists.

	Parameters
	----------
	path : Path | str
		The filesystem path to delete. Symbolic links are deleted as links; their targets are not traversed.
	missing_ok : bool, default: False
		If True, do not raise an error if the path does not exist.
	retry_config : RetryConfig, optional
		Configuration for automatic retry behavior on failure. If None, uses the default retry configuration for file I/O operations.
	"""
	path = Path(path)
	# Checking for existence without retry
	if not path.is_symlink() and not path.exists():
		if missing_ok:
			return
		raise FileNotFoundError(path)

	retry_config = retry_config or get_retry_config(RetryConfigType.FILE_IO)
	for attempt in Retry(retry_config):
		with attempt:
			_delete_attempt(path)
