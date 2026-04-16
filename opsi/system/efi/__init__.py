# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.system.efi._efi import (
	DevicePathType,
	EFIBootEntry,
	EFIBootManager,
	EFINVRAMStats,
	EFIVariableAttribute,
	cleanup_efi_nvram,
	get_efi_nvram_stats,
)

__all__ = [
	"EFIBootManager",
	"EFIBootEntry",
	"DevicePathType",
	"EFIVariableAttribute",
	"get_efi_nvram_stats",
	"EFINVRAMStats",
	"cleanup_efi_nvram",
]
