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

from OPSI.tests.helper.matchers import GreaterThan
from testtools.tests.test_matchers import TestMatchersInterface
from testtools import TestCase

class GreaterThanMatcherTest(TestCase, TestMatchersInterface):

	matches_matcher = GreaterThan(4)
	matches_matches = [5, 9, 1000]
	matches_mismatches = [-5, 0, 2]

	str_examples = [
		("GreaterThan(12)", GreaterThan(12)),
	]

	describe_examples = [
		('5 is not < 4', 4, GreaterThan(5)),
		('4 is not < 4', 4, GreaterThan(4)),
	]
	
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)