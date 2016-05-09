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
Testing Distribution functionality from OPSI.System.Posix

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .helpers import unittest

from OPSI.System.Posix import Distribution


class DistributionTestCase(unittest.TestCase):
    DIST_INFO = None

    @classmethod
    def setUpClass(self):
        if self.DIST_INFO is not None:
            self.dist = Distribution(distribution_information=self.DIST_INFO)
        else:
            self.dist = Distribution()

    @classmethod
    def tearDownClass(self):
        del self.dist

    def testReadingVersionDoesNotFailAndIsNotEmpty(self):
        self.assertNotEqual(None, self.dist.version)
        self.assertNotEqual(tuple(), self.dist.version)

    def test__repr__has_information(self):
        if self.DIST_INFO is None:
            raise unittest.SkipTest('No specific distribution information set.')

        for part in self.DIST_INFO:
            self.assertTrue(part.strip() in repr(self.dist),
                'Expected "{0}" to be in {1}.'.format(part, repr(self.dist))
            )

    def testDistributorIsNotNone(self):
        self.assertNotEqual(None, self.dist.distributor)


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


class RHEL7TestCase(DistributionTestCase):
    DIST_INFO = ('Red Hat Enterprise Linux Server', '7.0', 'Maipo')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((7, 0), self.dist.version)


class OpenSuse113TestCase(DistributionTestCase):
    DIST_INFO = ('openSUSE ', '11.3', 'i586')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((11, 3), self.dist.version)

    def testDistributionNameGetsTruncated(self):
        self.assertEquals('openSUSE', self.dist.distribution)


class OpenSuse121TestCase(DistributionTestCase):
    DIST_INFO = ('openSUSE ', '12.1', 'x86_64')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((12, 1), self.dist.version)

    def testDistributionNameGetsTruncated(self):
        self.assertEquals('openSUSE', self.dist.distribution)


class RedHatEnterpriseLinux6TestCase(DistributionTestCase):
    DIST_INFO = ('Red Hat Enterprise Linux Server', '6.4', 'Santiago')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((6, 4), self.dist.version)


class SuseLinuxEnterpriseLinuxServer11TestCase(DistributionTestCase):
    DIST_INFO = ('SUSE Linux Enterprise Server ', '11', 'x86_64')

    def testReadingVersionIsCorrect(self):
        self.assertEqual((11, ), self.dist.version)

    def testDistributionNameGetsTruncated(self):
        self.assertEquals('SUSE Linux Enterprise Server', self.dist.distribution)


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
