#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013 uib GmbH <info@uib.de>

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
opsi python library - Util - Task - Sudoers

Functionality to patch a sudoers file on a Linux system.

.. versionadded:: 4.0.4.3

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
import codecs
import shutil
import time

from OPSI.Logger import Logger
from OPSI.System.Posix import Distribution

try:
	from OPSI.Util.File.Opsi import OpsiConfFile
	FILE_ADMIN_GROUP = OpsiConfFile().getOpsiFileAdminGroup()
except Exception:
	FILE_ADMIN_GROUP = u'pcpatch'

SUDOERS_FILE = u'/etc/sudoers'
_NO_TTY_FOR_SERVICE_REQUIRED = u"Defaults!/sbin/service !requiretty"
_NO_TTY_REQUIRED_DEFAULT = u"Defaults:opsiconfd !requiretty"
LOGGER = Logger()


def patchSudoersFileForOpsi(sudoersFile=SUDOERS_FILE):
	"""
	Patches the sudoers file so opsiconfd and the OPSI file admins can \
call opsi-set-rights.

	:param sudoersFile: The path to the sudoers file.
	"""
	entries = [
		"opsiconfd ALL=NOPASSWD: %s" % "/usr/bin/opsi-set-rights",
		"%%%s ALL=NOPASSWD: %s" % (FILE_ADMIN_GROUP, "/usr/bin/opsi-set-rights"),
	]

	_patchSudoersFileWithEntries(sudoersFile, entries)


def patchSudoersFileToAllowRestartingDHCPD(dhcpdRestartCommand, sudoersFile=SUDOERS_FILE):
	"""
	Patches the sudoers file so opsiconfd can restart the DHCP daemon
	and execute the ``service`` command without an tty.

	:param dhcpdRestartCommand: The command used to restart the DHCP daemon
	:param sudoersFile: The path to the sudoers file.
	"""
	entries = [
		u"opsiconfd ALL=NOPASSWD: {0}\n".format(dhcpdRestartCommand)
	]

	_patchSudoersFileWithEntries(sudoersFile, entries)


def _patchSudoersFileWithEntries(sudoersFile, entries):
	"""
	Patches ``sudoersFile`` with ``entries`` if they are missing.

	.. versionadded:: 4.0.4.6


	.. versionchanged:: 4.0.5.15

		Do not require a TTY for running the service command.
	"""
	lines = []
	entriesAlreadyExisting = False
	ttyPatchRequired = True
	servicePatchRequired = True

	with codecs.open(sudoersFile, 'r', 'utf-8') as inputFile:
		for line in inputFile:
			for entry in entries:
				if entry in line:
					entriesAlreadyExisting = True
					break

			if _NO_TTY_REQUIRED_DEFAULT in line:
				ttyPatchRequired = False
			elif _NO_TTY_FOR_SERVICE_REQUIRED in line:
				servicePatchRequired = False

			lines.append(line)

	ttyPatchRequired = ttyPatchRequired and distributionRequiresNoTtyPatch()
	modifyFile = ttyPatchRequired or servicePatchRequired or (not entriesAlreadyExisting)
	if modifyFile:
		LOGGER.notice(u"   Adding sudoers entries for opsi")

	if not entriesAlreadyExisting:
		for entry in entries:
			lines.append("{0}\n".format(entry))

	if ttyPatchRequired:
		lines.append(u"{0}\n".format(_NO_TTY_REQUIRED_DEFAULT))

	if servicePatchRequired:
		lines.append(u"{0}\n".format(_NO_TTY_FOR_SERVICE_REQUIRED))

	if modifyFile:
		lines.append('\n')

		LOGGER.notice(u"   Creating backup of %s" % sudoersFile)
		shutil.copy(
			sudoersFile,
			u'{filename}.{timestamp}'.format(
				filename=sudoersFile,
				timestamp=time.strftime("%Y-%m-%d_%H:%M")
			)
		)

		LOGGER.notice(u"   Writing new %s" % sudoersFile)
		with codecs.open(sudoersFile, 'w', 'utf-8') as outputFile:
			outputFile.writelines(lines)


def distributionRequiresNoTtyPatch():
	"""
	Checks if the used Distribution requires a patch to use sudo without a tty.

	.. versionadded:: 4.0.4.3

	:returntype: bool
	"""
	distributor = Distribution().distributor
	distributor = distributor.lower()
	return ('scientificsl' in distributor or 'redhat' in distributor
			or 'centos' in distributor or 'sme' in distributor)
