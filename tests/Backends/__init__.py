# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2018 uib GmbH <info@uib.de>

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
Basics for backend tests.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from contextlib import contextmanager

from OPSI.Backend.Backend import ExtendedConfigDataBackend

__all__ = ('getTestBackend', 'BackendMixin')


@contextmanager
def getTestBackend(extended=False):
    """
    Get a backend for tests.

    Each call to this will return a different backend.

    If `extended` is True the returned backend will be an
    `ExtendedConfigDataBackend`.
    """
    from .File import getFileBackend  # lazy import

    with getFileBackend() as backend:
        if extended:
            backend = ExtendedConfigDataBackend(backend)

        backend.backend_createBase()
        try:
            yield backend
        finally:
            backend.backend_deleteBase()


class BackendMixin(object):
    """
    Base class for backend test mixins.

    :param CREATES_INVENTORY_HISTORY: Set to true if the backend keeps a \
history of the inventory. This will affects tests!
    :type CREATES_INVENTORY_HISTORY: bool
    """

    CREATES_INVENTORY_HISTORY = False

    def setUpBackend(self):
        pass

    def tearDownBackend(self):
        pass
