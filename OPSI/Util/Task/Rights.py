#!/usr/bin/python
# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2014-2016 uib GmbH - http://www.uib.de/

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


.. versionchanged:: 4.0.6.3

	Added function :py:func:`chown`.


.. versionchanged:: 4.0.6.4

	Improved :py:func:`removeDuplicatesFromDirectories`.


.. versionchanged:: 4.0.6.24

	Disabled :py:func:`removeDuplicatesFromDirectories` to avoid
	problems with wrong rights set on /var/lib/opsi/depot

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
from OPSI.System.Posix import isSLES

__version__ = '4.0.6.48'

LOGGER = Logger()

_DEPOT_DIRECTORY = None
_OPSICONFD_USER = u'opsiconfd'
_ADMIN_GROUP = u'opsiadmin'
_CLIENT_USER = u'pcpatch'

try:
	_FILE_ADMIN_GROUP = OpsiConfFile().getOpsiFileAdminGroup()
except Exception:
	_FILE_ADMIN_GROUP = u'pcpatch'

KNOWN_EXECUTABLES = frozenset((
	u'create_driver_links.py', u'opsi-deploy-client-agent',
	u'opsi-deploy-client-agent-default', u'opsi-deploy-client-agent-old',
	u'service_setup.sh', u'setup.py', u'show_drivers.py', u'winexe',
	u'windows-image-detector.py',
))


# TODO: use OPSI.System.Posix.Sysconfig for a more standardized approach
def getLocalFQDN():
	try:
		fqdn = getfqdn(conf=OPSI_GLOBAL_CONF)
		return forceHostId(fqdn)
	except Exception as error:
		raise Exception(
			u"Failed to get fully qualified domain name: {0}".format(error)
		)


def setRights(path=u'/'):
	LOGGER.debug(u"Setting rights on {0!r}", path)
	LOGGER.debug("euid is {0}", os.geteuid())

	basedir = os.path.abspath(path)
	if not os.path.isdir(basedir):
		basedir = os.path.dirname(basedir)

	clientUserUid = pwd.getpwnam(_CLIENT_USER)[2]
	opsiconfdUid = pwd.getpwnam(_OPSICONFD_USER)[2]
	adminGroupGid = grp.getgrnam(_ADMIN_GROUP)[2]
	fileAdminGroupGid = grp.getgrnam(_FILE_ADMIN_GROUP)[2]

	(directories, depotDir) = getDirectoriesForProcessing(path)

	processedDirectories = set()
	# TODO: try to re-introduce removeDuplicatesFromDirectories for speedups
	for dirname in directories:
		if not dirname.startswith(basedir) and not basedir.startswith(dirname):
			LOGGER.debug(u"Skipping {0!r}", dirname)
			continue
		uid = opsiconfdUid
		gid = fileAdminGroupGid
		fileMode = 0o660
		directoryMode = 0o770
		correctLinks = False

		if dirname in (u'/var/lib/tftpboot/opsi', u'/tftpboot/linux'):
			fileMode = 0o664
			directoryMode = 0o775
		elif dirname in (u'/var/log/opsi', u'/etc/opsi'):
			gid = adminGroupGid
			correctLinks = True
		elif dirname in (u'/home/opsiproducts', '/var/lib/opsi/workbench'):
			uid = -1
			directoryMode = 0o2770

		if os.path.isfile(path):
			chown(path, uid, gid)

			LOGGER.debug(u"Setting rights on file {0!r}", path)
			if path.startswith(u'/var/lib/opsi/depot/'):
				LOGGER.debug("Assuming file in product folder...")
				os.chmod(path, (os.stat(path)[0] | 0o660) & 0o770)
			else:
				LOGGER.debug("Assuming general file...")
				os.chmod(path, fileMode)
			continue

		startPath = dirname
		if basedir.startswith(dirname):
			startPath = basedir

		if startPath in processedDirectories:
			LOGGER.debug(u"Already proceesed {0}, Skipping.", startPath)
			continue

		if dirname == depotDir:
			directoryMode = 0o2770

		LOGGER.notice(u"Setting rights on directory {0!r}", startPath)
		LOGGER.debug2(u"Current setting: startPath={path}, uid={uid}, gid={gid}", path=startPath, uid=uid, gid=gid)
		chown(startPath, uid, gid)
		os.chmod(startPath, directoryMode)
		for filepath in findFiles(startPath, prefix=startPath, returnLinks=correctLinks, excludeFile=re.compile("(.swp|~)$")):
			chown(filepath, uid, gid)
			if os.path.isdir(filepath):
				LOGGER.debug(u"Setting rights on directory {0!r}", filepath)
				os.chmod(filepath, directoryMode)
			elif os.path.isfile(filepath):
				LOGGER.debug(u"Setting rights on file {0!r}", filepath)
				if filepath.startswith((u'/var/lib/opsi/depot/', u'/opt/pcbin/install/')):
					if os.path.basename(filepath) in KNOWN_EXECUTABLES:
						LOGGER.debug(u"Setting rights on special file {0!r}", filepath)
						os.chmod(filepath, 0o770)
					else:
						LOGGER.debug(u"Setting rights on file {0!r}", filepath)
						os.chmod(filepath, (os.stat(filepath)[0] | 0o660) & 0o770)
				else:
					LOGGER.debug(u"Setting rights {rights!r} on file {file!r}", file=filepath, rights=fileMode)
					os.chmod(filepath, fileMode)

		if startPath.startswith(u'/var/lib/opsi') and os.geteuid() == 0:
			os.chmod(u'/var/lib/opsi', 0o750)
			chown(u'/var/lib/opsi', clientUserUid, fileAdminGroupGid)
			setRightsOnSSHDirectory(clientUserUid, fileAdminGroupGid)

		processedDirectories.add(startPath)


