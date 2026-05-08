# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import platform
import enum
from opsi.util.pattern import MappedStrEnum
from opsi.exception import OperatingSystemUnsupportedError

class OperatingSystemType(MappedStrEnum):
	WINDOWS = "windows"
	MACOS = "macos"
	LINUX = "linux"

	_NAME = enum.nonmember("operating system type")
	_ALIASES = enum.nonmember({"darwin": "macos"})


try:
	OPERATING_SYSTEM_TYPE = OperatingSystemType(platform.system())
except ValueError:
	raise OperatingSystemUnsupportedError(f"Unsupported operating system: {platform.system()}")


def get_system() -> OperatingSystemType:
	return OPERATING_SYSTEM_TYPE


def is_linux() -> bool:
	return OPERATING_SYSTEM_TYPE == OperatingSystemType.LINUX


def is_windows() -> bool:
	return OPERATING_SYSTEM_TYPE == OperatingSystemType.WINDOWS


def is_macos() -> bool:
	return OPERATING_SYSTEM_TYPE == OperatingSystemType.MACOS


def is_unix() -> bool:
	return OPERATING_SYSTEM_TYPE in (OperatingSystemType.LINUX, OperatingSystemType.MACOS)


def is_posix() -> bool:
	return OPERATING_SYSTEM_TYPE in (OperatingSystemType.LINUX, OperatingSystemType.MACOS)
