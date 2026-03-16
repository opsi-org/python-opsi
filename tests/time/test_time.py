# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.time import unix_timestamp


def test_unix_timestamp() -> None:
	# TODO: mock timezones
	unix_ts = unix_timestamp()
	assert isinstance(unix_ts, float)
	unix_ts_ms = unix_timestamp(millis=True)
	assert unix_ts_ms / 1000 - unix_ts < 2
	assert (unix_timestamp(add_seconds=30) - (unix_ts + 30)) < 2
	assert (unix_timestamp(add_seconds=-30) - (unix_ts - 30)) < 2
