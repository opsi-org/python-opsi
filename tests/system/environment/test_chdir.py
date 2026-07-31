# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
from pathlib import Path
from unittest.mock import patch

from opsi.system.environment import chdir


def test_chdir(tmp_path: Path) -> None:
	original_dir = os.getcwd()
	with chdir(tmp_path):
		assert os.getcwd() == str(tmp_path)
	assert os.getcwd() == original_dir

	orig_getcwd = os.getcwd
	with patch("os.getcwd", side_effect=FileNotFoundError()), chdir(tmp_path):
		assert orig_getcwd() == str(tmp_path)
	assert orig_getcwd() == str(tmp_path)
	os.chdir(original_dir)
