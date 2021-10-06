# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Working with archives.

This include functionality for using Tar-Files and their compression.


.. versionadded:: 4.0.5.1
	Control the usage of pigz via ``PIGZ_ENABLED``
"""

import locale
import os
import re
import subprocess
import time
if os.name == 'posix':
	import fcntl

import OPSI.Util.File.Opsi
from OPSI import System
from OPSI.Types import forceBool, forceFilename, forceUnicodeList, forceUnicodeLower
from OPSI.Util import compareVersions
from OPSI.Util.Path import cd

from opsicommon.logging import logger

try:
	PIGZ_ENABLED = OPSI.Util.File.Opsi.OpsiConfFile().isPigzEnabled()
except IOError:
	PIGZ_ENABLED = True


def getFileType(filename):
	filename = forceFilename(filename)
	with open(filename, "rb") as f:
		head = f.read(257+5)

	if head[:3] == b"\x1f\x8b\x08" or head[:8] == b"\x5c\x30\x33\x37\x5c\x32\x31\x33":
		return ".gz"
	if head[:3] == b"\x42\x5a\x68":
		return ".bzip2"
	if head[:5] == b"\x30\x37\x30\x37\x30":
		return ".cpio"
	if head[257:257+5] == b"\x75\x73\x74\x61\x72":
		return ".tar"
	raise NotImplementedError("getFileType only accepts .gz .bzip2 .cpio .tar archive types.")


class BaseArchive:
	def __init__(self, filename, compression=None, progressSubject=None):
		self._filename = forceFilename(filename)
		self._progressSubject = progressSubject
		self._compression = None
		if compression:
			compression = forceUnicodeLower(compression)
			if compression not in ('gzip', 'bzip2'):
				raise ValueError("Compression '%s' not supported" % compression)
			self._compression = compression
		elif os.path.exists(self._filename):
			fileType = getFileType(self._filename)
			logger.debug("Identified fileType %s for file %s", fileType, self._filename)
			if "gz" in fileType.lower():
				self._compression = 'gzip'
			elif "bzip2" in fileType.lower():
				self._compression = 'bzip2'
			else:
				self._compression = None


	def getFilename(self):
		return self._filename

	def _extract(self, command, fileCount):
		try:
			logger.info("Executing: %s", command)
			proc = subprocess.Popen(
				command,
				shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
			)

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
				except Exception:  # pylint: disable=broad-except
					pass
				try:
					chunk = proc.stderr.read()
					if chunk:
						error = chunk
						filesExtracted = chunk.count('\n')
						if filesExtracted > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesExtracted)
				except Exception:  # pylint: disable=broad-except
					time.sleep(0.001)
				ret = proc.poll()

			logger.info("Exit code: %s", ret)

			if ret != 0:
				logger.error(error)
				raise RuntimeError("Command '%s' failed with code %s: %s" % (command, ret, error))

			if self._progressSubject:
				self._progressSubject.setState(fileCount)
		except Exception as err:
			logger.error(err, exc_info=True)
			raise

	def _create(self, fileList, baseDir, command):
		baseDir = os.path.abspath(forceFilename(baseDir))
		if not os.path.isdir(baseDir):
			raise IOError("Base dir '%s' not found" % baseDir)

		with cd(baseDir):
			logger.info("Executing: %s", command)
			proc = subprocess.Popen(command,
				shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
				stderr=subprocess.PIPE
			)

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
					raise IOError(f"File '{filename}' not found")
				if filename.startswith(baseDir):
					filename = filename[len(baseDir):]
					while filename.startswith('/'):
						filename = filename[1:]
				logger.info("Adding file '%s'", filename)
				proc.stdin.write(("%s\n" % filename).encode())

				try:
					chunk = proc.stdout.read()
					if chunk:
						filesAdded = chunk.count('\n')
						if filesAdded > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except Exception:  # pylint: disable=broad-except
					pass

				try:
					chunk = proc.stderr.read()
					if chunk:
						error += chunk
						filesAdded = chunk.count('\n')
						if filesAdded > 0:
							if self._progressSubject:
								self._progressSubject.addToState(filesAdded)
				except Exception:  # pylint: disable=broad-except
					time.sleep(0.001)

			proc.stdin.close()

			while ret is None:
				ret = proc.poll()
				try:
					chunk = proc.stdout.read()
				except Exception:  # pylint: disable=broad-except
					pass

				try:
					chunk = proc.stderr.read()
					if chunk:
						if self._progressSubject:
							self._progressSubject.addToState(chunk.count('\n'))
						error += chunk
				except Exception:  # pylint: disable=broad-except
					pass

			logger.info("Exit code: %s", ret)

			if ret != 0:
				error = error.decode()
				logger.error(error)
				raise RuntimeError("Command '%s' failed with code %s: %s" % (command, ret, error))
			if self._progressSubject:
				self._progressSubject.setState(len(fileList))


class PigzMixin:
	@property
	def pigz_detected(self):
		if not hasattr(self, '_pigz_detected'):
			self._pigz_detected = self.is_pigz_available()

		return self._pigz_detected

	@staticmethod
	def is_pigz_available():
		def is_correct_pigz_version():
			ver = System.execute('pigz --version')[0][5:]

			logger.debug('Detected pigz version: %s', ver)
			versionMatches = compareVersions(ver, '>=', '2.2.3')
			logger.debug('pigz version is compatible? %s', versionMatches)
			return versionMatches

		if not PIGZ_ENABLED:
			return False

		try:
			System.which('pigz')
			logger.debug('Detected "pigz".')

			return is_correct_pigz_version()
		except Exception:  # pylint: disable=broad-except
			logger.debug('Did not detect "pigz".')
			return False


class TarArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression=None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise IOError("Archive file not found: '%s'" % self._filename)
			names = []
			options = ''
			if self._compression == 'gzip':
				if self.pigz_detected:
					options += '--use-compress-program=pigz'
				else:
					options += '--gunzip'
			elif self._compression == 'bzip2':
				options += '--bzip2'

			for line in System.execute('%s %s --list --file "%s"' % (System.which('tar'), options, self._filename)):
				if line:
					names.append(line)

			return names
		except Exception as err:
			raise RuntimeError(f"Failed to get archive content '{self._filename}': {err}") from err

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as err:  # pylint: disable=broad-except
					raise IOError(f"Failed to create target dir '{targetPath}': {err}") from err

			options = ''
			if self._compression == 'gzip':
				if self.pigz_detected:
					options += '--use-compress-program=pigz'
				else:
					options += '--gunzip'
			elif self._compression == 'bzip2':
				options += '--bzip2'

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
						except Exception as err:  # pylint: disable=broad-except
							raise ValueError(f"Bad pattern '{pattern}': {err}") from err

				if match:
					fileCount += 1
				else:
					options += ' --exclude="%s"' % filename

			command = '%s %s --directory "%s" --extract --verbose --file "%s"' % (System.which('tar'), options, targetPath, self._filename)
			self._extract(command, fileCount)
		except Exception as err:  # pylint: disable=broad-except
			raise RuntimeError(f"Failed to extract archive '{self._filename}': {err}") from err

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList = forceUnicodeList(fileList)
			baseDir = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise IOError("Base dir '%s' not found" % baseDir)

			command = '%s --no-recursion --verbose --create --files-from -' % System.which('tar')
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
		except Exception as err:  # pylint: disable=broad-except
			raise RuntimeError(f"Failed to create archive '{self._filename}': {err}") from err


class CpioArchive(BaseArchive, PigzMixin):
	def __init__(self, filename, compression=None, progressSubject=None):
		BaseArchive.__init__(self, filename, compression, progressSubject)

	def content(self):
		try:
			if not os.path.exists(self._filename):
				raise IOError("Archive file not found: '%s'" % self._filename)

			cat = System.which('cat')
			if self._compression == 'gzip':
				if self.pigz_detected:
					cat = '{pigz} --stdout --decompress'.format(pigz=System.which('pigz'))
				else:
					cat = System.which('zcat')
			elif self._compression == 'bzip2':
				cat = System.which('bzcat')

			return [line for line in
					System.execute('{cat} "{filename}" | {cpio} --quiet --extract --list'.format(cat=cat, filename=self._filename, cpio=System.which('cpio')))
					if line]
		except Exception as err:  # pylint: disable=broad-except
			raise RuntimeError(f"Failed to get archive content '{self._filename}': {err}") from err

	def extract(self, targetPath='.', patterns=[]):
		try:
			targetPath = os.path.abspath(forceFilename(targetPath))
			patterns = forceUnicodeList(patterns)
			if not os.path.isdir(targetPath):
				try:
					os.mkdir(targetPath)
				except Exception as err:  # pylint: disable=broad-except
					raise IOError(f"Failed to create target dir '{targetPath}': {err}") from err

			cat = System.which('cat')
			if self._compression == 'gzip':
				if self.pigz_detected:
					cat = '%s --stdout --decompress' % (System.which('pigz'), )
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
						except Exception as err:  # pylint: disable=broad-except
							raise ValueError(f"Bad pattern '{pattern}': {err}") from err
				if match:
					fileCount += 1

			include = ' '.join('"%s"' % pattern for pattern in patterns)

			with cd(targetPath):
				command = '%s "%s" | %s --quiet --extract --make-directories --unconditional --preserve-modification-time --verbose --no-preserve-owner %s' % (cat, self._filename, System.which('cpio'), include)
				self._extract(command, fileCount)
		except Exception as err:  # pylint: disable=broad-except
			raise RuntimeError(f"Failed to extract archive '{self._filename}': {err}") from err

	def create(self, fileList, baseDir='.', dereference=False):
		try:
			fileList = forceUnicodeList(fileList)
			baseDir = os.path.abspath(forceFilename(baseDir))
			dereference = forceBool(dereference)

			if not os.path.isdir(baseDir):
				raise IOError(f"Base dir '{baseDir}' not found")

			command = '%s --create --quiet --verbose --format crc' % System.which('cpio')
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
		except Exception as err:  # pylint: disable=broad-except
			raise RuntimeError(f"Failed to create archive '{self._filename}': {err}") from err


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
			raise ValueError("Unsupported format '%s'" % format)

	elif os.path.exists(filename):
		fileType = getFileType(filename)
		logger.debug("Identified fileType %s for file %s", fileType, filename)
		if 'tar' in fileType.lower():
			Class = TarArchive
		elif 'cpio' in fileType.lower():
			Class = CpioArchive
		elif filename.lower().endswith(('tar', 'tar.gz')):
			Class = TarArchive
		elif filename.lower().endswith(('cpio', 'cpio.gz')):
			Class = CpioArchive

	if not Class:
		raise RuntimeError("Failed to guess archive type of '%s'" % filename)

	return Class(filename=filename, compression=compression, progressSubject=progressSubject)
