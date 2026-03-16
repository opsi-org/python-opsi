# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path
from unittest import mock

import pytest


@pytest.mark.linux
def test_get_kernel_params(tmp_path: Path) -> None:
	cmdline_path = tmp_path / "cmdline"
	cmdline_path.write_text("root=/root rw quiet splash apparmor=1 security=apparmor", encoding="utf-8", newline="")

	from opsi.system.linux import get_kernel_params

	with mock.patch("opsi.system.linux._kernel.CMDLINE_PATH", str(cmdline_path)):
		assert get_kernel_params() == {"root": "/root", "rw": "", "quiet": "", "splash": "", "apparmor": "1", "security": "apparmor"}
