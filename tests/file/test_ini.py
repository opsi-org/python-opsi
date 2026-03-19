# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only
from pathlib import Path

import pytest

from opsi.file import ini
from opsi.file.ini._ini import IniParseError
from tests.file.conftest import PATH_TYPES

ENCODING = "utf-8"


def test_has_section(tmp_path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	with ini.open(file) as f:
		assert f.has_section("section")
		assert not f.has_section("missing")


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_has_section_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	file = path_type(str(file))
	assert ini.has_section(file, "section")
	assert not ini.has_section(file, "missing")


def test_has_option(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	with ini.open(file) as f:
		assert f.has_option("section", "option")
		assert not f.has_option("section", "missing")


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_has_option_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	file = path_type(str(file))
	assert ini.has_option(file, "section", "option")
	assert not ini.has_option(file, "section", "missing")


def test_set_option(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\n", encoding=ENCODING)

	with ini.open(file) as f:
		f.set_option("section", "option", "value")

	with ini.open(file) as f:
		assert f.get_option("section", "option") == "value"


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_set_option_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\n", encoding=ENCODING)

	file = path_type(str(file))
	ini.set_option(file, "section", "option", "value")

	assert ini.get_option(file, "section", "option") == "value"


def test_remove_option(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	with ini.open(file) as f:
		f.remove_option("section", "option")

	with ini.open(file) as f:
		assert not f.has_option("section", "option")


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_remove_option_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	file = path_type(str(file))
	ini.remove_option(file, "section", "option")

	assert not ini.has_option(file, "section", "option")


def test_remove_section(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	with ini.open(file) as f:
		f.remove_section("section")

	with ini.open(file) as f:
		assert not f.has_section("section")


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_remove_section_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[section]\noption=value\n", encoding=ENCODING)

	file = path_type(str(file))
	ini.remove_section(file, "section")

	assert not ini.has_section(file, "section")


def test_list_sections(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[a]\nx=1\n[b]\ny=2\n", encoding=ENCODING)

	with ini.open(file) as f:
		sections = f.list_sections()

	assert set(sections) == {"a", "b"}


@pytest.mark.parametrize("path_type", PATH_TYPES)
def test_list_sections_convenience(tmp_path: Path, path_type) -> None:
	file = tmp_path / "test.ini"
	file.write_text("[a]\nx=1\n[b]\ny=2\n", encoding=ENCODING)

	file = path_type(str(file))
	sections = ini.list_sections(file)

	assert set(sections) == {"a", "b"}


def test_roundtrip(tmp_path: Path) -> None:
	file = tmp_path / "test.ini"

	ini.set_option(file, "section", "option", "new_value")

	assert ini.has_option(file, "section", "option")
	assert ini.has_section(file, "section")
	assert ini.get_option(file, "section", "option") == "new_value"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-32", "latin-1"])
def test_encoding_match(tmp_path: Path, encoding) -> None:
	file = tmp_path / "test.ini"
	ini.set_option(file, "section", "option", "value with ümlauts", encoding=encoding)

	value = ini.get_option(file, "section", "option", encoding=encoding)

	assert value == "value with ümlauts"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-32"])
def test_encoding_mismatch(tmp_path: Path, encoding) -> None:
	file = tmp_path / "test.ini"
	ini.set_option(file, "section", "option", "value with ümlauts", encoding="latin-1")

	with pytest.raises(IniParseError):
		ini.get_option(file, "section", "option", encoding=encoding)
