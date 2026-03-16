# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from datetime import datetime, timedelta, timezone

import pytest

from opsi.system.time import set_system_datetime


@pytest.mark.not_in_docker
@pytest.mark.admin_permissions
def test_set_system_datetime() -> None:
	now = datetime.now(tz=timezone.utc)
	try:
		new_time = now - timedelta(seconds=10)
		set_system_datetime(new_time)
		cur = datetime.now(tz=timezone.utc)
		assert abs((new_time - cur).total_seconds()) <= 1
	finally:
		set_system_datetime(now)
