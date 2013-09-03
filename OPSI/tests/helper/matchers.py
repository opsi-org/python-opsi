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

from testtools.matchers import Matcher, Mismatch
from testtools.matchers import GreaterThan  # This is here for backwards compat

class In(Matcher):

	def __init__(self, haystack):
		self.haystack = haystack

	def match(self, needle):

		if needle in self.haystack:
			return None
		return Mismatch("No value %s was found in haystack %s" %(needle, self.haystack))

	def __str__(self):
		return "%s(%r)" % (self.__class__.__name__, self.haystack)
