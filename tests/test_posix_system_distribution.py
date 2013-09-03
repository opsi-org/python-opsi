#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest
from OPSI.System.Posix import Distribution


class DistributionTestCase(unittest.TestCase):
    DIST_INFO = None
    def setUp(self):
        if self.DIST_INFO is not None:
            self.dist = Distribution(distribution_information=self.DIST_INFO)
        else:
            self.dist = Distribution()

    def tearDown(self):
        self.dist

    def testReadingVersionDoesNotFailAndIsNotEmpty(self):
        self.assertNotEqual(None, self.dist.version)
        self.assertNotEqual(tuple(), self.dist.version)

    def test__repr__has_information(self):
        if self.DIST_INFO is None:
            try:
                raise unittest.SkipTest('No specific distribution information set.')
            except AttributeError:
                print('Probably running an Python < 2.7. Skipping...')
                return

        for part in self.DIST_INFO:
            self.assertTrue(part in repr(self.dist),
                'Expected "{0}" to be in {1}.'.format(part, self.dist)
            )


class DebianSqueezeTestCase(DistributionTestCase):
    DIST_INFO = ('debian', '6.0.7', '')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((6, 0, 7), self.dist.version)


class DebianWheezyTestCase(DistributionTestCase):
    DIST_INFO = ('debian', '7.1', '')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((7, 1), self.dist.version)


class CentOS64TestCase(DistributionTestCase):
    DIST_INFO = ('CentOS', '6.4', 'Final')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((6, 4), self.dist.version)


class OpenSuse113TestCase(DistributionTestCase):
    DIST_INFO = ('openSUSE ', '11.3', 'i586')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((11, 3), self.dist.version)


class OpenSuse121TestCase(DistributionTestCase):
    DIST_INFO = ('openSUSE ', '12.1', 'x86_64')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((12, 1), self.dist.version)


class RedHatEnterpriseLinux6TestCase(DistributionTestCase):
    DIST_INFO = ('Red Hat Enterprise Linux Server', '6.4', 'Santiago')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((6, 4), self.dist.version)


class SuseLinuxEnterpriseLinuxServer11TestCase(DistributionTestCase):
    DIST_INFO = ('SUSE Linux Enterprise Server ', '11', 'x86_64')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((11, ), self.dist.version)


class UbuntuRaringTestCase(DistributionTestCase):
    DIST_INFO = ('Ubuntu', '13.04', 'raring')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((13, 4), self.dist.version)


class UbuntuPreciseTestCase(DistributionTestCase):
    DIST_INFO = ('Ubuntu', '12.04', 'precise')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((12, 4), self.dist.version)


class UCSHornLeheTestCase(DistributionTestCase):
    DIST_INFO = ('"Univention"', '"3.0-2 errata145"', '"Horn-Lehe"')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((3, 0), self.dist.version)


class UCSFinndorfTestCase(DistributionTestCase):
    DIST_INFO = ('"Univention"', '"3.1-1 errata163"', '"Findorff"')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((3, 1), self.dist.version)


if __name__ == '__main__':
    unittest.main()