# This file is part of the desktop management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import platform

from opsi.system.info import is_linux, is_macos, is_unix, is_windows


def test_is_windows() -> None:
	assert is_windows() == bool(os.name == "nt")


def test_is_linux() -> None:
	assert is_linux() == bool(platform.system() == "Linux")


def test_is_macos() -> None:
	assert is_macos() == bool(platform.system() == "Darwin")


def test_is_unix() -> None:
	assert is_unix() == bool(platform.system() in ("Linux", "Darwin"))