def getDirectoriesForProcessing(path):
	basedir = os.path.abspath(path)
	if not os.path.isdir(basedir):
		basedir = os.path.dirname(basedir)

	depotDir = ''
	dirnames = getDirectoriesManagedByOpsi()
	if not basedir.startswith(('/etc', '/tftpboot')):
		global _DEPOT_DIRECTORY
		if _DEPOT_DIRECTORY is not None:
			depotDir = _DEPOT_DIRECTORY
		else:
			try:
				depotUrl = getDepotUrl()
				depotDir = depotUrl[7:]
				_DEPOT_DIRECTORY = depotDir
			except Exception as error:
				LOGGER.error(error)

		if os.path.exists(depotDir):
			LOGGER.info(u"Local depot directory {0!r} found", depotDir)
			dirnames.add(depotDir)

	if basedir.startswith('/opt/pcbin/install'):
		for dirname in dirnames:
			if dirname.startswith('/opt/pcbin/install'):
				break
		else:
			dirnames.add('/opt/pcbin/install')

	return (dirnames, depotDir)


def getDirectoriesManagedByOpsi():
	directories = set([u'/etc/opsi', u'/var/lib/opsi', u'/var/log/opsi'])

	if isSLES():
		directories.add(u'/var/lib/tftpboot/opsi')
		directories.add(u'/var/lib/opsi/workbench')
	else:
		directories.add(u'/tftpboot/linux')
		directories.add(u'/home/opsiproducts')

	return directories


def getDepotUrl():
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
			raise Exception(u"Bad repository local url {0!r}".format(depotUrl))

		return depotUrl

	raise Exception("Could not get depot URL.")


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
			LOGGER.debug("Initial fill for folders with: {0}".format(folder))
			folders.add(folder)
			continue

		shouldAdd = True
		for alreadyAddedFolder in folders.copy():
			if alreadyAddedFolder.startswith(folder) and not alreadyAddedFolder == folder:
				LOGGER.debug("{0} in {1}. Removing {1}, adding {0}", folder, alreadyAddedFolder)
				folders.remove(alreadyAddedFolder)
				folders.add(folder)
				shouldAdd = False
			elif folder.startswith(alreadyAddedFolder):
				LOGGER.debug("{1} in {0}. Ignoring.", folder, alreadyAddedFolder)
				shouldAdd = False

		if shouldAdd:
			LOGGER.debug("Adding new folder: {0}", folder)
			folders.add(folder)

	LOGGER.debug("Final folder collection: {0}", folders)
	return folders


def chown(path, uid, gid):
	"""
	Set the ownership of a file or folder.

	The uid will only be set if the efficte uid is 0 - i.e. running with sudo.

	If changing the owner fails an Exception will only be risen if the
	current uid is 0 - we are root.
	In all other cases only a warning is shown.
	"""
	try:
		if os.geteuid() == 0:
			LOGGER.debug(u"Setting ownership to {user}:{group} on {path!r}", path=path, user=uid, group=gid)
			if os.path.islink(path):
				os.lchown(path, uid, gid)
			else:
				os.chown(path, uid, gid)
		else:
			LOGGER.debug(u"Setting ownership to -1:{group} on {path!r}", path=path, group=gid)
			if os.path.islink(path):
				os.lchown(path, -1, gid)
			else:
				os.chown(path, -1, gid)
	except OSError as fist:
		if os.geteuid() == 0:
			# We are root so something must be really wrong!
			raise fist

		LOGGER.warning(u"Failed to set ownership on {file!r}: {error}", file=path, error=fist)
		LOGGER.notice(u"Please try setting the rights as root.")


def setRightsOnSSHDirectory(userId, groupId, path=u'/var/lib/opsi/.ssh'):
	if os.path.exists(path):
		os.chown(path, userId, groupId)
		os.chmod(path, 0o750)

		idRsa = os.path.join(path, u'id_rsa')
		if os.path.exists(idRsa):
			os.chmod(idRsa, 0o640)
			os.chown(idRsa, userId, groupId)

		idRsaPub = os.path.join(path, u'id_rsa.pub')
		if os.path.exists(idRsaPub):
			os.chmod(idRsaPub, 0o644)
			os.chown(idRsaPub, userId, groupId)

		authorizedKeys = os.path.join(path, u'authorized_keys')
		if os.path.exists(authorizedKeys):
			os.chmod(authorizedKeys, 0o600)
			os.chown(authorizedKeys, userId, groupId)
