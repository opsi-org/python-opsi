#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Backend.BackendManager import BackendManager, ConfigDataBackend


class BackendExtensionTestCase(unittest.TestCase):
    def testBackendManagerDispatchesCallsToExtensionClass(self):
        """
        Make sure that calls are dispatched to the extension class.
        These calls should not fail.
        """
        class TestClass(object):
            def testMethod(self, y):
                print("Working test.")
                print('Argument: {0}'.format(y))
                print('This is me: {0}'.format(self))

            def testMethod2(self):
                print('Getting all that shiny options...')
                print(self.backend_getOptions())

        cdb = ConfigDataBackend()
        bm = BackendManager(backend=cdb, extensionClass=TestClass)
        bm.testMethod('yyyyyyyy')
        bm.testMethod2()


if __name__ == '__main__':
    unittest.main()
