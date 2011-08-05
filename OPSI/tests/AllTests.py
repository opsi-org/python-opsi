# -*- coding: utf-8 -*-
"""
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope thatf it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright: uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

__unittest = True

from backend.FileBackendTest import FileBackendTestCase
from backend.MySQLTest import MySQLTestCase
from backend.SQLiteTest import SQLiteTestCase
from backend.LdapTest import LdapTestCase
from backend.JsonRPCTest import JSONRPCTestCase
from backend.HostControlTest import HostControlTestCase
#from OPSI.Logger import *

#logger = Logger()
#logger.setSyslogLevel(LOG_NONE)
#logger.setFileLevel(LOG_NONE)
#logger.setConsoleLevel(LOG_DEBUG2)
#logger.setConsoleColor(True)

from opsidevtools.unittest.lib.unittest2.suite import TestSuite
from opsidevtools.unittest.lib.unittest2.case import TestCase
import opsidevtools.unittest.lib.unittest2

test_cases = (	FileBackendTestCase,
		MySQLTestCase,
		#SQLiteTestCase,
		LdapTestCase,
		JSONRPCTestCase,
		HostControlTestCase)

def load_tests(loader, tests, pattern):
	suite = TestSuite()
	for test_class in test_cases:
		tests = loader.loadTestsFromTestCase(test_class)
		suite.addTests(tests)
	return suite
