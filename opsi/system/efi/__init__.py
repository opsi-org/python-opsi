# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.efi._efi import (
	DevicePathType,
	EFIBootEntry,
	EFIBootManager,
	EFINVRAMStats,
	EFIVariableAttribute,
	cleanup_efi_nvram,
	get_efi_nvram_stats,
)
from opsi.system.info import get_system, is_linux, is_macos, is_windows

if is_linux():
	from opsi.system.efi._linux import get_system_uuid
elif is_windows():
	from opsi.system.efi._windows import get_system_uuid
elif is_macos():
	from opsi.system.efi._macos import get_system_uuid
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = [
	"EFIBootManager",
	"EFIBootEntry",
	"DevicePathType",
	"EFIVariableAttribute",
	"get_efi_nvram_stats",
	"EFINVRAMStats",
	"cleanup_efi_nvram",
	"get_system_uuid",
]
