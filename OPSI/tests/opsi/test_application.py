
from testtools import TestCase
import fixtures, os, sys

from OPSI.Application import Application, ProfileRunner, CProfileRunner


class MockApp(object):
	def __init__(self):
		self.ran = False
	def run(self):
		if self.ran:
			raise Exception("App already ran.")
		self.ran = True

class TestApplication(Application):
	
	def __init__(self, config):
		Application.__init__(self, config)
		
		steps = []
		self.steps = steps
	
	def setup(self):
		self.steps.append("setup")
		
	def shutdown(self):
		self.steps.append("shutdown")

	def _getApplication(self):
		return MockApp()

class ApplicationTests(TestCase):
	
	def test_setupShutdown(self):
		
		a = TestApplication({})
		
		class MockRunner(object):
			def run(self):
				a.steps.append("run")
		
		a._runner = MockRunner()
		a.run()
		
		self.assertEquals(["setup", "run", "shutdown"], a.steps)
	
	def test_profile(self):
		
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
		
		config = {"profile": path,
			  "profiler": "profiler"}
		
		a = TestApplication(config)
		a.run()
		self.assertTrue(a._app.ran)
		data = file(path).read()
		self.assertIn("MockApp.run", data)
		self.assertIn("function calls", data)
		
	def test_cprofile(self):
		
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
		
		config = {"profile": path,
			  "profiler": "cProfiler"}
		
		a = TestApplication(config)
		a.run()
		self.assertTrue(a._app.ran)
		data = file(path).read()
		self.assertIn("run", data)
		self.assertIn("function calls", data)
		
	def test_assertNoProfiler(self):
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
		
		mods = sys.modules.copy()
		sys.modules["cProfile"] = None
		
		config = {"profile": path,
			  "profiler": "cProfiler"}
		
		a = TestApplication(config)
		
		try:
			self.assertRaises(ImportError, a.run)
		finally:
			sys.modules.clear()
			sys.modules.update(mods)
			
	def test_unknownProfiler(self):
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
	
		config = {"profile": path,
			  "profiler": "foobar"}
	
		self.assertRaises(NotImplementedError, TestApplication, config )
	
	def test_defaultProfiler(self):
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
		
		config = {"profile": path}
		a = TestApplication(config)
		self.assertEquals(a._runner.__class__, ProfileRunner)
	
	def test_caseSensetiveProfilerName(self):
		
		td = self.useFixture(fixtures.TempDir())
		path = os.path.join(td.path, "profile")
		
		config = {"profile": path,
			  "profiler": "cPrOfIlEr"}
		
		a = TestApplication(config)
		self.assertEquals(a._runner.__class__, CProfileRunner)
		

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)