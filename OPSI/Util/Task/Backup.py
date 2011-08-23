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

import sys, types, os, termios, fcntl, gettext, bz2, gzip, shutil

from OPSI.Types import *
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

			logger.notice(u"Backup complete")
		except Exception, e:
			os.remove(archive.name)
			logger.logException(e, LOG_DEBUG)
			raise e
		
	def _verify(self, file, **kwargs):
		
		files = forceList(file)
		
		result = 0
		
		for f in files:
			
			archive = self._getArchive(mode="r", file=f)
			
			logger.info(u"Verifying archive %s" % f)
			try:
				archive.verify()
				logger.notice(u"Archive is OK.")
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
			
				logger.notice(u"Restoring data from backup archive %s." % archive.name)
				
				if configuration:
					if not archive.hasConfiguration() and not force:
						raise OpsiBackupFileError(u"Backup file does not contain configuration data.")
					logger.debug(u"Restoring opsi configuration.")
					functions.append(lambda x: archive.restoreConfiguration())
		


				if (mode == "raw"):
					for backend in backends:
						if backend in ("file", "all", "auto"):
							if not archive.hasFileBackend() and not force and not auto:
								raise OpsiBackupFileError(u"Backup file does not contain file backend data.")
							functions.append(archive.restoreFileBackend)
							
						if backend in ("mysql", "all", "auto"):
							if not archive.hasMySQLBackend() and not force and not auto:
								raise OpsiBackupFileError(u"Backup file does not contain mysql backend data.")
							functions.append(archive.restoreMySQLBackend)
						
						if backend in ("dhcp", "all", "auto"):
							if not archive.hasDHCPBackend() and not force and not auto:
								raise OpsiBackupFileError(u"Backup file does not contain DHCP backup data.")
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
						logger.debug2(u"Running restoration function %s" % repr(f))
						f(auto)
				except OpsiBackupBackendNotFound, e:
					if not auto:
						raise e
				except Exception, e:
					logger.error(u"Failed to restore data from archive %s: %s. Aborting." % (archive.name, e))
					logger.logException(e, LOG_DEBUG)
					raise e
				
				logger.notice(u"Restoration complete")
		finally:
			archive.close()








