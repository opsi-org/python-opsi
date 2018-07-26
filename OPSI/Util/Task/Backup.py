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
Utilites to backup configuration of an opsi system.

:copyright: uib GmbH <info@uib.de>
:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import bz2
import fcntl
import gettext
import gzip
import os
import shutil
import sys
import termios
from contextlib import closing

from OPSI.Types import (forceList, forceUnicode, OpsiBackupFileError,
	OpsiBackupBackendNotFound, OpsiError)
from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Util.File.Opsi import OpsiBackupArchive
from OPSI.System.Posix import SysInfo

logger = Logger()

try:
	translation = gettext.translation('opsi-utils', '/usr/share/locale')
	_ = translation.ugettext
except Exception as error:
	logger.error(u"Locale not found: {0}".format(error))

	def _(string):
		""" Function for translating text. """
		return string


WARNING_DIFF = _(u"""WARNING: Your system config is different from the one recorded with this backup.
This means the backup was probably taken for another machine and restoring it might leave this opsi installation unusable.
Do you wish to continue? [y/n]""")

WARNING_SYSCONFIG = _(u"""WARNING: A problem occurred while reading the sysconfig: %s
This means the backup was probably taken for another machine and restoring it might leave this opsi installation unusable.
Do you wish to continue? [y/n]""")


