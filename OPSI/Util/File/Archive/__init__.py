#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = =
   =    opsi python library - File.Archive   =
   = = = = = = = = = = = = = = = = = = = = = =
   
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

__version__ = "3.4.99"

# Imports
import os, magic, subprocess, fcntl, locale

# OPSI imports
from OPSI.Logger import *
from OPSI import System
from OPSI.Types import *

logger = Logger()

def getFileTye(filename):
	filename = forceFilename(filename)
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	fileType = ms.file(filename)
	ms.close()
	return fileType

class BaseArchive(object):
	def __init__(self, filename):
		self._filename = forceFilename(filename)
		self._compression = None
		if os.path.exists(self._filename):
			fileType = getFileTye(self._filename)
			if   fileType.lower().startswith('gzip compressed data'):
				self._compression = 'gzip'
			elif fileType.lower().startswith('bzip2 compressed data'):
				self._compression = 'bzip2'
			elif fileType.lower().startswith('posix tar archive') and isinstance(self, TarArchive):
				self._compression = None
			elif fileType.lower().startswith('ascii cpio archive') and isinstance(self, CpioArchive):
				self._compression = None
			else:
				raise Exception(u"Unsupported file type '%s'" % fileType)
	
	def _create(self, fileList, baseDir, command):
		curDir = os.path.abspath(os.getcwd())
		try:
			baseDir = os.path.abspath(forceFilename(baseDir))
			if not os.path.isdir(baseDir):
				raise Exception(u"Base dir '%s' not found" % baseDir)
			os.chdir(baseDir)
			
			logger.info(u"Executing: %s" % command )
			proc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			
			encoding = proc.stdin.encoding
			if not encoding:
				encoding = locale.getpreferredencoding()
			
			flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
			fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			
			error = ''
			ret = None
			for f in fileList:
				if not f:
					continue
				f = os.path.relpath(f, baseDir)
				logger.info(u"Adding file '%s'" % f)
				proc.stdin.write("%s\n" % f.encode(encoding))
				
				try:
					chunk = proc.stderr.read()
					if chunk:
						error += chunk
				except:
					pass
			
			proc.stdin.close()
			
			while ret is None:
				ret = proc.poll()
			
			logger.info(u"Exit code: %s" % ret)
			
			if (ret != 0):
				error = error.decode(encoding, 'replace')
				logger.error(error)
				raise Exception(u"Command '%s' failed with code %s: %s" % (command, ret, error))
		finally:
			os.chdir(curDir)
		
class TarArchive(BaseArchive):
	def __init__(self, filename):
		BaseArchive.__init__(self, filename)
	
	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise Exception(u"Archive file not found: '%s'" % self._filename)
			names = []
			options = u''
			if   (self._compression == 'gzip'):
				options += u'--gunzip'
			elif (self._compression == 'bzip2'):
				options += u'--bzip2'
			for line in System.execute(u'%s %s --list --file "%s"' % (System.which('tar'), options, self._filename)):
				if line:
					names.append(unicode(line))
			return names
		except Exception, e:
			raise Exception(u"Failed to get archive content '%s': %s" % (self._filename, e))
	
	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns   = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				os.mkdir(targetPath)
			
			options = u''
			if   (self._compression == 'gzip'):
				options += u'--gunzip'
			elif (self._compression == 'bzip2'):
				options += u'--bzip2'
			
			for f in self.content():
				for p in patterns:
					try:
						p = p.replace('*', '.*')
						if not re.search(p, f):
							options += u' --exclude="%s"' % f
							continue
					except Exception, e:
						raise Exception(u"Bad pattern '%s': %s" % (p, e))
			
			System.execute(u'%s %s --directory "%s" --extract --file "%s"' % (System.which('tar'), options, targetPath, self._filename))
		except Exception, e:
			raise Exception(u"Failed to extract archive '%s': %s" % (self._filename, e))
	
	def create(self, fileList, baseDir='.', dereference=False, compression=None):
		try:
			fileList    = forceUnicodeList(fileList)
			baseDir     = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)
			
			if not os.path.isdir(baseDir):
				raise Exception(u"Base dir '%s' not found" % baseDir)
			
			if compression:
				compression = forceUnicodeLower(compression)
				if compression not in ('gzip', 'bzip2'):
					raise Exception(u"Compression '%s' not supported" % compression)
				self._compression = compression
			else:
				self._compression = None
			
			command = u'%s --no-recursion --create --files-from -' % System.which('tar')
			if dereference:
				command += ' --dereference'
			if   (self._compression == 'gzip'):
				command += ' | %s --rsyncable' % System.which('gzip')
			elif (self._compression == 'bzip2'):
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename
			
			self._create(fileList, baseDir, command)
			
		except Exception, e:
			raise Exception(u"Failed to create archive '%s': %s" % (self._filename, e))
	
