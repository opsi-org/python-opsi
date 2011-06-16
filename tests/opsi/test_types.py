
from opsidevtools.unittest.lib.unittest2.case import TestCase
from opsidevtools.unittest.lib import unittest2 as unittest
from OPSI.Types import *
import sys

class TypesTestCase(TestCase):
	
	@unittest.skipIf(sys.version_info < (2, 6), "Class decorators are not supported in python < 2.6")
	def test_argsDecoratorClassConstruction(self):

		# will raise SyntaxError on python < 2.6 so we need to create this on demand
		exec(' \
		@args("somearg", "someOtherArg") \
		class SomeClass(object): \
			def __init__(self, **kwargs): \
				pass'
		)
			
		someObj = SomeClass()
		try:
			self.assertIsNone(someObj.somearg, "Expected somearg to be None, but got %s instead" % someObj.somearg)
			self.assertIsNone(someObj.someOtherArg, "Expected someOtherArg to be None, but got %s instead" % someObj.someOtherArg)
		except AttributeError, e:
			self.fail(e)
		
		# will raise SyntaxError on python < 2.6 so we need to create this on demand
		exec(' \
		@args("somearg", someOtherArg=forceInt) \
		class SomeClass(object): \
			def __init__(self, **kwargs): \
				pass'
		)

		someOtherObj = SomeOtherClass(someOtherArg="5")
		

		
		try:
			self.assertIsNone(someOtherObj.somearg, "Expected somearg to be None, but got %s instead" % someOtherObj.somearg)
			self.assertEqual(5, someOtherObj.someOtherArg, "Expected someOtherArg to be %d, but got %s instead." %(5, someOtherObj.someOtherArg))
		except AttributeError,e:
			self.fail(e)
			
	@unittest.skipIf(sys.version_info < (2, 6), "Class decorators are not supported in python < 2.6")
	def test_argsDecoratorWithPrivateArgs(self):
		
		# will raise SyntaxError on python < 2.6 so we need to create this on demand
		exec(' \
		@args("_somearg", "_someOtherArg") \
		class SomeClass(object): \
			def __init__(self, **kwargs): \
				pass'
		)

		someObj = SomeClass(somearg=5)
		try:
			self.assertEqual(5, someObj._somearg, "Expected somearg to be %d, but got %s instead" % (5, someObj._somearg))
			self.assertIsNone(someObj._someOtherArg, "Expected someOtherArg to be None, but got %s instead" % someObj._someOtherArg)
		except AttributeError, e:
			self.fail(e)