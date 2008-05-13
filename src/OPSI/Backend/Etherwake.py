#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Etherwake   =
   = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '0.9.1.1'

# Imports
import os

# OPSI imports
from OPSI.Backend.Backend import *
from OPSI.Logger import *
import OPSI.System
import OPSI.Tools

# Get logger instance
logger = Logger()


# ======================================================================================================
# =                                    CLASS ETHERWAKEBACKEND                                          =
# ======================================================================================================
class EtherwakeBackend(Backend):
	
	def __init__(self, username = '', password = '', address = '', backendManager=None, args={}):
		''' EtherwakeBackend constructor. '''
		
		self.__backendManager = backendManager
		self.__etherwakeCommand = None
		
		# Parse arguments
		for (option, value) in args.items():
			if   (option.lower() == 'etherwakecommand'):	self.__etherwakeCommand = value
			elif (option.lower() == 'defaultdomain'): 	self.__defaultDomain = value
			else:
				logger.warning("Unknown argument '%s' passed to EtherwakeBackend constructor" % option)
		
		if not self.__etherwakeCommand:
			self.__etherwakeCommand = OPSI.Tools.which('etherwake')
		
		# Test if etherwake command is executable
		if not os.access(self.__etherwakeCommand, os.X_OK):
			raise BackendIOError("Command %s not executable!" % self.__etherwakeCommand )
	
	def powerOnHost(self, mac):
		cmd = '%s %s 2>&1' % (self.__etherwakeCommand, mac)
		try:
			OPSI.System.execute(cmd)
		except Exception, e:
			raise BackendIOError("Command '%s' failed: %s" % (cmd, e) )
		
	
