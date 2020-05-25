# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2019 uib GmbH <info@uib.de>

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
Handling an .opsirc file.

An .opsirc file contains information about how to connect to an
opsi API.
By default the file is expected to be at `~/.opsi.org/opsirc`.

An example::

	address = https://opsimain.domain.local:4447/rpc
	username = myname
	password = topsecret


None of these settings are mandatory.

Instead of writing the password directly to the file it is possible
to reference a file with the secret as follows::

	password file = ~/.opsi.org/opsirc.secret


The files should be encoded as utf-8.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os

from OPSI.Logger import Logger
from OPSI.Types import forceUnicode, forceUrl

__all__ = ('getOpsircPath', 'readOpsirc')


logger = Logger()


def readOpsirc(filename=None):
	"""
	Read the configuration file and parse it for usable information.

	:param filename: The path of the file to read. Defaults to using \
the result from `getOpsircPath`.
	:type filename: str
	:returns: Settings read from the file. Possible keys are `username`,\
`password` and `address`.
	:rtype: {str: str}
	"""
	if filename is None:
		filename = getOpsircPath()

	if not os.path.exists(filename):
		logger.debug(u".opsirc file %s does not exist.", filename)
		return {}

	return _parseConfig(filename)


def getOpsircPath():
	"""
	Return the path where an opsirc file is expected to be.

	:return: The path of an opsirc file.
	:rtype: str
	"""
	path = os.path.expanduser('~/.opsi.org/opsirc')
	return path


def _parseConfig(filename):
	config = {}
	with codecs.open(filename, mode='r', encoding='utf-8') as opsircfile:
		for line in opsircfile:
			line = line.strip()
			if line.startswith(('#', ';')) or not line:
				continue

			try:
				key, value = line.split('=', 1)
			except ValueError:
				logger.debug2(u"Unable to split line %s", line)
				continue

			key = key.strip()
			value = value.strip()

			if not value:
				logger.warning(
					"There is no value for %s in opsirc file %s, skipping.",
					key, filename
				)
				continue

			if key == 'address':
				config[key] = forceUrl(value)
			elif key == 'username':
				config[key] = forceUnicode(value)
			elif key == 'password':
				value = forceUnicode(value)
				logger.addConfidentialString(value)
				config[key] = value
			elif key == 'password file':
				passwordFilePath = os.path.expanduser(value)
				value = _readPasswordFile(passwordFilePath)
				logger.addConfidentialString(value)
				config['password'] = value
			else:
				logger.debug(u"Ignoring unknown key %s", key)

	logger.debug(
		"Found the following usable keys in %s: %s",
		filename, ", ".join(config.keys())
	)
	return config


def _readPasswordFile(filename):
	with codecs.open(filename, mode='r', encoding='utf-8') as pwfile:
		password = pwfile.read()

	return password.strip()
