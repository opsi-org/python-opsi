# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2019 uib GmbH <info@uib.de>

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
Various important configuration values.

This module should be used to refer to often used values in a consistent
way instead of hardcoding the values.

If new values are added they must be added that the module stays
functional independen of the current underlying system.

These values are not intended to be changed on-the-fly!
Doing so might result in unforseen problems and is strongly discouraged!

:copyright:	uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""


# Group used to identify members whits administrative rights in opsi
OPSI_ADMIN_GROUP = "opsiadmin"

# Default user when accessing the opsi depot
DEFAULT_DEPOT_USER = "pcpatch"

# Default home dir of depot user
DEFAULT_DEPOT_USER_HOME = "/var/lib/opsi"

# Path to global opsi configuration file
OPSI_GLOBAL_CONF = "/etc/opsi/global.conf"

try:
	from OPSI.Util.File.Opsi import OpsiConfFile
	FILE_ADMIN_GROUP = OpsiConfFile().getOpsiFileAdminGroup()
except Exception:
	# Use "pcpatch" if group exists otherwise use the new default "opsifileadmins"
	try:
		import grp
		grp.getgrnam("pcpatch")
		FILE_ADMIN_GROUP = "pcpatch"
	except (KeyError, ImportError):
		FILE_ADMIN_GROUP = "opsifileadmins"

# User that is running opsiconfd.
try:
	from opsiconfd.config import config
	OPSICONFD_USER = config.run_as_user
except Exception:
	OPSICONFD_USER = "opsiconfd"
