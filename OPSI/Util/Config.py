# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2017 uib GmbH <info@uib.de>
# http://www.uib.de/

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
Configuration utility functions.


:copyright:	uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os

from OPSI.Config import OPSI_GLOBAL_CONF
from OPSI.Types import forceUnicode


__all__ = ('getGlobalConfig', )


def getGlobalConfig(name, configFile=OPSI_GLOBAL_CONF):
	"""
	Reads the value of ``name`` from the global configuration.

	:param configFile: The path of the config file.
	:type configFile: str
	"""
	name = forceUnicode(name)
	if os.path.exists(configFile):
		with codecs.open(configFile, 'r', 'utf8') as config:
			for line in config:
				line = line.strip()
				if line.startswith(('#', ';')):
					continue

				try:
					key, value = line.split('=', 1)
					if key.strip().lower() == name.lower():
						return value.strip()
				except ValueError:
					continue

	return None
