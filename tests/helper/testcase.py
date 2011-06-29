

import testtools

class TestCase(testtools.TestCase):
	
	def useFixture(self, fixture):
		fixture.test = self
		super(TestCase, self).useFixture(fixture)