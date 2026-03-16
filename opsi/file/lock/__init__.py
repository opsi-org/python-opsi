# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_posix, is_windows

if is_posix():
	from ._posix import lock_file
elif is_windows():
	from ._windows import lock_file
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")


__all__ = ["lock_file"]