class CpioArchive(BaseArchive):
	def __init__(self, filename):
		BaseArchive.__init__(self, filename)
	
	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise Exception(u"Archive file not found: '%s'" % self._filename)
			names = []
			cat = System.which('cat')
			if (self._compression == 'gzip'):
				cat = System.which('zcat')
			if (self._compression == 'bzip2'):
				cat = System.which('bzcat')
			for line in System.execute(u'%s "%s" | %s --quiet -it' % (cat, self._filename, System.which('cpio'))):
				if line:
					names.append(unicode(line))
			return names
		except Exception, e:
			raise Exception(u"Failed to get archive content '%s': %s" % (self._filename, e))
	
	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns   = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				os.mkdir(targetPath)
			
			cat = System.which('cat')
			if   (self._compression == 'gzip'):
				cat = System.which('zcat')
			elif (self._compression == 'bzip2'):
				cat = System.which('bzcat')
			
			include = u''
			for p in patterns:
				include += ' "%s"' % p
			
			curDir = os.path.abspath(os.getcwd())
			os.chdir(targetPath)
			try:
				System.execute(u'%s "%s" | %s --quiet -idum %s' % (cat, self._filename, System.which('cpio'), include))
			finally:
				os.chdir(curDir)
		except Exception, e:
			raise Exception(u"Failed to extract archive '%s': %s" % (self._filename, e))
	
	def create(self, fileList, baseDir='.', dereference=False, compression=None):
		try:
			fileList    = forceUnicodeList(fileList)
			baseDir     = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)
			
			if not os.path.isdir(baseDir):
				raise Exception(u"Base dir '%s' not found" % baseDir)
			
			if compression:
				compression = forceUnicodeLower(compression)
				if compression not in ('gzip', 'bzip2'):
					raise Exception(u"Compression '%s' not supported" % compression)
				self._compression = compression
			else:
				self._compression = None
			
			command = u'%s --quiet -o -H crc' % System.which('cpio')
			if dereference:
				command += ' --dereference'
			if   (self._compression == 'gzip'):
				command += ' | %s --rsyncable' % System.which('gzip')
			elif (self._compression == 'bzip2'):
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename
			
			self._create(fileList, baseDir, command)
			
		except Exception, e:
			raise Exception(u"Failed to create archive '%s': %s" % (self._filename, e))



def Archive(filename):
	filename = forceFilename(filename)
	Class = None
	fileType = getFileTye(filename)
	if   fileType.lower().startswith('posix tar archive'):
		Class = TarArchive
	elif fileType.lower().startswith('ascii cpio archive'):
		Class = CpioArchive
	elif filename.lower().endswith('tar.gz') or filename.lower().endswith('tar.gz'):
		Class = TarArchive
	elif filename.lower().endswith('cpio.gz') or filename.lower().endswith('cpio.gz'):
		Class = CpioArchive
	else:
		raise Exception(u"Failed to guess archive type of '%s'" % filename)
	return Class(filename)
	





























