#!/usr/bin/python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2014-2015 uib GmbH - http://www.uib.de/

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
Setting access rights for opsi.

Opsi needs different access rights and ownerships for files and folders
during its use. To ease the setting of these permissions this modules
provides helpers for this task.


.. versionadded:: 4.0.6.1


:copyright:  uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import grp
import os
import pwd
import re

from OPSI.Backend.Backend import OPSI_GLOBAL_CONF
from OPSI.Logger import Logger
from OPSI.Types import forceHostId
from OPSI.Util import findFiles, getfqdn
from OPSI.Util.File.Opsi import OpsiConfFile

logger = Logger()

_OPSICONFD_USER = u'opsiconfd'
_ADMIN_GROUP = u'opsiadmin'
_CLIENT_USER = u'pcpatch'

try:
	_FILE_ADMIN_GROUP = OpsiConfFile().getOpsiFileAdminGroup()
except Exception:
	_FILE_ADMIN_GROUP = u'pcpatch'

SPECIAL_FILES = set([
	u'setup.py', u'show_drivers.py', u'create_driver_links.py',
	u'opsi-deploy-client-agent', u'opsi-deploy-client-agent-old', u'winexe'
])


# TODO: use OPSI.System.Posix.Sysconfig for a more standardized approach
def getLocalFQDN():
	try:
		fqdn = getfqdn(conf=OPSI_GLOBAL_CONF)
		return forceHostId(fqdn)
	except Exception:
		raise Exception(
			u"Failed to get fully qualified domain name, "
			u"got '{0}'".format(fqdn)
		)


def setRights(path=u'/'):
	logger.notice(u"Setting rights")
	basedir = path
	if not os.path.isdir(basedir):
		basedir = os.path.dirname(basedir)

	depotDir = ''
	dirnames = getDirectoriesToProcess()
	if not path.startswith('/etc') and not path.startswith('/tftpboot'):
		try:
			from OPSI.Backend.BackendManager import BackendManager
			backend = BackendManager(
				dispatchConfigFile=u'/etc/opsi/backendManager/dispatch.conf',
				backendConfigDir=u'/etc/opsi/backends',
				extensionConfigDir=u'/etc/opsi/backendManager/extend.d'
			)
			depot = backend.host_getObjects(type='OpsiDepotserver', id=getLocalFQDN())
			backend.backend_exit()
			if depot:
				depot = depot[0]
				depotUrl = depot.getDepotLocalUrl()
				if not depotUrl.startswith('file:///'):
					raise Exception(u"Bad repository local url '%s'" % depotUrl)
				depotDir = depotUrl[7:]
				if os.path.exists(depotDir):
					logger.info(u"Local depot directory '%s' found" % depotDir)
					dirnames.append(depotDir)
		except Exception as e:
			logger.error(e)

	if basedir.startswith('/opt/pcbin/install'):
		found = False
		for dirname in dirnames:
			if dirname.startswith('/opt/pcbin/install'):
				found = True
				break
		if not found:
			dirnames.append('/opt/pcbin/install')

	# TODO: split into paths here:
	# First we want a part that just gives (yield?) us the directories to travel through.
	# Then we want a part that processes that directory and sets the rights

	clientUserUid = pwd.getpwnam(_CLIENT_USER)[2]
	opsiconfdUid = pwd.getpwnam(_OPSICONFD_USER)[2]
	adminGroupGid = grp.getgrnam(_ADMIN_GROUP)[2]
	fileAdminGroupGid = grp.getgrnam(_FILE_ADMIN_GROUP)[2]

	for dirname in removeDuplicatesFromDirectories(dirnames):
		if not dirname.startswith(basedir) and not basedir.startswith(dirname):
			continue
		uid  = opsiconfdUid
		gid  = fileAdminGroupGid
		fmod = 0660
		dmod = 0770
		correctLinks = False

		isProduct = dirname not in (u'/var/lib/tftpboot/opsi', u'/tftpboot/linux', u'/var/log/opsi', u'/etc/opsi', u'/var/lib/opsi', u'/var/lib/opsi/workbench')

		if dirname in (u'/var/lib/tftpboot/opsi', u'/tftpboot/linux'):
			fmod = 0664
			dmod = 0775
		elif dirname in (u'/var/log/opsi', u'/etc/opsi'):
			gid = adminGroupGid
			correctLinks = True
		elif dirname in (u'/home/opsiproducts', '/var/lib/opsi/workbench'):
			uid = -1
			dmod = 02770
		if dirname == depotDir:
			dmod = 02770

		if os.path.isfile(path):
			logger.debug(u"Setting ownership to {user}:{group} on file '{file}'".format(file=path, user=uid, group=gid))
			os.chown(path, uid, gid)
			logger.debug(u"Setting rights on file '%s'" % path)
			if isProduct:
				os.chmod(path, (os.stat(path)[0] | 0660) & 0770)
			else:
				os.chmod(path, fmod)
			continue

		startPath = dirname
		if basedir.startswith(dirname):
			startPath = basedir

		logger.notice(u"Setting rights on directory '%s'" % startPath)
		os.chown(startPath, uid, gid)
		os.chmod(startPath, dmod)
		for filepath in findFiles(startPath, prefix=startPath, returnLinks=correctLinks, excludeFile=re.compile("(.swp|~)$")):
			logger.debug(u"Setting ownership to {user}:{group} on file '{file}'".format(file=filepath, user=uid, group=gid))
			os.chown(filepath, uid, gid)
			if os.path.isdir(filepath):
				logger.debug(u"Setting rights on directory '%s'" % filepath)
				os.chmod(filepath, dmod)
			elif os.path.isfile(filepath):
				logger.debug(u"Setting rights on file '%s'" % filepath)
				if isProduct:
					if os.path.basename(filepath) in SPECIAL_FILES:
						logger.debug(u"Setting rights on special file '{0}'".format(filepath))
						os.chmod(filepath, 0770)
					else:
						logger.debug(u"Setting rights on file '{0}'".format(filepath))
						os.chmod(filepath, (os.stat(filepath)[0] | 0660) & 0770)
				else:
					logger.debug(u"Setting rights {rights} on file '{file}'".format(file=filepath, rights=fmod))
					os.chmod(filepath, fmod)

		if startPath.startswith(u'/var/lib/opsi'):
			os.chmod(u'/var/lib/opsi', 0750)
			os.chown(u'/var/lib/opsi', clientUserUid, fileAdminGroupGid)
			setRightsOnSSHDirectory(clientUserUid, fileAdminGroupGid)


