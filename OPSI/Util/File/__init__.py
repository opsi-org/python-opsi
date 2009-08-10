#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =    opsi python library - File     =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH
   
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

__version__ = "3.5"

import os, codecs, re

if (os.name == 'posix'):
	import fcntl

elif (os.name == 'nt'):
	import win32con
	import win32file
	import pywintypes

# OPSI imports
from OPSI.Logger import *
from OPSI.Backend.Object import *

# Get logger instance
logger = Logger()

class File(object):
	def __init__(self, filename):
		self._filename = forceUnicode(filename)
		self._fileHandle = None
		self.mode = None
		
	def open(self, mode = 'r'):
		self.mode = mode
		self._fileHandle = __builtins__['open'](self._filename, mode)
		return self._fileHandle
		
	def close(self):
		if not self._fileHandle:
			return
		self._fileHandle.close()
	
	def __getattr__(self, attr):
		if self.__dict__.has_key(attr):
			return self.__dict__[attr]
		elif self.__dict__['_fileHandle']:
			return getattr(self.__dict__['_fileHandle'], attr)

class LockableFile(File):
	def __init__(self, filename, lockFailTimeout = 2000):
		File.__init__(self, filename)
		self._lockFailTimeout = forceInt(lockFailTimeout)
		
	def open(self, mode = 'r'):
		File.open(self, mode)
		self._lockFile()
	
	def close(self):
		self._unlockFile()
		File.close(self)
	
	def _lockFile(self):
		timeout = 0
		while (timeout < self._lockFailTimeout):
			# While not timed out and not locked
			logger.debug("Trying to lock file '%s' (%s/%s)" % (self._filename, timeout, self._lockFailTimeout))
			try:
				# Try to lock file
				if (os.name =='posix'):
					# Flags for exclusive, non-blocking lock
					flags = fcntl.LOCK_EX | fcntl.LOCK_NB
					if self.mode in ('r', 'rb'):
						# Flags for shared, non-blocking lock
						flags = fcntl.LOCK_SH | fcntl.LOCK_NB
					fcntl.flock(self._fileHandle.fileno(), flags)
				elif (os.name == 'nt'):
					flags = win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY
					if self.mode in ('r', 'rb'):
						flags = win32con.LOCKFILE_FAIL_IMMEDIATELY
					hfile = win32file._get_osfhandle(self._fileHandle.fileno())
					win32file.LockFileEx(hfile, flags, 0, 0x7fff0000, pywintypes.OVERLAPPED())
				
			except IOError, e:
				# Locking failed 
				# increase timeout counter, sleep 100 millis
				timeout += 100
				time.sleep(0.1)
				continue
			# File successfully locked
			logger.debug("File '%s' locked after %d millis" % (self._filename, timeout))
			return self._fileHandle
		
		self.close()
		# File lock failed => raise BackendIOError
		raise IOError("Failed to lock file '%s' after %d millis" % (self._filename,  self._lockFailTimeout))
	
	def _unlockFile(self):
		if not self._fileHandle:
			return
		if (os.name == 'posix'):
			fcntl.flock(self._fileHandle.fileno(), fcntl.LOCK_UN)
		elif (os.name == 'nt'):
			hfile = win32file._get_osfhandle(self._fileHandle.fileno())
			win32file.UnlockFileEx(hfile, 0, 0x7fff0000, pywintypes.OVERLAPPED())
	
class TextFile(LockableFile):
	def __init__(self, filename, lockFailTimeout = 2000):
		LockableFile.__init__(self, filename)
		
	def open(self, mode = 'r', encoding='utf-8', errors='replace'):
		self._fileHandle = codecs.open(self._filename, mode, encoding, errors)
		self._lockFile()
	
	def write(self, str):
		if not self._fileHandle:
			raise IOError("File not opened")
		str = forceUnicode(str)
		self._fileHandle.write(str)
	
	def writelines(self, sequence):
		if not self._fileHandle:
			raise IOError("File not opened")
		sequence = forceUnicodeList(sequence)
		self._fileHandle.writelines(sequence)
	
class ConfigFile(TextFile):
	def __init__(self, filename, lockFailTimeout = 2000, commentChars=[';', '/', '#']):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._commentChars = forceList(commentChars)
		self._lines = []
		
	def readlines(self):
		self._lines = []
		if not self._fileHandle:
			self.open()
		for line in self._fileHandle.readlines():
			line = line.strip()
			if not line or line[0] in self._commentChars:
				continue
			self._lines.append(line)
		self.close()
		return self._lines
	
class OpsiBackendACLFile(ConfigFile):
	def parse(self):
		aclEntryRegex = re.compile('^([^:]+)+\s*:\s*(\S.*)$')
		acl = []
		for line in self.readlines():
			match = re.search(aclEntryRegex, line)
			if not match:
				logger.error(u"Found bad formatted line '%s' in acl file '%s'" % (line, self._filename))
				continue
			method = match.group(1)
			acl.append([match.group(1), []])
			for entry in match.group(2).split(','):
				entry = entry.strip()
				type = entry
				param = ''
				if (entry.find('(') != -1):
					(type, param) = entry.split('(', 1)
					if (param.find(')') == -1):
						logger.error(u"Bad formatted acl entry: '%s'" % entry)
						continue
					type = type.strip()
					param = param.split(')')[0].strip()
				if not type in ('all', 'opsi_depotserver', 'opsi_client', 'sys_group', 'sys_user'):
					logger.error(u"Unhandled acl entry: '%s'" % entry)
					continue
				entry = type
				if param:
					entry += u'(%s)' % param
				acl[-1][1].append(entry)
		return acl

class OpsiBackendDispatchConfigFile(ConfigFile):
	def parse(self):
		dispatchEntryRegex = re.compile('^([^:]+)+\s*:\s*(\S.*)$')
		dispatch = []
		for line in self.readlines():
			match = re.search(dispatchEntryRegex, line)
			if not match:
				logger.error(u"Found bad formatted line '%s' in dispatch config file '%s'" % (line, self._filename))
				continue
			method = match.group(1)
			dispatch.append([match.group(1), []])
			for entry in match.group(2).split(','):
				dispatch[-1][1].append(entry.strip())
		return dispatch















