#! /usr/bin/env python
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
Testing the work with the DHCPD configuration files.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import unittest

from OPSI.Util.File import DHCPDConfFile

from .helpers import createTemporaryTestfile


class DHCPDConfFileTestCase(unittest.TestCase):
    def testParsingFile(self):
        testExample = os.path.join(
            os.path.dirname(__file__), 'testdata',
            'util', 'dhcpd', 'dhcpd_1.conf'
        )

        with createTemporaryTestfile(testExample) as fileName:
            confFile = DHCPDConfFile(fileName)
            confFile.parse()


if __name__ == '__main__':
    unittest.main()
