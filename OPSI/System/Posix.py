#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - Posix   =
   = = = = = = = = = = = = = = = = = =
   
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

__version__ = '3.5'

# Imports
import os, sys, subprocess

# OPSI imports
from OPSI.Logger import *

# Get Logger instance
logger = Logger()

# Constants
BIN_WHICH   = '/usr/bin/which'
WHICH_CACHE = {}

def which(cmd):
	if not WHICH_CACHE.has_key(cmd):
		w = os.popen('%s "%s" 2>/dev/null' % (BIN_WHICH, cmd))
		path = w.readline().strip()
		w.close()
		if not path:
			raise Exception(u"Command '%s' not found in PATH" % cmd)
		WHICH_CACHE[cmd] = path
		logger.debug(u"Command '%s' found at: '%s'" % (cmd, WHICH_CACHE[cmd]))
	
	return WHICH_CACHE[cmd]

def execute(cmd, nowait=False, getHandle=False, ignoreExitCode=False, exitOnStderr=False, captureStderr=True, encoding='utf-8'):
	"""
	Executes a command and returns output lines as list
	"""
	exitCode = 0
	result = u''
	
	try:
		logger.info(u"Executing: %s" % cmd)
		
		if nowait:
			os.spawnv(os.P_NOWAIT, which('bash'), [which('bash'), '-c', cmd])
			return []
		
		elif getHandle:
			if captureStderr:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)).stdout
			else:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None)).stdout
		
		else:
			stderr = None
			if captureStderr:
				stderr	= subprocess.PIPE
			proc = subprocess.Popen(
				cmd,
				shell	= True,
				stdin	= subprocess.PIPE,
				stdout	= subprocess.PIPE,
				stderr	= stderr,
			)
			
			flags = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
			fcntl.fcntl(proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			
			if captureStderr:
				flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
				fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			
			ret = None
			curLine = u''
			curErrLine = u''
			while ret is None:
				ret = proc.poll()
				try:
					string = proc.stdout.read().decode(encoding)
					if (len(string) > 0):
						result += string
						curLine += string
						if (curLine.find(u'\n') != -1):
							lines = curLine.split(u'\n')
							for i in range(len(lines)):
								if (i == len(lines)-1):
									curLine = lines[i]
								else:
									logger.debug(u" ->>> %s" % lines[i])
				except IOError, e:
					if (e.errno != 11):
						raise
				
				if captureStderr:
					try:
						string = proc.stderr.read().decode(encoding)
						if (len(string) > 0):
							result += string
							curErrLine += string
							if (curErrLine.find(u'\n') != -1):
								if exitOnStderr:
									if (type(exitOnStderr) is bool) or (type(exitOnStderr) in (unicode, str, type(re.compile(''))) and re.search(exitOnStderr, curErrLine)):
										raise Exception(u"Command '%s' failed: %s" % (cmd, curErrLine) )
								lines = curErrLine.split(u'\n')
								for i in range(len(lines)):
									if (i == len(lines)-1):
										curErrLine = lines[i]
									else:
										logger.error(u" ->>> %s" % lines[i])
					except IOError, e:
						if (e.errno != 11):
							raise
				
				time.sleep(0.001)
			
			if curLine:
				logger.debug(u" ->>> %s" % curLine)
			if curErrLine:
				logger.error(u" ->>> %s" % curErrLine)
			
			exitCode = ret
			result = result.split(u'\n')
			
	except (os.error, IOError), e:
		# Some error occured during execution
		raise Exception(u"Command '%s' failed:\n%s" % (cmd, e) )
	
	logger.debug(u"Exit code: %s" % exitCode)
	if exitCode and not ignoreExitCode:
		raise Exception(u"Command '%s' failed (%s):\n%s" % (cmd, exitCode, '\n'.join(result)) )
	return result

def getDiskSpaceUsage(path):
	disk = os.statvfs(path)
	info = {}
	info['capacity'] = disk.f_bsize * disk.f_blocks
	info['available'] = disk.f_bsize * disk.f_bavail
	info['used'] = disk.f_bsize * (disk.f_blocks - disk.f_bavail)
	info['usage'] = float(disk.f_blocks - disk.f_bavail) / float(disk.f_blocks)
	logger.info(u"Disk space usage for path '%s': %s" % (path, info))
	return info

