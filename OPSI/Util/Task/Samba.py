#! /usr/bin/env python
# Copyright (C) 2015 uib GmbH - http://www.uib.de
# All rights reserved.

import codecs
import os
import shutil
import time

import OPSI.System.Posix as Posix
from OPSI.Logger import LOG_NOTICE, Logger
from OPSI.System import *

logger = Logger()

logger.setConsoleLevel(LOG_NOTICE)
logger.setConsoleColor(True)

SMB_CONF = u'/etc/samba/smb.conf'
FILE_ADMIN_GROUP = u'pcpatch'

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

def configureSamba():
	logger.notice(u"Configuring samba")

	smb_init_command = u'service {name}'.format(name=Posix.getSambaServiceName(default="smbd"))

	f = codecs.open(SMB_CONF, 'r', 'utf-8')
	lines = f.readlines()
	f.close()
	newlines = []
	optPcbinShareFound = False
	depotShareFound = False
	depotShareRWFound = False
	configShareFound = False
	workbenchShareFound = False
	opsiImagesFound = False
	confChanged = False
	samba4 = isSamba4()

	for i in range(len(lines)):
		if (lines[i].lower().strip() == '; load opsi shares') and ((i+1) < len(lines)) and (lines[i+1].lower().strip() == 'include = /etc/samba/share.conf'):
			i += 1
			confChanged = True
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
		logger.warning(u"Share opt_pcbin configuration found in '%s'. You should use opsi_depot_rw instead, if you need a writeable depot-Share." % SMB_CONF)

	if not depotShareFound:
		logger.notice(u"   Adding share [opsi_depot]")
		confChanged = True
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
		fixedLines = []
		sectionFound = False
		for i in range(len(lines)):
			if lines[i].lower().strip() == '[opsi_depot]':
				startpos = endpos = i + 1
				sectionFound = True
				slicedList = lines[startpos:]
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
			fixedLines = lines
			fixedLines.insert(endpos, u"   admin users = @%s\n" % FILE_ADMIN_GROUP)
			with codecs.open(SMB_CONF, 'w', 'utf-8') as f:
				f.writelines(fixedLines)
			logger.notice(u"   Reloading samba")
			try:
				execute(u'%s reload' % smb_init_command)
			except Exception as e:
				logger.warning(e)

	if not depotShareRWFound:
		logger.notice(u"   Adding share [opsi_depot_rw]")
		confChanged = True
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
		confChanged = True
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
		confChanged = True
		newlines.append(u"[opsi_config]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi config share\n")
		newlines.append(u"   path = /var/lib/opsi/config\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"\n")

	if not workbenchShareFound:
		logger.notice(u"   Adding share [opsi_workbench]")
		confChanged = True
		newlines.append(u"[opsi_workbench]\n")
		newlines.append(u"   available = yes\n")
		newlines.append(u"   comment = opsi workbench\n")
		if (getSysConfig()['distribution'].lower().find('suse linux enterprise server') != -1):
			newlines.append(u"   path = /var/lib/opsi/workbench\n")
		else:
			newlines.append(u"   path = /home/opsiproducts\n")
		newlines.append(u"   writeable = yes\n")
		newlines.append(u"   invalid users = root\n")
		newlines.append(u"   create mask = 0660\n")
		newlines.append(u"   directory mask = 0770\n")
		newlines.append(u"\n")

	if confChanged:
		logger.notice(u"   Creating backup of %s" % SMB_CONF)
		shutil.copy(SMB_CONF, SMB_CONF + u'.' + time.strftime("%Y-%m-%d_%H:%M"))

		logger.notice(u"   Writing new smb.conf")
		f = codecs.open(SMB_CONF, 'w', 'utf-8')
		lines = f.writelines(newlines)
		f.close()

		logger.notice(u"   Reloading samba")
		try:
			execute(u'%s reload' % smb_init_command)
		except Exception as e:
			logger.warning(e)
