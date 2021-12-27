# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing behaviour of exceptions.
"""

from __future__ import print_function

import time

import pytest

from OPSI.Exceptions import (BackendError, OpsiError, OpsiProductOrderingError,
	OpsiBackupFileError, OpsiBackupFileNotFound, OpsiBackupBackendNotFound,
	OpsiAuthenticationError, OpsiServiceVerificationError, OpsiBadRpcError,
	OpsiRpcError, OpsiConnectionError, OpsiTimeoutError,
	BackendIOError, BackendConfigurationError, BackendReferentialIntegrityError,
	BackendBadValueError, BackendMissingDataError, BackendAuthenticationError,
	BackendPermissionDeniedError, BackendTemporaryError,
	BackendUnaccomplishableError, BackendModuleDisabledError,
	BackendUnableToConnectError,
	LicenseConfigurationError, LicenseMissingError, RepositoryError)


@pytest.fixture(
	params=[
		OpsiError, OpsiProductOrderingError, BackendError,
		OpsiBackupFileError, OpsiBackupFileNotFound,
		OpsiBackupBackendNotFound, OpsiAuthenticationError,
		OpsiServiceVerificationError, OpsiBadRpcError, OpsiRpcError,
		OpsiConnectionError, OpsiTimeoutError,
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
