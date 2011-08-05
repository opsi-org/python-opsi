

import testtools
from testtools.matchers import Annotate, Not

from OPSI.tests.helper.matchers import In, GreaterThan


class TestCase(testtools.TestCase):
	
	def useFixture(self, fixture):
		fixture.test = self
		return super(TestCase, self).useFixture(fixture)

	def assertIn(self, needle, haystack, message=''):
		matcher = In(haystack)
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(needle, matcher)
		
	def assertNotIn(self, needle, haystack, message=''):
		matcher = Not(In(haystack))
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(needle, matcher)

	def assertGreater(self, matchee, expected, message=''):
		matcher = GreaterThan(expected)
		if message:
			matcher = Annotate(message, matcher)
		self.assertThat(matchee, matcher)