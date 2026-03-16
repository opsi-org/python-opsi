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