class OpsiBackup(object):

	def __init__(self, stdout=None):
		if stdout is None:
			self.stdout = sys.stdout
		else:
			self.stdout = stdout

	def _getArchive(self, mode, file=None, compression=None):
		fileobj = None
		if file and os.path.exists(file):
			try:
				fileobj = gzip.GzipFile(file, mode)
				fileobj.read(1)
				fileobj.seek(0)
				compression = "gz"
			except IOError:
				fileobj = None

			try:
				fileobj = bz2.BZ2File(file, mode)
				fileobj.read(1)
				fileobj.seek(0)
				compression = "bz2"
			except IOError:
				fileobj = None

		if compression not in ('none', None):
			mode = ":".join((mode, compression))

		return OpsiBackupArchive(name=file, mode=mode, fileobj=fileobj)

	def _create(self, destination=None, mode="raw", backends=["auto"], no_configuration=False, compression="bz2", flush_logs=False, **kwargs):
		if "all" in backends:
			backends = ["all"]

		if "auto" in backends:
			backends = ["auto"]

		if destination and os.path.exists(destination):
			file = None
		else:
			file = destination

		archive = self._getArchive(file=file, mode="w", compression=compression)

		try:
			if destination is None:
				name = archive.name.split(os.sep)[-1]
			else:
				name = archive.name
			logger.notice(u"Creating backup archive %s" % name)

			if mode == "raw":
				for backend in backends:
					if backend in ("file", "all", "auto"):
						logger.debug(u"Backing up file backend.")
						archive.backupFileBackend(auto=("auto" in backends))
					if backend in ("mysql", "all", "auto"):
						logger.debug(u"Backing up mysql backend.")
						archive.backupMySQLBackend(flushLogs=flush_logs, auto=("auto" in backends))
					if backend in ("dhcp", "all", "auto"):
						logger.debug(u"Backing up dhcp configuration.")
						archive.backupDHCPBackend(auto=("auto" in backends))

			if not no_configuration:
				logger.debug(u"Backing up opsi configuration.")
				archive.backupConfiguration()

			archive.close()

			self._verify(archive.name)

			filename = archive.name.split(os.sep)[-1]
			if not destination:
				destination = os.getcwdu()

			if os.path.isdir(destination):
				destination = os.path.join(destination, filename)

			shutil.move(archive.name, destination)

			logger.notice(u"Backup complete")
		except Exception as error:
			os.remove(archive.name)
			logger.logException(error, LOG_DEBUG)
			raise error

	def _verify(self, file, **kwargs):
		"""
		Verify a backup.

		:return: 0 if everything is okay, 1 if there was a failure.
		:returntype: int
		"""
		files = forceList(file)

		result = 0

		for fileName in files:
			with closing(self._getArchive(mode="r", file=fileName)) as archive:
				logger.info(u"Verifying archive %s" % fileName)
				try:
					archive.verify()
					logger.notice(u"Archive is OK.")
				except OpsiBackupFileError as error:
					logger.error(error)
					result = 1

		return result

	def _verifySysconfig(self, archive):
		def ask(question=WARNING_DIFF):
			"""
			Ask for a yes or no.

			Returns ``True`` if the answer is ``Yes``, false otherwise.
			"""
			fd = sys.stdin.fileno()

			oldterm = termios.tcgetattr(fd)
			newattr = termios.tcgetattr(fd)
			newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
			termios.tcsetattr(fd, termios.TCSANOW, newattr)

			oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
			fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

			self.stdout.write(question)

			try:
				while True:
					try:
						firstCharacter = sys.stdin.read(1)
						return (forceUnicode(firstCharacter) in (u"y", u"Y"))
					except IOError:
						pass
			finally:
				termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
				fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

		try:
			if self._getDifferencesInSysConfig(archive.sysinfo, SysInfo()):
				return ask(WARNING_DIFF)
		except OpsiError as error:
			return ask(WARNING_SYSCONFIG % unicode(error))

		return True

	def _getDifferencesInSysConfig(self, archiveSysInfo, sysInfo=None):
		"""
		Checks system informations for differences and returns the findings.

		:param archiveSysInfo: The information from the archive.
		:type archiveSysInfo: dict
		:param sysInfo: The information from the system. Defaults to SysInfo().
		:type sysInfo: OPSI.System.Posix.SysInfo
		"""
		if sysInfo is None:
			sysInfo = SysInfo()

		archiveInfo = archiveSysInfo

		diff = {}

		for key, value in archiveInfo.iteritems():
			sysValue = str(getattr(sysInfo, key, None))
			if sysValue.strip() != value.strip():
				logger.debug(
					'Found difference (System != Archive) at "{key}": '
					'"{0}" vs. "{1}"'.format(
						sysValue,
						value,
						key=key
					)
				)
				diff[key] = value

		return diff

	def _restore(self, file, mode="raw", backends=[], configuration=True, force=False, **kwargs):
		if not backends:
			backends = []

		if "all" in backends:
			backends = ["all"]

		auto = "auto" in backends

		logger.debug("Backends for restore: {}", backends)

		with closing(self._getArchive(file=file[0], mode="r")) as archive:
			self._verify(archive.name)

			if force or self._verifySysconfig(archive):
				logger.notice(u"Restoring data from backup archive %s." % archive.name)

				functions = []
				if configuration:
					if not archive.hasConfiguration() and not force:
						raise OpsiBackupFileError(u"Backup file does not contain configuration data.")

					logger.debug(u"Adding restore of opsi configuration.")
					functions.append(lambda x: archive.restoreConfiguration())

				if mode == "raw":
					backendMapping = {
						"file": (archive.hasFileBackend, archive.restoreFileBackend),
						"mysql": (archive.hasMySQLBackend, archive.restoreMySQLBackend),
						"dhcp": (archive.hasDHCPBackend, archive.restoreDHCPBackend),
					}

					for backend in backends:
						for name, handlingFunctions in backendMapping.items():
							if backend in (name, "all", "auto"):
								dataExists, restoreData = handlingFunctions

								if not dataExists() and not force:
									if auto:
										logger.debug(u"No backend data for {0} - skipping.", name)
										continue  # Don't attempt to restore.
									else:
										raise OpsiBackupFileError(u"Backup file does not contain {0} backend data.".format(name))

								logger.debug(u"Adding restore of {0} backend.", name)
								functions.append(restoreData)

				try:
					for restoreFunction in functions:
						logger.debug2(u"Running restoration function {0!r}", restoreFunction)
						restoreFunction(auto)
				except OpsiBackupBackendNotFound as error:
					logger.logException(error, LOG_DEBUG)
					logger.debug("Restoring with {0!r} failed: {1}", restoreFunction, error)

					if not auto:
						raise error
				except Exception as error:
					logger.logException(error, LOG_DEBUG)
					logger.error(u"Failed to restore data from archive %s: %s. Aborting." % (archive.name, error))
					raise error

				logger.notice(u"Restoration complete")
