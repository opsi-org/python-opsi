# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows

if is_linux():
	from opsi.system.certificate_store._linux import install_ca, load_ca, load_cas, remove_ca
elif is_windows():
	from opsi.system.certificate_store._windows import install_ca, load_ca, load_cas, remove_ca
elif is_macos():
	from opsi.system.certificate_store._macos import install_ca, load_ca, load_cas, remove_ca
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = ["install_ca", "load_cas", "load_ca", "remove_ca"]
