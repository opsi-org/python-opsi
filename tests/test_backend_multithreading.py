# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2019 uib GmbH <info@uib.de>

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
Testing backend multithreading behaviour.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import threading
import time

import pytest

from OPSI.Backend.Backend import ExtendedConfigDataBackend
from .test_groups import fillBackendWithObjectToGroups


@pytest.mark.parametrize("numberOfThreads", [50])
def testMultiThreadingBackend(multithreadingBackend, numberOfThreads):
	backend = ExtendedConfigDataBackend(multithreadingBackend)

	MySQLdb = pytest.importorskip("MySQLdb")
	IntegrityError = MySQLdb.IntegrityError
	errorConstants = pytest.importorskip("MySQLdb.constants.ER")
	DUP_ENTRY = errorConstants.DUP_ENTRY

	o2g, _, clients = fillBackendWithObjectToGroups(backend)

	class MultiThreadTester(threading.Thread):
		def __init__(self, backend, clients, objectToGroups):
			threading.Thread.__init__(self)

			self.exitCode = 0
			self.errorMessage = None

			self.backend = backend
			self.clients = clients
			self.objectToGroups = objectToGroups

		def run(self):
			self.client1 = clients[0]
			self.client2 = clients[1]
			self.objectToGroup1 = o2g[0]
			self.objectToGroup2 = o2g[1]

			try:
				print(u"Thread %s started" % self)
				time.sleep(1)
				self.backend.host_getObjects()
				self.backend.host_deleteObjects(self.client1)

				self.backend.host_getObjects()
				self.backend.host_deleteObjects(self.client2)

				self.backend.host_createObjects(self.client2)
				self.backend.host_createObjects(self.client1)
				self.backend.objectToGroup_createObjects(self.objectToGroup1)
				self.backend.objectToGroup_createObjects(self.objectToGroup2)

				self.backend.host_getObjects()
				self.backend.host_createObjects(self.client1)
				self.backend.host_deleteObjects(self.client2)
				self.backend.host_createObjects(self.client1)
				self.backend.host_getObjects()
			except IntegrityError as e:
				if e.args[0] != DUP_ENTRY:
					self.errorMessage = e.msg
					self.exitCode = 2
			except Exception as e:
				self.errorMessage = e
				self.exitCode = 1
			finally:
				print(u"Thread %s done" % self)

	mtts = [MultiThreadTester(backend, clients, o2g) for i in range(numberOfThreads)]
	for mtt in mtts:
		mtt.start()

	for mtt in mtts:
		mtt.join()

	client1 = clients[0]
	backend.host_createObjects(client1)

	while mtts:
		mtt = mtts.pop(0)
		if not mtt.is_alive():
			assert 0 == mtt.exitCode, u"Multithreading test failed: Exit Code {0.exitCode}: {0.errorMessage}".format(mtt)
		else:
			mtts.append(mtt)
