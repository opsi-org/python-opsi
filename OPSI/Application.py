
import sys, types

from OPSI.Logger import Logger
logger = Logger()


class AppRunner(object):
	
	def __init__(self, app, config):
		self._app = app
		self._config = config
	
	def run(self):
		self._app.run()



class _BaseProfiler(AppRunner):

	def _getProfiler(self):
		raise NotImplementedError("Subclass must implement this.")
	
	def run(self):
		try:
			import pstats
			p = self._getProfiler()
			p.runcall(self._app.run)
			
			out = self._config.get("profile")
			
			f = open(out,"w")
			try:
				s = pstats.Stats(p, stream=f)
				s.strip_dirs()
				s.sort_stats(-1)
				s.print_stats()

			finally:
				f.close()
		
		except ImportError, e:
			logger.error("Failed to load profiler %s. Make sure the profiler module is installed on your system. (%s)" %(self._config.get("profiler"), e))
			raise e
		
		
class ProfileRunner(_BaseProfiler):

	def _getProfiler(self):
			import profile
			return profile.Profile()
		
class CProfileRunner(_BaseProfiler):
	
	def _getProfiler(self):
			import cProfile
			return cProfile.Profile()


class Application(object):
	
	profiler = {	"profiler": ProfileRunner,
			"cprofiler": CProfileRunner}
	
	def __init__(self, config):
		self._config = config
		self._app = self._getApplication()
		self._runner = self._getRunner()
		
	def _getApplication(self):
		raise NotImplementedError("Subclass must implement this function.")
	
	def _getRunner(self):
		if self._config.get("profile", False):
			profiler = self._config.get("profiler", "profiler").lower()
			if profiler in self.profiler:
				return self.profiler[profiler](self._app, self._config)
			raise NotImplementedError("Profiler %s is not supported." % profiler)
		return AppRunner(self._app, self._config)

	def setup(self):
		pass

	def shutdown(self):
		pass

	def run(self):
		
		try:
			self.setup()
			return self._runner.run()
		finally:
			self.shutdown()
		