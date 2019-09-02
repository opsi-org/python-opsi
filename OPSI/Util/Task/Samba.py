# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
Configuration of Samba for the use with opsi.

:author: Mathias Radtke <m.radtke@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os
import shutil
import time

from OPSI.Config import FILE_ADMIN_GROUP
from OPSI.Logger import Logger
from OPSI.System import execute, which
from OPSI.System.Posix import getSambaServiceName
from OPSI.Util.Task.Rights import getWorkbenchDirectory

__all__ = ('configureSamba', 'isSamba4')

logger = Logger()

SMB_CONF = u'/etc/samba/smb.conf'


def configureSamba(config=SMB_CONF):
	"""
	Configure the Samba configuration to include the required shares.

	:param config: The path to the Samba configuration file.
	:type config: str
	"""
	logger.notice(u"Configuring samba")
	lines = _readConfig(config)
	newlines = _processConfig(lines)
	if lines != newlines:
		_writeConfig(newlines, config)
		_reloadSamba()
		logger.notice(u"Samba configuration finished. You may want to restart your Samba daemon.")


def _readConfig(config):
	with codecs.open(config, 'r', 'utf-8') as readConf:
		return readConf.readlines()


def _processConfig(lines):
	newlines = []
	optPcbinShareFound = False
	depotShareFound = False
	depotShareRWFound = False
	workbenchShareFound = False
	opsiImagesFound = False
	repositoryFound = False
	logsFound = False
	oplocksFound = False

	samba4 = isSamba4()

	for line in lines:
		currentLine = line.lower().strip()
		if currentLine == '[opt_pcbin]':
			optPcbinShareFound = True
		elif currentLine == '[opsi_depot]':
			depotShareFound = True
		elif currentLine == '[opsi_depot_rw]':
			depotShareRWFound = True
		elif currentLine == '[opsi_images]':
			opsiImagesFound = True
		elif currentLine == '[opsi_workbench]':
			workbenchShareFound = True
		elif currentLine == '[opsi_repository]':
			repositoryFound = True
		elif currentLine == '[opsi_logs]':
			logsFound = True
		elif 'oplocks' in currentLine:
			oplocksFound = True
		newlines.append(line)

	if optPcbinShareFound:
		logger.warning(u"Share opt_pcbin configuration found. You should use opsi_depot_rw instead, if you need a writeable depot-Share.")

	if not depotShareFound:
		logger.notice(u"   Adding share [opsi_depot]")
		newlines.append(u"[opsi_depot]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi depot share (ro)\n")
		newlines.append(u"   path = /var/lib/opsi/depot\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   writeable = no\n")
		newlines.append(u"   invalid users = root\n")
		if samba4:
			newlines.append(u"   admin users = @%s\n" % FILE_ADMIN_GROUP)
		newlines.append(u"\n")

		depotDir = '/var/lib/opsi/depot'
		if not os.path.exists(depotDir):
			try:
				os.mkdir(depotDir)
				if os.path.exists("/opt/pcbin/install"):
					logger.warning(u"You have an old depot configuration. Using /opt/pcbin/install is deprecated, please use /var/lib/opsi/depot instead.")
			except Exception as error:
				logger.warning(u"Failed to create depot directory '%s': %s" % (depotDir, error))
	elif samba4:
		logger.notice(u"   Share opsi_depot found and samba 4 is detected. Trying to detect the executablefix for opsi_depot-Share")
		endpos = 0
		found = False
		sectionFound = False
		for i, line in enumerate(newlines):
			if line.lower().strip() == '[opsi_depot]':
				startpos = endpos = i + 1
				sectionFound = True
				slicedList = newlines[startpos:]
				for element in slicedList:
					lines = element.lower().strip()
					if lines == "admin users = @%s" % FILE_ADMIN_GROUP:
						logger.notice(u"   fix found, nothing to do")
						found = True
						break
					elif lines.startswith("[") or not lines:
						logger.notice(u"   End of section detected")
						break
					else:
						endpos += 1
			if sectionFound:
				break

		if not found:
			logger.notice(u"   Section found but don't inherits samba4 fix, trying to set the fix.")
			newlines.insert(endpos, u"   admin users = @%s\n" % FILE_ADMIN_GROUP)

	if not depotShareRWFound:
		logger.notice(u"   Adding share [opsi_depot_rw]")
		newlines.append(u"[opsi_depot_rw]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi depot share (rw)\n")
		newlines.append(u"   path = /var/lib/opsi/depot\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")

	if not opsiImagesFound:
		logger.notice(u"   Adding share [opsi_images]")
		newlines.append(u"[opsi_images]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi ntfs images share (rw)\n")
		newlines.append(u"   path = /var/lib/opsi/ntfs-images\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")
		if not os.path.exists("/var/lib/opsi/ntfs-images"):
			logger.debug(u"Path:  /var/lib/opsi/ntfs-images not found: creating.")
			os.mkdir("/var/lib/opsi/ntfs-images")

	if not workbenchShareFound:
		try:
			workbenchDirectory = getWorkbenchDirectory()
		except Exception as error:
			logger.warning("Failed to read the location of the workbench: {0}", error)
			workbenchDirectory = None

		if workbenchDirectory:
			if workbenchDirectory.endswith('/'):
				# Removing trailing slash
				workbenchDirectory = workbenchDirectory[:-1]

			try:
				os.mkdir(workbenchDirectory)
				logger.notice(u"Created missing workbench directory {0}", workbenchDirectory)
			except OSError as mkdirErr:
				logger.debug2(u"Did not create workbench {}: {!r}", workbenchDirectory, mkdirErr)

			logger.notice(u"   Adding share [opsi_workbench]")
			newlines.append(u"[opsi_workbench]\n")
			newlines.append(u"   available = yes\n")
			newlines.append(u"   comment = opsi workbench\n")
			newlines.append(u"   path = {0}\n".format(workbenchDirectory))
			newlines.append(u"   writeable = yes\n")
			newlines.append(u"   invalid users = root\n")
			newlines.append(u"   create mask = 0660\n")
			newlines.append(u"   directory mask = 0770\n")
			newlines.append(u"\n")

	if not repositoryFound:
		logger.notice(u"  Adding share [opsi_repository]")
		newlines.append(u"[opsi_repository]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi repository share (ro)\n")
		newlines.append(u"   path = /var/lib/opsi/repository\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   writeable = no\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")
		if not os.path.exists("/var/lib/opsi/repository"):
			logger.debug(u"Path:  /var/lib/opsi/repository not found: creating.")
			os.mkdir("/var/lib/opsi/repository")

	if not logsFound:
		logger.notice(u"  Adding share [opsi_logs]")
		newlines.append(u"[opsi_logs]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi logs share (ro)\n")
		newlines.append(u"   path = /var/logs/opsi\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   writeable = no\n")
		newlines.append(u"   invalid users = root\n")
		if not os.path.exists("/var/log/opsi"):
			logger.debug(u"Path:  /var/log/opsi not found: creating.")
			os.mkdir("/var/log/opsi")

	if oplocksFound:
		logger.warning(u" Detected oplocks in your samba configuration. It is not recommended to use them with opsi. Please see the opsi manual for further information.")

	return newlines


def isSamba4():
	"""
	Check if the current system uses samba 4.

	:return: True if running Samba 4. False otherwise.
	:rtype: bool
	"""
	samba4 = False

	try:
		smbd = which('smbd')
		result = execute('%s -V 2>/dev/null' % smbd)
		for line in result:
			if line.lower().startswith("version"):
				samba4 = line.split()[1].startswith('4')
	except Exception as error:
		logger.debug('Getting Samba Version failed due to: {0}', error)

	return samba4


def _writeConfig(newlines, config):
	logger.notice(u"   Creating backup of %s" % config)
	shutil.copy(config, config + u'.' + time.strftime("%Y-%m-%d_%H:%M"))

	logger.notice(u"   Writing new smb.conf")
	with codecs.open(config, 'w', 'utf-8') as writeConf:
		writeConf.writelines(newlines)

def _reloadSamba():
	logger.notice(u"   Reloading samba")

	try:
		execute(u'service {name} reload'.format(name=getSambaServiceName(default="smbd")))
	except Exception as error:
		logger.warning(error)
