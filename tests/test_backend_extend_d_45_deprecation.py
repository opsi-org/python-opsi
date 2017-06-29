#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2017 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded legacy extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/45_deprecated.conf``.

These extension shows methods that will be removed in the future.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""


def testIsLegacyOpsi(backendManager):
    assert backendManager.isLegacyOpsi() is False


def testIsOpsi35(backendManager):
    assert backendManager.isOpsi35() is False


def testIsOpsi4(backendManager):
    assert backendManager.isOpsi4() is True
