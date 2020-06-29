# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2019-2020 uib GmbH <info@uib.de>

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
Testing the opsi-package-updater functionality.

:license: GNU Affero General Public License version 3
"""

import pytest

from OPSI.Util.Task.UpdatePackages.Repository import ProductRepositoryInfo

def testRepositoryInfo_checkingParameterDefaults():
	pri = ProductRepositoryInfo(name="test_repo", baseUrl="http://example.com")

	assert pri.name == "test_repo"
	assert pri.includes == []
	assert pri.excludes == []
	assert pri.dirs == []
	assert pri.autosetupexcludes == []