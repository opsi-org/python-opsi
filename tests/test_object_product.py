#!/usr/bin/env python
#-*- coding: utf-8 -*-

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
