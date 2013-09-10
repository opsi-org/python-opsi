#!/usr/bin/env python
#-*- coding: utf-8 -*-

import random
import unittest

from OPSI.Util import ipAddressInNetwork, objectToHtml
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


if __name__ == '__main__':
    unittest.main()
