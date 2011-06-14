# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Util - Task =
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
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = (0,0)
__verstr__ = ".".join([str(i) for i in __version__])

import sys, types, os, termios, fcntl, gettext, bz2, gzip, shutil

from OPSI.Types import *
from OPSI.Util import argparse
from OPSI.Util.Collections import DefaultList
from OPSI.Logger import *
from OPSI.Util.File.Opsi import OpsiBackupArchive
from OPSI.System.Posix import SysInfo

logger = Logger()

try:
	t = gettext.translation('opsi-utils', '/usr/share/locale')
	_ = t.ugettext
except Exception, e:
	logger.error(u"Locale not found: %s" % e)
	def _(string):
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
			except IOError:	fileobj=None
			try:
				fileobj = bz2.BZ2File(file, mode)
				fileobj.read(1)
				fileobj.seek(0)
				compression = "bz2"
			except IOError:	fileobj=None
	
		if compression not in ('none', None):
			mode = ":".join((mode, compression)) 
		
		return OpsiBackupArchive(name=file, mode=mode, fileobj=fileobj)


	def _create(self, destination=None, mode="raw", backends=["auto"], no_configuration=False, compression="bz2", flush_logs=False, **kwargs):

		
		if "all" in backends:
			backends = ["all"]
			
		if "auto" in backends:
			backends = ["auto"]


		if destination and os.path.exists(destination) and not os.path.isfile(destination):
			file = None
		else:
			file = destination
		
		archive = self._getArchive(file=file, mode="w", compression=compression)
		
		try:
			if destination is None:
				name = archive.name.split(os.sep)[-1]
			else:
				name = archive.name
			logger.notice(_(u"Creating backup archive %s" % name))
			
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
					#TODO: implement ldap/univention backup
					#if backend in ("ldap", "all"):
					#	logger.debug(u"Backing up ldap backend.")
					#	archive.backupLdapBackend()
					#if backend in ("ldap", "all"):
					#	logger.debug(u"Backing up univention backend.")
					#	archive.backupUniventionBackend()
			
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

			logger.notice(_("Backup complete"))
		except Exception, e:
			os.remove(archive.name)
			logger.logException(e, LOG_DEBUG)
			raise e
		
	def _verify(self, file, **kwargs):
		
		files = forceList(file)
		
		result = 0
		
		for f in files:
			
			archive = self._getArchive(mode="r", file=f)
			
			logger.info(_("Verifying archive %s" %f))
			try:
				archive.verify()
				logger.notice(_("Archive is OK."))
			except OpsiBackupFileError, e:
				logger.error(e)
				result = 1
			archive.close()
		return result
	
	def _verifySysconfig(self, archive):
		
		def ask(q=WARNING_DIFF):
				fd = sys.stdin.fileno()
	
				oldterm = termios.tcgetattr(fd)
				newattr = termios.tcgetattr(fd)
				newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
				termios.tcsetattr(fd, termios.TCSANOW, newattr)
				
				oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
				fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
				
				self.stdout.write(q)
				
					
				try:
					while 1:
						try:
							c = sys.stdin.read(1)
							return (forceUnicode(c) in (u"y",u"Y"))
						except IOError: pass
				finally:
					termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
					fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
		
		try:
			sysInfo = SysInfo()
			archiveInfo = archive.sysinfo
		
		
			diff = {}
			
			for key, value in archiveInfo.iteritems():
				if str(getattr(sysInfo, key, None)) != value:
					diff[key] = value
					
			if diff:
				return ask(WARNING_DIFF)
		except OpsiError, e:
			return ask(WARNING_SYSCONFIG % unicode(e))
		return True


	def _restore(self, file, mode="raw", backends=[], configuration=True, force=False, **kwargs):
		
		if not backends:
			backends = []
		
		if "all" in backends:
			backends = ["all"]

		auto = "auto" in backends

		archive = self._getArchive(file=file[0], mode="r")
		
		try:
			
			self._verify(archive.name)
			
			functions = []
			
			if force or self._verifySysconfig(archive):
			
				logger.notice(_(u"Restoring data from backup archive %s." % archive.name))
				
				if configuration:
					if not archive.hasConfiguration() and not force:
						raise OpsiBackupFileError(_("Backup file does not contain configuration data."))
					logger.debug(u"Restoring opsi configuration.")
					functions.append(archive.restoreConfiguration)
		


				if mode == "raw":
					for backend in backends:
						if backend in ("file", "all", "auto"):
							if not archive.hasFileBackend() and not force and not auto:
								raise OpsiBackupFileError(_("Backup file does not contain file backend data."))
							functions.append(archive.restoreFileBackend)
							
						if backend in ("mysql", "all", "auto"):
							if not archive.hasMySQLBackend() and not force and not auto:
								raise OpsiBackupFileError(_("Backup file does not contain mysql backend data."))
							functions.append(archive.restoreMySQLBackend)
						
						if backend in ("dhcp", "all", "auto"):
							if not archive.hasDHCPBackend() and not force and not auto:
								raise OpsiBackupFileError(_("Backup file does not contain DHCP backup data."))
							functions.append(archive.restoreDHCPBackend)
						#TODO: implement ldap/univention backup
						#if backend in ("ldap", "all"):
						#	logger.debug(u"Backing up ldap backend.")
						#	archive.backupLdapBackend()
						#if backend in ("ldap", "all"):
						#	logger.debug(u"Backing up univention backend.")
						#	archive.backupUniventionBackend()
				try:
					for f in functions:
						logger.debug2("Running restoration function %s" % repr(f))
						f(auto)
				except OpsiBackupBackendNotFound, e:
					if not auto:
						raise e
				except Exception, e:
					logger.error("Failed to restore data from archive %s: %s. Aborting." %(archive.name, e))
					raise e
				
				logger.notice(_("Restoration complete"))
		finally:
			archive.close()


	def run(self):
		
		func = getattr(self, "_%s" % self.__dict__.pop("command"), None)
		if func is None:
			raise RuntimeError("Invalid command specified")
		
		func(**self.__dict__)
		
