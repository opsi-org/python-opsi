# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import time
from typing import Generator

import pytest
from hypothesis import given, strategies


class FixtureRequest:
	param: str


exception_classes = []
pre_globals = list(globals())
from opsi.exception import (  # noqa: E402,F401
	OperatingSystemUnsupportedError,
	OpsiBadRpcError,
	OpsiError,
	OpsiLicenseConfigurationError,
	OpsiLicenseMissingError,
	OpsiRepositoryError,
	OpsiRpcError,
	OpsiServiceAuthenticationError,
	OpsiServiceClientCertificateError,
	OpsiServiceConnectionError,
	OpsiServiceConnectionRefusedError,
	OpsiServiceError,
	OpsiServicePermissionError,
	OpsiServiceTimeoutError,
	OpsiServiceUnavailableError,
	OpsiServiceVerificationError,
)

exception_classes = [obj for name, obj in dict(globals()).items() if name not in pre_globals and name != "pre_globals"]


@pytest.fixture(
	params=exception_classes,
)
def exception_class(request: FixtureRequest) -> Generator[str, None, None]:
	yield request.param


@pytest.fixture(
	params=[
		"",
		1,
		True,
		time.localtime(),
		"unicode string",
		"utf-8 string: äöüß€".encode(),
		"windows-1258 string: äöüß€".encode("windows-1258"),
		"utf-16 string: äöüß€".encode("utf-16"),
		"latin1 string: äöüß".encode("latin-1"),
	],
	ids=["empty", "int", "bool", "time", "unicode", "utf8-encoded", "windows-1258-encoded", "utf16-encoded", "latin1-encoded"],
)
def exception_parameter(request: FixtureRequest) -> Generator[str, None, None]:
	yield request.param


@pytest.fixture
def exception(exception_class: type[Exception], exception_parameter: str) -> Generator[Exception, None, None]:
	yield exception_class(exception_parameter)


def test_exception_can_be_printed(exception: Exception) -> None:
	print(exception)


def test_exception_is_sub_class_of_opsi_error(exception_class: type[Exception]) -> None:
	with pytest.raises(OpsiError):
		raise exception_class("message")


@given(strategies.text())
def test_exception_constuctor_hypothesis(message: str) -> None:
	for cls in exception_classes:
		cls(message)
