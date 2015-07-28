#! /usr/bin/env python
# Copyright (C) 2015 uib GmbH - http://www.uib.de
# All rights reserved.

import codecs
import os
import shutil
import time

import OPSI.System.Posix as Posix
from OPSI.Logger import Logger
from OPSI.System import *

logger = Logger()

SMB_CONF = u'/etc/samba/smb.conf'
FILE_ADMIN_GROUP = u'pcpatch'


def getDistribution():
	distribution = ''
	try:
		f = os.popen('lsb_release -d 2>/dev/null')
		distribution = f.read().split(':')[1].strip()
		f.close()
	except:
		pass
	return distribution


def isSamba4():
	samba4 = False
	try:
		smbd = which('smbd')
		print smbd
		result = execute('%s -V 2>/dev/null' % smbd)
		for line in result:
			if line.lower().startswith("version"):
				samba4 = line.split()[1].startswith('4')
	except Exception:
		pass
	return samba4


def _readConfig(config):
	with codecs.open(config, 'r', 'utf-8') as f:
		lines = f.readlines()
	return lines


def _processConfig(lines):
	newlines = []
	optPcbinShareFound = False
	depotShareFound = False
	depotShareRWFound = False
	configShareFound = False
	workbenchShareFound = False
	opsiImagesFound = False

	samba4 = isSamba4()

	for i in range(len(lines)):
		if (lines[i].lower().strip() == '; load opsi shares') and ((i + 1) < len(lines)) and (lines[i + 1].lower().strip() == 'include = /etc/samba/share.conf'):
			i += 1
			continue
		if (lines[i].lower().strip() == '[opt_pcbin]'):
			optPcbinShareFound = True
		elif (lines[i].lower().strip() == '[opsi_depot]'):
			depotShareFound = True
		elif (lines[i].lower().strip() == '[opsi_depot_rw]'):
			depotShareRWFound = True
		elif (lines[i].lower().strip() == '[opsi_images]'):
			opsiImagesFound = True
		elif (lines[i].lower().strip() == '[opsi_config]'):
			configShareFound = True
		elif (lines[i].lower().strip() == '[opsi_workbench]'):
			workbenchShareFound = True
		newlines.append(lines[i])

	if optPcbinShareFound:
		logger.warning(u"Share opt_pcbin configuration found. You should use opsi_depot_rw instead, if you need a writeable depot-Share.")

	if not depotShareFound:
		logger.notice(u"   Adding share [opsi_depot]")
		newlines.append(u"[opsi_depot]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi depot share (ro)\n")
		newlines.append(u"   path = /var/lib/opsi/depot\n")
		newlines.append(u"   oplocks = no\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   level2 oplocks = no\n")
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
					logger.warning(u"You have an old depot configuration. Using /opt/pcbin/install is depracted, please use /var/lib/opsi/depot instead.")
			except Exception as e:
				logger.warning(u"Failed to create depot directory '%s': %s" % (depotDir, e))
	elif samba4:
		logger.notice(u"   Share opsi_depot found and samba 4 is detected. Trying to detect the executablefix for opsi_depot-Share")
		startpos = 0
		endpos = 0
		found = False
		sectionFound = False
		for i in range(len(newlines)):
			if newlines[i].lower().strip() == '[opsi_depot]':
				startpos = endpos = i + 1
				sectionFound = True
				slicedList = newlines[startpos:]
				for z in range(len(slicedList)):
					line = slicedList[z].lower().strip()
					if line == "admin users = @%s" % FILE_ADMIN_GROUP:
						logger.notice(u"   fix found, nothing to do")
						found = True
						break
					elif line.startswith("[") or not line:
						logger.notice(u"   End of section detected")
						break
					else:
						endpos += 1
			if sectionFound:
				break

		if not found:
			logger.notice(u"   Section found but don't inherits samba4 fix, trying to set the fix.")
			newlines.insert(endpos, u"   admin users = @%s\n" % FILE_ADMIN_GROUP)
			logger.notice(u"   Reloading samba")
			try:
				execute(u'%s reload' % u'service {name}'.format(name=Posix.getSambaServiceName(default="smbd")))
			except Exception as e:
				logger.warning(e)

	if not depotShareRWFound:
		logger.notice(u"   Adding share [opsi_depot_rw]")
		newlines.append(u"[opsi_depot_rw]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi depot share (rw)\n")
		newlines.append(u"   path = /var/lib/opsi/depot\n")
		newlines.append(u"   oplocks = no\n")
		newlines.append(u"   follow symlinks = yes\n")
		newlines.append(u"   level2 oplocks = no\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")

	if not opsiImagesFound:
		logger.notice(u"   Adding share [opsi_images]")
		newlines.append(u"[opsi_images]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi ntfs images share (rw)\n")
		newlines.append(u"   path = /var/lib/opsi/ntfs-images\n")
		newlines.append(u"   oplocks = no\n")
		newlines.append(u"   level2 oplocks = no\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")
		if not os.path.exists("/var/lib/opsi/ntfs-images"):
			logger.debug(u"Path:  /var/lib/opsi/ntfs-images not found: creating.")
			os.mkdir("/var/lib/opsi/ntfs-images")

	if not configShareFound:
		logger.notice(u"   Adding share [opsi_config]")
		newlines.append(u"[opsi_config]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi config share\n")
		newlines.append(u"   path = /var/lib/opsi/config\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")

	if not workbenchShareFound:
		logger.notice(u"   Adding share [opsi_workbench]")
		newlines.append(u"[opsi_workbench]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi workbench\n")
		if (getDistribution().lower().find('suse linux enterprise server') != -1):
			newlines.append(u"   path = /var/lib/opsi/workbench\n")
		else:
			newlines.append(u"   path = /home/opsiproducts\n")

		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"   create mask = 0660\n")
		newlines.append(u"   directory mask = 0770\n")
		newlines.append(u"\n")

	return newlines


def _writeConfig(newlines, config):
	logger.notice(u"   Creating backup of %s" % config)
	shutil.copy(config, config + u'.' + time.strftime("%Y-%m-%d_%H:%M"))

	logger.notice(u"   Writing new smb.conf")
	with codecs.open(config, 'w', 'utf-8') as f:
		f.writelines(newlines)

	logger.notice(u"   Reloading samba")
	try:
		execute(u'%s reload' % u'service {name}'.format(name=Posix.getSambaServiceName(default="smbd")))
	except Exception as e:
		logger.warning(e)


def configureSamba(config=SMB_CONF):

	logger.notice(u"Configuring samba")

	smb_init_command = u'service {name}'.format(name=Posix.getSambaServiceName(default="smbd"))

	lines = _readConfig(config)

	newlines = _processConfig(lines)

	if lines != newlines:
		_writeConfig(newlines, config)
