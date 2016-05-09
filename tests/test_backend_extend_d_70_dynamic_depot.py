#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded dynamic depot extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/70_dynamic_depot.conf``.

.. versionadded:: 4.0.4.6

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import random
import unittest

from OPSI.Logger import Logger
from .Backends.File import FileBackendBackendManagerMixin

# Logger is needed because the functions expect a global "logger"
logger = Logger()


class FakeDepot(object):
	def __init__(self, id, latency=2, masterDepotId=None):
		self.id = id
		self.latency = latency
		self.repositoryRemoteUrl = self
		self.masterDepotId = masterDepotId

	def __repr__(self):
		return "<FakeDepot({id}, latency={latency}, masterDepotId={masterDepotId})>".format(**self.__dict__)


class DynamicDepotTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
	"""
	Testing the dynamic depot selection.

	The dynamic depot selection is dynamically loaded onto to the
	backend and the user usually selects one of the offered variants.
	The code is listet as cleartext because the client makes a call
	to the webservice, receives the code and then makes a runnable
	version of it via ``exec``.
	"""
	def setUp(self):
		self.setUpBackend()

		self.masterDepot = FakeDepot('clients.master.depot')

	def tearDown(self):
		self.tearDownBackend()

		del self.masterDepot

	def getAlgorythm(self):
		return self.backend.getDepotSelectionAlgorithm()

	def testAlgorythmIsExecutable(self):
		"""
		Executing the default configuration should never fail.
		"""
		algo = self.getAlgorythm()
		self.showAlgoWithLineNumbers(algo)
		exec(algo)

	def testAlgorythmReturnsMasterDepotIfNoAlternativesAreGiven(self):
		exec(self.getAlgorythm())
		self.assertEqual(self.masterDepot, selectDepot({}, self.masterDepot))

	@staticmethod
	def showAlgoWithLineNumbers(algo):
		"""
		Prints the given algorythm with line numbers preceding each line.
		"""
		for number, line in enumerate(algo.split('\n')):
			print("{num}: {line}".format(num=number, line=line))

	def patchPingFunctionalityInAlgorythm(self, algorythm):
		testPingFunction = "ping = lambda host: host.latency"
		testUrlsplitFunction = "urlsplit = lambda host: (None, host, None, None, None, None)"

		algorythm = algorythm.replace("from OPSI.Util.Ping import ping", testPingFunction)
		algorythm = algorythm.replace("from OPSI.Util.HTTP import urlsplit", testUrlsplitFunction)

		for replacedPart in ("from OPSI.Util.Ping import ping", "from OPSI.Util.HTTP import urlsplit"):
			if replacedPart in algorythm:
				self.fail("Replacing {0} failed.".format(replacedPart))

		return algorythm


class DepotSelectionByLatencyTestCase(DynamicDepotTestCase):
	def getAlgorythm(self):
		algo = self.backend.getDepotSelectionAlgorithmByLatency()
		algo = self.patchPingFunctionalityInAlgorythm(algo)

		self.showAlgoWithLineNumbers(algo)

		return algo

	def testDepotSelectionAlgorithmByLowestLatency(self):
		exec(self.getAlgorythm())

		lowLatencyRepo = FakeDepot('x.y.z', latency=1.5)
		alternativeDepots = [FakeDepot('a'), lowLatencyRepo, FakeDepot('b', latency=5)]
		random.shuffle(alternativeDepots)
		self.assertEqual(lowLatencyRepo, selectDepot({}, self.masterDepot, alternativeDepots))

	def testThatDepotsWithoutLatencyArentUsed(self):
		exec(self.getAlgorythm())

		highLatencyRepo = FakeDepot('a', latency=10)
		alternativeDepots = [highLatencyRepo]
		random.shuffle(alternativeDepots)
		self.assertEqual(highLatencyRepo, selectDepot({}, FakeDepot('m', latency=None), alternativeDepots))


class DepotSelectionByMasterDepotAndLatencyTestCase(DynamicDepotTestCase):
	def getAlgorythm(self):
		algo = self.backend.getDepotSelectionAlgorithmByMasterDepotAndLatency()
		algo = self.patchPingFunctionalityInAlgorythm(algo)

		self.showAlgoWithLineNumbers(algo)

		return algo

	def testDepotSelectionAlgorithmByMasterDepotAndLatency(self):
		wantedRepo = FakeDepot('our.wanted.repo', latency=1, masterDepotId='clients.master.depot')
		alternativeDepots = [
			FakeDepot('another.master', latency=0.5),
			FakeDepot('sub.for.another.master', latency=0.4, masterDepotId='another.master'),
			wantedRepo,
			FakeDepot('slower.repo.with.right.master', latency=1.5, masterDepotId='clients.master.depot')
		]
		random.shuffle(alternativeDepots)

		exec(self.getAlgorythm())
		self.assertEqual(wantedRepo, selectDepot({}, self.masterDepot, alternativeDepots))


class DepotSelectionByNetworkAddressTestCase(DynamicDepotTestCase):
	# TODO: functional test
	def getAlgorythm(self):
		algo = self.backend.getDepotSelectionAlgorithmByNetworkAddress()
		self.showAlgoWithLineNumbers(algo)
		return algo


if __name__ == '__main__':
	unittest.main()
