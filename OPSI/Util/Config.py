# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2017-2019 uib GmbH <info@uib.de>
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

__all__ = ('getGlobalConfig', 'setGlobalConfig')


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

def setGlobalConfig(name, value, configFile=OPSI_GLOBAL_CONF):
	"""
	Set ``name`` to ``value`` in the global configuration.

	:param configFile: The path of the config file.
	:type configFile: str
	"""
	name = forceUnicode(name)
	value = forceUnicode(value)
	
	lines = []
	new_line = f"{name} = {value}"
	if os.path.exists(configFile):
		with codecs.open(configFile, 'r', 'utf8') as config:
			for line in config:
				lines.append(line.rstrip())
				line = line.strip()
				if line.startswith(('#', ';')):
					continue

				key, value = line.split('=', 1)
				if key.strip().lower() == name.lower():
					lines[-1] = new_line
					new_line = None
	if new_line:
		lines.append(new_line)
	
	with codecs.open(configFile, 'w', 'utf8') as config:
		config.writelines(lines)
	
	from OPSI.Util.Task.Rights import setRights
	setRights(configFile)
