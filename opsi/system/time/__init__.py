# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows

if is_linux():
	from ._linux import set_system_datetime
elif is_windows():
	from ._windows import set_system_datetime
elif is_macos():
	from ._macos import set_system_datetime
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = ["set_system_datetime"]
