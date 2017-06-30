# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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


.. versionchanged:: 4.0.6.3

	The path to service is received directly from the OS.


.. versionchanged:: 4.0.6.6

	Avoid duplicating settings.


:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
import codecs
import shutil
import time

from OPSI.Config import FILE_ADMIN_GROUP
from OPSI.Logger import Logger
from OPSI.System.Posix import Distribution, which

LOGGER = Logger()

SUDOERS_FILE = u'/etc/sudoers'
_NO_TTY_REQUIRED_DEFAULT = u"Defaults:opsiconfd !requiretty"

try:
	_NO_TTY_FOR_SERVICE_REQUIRED = u"Defaults!{0} !requiretty".format(which('service'))
except Exception:
	_NO_TTY_FOR_SERVICE_REQUIRED = u"Defaults!/sbin/service !requiretty"


def patchSudoersFileForOpsi(sudoersFile=SUDOERS_FILE):
	"""
	Patches the sudoers file so opsiconfd and the OPSI file admins can \
call opsi-set-rights.

	:param sudoersFile: The path to the sudoers file.
	"""
	entries = [
		"opsiconfd ALL=NOPASSWD: /usr/bin/opsi-set-rights",
		"%{group} ALL=NOPASSWD: /usr/bin/opsi-set-rights".format(group=FILE_ADMIN_GROUP),
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


	.. versionchanged:: 4.0.6.3

		Add single entry if missing.

	"""
	entries = [element.strip() for element in entries]
	lines = []
	ttyPatchRequired = True
	servicePatchRequired = True

	with codecs.open(sudoersFile, 'r', 'utf-8') as inputFile:
		for line in inputFile:
			if _NO_TTY_REQUIRED_DEFAULT in line:
				ttyPatchRequired = False
			elif _NO_TTY_FOR_SERVICE_REQUIRED in line:
				servicePatchRequired = False

			lines.append(line)

	# Stripping is important to avoid problems with newlines.
	entriesToAdd = set(entries) - set(l.strip() for l in lines)

	ttyPatchRequired = ttyPatchRequired and distributionRequiresNoTtyPatch()
	modifyFile = ttyPatchRequired or servicePatchRequired or entriesToAdd
	if modifyFile:
		LOGGER.notice(u"   Adding sudoers entries for opsi")

	if entriesToAdd:
		for entry in entriesToAdd:
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

	:rtype: bool
	"""
	distributor = Distribution().distributor.lower()

	return bool('redhat' in distributor or 'centos' in distributor)
