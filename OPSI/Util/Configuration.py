#!/usr/bin/python
# -*- coding: utf-8 -*-


#= = = = = = = = = = = = = = = = = = = = = = =
#=##                                     =
#= = = = = = = = = = = = = = = = = = = = = = =
#
#All rights reserved.
#
#This program is free software; you can redistribute it and/or modify
#it under the terms of the GNU General Public License version 2 as
#published by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#   @copyright: 
#   @author: Christian Kampka <c.kampka@uib.de>
#   @license: GNU General Public License version 2



import os, sys
import optparse
from optparse import OptionParser, OptionGroup
from ConfigParser import ConfigParser

class BaseConfiguration(object):

	configFiles = []

	configFiles = tuple(configFiles)
	
	def __init__(self, args):
		self._options = {}
		self._parser = self._makeParser()
		self._loadConfiguration(args)

	def _makeParser(self):
		
		parser = OptionParser()
		return parser

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