def main(argv = sys.argv[1:], stdout=sys.stdout):

	logger.setLogFormat('[%l] [%D] %M')
	logger.setConsoleLevel(LOG_WARNING)
	
	backup = OpsiBackup(stdout=stdout)
	parser = argparse.ArgumentParser(prog="opsi-backup", description=_('Creates and restores opsi backups.'))
	#FIXME: show program version
	parser.add_argument("-v", "--verbose", action="store_true", default=False, help=_("Show log output on standard out."))
	parser.add_argument("-V", "--version", action="version", version='opsi-backup %s'%  __verstr__, help="Show program version.")
	parser.add_argument("-l", "--log-level", type=int, default=5, choices=range(1,10), help=_("Set the log level for this program (Default: 5)."))
	parser.add_argument("--log-file", metavar='FILE', default="/var/log/opsi/opsi-backup.log", help=_("Set a log file for this program."))
	subs = parser.add_subparsers(title="commands", dest="command", help=_("opsi-backup sub-commands"))
	
	parser_verify = subs.add_parser("verify", help=_("Verify archive integrity."))
	parser_verify.add_argument("file", nargs="+", help=_("The backup archive to verify."))
	
	parser_restore = subs.add_parser("restore", help=_("Restore data from a backup archive."))
	parser_restore.add_argument("file", nargs=1, help=_("The backup archive to restore data from."))
	parser_restore.add_argument("--mode", nargs=1, choices=['raw', 'data'], default="raw", help=argparse.SUPPRESS ) # TODO: help=_("Select a mode that should ne used for restoration. (Default: raw)"))
	parser_restore.add_argument("--backends", action="append", choices=['file','mysql','dhcp','auto','all'], help=_("Select a backend to restore or 'all' for all backends. Can be given multiple times."))
	parser_restore.add_argument("--configuration", action="store_true", default=False, help=_("Restore opsi configuration."))
	#parser_restore.add_argument("--dhcp", action="store_true", default=False, help=_("Restore dhcp configuration."))
	parser_restore.add_argument("-f", "--force", action="store_true", default=False, help=_("Ignore sanity checks and try to apply anyways. Use with caution! (Default: false)"))
	
	parser_create = subs.add_parser("create", help=_("Create a new backup."))
	parser_create.add_argument("destination", nargs="?", help=_("Destination of the generated output file. (optional)"))
	parser_create.add_argument("--mode", nargs=1, choices=['raw', 'data'], default="raw", help=argparse.SUPPRESS ) # TODO: help=_("Select a mode that should ne used for backup. (Default: raw)"))
	parser_create.add_argument("--flush-logs", action="store_true", default=False, help=_("Causes mysql to flush table logs to disk before the backup. (recommended)"))
	parser_create.add_argument("--backends", action="append", choices=['file','mysql','dhcp', 'auto', 'all'], default=DefaultList(["auto"]), help=_("Select a backend to backup or 'all' for all backends. Can be given multiple times. (Default: auto)"))
	parser_create.add_argument("--no-configuration", action="store_true", default=False, help=_("Backup opsi configuration."))
	#parser_create.add_argument("--dhcp", action="store_true", default=False, help=_("Backup dhcp configuration."))
	parser_create.add_argument("-c", "--compression", nargs="?", default="bz2", choices=['gz','bz2', 'none'], help=_("Sets the compression format for the archive (Default: bz2)"))

	parser.parse_args(argv, namespace=backup)

	logLevel = backup.__dict__.pop("log_level")

	verbose = backup.__dict__.pop("verbose", None)
	if verbose:
		logger.setConsoleLevel(logLevel)

	logFile = backup.__dict__.pop("log_file", None)
	if logFile:
		logger.setLogFile(logFile)
		logger.setFileLevel(logLevel)

	try:
		result = backup.run()
		if type(result) == types.IntType:
			return result
		return 0
	except KeyboardInterrupt, e:
		return 1
	except Exception, e:
		logger.logException(e, LOG_DEBUG)
		logger.error(_(u"Task backup failed: %s" %e))
		return 1










