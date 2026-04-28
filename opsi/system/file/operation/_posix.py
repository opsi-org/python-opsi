# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path


def get_link_target(link_path: Path | str) -> Path | None:
	"""
	Return the target path of a symbolic link.

	Parameters
	----------
	link_path : Path | str
		The path to inspect.

	Returns
	-------
	Path | None
		The link target if `link_path` is a symbolic link, otherwise None.
	"""
	link_path = Path(link_path)
	if link_path.is_symlink():
		return link_path.resolve()
	return None
