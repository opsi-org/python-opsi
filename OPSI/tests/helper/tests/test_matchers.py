
from OPSI.tests.helpers.matchers import GreaterThan
from testtools.tests.test_matchers import TestMatchersInterface
from testtools import TestCase

class GreaterThanMatcherTest(TestCase, TestMatchersInterface):

	matches_matcher = GreaterThan(4)
	matches_matches = [5, 9, 1000]
	matches_mismatches = [-5, 0, 2]

	str_examples = [
		("GreaterThan(12)", GreaterThan(12)),
	]

	describe_examples = [
		('5 is not < 4', 4, GreaterThan(5)),
		('4 is not < 4', 4, GreaterThan(4)),
	]
	
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)