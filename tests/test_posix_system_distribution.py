#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest
from OPSI.System.Posix import Distribution


class DistributionTestCase(unittest.TestCase):
    def setUp(self):
        self.dist = Distribution()

    def tearDown(self):
        self.dist

    def testReadingVersionDoesNotFailAndIsNotEmpty(self):
        self.assertNotEqual(None, self.dist.version)
        self.assertNotEqual(tuple(), self.dist.version)


class DebianSqueezeTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('debian', '6.0.7', ''))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((6, 0, 7), self.dist.version)


class DebianWheezyTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('debian', '7.1', ''))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((7, 1), self.dist.version)


class UbuntuRaringTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('Ubuntu', '13.04', 'raring'))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((13, 4), self.dist.version)


class UbuntuPreciseTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('Ubuntu', '12.04', 'precise'))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((12, 4), self.dist.version)


class UCSHornLeheTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('"Univention"', '"3.0-2 errata145"', '"Horn-Lehe"'))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((3, 0), self.dist.version)


class UCSFinndorfTestCase(DistributionTestCase):
    def setUp(self):
        self.dist = Distribution(distribution_information=('"Univention"', '"3.1-1 errata163"', '"Findorff"'))

    def testReadingVersionIsCorrect(self):
        self.assertEqual((3, 1), self.dist.version)





if __name__ == '__main__':
    unittest.main()