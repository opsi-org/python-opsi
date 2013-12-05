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

__version__ = "4.0"

import locale
import os
import subprocess

if (os.name == 'posix'):
	import fcntl
	import magic

from OPSI.Logger import *
from OPSI import System
from OPSI.Types import *
from OPSI.Util import compareVersions

logger = Logger()


def getFileType(filename):
	if (os.name == 'nt'):
		raise NotImplementedError(u"getFileType() not implemented on windows")

	filename = forceFilename(filename)
	ms = magic.open(magic.MAGIC_NONE)
	ms.load()
	fileType = ms.file(filename)
	ms.close()
	return fileType


class BaseArchive(object):
	def __init__(self, filename, compression = None, progressSubject=None):
		self._filename = forceFilename(filename)
		self._progressSubject = progressSubject
		self._compression = None
		if compression:
			compression = forceUnicodeLower(compression)
			if not compression in ('gzip', 'bzip2'):
				raise Exception(u"Compression '%s' not supported" % compression)
			self._compression = compression
		elif os.path.exists(self._filename):
			fileType = getFileType(self._filename)
			if   fileType.lower().startswith('gzip compressed data'):
				self._compression = u'gzip'
			elif fileType.lower().startswith('bzip2 compressed data'):
				self._compression = u'bzip2'
			else:
				self._compression = None

	def getFilename(self):
		return self._filename

	def _extract(self, command, fileCount):
		try:
			logger.info(u"Executing: %s" % command )
			proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

			encoding = proc.stdout.encoding
			if not encoding:
				encoding = locale.getpreferredencoding()

			flags = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
			fcntl.fcntl(proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
			fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

			if self._progressSubject:
				self._progressSubject.setEnd(fileCount)
				self._progressSubject.setState(0)

			error = ''
			ret = None
			while ret is None:
				try:
					chunk = proc.stdout.read()
					if chunk:
						filesExtracted = chunk.count('\n')
						if (filesExtracted > 0):
							if self._progressSubject:
								self._progressSubject.addToState(filesExtracted)
				except:
					pass
				try:
					chunk = proc.stderr.read()
					if chunk:
						error = chunk
						filesExtracted = chunk.count('\n')
						if (filesExtracted > 0):
							if self._progressSubject:
								self._progressSubject.addToState(filesExtracted)
				except:
					time.sleep(0.001)
				ret = proc.poll()

			logger.info(u"Exit code: %s" % ret)

			if (ret != 0):
				error = error.decode(encoding, 'replace')
				logger.error(error)
				raise Exception(u"Command '%s' failed with code %s: %s" % (command, ret, error))
			if self._progressSubject:
				self._progressSubject.setState(fileCount)

		except Exception as e:
			logger.logException(e)
			raise

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

			flags = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
			fcntl.fcntl(proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
			flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
			fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

			if self._progressSubject:
				self._progressSubject.setEnd(len(fileList))
				self._progressSubject.setState(0)

			error = ''
			ret = None
			for f in fileList:
				if not f:
					continue
				if not os.path.exists(f):
					raise Exception(u"File '%s' not found" % f)
				# python 2.6:
				if f.startswith(baseDir):
					#f = os.path.relpath(f, baseDir)
					f = f[len(baseDir):]
					while f.startswith('/'):
						f = f[1:]
				logger.info(u"Adding file '%s'" % f)
				proc.stdin.write("%s\n" % f.encode(encoding))

				try:
					chunk = proc.stdout.read()
					if chunk:
						filesAdded = chunk.count('\n')
						if (filesAdded > 0):
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except:
					pass
				try:
					chunk = proc.stderr.read()
					if chunk:
						error += chunk
						filesAdded = chunk.count('\n')
						if (filesAdded > 0):
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except:
					time.sleep(0.001)

			proc.stdin.close()

			while ret is None:
				ret = proc.poll()
				try:
					chunk = proc.stdout.read()
				except:
					pass
				try:
					chunk = proc.stderr.read()
					if chunk:
						if self._progressSubject:
							self._progressSubject.addToState(chunk.count('\n'))
						error += chunk
				except:
					pass

			logger.info(u"Exit code: %s" % ret)

			if (ret != 0):
				error = error.decode(encoding, 'replace')
				logger.error(error)
				raise Exception(u"Command '%s' failed with code %s: %s" % (command, ret, error))
			if self._progressSubject:
				self._progressSubject.setState(len(fileList))
		finally:
			os.chdir(curDir)


class PigzMixin(object):
	@property
	def pigz_detected(self):
		if not hasattr(self, '_pigz_detected'):
			self._pigz_detected = self.is_pigz_available()

		return self._pigz_detected

	@staticmethod
	def is_pigz_available():
		def is_correct_pigz_version():
			ver = System.execute('pigz --version')[0][5:]

			logger.debug('Detected pigz version: %s' % (ver, ))
			versionMatches = compareVersions(ver, '>=', '2.2.3')
			logger.debug('pigz version is compatible? %s' % (versionMatches))
			return versionMatches

		try:
			System.which('pigz')
			logger.debug(u'Detected "pigz".')

			return is_correct_pigz_version()
		except Exception:
			logger.debug(u'Did not detect "pigz".')
			return False


class TarArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression = None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise Exception(u"Archive file not found: '%s'" % self._filename)
			names = []
			options = u''
			if   (self._compression == 'gzip'):
				if self.pigz_detected:
					options += u'--use-compress-program=pigz'
				else:
					options += u'--gunzip'
			elif (self._compression == 'bzip2'):
				options += u'--bzip2'
			for line in System.execute(u'%s %s --list --file "%s"' % (System.which('tar'), options, self._filename)):
				if line:
					names.append(unicode(line))
			return names
		except Exception as e:
			raise Exception(u"Failed to get archive content '%s': %s" % (self._filename, e))

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns   = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as e:
					raise Exception(u"Failed to create target dir '%s': %s" % (targetPath, e))

			options = u''
			if   (self._compression == 'gzip'):
				if self.pigz_detected:
					options += u'--use-compress-program=pigz'
				else:
					options += u'--gunzip'
			elif (self._compression == 'bzip2'):
				options += u'--bzip2'

			fileCount = 0
			for f in self.content():
				match = False
				if not patterns:
					match = True
				else:
					for p in patterns:
						try:
							p = p.replace('*', '.*')
							if re.search(p, f):
								match = True
								break
							fileCount += 1
						except Exception as e:
							raise Exception(u"Bad pattern '%s': %s" % (p, e))
				if match:
					fileCount += 1
				else:
					options += u' --exclude="%s"' % f

			command = u'%s %s --directory "%s" --extract --verbose --file "%s"' % (System.which('tar'), options, targetPath, self._filename)
			self._extract(command, fileCount)

		except Exception as e:
			raise Exception(u"Failed to extract archive '%s': %s" % (self._filename, e))

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList    = forceUnicodeList(fileList)
			baseDir     = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise Exception(u"Base dir '%s' not found" % baseDir)

			command = u'%s --no-recursion --verbose --create --files-from -' % System.which('tar')
			if dereference:
				command += ' --dereference'
			if   (self._compression == 'gzip'):
				if self.pigz_detected:
					command += ' | %s --rsyncable' % System.which('pigz')
				else:
					command += ' | %s --rsyncable' % System.which('gzip')
			elif (self._compression == 'bzip2'):
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename

			self._create(fileList, baseDir, command)

		except Exception as e:
			raise Exception(u"Failed to create archive '%s': %s" % (self._filename, e))


class CpioArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression = None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise Exception(u"Archive file not found: '%s'" % self._filename)
			names = []
			cat = System.which('cat')
			if (self._compression == 'gzip'):
				if self.pigz_detected:
					cat = u'%s -cd' % (System.which('pigz'), )
				else:
					cat = System.which('zcat')
			if (self._compression == 'bzip2'):
				cat = System.which('bzcat')
			for line in System.execute(u'%s "%s" | %s --quiet -it' % (cat, self._filename, System.which('cpio'))):
				if line:
					names.append(unicode(line))
			return names
		except Exception as e:
			raise Exception(u"Failed to get archive content '%s': %s" % (self._filename, e))

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns   = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as e:
					raise Exception(u"Failed to create target dir '%s': %s" % (targetPath, e))

			cat = System.which('cat')
			if   (self._compression == 'gzip'):
				if self.pigz_detected:
					cat = u'%s -cd' % (System.which('pigz'), )
				else:
					cat = System.which('zcat')
			elif (self._compression == 'bzip2'):
				cat = System.which('bzcat')

			fileCount = 0
			for f in self.content():
				match = False
				if not patterns:
					match = True
				else:
					for p in patterns:
						try:
							p = p.replace('*', '.*')
							if re.search(p, f):
								match = True
								break
							fileCount += 1
						except Exception as e:
							raise Exception(u"Bad pattern '%s': %s" % (p, e))
				if match:
					fileCount += 1

			include = u''
			for p in patterns:
				include += ' "%s"' % p

			curDir = os.path.abspath(os.getcwd())
			os.chdir(targetPath)
			try:
				command = u'%s "%s" | %s --quiet -idumv %s' % (cat, self._filename, System.which('cpio'), include)
				self._extract(command, fileCount)
			finally:
				os.chdir(curDir)
		except Exception as e:
			raise Exception(u"Failed to extract archive '%s': %s" % (self._filename, e))

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList    = forceUnicodeList(fileList)
			baseDir     = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise Exception(u"Base dir '%s' not found" % baseDir)

			command = u'%s --quiet -v -o -H crc' % System.which('cpio')
			if dereference:
				command += ' --dereference'
			if   (self._compression == 'gzip'):
				if self.pigz_detected:
					command += ' | %s --rsyncable' % System.which('pigz')
				else:
					command += ' | %s --rsyncable' % System.which('gzip')
			elif (self._compression == 'bzip2'):
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename

			self._create(fileList, baseDir, command)

		except Exception as e:
			raise Exception(u"Failed to create archive '%s': %s" % (self._filename, e))


def Archive(filename, format=None, compression=None, progressSubject=None):
	filename = forceFilename(filename)
	Class = None
	if format:
		format = forceUnicodeLower(format)
		if not format in ('tar', 'cpio'):
			raise Exception(u"Unsupported format '%s'" % format)
		if   (format == 'tar'):
			Class = TarArchive
		elif (format == 'cpio'):
			Class = CpioArchive

	elif os.path.exists(filename):
		fileType = getFileType(filename)
		if   (fileType.lower().find('tar archive') != -1):
			Class = TarArchive
		elif (fileType.lower().find('cpio archive') != -1):
			Class = CpioArchive
		elif filename.lower().endswith('tar') or filename.lower().endswith('tar.gz'):
			Class = TarArchive
		elif filename.lower().endswith('cpio') or filename.lower().endswith('cpio.gz'):
			Class = CpioArchive
	if not Class:
		raise Exception(u"Failed to guess archive type of '%s'" % filename)
	return Class(filename = filename, compression = compression, progressSubject = progressSubject)