def getDirectoriesToProcess():
	if _isSLES():
		return [u'/var/lib/tftpboot/opsi', u'/var/log/opsi', u'/etc/opsi',
				u'/var/lib/opsi', u'/var/lib/opsi/workbench']
	else:
		return [u'/tftpboot/linux', u'/home/opsiproducts', u'/var/log/opsi',
				u'/etc/opsi', u'/var/lib/opsi']


def _isSLES():
	return 'suse linux enterprise server' in getDistribution().lower()


# TODO: better ways!
def getDistribution():
	try:
		f = os.popen('lsb_release -d 2>/dev/null')
		distribution = f.read().split(':')[1].strip()
		f.close()
		return distribution
	except Exception:
		return ''


def removeDuplicatesFromDirectories(directories):
	"""
	Cleans the iterable `directories` from duplicates and also makes
	sure that no subfolders are included to avoid duplicate processing.

	:returntype: set
	"""
	folders = set()

	for folder in directories:
		folder = os.path.normpath(folder)
		folder = os.path.realpath(folder)

		if not folders:
			logger.debug("Initial fill for folders with: {0}".format(folder))
			folders.add(folder)
			continue

		for anotherDir in folders.copy():
			if folder == anotherDir:
				logger.debug("Already existing folder: {0}".format(folder))
				continue
			elif folder in anotherDir:
				logger.debug("{0} in {1}. Removing {1}, adding {0}".format(folder, anotherDir))
				folders.remove(anotherDir)
				folders.add(folder)
			elif anotherDir in folder:
				logger.debug("{1} in {0}. Ignoring.".format(folder, anotherDir))
				continue
			else:
				logger.debug("New folder: {0}".format(folder))
				folders.add(folder)

	logger.debug("Final folder collection: {0}".format(folders))
	return folders


def setRightsOnSSHDirectory(userId, groupId, path=u'/var/lib/opsi/.ssh'):
	if os.path.exists(path):
		os.chown(path, userId, groupId)
		os.chmod(path, 0750)

		idRsa = os.path.join(path, u'id_rsa')
		if os.path.exists(idRsa):
			os.chmod(idRsa, 0640)
			os.chown(idRsa, userId, groupId)

		idRsaPub = os.path.join(path, u'id_rsa.pub')
		if os.path.exists(idRsaPub):
			os.chmod(idRsaPub, 0644)
			os.chown(idRsaPub, userId, groupId)

		authorizedKeys = os.path.join(path, u'authorized_keys')
		if os.path.exists(authorizedKeys):
			os.chmod(authorizedKeys, 0600)
			os.chown(authorizedKeys, userId, groupId)
