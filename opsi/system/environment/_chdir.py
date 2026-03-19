# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

from opsi.logging import get_logger

if TYPE_CHECKING:
	pass

logger = get_logger("opsi")


@contextmanager
def chdir(new_dir: Path) -> Generator[None, None, None]:
	try:
		old_path = os.getcwd()
	except FileNotFoundError:
		old_path = None
	try:
		os.chdir(str(new_dir))
		yield
	finally:
		if old_path:
			os.chdir(old_path)
