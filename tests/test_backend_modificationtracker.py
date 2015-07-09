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
Testing the modification tracking.

Based on work of Christian Kampka.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import time
import unittest
from contextlib import contextmanager

from OPSI.Backend.Backend import ModificationTrackingBackend
from OPSI.Object import OpsiClient

from .Backends.SQLite import getSQLiteBackend, getSQLiteModificationTracker

from .helpers import patchAddress


@contextmanager
def prepareBackendAndTracker():
    with patchAddress():
        with getSQLiteBackend() as basebackend:
            backend = ModificationTrackingBackend(basebackend)

            with getSQLiteModificationTracker() as tracker:
                backend.addBackendChangeListener(tracker)

                yield backend, tracker



class ModificationTrackerTestCase(unittest.TestCase):

    # TODO: test with more backends.

    def testInsertObject(self):
        with prepareBackendAndTracker() as (backend, tracker):
            host = OpsiClient(
                id='client1.test.invalid',
                description='Test client 1',
                notes='Notes ...',
                hardwareAddress='00:01:02:03:04:05',
                ipAddress='192.168.1.100',
                lastSeen='2009-01-01 00:00:00',
                opsiHostKey='45656789789012789012345612340123',
                inventoryNumber="$$4"
            )
            backend.host_insertObject(host)
            time.sleep(0.1)

            modifications = tracker.getModifications()
            self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
            self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
            self.assertEqual(modifications[0]['command'], 'insert', u"Expected command %s, but got '%s'" % ('insert', modifications[0]['command']))
            self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))

    def testUpdatingObject(self):
        with prepareBackendAndTracker() as (backend, tracker):
            host = OpsiClient(
                id='client1.test.invalid',
                description='Test client 1',
                notes='Notes ...',
                hardwareAddress='00:01:02:03:04:05',
                ipAddress='192.168.1.100',
                lastSeen='2009-01-01 00:00:00',
                opsiHostKey='45656789789012789012345612340123',
                inventoryNumber="$$4"
            )

            backend.host_insertObject(host)
            tracker.clearModifications()
            backend.host_updateObject(host)
            time.sleep(0.1)

            modifications = tracker.getModifications()
            self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
            self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
            self.assertEqual(modifications[0]['command'], 'update', u"Expected command %s, but got '%s'" % ('update', modifications[0]['command']))
            self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))

    def testDeletingObject(self):
        with prepareBackendAndTracker() as (backend, tracker):
            host = OpsiClient(
                id='client1.test.invalid',
                description='Test client 1',
                notes='Notes ...',
                hardwareAddress='00:01:02:03:04:05',
                ipAddress='192.168.1.100',
                lastSeen='2009-01-01 00:00:00',
                opsiHostKey='45656789789012789012345612340123',
                inventoryNumber="$$4"
            )
            backend.host_insertObject(host)
            tracker.clearModifications()
            backend.host_deleteObjects(host)
            time.sleep(0.1)

            modifications = tracker.getModifications()
            self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
            self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
            self.assertEqual(modifications[0]['command'], 'delete', u"Expected command %s, but got '%s'" % ('delete', modifications[0]['command']))
            self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))


if __name__ == '__main__':
    unittest.main()
