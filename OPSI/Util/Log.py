# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2019 uib GmbH <info@uib.de>

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
Utilities for working with logs.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Types import forceInt

__all__ = ('truncateLogData', )


def truncateLogData(data, maxSize):
	"""
	Truncating `data` to not be longer than `maxSize` chars.

	:param data: Text
	:type data: str
	:param maxSize: The maximum size that is allowed in chars.
	:type maxSize: int
	"""
	maxSize = forceInt(maxSize)
	dataLength = len(data)
	if dataLength > maxSize:
		start = data.find('\n', dataLength - maxSize)
		if start == -1:
			start = dataLength - maxSize
		return data[start:].lstrip()

	return data
