#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing application behaviour.

This is based on work by Christian Kampka.

:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import os
import sys

from OPSI.Application import Application, ProfileRunner, CProfileRunner

from .helpers import unittest, workInTemporaryDirectory

try:
	import pstats
except ImportError:
	# Probably on Debian 6.
	print("Could not import 'pstats'. Please run: apt-get install python-profiler")
	pstats = None


class MockApp(object):
	def __init__(self):
		self.ran = False

	def run(self):
		if self.ran:
			raise Exception("App already ran.")

		self.ran = True


class FakeApplication(Application):

	def __init__(self, config):
		Application.__init__(self, config)
		self.steps = []

	def setup(self):
		self.steps.append("setup")

	def shutdown(self):
		self.steps.append("shutdown")

	def _getApplication(self):
		return MockApp()


class ApplicationTests(unittest.TestCase):

	def testSetupShutdown(self):
		"""
		First we should do a setup and the last thing should be shutdown.
		"""
		a = FakeApplication({})

		class MockRunner(object):
			def run(self):
				a.steps.append("run")

		a._runner = MockRunner()
		a.run()

		self.assertEquals(["setup", "run", "shutdown"], a.steps)

	@unittest.skipIf(pstats is None, "Missing pstats module")
	def testProfiler(self):
		with workInTemporaryDirectory() as tempDir:
			path = os.path.join(tempDir, "profile")

			config = {
				"profile": path,
				"profiler": "profiler"
			}

			a = FakeApplication(config)
			a.run()
			self.assertTrue(a._app.ran)

			with open(path) as f:
				data = f.read()

		self.assertIn("MockApp.run", data)
		self.assertIn("function calls", data)

	@unittest.skipIf(pstats is None, "Missing pstats module")
	def testCProfiler(self):
		with workInTemporaryDirectory() as tempDir:
			path = os.path.join(tempDir, "profile")

			config = {
				"profile": path,
				"profiler": "cProfiler"
			}

			a = FakeApplication(config)
			a.run()
			self.assertTrue(a._app.ran)

			with open(path) as f:
				data = f.read()

		self.assertIn("run", data)
		self.assertIn("function calls", data)

	def testReactingToMissingProfiler(self):
		mods = sys.modules.copy()
		try:
			with workInTemporaryDirectory() as tempDir:
				path = os.path.join(tempDir, "profile")

				sys.modules["cProfile"] = None

				config = {
					"profile": path,
					"profiler": "cProfiler"
				}

				a = FakeApplication(config)

				self.assertRaises(ImportError, a.run)
		finally:
			sys.modules.clear()
			sys.modules.update(mods)

	def testUnknownProfiler(self):
		with workInTemporaryDirectory() as tempDir:
			path = os.path.join(tempDir, "profile")

			config = {
				"profile": path,
				"profiler": "foobar"
			}

			self.assertRaises(NotImplementedError, FakeApplication, config)

	def testDefaultProfiler(self):
		with workInTemporaryDirectory() as tempDir:
			path = os.path.join(tempDir, "profile")
			config = {"profile": path}
			a = FakeApplication(config)
			self.assertEquals(a._runner.__class__, ProfileRunner)

	def testCaseInsensitiveProfilerName(self):
		with workInTemporaryDirectory() as tempDir:
			path = os.path.join(tempDir, "profile")

			config = {
				"profile": path,
				"profiler": "cPrOfIlEr"
			}

			a = FakeApplication(config)
			self.assertEquals(a._runner.__class__, CProfileRunner)
