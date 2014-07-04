#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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
Testing unbound methods for the backends.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest
import OPSI.Backend.Backend as Backend


class TestReadingMethodInformationTestCase(unittest.TestCase):
	"""
	Testing getArgAndCallString
	"""
	def testGettingSignatureForMethodWithoutArguments(self):
		def foo():
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertFalse(args)
		self.assertFalse(kwargs)

	def testGettingSignatureForMethodWithOnePositionalArgument(self):
		def foo(bar):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar', args)
		self.assertEquals('bar=bar', kwargs)

	def testGettingSignatureForMethodWithMultiplePositionalArguments(self):
		def foo(bar, baz):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar, baz', args)
		self.assertEquals('bar=bar, baz=baz', kwargs)

	def testGettingSignatureForMethodWithKeywordArgumentOnly(self):
		def foo(bar=None):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar=None', args)
		self.assertEquals('bar=bar', kwargs)

	def testGettingSignatureForMethodWithMultipleKeywordArgumentsOnly(self):
		def foo(bar=None, baz=None):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar=None, baz=None', args)
		self.assertEquals('bar=bar, baz=baz', kwargs)

	def testGettingSignatureForMethodWithMixedArguments(self):
		def foo(bar, baz=None):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar, baz=None', args)
		self.assertEquals('bar=bar, baz=baz', kwargs)

	def testSelfAsFirstArgumentIsIgnored(self):
		def foo(self, bar=None):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals('bar=None', args)
		self.assertEquals('bar=bar', kwargs)

	def testArgumentWithStringDefault(self):
		def foo(bar='baz'):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals("bar='baz'", args)
		self.assertEquals('bar=bar', kwargs)

	def testArgumentWithUnicodeDefault(self):
		def foo(bar=u'baz'):
			pass

		(args, kwargs) = Backend.getArgAndCallString(foo)

		self.assertEquals("bar=u'baz'", args)
		self.assertEquals('bar=bar', kwargs)


if __name__ == '__main__':
	unittest.main()
