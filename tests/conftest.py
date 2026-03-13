# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import platform
import sys
import threading
import time
from functools import lru_cache

import pytest

from opsi.logging import logging_config


@lru_cache
def _system_platform() -> str:
	return platform.system().lower()


@lru_cache
def _admin_permissions() -> bool:
	try:
		return os.geteuid() == 0
	except AttributeError:
		import ctypes

		return ctypes.windll.shell32.IsUserAnAdmin() != 0  # type: ignore[attr-defined]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
	# Run logging tests last, as they are messing up pytests logging
	items.sort(key=lambda item: 2 if "logging" in item.path.parts[-3:] else 1)


def pytest_runtest_setup(item: pytest.Item) -> None:
	for marker in item.iter_markers():
		if marker.name in ("windows", "linux", "macos", "posix"):
			supported_platforms = []
			if marker.name == "posix":
				supported_platforms.extend(["linux", "macos"])
			else:
				supported_platforms.append(marker.name)
			if _system_platform() not in supported_platforms:
				pytest.skip(f"Test only runs on: {', '.join(supported_platforms)}")
				return
		if marker.name == "admin_permissions" and not _admin_permissions():
			pytest.skip("No admin permissions")
			return

	item.stash["start_threads"] = set(threading.enumerate())  # type: ignore[index]


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
	# Reset log level
	logging_config(stderr_level=0)

	for wait in range(6):
		left_over_threads = set(
			t
			for t in threading.enumerate()
			if t.is_alive()
			and t.name not in ("MainThread", "ServiceConnectionThread")
			and "ThreadPoolExecutor" not in str((getattr(t, "_args", None) or [None])[0])
		) - item.stash.get("start_threads", set())  # type: ignore[arg-type]
		if not left_over_threads:
			break
		if wait >= 5:
			print("Left over threads after test:", file=sys.stderr)
			for thread in left_over_threads:
				print(thread.__dict__, file=sys.stderr)
			raise RuntimeError(f"Left over threads after test: {left_over_threads}")
		time.sleep(1)
