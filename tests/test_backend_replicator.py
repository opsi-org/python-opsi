#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015 uib GmbH <info@uib.de>

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
Testing backend replication.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Backend.Replicator import BackendReplicator


class ReplicatorTestCase(unittest.TestCase):
    # TODO: there are some cases we should test
    # * cleanupBackend
    # * handling backends with / without license management
    # * handling replicating the audit data

    def testInitialisation(self):
        replicator = BackendReplicator(None, None)

    # def testReplication(self):
    #     class FileBackend:
    #         # TODO: replace this with a real backend
    #         pass

    #     readBackend = FileBackend()
    #     writeBackend = FileBackend()

    #     # TODO: fill the backend for reading

    #     # TODO: make sure that there is no data in writebackend

    #     replicator = BackendReplicator(readBackend, writeBackend)

    #     # TODO: Test replication process

    #     # TODO: test if the data from backend1 == data from backend2




if __name__ == '__main__':
    unittest.main()
