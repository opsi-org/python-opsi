

import testtools

class TestCase(testtools.TestCase):
	
	def useFixture(self, fixture):
		fixture.test = self
		return super(TestCase, self).useFixture(fixture)
