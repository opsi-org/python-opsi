# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only


import os
from pathlib import Path


class CustomPathLike(os.PathLike[str]):
	def __init__(self, path: str) -> None:
		self._path = path

	def __fspath__(self) -> str:
		return self._path


PATH_TYPES = [str, Path, CustomPathLike]
