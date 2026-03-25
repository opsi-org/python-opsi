# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.system.windows_driver._driver_utils import (
	BinarySource,
	BinarySourceAccessType,
	BinarySourceBinaryType,
	BinarySourceOperationType,
	add_drivers_to_driver_store,
	integrate_windows_drivers,
)
from opsi.system.windows_driver._inffile import (  # TODO: do we need to expose all of these?
	Architecture,
	DeviceType,
	INFAddRegDirective,
	INFBitRegDirective,
	INFDelRegDirective,
	INFDevice,
	INFDriverVer,
	INFFile,
	INFHardwareID,
	INFInstallDirective,
	INFManufacturer,
	INFRebootDirective,
	INFSectionType,
	INFServiceFailureActionsInstall,
	INFServiceInstallDirective,
	INFServiceTriggerInstall,
	INFTargetOSVersion,
	INFVersion,
)

__all__ = [
	"integrate_windows_drivers",
	"add_drivers_to_driver_store",
	"INFFile",
	"Architecture",
	"INFSectionType",
	"INFDevice",
	"INFHardwareID",
	"INFManufacturer",
	"INFDriverVer",
	"INFInstallDirective",
	"INFRebootDirective",
	"INFAddRegDirective",
	"INFDelRegDirective",
	"INFBitRegDirective",
	"INFServiceInstallDirective",
	"INFServiceFailureActionsInstall",
	"INFServiceTriggerInstall",
	"INFTargetOSVersion",
	"DeviceType",
	"INFVersion",
	"BinarySource",
	"BinarySourceAccessType",
	"BinarySourceBinaryType",
	"BinarySourceOperationType",
]
