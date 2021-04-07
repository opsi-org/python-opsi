# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Applications for the use of opsi in an twisted-application context.
"""

from OPSI.Logger import Logger

LOGGER = Logger()


class AppRunner(object):

	def __init__(self, app, config):
		self._app = app
		self._config = config

	def run(self):
		self._app.run()


class _BaseProfiler(AppRunner):

	def _getProfiler(self):
		raise NotImplementedError(u"Subclass must implement this.")

	def run(self):
		try:
			import pstats
			profiler = self._getProfiler()
			profiler.runcall(self._app.run)

			out = self._config.get("profile")

			with open(out, "w") as outputfile:
				statistics = pstats.Stats(profiler, stream=outputfile)
				statistics.strip_dirs()
				statistics.sort_stats(-1)
				statistics.print_stats()

		except ImportError as error:
			LOGGER.error(
				u"Failed to load profiler {name}. Make sure the profiler "
				u"module is installed on your system. ({error})".format(
					name=self._config.get("profiler"),
					error=error
				)
			)
			raise error


class ProfileRunner(_BaseProfiler):

	def _getProfiler(self):
		import profile
		return profile.Profile()


class CProfileRunner(_BaseProfiler):

	def _getProfiler(self):
		import cProfile
		return cProfile.Profile()


class Application(object):

	profiler = {
		"profiler": ProfileRunner,
		"cprofiler": CProfileRunner
	}

	def __init__(self, config):
		self._config = config
		self._app = self._getApplication()
		self._runner = self._getRunner()

	def _getApplication(self):
		raise NotImplementedError(u"Subclass must implement this function.")

	def _getRunner(self):
		if self._config.get("profile", False):
			profiler = self._config.get("profiler", "profiler").lower()
			if profiler in self.profiler:
				return self.profiler[profiler](self._app, self._config)

			raise NotImplementedError(
				u"Profiler {0} is not supported.".format(profiler)
			)

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
