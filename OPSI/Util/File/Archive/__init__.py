# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2018 uib GmbH <info@uib.de>

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
Working with archives.

This include functionality for using Tar-Files and their compression.


.. versionadded:: 4.0.5.1
	Control the usage of pigz via ``PIGZ_ENABLED``

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import locale
import os
import re
import subprocess
import time
from contextlib import closing

import OPSI.Util.File.Opsi
from OPSI.Logger import Logger
from OPSI import System
from OPSI.Types import forceBool, forceFilename, forceUnicodeList, forceUnicodeLower
from OPSI.Util import compareVersions

if os.name == 'posix':
	import fcntl
	import magic

logger = Logger()

try:
	PIGZ_ENABLED = OPSI.Util.File.Opsi.OpsiConfFile().isPigzEnabled()
except IOError:
	PIGZ_ENABLED = True


def getFileType(filename):
	if os.name == 'nt':
		raise NotImplementedError(u"getFileType() not implemented on windows")

	filename = forceFilename(filename)
	with closing(magic.open(magic.MAGIC_SYMLINK)) as ms:
		ms.load()
		return ms.file(filename)


class BaseArchive(object):
	def __init__(self, filename, compression=None, progressSubject=None):
		self._filename = forceFilename(filename)
		self._progressSubject = progressSubject
		self._compression = None
		if compression:
			compression = forceUnicodeLower(compression)
			if compression not in ('gzip', 'bzip2'):
				raise ValueError(u"Compression '%s' not supported" % compression)
			self._compression = compression
		elif os.path.exists(self._filename):
			fileType = getFileType(self._filename)
			if fileType.lower().startswith('gzip compressed data'):
				self._compression = u'gzip'
			elif fileType.lower().startswith('bzip2 compressed data'):
				self._compression = u'bzip2'
			else:
				self._compression = None

	def getFilename(self):
		return self._filename

	def _extract(self, command, fileCount):
		try:
			logger.info(u"Executing: %s" % command)
			proc = subprocess.Popen(
				command,
				shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
			)

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
						if filesExtracted > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesExtracted)
				except Exception:
					pass
				try:
					chunk = proc.stderr.read()
					if chunk:
						error = chunk
						filesExtracted = chunk.count('\n')
						if filesExtracted > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesExtracted)
				except Exception:
					time.sleep(0.001)
				ret = proc.poll()

			logger.info(u"Exit code: %s" % ret)

			if ret != 0:
				error = error.decode(encoding, 'replace')
				logger.error(error)
				raise RuntimeError(u"Command '%s' failed with code %s: %s" % (command, ret, error))

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
				raise IOError(u"Base dir '%s' not found" % baseDir)
			os.chdir(baseDir)

			logger.info(u"Executing: %s" % command)
			proc = subprocess.Popen(command,
				shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
				stderr=subprocess.PIPE
			)

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
			for filename in fileList:
				if not filename:
					continue
				if not os.path.exists(filename):
					raise IOError(u"File '%s' not found" % filename)
				# python 2.6:
				if filename.startswith(baseDir):
					#f = os.path.relpath(f, baseDir)
					filename = filename[len(baseDir):]
					while filename.startswith('/'):
						filename = filename[1:]
				logger.info(u"Adding file '%s'" % filename)
				proc.stdin.write("%s\n" % filename.encode(encoding))

				try:
					chunk = proc.stdout.read()
					if chunk:
						filesAdded = chunk.count('\n')
						if filesAdded > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except Exception:
					pass

				try:
					chunk = proc.stderr.read()
					if chunk:
						error += chunk
						filesAdded = chunk.count('\n')
						if filesAdded > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except Exception:
					time.sleep(0.001)

			proc.stdin.close()

			while ret is None:
				ret = proc.poll()
				try:
					chunk = proc.stdout.read()
				except Exception:
					pass

				try:
					chunk = proc.stderr.read()
					if chunk:
						if self._progressSubject:
							self._progressSubject.addToState(chunk.count('\n'))
						error += chunk
				except Exception:
					pass

			logger.info(u"Exit code: %s" % ret)

			if ret != 0:
				error = error.decode(encoding, 'replace')
				logger.error(error)
				raise RuntimeError(u"Command '%s' failed with code %s: %s" % (command, ret, error))
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

		if not PIGZ_ENABLED:
			return False

		try:
			System.which('pigz')
			logger.debug(u'Detected "pigz".')

			return is_correct_pigz_version()
		except Exception:
			logger.debug(u'Did not detect "pigz".')
			return False


class TarArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression=None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise IOError(u"Archive file not found: '%s'" % self._filename)
			names = []
			options = u''
			if self._compression == 'gzip':
				if self.pigz_detected:
					options += u'--use-compress-program=pigz'
				else:
					options += u'--gunzip'
			elif self._compression == 'bzip2':
				options += u'--bzip2'

			for line in System.execute(u'%s %s --list --file "%s"' % (System.which('tar'), options, self._filename)):
				if line:
					names.append(unicode(line))

			return names
		except Exception as e:
			raise RuntimeError(u"Failed to get archive content '%s': %s" % (self._filename, e))

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as e:
					raise IOError(u"Failed to create target dir '%s': %s" % (targetPath, e))

			options = u''
			if self._compression == 'gzip':
				if self.pigz_detected:
					options += u'--use-compress-program=pigz'
				else:
					options += u'--gunzip'
			elif self._compression == 'bzip2':
				options += u'--bzip2'

			fileCount = 0
			for filename in self.content():
				match = False
				if not patterns:
					match = True
				else:
					for pattern in patterns:
						try:
							pattern = pattern.replace('*', '.*')
							if re.search(pattern, filename):
								match = True
								break
							fileCount += 1
						except Exception as e:
							raise ValueError(u"Bad pattern '%s': %s" % (pattern, e))

				if match:
					fileCount += 1
				else:
					options += u' --exclude="%s"' % filename

			command = u'%s %s --directory "%s" --extract --verbose --file "%s"' % (System.which('tar'), options, targetPath, self._filename)
			self._extract(command, fileCount)
		except Exception as e:
			raise RuntimeError(u"Failed to extract archive '%s': %s" % (self._filename, e))

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList = forceUnicodeList(fileList)
			baseDir = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise IOError(u"Base dir '%s' not found" % baseDir)

			command = u'%s --no-recursion --verbose --create --files-from -' % System.which('tar')
			if dereference:
				command += ' --dereference'
			if self._compression == 'gzip':
				if self.pigz_detected:
					command += ' | %s --rsyncable' % System.which('pigz')
				else:
					command += ' | %s --rsyncable' % System.which('gzip')
			elif self._compression == 'bzip2':
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename

			self._create(fileList, baseDir, command)
		except Exception as e:
			raise RuntimeError(u"Failed to create archive '%s': %s" % (self._filename, e))


class CpioArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression=None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise IOError(u"Archive file not found: '%s'" % self._filename)

			cat = System.which('cat')
			if self._compression == 'gzip':
				if self.pigz_detected:
					cat = u'{pigz} --create --diff'.format(pigz=System.which('pigz'))
				else:
					cat = System.which('zcat')
			elif self._compression == 'bzip2':
				cat = System.which('bzcat')

			return [unicode(line) for line in
					System.execute(u'{cat} "{filename}" | {cpio} --quiet --extract --list --no-preserve-owner'.format(cat=cat, filename=self._filename, cpio=System.which('cpio')))
					if line]
		except Exception as e:
			raise RuntimeError(u"Failed to get archive content '%s': %s" % (self._filename, e))

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as e:
					raise IOError(u"Failed to create target dir '%s': %s" % (targetPath, e))

			cat = System.which('cat')
			if self._compression == 'gzip':
				if self.pigz_detected:
					cat = u'%s --create --diff' % (System.which('pigz'), )
				else:
					cat = System.which('zcat')
			elif self._compression == 'bzip2':
				cat = System.which('bzcat')

			fileCount = 0
			for filename in self.content():
				match = False
				if not patterns:
					match = True
				else:
					for pattern in patterns:
						try:
							pattern = pattern.replace('*', '.*')
							if re.search(pattern, filename):
								match = True
								break
							fileCount += 1
						except Exception as e:
							raise ValueError(u"Bad pattern '%s': %s" % (pattern, e))
				if match:
					fileCount += 1

			include = ' '.join('"%s"' % pattern for pattern in patterns)

			curDir = os.path.abspath(os.getcwd())
			os.chdir(targetPath)
			try:
				command = u'%s "%s" | %s --quiet --extract --make-directories --unconditional --preserve-modification-time --verbose %s' % (cat, self._filename, System.which('cpio'), include)
				self._extract(command, fileCount)
			finally:
				os.chdir(curDir)
		except Exception as e:
			raise RuntimeError(u"Failed to extract archive '%s': %s" % (self._filename, e))

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList = forceUnicodeList(fileList)
			baseDir = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise IOError(u"Base dir '%s' not found" % baseDir)

			command = u'%s --create --quiet --verbose --format crc' % System.which('cpio')
			if dereference:
				command += ' --dereference'
			if self._compression == 'gzip':
				if self.pigz_detected:
					command += ' | %s --rsyncable' % System.which('pigz')
				else:
					command += ' | %s --rsyncable' % System.which('gzip')
			elif self._compression == 'bzip2':
				command += ' | %s' % System.which('bzip2')
			command += ' > "%s"' % self._filename

			self._create(fileList, baseDir, command)
		except Exception as e:
			raise RuntimeError(u"Failed to create archive '%s': %s" % (self._filename, e))


def Archive(filename, format=None, compression=None, progressSubject=None):
	filename = forceFilename(filename)
	Class = None
	if format:
		format = forceUnicodeLower(format)
		if format == 'tar':
			Class = TarArchive
		elif format == 'cpio':
			Class = CpioArchive
		else:
			raise ValueError(u"Unsupported format '%s'" % format)

	elif os.path.exists(filename):
		fileType = getFileType(filename)
		if 'tar archive' in fileType.lower():
			Class = TarArchive
		elif 'cpio archive' in fileType.lower():
			Class = CpioArchive
		elif filename.lower().endswith(('tar', 'tar.gz')):
			Class = TarArchive
		elif filename.lower().endswith(('cpio', 'cpio.gz')):
			Class = CpioArchive

	if not Class:
		raise RuntimeError(u"Failed to guess archive type of '%s'" % filename)

	return Class(filename=filename, compression=compression, progressSubject=progressSubject)
