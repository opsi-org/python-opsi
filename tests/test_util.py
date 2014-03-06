#!/usr/bin/env python
#-*- coding: utf-8 -*-

import random
import os
import unittest

from OPSI.Util import (compareVersions, flattenSequence, formatFileSize,
    generateOpsiHostKey, getGlobalConfig, ipAddressInNetwork, objectToHtml,
    randomString)
from OPSI.Object import LocalbootProduct


class IPAddressInNetwork(unittest.TestCase):
    def testNetworkWithSlashIntNotation(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/16'))
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/23'))
        self.assertFalse(ipAddressInNetwork('10.10.1.1', '10.10.0.0/24'))
        self.assertFalse(ipAddressInNetwork('10.10.1.1', '10.10.0.0/25'))

    def testIpAddressInNetworkWithEmptyNetworkMask(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '0.0.0.0/0'))

    def testIpAddressInNetworkWithFullNetmask(self):
        self.assertTrue(ipAddressInNetwork('10.10.1.1', '10.10.0.0/255.240.0.0'))


class ObjectToHTMLTestCase(unittest.TestCase):
    def testWorkingWithManyObjects(self):
        obj = []
        for i in range(1000):
            obj.append(
    			LocalbootProduct(
					id='product%d' % i,
					productVersion=random.choice(('1.0', '2', 'xxx', '3.1', '4')),
					packageVersion=random.choice(('1', '2', 'y', '3', '10', 11, 22)),
					name='Product %d' % i,
					licenseRequired=random.choice((None, True, False)),
					setupScript=random.choice(('setup.ins', None)),
					uninstallScript=random.choice(('uninstall.ins', None)),
					updateScript=random.choice(('update.ins', None)),
					alwaysScript=random.choice(('always.ins', None)),
					onceScript=random.choice(('once.ins', None)),
					priority=random.choice((-100, -90, -30, 0, 30, 40, 60, 99)),
					description=random.choice(('Test product %d' % i, 'Some product', '--------', '', None)),
					advice=random.choice(('Nothing', 'Be careful', '--------', '', None)),
					changelog=None,
					windowsSoftwareIds=None
			)
          )

        objectToHtml(obj, level=0)


class UtilTestCase(unittest.TestCase):
    """
    General tests for functions in the Util module.
    """
    def test_flattenSequence(self):
        self.assertEqual([1, 2], flattenSequence((1, [2])))
        self.assertEqual([1, 2, 3], flattenSequence((1, [2, (3, )])))
        self.assertEqual([1, 2, 3], flattenSequence(((1, ),(2, ), 3)))

    def test_formatFileSize(self):
        self.assertEqual('123', formatFileSize(123))
        self.assertEqual('1K', formatFileSize(1234))
        self.assertEqual('1M', formatFileSize(1234567))
        self.assertEqual('1G', formatFileSize(1234567890))

    def testRandomString(self):
        self.assertEqual(10, len(randomString(10)))
        self.assertNotEqual('', randomString(1).strip())
        self.assertEqual('', randomString(0).strip())
        self.assertEqual(5*'a', randomString(5, characters='a'))

    def testGenerateOpsiHostKeyIs32CharsLong(self):
        self.assertEqual(32, len(generateOpsiHostKey()))
        self.assertEqual(32, len(generateOpsiHostKey(forcePython=True)))


class CompareVersionTestCase(unittest.TestCase):
    def testComparingVersionsOfSameSize(self):
        self.assertTrue(compareVersions('1.0', '<', '2.0'))

    def testComparingWithoutGivingOperatorDefaultsToEqual(self):
        self.assertTrue(compareVersions('1.0', '', '1.0'))
        self.assertFalse(compareVersions('1', '', '2'))

    def testComparingWithOneEqualitySignWork(self):
        self.assertTrue(compareVersions('1.0', '=', '1.0'))

    def testUsingUnknownOperatorFails(self):
        self.assertRaises(Exception, compareVersions, '1', 'asdf', '2')
        self.assertRaises(Exception, compareVersions, '1', '+-', '2')
        self.assertRaises(Exception, compareVersions, '1', '<>', '2')
        self.assertRaises(Exception, compareVersions, '1', '!=', '2')

    def testIgnoringVersionsWithWaveInThem(self):
        self.assertTrue(compareVersions('1.0~20131212', '<', '2.0~20120101'))
        self.assertTrue(compareVersions('1.0~20131212', '==', '1.0~20120101'))

    def testUsingInvalidVersionStringsFails(self):
        self.assertRaises(Exception, compareVersions, 'abc-1.2.3-4', '==', '1.2.3-4')
        self.assertRaises(Exception, compareVersions, '1.2.3-4', '==', 'abc-1.2.3-4')

    def testComparingWorksWithLettersInVersionString(self):
        self.assertTrue(compareVersions('1.0.a', '<', '1.0.b'))
        self.assertTrue(compareVersions('a.b', '>', 'a.a'))

    def testComparisonsWithDifferntDepthsAreMadeTheSameDepth(self):
        self.assertTrue(compareVersions('1.1.0.1', '>', '1.1'))
        self.assertTrue(compareVersions('1.1', '<', '1.1.0.1'))

    def testPackageVersionsAreComparedAswell(self):
        self.assertTrue(compareVersions('1-2', '<', '1-3'))
        self.assertTrue(compareVersions('1-2.0', '<', '1-2.1'))


class GetGlobalConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.testFile = os.path.join(
            os.path.dirname(__file__), 'testdata', 'util', 'fake_global.conf'
        )

    def tearDown(self):
        del self.testFile

    def testCommentsAreIgnored(self):
        self.assertEqual("no", getGlobalConfig('comment', self.testFile))

    def testLinesNeedAssignments(self):
        self.assertEqual(None, getGlobalConfig('this', self.testFile))

    def testReadingValues(self):
        self.assertEqual("value", getGlobalConfig('keyword', self.testFile))
        self.assertEqual(
            "this works too",
            getGlobalConfig('value with spaces', self.testFile)
        )
        self.assertEqual(
            "we even can include a = and it works",
            getGlobalConfig('advanced value', self.testFile)
        )

    def testFileNotFoundExitsGracefully(self):
        self.assertEqual(None, getGlobalConfig('dontCare', 'nonexistingFile'))


if __name__ == '__main__':
    unittest.main()
