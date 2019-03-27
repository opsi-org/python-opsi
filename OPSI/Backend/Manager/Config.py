# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2018-2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
BackendManager configuration helper.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import socket
import sys
from functools import lru_cache

from OPSI.Exceptions import BackendConfigurationError


def loadBackendConfig(path):
	"""
	Load the backend configuration at `path`.
	:param path: Path to the configuration file to load.
	:type path: str
	:rtype: dict
	"""
	if not os.path.exists(path):
		raise BackendConfigurationError(u"Backend config file '%s' not found" % path)

	moduleGlobals = {
		'config': {},  # Will be filled after loading
		'module': '',  # Will be filled after loading
		'os': os,
		'socket': socket,
		'sys': sys,
	}

	exec(_readFile(path), moduleGlobals)

	return moduleGlobals


@lru_cache(maxsize=None)
def _readFile(path):
	with open(path) as configFile:
		return configFile.read()
