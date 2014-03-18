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
Testing BackendManager.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

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
