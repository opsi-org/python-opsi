# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from datetime import UTC, datetime, timedelta, timezone

import pytest

import opsi.system.time._linux as linux_time
import opsi.system.time._macos as macos_time
from opsi.system.time import set_system_datetime


@pytest.mark.not_in_docker
@pytest.mark.admin_permissions
def test_set_system_datetime() -> None:
	now = datetime.now(tz=UTC)
	try:
		new_time = now - timedelta(seconds=10)
		set_system_datetime(new_time)
		cur = datetime.now(tz=UTC)
		assert abs((new_time - cur).total_seconds()) <= 1
	finally:
		set_system_datetime(now)


@pytest.mark.linux
def test_set_system_datetime_linux_calls_clock_settime_with_utc_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
	requested = datetime(2026, 4, 22, 9, 12, 33, 500000, tzinfo=UTC)
	called: list[tuple[int, float]] = []
	monkeypatch.setattr(linux_time.time, "clock_settime", lambda clk, ts: called.append((clk, ts)))
	monkeypatch.setattr(linux_time, "run_command", lambda *_a, **_k: pytest.fail("hwclock must not be called"))

	linux_time.set_system_datetime(requested)

	assert called == [(linux_time.time.CLOCK_REALTIME, requested.timestamp())]


@pytest.mark.linux
def test_set_system_datetime_linux_converts_timezones_and_naive_values(monkeypatch: pytest.MonkeyPatch) -> None:
	called: list[float] = []
	monkeypatch.setattr(linux_time.time, "clock_settime", lambda _clk, ts: called.append(ts))
	utc = datetime(2026, 4, 22, 9, 12, 33, tzinfo=UTC)

	linux_time.set_system_datetime(utc.replace(tzinfo=None))
	linux_time.set_system_datetime(utc.astimezone(timezone(timedelta(hours=5))))

	assert called == [utc.timestamp(), utc.timestamp()]


@pytest.mark.linux
def test_set_system_datetime_linux_updates_hardware_clock(monkeypatch: pytest.MonkeyPatch) -> None:
	commands: list[list[str]] = []
	monkeypatch.setattr(linux_time.time, "clock_settime", lambda _clk, _ts: None)
	monkeypatch.setattr(linux_time, "run_command", lambda command, *, timeout: commands.append(command))

	linux_time.set_system_datetime(datetime(2026, 4, 22, 9, 12, 33, tzinfo=UTC), update_hardware_clock=True)

	assert commands == [["hwclock", "--systohc"]]


@pytest.mark.linux
def test_set_system_datetime_linux_raises_runtime_error_on_clock_settime_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_clock_settime(_clk: int, _ts: float) -> None:
		raise PermissionError("no permission")

	monkeypatch.setattr(linux_time.time, "clock_settime", fake_clock_settime)
	monkeypatch.setattr(linux_time.os, "geteuid", lambda: 42)

	with pytest.raises(RuntimeError, match="uid 42.*no permission") as exc_info:
		linux_time.set_system_datetime(datetime(2026, 4, 22, 9, 12, 33, tzinfo=UTC))

	assert isinstance(exc_info.value.__cause__, PermissionError)


@pytest.mark.linux
def test_set_system_datetime_linux_raises_runtime_error_on_hwclock_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_command(command: list[str], *, timeout: float) -> None:
		raise OSError("no rtc")

	monkeypatch.setattr(linux_time.time, "clock_settime", lambda _clk, _ts: None)
	monkeypatch.setattr(linux_time, "run_command", fake_run_command)

	with pytest.raises(RuntimeError, match="hardware clock.*no rtc"):
		linux_time.set_system_datetime(datetime(2026, 4, 22, 9, 12, 33, tzinfo=UTC), update_hardware_clock=True)


@pytest.mark.posix
def test_set_system_datetime_macos_calls_date_with_utc_time(monkeypatch: pytest.MonkeyPatch) -> None:
	called: list[list[str]] = []

	def fake_run_command(command: list[str], *, timeout: float) -> None:
		called.append(command)
		assert timeout == 10.0

	monkeypatch.setattr(macos_time, "run_command", fake_run_command)
	local_tz = timezone(timedelta(hours=2))

	macos_time.set_system_datetime(datetime(2026, 4, 22, 11, 12, 33, tzinfo=local_tz))

	assert called == [["date", "-u", "042209122026.33"]]


@pytest.mark.posix
def test_set_system_datetime_macos_raises_runtime_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_command(command: list[str], *, timeout: float) -> None:
		raise OSError("no permission")

	monkeypatch.setattr(macos_time, "run_command", fake_run_command)
	monkeypatch.setattr(macos_time.os, "geteuid", lambda: 42)

	with pytest.raises(RuntimeError, match="uid 42.*no permission") as exc_info:
		macos_time.set_system_datetime(datetime(2026, 4, 22, 9, 12, 33, tzinfo=UTC))

	assert isinstance(exc_info.value.__cause__, OSError)
