# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2018 uib GmbH <info@uib.de>

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
Backends.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Backend import describeInterface, Backend
from .ConfigData import ConfigDataBackend
from .Extended import (
	getArgAndCallString, ExtendedBackend, ExtendedConfigDataBackend)
from .ModificationTracking import (
	ModificationTrackingBackend, BackendModificationListener)

__all__ = (
	'describeInterface', 'getArgAndCallString',
	'Backend', 'ExtendedBackend', 'ConfigDataBackend',
	'ExtendedConfigDataBackend',
	'ModificationTrackingBackend', 'BackendModificationListener'
)