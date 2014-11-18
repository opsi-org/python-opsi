#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Configuration util.

:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from optparse import OptionParser


class BaseConfiguration(object):

	configFiles = tuple()

	def __init__(self, args):
		self._options = {}
		self._parser = self._makeParser()
		self._loadConfiguration(args)

	def _makeParser(self):
		return OptionParser()

	def _loadConfiguration(self, args):
		self._options.update(self._parser.defaults.copy())
		self._parser.defaults.clear()

		self._options.update(self._loadConfigFiles())

		(opts, args) = self._parser.parse_args(args)
		self._options.update(vars(opts))

	def _loadConfigFiles(self):
		return {}

	def __getitem__(self, name):
		return self.__getattr__(name)

	def __getattr__(self, name):
		option = self._parser.get_option("--" + name.replace("_", "-"))

		if option is not None:
			value = self._options.get(name)
			if isinstance(value, basestring):
				return option.convert_value(name, value)
		else:
			raise AttributeError(name)
