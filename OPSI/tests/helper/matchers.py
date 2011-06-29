import operator
from testtools.matchers import _BinaryComparison

class GreaterThan(_BinaryComparison):
	"""Matches if the item is greater than the matchers reference object."""

	comparator = operator.__gt__
	mismatch_string = 'is not <'