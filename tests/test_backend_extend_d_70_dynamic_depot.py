# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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

The dynamic depot selection is dynamically loaded onto to the backend
and the user usually selects one of the offered variants.
The code is listet as cleartext because the client makes a call to the
webservice, receives the code and then makes a runnable version of it
through ``exec``.


.. versionadded:: 4.0.4.6

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

import random
import pytest

from OPSI.Logger import Logger

# Logger is needed because the functions expect a global "logger"
logger = Logger()


def testDepotSelectionAlgorythmIsExecutable(depotSelectionAlgorythm):
	"""
	Executing the default configuration should never fail.
	"""
	exec(depotSelectionAlgorythm)


def testDepotSelectionAlgorythmReturnsMasterDepotIfNoAlternativesAreGiven(depotSelectionAlgorythm):
	exec(depotSelectionAlgorythm)

	masterDepot = FakeDepot('clients.master.depot')
	assert masterDepot == selectDepot({}, masterDepot)


def testDepotSelectionAlgorithmByLowestLatency(depotSelectionAlgorithmByLatency):
	exec(depotSelectionAlgorithmByLatency)

	masterDepot = FakeDepot('clients.master.depot')
	lowLatencyRepo = FakeDepot('x.y.z', latency=1.5)
	alternativeDepots = [FakeDepot('a'), lowLatencyRepo, FakeDepot('b', latency=5)]
	random.shuffle(alternativeDepots)
	assert lowLatencyRepo == selectDepot({}, masterDepot, alternativeDepots)


def testDepotSelectionByLatencyIgnoresDepotsWithoutLatency(depotSelectionAlgorithmByLatency):
	exec(depotSelectionAlgorithmByLatency)

	highLatencyRepo = FakeDepot('a', latency=10)
	alternativeDepots = [highLatencyRepo]
	random.shuffle(alternativeDepots)
	assert highLatencyRepo == selectDepot({}, FakeDepot('m', latency=None), alternativeDepots)


def testDepotSelectionAlgorithmByMasterDepotAndLatency(depotSelectionAlgorithmByMasterDepotAndLatency):
	masterDepot = FakeDepot('clients.master.depot')
	wantedRepo = FakeDepot('our.wanted.repo', latency=1, masterDepotId='clients.master.depot')
	alternativeDepots = [
		FakeDepot('another.master', latency=0.5),
		FakeDepot('sub.for.another.master', latency=0.4, masterDepotId='another.master'),
		wantedRepo,
		FakeDepot('slower.repo.with.right.master', latency=1.5, masterDepotId='clients.master.depot')
	]
	random.shuffle(alternativeDepots)

	exec(depotSelectionAlgorithmByMasterDepotAndLatency)
	assert wantedRepo == selectDepot({}, masterDepot, alternativeDepots)


@pytest.fixture(params=[
	'getDepotSelectionAlgorithm',  # must always return a working algo
	'getDepotSelectionAlgorithmByLatency',
	'getDepotSelectionAlgorithmByMasterDepotAndLatency',
	'getDepotSelectionAlgorithmByNetworkAddress'
])
def depotSelectionAlgorythm(request, backendManager):
	"""
	All possible algorythms.
	"""
	algorythm = getattr(backendManager, request.param)
	return algorythm()


@pytest.fixture
def depotSelectionAlgorithmByLatency(backendManager):
	algo = backendManager.getDepotSelectionAlgorithmByLatency()
	algo = patchPingFunctionalityInAlgorythm(algo)

	try:
		yield algo
	except Exception:
		showAlgoWithLineNumbers(algo)


@pytest.fixture
def depotSelectionAlgorithmByMasterDepotAndLatency(backendManager):
	algo = backendManager.getDepotSelectionAlgorithmByMasterDepotAndLatency()
	algo = patchPingFunctionalityInAlgorythm(algo)

	try:
		yield algo
	except Exception:
		showAlgoWithLineNumbers(algo)


def patchPingFunctionalityInAlgorythm(algorythm):
	testPingFunction = "ping = lambda host: host.latency"
	testUrlsplitFunction = "urlsplit = lambda host: (None, host, None, None, None, None)"

	algorythm = algorythm.replace("from OPSI.Util.Ping import ping", testPingFunction)
	algorythm = algorythm.replace("from OPSI.Util.HTTP import urlsplit", testUrlsplitFunction)

	for replacedPart in ("from OPSI.Util.Ping import ping", "from OPSI.Util.HTTP import urlsplit"):
		if replacedPart in algorythm:
			raise RuntimeError("Replacing {0} failed.".format(replacedPart))

	return algorythm


def showAlgoWithLineNumbers(algo):
	"""
	Prints the given algorythm with line numbers preceding each line.
	"""
	for number, line in enumerate(algo.split('\n')):
		print("{num}: {line}".format(num=number, line=line))


class FakeDepot(object):
	def __init__(self, id, latency=2, masterDepotId=None):
		self.id = id
		self.latency = latency
		self.repositoryRemoteUrl = self
		self.masterDepotId = masterDepotId

	def __repr__(self):
		return "<FakeDepot({id}, latency={latency}, masterDepotId={masterDepotId})>".format(**self.__dict__)

