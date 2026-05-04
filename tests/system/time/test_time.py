# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from datetime import datetime, timedelta, timezone

import pytest

import opsi.system.time._linux as linux_time
import opsi.system.time._macos as macos_time
from opsi.system.info import is_linux, is_macos
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


@pytest.mark.posix
def test_set_system_datetime_calls_run_command_with_utc_time(monkeypatch: pytest.MonkeyPatch) -> None:
	requested = datetime(2026, 4, 22, 9, 12, 33, tzinfo=timezone.utc)
	called: list[list[str]] = []

	def fake_run_command(command: list[str], *, timeout: float) -> None:
		called.append(command)
		assert timeout == 10.0

	if is_linux():
		monkeypatch.setattr(linux_time, "run_command", fake_run_command)
		linux_time.set_system_datetime(requested)
		assert called == [["date", "--utc", "--set", "2026-04-22 09:12:33"]]
	elif is_macos():
		monkeypatch.setattr(macos_time, "run_command", fake_run_command)
		macos_time.set_system_datetime(requested)
		assert called == [["date", "-f", "%Y-%m-%d %H:%M:%S %Z", "-u", "2026-04-22 09:12:33 UTC"]]


@pytest.mark.posix
def test_set_system_datetime_raises_runtime_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_run_command(command: list[str], *, timeout: float) -> None:
		raise OSError("no permission")

	if is_linux():
		monkeypatch.setattr(linux_time, "run_command", fake_run_command)
		monkeypatch.setattr(linux_time.os, "geteuid", lambda: 42)
	elif is_macos():
		monkeypatch.setattr(macos_time, "run_command", fake_run_command)
		monkeypatch.setattr(macos_time.os, "geteuid", lambda: 42)

	with pytest.raises(RuntimeError) as exc_info:
		linux_time.set_system_datetime(datetime(2026, 4, 22, 9, 12, 33, tzinfo=timezone.utc))

	assert "uid 42" in str(exc_info.value)
	assert "no permission" in str(exc_info.value)
	assert isinstance(exc_info.value.__cause__, OSError)
