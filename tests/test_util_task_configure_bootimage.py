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
Testing functionality of OPSI.Util.Task.ConfigureBootimage

:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import os.path
import pytest

import OPSI.Util.Task.ConfigureBootimage as ConfigureBootimage

from .helpers import mock

def testMenuFiles():
	with mock.patch('os.path.exists', lambda x:True):
		defaultMenu, grubmenu = configureBootimage.getMenuFiles()
		assert defaultMenu == u'/tftpboot/linux/pxelinux.cfg/default.menu'
		assert grubMenu == u'/tftpboot/grub/grub.cfg'
