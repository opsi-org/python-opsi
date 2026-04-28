# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.file.operation._operation import delete, link
from opsi.system.info import get_system, is_posix, is_windows

if is_posix():
	from opsi.system.file.operation._posix import get_link_target
elif is_windows():
	from opsi.system.file.operation._windows import get_link_target
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")

__all__ = ["delete", "link", "get_link_target"]
