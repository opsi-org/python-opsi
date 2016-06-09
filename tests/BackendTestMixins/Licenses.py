#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Backend mixin for testing the functionality of working with licenses.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from OPSI.Object import LicensePool

from .Clients import ClientsMixin
from .Products import ProductsMixin


class LicensesMixin(ClientsMixin, ProductsMixin):
    def setUpLicensePool(self):
        self.setUpProducts()
        self.createProductsOnBackend()

        self.licensePool1 = LicensePool(
            id=u'license_pool_1',
            description=u'licenses for product1',
            productIds=self.product1.getId()
        )

        self.licensePool2 = LicensePool(
            id=u'license_pool_2',
            description=u'licenses for product2',
            productIds=self.product2.getId()
        )
        self.licensePools = [self.licensePool1, self.licensePool2]
