#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing basic backends.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path

from OPSI.Backend.Backend import ExtendedBackend
from OPSI.Types import BackendError, BackendMissingDataError
from OPSI.Util import randomString
from .test_hosts import getConfigServer
from .helpers import workInTemporaryDirectory

import pytest


def testGettingBackendInfoWithoutBackend():
    backend = ExtendedBackend(None)
    backend.backend_info()


def testSettingAndGettingUserCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    with pytest.raises(BackendMissingDataError):
        backend.user_getCredentials('unknown')

    backend.user_setCredentials(username="hans", password='blablabla')

    credentials = backend.user_getCredentials(username="hans")
    assert 'blablabla' == credentials['password']


def testOverWritingOldCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    backend.user_setCredentials(username="hans", password='bla')
    backend.user_setCredentials(username="hans", password='itworks')

    credentials = backend.user_getCredentials(username="hans")
    assert 'itworks' == credentials['password']


def testWorkingWithManyCredentials(fakeCredentialsBackend):
    backend = fakeCredentialsBackend

    for _ in range(100):
        backend.user_setCredentials(username=randomString(12),
                                    password=randomString(12))
    backend.user_setCredentials(username="hans", password='bla')

    credentials = backend.user_getCredentials(username="hans")
    assert 'bla' == credentials['password']


def testSettingUserCredentialsWithoutDepot(fakeCredentialsBackend):
    backend = fakeCredentialsBackend
    backend.host_deleteObjects(backend.host_getObjects())

    with pytest.raises(Exception):
        backend.user_setCredentials("hans", '')


@pytest.yield_fixture
def fakeCredentialsBackend(configDataBackend):
    backend = configDataBackend
    backend.host_insertObject(getConfigServer())  # Required for file backend.

    with workInTemporaryDirectory() as tempDir:
        credFile = os.path.join(tempDir, 'credentials')
        with open(credFile, 'w'):
            pass

        originalFile = backend._opsiPasswdFile
        backend._opsiPasswdFile = credFile
        try:
            yield backend
        finally:
            backend._opsiPasswdFile = originalFile


def testBackend_info(configDataBackend):
    info = configDataBackend.backend_info()

    assert 'opsiVersion' in info
    assert 'modules' in info
    assert 'realmodules' in info


def testBackend_getSharedAlgorithmThrowsExceptionIfAlgoUnknown(configDataBackend):
    with pytest.raises(BackendError):
        configDataBackend.backend_getSharedAlgorithm("foo")


def testBackend_getInterface(configDataBackend):
    """
    Testing the behaviour of backend_getInterface.

    The method descriptions in `expected` may vary and should be
    reduced if problems because of missing methods occur.
    """
    print("Base backend {0!r}".format(configDataBackend))
    try:
        print("Checking with backend {0!r}".format(configDataBackend._backend._backend))
    except AttributeError:
        try:
            print("Checking with backend {0!r}".format(configDataBackend._backend))
        except AttributeError:
            pass

    expected = [
        {'name': 'backend_getInterface', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'backend_getOptions', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'backend_info', 'args': ['self'], 'params': [], 'defaults': None, 'varargs': None, 'keywords': None},
        {'name': 'configState_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'config_getIdents', 'args': ['self', 'returnType'], 'params': ['*returnType', '**filter'], 'defaults': ('unicode',), 'varargs': None, 'keywords': 'filter'},
        {'name': 'host_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'productOnClient_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
        {'name': 'productPropertyState_getObjects', 'args': ['self', 'attributes'], 'params': ['*attributes', '**filter'], 'defaults': ([],), 'varargs': None, 'keywords': 'filter'},
    ]

    results = configDataBackend.backend_getInterface()
    for selection in expected:
        for result in results:
            if result['name'] == selection['name']:
                print('Checking {0}'.format(selection['name']))
                for parameter in ('args', 'params', 'defaults', 'varargs', 'keywords'):
                    print('Now checking parameter {0!r}, expecting {1!r}'.format(parameter, selection[parameter]))
                    singleResult = result[parameter]
                    if isinstance(singleResult, (list, tuple)):
                        # We do check the content of the result
                        # because JSONRPC-Backends can only work
                        # with JSON and therefore not with tuples
                        assert len(singleResult) == len(selection[parameter])

                        for exp, res in izip(singleResult, selection[parameter]):
                            assert exp == res
                    else:
                        assert singleResult == selection[parameter]

                break  # We found what we are looking for.
        else:
            pytest.fail("Expected method {0!r} not found".format(selection['name']))
