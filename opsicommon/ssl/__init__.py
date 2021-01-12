# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import platform
from opsicommon.logging import logger

if platform.system().lower() == 'linux':
	from .linux import *
elif platform.system().lower() == 'windows':
	from .windows import *
elif platform.system().lower() == 'darwin':
	from .darwin import *
else:
	raise NotImplementedError(f"{platform.system().lower()} not supported")
