# -*- coding: utf-8 -*-
"""
:copyright: uib GmbH <info@uib.de>
This file is part of opsi - https://www.opsi.org

:license: GNU Affero General Public License version 3
"""

import platform

from OPSI.Logger import Logger

logger = Logger()

if platform.system().lower() == 'linux':
	from .linux import *
elif platform.system().lower() == 'windows':
	from .windows import *

else:
	logger.error("Unable to import System library for system %s", platform.system().lower())
