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
Testing the modification tracking.

Based on work of Christian Kampka.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from OPSI.Backend.Backend import ModificationTrackingBackend
from OPSI.Object import OpsiClient

from .Backends.SQLite import getSQLiteBackend, getSQLiteModificationTracker
from .Backends.MySQL import getMySQLBackend, getMySQLModificationTracker

import pytest


@pytest.fixture(
    params=[
        (getSQLiteBackend, getSQLiteModificationTracker),
        (getMySQLBackend, getMySQLModificationTracker),
    ],
    ids=['sqlite', 'mysql']
)
def backendAndTracker(request):
    backendFunc, trackerFunc = request.param
    with backendFunc() as basebackend:
        basebackend.backend_createBase()

        backend = ModificationTrackingBackend(basebackend)

        with trackerFunc() as tracker:
            backend.addBackendChangeListener(tracker)

            yield backend, tracker

            # When reusing a database there may be leftover modifications!
            tracker.clearModifications()

        backend.backend_deleteBase()


def testTrackingOfInsertObject(backendAndTracker):
    backend, tracker = backendAndTracker

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

    modifications = tracker.getModifications()
    assert 1 == len(modifications)
    mod = modifications[0]
    assert mod['objectClass'] == host.__class__.__name__
    assert mod['command'] == 'insert'
    assert mod['ident'] == host.getIdent()


def testTrackingOfUpdatingObject(backendAndTracker):
    backend, tracker = backendAndTracker

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

    modifications = tracker.getModifications()
    assert 1 == len(modifications)
    mod = modifications[0]
    assert mod['objectClass'] == host.__class__.__name__
    assert mod['command'] == 'update'
    assert mod['ident'] == host.getIdent()


def testTrackingOfDeletingObject(backendAndTracker):
    backend, tracker = backendAndTracker

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

    modifications = tracker.getModifications()

    assert 1 == len(modifications)
    modification = modifications[0]

    assert modification['objectClass'] == host.__class__.__name__
    assert modification['command'] == 'delete'
    assert modification['ident'] == host.getIdent()
