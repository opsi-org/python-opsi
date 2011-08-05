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

import operator
from testtools.matchers import Matcher, Mismatch, _BinaryComparison

class GreaterThan(_BinaryComparison):
	"""Matches if the item is greater than the matchers reference object."""

	comparator = operator.__gt__
	mismatch_string = 'is not <'
	
class In(Matcher):
	
	def __init__(self, haystack):
		self.haystack = haystack
	
	def match(self, needle):
		
		if needle in self.haystack:
			return None
		return Mismatch("No value %s was found in haystack %s" %(needle, self.haystack))