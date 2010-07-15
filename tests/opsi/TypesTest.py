
from opsidevtools.unittest.lib.unittest2.case import TestCase
from OPSI.Types import *


class TypesTestCase(TestCase):
	
	def test_argsDecoratorClassConstruction(self):
		
		raise Excpetion("produces syntax error on python 2.5")
		#@args("somearg", "someOtherArg")
		#class SomeClass(object):
		#	def __init__(self, **kwargs):
		#		pass
		
		someObj = SomeClass()
		try:
			self.assertIsNone(someObj.somearg, "Expected somearg to be None, but got %s instead" % someObj.somearg)
			self.assertIsNone(someObj.someOtherArg, "Expected someOtherArg to be None, but got %s instead" % someObj.someOtherArg)
		except AttributeError, e:
			self.fail(e)
			
		@args("somearg", someOtherArg=forceInt)
		class SomeOtherClass(object):
			def __init__(self, **kwargs):
				pass
		
		someOtherObj = SomeOtherClass(someOtherArg="5")
		

		
		try:
			self.assertIsNone(someOtherObj.somearg, "Expected somearg to be None, but got %s instead" % someOtherObj.somearg)
			self.assertEqual(5, someOtherObj.someOtherArg, "Expected someOtherArg to be %d, but got %s instead." %(5, someOtherObj.someOtherArg))
		except AttributeError,e:
			self.fail(e)
			
	def test_argsDecoratorWithPrivateArgs(self):
		
		@args("_somearg", "_someOtherArg")
		class SomeClass(object):
			def __init__(self, **kwargs):
				pass
		
		someObj = SomeClass(somearg=5)
		try:
			self.assertEqual(5, someObj._somearg, "Expected somearg to be %d, but got %s instead" % (5, someObj._somearg))
			self.assertIsNone(someObj._someOtherArg, "Expected someOtherArg to be None, but got %s instead" % someObj._someOtherArg)
		except AttributeError, e:
			self.fail(e)