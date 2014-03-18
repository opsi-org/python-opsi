#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing OPSI.Object.Product

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Object import Product

class ProductTestCase(unittest.TestCase):
    def setUp(self):
        self.product = Product(
            id='new_prod',
            name='New Product for Tests',
            productVersion='1.0',
            packageVersion='1.0'
        )

    def tearDown(self):
        del self.product

    def testLongNameCanBeSetAndRead(self):
        """
        Namens with a length of more than 128 characters can are supported.
        """
        newName = (
            u'This is a very long name with 128 characters to test the '
            u'creation of long product names that should work now but '
            u'were limited b4'
        )

        self.product.setName(newName)

        nameFromProd = self.product.getName()

        self.assertEqual(newName, nameFromProd)
        self.assertEqual(128, len(nameFromProd))
