#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Mixins to test the functionality of backends.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Backend import BackendTestsMixin
from .Configs import ConfigTestsMixin, ConfigStateTestsMixin
from .Products import (ProductPropertiesTestMixin, ProductDependenciesTestMixin,
    ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin)


class BackendTestMixin(ConfigStateTestsMixin, ProductPropertiesTestMixin,
    ProductDependenciesTestMixin, ConfigTestsMixin,
    ProductsTestMixin, ProductsOnClientTestsMixin, ProductsOnDepotTestsMixin,
    ProductPropertyStateTestsMixin, BackendTestsMixin):
    """
    Class collecting functional backend tests.

    MultiThreadingTestMixin and BackendPerformanceTest are excluded.
    Please inherit them manually if you feel the need.
    """
