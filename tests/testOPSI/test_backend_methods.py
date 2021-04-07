# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing unbound methods for the backends.
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
