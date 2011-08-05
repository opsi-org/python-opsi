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

import sys
from weakref import proxy

from OPSI.Util import _functools as functools
import testtools

def capture(*args, **kw):
	return args, kw

def signature(part):
	return (part.func, part.args, part.keywords, part.__dict__)

class TestPartial(testtools.TestCase):

	def test_basic_examples(self):
		p = functools.partial(capture, 1, 2, a=10, b=20)
		self.assertEqual(p(3, 4, b=30, c=40),
						 ((1, 2, 3, 4), dict(a=10, b=30, c=40)))
		p = functools.partial(map, lambda x: x*10)
		self.assertEqual(p([1,2,3,4]), [10, 20, 30, 40])

	def test_attributes(self):
		p = functools.partial(capture, 1, 2, a=10, b=20)
		# attributes should be readable
		self.assertEqual(p.func, capture)
		self.assertEqual(p.args, (1, 2))
		self.assertEqual(p.keywords, dict(a=10, b=20))
		# attributes should not be writable
		if not isinstance(functools.partial, type):
			return
		self.assertRaises(TypeError, setattr, p, 'func', map)
		self.assertRaises(TypeError, setattr, p, 'args', (1, 2))
		self.assertRaises(TypeError, setattr, p, 'keywords', dict(a=1, b=2))

		p = functools.partial(hex)
		try:
			del p.__dict__
		except TypeError:
			pass
		else:
			self.fail('partial object allowed __dict__ to be deleted')

	def test_argument_checking(self):
		self.assertRaises(TypeError, functools.partial)	 # need at least a func arg
		try:
			functools.partial(2)()
		except TypeError:
			pass
		else:
			self.fail('First arg not checked for callability')

	def test_protection_of_callers_dict_argument(self):
		# a caller's dictionary should not be altered by partial
		def func(a=10, b=20):
			return a
		d = {'a':3}
		p = functools.partial(func, a=5)
		self.assertEqual(p(**d), 3)
		self.assertEqual(d, {'a':3})
		p(b=7)
		self.assertEqual(d, {'a':3})

	def test_arg_combinations(self):
		# exercise special code paths for zero args in either partial
		# object or the caller
		p = functools.partial(capture)
		self.assertEqual(p(), ((), {}))
		self.assertEqual(p(1,2), ((1,2), {}))
		p = functools.partial(capture, 1, 2)
		self.assertEqual(p(), ((1,2), {}))
		self.assertEqual(p(3,4), ((1,2,3,4), {}))

	def test_kw_combinations(self):
		# exercise special code paths for no keyword args in
		# either the partial object or the caller
		p = functools.partial(capture)
		self.assertEqual(p(), ((), {}))
		self.assertEqual(p(a=1), ((), {'a':1}))
		p = functools.partial(capture, a=1)
		self.assertEqual(p(), ((), {'a':1}))
		self.assertEqual(p(b=2), ((), {'a':1, 'b':2}))
		# keyword args in the call override those in the partial object
		self.assertEqual(p(a=3, b=2), ((), {'a':3, 'b':2}))

	def test_positional(self):
		# make sure positional arguments are captured correctly
		for args in [(), (0,), (0,1), (0,1,2), (0,1,2,3)]:
			p = functools.partial(capture, *args)
			expected = args + ('x',)
			got, empty = p('x')
			self.assertTrue(expected == got and empty == {})

	def test_keyword(self):
		# make sure keyword arguments are captured correctly
		for a in ['a', 0, None, 3.5]:
			p = functools.partial(capture, a=a)
			expected = {'a':a,'x':None}
			empty, got = p(x=None)
			self.assertTrue(expected == got and empty == ())

	def test_no_side_effects(self):
		# make sure there are no side effects that affect subsequent calls
		p = functools.partial(capture, 0, a=1)
		args1, kw1 = p(1, b=2)
		self.assertTrue(args1 == (0,1) and kw1 == {'a':1,'b':2})
		args2, kw2 = p()
		self.assertTrue(args2 == (0,) and kw2 == {'a':1})

	def test_error_propagation(self):
		def f(x, y):
			x // y
		self.assertRaises(ZeroDivisionError, functools.partial(f, 1, 0))
		self.assertRaises(ZeroDivisionError, functools.partial(f, 1), 0)
		self.assertRaises(ZeroDivisionError, functools.partial(f), 1, 0)
		self.assertRaises(ZeroDivisionError, functools.partial(f, y=0), 1)

	def test_weakref(self):
		f = functools.partial(int, base=16)
		p = proxy(f)
		self.assertEqual(f.func, p.func)
		f = None
		self.assertRaises(ReferenceError, getattr, p, 'func')

	def test_with_bound_and_unbound_methods(self):
		data = map(str, range(10))
		join = functools.partial(str.join, '')
		self.assertEqual(join(data), '0123456789')
		join = functools.partial(''.join)
		self.assertEqual(join(data), '0123456789')

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)