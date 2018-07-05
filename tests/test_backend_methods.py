# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2018 uib GmbH <info@uib.de>

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

import OPSI.Backend.Backend as Backend


def testGettingSignatureForMethodWithoutArguments():
	def foo():
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert not args
	assert not kwargs


def testGettingSignatureForMethodWithOnePositionalArgument():
	def foo(bar):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar' == args
	assert 'bar=bar' == kwargs


def testGettingSignatureForMethodWithMultiplePositionalArguments():
	def foo(bar, baz):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar, baz' == args
	assert 'bar=bar, baz=baz' == kwargs


def testGettingSignatureForMethodWithKeywordArgumentOnly():
	def foo(bar=None):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar=None' == args
	assert 'bar=bar' == kwargs


def testGettingSignatureForMethodWithMultipleKeywordArgumentsOnly():
	def foo(bar=None, baz=None):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar=None, baz=None' == args
	assert 'bar=bar, baz=baz' == kwargs


def testGettingSignatureForMethodWithMixedArguments():
	def foo(bar, baz=None):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar, baz=None' == args
	assert 'bar=bar, baz=baz' == kwargs


def testSelfAsFirstArgumentIsIgnored():
	def foo(self, bar=None):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert 'bar=None' == args
	assert 'bar=bar' == kwargs


def testArgumentWithStringDefault():
	def foo(bar='baz'):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "bar='baz'" == args
	assert 'bar=bar' == kwargs


def testArgumentWithUnicodeDefault():
	def foo(bar=u'baz'):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "bar='baz'" == args
	assert 'bar=bar' == kwargs


def testArgumentWithVariableArgumentCount():
	def foo(*bar):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "*bar" == args
	assert '*bar' == kwargs


def testArgumentWithPositionalArgumentAndVariableArgumentCount():
	def foo(bar, *baz):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "bar, *baz" == args
	assert 'bar=bar, *baz' == kwargs


def testVariableKeywordArguments():
	def foo(**bar):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "**bar" == args
	assert '**bar' == kwargs


def testMethodWithAllTypesOfArguments():
	def foo(ironman, blackWidow=True, *hulk, **deadpool):
		pass

	args, kwargs = Backend.getArgAndCallString(foo)

	assert "ironman, blackWidow=True, *hulk, **deadpool" == args
	assert 'ironman=ironman, blackWidow=blackWidow, *hulk, **deadpool' == kwargs
