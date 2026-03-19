# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from typing import Literal

import pytest

from opsi.util import compare_versions


@pytest.mark.parametrize(
	"first, operator, second",
	[
		("1.0", "<", "2.0"),
		("2.0", ">", "1.0"),
		("1.0", "==", "1.0"),
		("1.2.3.5", "<=", "2.2.3.5"),
		("1.2.3.4-5~6", ">=", "1.2.3.4-5~1"),
	],
)
def test_comparing_versions_of_same_size(first: str, operator: Literal["<", "<=", "==", ">=", ">"], second: str) -> None:
	assert compare_versions(first, operator, second)


@pytest.mark.parametrize(
	"ver1, operator, ver2",
	[
		("1.0", "", "1.0"),
	],
)
def test_comparing_without_giving_operator_defaults_to_equal(ver1: str, operator: str, ver2: str) -> None:
	assert compare_versions(ver1, operator, ver2)  # type: ignore[arg-type]


def test_comparing_with_only_one_equality_sign() -> None:
	assert compare_versions("1.0", "=", "1.0")


@pytest.mark.parametrize(
	"first, operator, second", [("1.0or2.0", "<", "1.0or2.1"), ("1.0or2.0", "<", "1.1or2.0"), ("1.0or2.1", "<", "1.1or2.0")]
)
def test_comparing_or_versions(first: str, operator: Literal["<"], second: str) -> None:
	assert compare_versions(first, operator, second)


@pytest.mark.parametrize(
	"first, operator, second",
	[
		("20.09", "<", "21.h1"),
		("1.0.2s", "<", "1.0.2u"),
		("1.blubb.bla", "<", "1.foo"),
		("1.0.a", "<", "1.0.b"),
		("a.b", ">", "a.a"),
	],
)
def test_comparing_letter_versions(first: str, operator: Literal["<"], second: str) -> None:
	assert compare_versions(first, operator, second)


@pytest.mark.parametrize("operator", ["asdf", "+-", "<>", "!="])
def test_using_unknown_operator_fails(operator: str) -> None:
	with pytest.raises(ValueError):
		compare_versions("1", operator, "2")  # type: ignore[arg-type]


@pytest.mark.parametrize(
	"ver1, operator, ver2",
	[
		("1.0~20131212", "<", "2.0~20120101"),
		("1.0~20131212", "==", "1.0~20120101"),
	],
)
def test_ignoring_versions_with_wave_in_them(ver1: str, operator: Literal["<", "=="], ver2: str) -> None:
	assert compare_versions(ver1, operator, ver2)


@pytest.mark.parametrize("ver1, operator, ver2", [("abc-1.2.3-4", "==", "1.2.3-4"), ("1.2.3-4", "==", "abc-1.2.3-4")])
def test_using_invalid_version_strings_fails(ver1: str, operator: Literal["=="], ver2: str) -> None:
	with pytest.raises(ValueError):
		compare_versions(ver1, operator, ver2)


@pytest.mark.parametrize(
	"ver1, operator, ver2",
	[
		("1.1.0.1", ">", "1.1"),
		("1.1", "<", "1.1.0.1"),
		("1.1", "==", "1.1.0.0"),
	],
)
def test_comparisons_with_differnt_depths_are_made_the_same_depth(ver1: str, operator: Literal["<", ">", "=="], ver2: str) -> None:
	assert compare_versions(ver1, operator, ver2)


@pytest.mark.parametrize("ver1, operator, ver2", [("1-2", "<", "1-3"), ("1-2.0", "<", "1-2.1")])
def test_package_versions_are_compared_aswell(ver1: str, operator: Literal["<"], ver2: str) -> None:
	assert compare_versions(ver1, operator, ver2)
