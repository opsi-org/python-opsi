#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Util      =
   = = = = = = = = = = = = = = = = = = =
   
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

__version__ = '3.5'

# Imports
import ctypes, threading

# OPSI imports
from OPSI.Logger import *

# Get Logger instance
logger = Logger()

def _async_raise(tid, excobj):
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
	if (res == 0):
		logger.error(u"_async_raise: nonexistent thread id")
		raise ValueError(u"nonexistent thread id")
	elif (res > 1):
		# if it returns a number greater than one, you're in trouble,
		# and you should call it again with exc=NULL to revert the effect
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
		logger.error(u"_async_raise: PyThreadState_SetAsyncExc failed")
		raise SystemError(u"PyThreadState_SetAsyncExc failed")

class KillableThread(threading.Thread):
	def raise_exc(self, excobj):
		if not self.isAlive():
			logger.error(u"Cannot terminate, thread must be started")
			return
		for tid, tobj in threading._active.items():
			if tobj is self:
				_async_raise(tid, excobj)
				return
	
	# the thread was alive when we entered the loop, but was not found 
	# in the dict, hence it must have been already terminated. should we raise
	# an exception here? silently ignore?
	
	def terminate(self):
		# must raise the SystemExit type, instead of a SystemExit() instance
		# due to a bug in PyThreadState_SetAsyncExc
		self.raise_exc(SystemExit)



