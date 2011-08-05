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