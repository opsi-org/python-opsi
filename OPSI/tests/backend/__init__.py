"""
   = = = = = = = = = = = = = = = = = = =
   =  opsi python library - test suite =
   = = = = = = = = = = = = = = = = = = =

   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org

   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH

   http://www.uib.de/

   All rights reserved.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

   @copyright:	uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

__unittest = True

import unittest

def test_suite():
	from OPSI.tests.backend import (
		test_acl,
		test_modificationtracker,
		)
	modules = [
		test_acl,
		test_modificationtracker,
		]
	suites = map(lambda x: x.test_suite(), modules)
	return unittest.TestSuite(suites)
