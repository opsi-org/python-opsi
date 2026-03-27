# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import time
from datetime import datetime, timezone

import pytest

import opsi.time._time as time_module
from opsi.time import unix_timestamp


def test_unix_timestamp() -> None:
	unix_ts = unix_timestamp()
	assert isinstance(unix_ts, float)
	unix_ts_ms = unix_timestamp(millis=True)
	assert unix_ts_ms / 1000 - unix_ts < 2
	assert (unix_timestamp(add_seconds=30) - (unix_ts + 30)) < 2
	assert (unix_timestamp(add_seconds=-30) - (unix_ts - 30)) < 2


@pytest.mark.parametrize("local_timezone", ("UTC", "Europe/Berlin", "America/New_York", "Pacific/Auckland"))
@pytest.mark.linux
def test_unix_timestamp_with_tz(monkeypatch: pytest.MonkeyPatch, local_timezone: str) -> None:
	fixed_datetime = datetime(2026, 3, 27, 12, 0, 1, 250000, tzinfo=timezone.utc)
	original_timezone = os.environ.get("TZ")

	def fake_now(*, tz: timezone) -> datetime:
		assert tz is time_module._utc
		return fixed_datetime

	monkeypatch.setattr(time_module, "_now", fake_now)
	os.environ["TZ"] = local_timezone
	time.tzset()

	try:
		unix_ts = unix_timestamp()
		assert isinstance(unix_ts, float)
		assert unix_ts == fixed_datetime.timestamp()
		assert unix_timestamp(millis=True) == fixed_datetime.timestamp() * 1000
		assert unix_timestamp(add_seconds=30) == fixed_datetime.timestamp() + 30
		assert unix_timestamp(add_seconds=-30) == fixed_datetime.timestamp() - 30
	finally:
		if original_timezone is None:
			os.environ.pop("TZ", None)
		else:
			os.environ["TZ"] = original_timezone
		time.tzset()


def test_unix_timestamp_uses_current_utc_time(monkeypatch: pytest.MonkeyPatch) -> None:
	fixed_datetime = datetime(2026, 3, 27, 12, 0, 1, 250000, tzinfo=timezone.utc)

	def fake_now(*, tz: timezone) -> datetime:
		assert tz is time_module._utc
		return fixed_datetime

	monkeypatch.setattr(time_module, "_now", fake_now)

	assert unix_timestamp() == fixed_datetime.timestamp()
	assert unix_timestamp(add_seconds=30.5) == fixed_datetime.timestamp() + 30.5
	assert unix_timestamp(add_seconds=-30.5) == fixed_datetime.timestamp() - 30.5


def test_unix_timestamp_returns_milliseconds_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
	fixed_datetime = datetime(2026, 3, 27, 12, 0, 1, 250000, tzinfo=timezone.utc)

	def fake_now(*, tz: timezone) -> datetime:
		assert tz is time_module._utc
		return fixed_datetime

	monkeypatch.setattr(time_module, "_now", fake_now)

	assert unix_timestamp(millis=True) == fixed_datetime.timestamp() * 1000
	assert unix_timestamp(millis=True, add_seconds=1.5) == (fixed_datetime.timestamp() + 1.5) * 1000
