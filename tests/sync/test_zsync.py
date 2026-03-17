# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path

from opsi.sync.zsync import create_zsync_file


def test_create_zsync_file(tmp_path: Path) -> None:
	remote_file = tmp_path / "remote"
	remote_file.write_bytes(b"\0" * 1_000_000)
	zsync_file = tmp_path / "remote.zsync"
	create_zsync_file(remote_file, zsync_file)
	assert zsync_file.exists()
