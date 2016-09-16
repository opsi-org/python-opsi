#! /usr/bin/env python
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
Testing behaviour of exceptions.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import print_function

import time

import pytest

from OPSI.Types import (BackendError, OpsiError, OpsiProductOrderingError,
    OpsiBackupFileError, OpsiBackupFileNotFound, OpsiBackupBackendNotFound,
    OpsiAuthenticationError, OpsiServiceVerificationError, OpsiBadRpcError,
    OpsiRpcError, OpsiConnectionError, OpsiTimeoutError, OpsiVersionError,
    BackendIOError, BackendConfigurationError, BackendReferentialIntegrityError,
    BackendBadValueError, BackendMissingDataError, BackendAuthenticationError,
    BackendPermissionDeniedError, BackendTemporaryError,
    BackendUnaccomplishableError, BackendModuleDisabledError,
    LicenseConfigurationError, LicenseMissingError, RepositoryError)


@pytest.fixture(
    params=[
        OpsiError, OpsiProductOrderingError, BackendError,
        OpsiBackupFileError, OpsiBackupFileNotFound,
        OpsiBackupBackendNotFound, OpsiAuthenticationError,
        OpsiServiceVerificationError, OpsiBadRpcError, OpsiRpcError,
        OpsiConnectionError, OpsiTimeoutError, OpsiVersionError,
        BackendIOError, BackendConfigurationError,
        BackendReferentialIntegrityError, BackendBadValueError,
        BackendMissingDataError, BackendAuthenticationError,
        BackendPermissionDeniedError, BackendTemporaryError,
        BackendUnaccomplishableError, BackendModuleDisabledError,
        LicenseConfigurationError, LicenseMissingError, RepositoryError
    ],
)
def exceptionClass(request):
    yield request.param


@pytest.fixture(
    params=[
        1,
        True,
        time.localtime(),
        u'unicode string',
        u'utf-8 string: äöüß€'.encode('utf-8'),
        u'windows-1258 string: äöüß€'.encode('windows-1258'),
        u'utf-16 string: äöüß€'.encode('utf-16'),
        u'latin1 string: äöüß'.encode('latin-1'),
    ],
    ids=[
        'int', 'bool', 'time', 'unicode', 'utf8-encoded',
        'windows-1258-encoded', 'utf16-encoded', 'latin1-encoded'
    ]
)
def exceptionParameter(request):
    yield request.param


@pytest.fixture
def exception(exceptionClass, exceptionParameter):
    yield exceptionClass(exceptionParameter)


def testExceptionCanBePrinted(exception):
    print(exception)


def testExceptionHas__repr__(exception):
    r = repr(exception)

    assert r.startswith('<')
    assert exception.__class__.__name__ in r
    assert r.endswith('>')


def testOpsiProductOrderingErrorOrderingIsAccessible():
    error = OpsiProductOrderingError('message', [3, 4, 5])
    assert [3, 4, 5] == error.problematicRequirements


def testExceptionIsSubClassOfOpsiError(exceptionClass):
    with pytest.raises(OpsiError):
        raise exceptionClass('message')
