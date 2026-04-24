# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only


def get_system_uuid() -> str:
	# Import wmi only when needed
	# Import on module level can lead to problems during system startup

	import wmi  # type: ignore[import]

	wmi_inst = wmi.WMI()
	for csp in wmi_inst.Win32_ComputerSystemProduct():
		return csp.UUID.lower()
	raise RuntimeError("Failed to find UUID in Win32_ComputerSystemProduct")
