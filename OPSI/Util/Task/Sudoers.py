#!/usr/bin/env python
#-*- coding: utf-8 -*-

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

logger = Logger()


def patchSudoersFileForOpsi(sudoersFile=u'/etc/sudoers'):
	"""
	Patches the sudoers file so opsiconfd and the OPSI file admins can \
call opsi-set-rights.

	:param sudoersFile: The path to the sudoers file.
	"""
	#get opsifileadmins groupname!!!!
	entries = [
		"opsiconfd ALL=NOPASSWD: %s" % "/usr/bin/opsi-set-rights",
		"%%%s ALL=NOPASSWD: %s" % (FILE_ADMIN_GROUP, "/usr/bin/opsi-set-rights"),
	]
	lines = []
	found = False

	with codecs.open(sudoersFile, 'r', 'utf-8') as inputFile:
		for line in inputFile:
			for entry in entries:
				if entry in line:
					found = True

			lines.append(line)

	if not found:
		logger.notice(u"   Creating backup of %s" % sudoersFile)
		shutil.copy(sudoersFile, sudoersFile + u'.' + time.strftime("%Y-%m-%d_%H:%M"))

		logger.notice(u"   Adding sudoers entries for opsi")
		for entry in entries:
			lines.append("{0}\n".format(entry))

		distributor = Distribution().distributor
		distributor = distributor.lower()
		if ('scientificsl' in distributor or 'redhat' in distributor
			or 'centos' in distributor or 'sme' in distributor):

			lines.append(u"Defaults:opsiconfd !requiretty\n")

		lines.append('\n')

		logger.notice(u"   Writing new %s" % sudoersFile)
		with codecs.open(sudoersFile, 'w', 'utf-8') as outputFile:
			outputFile.writelines(lines)
