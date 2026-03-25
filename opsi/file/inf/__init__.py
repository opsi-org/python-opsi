# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.file.inf._inffile import (  # TODO: do we need to expose all of these?
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
	"DeviceType",
	"INFAddRegDirective",
	"INFBitRegDirective",
	"INFDelRegDirective",
	"INFDevice",
	"INFDriverVer",
	"INFFile",
	"INFHardwareID",
	"INFInstallDirective",
	"INFManufacturer",
	"INFRebootDirective",
	"INFSectionType",
	"INFServiceFailureActionsInstall",
	"INFServiceInstallDirective",
	"INFServiceTriggerInstall",
	"INFTargetOSVersion",
	"INFVersion",
]
