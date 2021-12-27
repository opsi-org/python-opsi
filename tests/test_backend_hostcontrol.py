# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing the Host Control backend.
"""

from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Exceptions import BackendMissingDataError
from .test_hosts import getClients

import pytest


def testCallingStartAndStopMethod(hostControlBackend):
	"""
	Test if calling the methods works.

	This test does not check if WOL on these clients work nor that
	they do exist.
	"""
	clients = getClients()
	hostControlBackend.host_createObjects(clients)

	hostControlBackend._hostRpcTimeout = 1  # for faster finishing of the test

	hostControlBackend.hostControl_start([u'client1.test.invalid'])
	hostControlBackend.hostControl_shutdown([u'client1.test.invalid'])


def testhostControlReachableWithoutHosts(hostControlBackend):
	with pytest.raises(BackendMissingDataError):
		hostControlBackend.hostControl_reachable()


@pytest.fixture
def hostControlBackend(extendedConfigDataBackend):
	yield HostControlBackend(extendedConfigDataBackend)
