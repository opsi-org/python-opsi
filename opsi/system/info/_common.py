# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import platform

SYSTEM = platform.system().lower()


def is_linux() -> bool:
	return SYSTEM == "linux"


def is_windows() -> bool:
	return SYSTEM == "windows"


def is_macos() -> bool:
	return SYSTEM == "darwin"


def is_unix() -> bool:
	return SYSTEM in ("linux", "darwin")


def is_posix() -> bool:
	return SYSTEM in ("linux", "darwin")
